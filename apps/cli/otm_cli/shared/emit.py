"""Write files and JSON payloads (no Rich/Typer)."""

from __future__ import annotations

import json
import os
import secrets
import time
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


def _os_error_detail(error: OSError) -> str:
    """The operating system's reason, with the paths left out.

    `str(OSError)` appends `filename` and `filename2`, and for a failed `os.replace` those are the
    internal temp name and the destination: the user read `permission denied: [WinError 5] Acesso
    negado: '.otm9fe6f00c.part' -> 'ro.json'` and went looking for a `.part` file they never typed
    and which no longer exists. `_temp_creation_failure` states that intent — "never quote the
    internal `.part` name" — and honours it; this is the other half of the same rule. The error
    code survives because it is what a support thread actually needs, and the destination is
    already named in the `failed` line.
    """
    winerror = getattr(error, "winerror", None)
    code = f"WinError {winerror}" if winerror is not None else (f"errno {error.errno}" if error.errno else "")
    reason = error.strerror or str(error)
    return f"[{code}] {reason}" if code else reason


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
            cause=f"permission denied: {_os_error_detail(error)}",
            next_step=_PERMISSION_NEXT_STEP,
        )
    return CliUserError(
        exit_code=1,
        failed=f"cannot write to `{output}`.",
        cause=f"the destination is not writable: {_os_error_detail(error)}",
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


#: How old a `.part` sibling must be before a later run reclaims it, in seconds.
#:
#: The whole point of the delay: a `.part` file that appeared a moment ago is **indistinguishable**
#: from the live temp of another `otm` writing into the same directory right now, and deleting
#: that one would break a run that was going to succeed — trading a disk-hygiene problem for a
#: corrupted write. An hour is orders of magnitude beyond any write this tool performs (a 32 MB
#: artifact spends tens of milliseconds in that state) and still reclaims the orphan on the next
#: run. It deliberately does not reclaim a fresh orphan; nothing safe can.
_STALE_TEMP_AGE_SECONDS = 3600.0

#: `.otm` + 8 hex + `.part`. Matched exactly so the sweep can never touch a user's own file that
#: happens to end in `.part`.
_TMP_NAME_LENGTH = len(_TMP_PREFIX) + 8 + len(_TMP_SUFFIX)


def _is_reclaimable_temp(entry: os.DirEntry[str], now: float) -> bool:
    name = entry.name
    if len(name) != _TMP_NAME_LENGTH or not name.startswith(_TMP_PREFIX) or not name.endswith(_TMP_SUFFIX):
        return False
    if not all(c in "0123456789abcdef" for c in name[len(_TMP_PREFIX) : -len(_TMP_SUFFIX)]):
        return False
    try:
        return entry.is_file() and (now - entry.stat().st_mtime) > _STALE_TEMP_AGE_SECONDS
    except OSError:  # vanished between listing and stat — someone else already reclaimed it
        return False


def _sweep_stale_temps(parent: Path) -> None:
    """Reclaim `.part` siblings left behind by a kill this process could not observe.

    `_write_atomically` cleans up in a `finally`, which covers Ctrl-C and a cancelled job but by
    construction cannot run on `SIGKILL` / `Stop-Process -Force`. Those runs left an
    `.otm<hex>.part` of up to the full payload size next to the destination and nothing ever
    removed it — a CI job killed by its timeout leaves a multi-megabyte file that the next
    artifact-upload glob happily collects.

    Best effort throughout: a directory that cannot be listed, or a file that cannot be removed
    because something else holds it, must never turn into the error the user sees for a write
    that is otherwise fine.
    """
    now = time.time()
    try:
        with os.scandir(parent) as entries:
            stale = [entry.path for entry in entries if _is_reclaimable_temp(entry, now)]
    except OSError:
        return
    for path in stale:
        _discard_temp(Path(path))


def _discard_temp(temp: Path) -> None:
    """Remove the temp file, and never let the removal become the error the user sees.

    This runs on the way out of a failed or interrupted write, where an exception is usually
    already propagating. An `OSError` raised here — a scanner or indexer holding the file open for
    a moment is the realistic case on Windows — would replace that exception with a raw traceback
    naming a `.part` path the user never typed, against the "user error, no stack trace" contract
    in `docs/features/CLI.md`. Failing to delete leaves the very file this is meant to remove, but
    that is a hygiene problem; masking the real failure is a correctness one.
    """
    try:
        temp.unlink(missing_ok=True)
    except OSError:
        pass


def _write_atomically(output: Path, write_payload: Callable[[Path], object], sources: Sequence[Path] = ()) -> None:
    """Fill a sibling temp file, then replace the destination in one step.

    `Path.write_text`/`write_bytes` truncate the destination *before* streaming the content into
    it. Interrupt a run inside that window — Ctrl-C, a cancelled CI job — and the previous, valid
    artifact is already gone and a 0-byte file stands where the next step expects a report. The
    temp file shares the destination's directory so `os.replace` stays a same-volume rename, which
    is atomic: the destination only ever holds the old artifact or a complete new one.

    Cleanup is a `finally`, not an `except OSError`, because the interruption this function exists
    for does not arrive as an `OSError`. Ctrl-C raises `KeyboardInterrupt` and a cancelled job can
    raise `SystemExit`; both are `BaseException`, both walked past an `except OSError` clause, and
    both left a hidden `.otm<hex>.part` — up to the full payload size — in the user's working
    directory, which nothing ever swept and which an artifact-upload glob in CI happily collects.
    After a successful `os.replace` the temp name no longer exists, so the unlink is a no-op and
    the success path is unchanged. Only a kill the process cannot observe (`SIGKILL`,
    `Stop-Process -Force`) can still orphan a temp; no in-process cleanup can cover that one, so
    it is reclaimed from the outside instead — `_sweep_stale_temps` runs before this write claims
    its own name and removes the `.part` siblings old enough to be nobody's.
    """
    _require_output_is_not_a_source(output, sources)
    _require_writable_parent(output)
    parent = _parent_of(output)
    _sweep_stale_temps(parent)
    try:
        temp = _create_temp_sibling(parent)
    except OSError as e:
        raise _temp_creation_failure(output, parent, e) from e
    try:
        write_payload(temp)
        os.replace(temp, output)
    except OSError as e:
        raise _write_failure(output, e) from e
    finally:
        _discard_temp(temp)


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
