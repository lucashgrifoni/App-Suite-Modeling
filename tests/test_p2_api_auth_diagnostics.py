"""
Regressão: uma rejeição de autenticação tem de ser observável, e o id de correlação
não pode ser o que o cliente quiser.

- O 401 do middleware de chave de API era devolvido *antes* do `ObservabilityMiddleware`,
  por isso não existia no log estruturado, não trazia `X-Request-ID` e não ecoava o
  `X-Request-ID` do cliente. Todos os outros códigos (200/400/404/413/422/500) apareciam.
- O 401 também não trazia `WWW-Authenticate`, exigido pela RFC 9110 11.6.1.
- O `X-Request-ID` recebido era adotado tal e qual: 4000 carateres, chavetas, newlines.
"""

from __future__ import annotations

import logging
import uuid

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402
from otm_api.observability import resolve_request_id  # noqa: E402

_KEY = "not-a-real-key"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def keyed(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OTM_API_KEY", _KEY)
    return TestClient(app, raise_server_exceptions=False)


# --- 401 observável -------------------------------------------------------------------


def test_rejected_request_carries_a_request_id_header(keyed: TestClient) -> None:
    assert keyed.get("/v1/templates").headers.get("x-request-id")


def test_rejected_request_echoes_the_client_correlation_id(keyed: TestClient) -> None:
    r = keyed.get("/v1/templates", headers={"X-Request-ID": "AUDIT-TRACE-401"})
    assert r.headers.get("x-request-id") == "AUDIT-TRACE-401"


def test_rejected_request_is_written_to_the_structured_log(
    keyed: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="otm.api"):
        keyed.get("/v1/templates")

    assert [r for r in caplog.records if getattr(r, "status_code", None) == 401]


def test_the_logged_rejection_names_the_path(keyed: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="otm.api"):
        keyed.get("/v1/templates")

    logged = [r for r in caplog.records if getattr(r, "status_code", None) == 401]
    assert logged[0].path == "/v1/templates"


def test_authorized_requests_are_still_logged(keyed: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="otm.api"):
        keyed.get("/v1/templates", headers={"X-OTM-API-Key": _KEY})

    assert [r for r in caplog.records if getattr(r, "status_code", None) == 200]


# --- desafio WWW-Authenticate ---------------------------------------------------------


def test_401_carries_the_required_challenge(keyed: TestClient) -> None:
    assert keyed.get("/v1/templates").headers.get("www-authenticate") == "Bearer"


def test_401_from_a_wrong_key_also_carries_the_challenge(keyed: TestClient) -> None:
    r = keyed.get("/v1/templates", headers={"X-OTM-API-Key": "wrong"})
    assert r.headers.get("www-authenticate") == "Bearer"


def test_successful_response_does_not_carry_a_challenge(keyed: TestClient) -> None:
    r = keyed.get("/v1/templates", headers={"X-OTM-API-Key": _KEY})
    assert "www-authenticate" not in r.headers


# --- X-Request-ID validado ------------------------------------------------------------


def test_an_oversized_client_id_is_not_adopted(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-ID": "A" * 4000})
    assert len(r.headers["x-request-id"]) < 200


@pytest.mark.parametrize(
    "hostile",
    ['{"x":"y"}', "id with spaces", "id\twith\ttabs", "café", "<script>", "a" * 129],
)
def test_hostile_client_ids_are_replaced_by_a_server_generated_one(hostile: str) -> None:
    assert resolve_request_id(hostile) != hostile


@pytest.mark.parametrize(
    "acceptable",
    ["trace-cli-e2e", "0af7651916cd43dd8448eb211c80319c", str(uuid.uuid4()), "svc_a:req/17=", "A" * 128],
)
def test_reasonable_client_ids_are_still_adopted(acceptable: str) -> None:
    assert resolve_request_id(acceptable) == acceptable


def test_a_surrounding_whitespace_id_is_still_trimmed_and_adopted() -> None:
    assert resolve_request_id("  trace-1  ") == "trace-1"


def test_a_missing_header_yields_a_uuid() -> None:
    assert uuid.UUID(resolve_request_id(None))


def test_a_rejected_id_yields_a_uuid() -> None:
    assert uuid.UUID(resolve_request_id("nope nope"))


def test_generated_ids_are_unique_per_request(client: TestClient) -> None:
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]
    assert first != second
