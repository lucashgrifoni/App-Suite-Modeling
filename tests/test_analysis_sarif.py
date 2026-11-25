"""SARIF 2.1.0 export of analysis threats (P1 evolution step).

`otm analyze --sarif-out` emits suggested threats in SARIF so they can be
uploaded to GitHub code scanning or any SARIF-aware pipeline. Rule `helpUri`
links to the CWE/CAPEC reference attached by the framework map.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_sarif, export_analysis_sarif_obj
from otm_threat_engine import analyze_document
from typer.testing import CliRunner

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


def _result():
    return analyze_document(load_document_from_yaml_path(_MINIMAL))


def test_sarif_structure_is_2_1_0() -> None:
    obj = export_analysis_sarif_obj(_result())
    assert obj["version"] == "2.1.0"
    assert obj["$schema"].endswith("sarif-2.1.0.json")
    driver = obj["runs"][0]["tool"]["driver"]
    assert driver["name"] == "App Suite Modeling"
    assert driver["rules"]


def test_sarif_one_result_per_active_threat_with_valid_levels() -> None:
    result = _result()
    obj = export_analysis_sarif_obj(result)
    active = [t for t in result.heuristic_threats if not t.skipped_as_duplicate]
    results = obj["runs"][0]["results"]
    assert len(results) == len(active)
    for r in results:
        assert r["level"] in {"error", "warning", "note"}
        assert r["ruleId"]
        assert r["partialFingerprints"]["otmThreatId"]
        assert "references" in r["properties"]


def test_sarif_rule_help_uri_links_to_cwe_or_capec() -> None:
    rules = export_analysis_sarif_obj(_result())["runs"][0]["tool"]["driver"]["rules"]
    links = (urlsplit(rule["helpUri"]) for rule in rules if "helpUri" in rule)
    assert any(link.scheme == "https" and link.hostname in {"cwe.mitre.org", "capec.mitre.org"} for link in links)


def test_sarif_is_valid_json_and_deterministic() -> None:
    result = _result()
    out = export_analysis_sarif(result)
    assert out == export_analysis_sarif(result)
    json.loads(out)  # parses as JSON


def test_cli_analyze_sarif_out_writes_sarif_file(tmp_path: Path) -> None:
    out = tmp_path / "threats.sarif"
    res = CliRunner().invoke(app, ["analyze", str(_MINIMAL), "--sarif-out", str(out), "--quiet"])
    assert res.exit_code == 0, res.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["results"]
