"""P2 evolution — the CI diff/drift gate (`otm diff --fail-on`).

Two properties matter more than any other, and they pull in opposite directions:

* **Never fail a build the developer cannot fix.** Removals, improvements, score drops and
  inert renames must exit 0.
* **Never pass what should trip.** A threat whose id churned appears as an `(added, removed)`
  pair — never in `modified` — and the remap signature ignores the score. Treating every remap
  as inert would silently swallow a threat that changed id *and* rose from medium to critical.

Exit-code contract: 0 = no trip, 1 = usage error, 3 = gate tripped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from otm_cli.cli import app
from otm_core_schema import StrideCategory, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.comparison_models import AnalysisDiff, HeuristicThreatDelta, HeuristicThreatDeltaSection
from otm_threat_engine.gate import GatePolicy, evaluate_gate
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment
from typer.testing import CliRunner

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"
_GATE_TRIP = 3


def _diff(**sections: object) -> AnalysisDiff:
    return AnalysisDiff(
        methodology_before="stride",
        methodology_after="stride",
        methodology_changed=False,
        heuristic_threats=HeuristicThreatDeltaSection(**sections),  # type: ignore[arg-type]
        max_risk_before=10.0,
        max_risk_after=10.0,
        max_risk_delta=0.0,
    )


def _added(threat_id: str, score_after: float | None, **kw: object) -> HeuristicThreatDelta:
    return HeuristicThreatDelta(threat_id=threat_id, change="added", score_after=score_after, **kw)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- evaluator


def test_inactive_policy_never_trips() -> None:
    result = evaluate_gate(_diff(added=[_added("a", 25)]), GatePolicy())
    assert result.tripped is False


@pytest.mark.parametrize(
    ("score", "threshold", "expected"),
    [
        (24, "high", True),  # critical >= high
        (12, "high", True),  # exactly at the band floor
        (11.9, "high", False),  # just below
        (8, "high", False),  # medium < high
        (8, "medium", True),
        (1, "low", True),  # `low` gates any new scored threat
    ],
)
def test_new_threat_trips_at_or_above_threshold(score: float, threshold: str, expected: bool) -> None:
    result = evaluate_gate(_diff(added=[_added("a", score)]), GatePolicy(fail_on=threshold))  # type: ignore[arg-type]
    assert result.tripped is expected


def test_remapped_threat_that_crosses_a_band_trips() -> None:
    """The silent-pass hole: id churned AND score rose medium(11) -> critical(24)."""
    diff = _diff(
        added=[_added("new", 24, match_kind="signature_remap", paired_id="old", score_before=11, score_delta=13)],
        removed=[
            HeuristicThreatDelta(
                threat_id="old", change="removed", match_kind="signature_remap", paired_id="new", score_before=11
            )
        ],
    )
    result = evaluate_gate(diff, GatePolicy(fail_on="high"))
    assert result.tripped is True
    (trip,) = result.trips
    assert trip.kind == "worsened_threat"
    assert (trip.severity_before, trip.severity_after) == ("medium", "critical")
    assert trip.paired_id == "old"


def test_inert_rename_does_not_trip() -> None:
    """Same threat, same score, new id — a rename must never fail a build."""
    diff = _diff(added=[_added("new", 24, match_kind="signature_remap", paired_id="old", score_before=24)])
    assert evaluate_gate(diff, GatePolicy(fail_on="high")).tripped is False


def test_remap_without_a_baseline_score_fails_closed() -> None:
    """Cannot compare, so treat it as genuinely new rather than assume it is inert."""
    diff = _diff(added=[_added("new", 24, match_kind="signature_remap", paired_id="old", score_before=None)])
    assert evaluate_gate(diff, GatePolicy(fail_on="high")).tripped is True


def test_within_band_worsening_does_not_trip_the_band_gate() -> None:
    """21 -> 22 stays critical: real, but not a severity regression. --fail-on-risk-increase covers it."""
    diff = _diff(modified=[HeuristicThreatDelta(threat_id="m", change="modified", score_before=21, score_after=22)])
    assert evaluate_gate(diff, GatePolicy(fail_on="high")).tripped is False


def test_modified_threat_crossing_up_trips() -> None:
    diff = _diff(modified=[HeuristicThreatDelta(threat_id="m", change="modified", score_before=8, score_after=20)])
    result = evaluate_gate(diff, GatePolicy(fail_on="high"))
    assert result.tripped and result.worsened_threats[0].severity_after == "critical"


def test_removals_and_improvements_never_trip() -> None:
    diff = _diff(
        removed=[HeuristicThreatDelta(threat_id="r", change="removed", score_before=25)],
        modified=[HeuristicThreatDelta(threat_id="m", change="modified", score_before=24, score_after=4)],
    )
    assert evaluate_gate(diff, GatePolicy(fail_on="low", fail_on_risk_increase=True)).tripped is False


def test_unranked_new_threats_are_reported_not_dropped() -> None:
    result = evaluate_gate(_diff(added=[_added("u", None)]), GatePolicy(fail_on="low"))
    assert result.tripped is False
    assert result.unranked_threat_ids == ["u"]


def test_risk_increase_flag_is_independent_of_the_band() -> None:
    diff = _diff()
    diff.max_risk_before, diff.max_risk_after, diff.max_risk_delta = 20.0, 21.0, 1.0
    assert evaluate_gate(diff, GatePolicy(fail_on="critical")).tripped is False
    assert evaluate_gate(diff, GatePolicy(fail_on_risk_increase=True)).tripped is True


def test_risk_decrease_never_trips() -> None:
    diff = _diff()
    diff.max_risk_delta = -5.0
    assert evaluate_gate(diff, GatePolicy(fail_on_risk_increase=True)).tripped is False


# --------------------------------------------------------------------------- pairing


def test_analysis_diff_marks_remapped_pairs_with_the_baseline_score() -> None:
    """The gate depends on `analysis_diff` populating match_kind/paired_id/score_before."""
    from otm_threat_engine.analysis_diff import diff_analysis_results

    def _threat(hid: str, likelihood: int, impact: int) -> HeuristicThreat:
        return HeuristicThreat(
            id=hid,
            title="Same Title",
            description="d",
            stride=StrideCategory.TAMPERING,
            risk=build_risk_assessment(likelihood, impact),
            target_component_id="c1",
        )

    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc).model_copy(update={"heuristic_threats": [_threat("old_id", 3, 3)]})
    rev = analyze_document(doc).model_copy(update={"heuristic_threats": [_threat("new_id", 5, 5)]})

    ad = diff_analysis_results(base, rev)
    (added,) = ad.heuristic_threats.added
    assert added.match_kind == "signature_remap"
    assert added.paired_id == "old_id"
    assert added.score_before == 9.0 and added.score_after == 25.0
    # ... and therefore the gate sees a medium -> critical crossing, not a "new" threat.
    assert evaluate_gate(ad, GatePolicy(fail_on="high")).worsened_threats


# --------------------------------------------------------------------------- CLI contract


def _revised_with_new_risk(tmp_path: Path) -> Path:
    doc = yaml.safe_load(_MINIMAL.read_text(encoding="utf-8"))
    doc["components"].append(
        {
            "id": "admin",
            "name": "Admin",
            "kind": "process",
            "in_trust_boundary": "internet",
            "asset_ids": ["orders_data"],
        }
    )
    doc["data_flows"].append(
        {
            "id": "admin_in",
            "name": "admin plaintext",
            "from_component": "admin",
            "to_component": "db",
            "protocol": "HTTP",
            "authenticated": False,
            "encrypted": False,
            "public_exposure": True,
            "stores_sensitive_data": True,
        }
    )
    out = tmp_path / "revised.otm.yaml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out


def test_cli_without_gate_flags_is_unchanged() -> None:
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL)])
    assert r.exit_code == 0
    assert "THREAT MODEL GATE" not in r.output


def test_cli_gate_passes_on_an_identical_model() -> None:
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--fail-on", "high"])
    assert r.exit_code == 0


def test_cli_gate_trips_with_exit_3_on_new_high_risk(tmp_path: Path) -> None:
    revised = _revised_with_new_risk(tmp_path)
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(revised), "--fail-on", "high"])
    assert r.exit_code == _GATE_TRIP
    assert "THREAT MODEL GATE: FAILED" in r.output


def test_cli_gate_does_not_trip_on_improvement(tmp_path: Path) -> None:
    """Removing the risky flow is the reverse diff: it must never fail the build."""
    revised = _revised_with_new_risk(tmp_path)
    r = CliRunner().invoke(app, ["diff", str(revised), str(_MINIMAL), "--fail-on", "high", "--fail-on-risk-increase"])
    assert r.exit_code == 0


def test_cli_invalid_fail_on_is_a_usage_error_not_a_trip() -> None:
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--fail-on", "catastrophic"])
    assert r.exit_code == 1
    assert r.exit_code != _GATE_TRIP


def test_cli_gate_writes_the_json_artifact_even_when_it_trips(tmp_path: Path) -> None:
    """CI wants the diff most on the runs that fail. The gate must be evaluated last."""
    revised = _revised_with_new_risk(tmp_path)
    artifact = tmp_path / "diff.json"
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(revised), "--fail-on", "high", "--json-out", str(artifact)])
    assert r.exit_code == _GATE_TRIP
    assert artifact.is_file()
    assert json.loads(artifact.read_text(encoding="utf-8"))["analysis"] is not None


def test_cli_gate_implies_with_analysis(tmp_path: Path) -> None:
    """Without the engine delta the gate could never trip — a silent pass."""
    revised = _revised_with_new_risk(tmp_path)
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(revised), "--fail-on", "critical"])
    assert r.exit_code == _GATE_TRIP  # no --with-analysis passed


def test_cli_diff_analysis_refuses_to_gate_across_engine_versions(tmp_path: Path) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc)
    rev = analyze_document(doc).model_copy(update={"engine_version": "99.0.0"})
    bf, rf = tmp_path / "b.json", tmp_path / "r.json"
    bf.write_text(json.dumps(base.model_dump(mode="json")), encoding="utf-8")
    rf.write_text(json.dumps(rev.model_dump(mode="json")), encoding="utf-8")

    runner = CliRunner()
    gated = runner.invoke(app, ["diff-analysis", str(bf), str(rf), "--fail-on", "high"])
    assert gated.exit_code == 1
    assert "engine" in gated.output.lower()

    # Without a gate the mismatch is not an error — the diff is still informative.
    assert runner.invoke(app, ["diff-analysis", str(bf), str(rf)]).exit_code == 0
