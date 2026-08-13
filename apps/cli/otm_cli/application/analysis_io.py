"""Read `AnalysisResult` from a JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from otm_threat_engine import AnalysisResult
from pydantic import ValidationError

from otm_cli.io_util import format_validation_error, refuse_character_device
from otm_cli.shared.errors import CliUserError

_SCHEMA_INVALID = "the document is not valid for the canonical schema."


def load_analysis_result_from_path(path: Path) -> AnalysisResult:
    try:
        refuse_character_device(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
    # ValueError, not JSONDecodeError: `read_text` runs first, and a cp1252/latin-1 file raises
    # UnicodeDecodeError — a sibling ValueError, not an OSError — which used to escape both
    # handlers and reach the user as a raw traceback.
    except (OSError, ValueError) as e:
        raise CliUserError(
            exit_code=1,
            failed=f"reading `{path}`.",
            cause=str(e),
            next_step="confirm the file is valid JSON (`otm analyze --json-out`).",
        ) from e
    try:
        return AnalysisResult.model_validate(raw)
    except ValidationError as e:
        raise CliUserError(
            exit_code=1,
            failed=f"AnalysisResult validation for `{path}`.",
            cause="incompatible structure.",
            next_step="regenerate with `otm analyze --json-out`.",
            validation_detail=format_validation_error(e),
        ) from e


def load_two_analysis_results(baseline: Path, revised: Path) -> tuple[AnalysisResult, AnalysisResult]:
    try:
        refuse_character_device(baseline)
        refuse_character_device(revised)
        b_obj = json.loads(baseline.read_text(encoding="utf-8"))
        r_obj = json.loads(revised.read_text(encoding="utf-8"))
    # See `load_analysis_result_from_path`: ValueError also covers the UnicodeDecodeError that
    # `read_text` raises on a non-UTF-8 analysis file.
    except (OSError, ValueError) as e:
        raise CliUserError(
            exit_code=1,
            failed=f"reading JSON at `{baseline}` / `{revised}`.",
            cause=str(e),
            next_step="confirm paths and that both files are valid JSON.",
        ) from e
    try:
        return AnalysisResult.model_validate(b_obj), AnalysisResult.model_validate(r_obj)
    except ValidationError as e:
        raise CliUserError(
            exit_code=1,
            failed="AnalysisResult validation.",
            cause=_SCHEMA_INVALID,
            next_step="regenerate with `otm analyze --json-out`.",
            validation_detail=format_validation_error(e),
        ) from e
