"""Diagrama Mermaid (flowchart) — só depende do modelo canónico."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument


def export_flowchart_mermaid(doc: ThreatModelDocument) -> str:
    """
    Flowchart LR com componentes como nós e fluxos como arestas etiquetadas.
    IDs Mermaid são derivados dos IDs do modelo (sanitizados para o parser).
    """
    lines: list[str] = ["flowchart LR"]
    for c in doc.components:
        label = c.name.replace('"', "'")
        nid = _mermaid_node_id(c.id)
        lines.append(f'    {nid}["{label}"]')

    for f in doc.data_flows:
        a, b = _mermaid_node_id(f.from_component), _mermaid_node_id(f.to_component)
        label = (f.name or f.id).replace('"', "'")
        lines.append(f"    {a} -->|{label}| {b}")

    return "\n".join(lines) + "\n"


def _mermaid_node_id(raw: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in raw)
