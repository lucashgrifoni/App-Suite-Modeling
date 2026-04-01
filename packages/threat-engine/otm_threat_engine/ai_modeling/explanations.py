"""
Explicabilidade curta específica de IA — anexada ao merge global da análise quando PLOT4ai.
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_explainability import ExplanationRecord, RelatedEntityRef

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.ai_modeling.explanation_plot4ai_blocks import (
    append_agent_block,
    append_governance_gap_block,
    append_provider_block,
    append_rag_block,
    append_sensitive_blocks,
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
    corpus = build_ai_calibration_corpus(doc)
    n = len(out)

    def take() -> int:
        nonlocal n
        n += 1
        return n

    rel_doc = [RelatedEntityRef(entity_kind="document", entity_id=(doc.metadata.title or "doc")[:120])]

    append_rag_block(out, take_id=take, sig=sig, ctx=ctx, rel_doc=rel_doc)
    append_agent_block(out, take_id=take, sig=sig, ctx=ctx, rel_doc=rel_doc)
    append_provider_block(out, take_id=take, sig=sig, corpus=corpus, rel_doc=rel_doc)
    append_sensitive_blocks(out, take_id=take, sig=sig, ctx=ctx, corpus=corpus, rel_doc=rel_doc)
    append_governance_gap_block(out, take_id=take, sig=sig, rel_doc=rel_doc)
