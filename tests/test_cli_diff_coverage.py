"""CLI coverage — `otm diff` across formats, analysis, pack, summary, and errors.

Uses two structurally-different example models so the structural/semantic
listing branches in diff_service are exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_A = str(_ROOT / "examples" / "minimal.otm.yaml")
_B = str(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_diff_text_structural(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B])
    assert r.exit_code == 0
    out = r.stdout + (r.stderr or "")
    assert "added" in out or "removed" in out


def test_diff_with_analysis_text(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B, "--with-analysis"])
    assert r.exit_code == 0


def test_diff_with_analysis_and_pack(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B, "--with-analysis", "--pack", "saas"])
    assert r.exit_code == 0


def test_diff_format_json(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B, "--format", "json"])
    assert r.exit_code == 0
    json.loads(r.stdout)


def test_diff_format_markdown(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B, "--format", "markdown"])
    assert r.exit_code == 0
    assert "#" in r.stdout


def test_diff_summary_only(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", _A, _B, "--with-analysis", "--summary-only"])
    assert r.exit_code == 0


def test_diff_json_out_file(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "diff.json"
    r = runner.invoke(app, ["diff", _A, _B, "--json-out", str(out)])
    assert r.exit_code == 0
    assert out.is_file()
    json.loads(out.read_text(encoding="utf-8"))


def test_diff_bad_baseline_errors(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["diff", str(tmp_path / "nope.yaml"), _B])
    assert r.exit_code == 1
