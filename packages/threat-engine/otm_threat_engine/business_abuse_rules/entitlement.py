from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_entitlement_billing_mismatch(context: BusinessAbuseContext, add) -> None:
    if not (context.has_payment and context.has_entitlement):
        return
    add(
        hid="biz_payment_entitlement_mismatch",
        title="[economic_fraud] Entitlement sem base economica valida",
        description=(
            "Risco de liberar entitlement premium sem correspondencia valida "
            "entre owner, valor e status "
            "de pagamento. Controle recomendado: correlacao obrigatoria "
            "payment_id->owner->plan->entitlement "
            "antes da ativacao."
        ),
        stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
        likelihood=4,
        impact=5,
        target_component_id=context.entitlement_component,
        target_asset_id=context.entitlement_asset or context.billing_asset,
    )
    if context.has_cancel and context.has_entitlement:
        add(
            hid="biz_cancel_without_entitlement_revocation",
            title="[state_inconsistency] Cancelamento sem revogacao de privilegio",
            description=(
                "Cancelamento pode nao revogar entitlement em tempo util, mantendo beneficio "
                "sem contraprestacao. "
                "Controle recomendado: revogacao atomica no cancelamento e reconciliacao periodica "
                "estado "
                "assinatura x entitlement."
            ),
            stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
            likelihood=3,
            impact=5,
            target_component_id=context.entitlement_component,
            target_asset_id=context.entitlement_asset,
        )
