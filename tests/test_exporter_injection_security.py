"""Regressions — attacker-controlled model names must not break generated artifacts.

- Mermaid: a name with a newline/pipe/quote must not inject extra statements
  (nodes/edges) into the flowchart source.
- Premium Markdown: a name with a pipe/newline must not add columns or split a
  table row.
"""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_flowchart_mermaid
from otm_report_premium.render_markdown import _md_cell, _md_table

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


def test_mermaid_label_neutralizes_statement_injection() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base_line_count = len(export_flowchart_mermaid(doc).splitlines())

    doc.components[0] = doc.components[0].model_copy(update={"name": 'a"]\n    evil["pwned'})
    doc.data_flows[0] = doc.data_flows[0].model_copy(update={"name": "lab|el\n    x --> y"})
    out = export_flowchart_mermaid(doc)

    # No extra lines: the hostile newline was flattened, not turned into a statement.
    assert len(out.splitlines()) == base_line_count
    # The injected node fragment never appears at the start of its own line.
    assert "\n    evil[" not in out
    # The edge-label terminator `|` is neutralized.
    assert "lab|el" not in out


def test_md_cell_escapes_pipe_and_flattens_newlines() -> None:
    assert _md_cell("a|b") == r"a\|b"
    assert _md_cell("line1\nline2") == "line1 line2"
    assert _md_cell("c:\\path") == "c:\\\\path"


def test_md_table_row_stays_single_row_with_hostile_cell() -> None:
    out = _md_table(["H1", "H2"], [["x|y\ninjected | row", "ok"]], "empty")
    pipe_lines = [ln for ln in out.splitlines() if ln.startswith("|") and "---" not in ln]
    # header + exactly one data row (the newline did not create a second row)
    assert len(pipe_lines) == 2
    data_row = pipe_lines[1]
    assert data_row.count(" | ") == 1  # exactly two columns
