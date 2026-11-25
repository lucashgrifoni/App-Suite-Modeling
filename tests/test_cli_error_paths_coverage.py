"""Coverage — CLI command error branches (exit_on_cli_error) and root help."""

from __future__ import annotations

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


_BAD = "definitely_missing_file.otm.yaml"


@pytest.mark.parametrize(
    "argv",
    [
        ["recommend-methodology", _BAD],
        ["export", _BAD, "-f", "json"],
        ["diagram", _BAD],
        ["backlog", _BAD],
        ["report", _BAD],
        ["precheck", _BAD],
        ["analyze", _BAD],
        ["validate", _BAD],
    ],
)
def test_command_errors_on_missing_file(runner: CliRunner, argv: list[str]) -> None:
    r = runner.invoke(app, argv)
    assert r.exit_code != 0


def test_diff_analysis_errors_on_missing_files(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff-analysis", _BAD, "also_missing.json"])
    assert r.exit_code != 0


def test_root_no_command_shows_help(runner: CliRunner) -> None:
    r = runner.invoke(app, [])
    # no subcommand -> help/usage, non-crash
    out = (r.stdout or "") + (r.stderr or "")
    assert "Usage" in out or "Commands" in out or r.exit_code in (0, 2)
