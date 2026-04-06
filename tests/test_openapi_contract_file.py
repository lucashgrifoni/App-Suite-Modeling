"""
Contrato OpenAPI exportado — anti-drift entre documentação HTTP e tipos TS gerados.

O ficheiro `contracts/openapi.json` é produzido por `python scripts/export_openapi.py`
e consumido por `openapi-typescript` no pacote web (`npm run contracts:sync`).
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_OPENAPI = _ROOT / "contracts" / "openapi.json"


def test_openapi_file_exists_and_defines_core_schemas() -> None:
    assert _OPENAPI.is_file(), "Run: python scripts/export_openapi.py"
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    schemas = data.get("components", {}).get("schemas", {})
    for name in (
        "AnalysisResult",
        "ThreatModelComparisonResult",
        "ComparisonResultMeta",
        "SemanticInterpretationLinkModel",
        "AnalysisDiff",
        "ModelPrecheckResponse",
        "ThreatModelDiff",
        "RemediationBacklog",
        "ExportResponse",
        "ArtifactImportResponse",
        "AntiPatternHit",
        "WizardSignalTraceEntry",
    ):
        assert name in schemas, f"OpenAPI missing schema {name}"


def test_openapi_analyze_response_refs_analysis_result() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    ref = data["paths"]["/v1/models/analyze"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/AnalysisResult"}


def test_openapi_compare_response_refs_comparison_result() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    ref = data["paths"]["/v1/models/compare"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/ThreatModelComparisonResult"}


def test_openapi_precheck_response_refs_model_precheck_response() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    ref = data["paths"]["/v1/models/precheck"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/ModelPrecheckResponse"}


def test_openapi_models_diff_refs_threat_model_diff() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    ref = data["paths"]["/v1/models/diff"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/ThreatModelDiff"}


def test_openapi_analyses_diff_refs_analysis_diff() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    ref = data["paths"]["/v1/analyses/diff"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/AnalysisDiff"}


def test_openapi_remediation_backlog_json_refs_remediation_backlog() -> None:
    data = json.loads(_OPENAPI.read_text(encoding="utf-8"))
    content = data["paths"]["/v1/remediation/backlog"]["post"]["responses"]["200"]["content"]
    ref = content["application/json"]["schema"]
    assert ref == {"$ref": "#/components/schemas/RemediationBacklog"}
