"""Use case: export document as YAML/JSON/Markdown text."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import dump_document_to_yaml
from otm_exporters import export_document_json, export_document_markdown

from otm_cli.shared.document_loader import load_otm_document
from otm_cli.shared.enums import ExportFormat


def run_export(path: Path, *, export_format: ExportFormat) -> str:
    doc = load_otm_document(
        path,
        failed=f"export of `{path}`.",
        validation_next_step="run `otm validate` and fix errors before exporting.",
        runtime_next_step="confirm the path and that the file can be read.",
    )
    if export_format == ExportFormat.yaml:
        return dump_document_to_yaml(doc)
    if export_format == ExportFormat.json:
        return export_document_json(doc)
    return export_document_markdown(doc)
