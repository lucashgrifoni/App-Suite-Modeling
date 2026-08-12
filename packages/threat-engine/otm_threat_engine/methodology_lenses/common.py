from __future__ import annotations

from otm_core_schema import RiskAssessment, StrideCategory, ThreatModelMethodology

# Os helpers lexicais e o gate de contexto IA vivem em core-schema porque a matriz de
# adequação metodologia × contexto (lá) precisa da mesma resposta que a lente PLOT4ai (aqui).
# Reexportados com os nomes históricos: o motor e os testes importam-nos deste módulo.
from otm_core_schema.ai_context import (
    build_ai_calibration_corpus,
    has_any,
    has_any_token,
    has_safe_ai_marker,
    has_token,
    looks_like_ai_context,
)

from otm_threat_engine.result import (
    AnalysisResult,
    HeuristicThreat,
    MethodologyInsightBlock,
    MethodologyInsights,
    StructuralFinding,
)

__all__ = [
    "append_engine_lens_note",
    "append_heuristics_from_entries",
    "append_methodology_insights",
    "boost_impact",
    "build_ai_calibration_corpus",
    "has_any",
    "has_any_token",
    "has_safe_ai_marker",
    "has_token",
    "looks_like_ai_context",
]


def append_engine_lens_note(
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
    note: str,
) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code=f"ENGINE_LENS_{methodology.value.upper()}",
            severity="info",
            message=note,
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def append_methodology_insights(
    result: AnalysisResult,
    *,
    profile: str,
    blocks: list[tuple[str, str, list[str]]],
) -> AnalysisResult:
    insight_blocks = [MethodologyInsightBlock(key=key, title=title, items=items) for key, title, items in blocks]
    insights = MethodologyInsights(profile=profile, blocks=insight_blocks)
    return result.model_copy(update={"methodology_insights": insights})


def boost_impact(result: AnalysisResult, predicate) -> AnalysisResult:
    boosted = []
    for h in result.heuristic_threats:
        if predicate(h):
            new_impact = min(5, h.risk.impact + 1)
            risk = h.risk.model_copy(
                update={
                    "impact": new_impact,
                    "score": float(h.risk.likelihood * new_impact),
                }
            )
            boosted.append(h.model_copy(update={"risk": risk}))
        else:
            boosted.append(h)
    return result.model_copy(update={"heuristic_threats": boosted})


def append_heuristics_from_entries(
    out: list[HeuristicThreat],
    existing: set[str],
    entries: list[tuple[str, str, str, StrideCategory, int, int]],
    *,
    target_component_id: str | None = None,
    target_data_flow_id: str | None = None,
) -> None:
    for hid, title, desc, stride, likelihood, impact in entries:
        if hid in existing:
            continue  # pragma: no cover - defensive guard
        out.append(
            HeuristicThreat(
                id=hid,
                title=title,
                description=desc,
                stride=stride,
                target_component_id=target_component_id,
                target_data_flow_id=target_data_flow_id,
                risk=RiskAssessment(
                    likelihood=likelihood,
                    impact=impact,
                    score=float(likelihood * impact),
                ),
                skipped_as_duplicate=False,
            )
        )
        existing.add(hid)
