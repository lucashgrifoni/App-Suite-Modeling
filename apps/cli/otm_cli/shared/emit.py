"""Write files and JSON payloads (no Rich/Typer)."""

from __future__ import annotations

import json
import os
import secrets
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from otm_cli.shared.errors import CliUserError

#: Fixed-length temp name (`.otm` + 8 random chars + `.part` = 17), deliberately independent of
#: the destination filename: deriving it from `output.name` would push a destination that is
#: already close to the Windows MAX_PATH limit over the edge and fail a write that used to work.
_TMP_PREFIX = ".otm"
_TMP_SUFFIX = ".part"

#: How many random temp names to draw before giving up. Each name carries 32 bits of entropy, so
#: eight collisions in a row is not a scenario — the bound exists so the loop is *bounded*, which
#: `tempfile.mkstemp` is not (see `_create_temp_sibling`).
_TMP_ATTEMPTS = 8

#: `O_EXCL` is what makes the temp name ours alone; `O_NOFOLLOW`/`O_BINARY` only exist on some
#: platforms, so they are resolved at import time instead of branching per call.
_TMP_OPEN_FLAGS = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)

_PERMISSION_NEXT_STEP = "check file/directory permissions or close any process holding the file."
_UNWRITABLE_NEXT_STEP = "check the file name, the path length, and that the destination is a writable location."
_DIRECTORY_DENIED_NEXT_STEP = "grant write permission on that directory, or choose another destination."
_IS_A_DIRECTORY_NEXT_STEP = "point the output at a file inside it (e.g. `{path}/report.md`), not at the directory."


def _parent_of(output: Path) -> Path:
    return output.parent if str(output.parent) else Path(".")


def _is_same_file(output: Path, source: Path) -> bool:
    """`samefile`, not string equality: it settles `./m.yaml` vs `m.yaml`, case and short names.

    A destination that does not exist yet cannot be one of the inputs, and `samefile` reports that
    by raising — which is the answer "no", not a failure worth surfacing.
    """
    try:
        return output.samefile(source)
    except OSError:
        return False


def directory_destination_error(output: Path) -> CliUserError:
    """One wording for "you named a folder where a file goes", shared with `otm init`."""
    return CliUserError(
        exit_code=1,
        failed=f"cannot write to `{output}`.",
        cause=f"the destination is an existing directory: {output}",
        next_step=_IS_A_DIRECTORY_NEXT_STEP.format(path=output),
    )


def input_paths(*candidates: Path | None) -> tuple[Path, ...]:
    """Drop the optional inputs the caller did not pass, so `sources=` stays a one-liner."""
    return tuple(p for p in candidates if p is not None)


def _require_output_is_not_a_source(output: Path, sources: Sequence[Path]) -> None:
    """Refuse to write the artifact over a file the command just read.

    `otm analyze m.otm.yaml --json-out m.otm.yaml` replaced a 5 KB hand-authored, git-versioned
    model with a 100 KB `AnalysisResult` dump, printed a success message and exited 0 — no
    warning, no confirmation, no backup. `otm export -o` and `otm report -o` did the same. The
    product positions the `.otm.yaml` as the source of truth and `otm init` already refuses this
    class of overwrite ("without --force the file is not overwritten"), so the convention exists;
    it just was not applied where the destination is an *input* rather than a previous artifact.
    """
    for source in sources:
        if _is_same_file(output, source):
            raise CliUserError(
                exit_code=1,
                failed=f"refusing to overwrite the input file `{output}`.",
                cause=(
                    "the output path is a file this command just read; writing the generated "
                    "artifact there would destroy the source."
                ),
                next_step="write the output to a different path.",
            )


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
    if output.is_dir():
        # `-o build/` (an output *folder* where the tool wants an output *file*) used to surface
        # as `os.replace` raising WinError 5, which the mapper below reads as "permission denied"
        # and blames a lock nobody is holding — pointing the user at the wrong cause entirely.
        raise directory_destination_error(output)


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


