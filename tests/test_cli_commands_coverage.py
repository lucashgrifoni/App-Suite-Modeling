"""CLI coverage — analyze/init/report/explain/backlog/diff-analysis/diagram/export/recommend/templates.

Drives the user-visible branches (formats, flags, error paths) through the Typer
app so the command + application + shared layers are exercised end to end.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = str(_ROOT / "examples" / "minimal.otm.yaml")
_SAAS = str(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")
_AI = str(_ROOT / "examples" / "plot4ai-calibration" / "otm-ai-003-agent-tools.otm.yaml")


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _analysis_json(runner: CliRunner, tmp_path: Path, model: str = _MINIMAL, name: str = "an.json") -> Path:
    out = tmp_path / name
    r = runner.invoke(app, ["analyze", model, "--json-out", str(out), "--quiet"])
    assert r.exit_code == 0
    assert out.is_file()
    return out


# --- analyze branches ---


def test_analyze_pack_line(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", _SAAS, "--pack", "saas"])
    assert r.exit_code == 0
    assert "Pack:" in (r.stdout + (r.stderr or ""))


def test_analyze_auto_methodology(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", _SAAS, "--auto-methodology"])
    assert r.exit_code == 0


def test_analyze_plot4ai_explain(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", _AI, "-m", "plot4ai", "--explain"])
    assert r.exit_code == 0


def test_analyze_json_out_quiet(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "a.json"
    r = runner.invoke(app, ["analyze", _MINIMAL, "--json-out", str(out), "--quiet"])
    assert r.exit_code == 0
    assert out.is_file()


def test_analyze_bad_path(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["analyze", str(tmp_path / "no.yaml")])
    assert r.exit_code == 1


# --- init ---


def test_init_list_templates(runner: CliRunner) -> None:
    r = runner.invoke(app, ["init", "--list-templates"])
    assert r.exit_code == 0
    assert "Templates" in (r.stdout + (r.stderr or ""))


def test_init_create_minimal(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "new.otm.yaml"
    r = runner.invoke(app, ["init", str(target)])
    assert r.exit_code == 0
    assert target.is_file()


def test_init_from_template(runner: CliRunner, tmp_path: Path) -> None:
    from otm_cli.application import templates_service as tmpl

    infos = tmpl.list_template_infos()
    assert infos, "expected embedded templates"
    tid = infos[0].id
    target = tmp_path / "from_tpl.otm.yaml"
    r = runner.invoke(app, ["init", str(target), "-t", tid])
    assert r.exit_code == 0
    assert target.is_file()


def test_init_existing_without_force_errors(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "exists.otm.yaml"
    target.write_text("x", encoding="utf-8")
    r = runner.invoke(app, ["init", str(target)])
    assert r.exit_code != 0


# --- report ---


def test_report_legacy_stdout(runner: CliRunner) -> None:
    r = runner.invoke(app, ["report", _MINIMAL])
    assert r.exit_code == 0
    assert "#" in r.stdout


def test_report_legacy_to_file(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "r.md"
    r = runner.invoke(app, ["report", _MINIMAL, "-o", str(out)])
    assert r.exit_code == 0
    assert out.is_file()


def test_report_premium_markdown(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "prem.md"
    r = runner.invoke(app, ["report", _SAAS, "--level", "executive", "-o", str(out), "--locale", "en"])
    assert r.exit_code == 0
    assert out.is_file()


def test_report_premium_with_analysis_json(runner: CliRunner, tmp_path: Path) -> None:
    aj = _analysis_json(runner, tmp_path, _SAAS, "saas_an.json")
    r = runner.invoke(app, ["report", _SAAS, "--level", "standard", "--analysis-json", str(aj)])
    assert r.exit_code == 0


def test_report_premium_pdf(runner: CliRunner, tmp_path: Path) -> None:
    pytest.importorskip("xhtml2pdf")
    out = tmp_path / "prem.pdf"
    r = runner.invoke(app, ["report", _SAAS, "--level", "executive", "--format", "pdf", "-o", str(out)])
    assert r.exit_code == 0
    assert out.is_file()


# --- explain ---


def test_explain_analysis(runner: CliRunner, tmp_path: Path) -> None:
    aj = _analysis_json(runner, tmp_path, _SAAS, "ex_an.json")
    r = runner.invoke(app, ["explain", str(aj)])
    assert r.exit_code == 0


def test_explain_category_filter_empty(runner: CliRunner, tmp_path: Path) -> None:
    aj = _analysis_json(runner, tmp_path, _MINIMAL, "ex2.json")
    r = runner.invoke(app, ["explain", str(aj), "--category", "no_such_category_xyz"])
    assert r.exit_code == 0
    assert "No explanations" in (r.stdout + (r.stderr or ""))


def test_explain_bad_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(tmp_path / "missing.json")])
    assert r.exit_code == 1


# --- backlog ---


def test_backlog_from_model_markdown(runner: CliRunner) -> None:
    r = runner.invoke(app, ["backlog", _SAAS])
    assert r.exit_code == 0


def test_backlog_from_model_json(runner: CliRunner) -> None:
    r = runner.invoke(app, ["backlog", _SAAS, "--format", "json"])
    assert r.exit_code == 0
    json.loads(r.stdout)


def test_backlog_group_by_and_output(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "bk.md"
    r = runner.invoke(app, ["backlog", _SAAS, "--group-by", "control", "-o", str(out)])
    assert r.exit_code == 0
    assert out.is_file()


def test_backlog_from_analysis_json_with_document(runner: CliRunner, tmp_path: Path) -> None:
    aj = _analysis_json(runner, tmp_path, _SAAS, "bk_an.json")
    r = runner.invoke(app, ["backlog", str(aj), "-d", _SAAS])
    assert r.exit_code == 0


# --- diff-analysis ---


def test_diff_analysis_text(runner: CliRunner, tmp_path: Path) -> None:
    a = _analysis_json(runner, tmp_path, _MINIMAL, "da_a.json")
    b = _analysis_json(runner, tmp_path, _SAAS, "da_b.json")
    r = runner.invoke(app, ["diff-analysis", str(a), str(b)])
    assert r.exit_code == 0


def test_diff_analysis_json_and_out(runner: CliRunner, tmp_path: Path) -> None:
    a = _analysis_json(runner, tmp_path, _MINIMAL, "da_a2.json")
    b = _analysis_json(runner, tmp_path, _SAAS, "da_b2.json")
    out = tmp_path / "da.json"
    r = runner.invoke(app, ["diff-analysis", str(a), str(b), "--format", "json", "--json-out", str(out)])
    assert r.exit_code == 0
    assert out.is_file()


# --- diagram / export / recommend / templates ---


def test_diagram_stdout_and_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["diagram", _MINIMAL])
    assert r.exit_code == 0
    out = tmp_path / "d.mmd"
    r2 = runner.invoke(app, ["diagram", _MINIMAL, "-o", str(out)])
    assert r2.exit_code == 0
    assert out.is_file()


@pytest.mark.parametrize("fmt", ["yaml", "json", "md"])
def test_export_formats(runner: CliRunner, tmp_path: Path, fmt: str) -> None:
    out = tmp_path / f"out.{fmt}"
    r = runner.invoke(app, ["export", _MINIMAL, "-f", fmt, "-o", str(out)])
    assert r.exit_code == 0
    assert out.is_file()


def test_recommend_methodology(runner: CliRunner) -> None:
    r = runner.invoke(app, ["recommend-methodology", _SAAS])
    assert r.exit_code == 0
    assert "Suggested methodology" in (r.stdout + (r.stderr or ""))


def test_templates_callback_list_and_show(runner: CliRunner) -> None:
    from otm_cli.application import templates_service as tmpl

    # bare group → callback list
    r = runner.invoke(app, ["templates"])
    assert r.exit_code == 0
    # explicit list subcommand with a filter
    r_list = runner.invoke(app, ["templates", "list", "--complexity", "medium"])
    assert r_list.exit_code == 0
    # show detail for a real template id
    tid = tmpl.list_template_infos()[0].id
    r_show = runner.invoke(app, ["templates", "show", tid])
    assert r_show.exit_code == 0


def test_templates_show_unknown_errors(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "show", "no_such_template_xyz"])
    assert r.exit_code != 0
