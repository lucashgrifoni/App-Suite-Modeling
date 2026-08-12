"""A mis-encoded analysis JSON must produce the CLI's structured error, not a traceback.

`analysis_io` decodes with `read_text(encoding="utf-8")` inside a `try` that caught only
`(OSError, json.JSONDecodeError)`. `UnicodeDecodeError` is a sibling `ValueError`, not an
`OSError`, so a cp1252/latin-1 file written by a Windows CI agent escaped both handlers and
`diff-analysis` / `report --analysis-json` dumped interpreter paths into the build log.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_LATIN1_JSON = '{"nome":"Jos\xe9"}'.encode("latin-1")


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _valid_analysis(tmp_path: Path) -> Path:
    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document

    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return p


def test_diff_analysis_on_a_non_utf8_file_is_a_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "latin1.json"
    bad.write_bytes(_LATIN1_JSON)
    r = runner.invoke(app, ["diff-analysis", str(bad), str(_valid_analysis(tmp_path))])
    assert r.exit_code == 1
    assert not isinstance(r.exception, UnicodeDecodeError)
    assert "Failure" in _out(r)


def test_report_analysis_json_on_a_non_utf8_file_is_a_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "latin1.json"
    bad.write_bytes(_LATIN1_JSON)
    r = runner.invoke(app, ["report", str(_MINIMAL), "--analysis-json", str(bad)])
    assert r.exit_code == 1
    assert not isinstance(r.exception, UnicodeDecodeError)
    assert "Failure" in _out(r)


def test_truncated_json_is_still_a_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    """Control: the pre-existing JSONDecodeError path must be unchanged."""
    bad = tmp_path / "truncated.json"
    bad.write_text('{"explanations": [', encoding="utf-8")
    r = runner.invoke(app, ["diff-analysis", str(bad), str(_valid_analysis(tmp_path))])
    assert r.exit_code == 1
    assert r.exception is None or isinstance(r.exception, SystemExit)
    assert "Failure" in _out(r)
