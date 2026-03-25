from __future__ import annotations

from typing import Protocol

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, ConfigDict

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


class ThreatModelingEngine(Protocol):
    methodology: ThreatModelMethodology

    def analyze(self, doc: ThreatModelDocument, *, pack=None) -> AnalysisResult: ...
