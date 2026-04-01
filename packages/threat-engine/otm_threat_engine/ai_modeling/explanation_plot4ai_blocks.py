"""Blocos de `ExplanationRecord` para PLOT4ai — extraídos para simplificar o merge."""

from __future__ import annotations

from collections.abc import Callable

from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.ai_modeling.signals import AiSignalBundle
from otm_threat_engine.methodology_lenses.common import has_any
from otm_threat_engine.result import AiSystemContextSummary

TakeId = Callable[[], int]


def evidence_lines(sig: AiSignalBundle, keys: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for k in keys:
        lines.extend(sig.evidence.get(k, [])[:2])
    return lines[:5]


def append_rag_block(
    out: list[ExplanationRecord],
    *,
    take_id: TakeId,
    sig: AiSignalBundle,
    ctx: AiSystemContextSummary,
    rel_doc: list[RelatedEntityRef],
) -> None:
    if not (sig.retrieval_grounding and sig.vector_embedding):
        return
    rag_ev = evidence_lines(sig, ("retrieval_grounding", "vector_embedding")) or ctx.pattern_tags[:5]
    out.append(
        ExplanationRecord(
            id=explanation_id(take_id(), prefix="exp_ai"),
            type=ExplanationType.AI_SPECIALIZED_RATIONALE,
            category=ExplanationCategory.AI_MODELING,
            subject="Padrão RAG + vector",
            message=(
                "RAG inferido por combinação de retrieval/grounding e vector store ou embeddings "
                "no modelo; validar contra o desenho real e políticas de isolamento."
            ),
            evidence=rag_ev,
            confidence="medium",
            related_entities=rel_doc,
        )
    )


def append_agent_block(
    out: list[ExplanationRecord],
    *,
    take_id: TakeId,
    sig: AiSignalBundle,
    ctx: AiSystemContextSummary,
    rel_doc: list[RelatedEntityRef],
) -> None:
    if not sig.agent_tool:
        return
    agent_ev = evidence_lines(sig, ("agent_tool",)) or [
        p for p in ctx.primary_risk_surfaces if "agent" in p.lower()
    ][:2]
    if not agent_ev:
        agent_ev = ["Agent/tools descritos no diagrama ou fluxos."]
    out.append(
        ExplanationRecord(
            id=explanation_id(take_id(), prefix="exp_ai"),
            type=ExplanationType.AI_SPECIALIZED_RATIONALE,
            category=ExplanationCategory.AI_MODELING,
            subject="Risco de execução (agente)",
            message=(
                "Agent/tool-use detectado por gateway de ferramentas, orquestrador ou fluxos de ação "
                "automatizada — reduzir superfície de ação e exigir confirmações quando o impacto é alto."
            ),
            evidence=agent_ev,
            confidence="medium",
            related_entities=rel_doc,
        )
    )


def append_provider_block(
    out: list[ExplanationRecord],
    *,
    take_id: TakeId,
    sig: AiSignalBundle,
    corpus: str,
    rel_doc: list[RelatedEntityRef],
) -> None:
    if not (
        sig.external_model_provider_linked
        or (sig.provider_inference and has_any(corpus, ("trust boundary", "third-party", "external", "provedor")))
    ):
        return
    prov_ev = evidence_lines(sig, ("provider_inference",)) or []
    out.append(
        ExplanationRecord(
            id=explanation_id(take_id(), prefix="exp_ai"),
            type=ExplanationType.AI_SPECIALIZED_RATIONALE,
            category=ExplanationCategory.AI_MODELING,
            subject="Dependência de fornecedor",
            message=(
                "External provider dependency detectada por componente de fornecedor de modelo e fluxos "
                "que cruzam fronteira até ao terceiro — rever DPA, dados no prompt e continuidade."
            ),
            evidence=prov_ev,
            confidence="medium",
            related_entities=rel_doc,
        )
    )


def append_sensitive_blocks(
    out: list[ExplanationRecord],
    *,
    take_id: TakeId,
    sig: AiSignalBundle,
    ctx: AiSystemContextSummary,
    corpus: str,
    rel_doc: list[RelatedEntityRef],
) -> None:
    hr_finance = has_any(
        corpus,
        (
            "hr-system",
            "finance-system",
            "payroll",
            "rh ",
            "human resources",
            "financial data",
            "prompt_with_sensitive_context",
            "hr finance",
        ),
    )
    if hr_finance and sig.prompt_input:
        out.append(
            ExplanationRecord(
                id=explanation_id(take_id(), prefix="exp_ai"),
                type=ExplanationType.AI_SPECIALIZED_RATIONALE,
                category=ExplanationCategory.AI_MODELING,
                subject="Contexto sensível (RH/Finanças)",
                message=(
                    "Sensitive AI context detectado por referências a RH/Finanças e envio de contexto "
                    "enriquecido ao provedor — reforçar minimização, segregação e controlos de acesso."
                ),
                evidence=ctx.sensitive_data_notes[:3] if ctx.sensitive_data_notes else [],
                confidence="medium",
                related_entities=rel_doc,
            )
        )
    elif sig.prompt_input and ctx.sensitive_data_notes:
        out.append(
            ExplanationRecord(
                id=explanation_id(take_id(), prefix="exp_ai"),
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


def append_governance_gap_block(
    out: list[ExplanationRecord],
    *,
    take_id: TakeId,
    sig: AiSignalBundle,
    rel_doc: list[RelatedEntityRef],
) -> None:
    if sig.explicit_governance_evidence or not (sig.model_interaction or sig.ml_pipeline_referenced):
        return
    out.append(
        ExplanationRecord(
            id=explanation_id(take_id(), prefix="exp_ai"),
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
