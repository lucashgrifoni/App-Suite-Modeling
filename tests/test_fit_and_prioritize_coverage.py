"""Coverage — methodology fit matrix branches + report prioritization helpers."""

from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelMethodology, create_blank_document
from otm_core_schema.methodology_fit_matrix import build_methodology_fit_matrix
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def _docs():
    blank = create_blank_document()
    no_assets = blank.model_copy(update={"assets": []})
    no_boundaries = blank.model_copy(update={"trust_boundaries": []})
    bare = blank.model_copy(update={"assets": [], "trust_boundaries": []})
    return [blank, no_assets, no_boundaries, bare]


def test_fit_matrix_all_docs_all_methodologies() -> None:
    vals = set()
    for doc in _docs():
        matrix = build_methodology_fit_matrix(doc)
        assert set(matrix) >= {m.value for m in ThreatModelMethodology}
        vals |= set(matrix.values())
    # exercises strong/partial/weak return branches across combos
    assert {"partial", "weak"} & vals


def test_prioritize_helpers() -> None:
    from otm_report_premium.prioritize import (
        _risk_score,
        assign_priority_tier,
        composite_priority_score,
    )

    t = HeuristicThreat(
        id="h",
        title="t",
        description="d",
        stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
        risk=build_risk_assessment(4, 4),
    )
    assert _risk_score(t) == 16.0
    assert composite_priority_score(t, None, ThreatModelMethodology.STRIDE) >= 0
    assert assign_priority_tier(0, 0) == "P3"  # total <= 0 guard
    assert assign_priority_tier(0, 9) == "P1"
    assert assign_priority_tier(8, 9) == "P3"


def test_risk_score_falls_back_to_likelihood_impact() -> None:
    from otm_report_premium.prioritize import _risk_score

    t = HeuristicThreat(
        id="h2", title="t", description="d", stride=StrideCategory.TAMPERING, risk=build_risk_assessment(3, 3)
    )
    # force score None to exercise the fallback path
    t2 = t.model_copy(update={"risk": t.risk.model_copy(update={"score": None})})
    assert _risk_score(t2) == float(t2.risk.likelihood * t2.risk.impact)
