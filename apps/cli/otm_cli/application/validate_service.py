"""Use case: validate an OTM document."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import ThreatModelDocument

from otm_cli.shared.document_loader import load_otm_document


def run_validate(path: Path) -> ThreatModelDocument:
    return load_otm_document(
        path,
        failed=f"validation of `{path}`.",
        validation_next_step="fix the fields listed below and run `otm validate` again.",
        runtime_next_step="confirm the path, YAML, and file permissions.",
    )
