"""Use case: remediation backlog."""

from __future__ import annotations

import json
from pathlib import Path

from otm_exporters import export_remediation_backlog_json, export_remediation_backlog_markdown
from otm_threat_engine import AnalysisResult, analyze_document, build_remediation_backlog
from pydantic import ValidationError

from otm_cli.application.analysis_match import require_analysis_matches_document
from otm_cli.io_util import format_validation_error
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.enums import BacklogFormat
from otm_cli.shared.errors import CliUserError


def _load_analysis_json(path: Path) -> AnalysisResult:
    """Read an `AnalysisResult` the way every other JSON reader in the CLI already does.

    The guard used to be `except json.JSONDecodeError` alone, so the three most ordinary
    failures on this path — the file is missing, the path is a directory, the file was saved in
    cp1252 — escaped as raw tracebacks. The YAML branch of this same command handled all three
    cleanly, and this is the path a CI job lands on after an interrupted `otm analyze --json-out`.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    # UnicodeDecodeError sits with the read errors, not the JSON ones: it comes out of
    # `read_text`, so the file was never decoded and the JSON was never seen. It is a ValueError,
    # not an OSError, which is how it escaped both handlers and reached the user as a traceback.
    except (OSError, UnicodeDecodeError) as e:
        raise CliUserError(
            exit_code=1,
            failed=f"reading `{path}`.",
            cause=str(e),
            next_step="confirm the path points at an existing, UTF-8 encoded analysis JSON file.",
        ) from e
    except ValueError as e:
        raise CliUserError(
            exit_code=1,
            failed="invalid JSON.",
            cause=str(e),
            next_step="confirm the analysis file.",
        ) from e
    try:
        return AnalysisResult.model_validate(raw)
    except ValidationError as e:
        raise CliUserError(
            exit_code=1,
            failed="not a valid AnalysisResult.",
            cause=str(e),
            next_step="fix the JSON or regenerate with `otm analyze --json-out`.",
            validation_detail=format_validation_error(e),
        ) from e


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
        result = _load_analysis_json(path)
        if document:
            doc = load_otm_document(
                document,
                failed=f"reading document `{document}`.",
                validation_next_step="run `otm validate`.",
                runtime_next_step="confirm the YAML path.",
            )
            # `-d` only resolves component names, which is exactly why a foreign model went
            # unnoticed: the backlog kept the analysis's title and threats and relabelled them
            # with another system's component names.
            require_analysis_matches_document(doc, result, flag="--document")
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
