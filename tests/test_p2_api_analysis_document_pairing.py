"""
Regressão: um `analysis` de outro modelo não pode ser aceite ao lado de um `document`.

Enviar o documento A com a análise do modelo B devolvia 200 e produzia artefactos com
duas identidades: `/v1/remediation/backlog` rotulava a resposta com o título e a
metodologia de B, e `/v1/reports/premium` emitia um relatório com o cabeçalho de A e as
20 ameaças de B — sem qualquer aviso. O `AnalysisResult` descreve-se a si próprio
(`document_title`, alvos por `component_id`), por isso a correspondência é verificável.
"""

from __future__ import annotations

from copy import deepcopy
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
def crossed(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """Documento A emparelhado com a análise do modelo B."""
    doc_a = _document(client, _DOC_A)
    doc_b = _document(client, _DOC_B)
    return doc_a, _analysis(client, doc_b)


_CROSSED_ROUTES = [
    ("/v1/remediation/backlog", {}),
    ("/v1/reports/premium", {"level": "standard"}),
    ("/v1/exports", {"formats": ["analysis_json"]}),
]


@pytest.mark.parametrize(("path", "extra"), _CROSSED_ROUTES)
def test_crossed_document_and_analysis_is_rejected(
    client: TestClient,
    crossed: tuple[dict[str, Any], dict[str, Any]],
    path: str,
    extra: dict[str, Any],
) -> None:
    doc_a, analysis_b = crossed
    r = client.post(path, json={"document": doc_a, "analysis": analysis_b, **extra})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(("path", "extra"), _CROSSED_ROUTES)
def test_crossed_pair_carries_a_stable_error_code(
    client: TestClient,
    crossed: tuple[dict[str, Any], dict[str, Any]],
    path: str,
    extra: dict[str, Any],
) -> None:
    doc_a, analysis_b = crossed
    r = client.post(path, json={"document": doc_a, "analysis": analysis_b, **extra})
    assert r.json()["detail"]["code"] == "ANALYSIS_DOCUMENT_MISMATCH"


def test_mismatch_error_names_both_titles(
    client: TestClient,
    crossed: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """A mensagem tem de dizer *o quê* não bate certo, não só que não bate."""
    doc_a, analysis_b = crossed
    r = client.post("/v1/remediation/backlog", json={"document": doc_a, "analysis": analysis_b})
    first_error = r.json()["detail"]["errors"][0]["msg"]
    assert "Agente com ferramentas" in first_error


def _error_of_type(payload: dict[str, Any], error_type: str) -> dict[str, Any]:
    """Pin the error by its stable `type`, not by position.

    The list grew a third entry (`…stale_components`), and indexing it positionally made a
    correct addition look like a regression while proving nothing about *which* error was read.
    """
    matching = [e for e in payload["detail"]["errors"] if e["type"] == error_type]
    assert len(matching) == 1, payload["detail"]["errors"]
    return matching[0]


def test_mismatch_error_names_the_unknown_components(
    client: TestClient,
    crossed: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    doc_a, analysis_b = crossed
    r = client.post("/v1/remediation/backlog", json={"document": doc_a, "analysis": analysis_b})
    assert "agent" in _error_of_type(r.json(), "analysis_document_mismatch.components")["msg"]


def test_run_analysis_true_with_a_foreign_analysis_is_rejected(
    client: TestClient,
    crossed: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """`run_analysis: true` não corria nada: a análise estranha ganhava em silêncio."""
    doc_a, analysis_b = crossed
    r = client.post(
        "/v1/remediation/backlog",
        json={"document": doc_a, "analysis": analysis_b, "run_analysis": True},
    )
    assert r.status_code == 422, r.text


def test_a_renamed_document_no_longer_matches_its_own_analysis(client: TestClient) -> None:
    """O título é a identidade que o `AnalysisResult` carrega; mudá-lo torna o par ambíguo."""
    doc = _document(client, _DOC_A)
    analysis = _analysis(client, doc)
    doc["metadata"]["title"] = "Portal admin (renomeado)"
    r = client.post("/v1/remediation/backlog", json={"document": doc, "analysis": analysis})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(("path", "extra"), _CROSSED_ROUTES)
def test_matching_pair_still_works(client: TestClient, path: str, extra: dict[str, Any]) -> None:
    doc = _document(client, _DOC_A)
    analysis = _analysis(client, doc)
    r = client.post(path, json={"document": doc, "analysis": analysis, **extra})
    assert r.status_code == 200, r.text


def _next_revision_of(document: dict[str, Any]) -> dict[str, Any]:
    """O mesmo modelo, renomeado e com um componente a mais — o que uma release faz."""
    revised = deepcopy(document)
    revised["metadata"]["title"] = f"{document['metadata']['title']} (v2)"
    revised["components"].append({"id": "new_worker", "name": "New worker", "kind": "process"})
    return revised


def test_premium_baseline_analysis_of_a_previous_version_is_not_blocked(client: TestClient) -> None:
    """`baseline_analysis` é, por definição, de outra versão — a divergência é o objetivo.

    O baseline usado aqui era a análise de **outro template** (`ai-agent-tool-use` ao lado de
    `admin-portal`), ou seja de outro sistema, e isso fixava como especificação o defeito que
    `test_p2r5_api_premium_baseline_system.py` corrige: a API devolvia 200 e uma secção
    `## Baseline / diff` sobre uma revisão que nunca existiu. A afirmação que este teste existe
    para proteger é a outra, e continua verdadeira: uma revisão anterior **do mesmo modelo**
    é aceite, mesmo depois de renomeada e de crescer.
    """
    previous = _document(client, _DOC_A)
    baseline = _analysis(client, previous)
    current = _next_revision_of(previous)
    r = client.post(
        "/v1/reports/premium",
        json={
            "document": current,
            "analysis": _analysis(client, current),
            "baseline_analysis": baseline,
            "level": "standard",
        },
    )
    assert r.status_code == 200, r.text


def test_premium_baseline_analysis_of_another_system_is_blocked(client: TestClient) -> None:
    """O contra-caso que o teste acima costumava afirmar ao contrário."""
    doc = _document(client, _DOC_A)
    other = _analysis(client, _document(client, _DOC_B))
    r = client.post(
        "/v1/reports/premium",
        json={
            "document": doc,
            "analysis": _analysis(client, doc),
            "baseline_analysis": other,
            "level": "standard",
        },
    )
    assert r.status_code == 422, r.text
