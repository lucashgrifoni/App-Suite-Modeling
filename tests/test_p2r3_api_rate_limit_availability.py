"""
Regressão de disponibilidade: o balde partilhado era o **default**, e não uma escolha.

A correção anterior (não confiar num endereço vindo de `X-Forwarded-For`) está certa como
segurança e mantém-se intacta aqui. O que ninguém decidiu foi o preço: atrás do reverse proxy
que `DEPLOYMENT_INVARIANTS.md` torna **obrigatório**, o uvicorn reescreve o endereço de *todos*
os pedidos a partir do cabeçalho, por isso *todos* caíam no balde partilhado. Os `120/minute`
de produção deixavam de ser "120 por chamador" e passavam a ser "120 para o serviço inteiro".

Medido antes desta correção, com `OTM_ENV=staging` e a app servida como o uvicorn a serve:
a Alice faz 120 pedidos (200x120) e o **primeiro** pedido do Bob leva 429. Ou seja: o upgrade
transformava um limite contornável numa negação de serviço auto-infligida para quem não lesse
as notas de versão.

Decisão: o balde partilhado continua a ser a única chave segura para um chamador que a app não
consegue identificar — mas deixa de ser alcançável por omissão. Em `staging`/`production`, com
o limite ativo, `OTM_TRUSTED_PROXY` passa a ser uma **declaração obrigatória**, e o arranque
falha com a consequência de cada opção escrita por extenso. Um deploy partido no arranque é
observável; um serviço que serve 429 a toda a gente ao fim de duas semanas não é.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator
from types import ModuleType

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.perimeter_settings import (  # noqa: E402
    TrustedProxyConfigError,
    describe_shared_bucket_consequence,
    resolve_trusted_proxy,
)
from uvicorn.config import Config  # noqa: E402
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware  # noqa: E402

_ENVS = [
    "OTM_ENV",
    "OTM_CORS_ORIGINS",
    "OTM_API_KEY",
    "OTM_RATE_LIMIT",
    "OTM_RATE_LIMIT_DISABLED",
    "OTM_TRUSTED_PROXY",
]

_LOOPBACK = ("127.0.0.1", 51000)


def _main() -> ModuleType:
    """`otm_api.main`, importado (a primeira vez) com o ambiente já limpo.

    Distinção que interessa a este ficheiro: `import` só executa o módulo se ele ainda não
    estiver em `sys.modules`, e vários testes aqui contam com o arranque a falhar. Carregá-lo
    uma vez com o ambiente limpo torna o `reload` de cada teste a única execução observada,
    corra o ficheiro sozinho ou no meio da suite.
    """
    return importlib.import_module("otm_api.main")


@pytest.fixture(autouse=True)
def _restore_app_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Outros módulos importam `otm_api.main`: devolver-lhes a app default."""
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    _main()
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    importlib.reload(_main())


def _reload(monkeypatch: pytest.MonkeyPatch, **env: str) -> object:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    main = _main()
    importlib.reload(main)
    return main.app


def _behind_the_proxy(app: object) -> TestClient:
    """A app tal como o uvicorn a serve num deployment com proxy no mesmo host."""
    served = ProxyHeadersMiddleware(app, trusted_hosts=Config("otm_api.main:app").forwarded_allow_ips)
    return TestClient(served, client=_LOOPBACK)


def _staging_client(monkeypatch: pytest.MonkeyPatch, *, limit: str, trusted_proxy: str) -> TestClient:
    app = _reload(monkeypatch, OTM_ENV="staging", OTM_RATE_LIMIT=limit, OTM_TRUSTED_PROXY=trusted_proxy)
    return _behind_the_proxy(app)


def _codes(client: TestClient, caller: str, count: int) -> list[int]:
    headers = {"X-Forwarded-For": f"{caller}, 127.0.0.1"}
    return [client.get("/health", headers=headers).status_code for _ in range(count)]


