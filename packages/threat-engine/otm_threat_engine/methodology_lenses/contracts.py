from __future__ import annotations

from typing import Literal, Protocol

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, ConfigDict, Field

from otm_threat_engine.result import AnalysisResult


class MethodologyRecommendation(BaseModel):
    """
    Recomendação de metodologia com explicabilidade estruturada.

    `reason` mantém um resumo único (compatível com API/UI existentes).
    """

    model_config = ConfigDict(frozen=True)

    methodology: ThreatModelMethodology
    reason: str
    explanations: tuple[ExplanationRecord, ...] = ()
    methodology_scores: dict[str, float] | None = Field(
        default=None,
        description="Pontuação por metodologia (valor enum → score).",
    )
    runner_up_methodology: ThreatModelMethodology | None = None
    runner_up_score: float | None = None
    score_gap: float | None = None
    recommendation_confidence: Literal["low", "medium", "high"] | None = None
    top_supporting_signals: tuple[str, ...] = Field(default_factory=tuple)
    counter_signals: tuple[str, ...] = Field(default_factory=tuple)


class ThreatModelingEngine(Protocol):
    methodology: ThreatModelMethodology

    def analyze(self, doc: ThreatModelDocument, *, pack=None) -> AnalysisResult: ...
