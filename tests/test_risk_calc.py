"""Contratos do cálculo heurístico L×I."""

from otm_core_schema import Asset, Component, DataFlow
from otm_core_schema.enums import AssetKind, ComponentKind, StrideCategory
from otm_threat_engine.risk_calc import (
    build_risk_assessment,
    compute_risk_score,
    likelihood_impact_for_component,
    likelihood_impact_for_data_flow,
)


def test_compute_risk_score_is_product() -> None:
    assert abs(compute_risk_score(4, 5) - 20.0) < 1e-9


def test_build_risk_assessment_sets_score() -> None:
    r = build_risk_assessment(2, 3)
    assert r.likelihood == 2
    assert r.impact == 3
    assert abs(r.score - 6.0) < 1e-9


def test_likelihood_impact_for_data_flow_crosses_boundary_raises_both() -> None:
    flow = DataFlow(
        id="f",
        from_component="a",
        to_component="b",
        encrypted=True,
        authenticated=True,
    )
    l1, i1 = likelihood_impact_for_data_flow(flow, crosses_boundary=False)
    l2, i2 = likelihood_impact_for_data_flow(flow, crosses_boundary=True)
    assert l2 >= l1
    assert i2 >= i1


def test_likelihood_impact_for_component_sensitivity_raises_impact() -> None:
    comp = Component(
        id="api",
        name="API",
        kind=ComponentKind.PROCESS,
        asset_ids=["pii"],
    )
    assets = {
        "pii": Asset(
            id="pii",
            name="PII",
            asset_kind=AssetKind.DATA,
            sensitivity="confidential",
        )
    }
    l_base, i_base = likelihood_impact_for_component(
        comp.model_copy(update={"asset_ids": []}), StrideCategory.TAMPERING, assets_by_id=assets
    )
    l2, i2 = likelihood_impact_for_component(comp, StrideCategory.TAMPERING, assets_by_id=assets)
    assert l2 == l_base
    assert i2 >= i_base
