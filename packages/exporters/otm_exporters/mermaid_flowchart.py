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

#: Characters that are safe in an *unquoted* edge label (`-->|like this|`).
#: Everything else — notably `( ) [ ] { }` and `@`, which open a node-shape or an
#: edge-id token — makes the parser abandon the label, so those labels are quoted
#: instead. Verified against mermaid 11 `mermaid.parse()`: a flow named
#: `Checkout (HTTPS)` produced `Parse error ... got 'PS'` before this guard.
_BARE_EDGE_LABEL_CHARS = frozenset(" _-.,:;!?'/&%#=+")

#: Node ids that are Mermaid grammar keywords. A component whose id is literally
#: `end` emits `end["…"]`, which the lexer reads as the `end` keyword and not as a
#: node, so the whole diagram fails to parse. `otm validate` accepts these ids, so
#: the exporter has to make them safe. Compared case-insensitively: today only the
#: exact lowercase spelling collides, but that is a lexer detail, not a contract.
_RESERVED_NODE_IDS = frozenset(
    {
        "call",
        "callback",
        "class",
        "classdef",
        "click",
        "default",
        "direction",
        "end",
        "flowchart",
        "graph",
        "href",
        "interpolate",
        "linkstyle",
        "style",
        "subgraph",
    }
)


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
        label = _mermaid_edge_label(f.name or f.id)
        lines.append(f"    {a} -->|{label}| {b}")

    return "\n".join(lines) + "\n"


def _mermaid_node_id(raw: str) -> str:
    ident = "".join(ch if ch.isalnum() else "_" for ch in raw)
    if ident.lower() in _RESERVED_NODE_IDS:
        return f"{ident}_"
    return ident


def _mermaid_label(raw: str) -> str:
    # Collapse line breaks/control chars to a space (prevents statement injection)
    # and neutralize the characters that terminate a label: `"` closes a quoted
    # node label and `|` closes an unquoted edge label.
    text = _LABEL_CONTROL_RE.sub(" ", raw)
    return text.replace('"', "'").replace("|", "/")


def _mermaid_edge_label(raw: str) -> str:
    """Edge label, quoted whenever a bare one would not parse.

    Node labels are always quoted (`id["name"]`); edge labels were not, so any
    everyday name with brackets — `Checkout (HTTPS)` — produced a `.mmd` that
    `otm diagram` reported as written and no Mermaid renderer would accept.
    Quoting is applied only when it is needed, so the diagrams of models whose
    flow names are plain words keep their existing, documented shape.
    """
    label = _mermaid_label(raw)
    if label and all(ch.isalnum() or ch in _BARE_EDGE_LABEL_CHARS for ch in label):
        return label
    return f'"{label}"'
