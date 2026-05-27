"""Coverage — aggregate risk + decision cockpit posture branches (low/moderate/high/elevated)."""

from __future__ import annotations

from otm_core_schema import StrideCategory
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.risk_aggregate import build_aggregate_and_cockpit
from otm_threat_engine.risk_calc import build_risk_assessment


def _threat(tid: str, likelihood: int, impact: int, **extra) -> HeuristicThreat:
    return HeuristicThreat(
        id=tid,
        title=f"threat {tid}",
        description="d",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(likelihood, impact),
        **extra,
    )


def _result(threats: list[HeuristicThreat]) -> AnalysisResult:
    return AnalysisResult(engine_version="test", document_title="T", heuristic_threats=threats)


def _posture(result: AnalysisResult) -> str:
    out = build_aggregate_and_cockpit(result)
    return out["decision_cockpit"].risk_posture  # type: ignore[union-attr]


def test_posture_low_empty() -> None:
    assert _posture(_result([])) == "low"


def test_posture_low_small_score() -> None:
    assert _posture(_result([_threat("h_low", 1, 2)])) == "low"  # score 2 < 6


def test_posture_moderate() -> None:
    assert _posture(_result([_threat("h_mod", 2, 4)])) == "moderate"  # score 8 in [6,12)


def test_posture_high() -> None:
    assert _posture(_result([_threat("h_high", 3, 5)])) == "high"  # score 15 in [12,20)


def test_posture_elevated() -> None:
    assert _posture(_result([_threat("h_crit", 5, 5)])) == "elevated"  # score 25 >= 20


def test_aggregate_groups_by_targets_and_families() -> None:
    threats = [
        _threat("cmp_a", 3, 4, target_component_id="c1", finding_family="injection"),
        _threat("flow_b", 2, 3, target_data_flow_id="f1"),
        _threat("asset_c", 4, 4, target_asset_id="a1"),
        _threat("dup_d", 5, 5),
    ]
    threats[-1] = threats[-1].model_copy(update={"skipped_as_duplicate": True})
    out = build_aggregate_and_cockpit(_result(threats))
    agg = out["aggregate_risk"]
    assert agg.active_threat_count == 3  # duplicate excluded
    assert agg.top_components and agg.top_flows and agg.top_assets
