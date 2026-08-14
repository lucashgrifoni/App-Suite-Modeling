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
#: NEL (U+0085), LINE SEPARATOR (U+2028) e PARAGRAPH SEPARATOR (U+2029) foram acrescentados em
#: 2026-08-13. O invariante que este exportador declara acima é "um nome não pode acrescentar uma
#: linha", e estes três acrescentam — enquanto `\r\n\t\f\v` eram achatados, os separadores Unicode
#: passavam intactos. Não foi construída injeção de statement (as aspas seguram o label), por isso
#: o impacto é `INFO`; o invariante é que estava falso.
_LABEL_CONTROL_RE = re.compile("[\r\n\t\f\v\x85\u2028\u2029]+")

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
    node_ids = _mermaid_node_ids(doc)
    lines: list[str] = ["flowchart LR"]
    for c in doc.components:
        label = _mermaid_label(c.name)
        lines.append(f'    {node_ids[c.id]}["{label}"]')

    for f in doc.data_flows:
        a = node_ids[f.from_component]
        b = node_ids[f.to_component]
        label = _mermaid_edge_label(f.name or f.id)
        lines.append(f"    {a} -->|{label}| {b}")

    return "\n".join(lines) + "\n"


def _mermaid_node_ids(doc: ThreatModelDocument) -> dict[str, str]:
    """One Mermaid node id per entity id, and never the same one twice.

    The per-id sanitiser is not injective and cannot be: `-`, `.` and every other character the
    entity-id pattern allows but Mermaid does not all fold to `_`, so `svc-a`, `svc.a` and
    `svc_a` — three ids `otm validate` accepts as distinct components — produced one node id
    defined three times, and both flows between them rendered as self-loops. The reserved-word
    escape collided the same way: `end` and `end_` both became `end_`. The diagram was silently
    wrong: three boxes drawn as one, with no warning and exit 0.

    Injectivity is a property of the whole set, so it is resolved over the whole set. Each id
    takes its sanitised form when that form is free, and otherwise the first `<base>_<n>` that
    collides with neither an id already assigned nor a base another id will claim — checking the
    bases too is what stops the disambiguated name from stealing a later id's node. Assignment
    follows document order, so the output stays deterministic, and a model whose sanitised ids
    are already distinct — every shipped example and template — renders byte for byte as before.

    Flow endpoints are looked up in the same table rather than re-sanitised, which is what keeps
    an edge attached to the node it names. Every endpoint is in it: the schema rejects a flow
    whose `from_component`/`to_component` is not a declared component, and rejects duplicate
    component ids, so the table is total over the endpoints and one entry per component.
    """
    component_ids = [c.id for c in doc.components]
    bases = {_mermaid_base_id(raw) for raw in component_ids}
    assigned: dict[str, str] = {}
    taken: set[str] = set()
    for raw in component_ids:
        base = _mermaid_base_id(raw)
        candidate = base
        suffix = 2
        while candidate in taken or (candidate != base and candidate in bases):
            candidate = f"{base}_{suffix}"
            suffix += 1
        taken.add(candidate)
        assigned[raw] = candidate
    return assigned


def _mermaid_base_id(raw: str) -> str:
    """The node id an entity id maps to before collisions are resolved."""
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
