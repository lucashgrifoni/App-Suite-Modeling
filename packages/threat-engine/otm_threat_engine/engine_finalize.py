from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology

from otm_explainability import ExplanationRecord

from otm_threat_engine.engine_support import recompute_summary_with_methodology
from otm_threat_engine.explanation_builders import merge_analysis_explanations
from otm_threat_engine.framework_refs import enrich_analysis_framework_refs
from otm_threat_engine.methodologies import apply_methodology_lens
from otm_threat_engine.result import AnalysisResult


def finalize_analysis_with_methodology(
    *,
    doc: ThreatModelDocument,
    base: AnalysisResult,
    methodology: ThreatModelMethodology,
    recommendation_reason: str | None,
    methodology_explanations: tuple[ExplanationRecord, ...] | None = None,
) -> AnalysisResult:
    final = apply_methodology_lens(doc, base, methodology=methodology).model_copy(
        update={
            "methodology": methodology,
            "methodology_recommendation_reason": recommendation_reason,
        }
    )
    final = enrich_analysis_framework_refs(final)
    final = recompute_summary_with_methodology(final)
    explanations = merge_analysis_explanations(
        doc,
        final,
        methodology_explanations=methodology_explanations,
        recommendation_reason=recommendation_reason,
    )
    return final.model_copy(update={"explanations": explanations})
