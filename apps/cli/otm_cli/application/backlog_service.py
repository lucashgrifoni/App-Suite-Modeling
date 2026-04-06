"""Use case: remediation backlog."""

from __future__ import annotations

import json
from pathlib import Path

from otm_exporters import export_remediation_backlog_json, export_remediation_backlog_markdown
from otm_threat_engine import AnalysisResult, analyze_document, build_remediation_backlog
from pydantic import ValidationError

from otm_cli.io_util import format_validation_error
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.enums import BacklogFormat
from otm_cli.shared.errors import CliUserError


def run_backlog(
    path: Path,
    *,
    document: Path | None,
    pack: str | None,
    fmt: BacklogFormat,
    group_by: str | None,
) -> str:
    pack_def = None
    if pack:
        pack_def = load_pack_or_raise(
            pack_id=pack,
            failed=f"loading pack `{pack}`.",
            next_step="run `otm packs`.",
        )

    suf = path.suffix.lower()
    result: AnalysisResult
    doc = None

    if suf in (".yaml", ".yml"):
        doc = load_otm_document(
            path,
            failed=f"reading model `{path}`.",
            validation_next_step="run `otm validate`.",
            runtime_next_step="confirm the YAML path.",
        )
        result = analyze_document(doc, pack=pack_def)
    elif suf == ".json":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            result = AnalysisResult.model_validate(raw)
        except json.JSONDecodeError as e:
            raise CliUserError(
                exit_code=1,
                failed="invalid JSON.",
                cause=str(e),
                next_step="confirm the analysis file.",
            ) from e
        except ValidationError as e:
            raise CliUserError(
                exit_code=1,
                failed="not a valid AnalysisResult.",
                cause=str(e),
                next_step="fix the JSON or regenerate with `otm analyze --json-out`.",
                validation_detail=format_validation_error(e),
            ) from e
        if document:
            doc = load_otm_document(
                document,
                failed=f"reading document `{document}`.",
                validation_next_step="run `otm validate`.",
                runtime_next_step="confirm the YAML path.",
            )
    else:
        raise CliUserError(
            exit_code=1,
            failed="unsupported file extension.",
            cause="use .yaml/.yml (model) or .json (analysis).",
            next_step="run `otm backlog --help`.",
        )

    backlog = build_remediation_backlog(result, doc)
    if fmt == BacklogFormat.json:
        return export_remediation_backlog_json(backlog)
    return export_remediation_backlog_markdown(backlog, group_by=group_by)
