"""Use case: model quality pre-check."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema.enums import ThreatModelMethodology
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_threat_engine.methodology_completeness import assess_methodology_completeness

from otm_cli.shared.document_loader import load_otm_document
from otm_cli.shared.enums import MethodologyOption


def run_precheck(
    path: Path,
    *,
    methodology: MethodologyOption | None,
) -> dict:
    doc = load_otm_document(
        path,
        failed=f"pre-check of `{path}`.",
        validation_next_step="run `otm validate` and fix errors before pre-check.",
        runtime_next_step="confirm the file path and YAML format.",
    )
    chosen = doc.model_info.methodology
    if methodology is not None:
        chosen = ThreatModelMethodology(methodology.value)
    pre = assess_model_precheck(doc)
    mc = assess_methodology_completeness(doc, chosen)
    return {
        "precheck": pre.model_dump(mode="json"),
        "methodology_completeness": mc.model_dump(mode="json"),
    }
