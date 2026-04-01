from __future__ import annotations

from otm_core_schema import RiskAssessment, StrideCategory, ThreatModelDocument

from otm_threat_engine.business_abuse_context import (
    build_business_abuse_context,
)
from otm_threat_engine.business_abuse_rules.authz import add_business_context_authz
from otm_threat_engine.business_abuse_rules.coupon import add_coupon_abuse
from otm_threat_engine.business_abuse_rules.entitlement import add_entitlement_billing_mismatch
from otm_threat_engine.business_abuse_rules.financial import add_financial_sequence_abuse
from otm_threat_engine.business_abuse_rules.webhook import add_webhook_abuse
from otm_threat_engine.result import HeuristicThreat


def append_business_abuse_heuristics(
    *,
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
) -> int:
    """Adiciona heuristicas de abuso de logica de negocio sem alterar contrato do motor."""
    existing_ids = {h.id for h in heuristics}
    context = build_business_abuse_context(doc)

    def add(
        *,
        hid: str,
        title: str,
        description: str,
        stride: StrideCategory,
        likelihood: int,
        impact: int,
        target_component_id: str | None = None,
        target_data_flow_id: str | None = None,
        target_asset_id: str | None = None,
    ) -> None:
        _append(
            heuristics,
            existing_ids,
            hid=hid,
            title=title,
            description=description,
            stride=stride,
            likelihood=likelihood,
            impact=impact,
            target_component_id=target_component_id,
            target_data_flow_id=target_data_flow_id,
            target_asset_id=target_asset_id,
        )

    before = len(existing_ids)
    add_webhook_abuse(context, add)
    add_entitlement_billing_mismatch(context, add)
    add_coupon_abuse(context, add)
    add_financial_sequence_abuse(context, add)
    add_business_context_authz(context, add)
    return len(existing_ids) - before


def _append(
    heuristics: list[HeuristicThreat],
    existing_ids: set[str],
    *,
    hid: str,
    title: str,
    description: str,
    stride: StrideCategory,
    likelihood: int,
    impact: int,
    target_component_id: str | None,
    target_data_flow_id: str | None,
    target_asset_id: str | None,
) -> None:
    if hid in existing_ids:
        return
    heuristics.append(
        HeuristicThreat(
            id=hid,
            title=title,
            description=description,
            stride=stride,
            target_component_id=target_component_id,
            target_data_flow_id=target_data_flow_id,
            target_asset_id=target_asset_id,
            risk=RiskAssessment(
                likelihood=likelihood,
                impact=impact,
                score=float(likelihood * impact),
            ),
            skipped_as_duplicate=False,
        )
    )
    existing_ids.add(hid)
