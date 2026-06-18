"""
Diagrama Mermaid (flowchart) — só depende do modelo canónico.

Estrutura nós/arestas: `tests/test_exporters.py` (`flowchart_mermaid`).
"""

from __future__ import annotations

import re

from otm_core_schema import ThreatModelDocument

# Line breaks / control chars would let an attacker-controlled component or
# data-flow name inject extra Mermaid statements (new nodes/edges) into the
# generated diagram source.
_LABEL_CONTROL_RE = re.compile(r"[\r\n\t\f\v]+")


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
    # Collapse line breaks/control chars to a space (prevents statement injection)
    # and neutralize the characters that terminate a label: `"` closes a quoted
    # node label and `|` closes an unquoted edge label.
    text = _LABEL_CONTROL_RE.sub(" ", raw)
    return text.replace('"', "'").replace("|", "/")
