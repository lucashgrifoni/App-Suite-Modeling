"""Abstração simples para múltiplas metodologias de threat modeling."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.contracts import (
    MethodologyRecommendation,
)
from otm_threat_engine.methodology_lenses.service import apply_with_dispatch, recommend_with_rules
from otm_threat_engine.result import AnalysisResult


def recommend_methodology(doc: ThreatModelDocument) -> MethodologyRecommendation:
    return recommend_with_rules(doc)


def apply_methodology_lens(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
) -> AnalysisResult:
    return apply_with_dispatch(doc, result, methodology=methodology)
