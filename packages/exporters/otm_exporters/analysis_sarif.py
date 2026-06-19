"""SARIF 2.1.0 export of analysis threats.

Lets `otm analyze` output flow into GitHub code scanning (or any SARIF-aware
pipeline): each suggested threat becomes a SARIF `result`, grouped by a rule per
methodology+STRIDE category, with `helpUri` pointing at the threat's CWE/CAPEC
reference (from the framework map). Deterministic output (stable ordering and
fingerprints) so it diffs cleanly in CI.

SARIF spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import json
from typing import Any

from otm_threat_engine.result import AnalysisResult, HeuristicThreat

_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_TOOL_NAME = "App Suite Modeling"
_TOOL_URI = "https://github.com/lucashgrifoni/App-Suite-Modeling"


def _level_for_score(score: float | None) -> str:
    """Map L×I score (1-25) to a SARIF level. critical/high -> error; medium -> warning; low -> note."""
    s = score or 0
    if s >= 12:
        return "error"
    if s >= 6:
        return "warning"
    return "note"


def _help_uri(threat: HeuristicThreat) -> str | None:
    """Prefer a CWE reference, then CAPEC, for the rule's helpUri (set by the framework map)."""
    cwe = next((r for r in threat.framework_refs if r.framework == "cwe"), None)
    if cwe and cwe.control_id.startswith("CWE-"):
        return f"https://cwe.mitre.org/data/definitions/{cwe.control_id.removeprefix('CWE-')}.html"
    capec = next((r for r in threat.framework_refs if r.framework == "capec"), None)
    if capec and capec.control_id.startswith("CAPEC-"):
        return f"https://capec.mitre.org/data/definitions/{capec.control_id.removeprefix('CAPEC-')}.html"
    return None


def _rule_id(result: AnalysisResult, threat: HeuristicThreat) -> str:
    return f"{result.methodology.value}.{threat.stride.value}"


def _logical_location(threat: HeuristicThreat) -> dict[str, Any] | None:
    target = threat.target_component_id or threat.target_data_flow_id or threat.target_asset_id
    if not target:
        return None
    kind = "component" if threat.target_component_id else "dataflow" if threat.target_data_flow_id else "asset"
    return {"fullyQualifiedName": target, "kind": kind}


def export_analysis_sarif_obj(result: AnalysisResult) -> dict[str, Any]:
    """SARIF 2.1.0 object for the analysis result (one run, one result per active threat)."""
    threats = [t for t in result.heuristic_threats if not t.skipped_as_duplicate]

    rules: list[dict[str, Any]] = []
    rule_index: dict[str, int] = {}
    sarif_results: list[dict[str, Any]] = []

    for t in threats:
        rid = _rule_id(result, t)
        if rid not in rule_index:
            rule_index[rid] = len(rules)
            rule: dict[str, Any] = {
                "id": rid,
                "name": f"{result.methodology.value.upper()} {t.stride.value}",
                "shortDescription": {"text": f"{t.stride.value} threats ({result.methodology.value})"},
                "defaultConfiguration": {"level": _level_for_score(t.risk.score)},
            }
            help_uri = _help_uri(t)
            if help_uri:
                rule["helpUri"] = help_uri
            rules.append(rule)

        refs = [f"{r.framework}:{r.control_id}" for r in t.framework_refs]
        res: dict[str, Any] = {
            "ruleId": rid,
            "ruleIndex": rule_index[rid],
            "level": _level_for_score(t.risk.score),
            "message": {"text": f"{t.title}. {t.description}".strip()},
            "partialFingerprints": {"otmThreatId": t.id},
            "properties": {
                "likelihood": t.risk.likelihood,
                "impact": t.risk.impact,
                "score": t.risk.score,
                "stride": t.stride.value,
                "references": refs,
            },
        }
        loc = _logical_location(t)
        if loc:
            res["locations"] = [{"logicalLocations": [loc]}]
        sarif_results.append(res)

    return {
        "version": "2.1.0",
        "$schema": _SARIF_SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": _TOOL_NAME,
                        "informationUri": _TOOL_URI,
                        "version": result.engine_version,
                        "rules": rules,
                    }
                },
                "results": sarif_results,
            }
        ],
    }


def export_analysis_sarif(result: AnalysisResult) -> str:
    """SARIF 2.1.0 JSON text for the analysis result."""
    return json.dumps(export_analysis_sarif_obj(result), indent=2, ensure_ascii=False)