def _temp_creation_failure(output: Path, parent: Path, error: OSError) -> CliUserError:
    """Blame the directory, and never quote the internal `.part` name the user never typed."""
    if isinstance(error, PermissionError):
        return CliUserError(
            exit_code=1,
            failed=f"cannot write to `{output}`.",
            cause=f"permission denied: the directory `{parent}` does not allow creating files.",
            next_step=_DIRECTORY_DENIED_NEXT_STEP,
        )
    return _write_failure(output, error)


def _create_temp_sibling(parent: Path) -> Path:
    """Claim a `.part` name next to the destination, in a *bounded* number of attempts.

    This replaces `tempfile.mkstemp`, which cannot be used here. On Windows CPython's
    `_mkstemp_inner` treats **every** `PermissionError` as a name collision as long as
    `os.access(dir, os.W_OK)` says the directory is writable — and on Windows `os.access` only
    inspects the read-only attribute and ignores ACLs, so it answers `True` for a directory whose
    ACL denies file creation (`C:\\Program Files` for a non-elevated user, or any `icacls /deny`
    target). `mkstemp` then retries up to `tempfile.TMP_MAX` — 2_147_483_647 — times: every `otm`
    command that writes a file emitted not one byte and never exited, which in CI blocks the job
    until its timeout. A bounded loop lets the `PermissionError` out on the first attempt, where
    the caller turns it into the same one-line error every other unwritable destination gives.
    """
    for _ in range(_TMP_ATTEMPTS):
        candidate = parent / f"{_TMP_PREFIX}{secrets.token_hex(4)}{_TMP_SUFFIX}"
        try:
            handle = os.open(candidate, _TMP_OPEN_FLAGS, 0o600)
        except FileExistsError:  # a genuine name collision: draw another name
            continue
        os.close(handle)
        return candidate
    raise FileExistsError(f"no free temporary name in `{parent}` after {_TMP_ATTEMPTS} attempts.")


def _write_atomically(output: Path, write_payload: Callable[[Path], object], sources: Sequence[Path] = ()) -> None:
    """Fill a sibling temp file, then replace the destination in one step.

    `Path.write_text`/`write_bytes` truncate the destination *before* streaming the content into
    it. Interrupt a run inside that window — Ctrl-C, a cancelled CI job — and the previous, valid
    artifact is already gone and a 0-byte file stands where the next step expects a report. The
    temp file shares the destination's directory so `os.replace` stays a same-volume rename, which
    is atomic: the destination only ever holds the old artifact or a complete new one.
    """
    _require_output_is_not_a_source(output, sources)
    _require_writable_parent(output)
    parent = _parent_of(output)
    try:
        temp = _create_temp_sibling(parent)
    except OSError as e:
        raise _temp_creation_failure(output, parent, e) from e
    try:
        write_payload(temp)
        os.replace(temp, output)
    except OSError as e:
        temp.unlink(missing_ok=True)
        raise _write_failure(output, e) from e


def write_text_file(*, content: str, output: Path, sources: Sequence[Path] = ()) -> None:
    """`sources` are the input files this artifact was derived from; the write refuses to hit one."""
    _write_atomically(output, lambda temp: temp.write_text(content, encoding="utf-8"), sources)


def write_bytes_file(*, content: bytes, output: Path, sources: Sequence[Path] = ()) -> None:
    """Binary sibling of `write_text_file` — same guards, same `CliUserError` contract.

    Exists so the PDF report cannot skip the pre-check the way it used to: calling
    `Path.write_bytes` directly turned a missing `-o` parent into a raw `FileNotFoundError`
    traceback while every other output path produced the one-line actionable error.
    """
    _write_atomically(output, lambda temp: temp.write_bytes(content), sources)


def write_json_file(*, payload: dict[str, Any], output: Path, sources: Sequence[Path] = ()) -> None:
    write_text_file(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        output=output,
        sources=sources,
    )
