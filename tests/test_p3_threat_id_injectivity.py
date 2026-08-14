"""
Duas ameaças distintas nunca podem partilhar um id.

`engine_stride_builder` emite `f"eng_{comp.id}_{stride}"` para componentes e
`f"eng_flow_{flow.id}_{stride}"` para fluxos, **no mesmo espaço de nomes plano e sem escape do
separador**. `ENTITY_ID_PATTERN` permite um id de componente começado por `flow_`, e o validador
`_unique_ids` do schema corre por lista — nunca entre `components` e `data_flows`. Portanto um
componente `flow_svc` e um fluxo `svc` produzem ids byte-idênticos, e o documento passa em
`otm validate` como **Valid**, com 0 avisos estruturais.

Reproduzido no motor, sem envolver o gate:

    collide   heuristics=9  DUPLICATE_IDS={'eng_flow_svc_tampering': 2,
                                           'eng_flow_svc_information_disclosure': 2}

`custom_rules/runtime.py` tem o mesmo defeito por `f"{ID_PREFIX}_{ruleset.id}_{rule.id}_{target}"`,
onde `_` é legal dentro de um `RuleId` e dentro de um id de entidade: a regra `a` sobre o
componente `b_c` colide com a regra `a_b` sobre o componente `c`.

O que torna isto grave é que três consumidores colapsam o par **em silêncio**:

* `analysis_diff._active_heuristics` — `{h.id: h for h in ...}`, um dict: o último vence e uma
  ameaça desaparece **antes** de o diff correr;
* `merge.merge_heuristic_threats` — `if h.id in existing_ids: continue`, sem diagnóstico;
* `analysis_sarif` — `partialFingerprints.otmThreatId`, o campo que o GitHub code scanning usa
  como identidade do alerta.

A consequência que interessa: o gate de drift do CI passa a julgar uma ameaça **substituída** em
vez de uma **acrescentada**. Consoante a relação de scores, a mesma mudança sai como modificação,
como redução de risco, ou não sai de todo.

## Porque é um erro e não um id novo

A correção óbvia — tornar a junção injetiva, por exemplo `eng|{id}|{stride}` — muda **todos** os
ids. Isso invalidaria os fingerprints SARIF (o GitHub recriaria todos os alertas) e todas as
baselines guardadas: a primeira execução após a atualização reportaria cada ameaça como nova e
faria disparar os gates de toda a gente. Para uma ferramenta de CI isso é pior do que o defeito.

O modelo em causa é genuinamente **ambíguo**: dois sujeitos diferentes reclamam uma identidade. A
resposta certa é recusá-lo alto e claro, nomeando os dois sujeitos, e deixar o formato do id — que
`docs/features/CUSTOM_RULES.md` documenta como contrato — intacto para toda a gente que não tem
colisão nenhuma.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml
from otm_threat_engine import analyze_document

_BASE = """model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: saas
metadata:
  title: "Collision fixture"
  summary: "Fixture."
components:
  - id: user
    name: "User"
    kind: user
    in_trust_boundary: internet
  - id: {component_id}
    name: "Service"
    kind: datastore
    in_trust_boundary: vpc
trust_boundaries:
  - id: internet
    name: "Internet"
  - id: vpc
    name: "VPC"
data_flows:
  - id: seed
    name: "seed"
    from_component: user
    to_component: {component_id}
  - id: {flow_id}
    name: "second flow"
    from_component: user
    to_component: {component_id}
    protocol: "HTTP"
    authenticated: false
    encrypted: false
"""


def _doc(*, component_id: str, flow_id: str):
    return load_document_from_yaml(_BASE.format(component_id=component_id, flow_id=flow_id))


def _duplicate_ids(result) -> dict[str, int]:
    counts = collections.Counter(t.id for t in result.heuristic_threats)
    return {i: n for i, n in counts.items() if n > 1}


# --- o caso que colide --------------------------------------------------------------------


def test_a_component_named_flow_x_colliding_with_flow_x_is_refused() -> None:
    """Componente `flow_svc` + fluxo `svc` -> ambos produzem `eng_flow_svc_<stride>`."""
    doc = _doc(component_id="flow_svc", flow_id="svc")

    with pytest.raises(ValueError) as exc:
        analyze_document(doc)

    message = str(exc.value)
    assert "eng_flow_svc" in message


def test_the_refusal_names_both_subjects_and_the_way_out() -> None:
    """Um erro que diz "colisão" e não diz entre o quê obriga a ler o código do motor."""
    doc = _doc(component_id="flow_svc", flow_id="svc")

    with pytest.raises(ValueError) as exc:
        analyze_document(doc)

    message = str(exc.value)
    assert "flow_svc" in message
    assert "svc" in message
    assert "rename" in message.lower() or "renomeie" in message.lower()


def test_the_document_itself_still_validates() -> None:
    """Fixa a premissa: o schema aceita o modelo. A ambiguidade é do esquema de ids do motor,
    não do documento, e é por isso que a recusa vive no motor."""
    assert _doc(component_id="flow_svc", flow_id="svc") is not None


# --- o caso que não colide ----------------------------------------------------------------


def test_a_near_miss_is_not_refused() -> None:
    """`flow_svc` + `svc2` não colide: a recusa não pode ser um alarme sobre o prefixo."""
    result = analyze_document(_doc(component_id="flow_svc", flow_id="svc2"))

    assert _duplicate_ids(result) == {}


def test_an_ordinary_model_is_unaffected() -> None:
    """Nenhum id começado por `flow_`; nada aqui pode colidir."""
    result = analyze_document(_doc(component_id="svc", flow_id="second"))

    assert _duplicate_ids(result) == {}
    assert len(result.heuristic_threats) > 0


def test_the_shipped_example_still_analyses() -> None:
    """A rede de segurança contra uma verificação demasiado apertada."""
    example = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"
    from otm_core_schema import load_document_from_yaml_path

    result = analyze_document(load_document_from_yaml_path(example))

    assert _duplicate_ids(result) == {}
    assert len(result.heuristic_threats) > 0


# --- a mesma causa raiz nas regras personalizadas ------------------------------------------


def test_custom_rule_ids_that_collide_are_refused() -> None:
    """Regra `a` sobre componente `b_c` vs regra `a_b` sobre componente `c`: `custom_rs_a_b_c`.

    O comentário em `runtime.py` justificava a remoção de um guarda de de-duplicação dizendo que
    "um par nunca se repete". É verdade para o **par** e falso para a **string** em que ele é
    concatenado — que é exatamente o local do defeito.
    """
    from otm_threat_engine.custom_rules import CustomRuleSet

    model = _BASE.format(component_id="b_c", flow_id="second")
    doc = load_document_from_yaml(
        model.replace(
            "  - id: user\n",
            "  - id: c\n    name: 'C'\n    kind: process\n    in_trust_boundary: vpc\n  - id: user\n",
        )
    )

    rules = CustomRuleSet.model_validate(
        {
            "id": "rs",
            "rules": [
                {
                    "id": "a",
                    "title": "Rule A",
                    "stride": "tampering",
                    "match": {"component": {"kind": ["datastore"]}},
                },
                {
                    "id": "a_b",
                    "title": "Rule A B",
                    "stride": "tampering",
                    "match": {"component": {"kind": ["process"]}},
                },
            ],
        }
    )

    with pytest.raises(ValueError, match="custom_rs_a_b_c"):
        analyze_document(doc, custom_rules=rules)
