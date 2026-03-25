"""
Explicabilidade curta específica de IA — anexada ao merge global da análise quando PLOT4ai.
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology

from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.ai_modeling.signals import collect_ai_signals_from_document
from otm_threat_engine.result import AnalysisResult


def append_plot4ai_merge_explanations(
    out: list[ExplanationRecord],
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> None:
    """Muta `out` com poucas frases acionáveis; ids sequenciais após o batch existente."""
    if result.methodology != ThreatModelMethodology.PLOT4AI or not result.ai_system_context:
        return
    ctx = result.ai_system_context
    sig = collect_ai_signals_from_document(doc)
    n = len(out)

    def take() -> int:
        nonlocal n
        n += 1
        return n

    rel_doc = [RelatedEntityRef(entity_kind="document", entity_id=(doc.metadata.title or "doc")[:120])]

    if sig.retrieval_grounding and sig.vector_embedding:
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_ai"),
                type=ExplanationType.AI_SPECIALIZED_RATIONALE,
                category=ExplanationCategory.AI_MODELING,
                subject="Padrão RAG + vector",
                message=(
                    "RAG inferido por presença de sinais de retrieval e de embeddings/vector store no texto do modelo; "
                    "validar com o desenho real."
                ),
                evidence=ctx.pattern_tags[:5],
                confidence="medium",
                related_entities=rel_doc,
            )
        )
    if sig.agent_tool:
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_ai"),
                type=ExplanationType.AI_SPECIALIZED_RATIONALE,
                category=ExplanationCategory.AI_MODELING,
                subject="Risco de execução (agente)",
                message=(
                    "Agent execution risk elevado quando há tool use ou orquestração automatizada — "
                    "reduzir superfície de acção e exigir confirmações onde o impacto é alto."
                ),
                evidence=[p for p in ctx.primary_risk_surfaces if "agent" in p.lower()][:2] or ["Agent/tools no modelo"],
                confidence="medium",
                related_entities=rel_doc,
            )
        )
    if sig.prompt_input and ctx.sensitive_data_notes:
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_ai"),
                type=ExplanationType.AI_SPECIALIZED_RATIONALE,
                category=ExplanationCategory.AI_MODELING,
                subject="Dados sensíveis no contexto",
                message=(
                    "Data leakage risk elevado quando prompts ou contexto podem incluir dados sensíveis sem controlos "
                    "explícitos de minimização e retenção."
                ),
                evidence=ctx.sensitive_data_notes[:3],
                confidence="low",
                related_entities=rel_doc,
            )
        )
    if not sig.explicit_governance_evidence and (sig.model_interaction or sig.ml_pipeline_referenced):
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_ai"),
                type=ExplanationType.AI_SPECIALIZED_RATIONALE,
                category=ExplanationCategory.AI_MODELING,
                subject="Governança / observabilidade",
                message=(
                    "Governance gap detectado por ausência de observabilidade/auditoria explícita no texto do modelo "
                    "apesar de fluxo de IA — planear trilhos mínimos (decision id, tool-call, versão de prompt)."
                ),
                evidence=[],
                confidence="low",
                related_entities=rel_doc,
            )
        )
