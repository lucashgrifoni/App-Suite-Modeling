"""Insights simples sobre trust boundaries e fluxos."""

from __future__ import annotations

from collections.abc import Mapping

from otm_core_schema import Component, ThreatModelDocument

from otm_threat_engine.result import TrustBoundaryFinding


def _boundary_of(component_id: str, by_id: Mapping[str, Component]) -> str | None:
    comp = by_id.get(component_id)
    return comp.in_trust_boundary if comp else None


def _flow_display_id(flow_id: str | None, flow_name: str | None) -> str:
    return flow_id or flow_name or "?"


def analyze_trust_boundary_crossings(doc: ThreatModelDocument) -> list[TrustBoundaryFinding]:
    """Identifica fluxos que atravessam fronteiras distintas (ponto de análise STRIDE)."""
    by_id = {c.id: c for c in doc.components}
    out: list[TrustBoundaryFinding] = []

    for flow in doc.data_flows:
        fb = _boundary_of(flow.from_component, by_id)
        tb = _boundary_of(flow.to_component, by_id)
        if fb is None or tb is None:
            continue
        if fb != tb:
            out.append(
                TrustBoundaryFinding(
                    code="CROSS_BOUNDARY_FLOW",
                    message=(f"Fluxo '{_flow_display_id(flow.id, flow.name)}' liga fronteira '{fb}' → '{tb}'."),
                    data_flow_id=flow.id,
                    from_boundary_id=fb,
                    to_boundary_id=tb,
                )
            )

    return out
