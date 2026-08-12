from __future__ import annotations

from otm_core_schema import StrideCategory

from otm_threat_engine.business_abuse_context import BusinessAbuseContext


def add_business_context_authz(context: BusinessAbuseContext, add) -> None:
    # Every sibling business-abuse rule guards on its own signal; this one did not,
    # so it fired on every document — even an empty one. Two things went wrong as a
    # result: the finding had no target to point at, and it pinned the `authorization`
    # family flag on permanently, which made the STRIDE noise-suppression gate delete
    # tampering / elevation-of-privilege findings from any component merely *named*
    # "authorization" or "ownership".
    if not (context.sensitive_component or context.sensitive_flow):
        return
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
