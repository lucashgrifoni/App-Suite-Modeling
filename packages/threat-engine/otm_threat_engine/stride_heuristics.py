"""Heurísticas STRIDE por tipo de componente e fluxo (MVP)."""

from __future__ import annotations

from otm_core_schema import Component, ComponentKind, StrideCategory


def strides_for_component(kind: ComponentKind) -> tuple[StrideCategory, ...]:
    """Conjunto representativo por tipo (evita explosão de ameaças idênticas)."""
    mapping: dict[ComponentKind, tuple[StrideCategory, ...]] = {
        ComponentKind.PROCESS: (
            StrideCategory.SPOOFING,
            StrideCategory.TAMPERING,
            StrideCategory.INFORMATION_DISCLOSURE,
            StrideCategory.DENIAL_OF_SERVICE,
            StrideCategory.ELEVATION_OF_PRIVILEGE,
        ),
        ComponentKind.DATASTORE: (
            StrideCategory.TAMPERING,
            StrideCategory.INFORMATION_DISCLOSURE,
            StrideCategory.DENIAL_OF_SERVICE,
        ),
        ComponentKind.EXTERNAL_ENTITY: (
            StrideCategory.SPOOFING,
            StrideCategory.TAMPERING,
        ),
        ComponentKind.USER: (
            StrideCategory.SPOOFING,
            StrideCategory.REPUDIATION,
        ),
        ComponentKind.GATEWAY: (
            StrideCategory.SPOOFING,
            StrideCategory.TAMPERING,
            StrideCategory.DENIAL_OF_SERVICE,
        ),
        ComponentKind.QUEUE: (
            StrideCategory.TAMPERING,
            StrideCategory.INFORMATION_DISCLOSURE,
            StrideCategory.DENIAL_OF_SERVICE,
        ),
        ComponentKind.OTHER: (
            StrideCategory.SPOOFING,
            StrideCategory.TAMPERING,
            StrideCategory.INFORMATION_DISCLOSURE,
        ),
    }
    return mapping.get(kind, mapping[ComponentKind.OTHER])


def title_for_component_threat(component: Component, stride: StrideCategory) -> str:
    role = (component.responsibility or component.technology_role or "").strip()
    if role:
        return f"[{stride.value}] {component.name} ({role})"
    return f"[{stride.value}] {component.name}"


def description_for_component_threat(component: Component) -> str:
    tech = f" ({component.technology})" if component.technology else ""
    extra = ""
    if component.handles_credentials:
        extra += " Componente indicado como manipulando credenciais — reforçar proteção de segredos e sessão."
    if component.supports_admin_operations:
        extra += " Superfície administrativa — priorizar controlos de autorização e auditoria."
    return (
        f"Ameaça STRIDE para '{component.name}'{tech} como {component.kind.value}.{extra} "
        "Rever controlos específicos do contexto."
    )


def strides_for_unencrypted_flow() -> tuple[StrideCategory, ...]:
    return (StrideCategory.TAMPERING, StrideCategory.INFORMATION_DISCLOSURE)


def stride_for_cross_boundary_flow() -> StrideCategory:
    return StrideCategory.TAMPERING
