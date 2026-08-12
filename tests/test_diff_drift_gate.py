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
    assert result.tripped
    assert result.worsened_threats[0].severity_after == "critical"


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
    assert added.score_before == 9.0
    assert added.score_after == 25.0
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


# ------------------------------------------------- regressions from the pre-v7.8.0 deep review
#
# Two holes the original suite did not discriminate. Both are in the gate itself, which is the
# one place where being wrong is expensive in both directions.


def _meth_switch_diff() -> AnalysisDiff:
    """A pure methodology switch: every threat of the new lens looks brand new."""
    return AnalysisDiff(
        methodology_before="stride",
        methodology_after="nist_data_centric",
        methodology_changed=True,
        heuristic_threats=HeuristicThreatDeltaSection(added=[_added("nist_dc_new", 25)]),
        max_risk_before=10.0,
        max_risk_after=25.0,
        max_risk_delta=15.0,
    )


def test_methodology_switch_is_never_a_red_build() -> None:
    """Principle 1: *troca de metodologia nunca dispara*.

    Switching lens swaps the ruler itself — the other lens's heuristics do not exist on this
    side, so `added` fills with threats the developer did not introduce. Gating on that failed
    the build for something nobody caused, under the strictest policy the CLI offers.
    """
    result = evaluate_gate(_meth_switch_diff(), GatePolicy(fail_on="low", fail_on_risk_increase=True))
    assert result.tripped is False
    assert result.not_evaluated_reason == "methodology_changed"
    assert result.trips == []


def test_methodology_switch_is_reported_as_not_evaluated_never_as_passed() -> None:
    """`PASSED` on a diff nobody judged is the gate claiming a clean bill of health it never took."""
    from otm_cli.shared.gate import render_gate_result

    text = render_gate_result(evaluate_gate(_meth_switch_diff(), GatePolicy(fail_on="low")))
    assert "NOT EVALUATED" in text
    assert "PASSED" not in text
    assert "methodology" in text.lower()


# ------------------------------------------------------- the gate must judge under the configured lens
#
# `otm analyze` accepts `--methodology`, and the shipped composite action forwards its
# `methodology` input to the Analyze step. The gate step ran `otm diff` with no lens at all, so
# the analysis the gate judged was not the analysis the user configured. Both directions were
# reproducible: a green build on a PR that adds a HIGH threat under the configured lens, and a
# red build for a repo whose lens says the change is harmless.


def test_diff_accepts_the_same_methodology_flag_as_analyze() -> None:
    """A gate that silently ignores the configured lens is a silent-pass hole."""
    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--methodology", "stride"])
    assert r.exit_code == 0, r.output
    assert "No such option" not in r.output


def _revised_with_bare_admin_actor(tmp_path: Path) -> Path:
    """A change whose verdict genuinely depends on the lens.

    Adding an unconnected external actor raises spoofing/repudiation concerns that
    STRIDE scores at/above `high`, while the CIA-DIE lens — which scores impact on
    data, not actors — stays below the bar. `_revised_with_new_risk` is unusable
    here: it also adds an unauthenticated plaintext flow carrying sensitive data,
    which trips every lens and so could not detect the flag being ignored.
    """
    doc = yaml.safe_load(_MINIMAL.read_text(encoding="utf-8"))
    doc["components"].append({"id": "admin", "name": "Admin", "kind": "external_entity"})
    out = tmp_path / "revised_actor.otm.yaml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out


def test_gate_verdict_follows_the_requested_methodology(tmp_path: Path) -> None:
    revised = _revised_with_bare_admin_actor(tmp_path)
    runner = CliRunner()

    under_stride = runner.invoke(
        app, ["diff", str(_MINIMAL), str(revised), "--methodology", "stride", "--fail-on", "high"]
    )
    under_cia_die = runner.invoke(
        app, ["diff", str(_MINIMAL), str(revised), "--methodology", "cia_die", "--fail-on", "high"]
    )

    # If the flag were ignored, both runs would return the same code — which is
    # exactly the silent-pass/spurious-failure bug this guards.
    assert under_stride.exit_code == _GATE_TRIP, under_stride.output
    assert under_cia_die.exit_code == 0, under_cia_die.output


def test_diff_rejects_methodology_and_auto_methodology_together() -> None:
    """Mirrors the mutual exclusion `otm analyze` already enforces."""
    r = CliRunner().invoke(
        app,
        ["diff", str(_MINIMAL), str(_MINIMAL), "--methodology", "stride", "--auto-methodology"],
    )
    assert r.exit_code != 0
    assert r.exit_code != _GATE_TRIP


