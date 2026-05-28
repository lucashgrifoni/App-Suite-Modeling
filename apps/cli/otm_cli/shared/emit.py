"""Write files and JSON payloads (no Rich/Typer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from otm_cli.shared.errors import CliUserError


def _require_writable_parent(output: Path) -> None:
    parent = output.parent if str(output.parent) else Path(".")
    if not parent.exists():
        raise CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"parent directory does not exist: {parent}",
            next_step=f"create the directory first (e.g. `mkdir {parent}`) or choose an existing path.",
        )


def write_text_file(*, content: str, output: Path) -> None:
    _require_writable_parent(output)
    try:
        output.write_text(content, encoding="utf-8")
    except PermissionError as e:
        raise CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"permission denied: {e}",
            next_step="check file/directory permissions or close any process holding the file.",
        ) from e


def write_json_file(*, payload: dict[str, Any], output: Path) -> None:
    write_text_file(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        output=output,
    )
