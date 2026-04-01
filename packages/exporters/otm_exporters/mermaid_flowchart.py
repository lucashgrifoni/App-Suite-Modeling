"""
Diagrama Mermaid (flowchart) — só depende do modelo canónico.

Estrutura nós/arestas: `tests/test_exporters.py` (`flowchart_mermaid`).
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument


def export_flowchart_mermaid(doc: ThreatModelDocument) -> str:
    """
    Flowchart LR: primeiro `flowchart LR`, depois um nó por componente, depois uma aresta
    por fluxo (ver `test_export_flowchart_mermaid_minimal_node_and_edge_line_counts`).
    IDs Mermaid sanitizados; labels com aspas duplas escapadas para aspas simples.
    """
    lines: list[str] = ["flowchart LR"]
    for c in doc.components:
        label = _mermaid_label(c.name)
        nid = _mermaid_node_id(c.id)
        lines.append(f'    {nid}["{label}"]')

    for f in doc.data_flows:
        a = _mermaid_node_id(f.from_component)
        b = _mermaid_node_id(f.to_component)
        label = _mermaid_label(f.name or f.id)
        lines.append(f"    {a} -->|{label}| {b}")

    return "\n".join(lines) + "\n"


def _mermaid_node_id(raw: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in raw)


def _mermaid_label(raw: str) -> str:
    return raw.replace('"', "'")
