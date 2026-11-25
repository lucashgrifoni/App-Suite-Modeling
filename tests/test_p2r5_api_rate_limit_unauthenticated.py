"""
Regressão: o único controlo volumétrico não contava os pedidos **não autenticados** a `/v1/*`.

O Starlette empilha a middleware ao contrário da ordem de registo, por isso o
`OptionalApiKeyMiddleware` ficava **por fora** do `RateLimitMiddleware`, e o seu 401 é
devolvido sem chamar `call_next`: o limitador nunca corria. Medido com `OTM_RATE_LIMIT=10/minute`
e `OTM_API_KEY` definida: 300 POST sem chave a `/v1/models/validate` em 0,26 s (1167 req/s),
todos 401, a gastar **zero** orçamento, enquanto 30 pedidos autenticados do mesmo chamador
levavam 22x 429. Ou seja: o atacante anónimo tinha um canal não medido (força bruta da chave,
inundação do log de erros, pressão de CPU e de sockets) e só o cliente que paga era travado.

`docs/features/API.md` promete o contrário — o limite "aplica-se como limite global a **todas**
as rotas, incluindo `/health` e `/v1/*`, contado por chamador".

A ordem tem três restrições ao mesmo tempo, e estes testes fixam-nas todas:

1. `RateLimitMiddleware` por **fora** do `OptionalApiKeyMiddleware` — senão o 401 não é contado;
2. `ObservabilityMiddleware` por **fora** de ambos — senão o 401 e o 429 não aparecem no log
   estruturado nem trazem `X-Request-ID` (regressão já corrigida numa ronda anterior, coberta
   por `test_p2_api_auth_diagnostics.py`);
3. o orçamento continua a ser **por chamador** — a inundação anónima de um IP não pode esgotar
   o balde de outro chamador.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

_ENVS = ["OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED", "OTM_API_KEY", "OTM_TRUSTED_PROXY", "OTM_ENV"]
_KEY = "p2r5-perimeter-secret"


@pytest.fixture(autouse=True)
def _restore_app_module() -> Iterator[None]:
    """Outros módulos importam `otm_api.main`: devolver-lhes a app default."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


def _keyed_app(monkeypatch: pytest.MonkeyPatch, *, limit: str) -> Any:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_RATE_LIMIT", limit)
    monkeypatch.setenv("OTM_API_KEY", _KEY)

    import otm_api.main as main

    importlib.reload(main)
    return main.app


def _client(app: Any, *, peer: tuple[str, int] = ("203.0.113.7", 40000)) -> TestClient:
    return TestClient(app, client=peer, raise_server_exceptions=False)


def _anonymous_codes(client: TestClient, *, count: int) -> list[int]:
    return [client.post("/v1/models/validate", json={"document": {}}).status_code for _ in range(count)]


def _authenticated(client: TestClient) -> Any:
    return client.post("/v1/models/validate", json={"document": {}}, headers={"X-OTM-API-Key": _KEY})


# --- o defeito ------------------------------------------------------------------------


def test_an_unauthenticated_flood_starts_getting_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """O sintoma: 300 pedidos sem chave a 1167 req/s, todos 401, orçamento intacto."""
    client = _client(_keyed_app(monkeypatch, limit="5/minute"))

    codes = _anonymous_codes(client, count=20)

    assert 429 in codes, f"o canal anónimo continua sem medição: {sorted(set(codes))}"


def test_the_unauthenticated_flood_is_bounded_by_the_configured_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_keyed_app(monkeypatch, limit="5/minute"))

    codes = _anonymous_codes(client, count=20)

    assert codes.count(401) == 5, f"o 401 não gasta exatamente um pedido do orçamento: {codes}"


def test_an_unauthenticated_flood_consumes_the_budget_of_that_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    """O contra-facto medido: a seguir à inundação, o contador estava intocado."""
    client = _client(_keyed_app(monkeypatch, limit="10/minute"))

    _anonymous_codes(client, count=6)

    assert int(_authenticated(client).headers["X-RateLimit-Remaining"]) <= 3


