"""A linha PLOT4ai da matriz de adequação tem de ser alcançável.

Antes, `_fit_plot4ai` só olhava para `import_signals_corpus` — um campo que o import de
artefactos preenche e que um modelo escrito à mão nunca tem — e não tinha ramo "strong". O
resultado: os seis templates que declaram `methodology: plot4ai` diziam ao utilizador
`fit: weak` / `score: minimal` enquanto a lente PLOT4ai gerava 6 a 9 ameaças bem dirigidas
sobre o mesmo documento. O sinal de qualidade contradizia o motor e não havia alvo nenhum
para o modelador melhorar.
"""

from __future__ import annotations

from pathlib import Path

import otm_industry_packs
from otm_core_schema import (
    ThreatModelMethodology,
    assess_model_precheck,
    build_methodology_fit_matrix,
    load_document_from_yaml_path,
)
from otm_core_schema.enums import MethodologyCompletenessState
from otm_threat_engine.methodology_completeness import assess_methodology_completeness

_ROOT = Path(__file__).resolve().parents[1]
_CALIBRATION = _ROOT / "examples" / "plot4ai-calibration"
_TEMPLATES = Path(otm_industry_packs.__file__).resolve().parent / "data" / "templates"


def test_ai_calibration_fixture_reaches_strong() -> None:
    doc = load_document_from_yaml_path(_CALIBRATION / "otm-ai-002-rag-enterprise.otm.yaml")
    assert build_methodology_fit_matrix(doc)["plot4ai"] == "strong"
    assert assess_model_precheck(doc).recommendation_confidence != "low"


def test_every_ai_calibration_fixture_is_at_least_partial() -> None:
    for p in sorted(_CALIBRATION.glob("otm-ai-*.otm.yaml")):
        doc = load_document_from_yaml_path(p)
        assert build_methodology_fit_matrix(doc)["plot4ai"] != "weak", p.name


def test_non_ai_calibration_fixtures_stay_weak() -> None:
    """O ramo novo não pode transformar qualquer documento num sistema de IA."""
    for p in sorted(_CALIBRATION.glob("otm-nai-*.otm.yaml")):
        doc = load_document_from_yaml_path(p)
        assert build_methodology_fit_matrix(doc)["plot4ai"] == "weak", p.name


def test_templates_declaring_plot4ai_do_not_self_report_weak() -> None:
    checked = 0
    for p in sorted(_TEMPLATES.glob("*.otm.yaml")):
        doc = load_document_from_yaml_path(p)
        if doc.model_info.methodology != ThreatModelMethodology.PLOT4AI:
            continue
        checked += 1
        assert build_methodology_fit_matrix(doc)["plot4ai"] == "strong", p.name
    assert checked == 6


def test_completeness_follows_the_same_ai_signal() -> None:
    ai = load_document_from_yaml_path(_CALIBRATION / "otm-ai-002-rag-enterprise.otm.yaml")
    non_ai = load_document_from_yaml_path(_CALIBRATION / "otm-nai-001-rules-workflow.otm.yaml")
    assert (
        assess_methodology_completeness(ai, ThreatModelMethodology.PLOT4AI).state
        == MethodologyCompletenessState.COMPLETE
    )
    assert (
        assess_methodology_completeness(non_ai, ThreatModelMethodology.PLOT4AI).state
        == MethodologyCompletenessState.PARTIAL
    )
