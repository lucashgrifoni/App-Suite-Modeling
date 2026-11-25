"""Load canonical OTM documents with structured CLI errors."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import ThreatModelDocument
from pydantic import ValidationError

from otm_cli.io_util import format_validation_error, load_doc
from otm_cli.shared.errors import CliUserError

_SCHEMA_INVALID = "the document is not valid for the canonical schema."


def load_otm_document(
    path: Path,
    *,
    failed: str,
    validation_next_step: str,
    runtime_next_step: str,
    source_lines: dict[tuple[str, str], int] | None = None,
) -> ThreatModelDocument:
    try:
        return load_doc(path) if source_lines is None else load_doc(path, source_lines=source_lines)
    except ValidationError as e:
        raise CliUserError(
            exit_code=1,
            failed=failed,
            cause=_SCHEMA_INVALID,
            next_step=validation_next_step,
            validation_detail=format_validation_error(e),
        ) from e
    except RuntimeError as e:
        raise CliUserError(
            exit_code=1,
            failed=failed,
            cause=str(e),
            next_step=runtime_next_step,
        ) from e


def load_pack_or_raise(*, pack_id: str, failed: str, next_step: str):
    from otm_industry_packs.loader import load_pack

    try:
        return load_pack(pack_id)
    except FileNotFoundError as e:
        raise CliUserError(
            exit_code=1,
            failed=failed,
            cause=f"unknown pack `{pack_id}`.",
            next_step=next_step,
        ) from e
