from __future__ import annotations

from otm_core_schema import Asset, StrideCategory, ThreatModelDocument
from otm_core_schema.enums import HeuristicTier
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.pack_runtime import apply_pack_to_li
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import (
    build_risk_assessment,
    likelihood_impact_for_component,
    likelihood_impact_for_data_flow,
)
from otm_threat_engine.stride_heuristics import (
    description_for_component_threat,
    stride_for_cross_boundary_flow,
    strides_for_component,
    strides_for_unencrypted_flow,
    title_for_component_threat,
)


def append_component_heuristics(
    *,
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
    existing: set[tuple[str | None, str | None, str]],
    assets_by_id: dict[str, Asset],
    pack: PackDefinition | None,
) -> int:
    skipped = 0
    for comp in doc.components:
        for stride in strides_for_component(comp.kind):
            key = (comp.id, None, stride.value)
            raw = likelihood_impact_for_component(comp, stride, assets_by_id=assets_by_id)
            li = apply_pack_to_li(raw[0], raw[1], pack)
            is_duplicate = key in existing
            _append_heuristic_threat(
                heuristics,
                threat_id=f"eng_{comp.id}_{stride.value}",
                title=title_for_component_threat(comp, stride),
                description=description_for_component_threat(comp),
                stride=stride,
                target_component_id=comp.id,
                risk_li=li,
                skipped_as_duplicate=is_duplicate,
            )
            if is_duplicate:
                skipped += 1
    return skipped


def append_flow_heuristics(
    *,
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
    existing: set[tuple[str | None, str | None, str]],
    cross_flows: set[str],
    pack: PackDefinition | None,
) -> int:
    skipped = 0
    for flow in doc.data_flows:
        crosses = flow.id in cross_flows
        unencrypted = flow.encrypted is not True
        flow_strides = _flow_stride_candidates(
            flow.id,
            flow.name,
            flow.from_component,
            flow.to_component,
            crosses=crosses,
            unencrypted=unencrypted,
        )
        seen_stride: set[str] = set()
        for stride_val, title_short, desc in flow_strides:
            if stride_val in seen_stride:
                continue
            seen_stride.add(stride_val)
            stride = StrideCategory(stride_val)
            key = (None, flow.id, stride.value)
            # Pass only the real boundary-crossing signal: `likelihood_impact_for_data_flow`
            # already applies a dedicated penalty for `flow.encrypted is False`/`None`,
            # so OR-ing `unencrypted` here double-counted it (inflating an unencrypted,
            # non-crossing flow to L×I 5×5 instead of 4×4).
            raw = likelihood_impact_for_data_flow(flow, crosses_boundary=crosses)
            li = apply_pack_to_li(raw[0], raw[1], pack)
            is_duplicate = key in existing
            _append_heuristic_threat(
                heuristics,
                threat_id=f"eng_flow_{flow.id}_{stride.value}",
                title=f"[{stride.value}] {title_short}",
                description=desc,
                stride=stride,
                target_data_flow_id=flow.id,
                risk_li=li,
                skipped_as_duplicate=is_duplicate,
            )
            if is_duplicate:
                skipped += 1
    return skipped


def _append_heuristic_threat(
    heuristics: list[HeuristicThreat],
    *,
    threat_id: str,
    title: str,
    description: str,
    stride: StrideCategory,
    risk_li: tuple[int, int],
    skipped_as_duplicate: bool,
    target_component_id: str | None = None,
    target_data_flow_id: str | None = None,
) -> None:
    heuristics.append(
        HeuristicThreat(
            id=threat_id,
            title=title,
            description=description,
            stride=stride,
            target_component_id=target_component_id,
            target_data_flow_id=target_data_flow_id,
            risk=build_risk_assessment(*risk_li),
            skipped_as_duplicate=skipped_as_duplicate,
            heuristic_tier=HeuristicTier.GENERIC_STRIDE,
        )
    )


def _flow_stride_candidates(
    flow_id: str,
    flow_name: str | None,
    from_component: str,
    to_component: str,
    *,
    crosses: bool,
    unencrypted: bool,
) -> list[tuple[str, str, str]]:
    flow_strides: list[tuple[str, str, str]] = []
    if crosses:
        s = stride_for_cross_boundary_flow()
        flow_strides.append(
            (
                s.value,
                f"Atravessa fronteira — {flow_id}",
                "Fluxo entre zonas de confiança distintas; rever integridade e autenticação de extremidades.",
            )
        )
    if unencrypted:
        for stride in strides_for_unencrypted_flow():
            flow_strides.append(
                (
                    stride.value,
                    f"Canal do fluxo {flow_name or flow_id}",
                    (
                        f"Propriedades de confidencialidade/integridade a rever no fluxo "
                        f"'{flow_id}' ({from_component} → {to_component})."
                    ),
                )
            )
    return flow_strides
