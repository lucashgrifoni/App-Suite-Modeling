"""Round-5 CLI contract repairs: a closed pipe, a device path, and two wrong help lines.

* `otm templates 2>&1 | head` exited **120** — Python's "failed to flush sys.stdout at interpreter
  shutdown" — so any `set -o pipefail` script that pages otm output failed, over a pipe the
  operator closed on purpose. The stdout data paths (`otm export -f json | head`) already returned
  0 whenever their output fit the buffer, so the CLI disagreed with itself.
* `otm validate CON` never returned. On Windows the reserved names resolve to a character device
  and opening `CON` blocks on console input; the same hang hit `analyze`, `precheck`, `export`,
  `diagram`, `diff` and `explain`. A hang is a worse failure mode than an error: in CI it holds a
  runner until the job-level timeout.
* `otm diff --help` and `otm diff-analysis --help` both promised "2 bad flag value", but an
  out-of-range `--fail-on` exits 1 by design (`shared/gate.py` scopes 2 to Typer/Click parsing).
  `docs/CI_AND_SECURITY_EVIDENCE.md` agrees with the code, so the help text was the wrong artifact.

The pipe cases run as real subprocesses. A closed pipe is an operating-system state; a stubbed
stream would assert the fix against a mock of the thing that was broken.
"""

from __future__ import annotations

import errno
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_cli.io_util import refuse_character_device
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

_CHILD = "import sys; sys.argv={argv!r}; from otm_cli.main import main; main()"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _run_and_close_the_pipe(argv: list[str], *, lines_to_read: int = 1) -> int:
    """Start the command, read a little, close the reader — exactly what `head` does."""
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD.format(argv=argv)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(_ROOT),
    )
    assert child.stdout is not None
    for _ in range(lines_to_read):
        child.stdout.readline()
    child.stdout.close()
    return child.wait(timeout=120)


def _run_to_completion(argv: list[str]) -> int:
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD.format(argv=argv)],
        capture_output=True,
        cwd=str(_ROOT),
        timeout=120,
    )
    return completed.returncode


# --- the closed pipe -------------------------------------------------------------------------


@pytest.mark.parametrize("command", [["templates"], ["templates", "list"], ["packs"]])
def test_a_reader_that_walks_away_is_not_a_failure(command: list[str]) -> None:
    assert _run_and_close_the_pipe(["otm", *command]) == 0


def test_a_tripped_gate_never_reports_success_through_a_closed_pipe() -> None:
    """The direction that matters more: a broken pipe must not turn a verdict into a green build.

    Not `== 3`. Typer's own handler converts a lost pipe into exit 1 before this CLI's `main` is
    reached, and 1 is a documented non-zero ("the command could not produce a verdict"), so a CI
    script that reads anything but 0 as failure is still correct. What must never happen is the
    obvious naive fix — answering 0 on a broken pipe unconditionally — which would hand a tripped
    security gate a passing exit code.
    """
    argv = ["otm", "diff", str(_SAAS), str(_MINIMAL), "--fail-on", "low"]

    assert _run_and_close_the_pipe(argv, lines_to_read=2) != 0


def test_the_verdict_survives_a_stderr_that_cannot_be_written() -> None:
    """The ordering fix, at the layer that owns it.

    The report used to be written before the code was computed, so a write that failed took the
    verdict with it. Exercised directly rather than through a pipe race: the property is that
    losing the report cannot lose the code.
    """
    import io

    from otm_cli.shared.gate import report_gate_verdict
    from otm_threat_engine.gate import GatePolicy, evaluate_gate

    class _DeadStream(io.TextIOBase):
        def write(self, _text: str) -> int:
            raise OSError(errno.EINVAL, "Invalid argument")

    policy = GatePolicy(fail_on="low", fail_on_risk_increase=False)
    tripped = evaluate_gate(_tripping_diff(), policy)
    assert tripped.tripped, "fixture premise: this diff must trip the gate"

    real_stderr, sys.stderr = sys.stderr, _DeadStream()
    try:
        code = report_gate_verdict(tripped)
    finally:
        sys.stderr = real_stderr

    assert code == 3


