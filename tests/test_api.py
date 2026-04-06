"""Testes da API FastAPI (TestClient)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_industry_packs.loader import list_template_ids

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_x_request_id_echo(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-ID": "trace-cli-e2e"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "trace-cli-e2e"


def test_x_request_id_generated(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) >= 8


def test_openapi_available(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "App Suite Modeling API"
    paths = spec["paths"]
    assert "/v1/models" in paths
    assert "/v1/models/precheck" in paths
    assert "/v1/models/diff" in paths
    assert "/v1/models/compare" in paths
    assert "/v1/analyses/diff" in paths
    assert "/v1/templates" in paths
    assert "/v1/templates/{template_id}" in paths
    assert "/v1/reports/premium" in paths


def test_create_model(client: TestClient) -> None:
    r = client.post("/v1/models")
    assert r.status_code == 201
    data = r.json()
    assert "document" in data
    assert data["document"]["metadata"]["title"]


def test_models_compare_ok(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    r = client.post(
        "/v1/models/compare",
        json={"baseline": d, "revised": d},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["has_structural_changes"] is False
    assert "structural" in body
    assert "key_insights" in body


def test_reports_premium_markdown(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    ar = client.post("/v1/models/analyze", json={"document": d}).json()
    r = client.post(
        "/v1/reports/premium",
        json={
            "document": d,
            "analysis": ar,
            "level": "standard",
            "output_format": "markdown",
        },
    )
    assert r.status_code == 200
    assert "Executive summary" in r.text


def test_reports_premium_markdown_locale_en(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    ar = client.post("/v1/models/analyze", json={"document": d}).json()
    r = client.post(
        "/v1/reports/premium",
        json={
            "document": d,
            "analysis": ar,
            "level": "executive",
            "output_format": "markdown",
            "locale": "en",
        },
    )
    assert r.status_code == 200
    assert "## Executive cover" in r.text


def test_reports_premium_pdf(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    d = doc.model_dump(mode="json", by_alias=True)
    ar = client.post("/v1/models/analyze", json={"document": d}).json()
    r = client.post(
        "/v1/reports/premium",
        json={
            "document": d,
            "analysis": ar,
            "level": "executive",
            "output_format": "pdf",
        },
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_analyses_diff_ok(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    b = client.post("/v1/models/analyze", json={"document": doc.model_dump(mode="json", by_alias=True)}).json()
    r = client.post("/v1/models/analyze", json={"document": doc.model_dump(mode="json", by_alias=True)}).json()
    out = client.post("/v1/analyses/diff", json={"baseline_analysis": b, "revised_analysis": r})
    assert out.status_code == 200
    assert out.json()["methodology_before"] == out.json()["methodology_after"]


def test_models_diff_ok(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    payload = {
        "baseline": doc.model_dump(mode="json", by_alias=True),
        "revised": doc.model_dump(mode="json", by_alias=True),
    }
    r = client.post("/v1/models/diff", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["baseline_title"] == doc.metadata.title
    assert body["revised_title"] == doc.metadata.title
    assert "summary_line" in body


def test_validate_ok(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    payload = {"document": doc.model_dump(mode="json", by_alias=True)}
    r = client.post("/v1/models/validate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["title"]
    assert body["component_count"] >= 0


def test_models_precheck_ok(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/precheck",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    body = r.json()
    assert "precheck" in body
    assert body["precheck"]["score_0_100"] >= 0
    assert "methodology_fit_matrix" in body["precheck"]
    assert "stride" in body["precheck"]["methodology_fit_matrix"]
    assert "methodology_completeness" in body


def test_validate_invalid_document(client: TestClient) -> None:
    r = client.post("/v1/models/validate", json={"document": {"invalid": True}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "DOCUMENT_VALIDATION_ERROR"
    assert set(detail.keys()) == {"code", "message", "errors"}


def test_validate_invalid_document_message_pt_br_accept_language(client: TestClient) -> None:
    r = client.post(
        "/v1/models/validate",
        json={"document": {"invalid": True}},
        headers={"Accept-Language": "pt-BR"},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "não satisfaz" in detail["message"].lower()


def test_validate_invalid_document_message_en_default(client: TestClient) -> None:
    r = client.post("/v1/models/validate", json={"document": {"invalid": True}})
    assert r.status_code == 422
    assert "does not satisfy" in r.json()["detail"]["message"].lower()


def test_validate_invalid_document_message_en_when_accept_language_unlisted(client: TestClient) -> None:
    """Only pt* and en* map to localized messages; other tags fall back to English."""
    r = client.post(
        "/v1/models/validate",
        json={"document": {"invalid": True}},
        headers={"Accept-Language": "fr-CA, de-DE;q=0.9"},
    )
    assert r.status_code == 422
    assert "does not satisfy" in r.json()["detail"]["message"].lower()
    assert "não satisfaz" not in r.json()["detail"]["message"].lower()


def test_request_validation_error_message_en_when_accept_language_unlisted(client: TestClient) -> None:
    r = client.post(
        "/v1/models/validate",
        json={},
        headers={"Accept-Language": "xx-Invalid, fr;q=0.8"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    assert "invalid" in body["message"].lower()
    assert "inválidos" not in body["message"].lower()


def test_request_validation_error_message_pt_br_accept_language(client: TestClient) -> None:
    r = client.post("/v1/models/validate", json={}, headers={"Accept-Language": "pt,en;q=0.5"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    assert "inválidos" in body["message"].lower()


def test_validate_missing_body_field_uses_request_validation_handler(client: TestClient) -> None:
    """Corpo que falha na validação Pydantic do FastAPI (campos em falta no envelope)."""
    r = client.post("/v1/models/validate", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    assert body["message"]
    assert body["status"] == 422
    assert isinstance(body["errors"], list) and body["errors"]
    assert "invalid" in body["message"].lower()


def test_remediation_input_error_message_pt_br_accept_language(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/remediation/backlog",
        json={"document": doc.model_dump(mode="json", by_alias=True), "run_analysis": False},
        headers={"Accept-Language": "pt-BR"},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "REMEDIATION_INPUT"
    assert "forneça" in detail["message"].lower() or "defina" in detail["message"].lower()


def test_remediation_input_error_message_en_default(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/remediation/backlog",
        json={"document": doc.model_dump(mode="json", by_alias=True), "run_analysis": False},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "REMEDIATION_INPUT"
    assert "provide" in detail["message"].lower()


def test_analyze_minimal(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/analyze",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    out = r.json()
    assert out["engine_version"]
    assert "heuristic_threats" in out


def test_analyze_with_explicit_methodology(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "methodology": "cia_die",
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["methodology"] == "cia_die"
    assert "methodology_recommendation_reason" in out
    assert "explanations" in out


def test_recommend_methodology_endpoint(client: TestClient) -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    doc = base.model_copy(update={"metadata": Metadata(title="Sistema LGPD com dados pessoais")})
    r = client.post(
        "/v1/models/recommend-methodology",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["methodology"] == "linddun"
    assert payload["reason"]
    assert payload.get("explanations")
    assert payload["explanations"][0]["type"] == "methodology_recommendation"


def test_analyze_with_auto_methodology(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Sistema LGPD com PII")}
    )
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "auto_recommend_methodology": True,
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["methodology"] == "linddun"
    assert payload["methodology_recommendation_reason"]
    assert payload.get("explanations")


def test_recommend_methodology_plot4ai(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Plataforma LLM com RAG, prompts e agentes")}
    )
    r = client.post(
        "/v1/models/recommend-methodology",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["methodology"] == "plot4ai"


def test_analyze_with_explicit_pasta(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "methodology": "pasta",
        },
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["methodology"] == "pasta"
    assert any(x["id"].startswith("pasta_") for x in payload["heuristic_threats"])


def test_list_templates(client: TestClient) -> None:
    r = client.get("/v1/templates")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    ids = {x["id"] for x in items}
    assert ids == set(list_template_ids())


def test_instantiate_unknown_template(client: TestClient) -> None:
    r = client.post("/v1/templates/nao_existe_xxx/instantiate")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TEMPLATE_NOT_FOUND"


def test_instantiate_known_template(client: TestClient) -> None:
    ids = list_template_ids()
    if not ids:
        pytest.skip("sem templates embutidos")
    tid = ids[0]
    r = client.post(f"/v1/templates/{tid}/instantiate")
    assert r.status_code == 201
    assert r.json()["document"]["metadata"]["title"]


def test_export_mermaid(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/exports",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "formats": ["flowchart_mermaid", "document_markdown"],
        },
    )
    assert r.status_code == 200
    arts = r.json()["artifacts"]
    assert "flowchart_mermaid" in arts
    assert arts["flowchart_mermaid"].startswith("flowchart LR")


def test_export_document_markdown_locale_en(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/exports",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "formats": ["document_markdown"],
            "locale": "en",
        },
    )
    assert r.status_code == 200
    md = r.json()["artifacts"]["document_markdown"]
    assert "## Components" in md


def test_export_bundle_runs_analysis(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/exports",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "formats": ["bundle_json"],
        },
    )
    assert r.status_code == 200
    bundle = json.loads(r.json()["artifacts"]["bundle_json"])
    assert bundle["document"] and bundle["analysis"]


def test_analyze_unknown_pack_detail_shape(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "pack_id": "pack_que_nao_existe_xxx",
        },
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "PACK_NOT_FOUND"
    assert isinstance(detail["message"], str) and detail["message"]
    assert set(detail.keys()) == {"code", "message"}


def test_export_unknown_pack_detail_shape(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/exports",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "formats": ["bundle_json"],
            "pack_id": "pack_que_nao_existe_xxx",
        },
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "PACK_NOT_FOUND"
    assert isinstance(detail["message"], str) and detail["message"]
    assert set(detail.keys()) == {"code", "message"}


def test_export_invalid_analysis_detail_shape(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/exports",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "formats": ["analysis_json"],
            "analysis": {"invalid": True},
        },
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "ANALYSIS_VALIDATION_ERROR"
    assert isinstance(detail["message"], str) and detail["message"]
    assert isinstance(detail["errors"], list) and detail["errors"]
    assert set(detail.keys()) == {"code", "message", "errors"}


def test_analyze_contract_keys_stable(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = client.post(
        "/v1/models/analyze",
        json={"document": doc.model_dump(mode="json", by_alias=True)},
    )
    assert r.status_code == 200
    out = r.json()
    expected_top = {
        "engine_version",
        "methodology",
        "methodology_recommendation_reason",
        "methodology_insights",
        "document_title",
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats",
        "summary",
        "industry_pack_id",
        "pack_control_hints",
        "explanations",
        "ai_system_context",
    }
    assert expected_top.issubset(set(out.keys()))
    summary_expected = {
        "structural_findings",
        "trust_boundary_findings",
        "heuristic_threats_generated",
        "heuristic_threats_skipped_duplicate",
        "pack_threats_generated",
        "pack_threats_skipped_duplicate",
        "max_risk_score",
        "framework_ref_counts_by_catalog",
    }
    assert summary_expected.issubset(set(out["summary"].keys()))


def test_analyze_methodology_outputs_keep_contract(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    methodologies = [
        "stride",
        "linddun",
        "nist_data_centric",
        "octave_allegro",
        "cia_die",
        "pasta",
        "plot4ai",
    ]
    for m in methodologies:
        r = client.post(
            "/v1/models/analyze",
            json={
                "document": doc.model_dump(mode="json", by_alias=True),
                "methodology": m,
            },
        )
        assert r.status_code == 200
        out = r.json()
        assert out["methodology"] == m
        assert isinstance(out["heuristic_threats"], list)
        assert "summary" in out and "max_risk_score" in out["summary"]


def test_analyze_plot4ai_contains_specialized_insights(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Plataforma LLM com RAG e agentes")}
    )
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "methodology": "plot4ai",
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["methodology"] == "plot4ai"
    assert out["methodology_insights"] is not None
    assert out["methodology_insights"]["profile"]
    assert out.get("ai_system_context") is not None
    assert out["ai_system_context"]["pattern_tags"]
