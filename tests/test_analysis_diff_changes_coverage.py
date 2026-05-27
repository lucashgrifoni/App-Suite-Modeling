"""Coverage — _analysis_has_changes / _analysis_insights isolated change detectors."""

from __future__ import annotations

from otm_threat_engine.analysis_diff import AnalysisDiff
from otm_threat_engine.comparison_models import (
    FrameworkRefCountDelta,
    HeuristicThreatDelta,
    HeuristicThreatDeltaSection,
    MethodologyInsightsDelta,
    PackHintsDelta,
    StructuralFindingDelta,
    TrustBoundaryFindingDelta,
)
from otm_threat_engine.threat_model_comparison import _analysis_has_changes


def _base(**kw) -> AnalysisDiff:
    d = {"methodology_before": "stride", "methodology_after": "stride", "methodology_changed": False}
    d.update(kw)
    return AnalysisDiff(**d)


def test_no_changes() -> None:
    assert _analysis_has_changes(_base()) is False


def test_methodology_changed() -> None:
    assert _analysis_has_changes(_base(methodology_changed=True)) is True


def test_signature_remap() -> None:
    assert _analysis_has_changes(_base(signature_remap_hints=["a->b"])) is True


def test_heuristic_threats_delta() -> None:
    delta = HeuristicThreatDelta(threat_id="t1", change="added")
    assert _analysis_has_changes(_base(heuristic_threats=HeuristicThreatDeltaSection(added=[delta]))) is True


def test_framework_ref_counts() -> None:
    fr = FrameworkRefCountDelta(catalog="nist", count_before=1, count_after=2)
    assert _analysis_has_changes(_base(framework_ref_counts=[fr])) is True


def test_pack_hints() -> None:
    assert _analysis_has_changes(_base(pack_control_hints=PackHintsDelta(added=["control"]))) is True


def test_methodology_insights() -> None:
    mi = MethodologyInsightsDelta(blocks_added=["b1"])
    assert _analysis_has_changes(_base(methodology_insights=mi)) is True


def test_trust_boundary_findings() -> None:
    tb = TrustBoundaryFindingDelta(added_keys=["k1"])
    assert _analysis_has_changes(_base(trust_boundary_findings=tb)) is True


def test_structural_findings() -> None:
    sf = StructuralFindingDelta(codes_added=["S001"])
    assert _analysis_has_changes(_base(structural_findings=sf)) is True


def test_max_risk_delta() -> None:
    assert _analysis_has_changes(_base(max_risk_delta=5.0)) is True