def test_a_wrong_key_is_metered_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adivinhar a chave é o uso óbvio do canal: cada tentativa tem de custar orçamento."""
    client = _client(_keyed_app(monkeypatch, limit="5/minute"))

    codes = [
        client.post(
            "/v1/models/validate",
            json={"document": {}},
            headers={"X-OTM-API-Key": f"guess-{i}"},
        ).status_code
        for i in range(20)
    ]

    assert 429 in codes, f"a força bruta da chave continua não medida: {sorted(set(codes))}"


def test_the_429_wins_over_the_401_once_the_budget_is_spent(monkeypatch: pytest.MonkeyPatch) -> None:
    """O limitador está por fora: gasto o orçamento, nem se chega a avaliar a chave."""
    client = _client(_keyed_app(monkeypatch, limit="3/minute"))

    _anonymous_codes(client, count=3)

    assert client.post("/v1/models/validate", json={"document": {}}).status_code == 429


# --- o que não pode partir: a rejeição continua observável ----------------------------


def test_the_401_still_carries_a_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ObservabilityMiddleware` tem de continuar por fora do perímetro inteiro."""
    client = _client(_keyed_app(monkeypatch, limit="50/minute"))

    assert client.post("/v1/models/validate", json={"document": {}}).headers.get("x-request-id")


def test_the_401_still_reaches_the_structured_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _client(_keyed_app(monkeypatch, limit="50/minute"))

    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.post("/v1/models/validate", json={"document": {}})

    assert [r for r in caplog.records if getattr(r, "status_code", None) == 401]


def test_the_429_still_reaches_the_structured_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _client(_keyed_app(monkeypatch, limit="1/minute"))

    with caplog.at_level(logging.INFO, logger="otm.api"):
        _anonymous_codes(client, count=2)

    assert [r for r in caplog.records if getattr(r, "status_code", None) == 429]


def test_the_401_still_carries_the_www_authenticate_challenge(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_keyed_app(monkeypatch, limit="50/minute"))

    r = client.post("/v1/models/validate", json={"document": {}})

    assert r.headers.get("www-authenticate") == "Bearer"


def test_the_401_body_is_still_the_documented_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_keyed_app(monkeypatch, limit="50/minute"))

    assert client.post("/v1/models/validate", json={"document": {}}).json()["code"] == "API_KEY_REQUIRED"


# --- o que não pode partir: o cliente legítimo não é vítima da inundação --------------


def test_an_anonymous_flood_does_not_starve_a_different_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    """A prova que o reporter pediu: o atacante paga o seu balde, não o de quem paga."""
    app = _keyed_app(monkeypatch, limit="5/minute")
    attacker = _client(app, peer=("198.51.100.66", 40000))
    legitimate = _client(app, peer=("198.51.100.77", 40000))

    _anonymous_codes(attacker, count=30)

    assert _authenticated(legitimate).status_code != 429


def test_the_legitimate_caller_keeps_its_whole_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _keyed_app(monkeypatch, limit="5/minute")
    attacker = _client(app, peer=("198.51.100.66", 40000))
    legitimate = _client(app, peer=("198.51.100.77", 40000))

    _anonymous_codes(attacker, count=30)

    assert [_authenticated(legitimate).status_code for _ in range(5)].count(429) == 0


def test_authenticated_traffic_below_the_limit_is_still_served(monkeypatch: pytest.MonkeyPatch) -> None:
    """Controlo: apertar o perímetro não pode passar a recusar quem está dentro do orçamento."""
    client = _client(_keyed_app(monkeypatch, limit="20/minute"))

    assert [_authenticated(client).status_code for _ in range(6)].count(429) == 0


def test_preflight_is_not_charged_to_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    """`OPTIONS` nunca exigiu chave; contá-lo agora gastaria o orçamento antes do pedido real."""
    client = _client(_keyed_app(monkeypatch, limit="5/minute"))

    for _ in range(10):
        client.options(
            "/v1/models/validate",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert _authenticated(client).status_code != 429


def test_routes_outside_v1_are_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/health` nunca exigiu chave e já era contado; a troca de ordem não pode mudá-lo."""
    client = _client(_keyed_app(monkeypatch, limit="4/minute"))

    codes = [client.get("/health").status_code for _ in range(6)]

    assert codes[:4] == [200] * 4 and codes[-1] == 429
