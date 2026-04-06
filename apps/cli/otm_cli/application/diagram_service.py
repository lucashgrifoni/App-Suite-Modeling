"""Use case: Mermaid flowchart."""

from __future__ import annotations

from pathlib import Path

from otm_diagram_engine import export_flowchart_mermaid

from otm_cli.shared.document_loader import load_otm_document


def run_diagram(path: Path) -> str:
    doc = load_otm_document(
        path,
        failed=f"diagram generation for `{path}`.",
        validation_next_step="run `otm validate` before generating the diagram.",
        runtime_next_step="confirm the file path and YAML.",
    )
    return export_flowchart_mermaid(doc)
