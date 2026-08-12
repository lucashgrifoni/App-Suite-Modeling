"""
Goldens semânticos compactos para respostas HTTP reais (/analyze, /compare).

Valida forma e campos de alto valor — não snapshots completos (evita fragilidade).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_EXPECT = _ROOT / "tests" / "fixtures" / "golden" / "http_api_semantic_expectations.json"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def expectations() -> dict:
    return json.loads(_EXPECT.read_text(encoding="utf-8"))


def test_http_analyze_minimal_semantic_shape(client: TestClient, expectations: dict) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    payload = {"document": doc.model_dump(mode="json", by_alias=True)}
    r = client.post("/v1/models/analyze", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    exp = expectations["analyze"]
    for key in exp["required_top_level"]:
        assert key in data, f"missing AnalysisResult.{key}"
    assert data["methodology"] == exp["methodology"]
    assert exp["document_title_substring"] in (data.get("document_title") or "")
    summary = data["summary"]
    for f in exp["summary_numeric_fields"]:
        assert f in summary
        assert isinstance(summary[f], int)
    assert isinstance(data["heuristic_threats"], list)
    mqp = data["model_quality_precheck"]
    assert isinstance(mqp, dict)
    assert mqp.get("band") in ("minimal", "good", "rich")
    assert isinstance(data["anti_pattern_hits"], list)


def test_http_compare_same_document_meta_semantic_shape(client: TestClient, expectations: dict) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["has_structural_changes"] is False
    meta = body["meta"]
    exp = expectations["compare_same_document"]
    assert meta.get("comparison_contract_version") == exp["comparison_contract_version"]
    assert meta.get("semantic_insights_version") == exp["semantic_insights_version"]
    for key in exp["meta_keys"]:
        assert key in meta, f"missing ComparisonResultMeta.{key}"
    assert isinstance(meta.get("semantic_interpretation_links"), list)
    assert isinstance(meta.get("semantic_structural_refs"), list)
    sections = meta.get("semantic_diff_sections") or {}
    assert isinstance(sections, dict)
    for k in ("improved", "worsened", "risk_impact", "structural_change_summary"):
        assert k in sections


def test_http_precheck_typed_response(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/precheck",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    data = r.json()
    assert "precheck" in data
    assert "methodology_completeness" in data
    assert "score_0_100" in data["precheck"]
    assert "state" in data["methodology_completeness"]


def test_http_analyses_diff_typed_response(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    ar = client.post("/v1/models/analyze", json={"document": d}).json()
    r = client.post(
        "/v1/analyses/diff",
        json={"baseline_analysis": ar, "revised_analysis": ar},
    )
    assert r.status_code == 200
    data = r.json()
    assert "methodology_before" in data
    assert "methodology_after" in data
    assert data["methodology_changed"] is False
