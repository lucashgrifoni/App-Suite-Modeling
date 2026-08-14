"""
Cinco defeitos de baixa severidade da auditoria da fase 3, agrupados por causa.

Nenhum é explorável para acesso indevido. Três são de **integridade de saída** — o artefacto que
sai não é o que o consumidor a jusante espera — e dois são de **limite de entrada** ausente num
sítio onde os irmãos já o têm. Ficam juntos porque separá-los em cinco commits daria mais ruído
do que sinal.

## Integridade de saída

**JSON com `NaN`/`Infinity`.** `json.dumps` aceita não-finitos por omissão e escreve `NaN` cru,
que **não é JSON** — nenhum parser fora de Python o lê. Um consumidor em Go ou Java rejeita o
documento inteiro; o `jq` reescreve silenciosamente o valor para `null`, o que num campo de score
é pior do que rejeitar. Hoje todos os scores calculados são finitos, por isso isto é uma rede de
segurança e não a correção de um bug ativo: `allow_nan=False` transforma um artefacto inválido
emitido em silêncio num erro alto e claro no momento em que for gerado.

**ANSI e NUL em Markdown.** `md_inline`/`md_block` achatavam terminadores de linha e deixavam
passar tudo o resto. `CSI 2K` + `CSI G` num nome de componente repintam a linha num terminal — o
`otm report` escreve para stdout com um `print()` — e um NUL literal fica dentro do `.md`
entregue. Não muda o *contorno* do documento, por isso o oráculo de estrutura não o via; muda o
que o leitor vê, que é o mesmo ativo.

**Separadores de linha Unicode em Mermaid.** `_LABEL_CONTROL_RE` cobria `\\r\\n\\t\\f\\v` e não
cobria NEL (U+0085), LINE SEPARATOR (U+2028) e PARAGRAPH SEPARATOR (U+2029). O invariante que o
exportador declara é "um nome não pode acrescentar uma linha"; estes três acrescentam. Não foi
demonstrada injeção de statement — as aspas seguram —, por isso é `INFO`, mas o invariante é do
exportador e estava falso.

## Limite de entrada

**Profundidade do ficheiro de regras.** `load_custom_rules` tem tecto de bytes e usa
`yaml.safe_load` — o mesmo `safe_load` sem tecto de profundidade que já foi corrigido para o
documento canónico em `f96817a`. Um ficheiro de 4 KB rebentava a pilha e saía como
`RecursionError` cru, fora do contrato `ValueError`/`CliUserError` que o próprio loader declara.
A correção é ligar o consumidor ao limite que já existe, não inventar outro.

**Comprimento de cada `refs`.** `max_length=20` limita a **lista**, não cada string: um único
item de 400 000 caracteres passava, enquanto `title`, `description` e os restantes campos irmãos
têm tecto próprio. O ref entra no relatório e no SARIF por cada ameaça que a regra dispara, por
isso o custo multiplica pela população que casa.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_json, export_document_json
from otm_exporters.markdown_text import md_block, md_inline
from otm_exporters.mermaid_flowchart import _mermaid_label
from otm_threat_engine import analyze_document
from otm_threat_engine.custom_rules import CustomRuleSet
from otm_threat_engine.custom_rules.loader import load_custom_rules

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


# --- integridade de saída: JSON -----------------------------------------------------------


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_the_exporter_refuses_a_non_finite_score_instead_of_writing_invalid_json(value: float) -> None:
    """`NaN` cru não é JSON. Falhar alto vale mais do que emitir um ficheiro que ninguém lê.

    Exercita o **exportador**, não o `json.dumps`. A primeira versão deste teste asseriva
    `json.dumps({...}, allow_nan=False)` e passaria com a correção revertida, porque testava a
    biblioteca-padrão em vez da mudança — o mesmo defeito de oráculo que esta fase encontrou nos
    testes de estrutura Markdown.

    O caminho é real: `risk.score` é um `float` do Pydantic e aceita atribuição de não-finito, por
    isso um score corrompido a montante chegava ao ficheiro em vez de ser recusado.
    """
    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    threat = next(t for t in result.heuristic_threats if t.risk)
    threat.risk.score = value

    with pytest.raises(ValueError, match="JSON compliant"):
        export_analysis_json(result)


def test_the_shipped_model_still_exports_parseable_json() -> None:
    """Controlo: a rede de segurança não pode ter apanhado o caso normal."""
    text = export_document_json(load_document_from_yaml_path(_MINIMAL))

    assert json.loads(text)["metadata"]["title"]


# --- integridade de saída: Markdown --------------------------------------------------------


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_ansi_escapes_do_not_survive_into_markdown(helper) -> None:
    """`CSI 2K` + `CSI G` repintam a linha de um terminal que mostre o relatório."""
    out = helper("Edge\x1b[2K\x1b[G REPAINTED")

    assert "\x1b" not in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_a_nul_byte_does_not_survive_into_markdown(helper) -> None:
    """Um NUL literal num `.md` entregue é lixo que nenhum autor escreveu de propósito."""
    out = helper("Edge\x00gateway")

    assert "\x00" not in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_the_visible_text_is_preserved(helper) -> None:
    """Neutralizar, não censurar — a mesma regra do resto do módulo."""
    out = helper("Edge\x1b[2K gateway")

    assert "Edge" in out
    assert "gateway" in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_ordinary_text_is_untouched(helper) -> None:
    assert helper("Edge gateway (HTTPS) — 99.9%") == "Edge gateway (HTTPS) — 99.9%"


# --- integridade de saída: Mermaid ---------------------------------------------------------


@pytest.mark.parametrize(
    ("separator", "name"),
    [("", "NEL"), (" ", "LINE SEPARATOR"), (" ", "PARAGRAPH SEPARATOR")],
)
def test_unicode_line_separators_cannot_add_a_line_to_a_mermaid_label(separator: str, name: str) -> None:
    """O invariante que o exportador declara: um nome não acrescenta uma linha."""
    label = _mermaid_label(f"a{separator}b")

    assert separator not in label


def test_the_separators_already_covered_still_are() -> None:
    """Não-regressão do que `_LABEL_CONTROL_RE` já cobria."""
    for separator in ("\r", "\n", "\t", "\f", "\v"):
        assert separator not in _mermaid_label(f"a{separator}b")


def test_a_normal_label_is_unchanged() -> None:
    assert "Edge gateway" in _mermaid_label("Edge gateway")


# --- limite de entrada: profundidade do ficheiro de regras ---------------------------------


def test_a_deeply_nested_rules_file_is_refused_as_a_value_error(tmp_path: Path) -> None:
    """O contrato do loader é `ValueError`; `RecursionError` escapava-lhe."""
    rules = tmp_path / "deep.yaml"
    rules.write_text("a: " + "[" * 3000 + "]" * 3000, encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_custom_rules(rules)

    assert not isinstance(exc.value, RecursionError)


def test_the_rules_file_bound_is_the_same_one_the_document_uses(tmp_path: Path) -> None:
    """Ligar o consumidor ao limite existente, em vez de inventar um segundo."""
    from otm_core_schema.io import ENV_MAX_DOCUMENT_DEPTH

    rules = tmp_path / "deep.yaml"
    rules.write_text("a: " + "[" * 3000 + "]" * 3000, encoding="utf-8")

    with pytest.raises(ValueError, match=ENV_MAX_DOCUMENT_DEPTH):
        load_custom_rules(rules)


def test_an_ordinary_rules_file_still_loads(tmp_path: Path) -> None:
    rules = tmp_path / "ok.yaml"
    rules.write_text(
        "id: rs\n"
        "rules:\n"
        "  - id: a\n"
        "    title: 'Rule A'\n"
        "    stride: tampering\n"
        "    match:\n"
        "      component:\n"
        "        kind: [process]\n",
        encoding="utf-8",
    )

    assert load_custom_rules(rules).id == "rs"


# --- limite de entrada: comprimento de cada `refs` -----------------------------------------


def _ruleset(refs: list[str]) -> dict:
    return {
        "id": "rs",
        "rules": [
            {
                "id": "a",
                "title": "T",
                "stride": "tampering",
                "match": {"component": {"kind": ["process"]}},
                "refs": refs,
            }
        ],
    }


def test_an_enormous_single_ref_is_refused() -> None:
    """`max_length=20` limita a lista; cada item precisa do seu próprio tecto."""
    with pytest.raises(ValueError):
        CustomRuleSet.model_validate(_ruleset(["R" * 400_000]))


def test_an_ordinary_ref_is_accepted() -> None:
    ruleset = CustomRuleSet.model_validate(_ruleset(["ISO/IEC 27001:2022 A.8.24", "internal-std-014"]))

    assert ruleset.rules[0].refs == ["ISO/IEC 27001:2022 A.8.24", "internal-std-014"]


def test_the_list_length_cap_still_applies() -> None:
    """A correção acrescenta um tecto; não pode ter removido o que já existia."""
    with pytest.raises(ValueError):
        CustomRuleSet.model_validate(_ruleset([f"ref-{i}" for i in range(50)]))
