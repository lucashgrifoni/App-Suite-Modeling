from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_explainability import ExplanationRecord

from otm_threat_engine.methodologies import recommend_methodology


def resolve_methodology_selection(
    doc: ThreatModelDocument,
    *,
    methodology: ThreatModelMethodology | str | None,
    auto_recommend: bool,
) -> tuple[ThreatModelMethodology, str | None, tuple[ExplanationRecord, ...]]:
    chosen = (
        ThreatModelMethodology(methodology)
        if methodology is not None
        else (doc.model_info.methodology or ThreatModelMethodology.STRIDE)
    )
    rec_reason: str | None = None
    methodology_explanations: tuple[ExplanationRecord, ...] = ()
    if auto_recommend and methodology is None:
        rec = recommend_methodology(doc)
        chosen = rec.methodology
        rec_reason = rec.reason
        methodology_explanations = rec.explanations
    return chosen, rec_reason, methodology_explanations
