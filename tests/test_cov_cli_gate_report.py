"""The CI gate report a red `otm diff-analysis` build actually prints.

`test_diff_drift_gate.py` proves the *verdict* (`evaluate_gate`) and the exit code. What it never
reads is the block the operator sees in the CI log, and that block is the only artifact of the
gate a human consumes: three of its four sections (worsened threats, risk increases, the unranked
note) had no test at all, so a rename could have printed the wrong baseline id, a within-band
increase could have vanished, and every suite would still have been green.

The fixture is a pair of `analyze.json` artifacts — exactly what a CI job stores between the
baseline run and the PR run — carrying one threat of each shape the report has a section for:

* ``renamed_old`` → ``renamed_new``  same signature, medium(9) → critical(25): a *worsened* threat
  reported under its new id with the old one named, never as a "new" threat;
* ``bumped``                          12 → 15, both ``high``: a within-band rise that only
  ``--fail-on-risk-increase`` can see;
* ``unranked_new``                    a new threat the engine could not score: reported, not dropped.

There is deliberately no genuinely-new scored threat, so the `NEW threats` header must be absent —
an empty section that still printed its header would tell the reader threats were introduced.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from otm_cli.shared.gate import parse_fail_on
from otm_core_schema import RiskAssessment, StrideCategory, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment
from typer.testing import CliRunner

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"
_GATE_TRIP = 3


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich wraps to the terminal; a wrapped error message would fail for the wrong reason."""
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _scored(threat_id: str, title: str, *, likelihood: int, impact: int) -> HeuristicThreat:
    """A threat whose signature is (stride, targets, title) — the score is deliberately outside it."""
    return HeuristicThreat(
        id=threat_id,
        title=title,
        description="fixture threat",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(likelihood, impact),
        target_component_id="api",
    )


def _unscored(threat_id: str, title: str) -> HeuristicThreat:
    return HeuristicThreat(
        id=threat_id,
        title=title,
        description="fixture threat the engine could not rank",
        stride=StrideCategory.SPOOFING,
        risk=RiskAssessment(likelihood=3, impact=3, score=None),
        target_component_id="api",
    )


def _write_analysis_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Two `analyze.json` artifacts from the same engine, differing only in their threats."""
    analysis = analyze_document(load_document_from_yaml_path(_MINIMAL))

    baseline = analysis.model_copy(
        update={
            "heuristic_threats": [
                _scored("renamed_old", "Renamed Threat", likelihood=3, impact=3),  # 9  → medium
                _scored("bumped", "Bumped Threat", likelihood=3, impact=4),  # 12 → high
            ],
            "summary": analysis.summary.model_copy(update={"max_risk_score": 12.0}),
        }
    )
    revised = analysis.model_copy(
        update={
            "heuristic_threats": [
                _scored("renamed_new", "Renamed Threat", likelihood=5, impact=5),  # 25 → critical
                _scored("bumped", "Bumped Threat", likelihood=3, impact=5),  # 15 → still high
                _unscored("unranked_new", "Unranked Threat"),
            ],
            "summary": analysis.summary.model_copy(update={"max_risk_score": 25.0}),
        }
    )

    baseline_path = tmp_path / "baseline.analysis.json"
    revised_path = tmp_path / "revised.analysis.json"
    baseline_path.write_text(json.dumps(baseline.model_dump(mode="json")), encoding="utf-8")
    revised_path.write_text(json.dumps(revised.model_dump(mode="json")), encoding="utf-8")
    return baseline_path, revised_path


@pytest.fixture
def gate_run(tmp_path: Path) -> Result:
    """One `diff-analysis` run with both criteria armed, shared by the report assertions."""
    baseline, revised = _write_analysis_pair(tmp_path)
    return CliRunner().invoke(
        app,
        ["diff-analysis", str(baseline), str(revised), "--fail-on", "high", "--fail-on-risk-increase"],
    )


# --------------------------------------------------------------------------- verdict


def test_armed_gate_exits_three_on_diff_analysis(gate_run: Result) -> None:
    """`diff-analysis` owns the same exit-code contract as `diff`: 3 means the policy failed."""
    assert gate_run.exit_code == _GATE_TRIP


def test_report_headline_states_the_verdict_and_the_armed_policy(gate_run: Result) -> None:
    report = _out(gate_run)
    assert "THREAT MODEL GATE: FAILED" in report
    assert "--fail-on=high" in report
    assert "--fail-on-risk-increase" in report


def test_report_counts_every_condition_that_hit(gate_run: Result) -> None:
    """One worsened threat plus two risk increases — a miscount hides a condition from the reader."""
    assert "3 condition(s) hit. Exit code 3." in _out(gate_run)


# --------------------------------------------------------------------------- worsened section


def test_worsened_section_names_the_band_crossing(gate_run: Result) -> None:
    report = _out(gate_run)
    assert "WORSENED threats crossing into high+ (1):" in report
    assert "[MEDIUM 9 -> CRITICAL 25]  renamed_new" in report


def test_worsened_section_names_the_id_the_threat_had_before(gate_run: Result) -> None:
    """Without `(was ...)` the reader searches the baseline for an id that never existed there."""
    assert "(was `renamed_old`)" in _out(gate_run)


def test_a_renamed_threat_is_never_reported_as_a_new_one(gate_run: Result) -> None:
    """No threat was introduced, so the NEW header must be absent — not present over an empty list."""
    assert "NEW threats" not in _out(gate_run)


# --------------------------------------------------------------------------- risk-increase section


def test_report_shows_the_summary_maximum_rising(gate_run: Result) -> None:
    """The trip with no threat id is the summary maximum, and must not read as a concrete threat."""
    assert "MAX RISK increased: 12 -> 25" in _out(gate_run)


def test_report_shows_the_within_band_rise_that_the_band_criterion_cannot_see(gate_run: Result) -> None:
    """12 → 15 stays `high`; only this line tells the operator the threat got worse."""
    assert "RISK increased (within band): 12 -> 15  bumped" in _out(gate_run)


# --------------------------------------------------------------------------- unranked note


def test_a_new_threat_without_a_score_is_reported_rather_than_dropped(gate_run: Result) -> None:
    report = _out(gate_run)
    assert "1 new threat(s) carry no score" in report
    assert "unranked_new" in report


# --------------------------------------------------------------------------- usage errors


def test_absent_fail_on_value_means_the_band_criterion_is_off() -> None:
    """`--fail-on` is a string option at the CLI edge, but the parser is also called with `None`."""
    assert parse_fail_on(None) is None


def test_diff_analysis_rejects_an_unknown_fail_on_band(tmp_path: Path) -> None:
    baseline, revised = _write_analysis_pair(tmp_path)
    result = CliRunner().invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "catastrophic"])
    report = _out(result)
    assert result.exit_code == 1
    assert result.exit_code != _GATE_TRIP, "a mistyped policy must not look like a failed policy"
    assert "invalid `--fail-on` value" in report


def test_diff_analysis_json_out_into_a_missing_directory_is_a_clean_error(tmp_path: Path) -> None:
    baseline, revised = _write_analysis_pair(tmp_path)
    target = tmp_path / "nodir" / "analysis-diff.json"
    result = CliRunner().invoke(app, ["diff-analysis", str(baseline), str(revised), "--json-out", str(target)])
    report = _out(result)
    assert result.exit_code == 1
    assert "parent directory does not exist" in report
    assert "Traceback" not in report
    assert not target.exists()
