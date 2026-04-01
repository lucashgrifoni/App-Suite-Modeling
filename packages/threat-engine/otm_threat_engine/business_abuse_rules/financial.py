from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_financial_sequence_abuse(context: BusinessAbuseContext, add) -> None:
    if not (context.has_ledger or context.has_transfer):
        return
    add(
        hid="biz_double_submission_financial_action",
        title="[business_abuse] Dupla submissao de acao financeira",
        description=(
            "Reenvio intencional de acao critica (transferencia/confirmacao) pode duplicar "
            "efeito economico. "
            "Controle recomendado: idempotency key por request + lock logico por operacao de valor."
        ),
        stride=StrideCategory.TAMPERING,
        likelihood=4,
        impact=5,
        target_component_id=context.ledger_component,
        target_data_flow_id=context.sensitive_flow,
        target_asset_id=context.billing_asset,
    )
    add(
        hid="biz_balance_transaction_inconsistency",
        title="[state_inconsistency] Saldo inconsistente com transacoes",
        description=(
            "Eventos processados em sequencia incorreta podem quebrar reconciliacao entre saldo "
            "e transacoes confirmadas. Controle recomendado: reconciliacao deterministica "
            "saldo<->ledger e trilha de "
            "auditoria imutavel para eventos financeiros."
        ),
        stride=StrideCategory.TAMPERING,
        likelihood=3,
        impact=5,
        target_component_id=context.ledger_component,
        target_asset_id=context.billing_asset,
    )
