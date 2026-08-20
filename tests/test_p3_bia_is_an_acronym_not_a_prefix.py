""""bias" não é uma análise de impacto no negócio, e o recomendador achava que sim.

`compute_methodology_ranking` dá **+30** ao OCTAVE Allegro quando encontra contexto de BIA. A lista
de sinais compara por subcadeia e inclui o acrónimo `"bia"`, que mora dentro de **bias** — palavra
banal em qualquer modelo de ameaças de IA, e precisamente o vocabulário da lente PLOT4ai que este
produto vende.

Medido, no mesmo documento com uma frase de diferença:

    resumo sem a palavra                       vencedora=stride           octave=2.0
    "avaliamos bias do modelo periodicamente"  vencedora=octave_allegro   octave=32.0

A metodologia recomendada decide que lente corre e que ameaças o utilizador recebe.

`bia` é acrónimo, portanto pede fronteira dos **dois** lados (`has_token`) e não a regra de radical
usada para `admin`/*administrator*: "bias" começa por "bia", por isso a fronteira à esquerda não
chegaria. É a mesma distinção que o resto da campanha já fez — o modo de comparação é uma decisão
por palavra.

**Os 38 templates distribuídos não são afectados** — medido, 0 de 38. O relatório que originou este
teste dizia "17 de 38"; não se confirma, e o defeito continua a valer pelo caso alcançável.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_BASE = {
    "model": {"schema_version": "1.1.0"},
    "metadata": {"title": "Assistente de recomendacoes", "summary": "", "tags": []},
    "components": [{"id": "svc", "name": "Servico", "kind": "process"}],
}


def _ranking(summary: str):
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine.methodology_lenses.recommendation import compute_methodology_ranking

    document = copy.deepcopy(_BASE)
    document["metadata"]["summary"] = summary
    return compute_methodology_ranking(ThreatModelDocument.model_validate(document))


def _octave(ranking) -> float:
    return {getattr(k, "value", k): v for k, v in ranking.scores.items()}["octave_allegro"]


def test_o_documento_sem_o_termo_nao_pontua_octave() -> None:
    """Premissa: é contra esta linha de base que a outra é comparada."""
    ranking = _ranking("Servico de recomendacoes com modelo de linguagem.")

    assert ranking.winner.value == "stride"
    assert _octave(ranking) < 10


def test_a_palavra_bias_nao_pontua_como_analise_de_impacto() -> None:
    plain = _ranking("Servico de recomendacoes com modelo de linguagem.")
    biased = _ranking("Servico de recomendacoes; avaliamos bias do modelo periodicamente.")

    assert _octave(biased) == _octave(plain), (
        f"`bia` casou dentro de `bias`: octave {_octave(plain)} -> {_octave(biased)}"
    )
    assert biased.winner == plain.winner


@pytest.mark.parametrize(
    "summary",
    [
        "Fizemos a BIA deste sistema em janeiro.",
        "Business impact analysis concluida.",
        "Inventario de ativos mantido pela equipa.",
    ],
)
def test_o_contexto_de_bia_verdadeiro_continua_a_pontuar(summary: str) -> None:
    """A correcção não podia ser apagar o sinal: `bia` é mesmo um sinal de OCTAVE."""
    plain = _ranking("Servico de recomendacoes com modelo de linguagem.")

    assert _octave(_ranking(summary)) > _octave(plain)


def test_os_templates_distribuidos_nao_mudam() -> None:
    """A medição que corrige o relatório de origem: nenhum dos 38 depende deste match."""
    import yaml
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.ai_context import has_token
    from otm_industry_packs.loader import list_template_ids, load_template_yaml
    from otm_threat_engine.methodology_lenses.recommendation import (
        build_recommendation_context_text,
        compute_methodology_ranking,
    )

    affected = []
    for template_id in list_template_ids():
        document = ThreatModelDocument.model_validate(yaml.safe_load(load_template_yaml(template_id)))
        text = build_recommendation_context_text(document).lower()
        if "bia" in text and not has_token(text, "bia"):
            affected.append(template_id)
        compute_methodology_ranking(document)

    assert not affected, f"templates que dependiam do match por subcadeia: {affected}"
