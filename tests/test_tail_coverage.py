"""Coverage — assorted tail branches (CLI options, service wrappers, exporters)."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document, build_remediation_backlog
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MODEL = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _analysis_json(runner: CliRunner, tmp_path: Path, name: str = "an.json") -> Path:
    out = tmp_path / name
    r = runner.invoke(app, ["analyze", str(_MODEL), "--json-out", str(out), "--quiet"])
    assert r.exit_code == 0
    return out


def test_precheck_json_out(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "pre.json"
    r = runner.invoke(app, ["precheck", str(_MODEL), "--json-out", str(out), "--methodology", "stride"])
    assert r.exit_code == 0
    assert out.is_file()


def test_report_with_pack_and_baseline(runner: CliRunner, tmp_path: Path) -> None:
    baseline = _analysis_json(runner, tmp_path, "base.json")
    out = tmp_path / "rep.md"
    r = runner.invoke(
        app,
        ["report", str(_MODEL), "--pack", "saas", "--level", "standard", "--baseline", str(baseline), "-o", str(out)],
    )
    assert r.exit_code == 0


def test_reporting_wrappers() -> None:
    from otm_cli.reporting import export_analysis_section_markdown, export_full_report_markdown

    doc = load_document_from_yaml_path(_MODEL)
    res = analyze_document(doc)
    assert export_analysis_section_markdown(res)
    assert export_full_report_markdown(doc, res)


def test_remediation_json_obj_and_str() -> None:
    from otm_exporters.remediation_json import export_remediation_backlog_json, export_remediation_backlog_obj

    doc = load_document_from_yaml_path(_MODEL)
    backlog = build_remediation_backlog(analyze_document(doc), doc)
    assert isinstance(export_remediation_backlog_obj(backlog), dict)
    assert export_remediation_backlog_json(backlog).startswith("{")