# --- o sintoma: um chamador esgotava o orçamento do serviço inteiro ---------------------


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_the_service_wide_bucket_is_no_longer_reachable_by_default(
    environment: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem declaração, a app recusa arrancar em vez de servir 429 a toda a gente por causa de um."""
    monkeypatch.setenv("OTM_ENV", environment)

    with pytest.raises(TrustedProxyConfigError, match="OTM_TRUSTED_PROXY"):
        importlib.reload(_main())


def test_a_declared_proxy_gives_every_caller_its_own_budget_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """O inverso exato do sintoma medido: a Alice gasta 120, e o Bob continua servido."""
    client = _behind_the_proxy(_reload(monkeypatch, OTM_ENV="staging", OTM_TRUSTED_PROXY="1"))

    _codes(client, "203.0.113.10", 120)

    assert _codes(client, "198.51.100.20", 5) == [200] * 5


def test_the_declared_proxy_still_limits_a_single_busy_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    """Devolver o balde por chamador não pode significar devolver o limite a ninguém."""
    client = _behind_the_proxy(_reload(monkeypatch, OTM_ENV="staging", OTM_TRUSTED_PROXY="1"))

    codes = _codes(client, "203.0.113.10", 130)

    assert codes.count(429) == 10


# --- a recusa tem de ser acionável -----------------------------------------------------


def _startup_error(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("OTM_ENV", "production")

    with pytest.raises(TrustedProxyConfigError) as excinfo:
        importlib.reload(_main())
    return str(excinfo.value)


@pytest.mark.parametrize("expected", ["OTM_TRUSTED_PROXY=1", "OTM_TRUSTED_PROXY=0"])
def test_the_refusal_names_both_valid_declarations(
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert expected in _startup_error(monkeypatch)


def test_the_refusal_states_the_availability_cost_of_declaring_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem isto, `OTM_TRUSTED_PROXY=0` é só a opção que faz o erro desaparecer."""
    assert "one busy client can 429 everyone else" in _startup_error(monkeypatch)


def test_the_refusal_names_the_limit_that_is_at_stake(monkeypatch: pytest.MonkeyPatch) -> None:
    assert "120/minute" in _startup_error(monkeypatch)


def test_the_refusal_names_the_uvicorn_flags_that_option_1_requires(monkeypatch: pytest.MonkeyPatch) -> None:
    assert "--forwarded-allow-ips" in _startup_error(monkeypatch)


def test_the_refusal_offers_the_escape_hatch_for_a_gateway_that_already_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "OTM_RATE_LIMIT_DISABLED=1" in _startup_error(monkeypatch)


# --- onde a declaração NÃO é exigida ---------------------------------------------------


def test_local_development_still_starts_with_no_configuration_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """`development` não tem limite por defeito: exigir a declaração aí seria burocracia."""
    client = TestClient(_reload(monkeypatch))

    assert client.get("/health").status_code == 200


def test_development_with_an_explicit_limit_still_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(_reload(monkeypatch, OTM_RATE_LIMIT="5/minute"))

    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_a_disabled_limit_needs_no_proxy_declaration(environment: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem limite não há balde, logo não há decisão a tomar sobre a identidade do chamador."""
    client = TestClient(_reload(monkeypatch, OTM_ENV=environment, OTM_RATE_LIMIT_DISABLED="1"))

    assert client.get("/health").status_code == 200


# --- a declaração em si ----------------------------------------------------------------


@pytest.mark.parametrize("value", ["1", "true", "YES", "on", " On "])
def test_every_documented_affirmative_declares_a_trusted_proxy(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_TRUSTED_PROXY", value)

    assert resolve_trusted_proxy(environment="production", rate_limit="120/minute") is True


@pytest.mark.parametrize("value", ["0", "false", "NO", "off", " Off "])
def test_every_documented_negative_declares_no_trusted_proxy(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_TRUSTED_PROXY", value)

    assert resolve_trusted_proxy(environment="production", rate_limit="120/minute") is False


@pytest.mark.parametrize("value", ["maybe", "2", "sim", "true-ish", "-"])
def test_an_unrecognised_declaration_is_refused_instead_of_read_as_off(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma gralha não pode significar "off": era assim que o balde partilhado voltava em silêncio."""
    monkeypatch.setenv("OTM_TRUSTED_PROXY", value)

    with pytest.raises(TrustedProxyConfigError, match="not a recognised value"):
        resolve_trusted_proxy(environment="development", rate_limit=None)


def test_the_rejection_lists_the_accepted_declarations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_TRUSTED_PROXY", "maybe")

    with pytest.raises(TrustedProxyConfigError, match="off, on"):
        resolve_trusted_proxy(environment="development", rate_limit=None)


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_a_blank_declaration_counts_as_undeclared(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret de CI que resolveu para vazio: falhar fechado, não cair no balde partilhado."""
    monkeypatch.setenv("OTM_TRUSTED_PROXY", blank)

    with pytest.raises(TrustedProxyConfigError, match="not declared"):
        resolve_trusted_proxy(environment="production", rate_limit="120/minute")


def test_an_undeclared_proxy_without_a_limit_is_simply_untrusted() -> None:
    assert resolve_trusted_proxy(environment="production", rate_limit=None) is False


def test_an_undeclared_proxy_in_development_is_simply_untrusted() -> None:
    assert resolve_trusted_proxy(environment="development", rate_limit="5/minute") is False


# --- declarar `0` também não pode ser silencioso ---------------------------------------


def test_declaring_no_proxy_states_the_shared_bucket_at_startup(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`OTM_TRUSTED_PROXY=0` é uma escolha legítima, mas o seu custo tem de estar no log."""
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_TRUSTED_PROXY", "0")

    with caplog.at_level(logging.WARNING, logger="otm.api"):
        importlib.reload(_main())

    assert "rate_limit_shared_bucket" in caplog.text


def test_the_shared_bucket_line_is_a_warning(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_TRUSTED_PROXY", "0")

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(_main())

    assert [r.levelname for r in caplog.records if "rate_limit_shared_bucket" in r.message] == ["WARNING"]


def test_the_shared_bucket_line_names_the_limit_and_the_consequence() -> None:
    line = describe_shared_bucket_consequence(
        environment="production",
        rate_limit="120/minute",
        trusted_proxy=False,
    )

    assert line is not None
    assert "120/minute" in line
    assert "one busy client can 429 everyone else" in line


def test_a_trusted_proxy_has_no_shared_bucket_to_warn_about() -> None:
    assert (
        describe_shared_bucket_consequence(environment="production", rate_limit="120/minute", trusted_proxy=True)
        is None
    )


def test_no_limit_means_no_shared_bucket_warning() -> None:
    assert describe_shared_bucket_consequence(environment="production", rate_limit=None, trusted_proxy=False) is None


def test_development_is_not_warned_about_a_proxy_it_does_not_have() -> None:
    """Em `development` o cabeçalho não aparece; avisar sempre seria ruído em cada arranque."""
    assert (
        describe_shared_bucket_consequence(environment="development", rate_limit="5/minute", trusted_proxy=False)
        is None
    )


def test_a_trusted_proxy_startup_says_nothing_about_a_shared_bucket(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_TRUSTED_PROXY", "1")

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(_main())

    assert "rate_limit_shared_bucket" not in caplog.text


# --- distinguir os dois 429 -------------------------------------------------------------


def _spend_the_shared_bucket(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    client = _staging_client(monkeypatch, limit="1/minute", trusted_proxy="0")
    with caplog.at_level(logging.WARNING, logger="otm.api"):
        _codes(client, "203.0.113.1", 1)
        _codes(client, "198.51.100.2", 1)


def test_a_429_from_the_shared_bucket_has_its_own_event_name(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Do lado do cliente os dois 429 são iguais; "está tudo a dar 429" tem de ter resposta no log."""
    _spend_the_shared_bucket(monkeypatch, caplog)

    assert "rate_limit_exceeded_shared_bucket" in caplog.text


def test_a_429_from_a_caller_of_its_own_keeps_the_plain_event_name(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = _staging_client(monkeypatch, limit="1/minute", trusted_proxy="1")

    with caplog.at_level(logging.WARNING, logger="otm.api"):
        _codes(client, "203.0.113.1", 2)

    assert [r.message for r in caplog.records if r.message.startswith("rate_limit_exceeded")] == ["rate_limit_exceeded"]


# --- a propriedade de segurança tem de sobreviver a tudo isto ---------------------------


def test_declaring_no_proxy_still_refuses_to_mint_buckets_from_a_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """O motivo original da correção: rodar o cabeçalho não pode reabrir crédito."""
    client = _staging_client(monkeypatch, limit="5/minute", trusted_proxy="0")

    codes = [_codes(client, f"203.0.113.{i + 1}", 1)[0] for i in range(20)]

    assert codes.count(200) == 5


def test_a_trusted_proxy_does_not_let_a_caller_escape_its_own_spent_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confiar no proxy é confiar no endereço que ele resolve, não no que o cliente escreve."""
    client = _staging_client(monkeypatch, limit="3/minute", trusted_proxy="1")

    codes = _codes(client, "203.0.113.7", 6)

    assert codes.count(429) == 3
