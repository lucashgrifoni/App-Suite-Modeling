"""
Dois erros que a própria API já tinha classificado corretamente e depois estragou a caminho
do cliente.

1. **Surrogate UTF-16 solto.** `{"metadata": {"title": "\\ud800"}}` é JSON sintaticamente
   válido — é exatamente o que `JSON.stringify` de um browser emite para uma string com meio
   par substituto — e o Pydantic rejeita-o com o veredicto certo (`string_unicode`). O 422
   documentado era construído e morria a ser serializado: `errors[].input` ecoa o valor
   ofensivo, `errors[].loc` também o carrega quando o surrogate está numa *chave*, e
   `.encode("utf-8")` recusa surrogates soltos. O cliente recebia 500 `INTERNAL_ERROR` em
   seis rotas. Como remate, o `X-Request-ID` — presente em 200, 401, 422 e 429 — faltava
   precisamente nessa 500, o estado em que um cliente mais precisa do id de correlação.

2. **`detail` como string solta no 400 de corpo ilegível.** `fastapi/routing.py` levanta
   `HTTPException(400, "There was an error parsing the body")` para qualquer falha de leitura
   do corpo que não seja `JSONDecodeError` (aqui, o `RecursionError` de um JSON com 10 000
   níveis). Isso é uma **terceira** forma de erro, que `docs/features/API.md` exclui — "Não há
   exceções ao envelope nestas rotas" — e que rebenta com `TypeError: string indices must be
   integers` num cliente escrito contra o contrato. É o mesmo defeito já corrigido uma vez no
   413 do upload. A correção alinha-o com o irmão imediato: um corpo que não é JSON válido
   (o ramo `JSONDecodeError`, logo acima no FastAPI) já produzia `REQUEST_VALIDATION_ERROR`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi import Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.errors import http_exception_handler  # noqa: E402
from otm_api.main import app  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

# As seis rotas em que o surrogate produzia 500. As quatro do relatório mais `precheck` e
# `remediation/backlog`, encontradas ao reproduzir.
_SURROGATE_ROUTES: list[tuple[str, dict[str, Any]]] = [
    ("/v1/models/validate", {}),
    ("/v1/models/analyze", {}),
    ("/v1/models/precheck", {}),
    ("/v1/exports", {"formats": ["document_json"]}),
    ("/v1/reports/premium", {"run_analysis": True}),
    ("/v1/remediation/backlog", {"run_analysis": True}),
]

# Todas as rotas POST documentadas: o envelope não pode ter excepções.
_POST_ROUTES = [
    "/v1/models/validate",
    "/v1/models/analyze",
    "/v1/models/precheck",
    "/v1/exports",
    "/v1/reports/premium",
    "/v1/remediation/backlog",
    "/v1/models/diff",
    "/v1/models/compare",
    "/v1/analyses/diff",
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def _post_raw(client: TestClient, route: str, raw: bytes) -> httpx.Response:
    return client.post(route, content=raw, headers={"content-type": "application/json"})


def _with_surrogate_title(route: str, extra: dict[str, Any]) -> bytes:
    doc = _doc()
    doc["metadata"]["title"] = "\ud800"
    body: dict[str, Any] = {"document": doc, **extra}
    return json.dumps(body).encode("utf-8", "surrogatepass")


def _deeply_nested_body() -> bytes:
    """20 KB de aninhamento: `json.loads` levanta `RecursionError`, não `JSONDecodeError`."""
    return b'{"document": {"metadata": {"tags": ' + b"[" * 10_000 + b"]" * 10_000 + b"}}}"


# --- surrogate solto ------------------------------------------------------------------


@pytest.mark.parametrize(("route", "extra"), _SURROGATE_ROUTES)
def test_a_lone_surrogate_is_a_client_error_not_a_crash(client: TestClient, route: str, extra: dict[str, Any]) -> None:
    """O sintoma: 500 INTERNAL_ERROR para um input que o produto já sabia recusar."""
    assert _post_raw(client, route, _with_surrogate_title(route, extra)).status_code == 422


@pytest.mark.parametrize(("route", "extra"), _SURROGATE_ROUTES)
def test_the_lone_surrogate_response_uses_the_documented_code(
    client: TestClient, route: str, extra: dict[str, Any]
) -> None:
    body = _post_raw(client, route, _with_surrogate_title(route, extra)).json()

    assert body["detail"]["code"] == "DOCUMENT_VALIDATION_ERROR"


def test_the_response_still_names_the_offending_field(client: TestClient) -> None:
    """Um 422 sem o `loc` do campo obriga o utilizador a adivinhar qual string é a má."""
    body = _post_raw(client, "/v1/models/validate", _with_surrogate_title("", {})).json()

    assert any("title" in err["loc"] for err in body["detail"]["errors"])


def test_the_echoed_value_survives_as_the_same_code_point(client: TestClient) -> None:
    """`\\ud800` reescrito como escape JSON continua a ler-se como o valor que o cliente enviou."""
    r = _post_raw(client, "/v1/models/validate", _with_surrogate_title("", {}))

    assert r.json()["detail"]["errors"][0]["input"] == "\ud800"


def test_a_surrogate_in_a_key_is_handled_too(client: TestClient) -> None:
    """O valor ofensivo também chega a `errors[].loc`, que não passa pelo truncador."""
    doc = _doc()
    doc["\ud800"] = 1
    raw = json.dumps({"document": doc}).encode("utf-8", "surrogatepass")

    assert _post_raw(client, "/v1/models/validate", raw).status_code == 422


def test_a_surrogate_in_the_request_envelope_is_handled_too(client: TestClient) -> None:
    """Caminho irmão: `RequestValidationError`, com o seu próprio handler."""
    raw = json.dumps({"document": _doc(), "\ud800": 1}).encode("utf-8", "surrogatepass")
    r = _post_raw(client, "/v1/models/validate", raw)

    assert r.status_code == 422
    assert r.json()["code"] == "REQUEST_VALIDATION_ERROR"


@pytest.mark.parametrize("hostile", ["\x00", "‮", "﻿", "￿", "🙂", "é"])
def test_the_other_hostile_strings_are_unaffected(client: TestClient, hostile: str) -> None:
    """Controlo: só surrogates soltos mudam de forma; o resto continua a ser aceite."""
    doc = _doc()
    doc["metadata"]["title"] = f"t{hostile}"

    assert client.post("/v1/models/validate", json={"document": doc}).status_code == 200


def test_a_normal_title_is_not_escaped_by_the_new_encoder(client: TestClient) -> None:
    """`backslashreplace` não pode transformar acentuação normal em escapes."""
    doc = _doc()
    doc["metadata"]["title"] = "Modelo de produção – ção"

    r = client.post("/v1/models/validate", json={"document": doc})

    assert r.json()["title"] == "Modelo de produção – ção"


# --- X-Request-ID na 500 --------------------------------------------------------------


def test_an_unhandled_error_still_carries_the_correlation_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 500 sai por fora do middleware de observabilidade e era a única resposta sem o id."""
    import otm_api.routers.models as models_router

    def _boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(models_router, "assess_model_precheck", _boom)
    client = TestClient(app, raise_server_exceptions=False)

    r = client.post("/v1/models/precheck", json={"document": _doc()})

    assert r.status_code == 500
    assert r.headers["x-request-id"] == r.json()["request_id"]