def test_cli_methodology_switch_exits_zero(tmp_path: Path) -> None:
    raw = yaml.safe_load(_MINIMAL.read_text(encoding="utf-8"))
    raw["model"]["methodology"] = "nist_data_centric"
    revised = tmp_path / "meth.otm.yaml"
    revised.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    r = CliRunner().invoke(app, ["diff", str(_MINIMAL), str(revised), "--fail-on", "high"])
    assert r.exit_code == 0


def test_within_band_worsening_of_a_non_maximum_threat_is_caught() -> None:
    """The fail-open.

    `12 -> 15` stays inside `high`, so the band criterion cannot see it by design. And when the
    worsened threat is not the global maximum, `max_risk_delta` is `0`, so the summary criterion
    could not see it either — leaving a real +3.0 regression that *no* policy could catch.
    """
    diff = _diff(modified=[HeuristicThreatDelta(threat_id="m", change="modified", score_before=12, score_after=15)])
    assert diff.max_risk_delta == 0.0, "fixture must model a NON-maximum threat worsening"

    assert evaluate_gate(diff, GatePolicy(fail_on="low")).tripped is False  # band gate blind, by design

    result = evaluate_gate(diff, GatePolicy(fail_on_risk_increase=True))
    assert result.tripped is True
    trip = next(t for t in result.trips if t.kind == "risk_increase")
    assert (trip.threat_id, trip.score_before, trip.score_after) == ("m", 12.0, 15.0)


def test_within_band_worsening_via_id_churn_is_caught() -> None:
    """Same hole reached through the remap path rather than `modified`."""
    diff = _diff(added=[_added("new", 15, match_kind="signature_remap", paired_id="old", score_before=12)])
    result = evaluate_gate(diff, GatePolicy(fail_on_risk_increase=True))
    assert result.tripped is True
    trip = next(t for t in result.trips if t.kind == "risk_increase")
    assert trip.paired_id == "old"


def test_a_band_crossing_is_not_reported_twice() -> None:
    """Under both criteria at once, one threat must produce one entry, not two."""
    diff = _diff(modified=[HeuristicThreatDelta(threat_id="m", change="modified", score_before=8, score_after=20)])
    result = evaluate_gate(diff, GatePolicy(fail_on="high", fail_on_risk_increase=True))
    assert [t.threat_id for t in result.trips].count("m") == 1


def test_the_exit_code_contract_is_what_the_docs_claim() -> None:
    """Pins the exit codes a CI script branches on.

    Found by driving the published CLI as a user: the docs said "1 = usage error", but Click
    raises **2** for an invalid enum value, an unknown flag or a missing argument, and this CLI
    does not override that. Anyone scripting `if [ $rc -eq 1 ]` to catch a mistyped command was
    missing half the cases. Both are usage errors; only `3` means the policy failed.
    """
    runner = CliRunner()

    # 1 — raised by the CLI itself.
    assert runner.invoke(app, ["validate", "does-not-exist.otm.yaml"]).exit_code == 1
    assert runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--fail-on", "nope"]).exit_code == 1

    # 2 — raised by Typer/Click while parsing.
    assert runner.invoke(app, ["analyze", str(_MINIMAL), "-m", "nope"]).exit_code == 2
    assert runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "-f", "nope"]).exit_code == 2
    assert runner.invoke(app, ["analyze", str(_MINIMAL), "--flag-that-does-not-exist"]).exit_code == 2
    assert runner.invoke(app, ["validate"]).exit_code == 2

    # 0 and 3 — the two the gate owns.
    assert runner.invoke(app, ["diff", str(_MINIMAL), str(_MINIMAL), "--fail-on", "low"]).exit_code == 0


def test_fail_on_help_lists_its_allowed_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich parses `[...]` as a style tag: unescaped, the allowed-value list vanished from --help.

    The width is pinned because Rich wraps help text to the terminal, and a wrapped line would
    split the token and fail the assertion for a reason that has nothing to do with the escape.
    """
    monkeypatch.setenv("COLUMNS", "200")
    for command in ("diff", "diff-analysis"):
        out = CliRunner().invoke(app, [command, "--help"]).output
        assert "none|low|medium|high|critical" in out, f"`{command} --help` lost the value list"
