"""Coverage — analysis_markdown business-cluster suppression helpers."""

from __future__ import annotations

import pytest
from otm_core_schema import StrideCategory
from otm_exporters import analysis_markdown as am
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def _t(tid: str, title: str, stride: StrideCategory = StrideCategory.TAMPERING) -> HeuristicThreat:
    return HeuristicThreat(id=tid, title=title, description="d", stride=stride, risk=build_risk_assessment(3, 3))


def test_is_business_specific() -> None:
    assert am._is_business_specific(_t("biz_x", "t")) is True
    assert am._is_business_specific(_t("stride_x", "economic_fraud here")) is True
    assert am._is_business_specific(_t("stride_y", "plain")) is False


def test_biz_family_flags() -> None:
    active = [_t("biz_webhook_1", "w"), _t("biz_coupon_2", "c"), _t("biz_balance_3", "b")]
    flags = am._biz_family_flags(active)
    assert flags["webhook"] and flags["coupon"] and flags["balance"]
    assert not flags["authorization"]


_CLUSTERS = [
    ("webhook", "webhook replay"),
    ("coupon", "coupon stacking"),
    ("payment_entitlement", "entitlement billing"),
    ("authorization", "authorization ownership"),
    ("balance", "balance ledger"),
    ("cancel", "cancel revog"),
]


@pytest.mark.parametrize("family,title", _CLUSTERS)
def test_cluster_suppressible_each_family(family: str, title: str) -> None:
    flags = {f: (f == family) for f in ("webhook", "coupon", "payment_entitlement", "authorization", "balance", "cancel")}
    h = _t("stride_generic", title, StrideCategory.TAMPERING)
    assert am._cluster_suppressible(h=h, flags=flags) is True


def test_cluster_not_suppressible_when_business_specific() -> None:
    flags = {f: True for f in ("webhook", "coupon", "payment_entitlement", "authorization", "balance", "cancel")}
    assert am._cluster_suppressible(h=_t("biz_webhook_1", "webhook"), flags=flags) is False


def test_cluster_not_suppressible_wrong_stride() -> None:
    flags = {"webhook": True}
    h = _t("stride_generic", "webhook", StrideCategory.INFORMATION_DISCLOSURE)
    assert am._cluster_suppressible(h=h, flags=flags) is False