# --- 400 de corpo ilegível ------------------------------------------------------------


@pytest.mark.parametrize("route", _POST_ROUTES)
def test_an_unparsable_body_never_returns_a_bare_string_detail(client: TestClient, route: str) -> None:
    """O sintoma: `resp.json()["detail"]["code"]` -> TypeError num cliente conforme."""
    assert not isinstance(_post_raw(client, route, _deeply_nested_body()).json().get("detail"), str)


@pytest.mark.parametrize("route", _POST_ROUTES)
def test_an_unparsable_body_carries_a_stable_documented_code(client: TestClient, route: str) -> None:
    assert _post_raw(client, route, _deeply_nested_body()).json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_an_unparsable_body_answers_exactly_like_malformed_json(client: TestClient) -> None:
    """As duas falhas são a mesma coisa — "o corpo não se lê" — e diferiam em estado e forma."""
    nested = _post_raw(client, "/v1/models/validate", _deeply_nested_body())
    malformed = _post_raw(client, "/v1/models/validate", b"{not json")

    assert (nested.status_code, nested.json()["code"]) == (malformed.status_code, malformed.json()["code"])


def test_the_unparsable_body_error_is_localised(client: TestClient) -> None:
    r = client.post(
        "/v1/models/validate",
        content=_deeply_nested_body(),
        headers={"content-type": "application/json", "Accept-Language": "pt-BR"},
    )

    assert r.json()["message"] == "Corpo do pedido ou parâmetros inválidos."


def test_the_unparsable_body_error_says_where_the_problem_is(client: TestClient) -> None:
    errors = _post_raw(client, "/v1/models/validate", _deeply_nested_body()).json()["errors"]

    assert errors[0]["loc"] == ["body"]


# --- controlos: o resto do envelope não mudou -----------------------------------------


def test_a_business_error_still_uses_the_detail_envelope(client: TestClient) -> None:
    r = client.post("/v1/remediation/backlog", json={"document": _doc(), "run_analysis": False})

    assert r.json()["detail"]["code"] == "REMEDIATION_INPUT"


def test_a_route_outside_the_documented_table_is_left_alone(client: TestClient) -> None:
    """404/405 do router do Starlette não são contrato desta API e não foram reinventados."""
    assert client.get("/v1/nope").json() == {"detail": "Not Found"}


@pytest.mark.parametrize("status_code", [204, 304])
def test_a_status_that_forbids_a_body_still_gets_none(status_code: int) -> None:
    """
    O handler substitui o do FastAPI e tem de manter o resto do contrato dele.

    Um corpo JSON num 204/304 viola o HTTP (RFC 9110) e alguns clientes tratam-no como
    resposta corrompida. Nenhuma rota levanta hoje um destes estados, por isso o handler é
    exercitado diretamente — a alternativa seria descobri-lo quando alguém adicionar a rota.
    """
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})

    response = asyncio.run(http_exception_handler(request, StarletteHTTPException(status_code=status_code)))

    assert response.body == b""


def test_the_happy_path_still_answers_normally(client: TestClient) -> None:
    assert client.post("/v1/models/validate", json={"document": _doc()}).status_code == 200
