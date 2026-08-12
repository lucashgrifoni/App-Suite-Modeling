"""Write files and JSON payloads (no Rich/Typer)."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from otm_cli.shared.errors import CliUserError

#: Fixed-length temp name (`.otm` + 8 random chars + `.part` = 17), deliberately independent of
#: the destination filename: deriving it from `output.name` would push a destination that is
#: already close to the Windows MAX_PATH limit over the edge and fail a write that used to work.
_TMP_PREFIX = ".otm"
_TMP_SUFFIX = ".part"

_PERMISSION_NEXT_STEP = "check file/directory permissions or close any process holding the file."
_UNWRITABLE_NEXT_STEP = "check the file name, the path length, and that the destination is a writable location."


def _parent_of(output: Path) -> Path:
    return output.parent if str(output.parent) else Path(".")


def _require_writable_parent(output: Path) -> None:
    parent = _parent_of(output)
    if not parent.exists():
        raise CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"parent directory does not exist: {parent}",
            next_step=f"create the directory first (e.g. `mkdir {parent}`) or choose an existing path.",
        )
    if not parent.is_dir():
        # `exists()` alone said yes for `-o model.otm.yaml/x.json`, so the guard passed and the
        # write then died with a raw FileNotFoundError naming a path the user never typed.
        raise CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"not a directory: {parent}",
            next_step="point the output at a path inside a directory, not through an existing file.",
        )


def _write_failure(output: Path, error: OSError) -> CliUserError:
    """Every `OSError`, not only `PermissionError`.

    The guard used to catch `PermissionError` alone, so an illegal filename (`out?.json`), a path
    over MAX_PATH or a full disk escaped as a raw Rich traceback dumping the maintainer's absolute
    source paths — against the "user error, no stack trace" contract in `docs/features/CLI.md`.
    """
    if isinstance(error, PermissionError):
        return CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"permission denied: {error}",
            next_step=_PERMISSION_NEXT_STEP,
        )
    return CliUserError(
        exit_code=1,
        failed=f"cannot write to `{output}`.",
        cause=f"the destination is not writable: {error}",
        next_step=_UNWRITABLE_NEXT_STEP,
    )


def _write_atomically(output: Path, write_payload: Callable[[Path], object]) -> None:
    """Fill a sibling temp file, then replace the destination in one step.

    `Path.write_text`/`write_bytes` truncate the destination *before* streaming the content into
    it. Interrupt a run inside that window — Ctrl-C, a cancelled CI job — and the previous, valid
    artifact is already gone and a 0-byte file stands where the next step expects a report. The
    temp file shares the destination's directory so `os.replace` stays a same-volume rename, which
    is atomic: the destination only ever holds the old artifact or a complete new one.
    """
    _require_writable_parent(output)
    temp: Path | None = None
    try:
        handle, name = tempfile.mkstemp(dir=_parent_of(output), prefix=_TMP_PREFIX, suffix=_TMP_SUFFIX)
        os.close(handle)
        temp = Path(name)
        write_payload(temp)
        os.replace(temp, output)
    except OSError as e:
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise _write_failure(output, e) from e


def write_text_file(*, content: str, output: Path) -> None:
    _write_atomically(output, lambda temp: temp.write_text(content, encoding="utf-8"))


def write_bytes_file(*, content: bytes, output: Path) -> None:
    """Binary sibling of `write_text_file` — same guards, same `CliUserError` contract.

    Exists so the PDF report cannot skip the pre-check the way it used to: calling
    `Path.write_bytes` directly turned a missing `-o` parent into a raw `FileNotFoundError`
    traceback while every other output path produced the one-line actionable error.
    """
    _write_atomically(output, lambda temp: temp.write_bytes(content))


def write_json_file(*, payload: dict[str, Any], output: Path) -> None:
    write_text_file(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        output=output,
    )
