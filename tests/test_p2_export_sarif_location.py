"""Every SARIF result must be locatable, and the driver must name the product release.

`otm analyze --help` advertises the SARIF as "e.g. for GitHub code scanning" and `action.yml`
wires `upload-sarif` to `github/codeql-action/upload-sarif`. GitHub's SARIF support
documentation marks `result.locations[]`, `location.physicalLocation`,
`physicalLocation.artifactLocation.uri` and `physicalLocation.region.startLine` as required for
code scanning; the exporter emitted only `logicalLocations`, so 0 of 26 results on the stock
model carried an artifact URI and the advertised upload path could not produce located alerts.

Second defect in the same run object: `tool.driver.version` published `engine_version`
(`0.1.0`, never bumped) under `driver.name = "App Suite Modeling"`, so two scans from different
product releases were indistinguishable while `otm --version` reported 7.9.0.
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import StrideCategory, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_exporters import export_analysis_sarif, export_analysis_sarif_obj
from otm_exporters.analysis_sarif import product_version
from otm_threat_engine import analyze_document
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


@pytest.fixture
def stock_sarif() -> dict[str, Any]:
    return export_analysis_sarif_obj(analyze_document(load_document_from_yaml_path(_MINIMAL)))


def _results(sarif: dict[str, Any]) -> list[dict[str, Any]]:
    return sarif["runs"][0]["results"]


def test_the_stock_model_produces_results_at_all(stock_sarif: dict[str, Any]) -> None:
    """Guards the two counters below from passing vacuously on an empty result list."""
    assert len(_results(stock_sarif)) > 0


def test_no_result_is_left_without_a_location(stock_sarif: dict[str, Any]) -> None:
    assert [r for r in _results(stock_sarif) if not r.get("locations")] == []


def test_every_location_carries_a_physical_location(stock_sarif: dict[str, Any]) -> None:
    """This is the exact counter the bug measured: 0 of 26 results had one."""
    missing = [r["ruleId"] for r in _results(stock_sarif) if "physicalLocation" not in r["locations"][0]]

    assert missing == []


def test_the_artifact_uri_is_the_model_file_the_caller_named() -> None:
    sarif = export_analysis_sarif_obj(
        analyze_document(load_document_from_yaml_path(_MINIMAL)), model_uri="threat-models/orders.otm.yaml"
    )
    location = _results(sarif)[0]["locations"][0]["physicalLocation"]

    assert location["artifactLocation"]["uri"] == "threat-models/orders.otm.yaml"


def test_the_artifact_uri_falls_back_to_the_canonical_model_name(stock_sarif: dict[str, Any]) -> None:
    """The API analyses an uploaded document with no path; GitHub still needs a uri."""
    location = _results(stock_sarif)[0]["locations"][0]["physicalLocation"]

    assert location["artifactLocation"]["uri"] == "threat-model.otm.yaml"


def test_the_region_anchors_at_the_first_line(stock_sarif: dict[str, Any]) -> None:
    """A threat has no source line, and GitHub requires `region.startLine` to ingest a result."""
    region = _results(stock_sarif)[0]["locations"][0]["physicalLocation"]["region"]

    assert region["startLine"] == 1


def test_the_logical_location_survives_next_to_the_physical_one(stock_sarif: dict[str, Any]) -> None:
    """The target id is what makes an alert readable; adding the file must not displace it."""
    logical = _results(stock_sarif)[0]["locations"][0]["logicalLocations"][0]

    assert logical["kind"] in {"component", "dataflow", "asset"}


def _untargeted_result() -> AnalysisResult:
    threat = HeuristicThreat(
        id="untargeted",
        title="Untargeted",
        description="synthetic threat with no target",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(3, 3),
    )
    return AnalysisResult(
        engine_version="test",
        methodology=ThreatModelMethodology.STRIDE,
        document_title="SARIF location contract",
        heuristic_threats=[threat],
    )


def test_a_threat_with_no_target_is_still_anchored_to_the_model_file() -> None:
    """A model-level threat has no component to name, but it still belongs to the model file.

    Superseded the earlier contract, which dropped `locations` entirely whenever the threat
    declared no target: PASTA emits five such threats and none of them could produce a located
    code-scanning alert. Only the `logicalLocations` half depends on a target.
    """
    res = _results(export_analysis_sarif_obj(_untargeted_result()))[0]

    assert res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "threat-model.otm.yaml"


def test_a_threat_with_no_target_carries_no_logical_location() -> None:
    """An empty `logicalLocations` array would be invalid SARIF, so the key stays absent."""
    res = _results(export_analysis_sarif_obj(_untargeted_result()))[0]

    assert "logicalLocations" not in res["locations"][0]


def test_the_driver_version_is_the_product_version(stock_sarif: dict[str, Any]) -> None:
    driver = stock_sarif["runs"][0]["tool"]["driver"]

    assert driver["version"] == importlib.metadata.version("open-threat-model")


def test_the_driver_version_is_no_longer_the_engine_version() -> None:
    """`engine_version` is a separate, never-incremented constant — it must not be the tool version."""
    driver = export_analysis_sarif_obj(_untargeted_result())["runs"][0]["tool"]["driver"]

    assert driver["version"] != "test"


def test_the_engine_version_is_still_published_in_the_property_bag() -> None:
    """Nothing is lost: a consumer that wants the heuristics version can still read it."""
    driver = export_analysis_sarif_obj(_untargeted_result())["runs"][0]["tool"]["driver"]

    assert driver["properties"]["engineVersion"] == "test"


def test_product_version_falls_back_when_the_distribution_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running from a source checkout without an install must not blow up the export."""

    def _absent(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError("open-threat-model")

    monkeypatch.setattr(importlib.metadata, "version", _absent)

    assert product_version() == "dev"


def test_the_text_export_passes_the_model_uri_through() -> None:
    out = export_analysis_sarif(
        analyze_document(load_document_from_yaml_path(_MINIMAL)), model_uri="models/api.otm.yaml"
    )

    assert '"uri": "models/api.otm.yaml"' in out


def test_the_export_is_still_deterministic() -> None:
    result = analyze_document(load_document_from_yaml_path(_MINIMAL))

    assert export_analysis_sarif(result) == export_analysis_sarif(result)
