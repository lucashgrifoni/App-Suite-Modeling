"""Model-level threats must still be anchored to the model file in SARIF.

`--sarif-out` is advertised for GitHub code scanning and `action.yml` feeds it to
`upload-sarif`. The exporter only attached `locations` when the threat named a component, data
flow or asset, so PASTA's five model-level threats — `pasta_external_exposure`,
`pasta_attack_chain_abuse`, `pasta_vulnerability_exposure`, `pasta_critical_integration_path`,
`pasta_high_value_asset_impact` — were emitted with no `locations` key at all, and by the
exporter's own documented rule (`physicalLocation` + `region.startLine` are what GitHub needs to
ingest a result) they could not produce a located alert. Measured on
`examples/saas-ordering-v1.otm.yaml`: 5 of 33 PASTA results, 0 of 27 STRIDE results.

The `physicalLocation` never depended on the target; only `logicalLocations` does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_exporters import export_analysis_sarif_obj
from otm_threat_engine import analyze_document

_MODEL = Path(__file__).resolve().parents[1] / "examples" / "saas-ordering-v1.otm.yaml"


def _results(methodology: ThreatModelMethodology, **kwargs: Any) -> list[dict[str, Any]]:
    result = analyze_document(load_document_from_yaml_path(_MODEL), methodology=methodology)
    return export_analysis_sarif_obj(result, **kwargs)["runs"][0]["results"]


@pytest.fixture
def pasta_results() -> list[dict[str, Any]]:
    return _results(ThreatModelMethodology.PASTA)


def test_the_pasta_run_still_produces_results(pasta_results: list[dict[str, Any]]) -> None:
    """Guards the counters below from passing vacuously."""
    assert len(pasta_results) > 0


def test_no_pasta_result_is_left_without_locations(pasta_results: list[dict[str, Any]]) -> None:
    assert [r["ruleId"] for r in pasta_results if "locations" not in r] == []


def test_every_pasta_result_carries_the_model_artifact(pasta_results: list[dict[str, Any]]) -> None:
    uris = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for r in pasta_results}

    assert uris == {"threat-model.otm.yaml"}


def test_every_pasta_result_anchors_at_the_first_line(pasta_results: list[dict[str, Any]]) -> None:
    lines = {r["locations"][0]["physicalLocation"]["region"]["startLine"] for r in pasta_results}

    assert lines == {1}


def test_the_model_level_threats_are_the_ones_without_a_logical_location(
    pasta_results: list[dict[str, Any]],
) -> None:
    """These five are the whole population of the defect; nothing else lost its target."""
    untargeted = {
        r["partialFingerprints"]["otmThreatId"] for r in pasta_results if "logicalLocations" not in r["locations"][0]
    }

    assert untargeted == {
        "pasta_attack_chain_abuse",
        "pasta_critical_integration_path",
        "pasta_external_exposure",
        "pasta_high_value_asset_impact",
        "pasta_vulnerability_exposure",
    }


def test_a_targeted_threat_still_names_its_target(pasta_results: list[dict[str, Any]]) -> None:
    targeted = [r for r in pasta_results if "logicalLocations" in r["locations"][0]]

    assert targeted[0]["locations"][0]["logicalLocations"][0]["kind"] in {"component", "dataflow", "asset"}


def test_the_caller_supplied_model_uri_reaches_a_model_level_result() -> None:
    """The URI the CLI will pass has to land on these results too, not only on targeted ones."""
    results = _results(ThreatModelMethodology.PASTA, model_uri="threat-models/orders.otm.yaml")
    untargeted = [r for r in results if "logicalLocations" not in r["locations"][0]]

    assert untargeted[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == (
        "threat-models/orders.otm.yaml"
    )


def test_stride_results_are_unaffected() -> None:
    """Only PASTA emits model-level threats; the other methodologies must not change shape."""
    stride = _results(ThreatModelMethodology.STRIDE)

    assert [r["ruleId"] for r in stride if "logicalLocations" not in r["locations"][0]] == []