def _tripping_diff() -> object:
    """A real analysis delta between the two shipped models, via the same service the CLI uses."""
    from otm_cli.application.diff_service import run_model_diff

    _payload, _json, _md, _panel, analysis_diff = run_model_diff(
        _SAAS,
        _MINIMAL,
        with_analysis=True,
        pack=None,
        fmt=None,
        summary_only=False,
        methodology=None,
        auto_methodology=False,
        rules=None,
    )
    assert analysis_diff is not None  # fixture premise
    return analysis_diff


def test_the_same_gate_reports_three_without_a_pipe() -> None:
    """Control for the test above: 3 is the code the command produces on its own."""
    assert _run_to_completion(["otm", "diff", str(_SAAS), str(_MINIMAL), "--fail-on", "low"]) == 3


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["otm", "templates"], 0),
        (["otm", "templates", "--nope"], 2),
        (["otm", "validate", "does-not-exist.otm.yaml"], 1),
        (["otm", "validate", str(_MINIMAL)], 0),
    ],
)
def test_the_ordinary_exit_codes_are_untouched(argv: list[str], expected: int) -> None:
    """The whole exit-code surface still behaves, now that `main` routes every code."""
    assert _run_to_completion(argv) == expected


# --- the device path -------------------------------------------------------------------------


def test_the_guard_refuses_a_character_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Asserted through a faked stat so the contract holds on every platform, not only Windows."""
    target = tmp_path / "CON"
    target.write_text("model: {}", encoding="utf-8")
    real_stat = os.stat

    def _as_device(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        fields = list(result)
        fields[stat.ST_MODE] = (result.st_mode & ~stat.S_IFMT(result.st_mode)) | stat.S_IFCHR
        return os.stat_result(fields)

    monkeypatch.setattr(os, "stat", _as_device)

    with pytest.raises(OSError) as excinfo:
        refuse_character_device(target)

    assert excinfo.value.errno == errno.EINVAL


def test_the_guard_accepts_an_ordinary_file() -> None:
    """The over-refusal direction: every shipped model must pass straight through."""
    assert refuse_character_device(_MINIMAL) is None


def test_the_guard_accepts_a_path_that_does_not_exist() -> None:
    """Absence is the reader's error to report, in the reader's own words."""
    assert refuse_character_device(_ROOT / "no-such-model.otm.yaml") is None


@pytest.mark.skipif(os.name != "nt", reason="`CON` only names a device on Windows")
@pytest.mark.parametrize("command", ["validate", "analyze", "precheck", "export", "diagram", "explain"])
def test_a_windows_reserved_name_errors_instead_of_hanging(command: str) -> None:
    """The reported hang, on the platform that has it, through the real binary."""
    assert _run_to_completion(["otm", command, "CON"]) == 1


# --- the help text ---------------------------------------------------------------------------


def _help(runner: CliRunner, command: str) -> str:
    """Help text with the terminal's line wrapping collapsed, so assertions read as sentences."""
    return " ".join(_out(runner.invoke(app, [command, "--help"])).split())


@pytest.mark.parametrize("command", ["diff", "diff-analysis"])
def test_the_help_no_longer_promises_exit_two_for_a_bad_fail_on(runner: CliRunner, command: str) -> None:
    text = _help(runner, command)

    assert "2 bad flag value" not in text
    assert "`--fail-on` value" in text


@pytest.mark.parametrize("command", ["diff", "diff-analysis"])
def test_the_help_still_documents_all_four_codes(runner: CliRunner, command: str) -> None:
    text = _help(runner, command)

    for code in ("0 no gate trip", "1 usage error", "2 parsing error", "3 gate tripped"):
        assert code in text, text


def test_an_out_of_range_fail_on_exits_one_on_diff(runner: CliRunner) -> None:
    """The behaviour the help now describes, unchanged — the code was the correct artifact."""
    result = runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--fail-on", "bogus"])

    assert result.exit_code == 1
    assert "invalid `--fail-on` value" in _out(result)


def test_a_genuine_enum_violation_still_exits_two(runner: CliRunner) -> None:
    """The distinction the help draws has to be real on both sides of the line."""
    result = runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "-f", "xml"])

    assert result.exit_code == 2
