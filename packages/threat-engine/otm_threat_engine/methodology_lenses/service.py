from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.methodology_lenses.contracts import MethodologyRecommendation
from otm_threat_engine.methodology_lenses.dispatch import build_lens_dispatch
from otm_threat_engine.methodology_lenses.recommendation import (
    _plot4ai_recommendation_detail,
    build_recommendation_context_text,
    compute_methodology_ranking,
)
from otm_threat_engine.result import AnalysisResult

_LENS_DISPATCH = build_lens_dispatch()


def recommend_with_rules(doc: ThreatModelDocument) -> MethodologyRecommendation:
    ranking = compute_methodology_ranking(doc)
    methodology = ranking.winner
    rec_conf = ranking.confidence
    if methodology == ThreatModelMethodology.STRIDE and ranking.score_gap < 4:
        rec_conf = "medium"
    detail_bits = [
        ranking.reason_summary,
        f"Confiança: {ranking.confidence} (gap {ranking.score_gap:.1f}).",
    ]
    if ranking.supporting_signals:
        detail_bits.append("Sinais positivos: " + "; ".join(ranking.supporting_signals[:6]) + ".")
    if ranking.counter_signals:
        detail_bits.append("Notas: " + "; ".join(ranking.counter_signals[:4]) + ".")
    reason = " ".join(detail_bits)
    if methodology == ThreatModelMethodology.PLOT4AI:
        ctx = build_recommendation_context_text(doc)
        plot = _plot4ai_recommendation_detail(doc, ctx)
        if plot is not None:
            reason = f"{plot[0]} {reason}"

    top_scores = sorted(ranking.scores.items(), key=lambda kv: -kv[1])[:6]
    scores_txt = ", ".join(f"{m.value}={s:.1f}" for m, s in top_scores)
    ev_body = [
        *ranking.supporting_signals,
        *[f"Concorrência: {c}" for c in ranking.counter_signals[:5]],
        f"Ranking de pontuações: {scores_txt}.",
    ]
    exp = ExplanationRecord(
        id=explanation_id(1),
        type=ExplanationType.METHODOLOGY_RECOMMENDATION,
        category=ExplanationCategory.METHODOLOGY,
        subject=f"Metodologia {methodology.value}",
        message=reason,
        evidence=[e for e in ev_body if e][:24],
        confidence=rec_conf,
        related_entities=[
            RelatedEntityRef(entity_kind="document", entity_id=(doc.metadata.title or "")[:120]),
        ],
    )
    score_dump = {k.value: round(v, 2) for k, v in ranking.scores.items()}
    ru = ranking.runner_up
    ru_score = ranking.scores[ru] if ru is not None else None
    return MethodologyRecommendation(
        methodology=methodology,
        reason=reason,
        explanations=(exp,),
        methodology_scores=score_dump,
        runner_up_methodology=ru,
        runner_up_score=round(ru_score, 2) if ru_score is not None else None,
        score_gap=ranking.score_gap,
        recommendation_confidence=rec_conf,
        top_supporting_signals=ranking.supporting_signals,
        counter_signals=ranking.counter_signals,
    )


def apply_with_dispatch(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
) -> AnalysisResult:
    handler = _LENS_DISPATCH.get(methodology)
    if handler is None:
        return result
    return handler(doc, result)
