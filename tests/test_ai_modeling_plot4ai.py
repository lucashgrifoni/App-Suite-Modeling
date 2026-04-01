"""Cenários AI/LLM e contrato PLOT4ai (camadas, heurísticas, explicabilidade)."""

from __future__ import annotations

from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_FINANCE = _ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml"
_E_COMMERCE = _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml"
_HEALTH = _ROOT / "examples" / "test-apps" / "health-clinic.otm.yaml"


def test_plot4ai_llm_simple_has_model_layer() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Chat LLM interno", summary="API de completion e prompts")}
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    assert r.ai_system_context is not None
    assert "llm_core" in r.ai_system_context.pattern_tags or any(
        L.layer_id == "model_interaction" and L.status != "no_signal" for L in r.ai_system_context.layers
    )


def test_plot4ai_rag_vector_heuristics_and_grouping() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Assistente RAG",
                summary="retrieval com pinecone embeddings vector store",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats}
    assert "plot4ai_rag_vector_composition" in ids
    assert r.ai_system_context is not None
    assert "rag" in r.ai_system_context.pattern_tags
    assert "vector_store" in r.ai_system_context.pattern_tags
    assert r.ai_system_context.heuristic_ids_by_layer.get("vector_embedding")


def test_plot4ai_agent_tool_scenario() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Agente com ferramentas",
                summary="OpenAI function calling e webhook HTTP externo",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats}
    assert "plot4ai_agent_tool_execution" in ids
    assert "plot4ai_agent_external_toolchain" in ids
    assert r.ai_system_context is not None
    assert "agent_tools" in r.ai_system_context.pattern_tags


def test_plot4ai_contract_json_includes_ai_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="LLM API", summary="rag retrieval")}
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    payload = r.model_dump(mode="json")
    assert "ai_system_context" in payload
    assert payload["ai_system_context"] is not None
    assert payload["ai_system_context"]["schema_version"] == "1.0"


def test_plot4ai_markdown_contains_ai_section() -> None:
    from otm_exporters.analysis_markdown import export_analysis_markdown

    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Produto LLM", summary="vertex ai inference pipeline")}
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    md = export_analysis_markdown(r)
    assert "PLOT4ai" in md
    assert "contexto IA" in md.lower() or "IA" in md


def test_plot4ai_avoids_sensitive_prompt_risk_when_controls_are_declared() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="LLM support assistant",
                summary=(
                    "prompt com dados pessoais; redaction e tokenization aplicados antes do envio "
                    "ao modelo com data minimization policy"
                ),
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats}
    assert "plot4ai_sensitive_prompt_surface" not in ids


def test_plot4ai_finance_non_ai_example_keeps_low_specialization_noise() -> None:
    doc = load_document_from_yaml_path(_FINANCE)
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats if h.id.startswith("plot4ai_")}
    # contrato: não forçar ruído de IA quando o exemplo não descreve camada AI/LLM
    assert "plot4ai_agent_external_toolchain" not in ids
    assert "plot4ai_rag_vector_composition" not in ids


def test_plot4ai_ecommerce_fixture_has_no_plot4ai_heuristics() -> None:
    doc = load_document_from_yaml_path(_E_COMMERCE)
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats if h.id.startswith("plot4ai_")}
    assert ids == set()


def test_plot4ai_health_fixture_has_no_plot4ai_heuristics() -> None:
    doc = load_document_from_yaml_path(_HEALTH)
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats if h.id.startswith("plot4ai_")}
    assert ids == set()
