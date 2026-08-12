"""
Regressão: `/v1/models/compare` aceitava um par `baseline_analysis`/`revised_analysis` que não
tinha sido produzido para os documentos enviados, e reportava o delta **ao contrário**.

Trocar as duas análises (um copy/paste num passo de CI) devolvia 200 e uma transição de
metodologia invertida (`plot4ai→stride` quando a real é `stride→plot4ai`), com `structural` e
`aggregate` — calculados a partir dos documentos certos — a dar-lhe ar de resposta legítima. As
rotas irmãs (`/v1/exports`, `/v1/remediation/backlog`, `/v1/reports/premium`) já rejeitavam o
mesmo par cruzado com 422 ANALYSIS_DOCUMENT_MISMATCH; a compare ficou de fora, apesar de já
validar outro invariante sobre esses mesmos dois campos ("ambos ou nenhum").
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_DOC_A = "admin-portal"
_DOC_B = "ai-agent-tool-use"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _document(client: TestClient, template_id: str) -> dict[str, Any]:
    return client.post(f"/v1/templates/{template_id}/instantiate").json()["document"]


def _analysis(client: TestClient, document: dict[str, Any]) -> dict[str, Any]:
    return client.post("/v1/models/analyze", json={"document": document}).json()


@pytest.fixture
def pair(client: TestClient) -> dict[str, Any]:
    """Dois documentos e as análises **certas** de cada um."""
    doc_a = _document(client, _DOC_A)
    doc_b = _document(client, _DOC_B)
    return {
        "baseline": doc_a,
        "revised": doc_b,
        "baseline_analysis": _analysis(client, doc_a),
        "revised_analysis": _analysis(client, doc_b),
    }


def _swapped(pair: dict[str, Any]) -> dict[str, Any]:
    return {**pair, "baseline_analysis": pair["revised_analysis"], "revised_analysis": pair["baseline_analysis"]}


def test_swapped_analyses_are_rejected(client: TestClient, pair: dict[str, Any]) -> None:
    """O sintoma: 200 com o delta ao contrário."""
    r = client.post("/v1/models/compare", json=_swapped(pair))

    assert r.status_code == 422, r.text


def test_swapped_analyses_carry_the_stable_error_code(client: TestClient, pair: dict[str, Any]) -> None:
    """O mesmo código que as rotas irmãs já devolvem para o mesmo erro."""
    r = client.post("/v1/models/compare", json=_swapped(pair))

    assert r.json()["detail"]["code"] == "ANALYSIS_DOCUMENT_MISMATCH"


def test_the_rejection_names_which_of_the_two_pairs_is_wrong(client: TestClient, pair: dict[str, Any]) -> None:
    """Dizer "analysis" numa rota que não tem esse campo manda o cliente procurar no sítio errado."""
    r = client.post("/v1/models/compare", json=_swapped(pair))

    assert r.json()["detail"]["errors"][0]["loc"] == ["body", "baseline_analysis", "document_title"]


def test_the_rejection_message_names_the_baseline_field(client: TestClient, pair: dict[str, Any]) -> None:
    r = client.post("/v1/models/compare", json=_swapped(pair))

    assert "baseline_analysis" in r.json()["detail"]["message"]


def test_a_foreign_revised_analysis_alone_is_rejected(client: TestClient, pair: dict[str, Any]) -> None:
    """Só a segunda metade trocada: o baseline continua certo, o delta continua inventado."""
    body = {**pair, "revised_analysis": _analysis(client, _document(client, _DOC_A))}

    r = client.post("/v1/models/compare", json=body)

    assert r.status_code == 422, r.text


def test_a_foreign_revised_analysis_is_reported_against_its_own_field(client: TestClient, pair: dict[str, Any]) -> None:
    body = {**pair, "revised_analysis": _analysis(client, _document(client, _DOC_A))}

    r = client.post("/v1/models/compare", json=body)

    assert r.json()["detail"]["errors"][0]["loc"] == ["body", "revised_analysis", "document_title"]


def test_the_rejection_also_names_the_components_the_analysis_invented(
    client: TestClient, pair: dict[str, Any]
) -> None:
    """O outro critério de emparelhamento: alvos que não existem no documento."""
    r = client.post("/v1/models/compare", json=_swapped(pair))

    types = [e["type"] for e in r.json()["detail"]["errors"]]
    assert "analysis_document_mismatch.components" in types


# --- o que a rota tem de continuar a fazer ---------------------------------------------


def test_the_correct_pairing_still_compares(client: TestClient, pair: dict[str, Any]) -> None:
    r = client.post("/v1/models/compare", json=pair)

    assert r.status_code == 200, r.text


def test_the_correct_pairing_reports_the_real_transition(client: TestClient, pair: dict[str, Any]) -> None:
    """A transição real é `stride→plot4ai`; era isto que a versão trocada invertia."""
    analysis = client.post("/v1/models/compare", json=pair).json()["analysis"]

    assert (analysis["methodology_before"], analysis["methodology_after"]) == ("stride", "plot4ai")


def test_two_versions_of_the_same_model_still_compare(client: TestClient) -> None:
    """O caso de uso do endpoint: mesmo modelo, revisto, com a análise de cada versão."""
    doc = _document(client, _DOC_A)
    baseline_analysis = _analysis(client, doc)
    added = {**doc["components"][0], "id": "new_cache", "name": "Cache de sessão"}
    revised = {**doc, "components": [*doc["components"], added]}
    body = {
        "baseline": doc,
        "revised": revised,
        "baseline_analysis": baseline_analysis,
        "revised_analysis": _analysis(client, revised),
    }

    r = client.post("/v1/models/compare", json=body)

    assert r.status_code == 200, r.text


def test_structural_only_comparison_needs_no_analysis(client: TestClient, pair: dict[str, Any]) -> None:
    r = client.post("/v1/models/compare", json={"baseline": pair["baseline"], "revised": pair["revised"]})

    assert r.status_code == 200, r.text


def test_run_analysis_true_still_produces_matching_analyses(client: TestClient, pair: dict[str, Any]) -> None:
    """O motor corre sobre os documentos enviados, por isso o par nunca pode divergir."""
    body = {"baseline": pair["baseline"], "revised": pair["revised"], "run_analysis": True}

    r = client.post("/v1/models/compare", json=body)

    assert r.status_code == 200, r.text


def test_an_invalid_analysis_is_still_a_validation_error(client: TestClient, pair: dict[str, Any]) -> None:
    """A validação de forma tem de continuar a vir antes da de emparelhamento."""
    body = {**pair, "baseline_analysis": {"bad": 1}, "revised_analysis": {"bad": 2}}

    r = client.post("/v1/models/compare", json=body)

    assert r.json()["detail"]["code"] == "ANALYSIS_VALIDATION_ERROR"


def test_premium_baseline_analysis_of_another_version_is_still_allowed(client: TestClient) -> None:
    """A exceção real: em `/v1/reports/premium` não há documento com que comparar o baseline."""
    doc = _document(client, _DOC_A)
    body = {
        "document": doc,
        "analysis": _analysis(client, doc),
        "baseline_analysis": _analysis(client, _document(client, _DOC_B)),
        "level": "standard",
    }

    r = client.post("/v1/reports/premium", json=body)

    assert r.status_code == 200, r.text
