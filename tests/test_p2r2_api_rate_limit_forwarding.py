"""
Regressão: `OTM_RATE_LIMIT` era contornável com um `X-Forwarded-For` rotativo.

O `client_key` prometia no docstring que **não** lia `X-Forwarded-For`, e essa promessa era
falsa por um andar acima: o uvicorn 0.52 corre `ProxyHeadersMiddleware` por defeito
(`proxy_headers=True`, `forwarded_allow_ips='127.0.0.1'`) e reescreve `scope["client"]` a
partir desse cabeçalho sempre que o peer é loopback — ou seja, em **todos** os pedidos que
chegam pelo reverse proxy no mesmo host que `DEPLOYMENT_INVARIANTS.md` torna obrigatório para
exposição. Medido antes da correção: 8 GET simples -> [200x5, 429x3]; 20 GET com o cabeçalho a
rodar -> 20x200, com o balde do 127.0.0.1 ainda esgotado.

Estes testes montam a app exatamente como o uvicorn a monta (a classe real, com os defaults
reais), em vez de assumirem o que ela faz.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.middleware_rate_limit import parse_rate_limit  # noqa: E402
from uvicorn.config import Config  # noqa: E402
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # noqa: E402

_ENVS = ["OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED", "OTM_API_KEY", "OTM_TRUSTED_PROXY"]

_LOOPBACK = ("127.0.0.1", 51000)


@pytest.fixture(autouse=True)
def _restore_app_module() -> Iterator[None]:
    """Outros módulos importam `otm_api.main`: devolver-lhes a app default."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


def _reloaded_app(monkeypatch: pytest.MonkeyPatch, *, limit: str, trusted_proxy: bool = False) -> object:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_RATE_LIMIT", limit)
    if trusted_proxy:
        monkeypatch.setenv("OTM_TRUSTED_PROXY", "1")

    import otm_api.main as main

    importlib.reload(main)
    return main.app


def _behind_uvicorn_proxy_headers(app: object) -> ProxyHeadersMiddleware:
    """A app tal como o uvicorn a serve: a middleware dele por fora da nossa."""
    return ProxyHeadersMiddleware(app, trusted_hosts=Config("otm_api.main:app").forwarded_allow_ips)


def _client(app: object, *, peer: tuple[str, int] = _LOOPBACK) -> TestClient:
    return TestClient(_behind_uvicorn_proxy_headers(app), client=peer)


def _codes(client: TestClient, *, count: int, header: str | None = None, rotate: bool = False) -> list[int]:
    out = []
    for i in range(count):
        headers = {}
        if header is not None:
            headers["X-Forwarded-For"] = header.format(i=i + 1) if rotate else header
        out.append(client.get("/health", headers=headers).status_code)
    return out


# --- o defeito, com a mecânica real do uvicorn ----------------------------------------


def test_uvicorn_rewrites_the_client_address_from_a_client_supplied_header() -> None:
    """A premissa do defeito, verificada na configuração resolvida e não assumida."""
    config = Config("otm_api.main:app")

    assert (config.proxy_headers, config.forwarded_allow_ips) == (True, "127.0.0.1")


def test_a_rotating_forwarded_header_cannot_mint_fresh_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
    """O sintoma: 20 pedidos, 20x200, com o limite de 5/minute configurado."""
    client = _client(_reloaded_app(monkeypatch, limit="5/minute"))

    codes = _codes(client, count=20, header="203.0.113.{i}", rotate=True)

    assert 429 in codes, f"o limite continua a ser contornável por cabeçalho: {codes}"


def test_the_rotating_bypass_is_bounded_by_the_configured_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_reloaded_app(monkeypatch, limit="5/minute"))

    codes = _codes(client, count=20, header="203.0.113.{i}", rotate=True)

    assert codes.count(200) == 5


def test_a_realistic_proxy_chain_cannot_mint_fresh_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
    """O que o `$proxy_add_x_forwarded_for` do nginx produz, com o cliente a rodar a cabeça."""
    client = _client(_reloaded_app(monkeypatch, limit="5/minute"))

    codes = _codes(client, count=15, header="198.51.100.{i}, 127.0.0.1", rotate=True)

    assert codes.count(200) == 5, f"a cadeia de proxy ainda dá baldes novos: {codes}"


