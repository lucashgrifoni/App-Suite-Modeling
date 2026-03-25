"""Contrato e presença mínima de explicabilidade nos motores."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_threat_engine import analyze_document, compare_threat_models, recommend_methodology
from otm_threat_engine.remediation import build_remediation_backlog

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_recommend_methodology_emits_structured_explanations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Sistema LGPD com dados pessoais")}
    )
    rec = recommend_methodology(doc)
    assert rec.explanations
    ex = rec.explanations[0]
    assert ex.type.value == "methodology_recommendation"
    assert ex.message
    assert ex.evidence


def test_analyze_includes_explanations_merge() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, auto_recommend=True)
    assert result.explanations
    types = {e.type.value for e in result.explanations}
    assert "methodology_recommendation" in types or "threat_heuristic" in types


def test_compare_threat_models_includes_explanations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    full = compare_threat_models(doc, doc)
    assert isinstance(full.explanations, list)


def test_backlog_items_carry_explanations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    backlog = build_remediation_backlog(result, doc)
    assert backlog.items
    assert backlog.items[0].explanations


def test_analysis_result_json_roundtrip_preserves_explanations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    raw = result.model_dump(mode="json")
    assert "explanations" in raw
    assert raw["explanations"]
