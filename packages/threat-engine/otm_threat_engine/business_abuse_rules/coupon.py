from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_coupon_abuse(context: BusinessAbuseContext, add) -> None:
    if not context.has_coupon:
        return
    add(
        hid="biz_coupon_reuse_and_discount_stacking",
        title="[economic_fraud] Reuso de cupom e empilhamento de desconto",
        description=(
            "Politica de cupom exploravel permite desconto indevido repetivel (reuse/stacking). "
            "Controle recomendado: limite por owner/periodo, anti-replay de coupon_use_id "
            "e bloqueio "
            "de combinacao de cupons nao permitida."
        ),
        stride=StrideCategory.TAMPERING,
        likelihood=4,
        impact=4,
        target_component_id=context.coupon_component,
        target_asset_id=context.billing_asset,
    )
