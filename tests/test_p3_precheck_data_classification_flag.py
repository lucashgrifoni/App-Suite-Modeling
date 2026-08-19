"""O check de classificação de dados não pode dar `passed` quando a classificação não existe.

`_check_data_classification` devolvia `passed=bool(doc.assets)` no ramo em que **nenhum** ativo
está classificado — isto é, passava por haver ativos, não por haver classificação — enquanto
emitia a mensagem *"Classificação de dados ausente ou só textual"*. O check reportava sucesso
para o estado exacto que existe para detectar.

Medido pela API, três documentos que diferem só na lista de ativos:

    sem ativos                 passed=False  score=6
    1 ativo NÃO classificado   passed=True   score=23   <- mensagem diz "ausente"
    1 ativo classificado       passed=True   score=32

O `passed` não entra no score (esse ramo já contribuía 0 pontos, e continua) — entra nas três
superfícies que listam ao utilizador os checks **falhados**: `analysis_markdown`, o relatório
premium e a UI (`DecisionCockpit`, `ModelQualityStrip`). O efeito era esconder a lacuna
precisamente no modelo onde ela é accionável: quem declarou ativos e não os classificou.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_UNCLASSIFIED = [{"id": "a1", "name": "PII database"}]
_CLASSIFIED = [{"id": "a1", "name": "PII database", "data_classification": "confidential"}]


def _precheck(assets: list[dict[str, Any]]) -> Any:
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.model_quality_precheck import assess_model_precheck

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "t"},
            "components": [{"id": "c1", "name": "svc", "kind": "process"}],
            "assets": assets,
        }
    )
    return assess_model_precheck(document)


def _classification_check(assets: list[dict[str, Any]]) -> Any:
    return next(c for c in _precheck(assets).checks if c.code == "data_classification")


@pytest.mark.parametrize("assets", [[], _UNCLASSIFIED], ids=["sem ativos", "ativo nao classificado"])
def test_sem_classificacao_o_check_falha(assets: list[dict[str, Any]]) -> None:
    check = _classification_check(assets)

    assert check.passed is False, (
        f"`passed={check.passed}` com a mensagem {check.message!r} — o check reporta sucesso "
        "para o estado que existe para detectar"
    )


def test_com_classificacao_o_check_passa() -> None:
    """A correcção não podia ser fazer o check falhar sempre."""
    check = _classification_check(_CLASSIFIED)

    assert check.passed is True
    assert "1 ativo" in check.message


def test_a_mensagem_e_o_veredito_concordam() -> None:
    """Invariante: quem diz `ausente` não pode dizer `passed`."""
    for assets in ([], _UNCLASSIFIED, _CLASSIFIED):
        check = _classification_check(assets)
        says_absent = "ausente" in check.message
        assert check.passed is not says_absent, f"{check.message!r} com passed={check.passed}"


def test_a_correccao_nao_mexe_no_score() -> None:
    """O ramo já contribuía 0 pontos; o `passed` é relatório, e tem de continuar a sê-lo."""
    assert _precheck(_UNCLASSIFIED).score_0_100 == 23
    assert _precheck([]).score_0_100 == 6
    assert _precheck(_CLASSIFIED).score_0_100 == 32


def test_a_lacuna_chega_ao_relatorio_de_quem_tem_ativos_por_classificar() -> None:
    """O ponto todo: sem isto a lacuna não aparece em lado nenhum ao utilizador."""
    from otm_core_schema import ThreatModelDocument
    from otm_exporters import export_analysis_markdown
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "t"},
            "components": [{"id": "c1", "name": "svc", "kind": "process"}],
            "assets": _UNCLASSIFIED,
        }
    )
    markdown = export_analysis_markdown(analyze_document(document))

    assert "Classificação de dados ausente" in markdown, (
        "a lacuna não aparece no relatório de um modelo que declara ativos sem classificação"
    )
