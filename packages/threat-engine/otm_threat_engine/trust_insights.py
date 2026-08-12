"""Insights simples sobre trust boundaries e fluxos."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_core_schema.trust_membership import resolve_component_boundaries

from otm_threat_engine.result import TrustBoundaryFinding


def _flow_display_id(flow_id: str | None, flow_name: str | None) -> str:
    return flow_id or flow_name or "?"


def analyze_trust_boundary_crossings(doc: ThreatModelDocument) -> list[TrustBoundaryFinding]:
    """Identifica fluxos que atravessam fronteiras distintas (ponto de análise STRIDE)."""
    # Resolvido das duas direcções: ler só `Component.in_trust_boundary` deixava um modelo
    # que declara a pertença na fronteira sem travessia nenhuma, sem aviso.
    boundaries = resolve_component_boundaries(doc)
    out: list[TrustBoundaryFinding] = []

    for flow in doc.data_flows:
        fb = boundaries.get(flow.from_component)
        tb = boundaries.get(flow.to_component)
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
