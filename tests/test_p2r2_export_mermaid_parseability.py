"""`otm diagram` must emit Mermaid that a Mermaid parser accepts.

Two defects, one symptom — `otm validate` and `otm diagram` both exit 0 and the `.mmd` fails to
render wherever it is pasted:

* Edge labels were written unquoted (`user -->|Checkout (HTTPS)| waf`), so any everyday flow name
  containing `( ) [ ] { }` or `@` broke the parse. Node labels were already quoted, so the very
  same characters were safe one line above.
* A component id that is a Mermaid grammar keyword (`end`, `graph`, `subgraph`, `class`,
  `classDef`, `style`, `linkStyle`, `flowchart`, `call`, `href`, `interpolate`) was emitted raw,
  and the lexer read the keyword instead of a node.

Both were reproduced and both fixes were verified against the real parser (mermaid 11.16.1 +
jsdom, `mermaid.parse`, `securityLevel: 'strict'`) over a 72-case matrix of flow names, component
ids and every shipped example: 19 of 72 failed before, 0 of 72 after. That harness needs npm and
a browser DOM, so it cannot run in this suite; the assertions below pin the emitted shape it
proved correct.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_exporters import export_flowchart_mermaid

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"

#: Exactly the ids the real parser rejected before the fix.
_KEYWORD_IDS = [
    "end",
    "graph",
    "subgraph",
    "class",
    "classDef",
    "style",
    "linkStyle",
    "flowchart",
    "call",
    "href",
    "interpolate",
]


@pytest.fixture
def doc() -> ThreatModelDocument:
    return load_document_from_yaml_path(_MINIMAL)


def _edge_lines(mermaid: str) -> list[str]:
    return [line.strip() for line in mermaid.splitlines() if "-->" in line]


def _node_lines(mermaid: str) -> list[str]:
    return [line.strip() for line in mermaid.splitlines() if "-->" not in line and line.startswith("    ")]


@pytest.mark.parametrize("name", ["Checkout (HTTPS)", "a)b", "a[b", "a]b", "a{b", "a}b", "a@b"])
def test_an_edge_label_with_grammar_characters_is_quoted(doc: ThreatModelDocument, name: str) -> None:
    doc.data_flows[0].name = name

    assert _edge_lines(export_flowchart_mermaid(doc))[0].endswith(f'-->|"{name}"| api')


def test_a_plain_edge_label_is_left_unquoted(doc: ThreatModelDocument) -> None:
    """The published `examples/export_samples/minimal.flowchart.mmd` shows this shape."""
    doc.data_flows[0].name = "HTTPS"

    assert _edge_lines(export_flowchart_mermaid(doc))[0] == "user -->|HTTPS| api"


def test_a_quote_inside_a_quoted_edge_label_cannot_close_it(doc: ThreatModelDocument) -> None:
    """`"` is already folded to `'`, which is what makes unconditional quoting safe."""
    doc.data_flows[0].name = 'Checkout ("fast")'

    assert _edge_lines(export_flowchart_mermaid(doc))[0] == "user -->|\"Checkout ('fast')\"| api"


def test_a_pipe_in_an_edge_label_still_cannot_terminate_it(doc: ThreatModelDocument) -> None:
    doc.data_flows[0].name = "a|b(c)"

    assert '-->|"a/b(c)"|' in export_flowchart_mermaid(doc)


def test_a_newline_in_an_edge_label_still_cannot_inject_a_statement(doc: ThreatModelDocument) -> None:
    """The pre-existing injection guard must survive the new quoting path."""
    doc.data_flows[0].name = "evil\n    hack[Injected]"
    before = len(export_flowchart_mermaid(load_document_from_yaml_path(_MINIMAL)).splitlines())

    assert len(export_flowchart_mermaid(doc).splitlines()) == before


@pytest.mark.parametrize("component_id", _KEYWORD_IDS)
def test_a_component_id_that_is_a_mermaid_keyword_is_escaped(doc: ThreatModelDocument, component_id: str) -> None:
    original = doc.components[0].id
    doc.components[0].id = component_id
    for flow in doc.data_flows:
        if flow.from_component == original:
            flow.from_component = component_id

    assert _node_lines(export_flowchart_mermaid(doc))[0].startswith(f'{component_id}_["')


def test_the_escaped_id_is_used_on_the_edge_too(doc: ThreatModelDocument) -> None:
    """A node renamed on one side only would produce a dangling edge to a phantom node."""
    doc.components[0].id = "end"
    doc.data_flows[0].from_component = "end"

    assert _edge_lines(export_flowchart_mermaid(doc))[0].startswith("end_ -->")


def test_an_ordinary_component_id_is_not_renamed(doc: ThreatModelDocument) -> None:
    assert '    user["' in export_flowchart_mermaid(doc)


def test_the_keyword_check_ignores_case(doc: ThreatModelDocument) -> None:
    """`END` parses today, but that is a lexer detail rather than a promise."""
    doc.components[0].id = "End"
    doc.data_flows[0].from_component = "End"

    assert '    End_["' in export_flowchart_mermaid(doc)


def test_the_shipped_example_diagram_is_unchanged() -> None:
    """`examples/export_samples/minimal.flowchart.mmd` is published in docs/features/EXPORTERS.md."""
    sample = _MINIMAL.parent / "export_samples" / "minimal.flowchart.mmd"

    assert export_flowchart_mermaid(load_document_from_yaml_path(_MINIMAL)) == sample.read_text(encoding="utf-8")
