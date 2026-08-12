"""Every `otm` writer must fail like a CLI, on every command that has one.

`shared.emit` maps a missing parent directory and a denied write onto `CliUserError`, and each
command wraps its own write in the handler that renders that error and exits 1. Those handlers
were the least-tested lines in the CLI: `backlog`, `diagram`, `export`, `precheck`, `diff` and the
SARIF branch of `analyze` each had an untested `except`, so a regression there would have surfaced
to users as a raw traceback on a full disk, a read-only checkout or a mistyped `-o` path — and no
test would have noticed.

The contract asserted here is the same for all of them:
    exit code 1 · no traceback · a message naming the cause · and no half-written file left behind.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from typer.testing import CliRunner

_MINIMAL = str(Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml")

_OPENAPI_SPEC = """
openapi: 3.0.0
info:
  title: Orders API
  version: 1.0.0
paths:
  /orders:
    get:
      operationId: listOrders
"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich wraps to the terminal width; a wrapped message would fail for the wrong reason."""
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _spec(tmp_path: Path) -> Path:
    path = tmp_path / "orders.openapi.yaml"
    path.write_text(_OPENAPI_SPEC, encoding="utf-8")
    return path


# ------------------------------------------------- a missing parent directory, on every writer


@pytest.mark.parametrize(
    ("argv", "flag", "filename"),
    [
        (["backlog", _MINIMAL], "-o", "backlog.md"),
        (["diagram", _MINIMAL], "-o", "diagram.mmd"),
        (["export", _MINIMAL], "-o", "model.yaml"),
        (["precheck", _MINIMAL], "--json-out", "precheck.json"),
        (["diff", _MINIMAL, _MINIMAL], "--json-out", "diff.json"),
        (["analyze", _MINIMAL, "-q"], "--sarif-out", "analysis.sarif"),
    ],
    ids=["backlog", "diagram", "export", "precheck", "diff", "analyze-sarif"],
)
def test_writing_into_a_missing_directory_is_a_clean_cli_error(
    runner: CliRunner, tmp_path: Path, argv: list[str], flag: str, filename: str
) -> None:
    target = tmp_path / "nodir" / filename
    result = runner.invoke(app, [*argv, flag, str(target)])
    report = _out(result)
    assert result.exit_code == 1
    assert "parent directory does not exist" in report
    assert "Traceback" not in report
    assert not target.exists()


def test_import_draft_into_a_missing_directory_is_a_clean_cli_error(runner: CliRunner, tmp_path: Path) -> None:
    """`import` writes through its own helper, so it needs its own proof."""
    target = tmp_path / "nodir" / "draft.otm.yaml"
    result = runner.invoke(app, ["import", "openapi", str(_spec(tmp_path)), "-o", str(target)])
    report = _out(result)
    assert result.exit_code == 1
    assert "parent directory does not exist" in report
    assert not target.exists()


def test_import_explain_out_into_a_missing_directory_is_a_clean_cli_error(runner: CliRunner, tmp_path: Path) -> None:
    """The draft is written first; only the transparency JSON fails, and it must still exit 1."""
    draft = tmp_path / "draft.otm.yaml"
    explain = tmp_path / "nodir" / "inferences.json"
    result = runner.invoke(
        app, ["import", "openapi", str(_spec(tmp_path)), "-o", str(draft), "--explain-out", str(explain)]
    )
    report = _out(result)
    assert result.exit_code == 1
    assert "parent directory does not exist" in report
    assert not explain.exists()
    assert draft.is_file(), "the draft was already on disk and must not be rolled back silently"


# ------------------------------------------------- a denied write, mapped instead of raised


def test_a_denied_write_is_reported_not_raised(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read-only checkout or a file held open by another process must not print a traceback.

    The parent directory exists here, so the pre-check passes and the failure can only come from
    the write itself — which is exactly the branch a missing-directory test can never reach.
    """

    def _deny(self: Path, *args: object, **kwargs: object) -> int:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_text", _deny)
    target = tmp_path / "readonly.yaml"
    result = runner.invoke(app, ["export", _MINIMAL, "-o", str(target)])
    report = _out(result)
    assert result.exit_code == 1
    assert "permission denied" in report
    assert "Traceback" not in report


# ------------------------------------------------- the successful SARIF branch


def test_analyze_says_where_it_wrote_the_sarif(runner: CliRunner, tmp_path: Path) -> None:
    """Without `-q` the command must name the file; the SARIF branch only ever ran quiet."""
    target = tmp_path / "analysis.sarif"
    result = runner.invoke(app, ["analyze", _MINIMAL, "--sarif-out", str(target)])
    assert result.exit_code == 0
    assert "SARIF written to" in _out(result)

    sarif = json.loads(target.read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"


def test_analyze_quiet_writes_the_sarif_without_announcing_it(runner: CliRunner, tmp_path: Path) -> None:
    """`-q` is the CI mode: the artifact still lands, the chatter does not."""
    target = tmp_path / "quiet.sarif"
    result = runner.invoke(app, ["analyze", _MINIMAL, "-q", "--sarif-out", str(target)])
    assert result.exit_code == 0
    assert "SARIF written to" not in _out(result)
    assert target.is_file()
