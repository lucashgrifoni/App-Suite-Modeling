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
        if sens in ("confidential", "restricted", "secret"):
            impact = min(5, impact + 1)
        elif sens == "internal":
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
    return likelihood, impact


def compute_risk_score(likelihood: int, impact: int) -> float:
    """Score simples: produto L×I (1–25)."""
    return float(likelihood * impact)


def build_risk_assessment(likelihood: int, impact: int) -> RiskAssessment:
    score = compute_risk_score(likelihood, impact)
    return RiskAssessment(likelihood=likelihood, impact=impact, score=score)
