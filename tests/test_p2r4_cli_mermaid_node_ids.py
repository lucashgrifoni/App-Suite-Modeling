"""Round-4 regression: distinct component ids must be distinct Mermaid nodes.

`otm validate` accepts `svc-a`, `svc.a` and `svc_a` as three components. `otm diagram` folded
every non-alphanumeric character to `_`, so all three emitted the node id `svc_a`: one box
instead of three, and both flows between them drawn as self-loops. Exit 0, no warning. The
reserved-word escape collided the same way — `end` and `end_` both became `end_`.

Checked end to end through the command, because the diagram is what the user reads, and the
property under test is about the whole document, not about one id.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_flowchart_mermaid
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"

_NODE_RE = re.compile(r"^\s{4}(\S+)\[")
_EDGE_RE = re.compile(r"^\s{4}(\S+) -->\|.*\| (\S+)$")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _model(tmp_path: Path, name: str, ids: list[str], flows: list[tuple[str, str, str]]) -> Path:
    components = "\n".join(f'  - id: {i}\n    name: "Component {i}"\n    kind: process' for i in ids)
    data_flows = "\n".join(
        f"  - id: {fid}\n    from_component: {src}\n    to_component: {dst}" for fid, src, dst in flows
    )
    data_flows = data_flows or "  []"
    path = tmp_path / name
    path.write_text(
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "  industry_sector: saas\n"
        "metadata:\n"
        '  title: "Collision probe"\n'
        f"components:\n{components}\n"
        f"data_flows:\n{data_flows}\n",
        encoding="utf-8",
    )
    return path


def _nodes(mermaid: str) -> list[str]:
    return [m.group(1) for line in mermaid.splitlines() if (m := _NODE_RE.match(line))]


def _edges(mermaid: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for line in mermaid.splitlines() if (m := _EDGE_RE.match(line))]


def test_ids_that_differ_only_by_separator_get_their_own_node(runner: CliRunner, tmp_path: Path) -> None:
    """The reported case: `svc-a`, `svc.a`, `svc_a` collapsed onto one node id."""
    model = _model(tmp_path, "coll.otm.yaml", ["svc-a", "svc.a", "svc_a"], [("f1", "svc-a", "svc.a")])

    result = runner.invoke(app, ["diagram", str(model)])

    assert result.exit_code == 0, result.output
    nodes = _nodes(result.output)
    assert len(nodes) == 3
    assert len(set(nodes)) == 3, f"node ids collided: {nodes}"


def test_a_flow_between_two_components_is_not_drawn_as_a_self_loop(runner: CliRunner, tmp_path: Path) -> None:
    """The consequence a reader sees: the edge disappeared into the collapsed box."""
    model = _model(
        tmp_path,
        "coll.otm.yaml",
        ["svc-a", "svc.a", "svc_a"],
        [("f1", "svc-a", "svc.a"), ("f2", "svc.a", "svc_a")],
    )

    result = runner.invoke(app, ["diagram", str(model)])

    edges = _edges(result.output)
    assert len(edges) == 2
    assert all(src != dst for src, dst in edges), f"self-loops: {edges}"


def test_each_edge_endpoint_resolves_to_the_node_of_the_component_it_names(tmp_path: Path) -> None:
    """Injectivity alone is not enough: the edge has to land on the right box."""
    model = _model(
        tmp_path,
        "coll.otm.yaml",
        ["svc-a", "svc.a", "svc_a"],
        [("f1", "svc-a", "svc.a"), ("f2", "svc.a", "svc_a")],
    )
    doc = load_document_from_yaml_path(model)

    mermaid = export_flowchart_mermaid(doc)

    nodes = _nodes(mermaid)
    # Nodes are emitted in component order, so position i is the node of component i.
    node_of = dict(zip([c.id for c in doc.components], nodes, strict=True))
    assert _edges(mermaid) == [
        (node_of["svc-a"], node_of["svc.a"]),
        (node_of["svc.a"], node_of["svc_a"]),
    ]


def test_the_reserved_word_escape_does_not_steal_an_existing_id(runner: CliRunner, tmp_path: Path) -> None:
    """`end` escapes to `end_`, which is itself a valid entity id someone may already use."""
    model = _model(tmp_path, "kw.otm.yaml", ["end", "end_", "endx"], [("f1", "end", "end_")])

    result = runner.invoke(app, ["diagram", str(model)])

    nodes = _nodes(result.output)
    assert len(set(nodes)) == 3, f"node ids collided: {nodes}"
    assert _edges(result.output) == [(nodes[0], nodes[1])]


def test_a_disambiguated_id_does_not_collide_with_a_later_component(tmp_path: Path) -> None:
    """The subtle one: the generated `<base>_2` must not be another component's own node id."""
    model = _model(tmp_path, "deep.otm.yaml", ["svc-a", "svc.a", "svc_a_2"], [])
    doc = load_document_from_yaml_path(model)

    nodes = _nodes(export_flowchart_mermaid(doc))

    assert len(set(nodes)) == 3, f"node ids collided: {nodes}"


@pytest.mark.parametrize("example", sorted(_EXAMPLES.glob("*.otm.yaml")))
def test_shipped_models_keep_one_node_per_component(example: Path) -> None:
    """Guards the other direction: the collision resolver must not rename anything gratuitously.

    Every shipped model already has ids that sanitise apart, so each node id must still be the
    plain sanitised form — no `_2` suffixes appearing in diagrams that were correct before.
    """
    doc = load_document_from_yaml_path(example)

    nodes = _nodes(export_flowchart_mermaid(doc))

    assert nodes == ["".join(ch if ch.isalnum() else "_" for ch in c.id) for c in doc.components]
