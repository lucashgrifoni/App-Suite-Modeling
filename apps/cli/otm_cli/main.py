"""Entry point for the `otm` command (console_scripts)."""

from __future__ import annotations

import errno
import os
import stat
import sys

# Ensure UTF-8 so that em-dash, bullets, arrows, accents and emojis render on
# legacy Windows consoles (CP850/CP1252) without mojibake or \uXXXX escapes.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

from otm_cli.cli import app as cli_app  # noqa: E402

#: Exit code when the consumer of a pipe walked away before the command finished writing.
#:
#: `otm templates 2>&1 | head` exited **120** — Python's "failed to flush sys.stdout at
#: interpreter shutdown" — which fails every `set -o pipefail` script that pages otm output, over
#: a pipe the operator closed on purpose. `head` and `less` are not error conditions, and the
#: stdout data paths (`otm export -f json | head`) already return 0 when they fit the buffer.
BROKEN_PIPE_EXIT_CODE = 0


#: Errnos a write can fail with once the reader of a pipe has gone. POSIX reports EPIPE and
#: CPython raises `BrokenPipeError`; Windows reports plain `OSError(EINVAL)` with no `winerror`
#: for the same event, which is why catching `BrokenPipeError` alone left `otm templates | head`
#: at 120 on the platform this tool is primarily used on.
_LOST_PIPE_ERRNOS = frozenset({errno.EPIPE, errno.EINVAL, errno.EBADF})


def _is_a_pipe(stream: object) -> bool:
    try:
        return stat.S_ISFIFO(os.fstat(stream.fileno()).st_mode)  # type: ignore[attr-defined]
    except (OSError, ValueError, AttributeError):
        return False


def _is_a_lost_pipe(error: OSError) -> bool:
    """Did the reader close the pipe, or is this an unrelated I/O failure?

    The distinction has to be drawn, because the two answers are opposite: a lost pipe is not a
    failure and a real one must keep its traceback and its non-zero exit. On Windows the type and
    the errno cannot draw it alone, so *where the output was going* does: this is only read as a
    lost pipe when stdout or stderr is actually a pipe. A failure writing to a console or to a
    redirected file is left to propagate exactly as before.
    """
    if isinstance(error, BrokenPipeError):
        return True
    if error.errno not in _LOST_PIPE_ERRNOS:
        return False
    return _is_a_pipe(sys.stdout) or _is_a_pipe(sys.stderr)


def _discard_output_streams() -> None:
    """Point stdout/stderr at the null device so the shutdown flush has nothing left to fail on.

    Handling the exception is not enough by itself: the interpreter flushes the buffered streams
    again on the way out, cannot report a failure at that point, and substitutes 120 for whatever
    code the command had decided.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    for stream in (sys.stdout, sys.stderr):
        try:
            os.dup2(devnull, stream.fileno())
        except (OSError, ValueError):
            # A stream someone replaced with an in-memory object has no descriptor to redirect,
            # and no descriptor is exactly the case that cannot fail at shutdown either.
            pass


def _exit_code_of(exit_request: SystemExit) -> int:
    if exit_request.code is None:
        return 0
    return exit_request.code if isinstance(exit_request.code, int) else 1


def main() -> None:
    # The command's own verdict, captured rather than left to propagate: a broken pipe during the
    # final flush must not overwrite it. A gate that tripped still says 3, even when the reader
    # walked away mid-report.
    code = 0
    try:
        try:
            cli_app()
        except SystemExit as e:  # Click's standalone mode exits through here.
            code = _exit_code_of(e)
        sys.stdout.flush()
        sys.stderr.flush()
    except OSError as e:
        if not _is_a_lost_pipe(e):
            raise
        _discard_output_streams()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
