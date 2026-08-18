"""STRIDE noise suppression — the two guards that keep it from over-reaching.

Suppression marks a generic `eng_*` finding as a duplicate when a specific `biz_*` finding
already covers the same root cause. Two guards bound it, and neither was exercised:

* a finding **already** marked duplicate must not be counted again, or the "covered" total in
  the summary reports more suppressions than actually happened;
* the `authorization` family matches on very generic words ("authorization", "ownership"),
  so it only suppresses findings that share a target with the business finding. Without that
  scope, any component merely *named* "ownership" lost its tampering and elevation-of-privilege
  findings — a real deletion of coverage, not a cosmetic one.
"""

from __future__ import annotations

import pytest
from otm_core_schema import Metadata, ModelInfo, RiskAssessment, ThreatModelDocument
from otm_core_schema.document import Component, DataFlow
from otm_core_schema.enums import ComponentKind, StrideCategory
from otm_threat_engine import analyze_document
from otm_threat_engine.engine import suppress_stride_genericity_noise
from otm_threat_engine.result import AnalysisResult, HeuristicThreat

_SUPPRESSIBLE = {StrideCategory.TAMPERING, StrideCategory.ELEVATION_OF_PRIVILEGE}


def _threat(tid: str, title: str, stride: StrideCategory, *, skipped: bool = False) -> HeuristicThreat:
    """Every threat here names the same component on purpose.

    Suppression is scoped to the target the `biz_*` finding points at, so a pair with no
    target is never suppressed and could not exercise the counting guard below.
    """
    return HeuristicThreat(
        id=tid,
        title=title,
        description="x",
        stride=stride,
        target_component_id="coupon_store",
        risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
        skipped_as_duplicate=skipped,
    )


@pytest.fixture
def suppression_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION", "1")


def test_a_finding_already_marked_duplicate_is_not_counted_twice(suppression_on: None) -> None:
    """The model already declared this threat, so generation marked it duplicate.

    Counting it again inflates `heuristic_threats_skipped_duplicate` in the summary.
    """
    already = _threat("eng_coupon_tampering", "Coupon tampering on checkout", StrideCategory.TAMPERING, skipped=True)
    heuristics = [_threat("biz_coupon_reuse", "Coupon reuse", StrideCategory.TAMPERING), already]

    assert suppress_stride_genericity_noise(heuristics) == 0
    assert already.skipped_as_duplicate is True


def test_an_equivalent_finding_not_yet_marked_is_counted_once(suppression_on: None) -> None:
    """Control for the test above: the only difference is the starting flag."""
    fresh = _threat("eng_coupon_tampering", "Coupon tampering on checkout", StrideCategory.TAMPERING)
    heuristics = [_threat("biz_coupon_reuse", "Coupon reuse", StrideCategory.TAMPERING), fresh]

    assert suppress_stride_genericity_noise(heuristics) == 1
    assert fresh.skipped_as_duplicate is True


def _ownership_document() -> ThreatModelDocument:
    """Two components whose names both contain "ownership"; only one is on the checkout flow.

    `biz_authorization_without_business_context` targets the component the sensitive flow
    reaches — here `ownership_service`. `ownership_audit` is a bystander with the same word in
    its id.
    """
    return ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="Ownership scoping"),
        components=[
            Component(id="user", name="User", kind=ComponentKind.USER),
            Component(id="ownership_service", name="Ownership service", kind=ComponentKind.PROCESS),
            Component(id="ownership_audit", name="Ownership audit", kind=ComponentKind.PROCESS),
        ],
        data_flows=[
            DataFlow(id="checkout_call", name="checkout", from_component="user", to_component="ownership_service"),
            DataFlow(id="audit_call", name="audit", from_component="user", to_component="ownership_audit"),
        ],
    )


def _suppressible_by_target(result: AnalysisResult, component_id: str) -> dict[str, bool]:
    return {
        h.id: h.skipped_as_duplicate
        for h in result.heuristic_threats
        if h.id.startswith("eng_") and h.stride in _SUPPRESSIBLE and h.target_component_id == component_id
    }


def test_authorization_suppression_applies_to_the_component_the_finding_points_at() -> None:
    result = analyze_document(_ownership_document())
    on_target = _suppressible_by_target(result, "ownership_service")

    assert on_target, "the model must produce suppressible findings for this to mean anything"
    assert all(on_target.values()), f"expected every finding suppressed, got {on_target}"


def test_authorization_suppression_spares_a_component_that_merely_shares_the_word() -> None:
    """The regression the target scoping exists to prevent."""
    result = analyze_document(_ownership_document())
    bystander = _suppressible_by_target(result, "ownership_audit")

    assert bystander, "the bystander must produce suppressible findings for this to mean anything"
    assert not any(bystander.values()), f"a bystander lost coverage: {bystander}"


def test_the_business_finding_itself_survives_suppression() -> None:
    result = analyze_document(_ownership_document())
    biz = [h for h in result.heuristic_threats if h.id.startswith("biz_authorization_")]

    assert len(biz) == 1
    assert biz[0].skipped_as_duplicate is False
