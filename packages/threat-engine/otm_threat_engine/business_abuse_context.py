from __future__ import annotations

from dataclasses import dataclass

from otm_core_schema import ThreatModelDocument


@dataclass
class BusinessAbuseContext:
    has_payment: bool
    has_webhook: bool
    has_entitlement: bool
    has_coupon: bool
    has_ledger: bool
    has_transfer: bool
    has_cancel: bool
    webhook_flow: str | None
    payment_component: str | None
    entitlement_component: str | None
    coupon_component: str | None
    ledger_component: str | None
    billing_asset: str | None
    entitlement_asset: str | None
    sensitive_flow: str | None
    sensitive_component: str | None


def build_business_abuse_context(doc: ThreatModelDocument) -> BusinessAbuseContext:
    component_by_id = {c.id: c for c in doc.components}
    flow_by_id = {f.id: f for f in doc.data_flows}
    webhook_flow = first_flow_id_with(doc, "webhook")
    payment_component = first_component_id_with(doc, "payment", "checkout", "billing")
    entitlement_component = first_component_id_with(doc, "entitlement", "subscription", "premium")
    coupon_component = first_component_id_with(doc, "coupon", "discount")
    ledger_component = first_component_id_with(doc, "ledger", "finance", "wallet")
    billing_asset = first_asset_id_with(doc, "billing", "payment", "cobranca", "saldo", "balance")
    entitlement_asset = first_asset_id_with(doc, "entitlement", "premium", "subscription", "assinatura")
    sensitive_flow = first_flow_id_with(doc, "checkout", "transfer", "record", "entitlement", "webhook")
    sensitive_component = None
    if sensitive_flow and sensitive_flow in flow_by_id:
        flow = flow_by_id[sensitive_flow]
        sensitive_component = flow.to_component if flow.to_component in component_by_id else None
    return BusinessAbuseContext(
        has_payment=bool(first_component_id_with(doc, "payment", "billing", "checkout")),
        has_webhook=bool(webhook_flow),
        has_entitlement=bool(entitlement_component),
        has_coupon=bool(coupon_component) or bool(first_asset_id_with(doc, "coupon", "desconto", "discount")),
        has_ledger=bool(ledger_component),
        has_transfer=bool(first_flow_id_with(doc, "transfer", "transaction", "ledger")),
        has_cancel=bool(first_component_id_with(doc, "cancel", "subscription")),
        webhook_flow=webhook_flow,
        payment_component=payment_component,
        entitlement_component=entitlement_component,
        coupon_component=coupon_component,
        ledger_component=ledger_component,
        billing_asset=billing_asset,
        entitlement_asset=entitlement_asset,
        sensitive_flow=sensitive_flow,
        sensitive_component=sensitive_component,
    )


def first_flow_id_with(doc: ThreatModelDocument, *tokens: str) -> str | None:
    for f in doc.data_flows:
        text = " ".join([f.id, f.name or "", f.from_component, f.to_component, f.protocol or ""]).lower()
        if any(t in text for t in tokens):
            return f.id
    return None


def first_component_id_with(doc: ThreatModelDocument, *tokens: str) -> str | None:
    for c in doc.components:
        text = " ".join([c.id, c.name, c.technology or "", c.kind.value]).lower()
        if any(t in text for t in tokens):
            return c.id
    return None


def first_asset_id_with(doc: ThreatModelDocument, *tokens: str) -> str | None:
    for a in doc.assets:
        text = " ".join([a.id, a.name, a.description or "", a.sensitivity or ""]).lower()
        if any(t in text for t in tokens):
            return a.id
    return None
