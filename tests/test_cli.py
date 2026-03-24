"""Testes da CLI (Typer) — fluxos principais."""

from __future__ import annotations

from pathlib import Path
import json

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_validate_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["validate", str(_MINIMAL)])
    assert r.exit_code == 0
    out = r.stdout + (r.stderr or "")
    assert "Válido" in out


def test_validate_missing_file(runner: CliRunner) -> None:
    """Typer/Click reports missing file."""
    r = runner.invoke(app, ["validate", "nao_existe.otm.yaml"])
    assert r.exit_code != 0


def test_analyze_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", str(_MINIMAL)])
    assert r.exit_code == 0


def test_export_json_stdout(runner: CliRunner) -> None:
    r = runner.invoke(app, ["export", str(_MINIMAL), "--format", "json"])
    assert r.exit_code == 0
    assert '"title"' in r.stdout


def test_diagram_mermaid(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diagram", str(_MINIMAL)])
    assert r.exit_code == 0
    assert "flowchart" in r.stdout


def test_init_creates_file(tmp_path: Path, runner: CliRunner) -> None:
    out = tmp_path / "x.otm.yaml"
    r = runner.invoke(app, ["init", str(out)])
    assert r.exit_code == 0
    assert out.is_file()
    r2 = runner.invoke(app, ["validate", str(out)])
    assert r2.exit_code == 0


def test_version(runner: CliRunner) -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    out = (r.stdout or "") + (r.stderr or "")
    assert "otm" in out.lower() or "open threat" in out.lower()


def test_analyze_with_methodology_option(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", str(_MINIMAL), "--methodology", "nist_data_centric"])
    assert r.exit_code == 0
    out = (r.stdout or "") + (r.stderr or "")
    assert "Metodologia: nist_data_centric" in out


def test_analyze_json_out_contract_stable(tmp_path: Path, runner: CliRunner) -> None:
    out_file = tmp_path / "analysis.json"
    r = runner.invoke(
        app,
        ["analyze", str(_MINIMAL), "--methodology", "stride", "--json-out", str(out_file)],
    )
    assert r.exit_code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "methodology" in payload
    assert "heuristic_threats" in payload
    assert "summary" in payload
    assert "methodology_insights" in payload
    assert "framework_ref_counts_by_catalog" in payload["summary"]
