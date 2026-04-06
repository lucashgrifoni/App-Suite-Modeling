"""Use case: recommend methodology."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine.methodologies import recommend_methodology

from otm_cli.shared.document_loader import load_otm_document


def run_recommend_methodology(path: Path):
    doc = load_otm_document(
        path,
        failed=f"methodology recommendation for `{path}`.",
        validation_next_step="run `otm validate` and fix the document.",
        runtime_next_step="confirm the path and YAML integrity.",
    )
    return recommend_methodology(doc)
