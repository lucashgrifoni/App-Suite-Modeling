"""
Regressão: uma configuração de perímetro inválida não pode desligar controlos em silêncio.

Dois modos de falha reais, ambos por erro de operador e ambos sem qualquer sinal:

- `OTM_API_KEY="   "` (segredo de CI que resolveu para vazio, linha `.env` com espaço,
  secret k8s com uma newline): o `strip()` transformava "definido mas inutilizável" em
  "não definido" e `/v1/*` passava a servir tudo sem credencial.
- `OTM_ENV=prd` / `stage`: qualquer valor não reconhecido caía em `development`, o que
  abre o CORS a `localhost:5173` com `*` em métodos/cabeçalhos e desliga o rate limit.

O arranque também não dizia nada sobre o perímetro efetivo, por isso a única diferença
visível entre um servidor bem configurado e um aberto era o 401 que ninguém via.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.cors_settings import InvalidEnvironmentError, resolve_cors_profile  # noqa: E402
from otm_api.perimeter_settings import (  # noqa: E402
    describe_effective_perimeter,
    resolve_api_key_perimeter,
    resolve_optional_api_secret,
    resolve_rate_limit_default,
)

_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def restore_main_module() -> Iterator[None]:
    """Testes que recarregam `otm_api.main` têm de devolver a app default aos outros módulos."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


# --- OTM_API_KEY definido mas em branco -----------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_blank_api_key_keeps_the_perimeter_enforced(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", blank)
    assert resolve_api_key_perimeter().enforced is True


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_blank_api_key_is_flagged_as_misconfigured(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", blank)
    assert resolve_api_key_perimeter().misconfigured is True


def test_unset_api_key_leaves_the_perimeter_off() -> None:
    assert resolve_api_key_perimeter().enforced is False


def test_usable_api_key_is_stripped_and_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", "  s3cr3t  ")
    assert resolve_api_key_perimeter().secret == "s3cr3t"


def test_legacy_secret_helper_still_reports_none_when_unset() -> None:
    assert resolve_optional_api_secret() is None


def test_v1_is_closed_when_the_api_key_is_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    """O sintoma original: 200 sem credencial nenhuma."""
    from otm_api.main import app

    monkeypatch.setenv("OTM_API_KEY", "   ")
    assert TestClient(app).get("/v1/templates").status_code == 401


def test_blank_api_key_rejection_names_the_misconfiguration(monkeypatch: pytest.MonkeyPatch) -> None:
    from otm_api.main import app

    monkeypatch.setenv("OTM_API_KEY", "   ")
    body = TestClient(app).get("/v1/templates").json()
    assert body["code"] == "API_KEY_MISCONFIGURED"


def test_a_blank_api_key_cannot_be_satisfied_by_sending_a_blank_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem isto, "fail closed" seria só "fail closed contra quem não tenta"."""
    from otm_api.main import app

    monkeypatch.setenv("OTM_API_KEY", "   ")
    r = TestClient(app).get("/v1/templates", headers={"X-OTM-API-Key": "   "})
    assert r.status_code == 401


def test_health_stays_open_when_the_api_key_is_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    from otm_api.main import app

    monkeypatch.setenv("OTM_API_KEY", "   ")
    assert TestClient(app).get("/health").status_code == 200


# --- OTM_ENV desconhecido -------------------------------------------------------------


@pytest.mark.parametrize("value", ["prd", "stage", "prod-eu", "PRODUCTON", "developement"])
def test_unrecognised_environment_is_rejected(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", value)
    with pytest.raises(InvalidEnvironmentError, match="OTM_ENV"):
        resolve_cors_profile()


def test_rejection_lists_the_accepted_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "prd")
    with pytest.raises(InvalidEnvironmentError, match="production"):
        resolve_cors_profile()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("development", "development"),
        ("staging", "staging"),
        ("prod", "production"),
        ("production", "production"),
        ("  Production  ", "production"),
        ("", "development"),
    ],
)
def test_documented_values_still_resolve(value: str, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", value)
    assert resolve_cors_profile().environment == expected


def test_unset_environment_is_development() -> None:
    assert resolve_cors_profile().environment == "development"


def test_rate_limit_default_propagates_the_environment_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    """`resolve_rate_limit_default` consome o perfil: não pode devolver "sem limite"."""
    monkeypatch.setenv("OTM_ENV", "stage")
    with pytest.raises(InvalidEnvironmentError, match="stage"):
        resolve_rate_limit_default()


def test_app_refuses_to_start_with_an_unrecognised_environment(
    monkeypatch: pytest.MonkeyPatch,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_ENV", "prd")
    import otm_api.main as main

    with pytest.raises(InvalidEnvironmentError, match="prd"):
        importlib.reload(main)


# --- perímetro efetivo no log de arranque ---------------------------------------------


def test_startup_states_the_effective_perimeter(
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "api_perimeter" in caplog.text


def test_startup_warns_when_the_api_key_is_blank(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_API_KEY", "   ")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "api_key=misconfigured" in caplog.text


def test_startup_perimeter_line_is_a_warning_when_misconfigured(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_API_KEY", "   ")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert [r.levelname for r in caplog.records if "api_perimeter" in r.message] == ["WARNING"]


# --- 429 igualmente observável --------------------------------------------------------


def _client_with_a_spent_budget(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OTM_RATE_LIMIT", "1/minute")
    import otm_api.main as main

    importlib.reload(main)
    client = TestClient(main.app)
    client.get("/health")
    return client


def test_rate_limited_response_carries_a_request_id(
    monkeypatch: pytest.MonkeyPatch,
    restore_main_module: None,
) -> None:
    """O 429 vinha do middleware de limite, que corria por dentro da observabilidade."""
    client = _client_with_a_spent_budget(monkeypatch)
    blocked = client.get("/health")
    assert blocked.headers.get("x-request-id")


def test_rate_limited_response_is_written_to_the_structured_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    client = _client_with_a_spent_budget(monkeypatch)
    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.get("/health")

    assert [r for r in caplog.records if getattr(r, "status_code", None) == 429]


# --- descrição do perímetro -----------------------------------------------------------


def test_perimeter_description_names_key_environment_and_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")
    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=resolve_rate_limit_default(),
    )
    assert line == "api_perimeter environment=production api_key=enforced rate_limit=120/minute cors_origins=0"


def test_perimeter_description_for_an_open_development_server() -> None:
    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=resolve_rate_limit_default(),
    )
    assert line == "api_perimeter environment=development api_key=off rate_limit=off cors_origins=2"
