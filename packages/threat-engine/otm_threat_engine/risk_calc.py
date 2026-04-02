"""Cálculo simples de risco (sem matriz de negócio pesada no MVP)."""

from __future__ import annotations

from otm_core_schema import (
    Asset,
    Component,
    ComponentKind,
    DataFlow,
    RiskAssessment,
    StrideCategory,
)
from otm_core_schema.enums import CriticalityLevel, FlowSemanticClass


def likelihood_impact_for_component(
    component: Component,
    stride: StrideCategory,
    *,
    assets_by_id: dict[str, Asset],
) -> tuple[int, int]:
    """
    Likelihood e impacto discretos (1–5).
    Heurística: componentes expostos (gateway, external) aumentam probabilidade;
    ativos sensíveis ligados aumentam impacto.
    """
    likelihood = 3
    impact = 3

    if component.kind in (ComponentKind.GATEWAY, ComponentKind.EXTERNAL_ENTITY):
        likelihood = min(5, likelihood + 1)
    if component.kind == ComponentKind.DATASTORE:
        impact = min(5, impact + 1)

    if stride in (StrideCategory.ELEVATION_OF_PRIVILEGE, StrideCategory.SPOOFING):
        likelihood = min(5, likelihood + 1)

    for aid in component.asset_ids:
        asset = assets_by_id.get(aid)
        if asset is None:
            continue
        sens = (asset.sensitivity or "").lower()
        if sens in ("confidential", "restricted", "secret", "internal"):
            impact = min(5, impact + 1)
        if asset.business_criticality in (CriticalityLevel.HIGH, CriticalityLevel.CRITICAL):
            impact = min(5, impact + 1)
        if asset.data_classification is not None and asset.data_classification.value in (
            "confidential",
            "restricted",
        ):
            impact = min(5, impact + 1)

    if component.supports_admin_operations or (component.privilege_level or "").lower() in (
        "admin",
        "high",
    ):
        likelihood = min(5, likelihood + 1)
        impact = min(5, impact + 1)

    return likelihood, impact


def likelihood_impact_for_data_flow(
    flow: DataFlow,
    *,
    crosses_boundary: bool,
) -> tuple[int, int]:
    likelihood = 3
    impact = 3
    if crosses_boundary:
        likelihood = min(5, likelihood + 1)
        impact = min(5, impact + 1)
    if flow.encrypted is False:
        likelihood = min(5, likelihood + 1)
        impact = min(5, impact + 1)
    elif flow.encrypted is None:
        likelihood = min(5, likelihood + 1)
    if flow.authenticated is False:
        likelihood = min(5, likelihood + 1)
    if flow.public_exposure:
        likelihood = min(5, likelihood + 1)
    if flow.affects_privileged_state:
        impact = min(5, impact + 1)
    if flow.semantic_class in (
        FlowSemanticClass.AUTHENTICATION_FLOW,
        FlowSemanticClass.PAYMENT_FLOW,
        FlowSemanticClass.PRIVILEGED_OPERATION,
    ):
        impact = min(5, impact + 1)
    if flow.stores_sensitive_data:
        impact = min(5, impact + 1)
    return likelihood, impact


def compute_risk_score(likelihood: int, impact: int) -> float:
    """Score simples: produto L×I (1–25)."""
    return float(likelihood * impact)


def build_risk_assessment(likelihood: int, impact: int) -> RiskAssessment:
    score = compute_risk_score(likelihood, impact)
    return RiskAssessment(likelihood=likelihood, impact=impact, score=score)
