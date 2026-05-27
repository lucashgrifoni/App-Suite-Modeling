"""Coverage — CLI application services error/edge branches."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.application.analysis_io import (
    load_analysis_result_from_path,
    load_two_analysis_results,
)
from otm_cli.application.explain_service import run_explain
from otm_cli.shared.errors import CliUserError


def _bad_json(tmp_path: Path, name: str = "bad.json") -> Path:
    p = tmp_path / name
    p.write_text("{not valid json", encoding="utf-8")
    return p


def _wrong_shape(tmp_path: Path, name: str = "wrong.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
    return p


# --- analysis_io ---


def test_load_analysis_bad_json(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        load_analysis_result_from_path(_bad_json(tmp_path))


def test_load_analysis_wrong_shape(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        load_analysis_result_from_path(_wrong_shape(tmp_path))


def test_load_two_bad_json(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        load_two_analysis_results(_bad_json(tmp_path, "a.json"), _bad_json(tmp_path, "b.json"))


def test_load_two_wrong_shape(tmp_path: Path) -> None:
    a = _wrong_shape(tmp_path, "a2.json")
    b = _wrong_shape(tmp_path, "b2.json")
    with pytest.raises(CliUserError):
        load_two_analysis_results(a, b)


# --- explain_service ---


def _expl(tmp_path: Path) -> Path:
    p = tmp_path / "an.json"
    p.write_text(
        json.dumps({"explanations": [{"category": "risk", "subject": "s", "message": "m"}]}),
        encoding="utf-8",
    )
    return p


def test_explain_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        run_explain(tmp_path / "nope.json", kind="analysis", category=None, limit=25)


def test_explain_bad_json(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        run_explain(_bad_json(tmp_path), kind="analysis", category=None, limit=25)


def test_explain_invalid_kind(tmp_path: Path) -> None:
    with pytest.raises(CliUserError):
        run_explain(_expl(tmp_path), kind="bogus", category=None, limit=25)


def test_explain_compare_kind(tmp_path: Path) -> None:
    rows = run_explain(_expl(tmp_path), kind="compare", category=None, limit=25)
    assert rows and rows[0][0] == "risk"


def test_explain_category_filter_match_and_miss(tmp_path: Path) -> None:
    assert run_explain(_expl(tmp_path), kind="analysis", category="risk", limit=25)
    assert run_explain(_expl(tmp_path), kind="analysis", category="nope", limit=25) == []