def test_the_header_cannot_escape_a_bucket_already_spent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gastar o balde sem cabeçalho e depois passar a enviá-lo não pode reabrir o crédito."""
    client = _client(_reloaded_app(monkeypatch, limit="3/minute"))
    _codes(client, count=4)

    escaped = _codes(client, count=5, header="203.0.113.{i}", rotate=True)

    assert escaped.count(200) <= 3


def test_the_expensive_engine_route_is_covered_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """O limite existe pelo custo de `/v1/models/analyze`, não pelo custo de `/health`."""
    client = _client(_reloaded_app(monkeypatch, limit="4/minute"))

    codes = [
        client.post(
            "/v1/models/analyze",
            json={"document": {}},
            headers={"X-Forwarded-For": f"192.0.2.{i + 1}, 127.0.0.1"},
        ).status_code
        for i in range(12)
    ]

    assert 429 in codes, f"a rota do motor continua contornável: {codes}"


def test_the_header_sent_twice_is_not_a_way_around_the_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """O uvicorn junta os valores repetidos; ler só o primeiro seria um buraco do tamanho do bug."""
    client = _client(_reloaded_app(monkeypatch, limit="3/minute"))

    codes = [
        client.get(
            "/health",
            headers=[("x-forwarded-for", "203.0.113.9"), ("x-forwarded-for", f"198.51.100.{i + 1}")],
        ).status_code
        for i in range(10)
    ]

    assert 429 in codes, f"dois cabeçalhos iguais contornam o limite: {codes}"


def test_an_ipv6_forwarded_entry_with_a_port_is_not_a_way_around_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O uvicorn desmonta `[addr]:porta`; a comparação tem de aguentar essa forma."""
    client = _client(_reloaded_app(monkeypatch, limit="3/minute"))

    codes = _codes(client, count=10, header="[2001:db8::{i}]:443", rotate=True)

    assert 429 in codes, f"a forma IPv6 com porta contorna o limite: {codes}"


# --- o que continua a funcionar --------------------------------------------------------


def test_a_direct_caller_without_the_header_keeps_its_own_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    """A degradação não pode custar o limite por IP a quem não usa proxy nenhum."""
    app = _reloaded_app(monkeypatch, limit="3/minute")
    first = _client(app, peer=("198.51.100.7", 40000))
    second = _client(app, peer=("198.51.100.8", 40000))

    _codes(first, count=4)

    assert _codes(second, count=3) == [200, 200, 200]


def test_requests_below_the_limit_are_still_served(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_reloaded_app(monkeypatch, limit="50/minute"))

    assert _codes(client, count=5, header="203.0.113.{i}", rotate=True) == [200] * 5


def test_an_operator_declared_proxy_gets_per_caller_buckets_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """`OTM_TRUSTED_PROXY` é o modo em que o endereço encaminhado vale como identidade."""
    client = _client(_reloaded_app(monkeypatch, limit="3/minute", trusted_proxy=True))

    codes = _codes(client, count=8, header="203.0.113.{i}, 127.0.0.1", rotate=True)

    assert codes == [200] * 8


def test_a_trusted_proxy_still_limits_a_single_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(_reloaded_app(monkeypatch, limit="3/minute", trusted_proxy=True))

    codes = _codes(client, count=6, header="203.0.113.42, 127.0.0.1")

    assert codes.count(429) == 3


# --- observabilidade -------------------------------------------------------------------


def test_the_startup_line_declares_a_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_TRUSTED_PROXY", "1")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "trusted_proxy=on" in caplog.text


def test_the_degradation_to_a_shared_bucket_is_visible_in_the_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Partilhar um balde é a resposta segura, mas é indistinguível de "limite apertado demais"."""
    client = _client(_reloaded_app(monkeypatch, limit="5/minute"))

    with caplog.at_level(logging.WARNING, logger="otm.api"):
        _codes(client, count=2, header="203.0.113.{i}", rotate=True)

    assert "rate_limit_forwarded_client_untrusted" in caplog.text


def test_the_degradation_warning_is_not_repeated_per_request(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Uma linha por pedido seria uma inundação de log controlada pelo atacante."""
    client = _client(_reloaded_app(monkeypatch, limit="20/minute"))

    with caplog.at_level(logging.WARNING, logger="otm.api"):
        _codes(client, count=6, header="203.0.113.{i}", rotate=True)

    emitted = [r for r in caplog.records if r.message == "rate_limit_forwarded_client_untrusted"]
    assert len(emitted) == 1


# --- `0/minute` ------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ["0/minute", "0/second", "0/hour"])
def test_a_limit_of_zero_is_refused_instead_of_rejecting_everything(spec: str) -> None:
    """`0` é o valor que muita gente lê como "sem limite", e o que `${LIMIT}/minute` dá vazio."""
    with pytest.raises(ValueError, match="allows no requests"):
        parse_rate_limit(spec)


def test_the_zero_limit_error_names_the_documented_way_to_disable_the_control() -> None:
    with pytest.raises(ValueError, match="OTM_RATE_LIMIT_DISABLED=1"):
        parse_rate_limit("0/minute")


def test_a_zero_limit_aborts_startup_instead_of_serving_429_to_its_own_health_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_RATE_LIMIT", "0/minute")
    import otm_api.main as main

    with pytest.raises(ValueError, match="allows no requests"):
        importlib.reload(main)


def test_a_positive_limit_still_parses() -> None:
    assert parse_rate_limit("120/minute").amount == 120
