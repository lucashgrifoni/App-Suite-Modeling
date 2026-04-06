"""Síntese `AiSystemContextSummary` para saída PLOT4ai especializada."""

from __future__ import annotations

from typing import Literal

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.ai_modeling.signals import AiSignalBundle
from otm_threat_engine.methodology_lenses.common import looks_like_ai_context
from otm_threat_engine.result import AiLayerAssessment, AiSystemContextSummary, AnalysisResult

HeuristicLayerMap = dict[str, str]

PLOT4AI_HEURISTIC_LAYER: HeuristicLayerMap = {
    "plot4ai_prompt_injection": "prompt_input",
    "plot4ai_prompt_input_handling": "prompt_input",
    "plot4ai_sensitive_prompt_surface": "prompt_input",
    "plot4ai_rag_data_leakage": "retrieval_grounding",
    "plot4ai_retrieval_grounding": "retrieval_grounding",
    "plot4ai_rag_vector_composition": "vector_embedding",
    "plot4ai_model_abuse": "model_interaction",
    "plot4ai_third_party_model_dependency": "provider_inference",
    "plot4ai_agent_tool_execution": "agent_tool",
    "plot4ai_agent_external_toolchain": "agent_tool",
    "plot4ai_governance_pipeline": "governance_observability",
    "plot4ai_observability_gap": "governance_observability",
    "plot4ai_grounding_attribution_weak": "retrieval_grounding",
}


def _status(
    active: bool,
    *,
    explicit: bool = False,
) -> Literal["no_signal", "weak", "moderate", "strong"]:
    if not active:
        return "no_signal"
    return "strong" if explicit else "moderate"


def _group_heuristics(result: AnalysisResult) -> dict[str, list[str]]:
    by_layer: dict[str, list[str]] = {lid: [] for lid in set(PLOT4AI_HEURISTIC_LAYER.values())}
    for h in result.heuristic_threats:
        if not h.id.startswith("plot4ai_"):
            continue
        lid = PLOT4AI_HEURISTIC_LAYER.get(h.id)
        if lid:
            by_layer.setdefault(lid, []).append(h.id)
    return {k: sorted(v) for k, v in by_layer.items() if v}


def _pattern_tags(bundle: AiSignalBundle) -> list[str]:
    tags: list[str] = []
    if bundle.model_interaction:
        tags.append("llm_core")
    if bundle.retrieval_grounding:
        tags.append("rag")
    if bundle.vector_embedding:
        tags.append("vector_store")
    if bundle.agent_tool:
        tags.append("agent_tools")
    if bundle.provider_inference:
        tags.append("third_party_inference")
    if bundle.ml_pipeline_referenced:
        tags.append("ml_pipeline")
    if bundle.explicit_governance_evidence:
        tags.append("governance_controls")
    return tags


def _layer_list(bundle: AiSignalBundle) -> list[AiLayerAssessment]:
    return [
        AiLayerAssessment(
            layer_id="model_interaction",
            label="Model interaction",
            status=_status(bundle.model_interaction),
            evidence=bundle.evidence.get("model_interaction", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="prompt_input",
            label="Prompt / input handling",
            status=_status(bundle.prompt_input),
            evidence=bundle.evidence.get("prompt_input", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="retrieval_grounding",
            label="Retrieval / grounding",
            status=_status(bundle.retrieval_grounding),
            evidence=bundle.evidence.get("retrieval_grounding", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="vector_embedding",
            label="Vector / embedding",
            status=_status(bundle.vector_embedding),
            evidence=bundle.evidence.get("vector_embedding", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="agent_tool",
            label="Agent / tool execution",
            status=_status(bundle.agent_tool),
            evidence=bundle.evidence.get("agent_tool", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="provider_inference",
            label="Provider / inference integration",
            status=_status(bundle.provider_inference),
            evidence=bundle.evidence.get("provider_inference", [])[:4],
        ),
        AiLayerAssessment(
            layer_id="governance_observability",
            label="Governance / audit / observability",
            status=_status(
                bundle.explicit_governance_evidence or bundle.ml_pipeline_referenced,
                explicit=bundle.explicit_governance_evidence,
            ),
            evidence=bundle.evidence.get("governance_observability", [])[:4],
        ),
    ]


def _primary_surfaces(
    doc: ThreatModelDocument,
    bundle: AiSignalBundle,
    grouped: dict[str, list[str]],
) -> list[str]:
    surfaces: list[str] = []
    if bundle.agent_tool:
        surfaces.append("Execução automatizada (agentes / tools) e superfície de acção")
    if bundle.retrieval_grounding or bundle.vector_embedding:
        surfaces.append("Recuperação de contexto e armazéns vectoriais (RAG / embeddings)")
    if bundle.prompt_input:
        surfaces.append("Ingestão de pedidos e gestão do contexto de prompt")
    if bundle.provider_inference:
        surfaces.append("Dependência de APIs ou modelos alojados externamente")
    if grouped.get("governance_observability"):
        surfaces.append("Trilha e governança do ciclo de vida da IA")
    if not surfaces and looks_like_ai_context(doc):
        surfaces.append("Interação genérica com modelo — reforçar desenho com base em dados reais")
    return surfaces[:6]


def _recommendations(bundle: AiSignalBundle) -> list[str]:
    recs: list[str] = []
    if bundle.agent_tool:
        recs.append("Políticas estritas de tool-use: allow-list, confirmação humana e sandbox por ferramenta.")
    if bundle.retrieval_grounding and bundle.vector_embedding:
        recs.append("Isolar índices/coleções por tenant e registar origem dos chunks recuperados.")
    if bundle.prompt_input:
        recs.append("Camada de validação e normalização de input; limites de contexto e políticas de dados.")
    if bundle.provider_inference:
        recs.append("Contratos e classificação de dados com o fornecedor; plano de continuidade e limites de uso.")
    if not bundle.explicit_governance_evidence and (bundle.model_interaction or bundle.ml_pipeline_referenced):
        recs.append(
            "Observabilidade mínima: logging seguro de prompts/respostas resumidas, IDs de sessão e tool-calls."
        )
    return recs[:8]


def _sensitive_notes(doc: ThreatModelDocument, bundle: AiSignalBundle) -> list[str]:
    notes: list[str] = []
    for a in doc.assets:
        sens = (getattr(a, "sensitivity", None) or "").lower()
        if sens and sens != "public":
            notes.append(f"Ativo `{a.name}` marcado como sensível — rever fluxo para contexto LLM.")
    if bundle.prompt_input and notes:
        notes.append("Dados sensíveis podem concentrar-se no contexto de prompt se não houver minimização.")
    return notes[:5]


def build_ai_system_context_summary(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    bundle: AiSignalBundle,
) -> AiSystemContextSummary:
    grouped = _group_heuristics(result)
    tags = _pattern_tags(bundle)
    synopsis_parts = [
        "Análise PLOT4ai com deteção heurística (não exaustiva) de componentes típicos de sistemas com IA.",
    ]
    if tags:
        synopsis_parts.append(f"Padrões prováveis: {', '.join(tags)}.")
    else:
        synopsis_parts.append("Sem sinais fortes no texto do modelo — validar com arquitetura real e artefactos.")
    synopsis = " ".join(synopsis_parts)

    return AiSystemContextSummary(
        synopsis=synopsis,
        pattern_tags=tags,
        layers=_layer_list(bundle),
        primary_risk_surfaces=_primary_surfaces(doc, bundle, grouped),
        prioritized_recommendations=_recommendations(bundle),
        sensitive_data_notes=_sensitive_notes(doc, bundle),
        heuristic_ids_by_layer=grouped,
    )
