from pathlib import Path

from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document, recommend_methodology
from otm_threat_engine.methodology_lenses.service import apply_with_dispatch, recommend_with_rules

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_recommend_with_rules_matches_public_contract() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="LLM app com RAG e agentes")}
    )
    rec = recommend_with_rules(doc)
    assert rec.methodology == ThreatModelMethodology.PLOT4AI


def test_service_and_public_recommendation_are_equivalent() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Advanced enterprise privacy risk-centric scenario")}
    )
    rec_public = recommend_methodology(doc)
    rec_service = recommend_with_rules(doc)
    assert rec_public.methodology == rec_service.methodology
    assert rec_public.reason == rec_service.reason


def test_apply_with_dispatch_preserves_selected_methodology_effect() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Contexto LGPD com PII")}
    )
    stride = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    linddun = apply_with_dispatch(doc, stride, methodology=ThreatModelMethodology.LINDDUN)
    assert any(h.id.startswith("linddun_") for h in linddun.heuristic_threats)
