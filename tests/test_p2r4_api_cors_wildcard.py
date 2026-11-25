"""
`OTM_CORS_ORIGINS=*` era uma escalada silenciosa, não a configuração que o operador escreveu.

Com `allow_credentials=True` fixo no `main.py`, o `CORSMiddleware` do Starlette **não** emite
um `*` literal quando as origens são `["*"]`: reflecte a `Origin` de quem chama e junta-lhe
`Access-Control-Allow-Credentials: true`. Um `*` literal faz o browser recusar leituras
cross-origin com credenciais; a reflexão autoriza-as. Escrever `*` passava assim a permitir
estritamente **mais** do que `*` significa, e o arranque anunciava-o como um neutro
`cors_origins=1`, indistinguível de uma origem real.

`docs/architecture/DEPLOYMENT_INVARIANTS.md` já exige listas CORS explícitas fora de
`development`, e todo o resto da configuração perigosa recusa arrancar (`OTM_ENV=prd`,
`OTM_TRUSTED_PROXY=maybe`, `OTM_RATE_LIMIT=0/minute`). As origens eram a excepção.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.cors_settings import InvalidCorsOriginsError, resolve_cors_profile  # noqa: E402
from otm_api.perimeter_settings import describe_effective_perimeter, resolve_api_key_perimeter  # noqa: E402

_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_TRUSTED_PROXY", "OTM_RATE_LIMIT_DISABLED"]
_UNRELATED_ORIGIN = "https://evil.example.com"


@pytest.fixture
def restore_main() -> Iterator[None]:
    """Recarrega `otm_api.main` no fim: o perímetro é resolvido no import do módulo."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


def _app_with(environment: str, origins: str) -> Any:
    os.environ["OTM_ENV"] = environment
    os.environ["OTM_CORS_ORIGINS"] = origins
    os.environ["OTM_TRUSTED_PROXY"] = "0"
    os.environ["OTM_RATE_LIMIT_DISABLED"] = "1"
    import otm_api.main as main

    importlib.reload(main)
    return main.app


def _preflight(app: Any) -> Any:
    return TestClient(app).options(
        "/v1/models/analyze",
        headers={
            "Origin": _UNRELATED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


# --- fora de development: recusa de arranque ------------------------------------------


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_a_wildcard_origin_list_refuses_to_start(environment: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", environment)
    monkeypatch.setenv("OTM_CORS_ORIGINS", "*")

    with pytest.raises(InvalidCorsOriginsError):
        resolve_cors_profile()


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_the_refusal_says_what_to_write_instead(environment: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Quem lê isto está a meio de um deploy: a linha tem de ser um runbook, não um diagnóstico."""
    monkeypatch.setenv("OTM_ENV", environment)
    monkeypatch.setenv("OTM_CORS_ORIGINS", "*")

    with pytest.raises(InvalidCorsOriginsError) as excinfo:
        resolve_cors_profile()

    assert "OTM_CORS_ORIGINS=https://app.example.com" in str(excinfo.value)


def test_a_wildcard_hidden_among_real_origins_is_refused_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """`*` numa lista não é "uma origem a mais": anula todas as outras."""
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "https://app.example.com,*")

    with pytest.raises(InvalidCorsOriginsError):
        resolve_cors_profile()


def test_an_explicit_origin_list_still_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Controlo: a configuração correta não foi apertada por engano."""
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "https://app.example.com")

    assert resolve_cors_profile().origins == ["https://app.example.com"]


def test_an_explicit_origin_list_keeps_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "https://app.example.com")

    assert resolve_cors_profile().allow_credentials is True


# --- development: `*` honrado como `*`, sem credenciais -------------------------------


def test_development_serves_a_literal_wildcard(restore_main: None) -> None:
    """O sintoma: a resposta trazia `https://evil.example.com`, não `*`."""
    r = _preflight(_app_with("development", "*"))

    assert r.headers["access-control-allow-origin"] == "*"


def test_development_does_not_pair_the_wildcard_with_credentials(restore_main: None) -> None:
    """É esta combinação que a same-origin policy existe para impedir."""
    r = _preflight(_app_with("development", "*"))

    assert "access-control-allow-credentials" not in r.headers


def test_a_real_request_from_an_unrelated_origin_is_not_credentialed(restore_main: None) -> None:
    """Não basta o preflight: o pedido real trazia os dois cabeçalhos."""
    client = TestClient(_app_with("development", "*"))

    r = client.get("/v1/templates", headers={"Origin": _UNRELATED_ORIGIN})

    assert r.headers.get("access-control-allow-credentials") is None


def test_the_declared_origins_still_work_in_development(restore_main: None) -> None:
    """Controlo: com uma lista concreta, o dev server do frontend continua a ser autorizado."""
    client = TestClient(_app_with("development", "http://localhost:5173"))

    r = client.get("/v1/templates", headers={"Origin": "http://localhost:5173"})

    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"


# --- o arranque deixa de o esconder ---------------------------------------------------


def test_the_startup_line_marks_the_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    """`cors_origins=1` descrevia `*` exatamente como descreve uma origem real."""
    monkeypatch.setenv("OTM_ENV", "development")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "*")

    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=None,
    )

    assert "cors_origins_wildcard=on cors_credentials=off" in line


def test_the_startup_line_is_unchanged_for_a_real_origin_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "development")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "http://localhost:5173")

    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=None,
    )

    assert line == "api_perimeter environment=development api_key=off rate_limit=off cors_origins=1"
