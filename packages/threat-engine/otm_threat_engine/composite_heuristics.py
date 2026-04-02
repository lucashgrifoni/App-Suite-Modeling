"""
Heurísticas compostas — correlaciona fluxos, componentes e exposição.
"""

from __future__ import annotations

from otm_core_schema import ComponentKind, StrideCategory, ThreatModelDocument
from otm_core_schema.enums import FlowSemanticClass, HeuristicTier

from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def append_composite_heuristics(
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
    *,
    existing_ids: set[str],
) -> int:
    """
    Acrescenta padrões compostos. Devolve número de heurísticas adicionadas.
    """
    added = 0
    by_id = {c.id: c for c in doc.components}

    for flow in doc.data_flows:
        if not by_id.get(flow.from_component) or not by_id.get(flow.to_component):
            continue

        # Padrão: fetch externo + input não confiável
        if flow.semantic_class == FlowSemanticClass.EXTERNAL_FETCH or flow.supports_external_fetch:
            if flow.input_from_untrusted_source or flow.public_exposure:
                hid = f"cmp_ssrf_{flow.id}"
                if hid not in existing_ids:
                    heuristics.append(
                        HeuristicThreat(
                            id=hid,
                            title="[composite] Risco SSRF / fetch server-side no fluxo",
                            description=(
                                f"Fluxo `{flow.id}` combina origem não confiável e fetch externo. "
                                "Validar allowlist, bloqueio de IPs internos e timeouts."
                            ),
                            stride=StrideCategory.TAMPERING,
                            target_data_flow_id=flow.id,
                            risk=build_risk_assessment(4, 4),
                            finding_family="external_fetch_risk",
                            heuristic_tier=HeuristicTier.COMPOSITE_PATTERN,
                            signal_refs=[flow.id, "untrusted_input", "external_fetch"],
                        )
                    )
                    existing_ids.add(hid)
                    added += 1

        # Padrão: upload + storage
        if flow.semantic_class in (FlowSemanticClass.FILE_UPLOAD, FlowSemanticClass.UPLOAD_VALIDATION):
            if flow.supports_file_upload or flow.stores_sensitive_data:
                hid = f"cmp_upload_{flow.id}"
                if hid not in existing_ids:
                    heuristics.append(
                        HeuristicThreat(
                            id=hid,
                            title="[composite] Cadeia de upload — validação e destino",
                            description=(
                                f"Fluxo `{flow.id}` sugere cadeia de upload. Rever tipo MIME, destino, "
                                "quarentena e permissões de leitura pública."
                            ),
                            stride=StrideCategory.TAMPERING,
                            target_data_flow_id=flow.id,
                            risk=build_risk_assessment(4, 5),
                            finding_family="user_content_execution_risk",
                            heuristic_tier=HeuristicTier.COMPOSITE_PATTERN,
                            signal_refs=[flow.id, "file_upload"],
                        )
                    )
                    existing_ids.add(hid)
                    added += 1

        # Padrão: API pública + operação privilegiada
        if flow.public_exposure and flow.affects_privileged_state:
            hid = f"cmp_priv_{flow.id}"
            if hid not in existing_ids:
                heuristics.append(
                    HeuristicThreat(
                        id=hid,
                        title="[composite] Superfície pública com estado privilegiado",
                        description=(
                            f"Fluxo `{flow.id}` expõe alteração de estado privilegiado. Rever authn/authz fortes, "
                            "anti-CSRF e rate limiting."
                        ),
                        stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
                        target_data_flow_id=flow.id,
                        risk=build_risk_assessment(5, 5),
                        finding_family="access_control_broken",
                        heuristic_tier=HeuristicTier.COMPOSITE_PATTERN,
                        signal_refs=[flow.id, "public_exposure", "privileged_state"],
                    )
                )
                existing_ids.add(hid)
                added += 1

    for comp in doc.components:
        if comp.kind != ComponentKind.GATEWAY:
            continue
        hid = f"cmp_gw_{comp.id}_policy"
        if hid in existing_ids:
            continue
        heuristics.append(
            HeuristicThreat(
                id=hid,
                title=f"[{StrideCategory.SPOOFING.value}] Gateway — política e spoofing de origem",
                description=(
                    f"Componente gateway `{comp.name}`: rever políticas de roteamento, cabeçalhos confiáveis "
                    "e rate limiting por política."
                ),
                stride=StrideCategory.SPOOFING,
                target_component_id=comp.id,
                risk=build_risk_assessment(4, 4),
                finding_family="admin_surface_risk" if comp.supports_admin_operations else None,
                heuristic_tier=HeuristicTier.CONTEXTUAL,
                signal_refs=[comp.id, "gateway"],
            )
        )
        existing_ids.add(hid)
        added += 1

    return added
