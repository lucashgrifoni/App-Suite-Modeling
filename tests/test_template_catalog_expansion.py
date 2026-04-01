"""Sanidade do catálogo de templates expandido (registo, YAML, API, filtros)."""

from __future__ import annotations

import pytest
from otm_core_schema import load_document_from_yaml
from otm_industry_packs.loader import list_template_ids, load_template_info, load_template_yaml
from otm_industry_packs.template_query import filter_template_infos, load_all_template_infos

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

# 35 IDs da expansão documentada (devem existir como ficheiros embutidos)
EXPECTED_EXPANSION_IDS: tuple[str, ...] = (
    "api-public",
    "microservices-messaging",
    "mobile-backend",
    "web-bff",
    "webhook-ingestion",
    "saas-multi-tenant",
    "serverless-api",
    "container-platform",
    "cloud-native-full",
    "batch-scheduled-jobs",
    "data-pipeline-etl",
    "identity-sso",
    "admin-portal",
    "service-identity",
    "pam-privileged-actions",
    "payment-integration",
    "third-party-api-consumer",
    "partner-integration",
    "file-upload-processing",
    "ai-llm-chat",
    "ai-rag-enterprise",
    "ai-agent-tool-use",
    "ai-sensitive-copilot",
    "ai-inference-pipeline",
    "industry-ecommerce",
    "industry-finance-core",
    "industry-telecom-oss-bss",
    "industry-transport-logistics",
    "industry-healthcare-clinical",
    "objective-internet-facing",
    "objective-sensitive-data",
    "objective-privileged-admin",
    "objective-third-party-heavy",
    "objective-ai-llm",
    "objective-high-availability",
)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_expansion_template_ids_registered() -> None:
    ids = set(list_template_ids())
    for eid in EXPECTED_EXPANSION_IDS:
        assert eid in ids, f"template em falta: {eid}"


def test_each_template_yaml_loads_document() -> None:
    for tid in list_template_ids():
        raw = load_template_yaml(tid)
        load_document_from_yaml(raw)


def test_each_template_has_manifest_with_category() -> None:
    for tid in EXPECTED_EXPANSION_IDS:
        info = load_template_info(tid)
        assert info is not None
        assert info.category
        assert info.title


def test_filter_by_category_ai() -> None:
    infos = load_all_template_infos()
    ai = filter_template_infos(infos, category="ai_llm")
    ids = {i.id for i in ai}
    assert "ai-llm-chat" in ids
    assert "api-public" not in ids


def test_filter_plot4ai_templates_have_hint() -> None:
    for tid in ("ai-llm-chat", "objective-ai-llm"):
        info = load_template_info(tid)
        assert info is not None
        assert info.suggested_methodology == "plot4ai"


def test_sensitive_objective_template_uses_linddun() -> None:
    info = load_template_info("objective-sensitive-data")
    assert info is not None
    assert info.suggested_methodology == "linddun"


def test_api_templates_list_filter(client: TestClient) -> None:
    r = client.get("/v1/templates", params={"category": "ai_llm"})
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert ids <= set(list_template_ids())
    assert "ai-rag-enterprise" in ids


def test_api_template_detail(client: TestClient) -> None:
    r = client.get("/v1/templates/ai-rag-enterprise")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "ai-rag-enterprise"
    assert body["category"] == "ai_llm"


def test_api_template_detail_404(client: TestClient) -> None:
    r = client.get("/v1/templates/nao_existe_xxx")
    assert r.status_code == 404


def test_instantiate_all_templates(client: TestClient) -> None:
    """Garante que instantiate continua válido para cada ficheiro embutido."""
    for tid in list_template_ids():
        r = client.post(f"/v1/templates/{tid}/instantiate")
        assert r.status_code == 201, tid
        assert r.json()["document"]["metadata"]["title"]
