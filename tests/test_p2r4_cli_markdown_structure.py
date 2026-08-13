"""Round-4 regression: model data must not decide the outline of a Markdown artifact.

A component name carrying `\\n\\n## Injected heading\\n\\n| col a | col b |\\n| --- | --- |…`
passes `otm validate`, and every Markdown exporter then emitted a genuine H2 and a genuine table
inside the deliverable — in `otm export -f md`, and three times over in `otm backlog`, corrupting
the document outline. Table cells were already protected (`_md_cell` flattens newlines); nothing
else was.

The property is stated as a comparison rather than a list of forbidden strings: rendering a
document whose names are hostile must produce the *same document structure* as rendering the same
document with plain names. Only the text inside the lines may differ. That way a renderer path
nobody thought of is covered too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_exporters import (
    export_analysis_markdown,
    export_comparison_markdown,
    export_document_markdown,
    export_remediation_backlog_markdown,
)
from otm_exporters.markdown_text import md_block, md_inline
from otm_threat_engine import analyze_document, build_remediation_backlog
from otm_threat_engine.threat_model_comparison import compare_threat_models
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: A name that closes the bullet it sits in and opens a heading, a table and a quote.
_HOSTILE = "Edge gateway\n\n## Injected heading\n\n| col a | col b |\n| --- | --- |\n| x | y |\n\n> quoted"
_BENIGN = "Edge gateway"

#: Every construct that must come from the renderer and never from the data.
_BLOCK_START = re.compile(r"^\s{0,3}(#{1,6}\s|\||>|```|---\s*$|===)")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _document(name: str) -> ThreatModelDocument:
    """The minimal example with `name` pushed into every string a renderer interpolates."""
    doc = load_document_from_yaml_path(_MINIMAL)
    doc = doc.model_copy(
        update={
            "metadata": doc.metadata.model_copy(
                update={"title": name, "summary": name, "owner": name, "document_version": name}
            ),
            "components": [c.model_copy(update={"name": name, "technology": name}) for c in doc.components],
            "assets": [a.model_copy(update={"name": name}) for a in doc.assets],
            "data_flows": [f.model_copy(update={"name": name}) for f in doc.data_flows],
            "trust_boundaries": [b.model_copy(update={"name": name}) for b in doc.trust_boundaries],
            "threats": [t.model_copy(update={"title": name}) for t in doc.threats],
            "mitigations": [m.model_copy(update={"title": name}) for m in doc.mitigations],
        }
    )
    if doc.business_context:
        doc = doc.model_copy(update={"business_context": doc.business_context.model_copy(update={"description": name})})
    return doc


def _structure(markdown: str) -> list[str]:
    """The document outline: the block-level construct each line opens, in order.

    The construct, not the line: a heading whose *text* now carries the payload inline is exactly
    the intended outcome. What must not change is how many blocks there are and of what kind.
    """
    return [m.group(1).strip() for line in markdown.splitlines() if (m := _BLOCK_START.match(line))]


def _renderings(name: str) -> dict[str, str]:
    """Every Markdown artifact the exporters produce for one document."""
    doc = _document(name)
    analysis = analyze_document(doc)
    comparison = compare_threat_models(doc, doc, baseline_analysis=analysis, revised_analysis=analysis)
    return {
        "document": export_document_markdown(doc),
        "analysis": export_analysis_markdown(analysis),
        "backlog": export_remediation_backlog_markdown(build_remediation_backlog(analysis, doc)),
        "comparison": export_comparison_markdown(comparison),
    }


@pytest.mark.parametrize("artifact", ["document", "analysis", "backlog", "comparison"])
def test_hostile_names_cannot_change_the_document_outline(artifact: str) -> None:
    """The whole property, one exporter at a time."""
    hostile = _renderings(_HOSTILE)[artifact]
    benign = _renderings(_BENIGN)[artifact]

    assert _structure(hostile) == _structure(benign)


@pytest.mark.parametrize("artifact", ["document", "analysis", "backlog", "comparison"])
def test_the_payload_is_kept_as_text_not_dropped(artifact: str) -> None:
    """Neutralised, not censored: the reader still sees what the author wrote."""
    hostile = _renderings(_HOSTILE)[artifact]

    assert "Injected heading" in hostile


def test_export_md_does_not_gain_a_heading_from_a_component_name(runner: CliRunner, tmp_path: Path) -> None:
    """End to end through the command a user runs."""
    model = tmp_path / "nl.otm.yaml"
    model.write_text(
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "  industry_sector: saas\n"
        "metadata:\n"
        '  title: "Newline probe"\n'
        "components:\n"
        "  - id: c1\n"
        '    name: "Edge gateway\\n\\n## Injected heading\\n\\n| col a | col b |\\n| --- | --- |\\n| x | y |"\n'
        "    kind: external_entity\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.md"

    result = runner.invoke(app, ["export", str(model), "-f", "md", "-o", str(out)])

    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert "Injected heading" in text
    assert [line for line in text.splitlines() if line.startswith("## ")] == ["## Componentes"]


def test_backlog_does_not_repeat_a_forged_heading_through_the_command(runner: CliRunner, tmp_path: Path) -> None:
    """`otm backlog` emitted the forged heading three times, once per section that lists the item."""
    model = tmp_path / "nl.otm.yaml"
    model.write_text(
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "  industry_sector: saas\n"
        "metadata:\n"
        '  title: "Newline probe"\n'
        "components:\n"
        "  - id: c1\n"
        '    name: "Edge gateway\\n\\n## Injected heading"\n'
        "    kind: external_entity\n"
        "  - id: c2\n"
        '    name: "Core service"\n'
        "    kind: process\n",
        encoding="utf-8",
    )
    out = tmp_path / "backlog.md"

    result = runner.invoke(app, ["backlog", str(model), "-o", str(out)])

    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert "Injected heading" in text
    assert not [line for line in text.splitlines() if line.startswith("## Injected")]


def _rendered_text_fields(doc: ThreatModelDocument) -> list[str]:
    """Every model string the exporters interpolate into a Markdown line."""
    values = [doc.metadata.title, doc.metadata.summary, doc.metadata.owner, doc.metadata.document_version]
    values += [c.name for c in doc.components] + [c.technology for c in doc.components]
    values += [a.name for a in doc.assets] + [b.name for b in doc.trust_boundaries]
    values += [f.name for f in doc.data_flows] + [t.title for t in doc.threats]
    values += [m.title for m in doc.mitigations]
    if doc.business_context:
        values.append(doc.business_context.description)
    return [v for v in values if v]


@pytest.mark.parametrize("example", sorted((_ROOT / "examples").glob("*.otm.yaml")))
def test_neutralising_is_a_no_op_on_every_shipped_model(example: Path) -> None:
    """The other direction: the guarantee must cost nothing on models that are already fine.

    Not one shipped example has a line break in a field these exporters interpolate - YAML folded
    scalars collapse to a single line - so no delivered artifact changes by a byte. Asserted here
    rather than left to be noticed as snapshot churn.
    """
    doc = load_document_from_yaml_path(example)

    values = _rendered_text_fields(doc)

    assert [md_inline(v).strip() for v in values] == [v.strip() for v in values]


def test_md_block_and_md_inline_flatten_every_line_terminator() -> None:
    """The helper itself: CR, LF, CRLF, NEL, VT, FF, LS and PS all collapse to one space."""
    assert md_inline("a\nb") == "a b"
    assert md_inline("a\r\nb") == "a b"
    assert md_inline("a\u2028b\u2029c") == "a b c"
    assert md_inline("a\x0bb\x0cc\x85d") == "a b c d"
    assert md_inline(12) == "12"
    assert md_block("  a\n\n## b  ") == "a ## b"
