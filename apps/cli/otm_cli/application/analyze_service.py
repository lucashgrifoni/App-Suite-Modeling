"""Use case: run the analysis engine."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine import AnalysisResult, analyze_document

from otm_cli.application.custom_rules_io import load_custom_rules_or_raise
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.enums import MethodologyOption


def run_analyze(
    path: Path,
    *,
    pack: str | None,
    methodology: MethodologyOption | None,
    auto_methodology: bool,
    rules: Path | None = None,
) -> AnalysisResult:
    doc = load_otm_document(
        path,
        failed=f"analysis of `{path}`.",
        validation_next_step="run `otm validate` and fix errors before analyzing.",
        runtime_next_step="confirm the file path and YAML format.",
    )
    pack_def = None
    if pack:
        pack_def = load_pack_or_raise(
            pack_id=pack,
            failed=f"loading pack `{pack}`.",
            next_step="run `otm packs` and use a listed ID.",
        )
    ruleset = load_custom_rules_or_raise(rules)

    return analyze_document(
        doc,
        pack=pack_def,
        methodology=methodology.value if methodology else None,
        auto_recommend=auto_methodology,
        custom_rules=ruleset,
    )
