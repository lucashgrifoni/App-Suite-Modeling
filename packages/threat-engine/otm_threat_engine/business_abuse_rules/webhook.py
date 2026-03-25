from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_webhook_abuse(context: BusinessAbuseContext, add) -> None:
    if not (context.has_webhook and context.has_payment):
        return
    add(
        hid="biz_webhook_replay_economic_abuse",
        title="[business_abuse] Replay de webhook com impacto economico",
        description=(
            "Eventos de webhook repetidos podem reaplicar confirmacao financeira "
            "e liberar beneficio "
            "economico indevido. Controle recomendado: idempotencia por event_id + "
            "janela de replay + "
            "armazenamento de eventos processados."
        ),
        stride=StrideCategory.TAMPERING,
        likelihood=4,
        impact=5,
        target_component_id=context.payment_component,
        target_data_flow_id=context.webhook_flow,
        target_asset_id=context.billing_asset,
    )
    add(
        hid="biz_webhook_out_of_order_state_regression",
        title="[state_inconsistency] Ordem de eventos invalida em webhook",
        description=(
            "Eventos fora de ordem podem causar regressao de estado (ex.: paid->pending) e quebrar "
            "consistencia operacional/economica. Controle recomendado: state machine monotonica "
            "com transicoes invalidas bloqueadas."
        ),
        stride=StrideCategory.TAMPERING,
        likelihood=3,
        impact=5,
        target_component_id=context.payment_component,
        target_data_flow_id=context.webhook_flow,
        target_asset_id=context.billing_asset,
    )
