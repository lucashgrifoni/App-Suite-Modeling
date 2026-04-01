"""Regressão oficial: fixtures sintéticas de calibração PLOT4ai (otm-ai-001 … 005)."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_explainability import ExplanationType

from otm_threat_engine import analyze_document, recommend_methodology
from otm_threat_engine.methodology_lenses.common import has_any_token, has_safe_ai_marker
from otm_threat_engine.ai_modeling.signals import collect_ai_signals_from_document

_ROOT = Path(__file__).resolve().parents[1]
_FIX = _ROOT / "examples" / "plot4ai-calibration"
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_NON_AI_ECOMMERCE = _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml"
_NON_AI_HEALTH = _ROOT / "examples" / "test-apps" / "health-clinic.otm.yaml"


def _plot_ids(r):
    return {h.id for h in r.heuristic_threats if h.id.startswith("plot4ai_")}


@pytest.mark.parametrize(
    "filename",
    [
        "otm-ai-001-llm-chat.otm.yaml",
        "otm-ai-002-rag-enterprise.otm.yaml",
        "otm-ai-003-agent-tools.otm.yaml",
        "otm-ai-004-copilot-hr-finance.otm.yaml",
        "otm-ai-005-inference-pipeline.otm.yaml",
    ],
)
def test_calibration_fixture_loads_and_plot4ai_analysis_contract(filename: str) -> None:
    doc = load_document_from_yaml_path(_FIX / filename)
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    payload = r.model_dump(mode="json")
    assert payload.get("methodology") == "plot4ai"
    assert payload.get("ai_system_context") is not None
    assert payload["ai_system_context"].get("schema_version") == "1.0"
    assert isinstance(payload.get("explanations"), list)


def test_otm_ai_001_llm_chat_detection_and_recommendation() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-ai-001-llm-chat.otm.yaml")
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PLOT4AI
    assert "PLOT4ai recomendado por" in rec.reason
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    p = _plot_ids(r)
    assert "plot4ai_prompt_injection" in p
    assert "plot4ai_third_party_model_dependency" in p
    assert "plot4ai_rag_vector_composition" not in p
    assert r.ai_system_context is not None
    assert any(L.layer_id == "model_interaction" for L in r.ai_system_context.layers)


def test_otm_ai_002_rag_vector_and_governance_audit_present() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-ai-002-rag-enterprise.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    p = _plot_ids(r)
    assert "plot4ai_rag_vector_composition" in p
    assert "plot4ai_retrieval_grounding" in p
    assert "plot4ai_grounding_attribution_weak" in p
    assert "plot4ai_observability_gap" not in p


def test_otm_ai_003_agent_internal_tools_no_external_toolchain_heuristic() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-ai-003-agent-tools.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    p = _plot_ids(r)
    assert "plot4ai_agent_tool_execution" in p
    assert "plot4ai_agent_external_toolchain" not in p
    assert "plot4ai_observability_gap" not in p


def test_otm_ai_004_hr_finance_sensitive_context_and_explains() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-ai-004-copilot-hr-finance.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    p = _plot_ids(r)
    assert "plot4ai_sensitive_prompt_surface" in p
    ai_msgs = [e.message for e in r.explanations if e.type == ExplanationType.AI_SPECIALIZED_RATIONALE]
    assert any("RH/Finanças" in m or "rh/finanças" in m.lower() for m in ai_msgs)


def test_otm_ai_005_inference_pipeline_provider_and_json_contract() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-ai-005-inference-pipeline.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    p = _plot_ids(r)
    assert "plot4ai_third_party_model_dependency" in p
    assert "plot4ai_governance_pipeline" in p
    assert "plot4ai_observability_gap" not in p
    prov_msg = [e.message for e in r.explanations if e.type == ExplanationType.AI_SPECIALIZED_RATIONALE and "fornecedor" in e.message.lower()]
    assert prov_msg


def test_non_ai_fixtures_remain_without_plot4ai_heuristics() -> None:
    for path in (_NON_AI_ECOMMERCE, _NON_AI_HEALTH):
        doc = load_document_from_yaml_path(path)
        r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
        assert _plot_ids(r) == set()


def test_ambiguous_negative_workflow_fixture_no_plot4ai_heuristics() -> None:
    """Automação/pipeline sem IA — não deve disparar heurísticas plot4ai_* mesmo com metodologia forçada."""
    doc = load_document_from_yaml_path(_FIX / "otm-nai-001-rules-workflow.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    assert _plot_ids(r) == set()
    rec = recommend_methodology(doc)
    assert rec.methodology != ThreatModelMethodology.PLOT4AI


def test_quasi_ai_analytics_negative_fixture_no_plot4ai_heuristics() -> None:
    doc = load_document_from_yaml_path(_FIX / "otm-nai-002-analytics-automation.otm.yaml")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    assert _plot_ids(r) == set()
    rec = recommend_methodology(doc)
    assert rec.methodology != ThreatModelMethodology.PLOT4AI


def test_token_safe_matching_avoids_rag_substring_false_positive() -> None:
    text = "Operational outrage workflow and storage migration"
    assert has_any_token(text.lower(), ("rag",)) is False


def test_safe_ai_marker_requires_context_companion_terms() -> None:
    assert has_safe_ai_marker("programa ai interno genérico") is False
    assert has_safe_ai_marker("programa ai model inference interno") is True


def test_token_safe_ai_avoids_airflow_substring_noise() -> None:
    text = "airflow orchestration and data model pipeline"
    assert has_any_token(text.lower(), ("ai",)) is False


def test_keyword_signals_accepts_safe_ai_marker_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="AI governance context", summary="ai model inference controls")}
    )
    sig = collect_ai_signals_from_document(doc)
    assert sig.model_interaction is True
