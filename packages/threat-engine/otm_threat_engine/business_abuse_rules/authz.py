from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_business_context_authz(context: BusinessAbuseContext, add) -> None:
    add(
        hid="biz_authorization_without_business_context",
        title="[business_abuse] Autorizacao tecnica sem contexto de negocio",
        description=(
            "Mesmo com autenticacao/role valida, operacao pode ser indevida "
            "sem validacao de ownership, "
            "vinculo comercial ou escopo economico. Controle recomendado: policy check contextual "
            "(owner, contrato, plano, vinculo clinico/financeiro) por operacao critica."
        ),
        stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
        likelihood=3,
        impact=4,
        target_component_id=context.sensitive_component,
        target_data_flow_id=context.sensitive_flow,
    )
