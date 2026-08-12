"""`otm explain` input guards.

Three defects lived in `run_explain`: the `analysis` and `compare` branches were byte-identical
so `--from` validated nothing, `raw` was never checked to be a JSON object so any array produced
an `AttributeError` traceback, and `explanations[:limit]` was unclamped so `--limit 0` reported a
populated file as empty and `--limit -3` silently dropped the last three rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.application.explain_service import run_explain
from otm_cli.cli import app
from otm_cli.shared.errors import CliUserError
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _analysis_json(tmp_path: Path) -> Path:
    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document

    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    p = tmp_path / "analysis.json"
    p.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return p


def _compare_json(tmp_path: Path) -> Path:
    """A `ThreatModelComparisonResult`, i.e. what `otm diff --with-analysis --json-out` writes."""
    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document
    from otm_threat_engine.threat_model_comparison import compare_threat_models

    doc = load_document_from_yaml_path(_MINIMAL)
    analysis = analyze_document(doc)
    full = compare_threat_models(doc, doc, baseline_analysis=analysis, revised_analysis=analysis)
    p = tmp_path / "compare.json"
    p.write_text(json.dumps(full.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return p


def test_explain_rejects_non_object_json(runner: CliRunner, tmp_path: Path) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text("[1,2,3]", encoding="utf-8")
    r = runner.invoke(app, ["explain", str(arr)])
    assert r.exit_code == 1
    assert not isinstance(r.exception, AttributeError), "raw traceback instead of a structured error"
    assert "Failure" in ((r.stdout or "") + (r.stderr or ""))


def test_explain_from_compare_rejects_an_analysis_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(_analysis_json(tmp_path)), "--from", "compare"])
    assert r.exit_code == 1
    assert "analysis" in ((r.stdout or "") + (r.stderr or "")).lower()


def test_explain_from_analysis_rejects_a_compare_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(_compare_json(tmp_path)), "--from", "analysis"])
    assert r.exit_code == 1
    assert "compare" in ((r.stdout or "") + (r.stderr or "")).lower()


def test_explain_from_compare_accepts_a_compare_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(_compare_json(tmp_path)), "--from", "compare"])
    assert r.exit_code == 0


def test_explain_from_analysis_accepts_an_analysis_file(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(_analysis_json(tmp_path)), "--from", "analysis"])
    assert r.exit_code == 0


def test_explain_zero_limit_is_a_usage_error_not_an_empty_file_claim(runner: CliRunner, tmp_path: Path) -> None:
    path = _analysis_json(tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["explanations"], "fixture must be populated"
    r = runner.invoke(app, ["explain", str(path), "--limit", "0"])
    out = (r.stdout or "") + (r.stderr or "")
    assert r.exit_code == 2
    assert "No explanations in this file." not in out, "a populated file was reported as empty"


def test_explain_negative_limit_does_not_silently_drop_rows(tmp_path: Path) -> None:
    """`explanations[:-3]` used to hide the LAST three rows — the opposite of a maximum."""
    with pytest.raises(CliUserError) as excinfo:
        run_explain(_analysis_json(tmp_path), kind="analysis", category=None, limit=-3)
    assert excinfo.value.exit_code == 2
