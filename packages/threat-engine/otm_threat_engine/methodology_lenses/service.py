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
    build_recommendation_context_text,
    build_recommendation_rules,
)
from otm_threat_engine.result import AnalysisResult

_LENS_DISPATCH = build_lens_dispatch()


def recommend_with_rules(doc: ThreatModelDocument) -> MethodologyRecommendation:
    text = build_recommendation_context_text(doc)
    seq = 0
    for predicate, methodology, reason, evidence in build_recommendation_rules(doc, text):
        if predicate:
            seq += 1
            conf: str = "high" if methodology != ThreatModelMethodology.STRIDE else "medium"
            exp = ExplanationRecord(
                id=explanation_id(seq),
                type=ExplanationType.METHODOLOGY_RECOMMENDATION,
                category=ExplanationCategory.METHODOLOGY,
                subject=f"Metodologia {methodology.value}",
                message=reason,
                evidence=list(evidence),
                confidence=conf,  # type: ignore[arg-type]
                related_entities=[
                    RelatedEntityRef(entity_kind="document", entity_id=doc.metadata.title[:120]),
                ],
            )
            return MethodologyRecommendation(
                methodology=methodology,
                reason=reason,
                explanations=(exp,),
            )
    seq = 1
    fallback = (
        "Sem sinal forte para outra metodologia; STRIDE é o default do produto para sistemas técnicos."
    )
    exp = ExplanationRecord(
        id=explanation_id(seq),
        type=ExplanationType.METHODOLOGY_RECOMMENDATION,
        category=ExplanationCategory.METHODOLOGY,
        subject="Metodologia stride",
        message=fallback,
        evidence=[
            "Nenhuma regra de contexto (IA, privacidade avançada, OCTAVE, etc.) disparou antes do fallback.",
            f"Tipo de sistema declarado: {doc.model_info.system_type.value}.",
        ],
        confidence="medium",
        related_entities=[
            RelatedEntityRef(entity_kind="document", entity_id=doc.metadata.title[:120]),
        ],
    )
    return MethodologyRecommendation(
        methodology=ThreatModelMethodology.STRIDE,
        reason="Sem sinal forte para outra metodologia; STRIDE é o default do produto.",
        explanations=(exp,),
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
