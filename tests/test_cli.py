"""Testes da CLI (Typer) — fluxos principais."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
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
    assert "Valid" in out


def test_diff_same_file_reports_no_structural_change(runner: CliRunner) -> None:
    r = runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL)])
    assert r.exit_code == 0
    out = (r.stdout or "") + (r.stderr or "")
    assert "sem diferenças estruturais" in out.lower()


def test_diff_analysis_two_identical_json(tmp_path: Path, runner: CliRunner) -> None:
    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document

    doc = load_document_from_yaml_path(_MINIMAL)
    ar = analyze_document(doc)
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    p1.write_text(json.dumps(ar.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    p2.write_text(json.dumps(ar.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    r = runner.invoke(app, ["diff-analysis", str(p1), str(p2)])
    assert r.exit_code == 0


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


def test_export_json_to_file(tmp_path: Path, runner: CliRunner) -> None:
    out = tmp_path / "doc.json"
    r = runner.invoke(app, ["export", str(_MINIMAL), "--format", "json", "--output", str(out)])
    assert r.exit_code == 0
    assert out.is_file()
    assert json.loads(out.read_text(encoding="utf-8"))


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
    assert "Methodology: nist_data_centric" in out


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


def test_analyze_with_unknown_pack_exits_1(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", str(_MINIMAL), "--pack", "pack_que_nao_existe_xxx"])
    assert r.exit_code == 1


def test_templates_command_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates"])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "Templates" in combined


def test_templates_list_filter(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "list", "--category", "ai_llm"])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "ai-llm-chat" in combined


def test_templates_show_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "show", "api-public"])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "api-public" in combined


def test_templates_show_unknown_exits_1(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "show", "nao_existe_xxx"])
    assert r.exit_code == 1


def test_packs_command_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["packs"])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "Industry packs" in combined


def test_recommend_methodology_ok(runner: CliRunner) -> None:
    r = runner.invoke(app, ["recommend-methodology", str(_MINIMAL)])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "Suggested methodology" in combined


def test_explain_command_reads_analysis_json(tmp_path: Path, runner: CliRunner) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    r = runner.invoke(app, ["explain", str(path), "--from", "analysis"])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert len(combined.strip()) > 0


def test_explain_command_category_filter(tmp_path: Path, runner: CliRunner) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    r = runner.invoke(app, ["explain", str(path), "--from", "analysis", "--category", "risk"])
    assert r.exit_code == 0


def test_report_writes_markdown(runner: CliRunner) -> None:
    r = runner.invoke(app, ["report", str(_MINIMAL)])
    assert r.exit_code == 0
    combined = (r.stdout or "") + (r.stderr or "")
    assert "#" in combined


def test_export_markdown_stdout(runner: CliRunner) -> None:
    r = runner.invoke(app, ["export", str(_MINIMAL), "--format", "md"])
    assert r.exit_code == 0
    assert "#" in r.stdout


def test_validate_invalid_document_cli_error_pattern(tmp_path: Path, runner: CliRunner) -> None:
    bad = tmp_path / "bad.otm.yaml"
    bad.write_text("only_invalid_root: true\n", encoding="utf-8")
    r = runner.invoke(app, ["validate", str(bad)])
    assert r.exit_code == 1
    combined = (r.stdout or "") + (r.stderr or "")
    assert "Falha:" in combined
    assert "Possível causa:" in combined


def test_init_unknown_template_exits_1(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "out.otm.yaml"
    r = runner.invoke(app, ["init", str(out), "-t", "template_id_inexistente_xyz"])
    assert r.exit_code == 1
    combined = (r.stdout or "") + (r.stderr or "")
    assert "Template desconhecido" in combined
