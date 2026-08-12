"""
Regressão: HEAD nas rotas GET de `/v1/templates`.

RFC 9110 9.3.2: HEAD é o GET sem corpo, por isso um recurso que serve GET deve servir
HEAD — é o que verificadores de links, caches e sondas usam. O `APIRoute` do FastAPI, ao
contrário do `Route` do Starlette, regista só o método declarado, pelo que `/openapi.json`
e `/docs` (dados pelo framework) respondiam a HEAD e as rotas da aplicação davam 405.

`HEAD /` continua 405 por decisão anterior deliberada: `tests/test_api_p1_health_head.py`
usa-o como controlo de que HEAD não foi ligado em bloco. Ver o relatório da fase.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_TEMPLATE_GET_ROUTES = ["/v1/templates", "/v1/templates/admin-portal"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("path", _TEMPLATE_GET_ROUTES)
def test_head_matches_get_status(client: TestClient, path: str) -> None:
    assert client.head(path).status_code == client.get(path).status_code


@pytest.mark.parametrize("path", _TEMPLATE_GET_ROUTES)
def test_head_is_not_a_405(client: TestClient, path: str) -> None:
    assert client.head(path).status_code == 200


def test_head_on_an_unknown_template_still_reports_not_found(client: TestClient) -> None:
    assert client.head("/v1/templates/no-such-template").status_code == 404


def test_head_did_not_leak_onto_post_only_routes(client: TestClient) -> None:
    """HEAD acompanha GET; não é um passe-livre para métodos que a rota não serve."""
    assert client.head("/v1/models").status_code == 405


def test_head_on_templates_is_absent_from_the_openapi_schema(client: TestClient) -> None:
    """Uma rota com GET e HEAD partilharia `operationId` e produziria um OpenAPI inválido."""
    assert set(client.get("/openapi.json").json()["paths"]["/v1/templates"]) == {"get"}


def test_get_on_templates_still_returns_the_catalog(client: TestClient) -> None:
    assert client.get("/v1/templates").json()
