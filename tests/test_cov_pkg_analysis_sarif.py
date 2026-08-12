"""SARIF export — the shapes GitHub code scanning actually reacts to.

`tests/test_analysis_sarif.py` covers the export against a real analysis, which only ever
produces error/warning results with CWE-backed rules and a target on every threat. The three
cases below are the ones that change what a consumer sees and that the example model cannot
produce, so they are built from the exporter's own input type:

* a low-scoring threat must be `note`, not `warning` — GitHub's default alert filter hides
  notes, and mislabelling low-risk suggestions as warnings is how a SARIF upload becomes noise;
* a threat whose only reference is CAPEC must still get a `helpUri`;
* a threat with no target must omit `locations` entirely rather than emit an empty one, which
  SARIF consumers reject.
"""

from __future__ import annotations

from typing import Any

import pytest
from otm_core_schema import StrideCategory
from otm_core_schema.document import FrameworkRef
from otm_core_schema.enums import ThreatModelMethodology
from otm_exporters import export_analysis_sarif_obj
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def _threat(tid: str, *, likelihood: int, impact: int, **kw: Any) -> HeuristicThreat:
    return HeuristicThreat(
        id=tid,
        title=tid.replace("_", " ").title(),
        description="synthetic threat for the SARIF contract",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(likelihood, impact),
        **kw,
    )


def _sarif(*threats: HeuristicThreat) -> dict[str, Any]:
    result = AnalysisResult(
        engine_version="test",
        methodology=ThreatModelMethodology.STRIDE,
        document_title="SARIF contract",
        heuristic_threats=list(threats),
    )
    return export_analysis_sarif_obj(result)


@pytest.mark.parametrize(
    ("likelihood", "impact", "expected"),
    [
        (1, 1, "note"),  # score 1
        (5, 1, "note"),  # score 5 — last value below the warning threshold
        (2, 3, "warning"),  # score 6 — first warning
        (5, 2, "warning"),  # score 10 — last value below the error threshold
        (3, 4, "error"),  # score 12 — first error
        (5, 5, "error"),  # score 25
    ],
)
def test_the_sarif_level_follows_the_risk_score(likelihood: int, impact: int, expected: str) -> None:
    obj = _sarif(_threat("scored", likelihood=likelihood, impact=impact, target_component_id="api"))

    assert obj["runs"][0]["results"][0]["level"] == expected


def test_a_low_score_is_a_note_on_the_rule_too() -> None:
    """The rule's `defaultConfiguration` is what drives the alert severity in the UI."""
    obj = _sarif(_threat("quiet", likelihood=1, impact=1, target_component_id="api"))
    rule = obj["runs"][0]["tool"]["driver"]["rules"][0]

    assert rule["defaultConfiguration"]["level"] == "note"


def test_a_capec_only_threat_still_gets_a_help_uri() -> None:
    """CWE is preferred, but a threat mapped only to CAPEC must not be left without a link."""
    threat = _threat(
        "capec_only",
        likelihood=3,
        impact=3,
        target_component_id="api",
        framework_refs=[FrameworkRef(framework="capec", control_id="CAPEC-593")],
    )
    rule = _sarif(threat)["runs"][0]["tool"]["driver"]["rules"][0]

    assert rule["helpUri"] == "https://capec.mitre.org/data/definitions/593.html"


def test_cwe_wins_over_capec_when_both_are_present() -> None:
    threat = _threat(
        "both",
        likelihood=3,
        impact=3,
        target_component_id="api",
        framework_refs=[
            FrameworkRef(framework="capec", control_id="CAPEC-593"),
            FrameworkRef(framework="cwe", control_id="CWE-306"),
        ],
    )
    rule = _sarif(threat)["runs"][0]["tool"]["driver"]["rules"][0]

    assert rule["helpUri"] == "https://cwe.mitre.org/data/definitions/306.html"


def test_a_threat_with_no_target_omits_locations() -> None:
    """An empty `locations` array is invalid SARIF; the key has to be absent instead."""
    obj = _sarif(_threat("untargeted", likelihood=3, impact=3))
    res = obj["runs"][0]["results"][0]

    assert "locations" not in res
    assert res["partialFingerprints"]["otmThreatId"] == "untargeted"


@pytest.mark.parametrize(
    ("field", "kind"),
    [("target_component_id", "component"), ("target_data_flow_id", "dataflow"), ("target_asset_id", "asset")],
)
def test_each_target_kind_is_named_in_the_logical_location(field: str, kind: str) -> None:
    obj = _sarif(_threat("targeted", likelihood=3, impact=3, **{field: "the_target"}))
    location = obj["runs"][0]["results"][0]["locations"][0]["logicalLocations"][0]

    assert location["fullyQualifiedName"] == "the_target"
    assert location["kind"] == kind
