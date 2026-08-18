"""
Regressão: `OTM_API_KEY` é a única variável do perímetro sem qualquer controlo de valor, e
por isso aceitava como segredo partilhado exatamente as palavras com que um operador tenta
**desligar** o perímetro.

Medido antes da correção, com `OTM_ENV=development` e `GET /v1/templates`:

    OTM_API_KEY   sem chave   chave errada   valor literal da variável
    'false'          401          401                200   <-- lê-se "desligado", é o segredo
    'off'            401          401                200
    '0' / 'true'     401          401                200
    'none' 'null'    401          401                200
    'disabled'       401          401                200
    'changeme'       401          401                200

E o arranque escrevia `api_key=enforced`, que é verdade e é tranquilizador — a linha é
idêntica quer o segredo sejam 32 bytes aleatórios quer seja a palavra `disabled`.

No mesmo ficheiro, `OTM_ENV=prd` e `OTM_TRUSTED_PROXY=maybe` já abortam o arranque com um erro
nomeado, precisamente para que uma gralha não possa virar uma mudança de postura silenciosa.
Esta correção estende esse tratamento à credencial, e separa dois casos que não têm a mesma
resposta certa:

* **um valor que é um interruptor, não um segredo** (`false`, `off`, `1`, `changeme`, ...):
  a intenção do operador é o contrário do efeito, por isso o arranque é recusado com uma
  mensagem que diz que a forma de desligar é *remover* a variável;
* **um segredo real mas fraco** (curto): a intenção e o efeito coincidem, o deployment é
  legítimo, e recusá-lo partiria instalações que hoje funcionam — leva uma linha de aviso
  própria no arranque, como `describe_shared_bucket_consequence` faz para o custo de
  `OTM_TRUSTED_PROXY=0`.
"""

from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Iterator

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402
from otm_api.perimeter_settings import (  # noqa: E402
    ApiKeyConfigError,
    describe_weak_api_key_consequence,
    resolve_api_key_perimeter,
)

_STRONG = "p3-api-key-quality-strong-secret"
_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def restore_main_module() -> Iterator[None]:
    """Quem recarrega `otm_api.main` tem de devolver a app default aos outros módulos."""
    yield
    for name in _ENVS:
        os.environ.pop(name, None)
    import otm_api.main as main

    importlib.reload(main)


# --- um interruptor não é um segredo ----------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["0", "false", "no", "off", "none", "null", "nil", "disabled", "disable", "changeme", "1", "true", "yes", "on"],
)
def test_a_switch_like_value_is_refused(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """O sintoma original: cada um destes valores virava o segredo partilhado."""
    monkeypatch.setenv("OTM_API_KEY", value)

    with pytest.raises(ApiKeyConfigError):
        resolve_api_key_perimeter()


@pytest.mark.parametrize("value", ["FALSE", "Off", "  none  ", "DISABLED"])
def test_the_refusal_is_not_defeated_by_case_or_spacing(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", value)

    with pytest.raises(ApiKeyConfigError):
        resolve_api_key_perimeter()


def test_the_refusal_says_that_unsetting_is_how_you_turn_it_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mensagem é a correção: sem ela o operador tenta `OTM_API_KEY=` e fica pior."""
    monkeypatch.setenv("OTM_API_KEY", "false")

    with pytest.raises(ApiKeyConfigError, match="unset"):
        resolve_api_key_perimeter()


def test_the_refusal_quotes_the_offending_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", "disabled")

    with pytest.raises(ApiKeyConfigError, match="disabled"):
        resolve_api_key_perimeter()


def test_the_app_refuses_to_start_with_a_switch_like_key(
    monkeypatch: pytest.MonkeyPatch,
    restore_main_module: None,
) -> None:
    """Um deploy que falha é observável; um perímetro adivinhado à segunda tentativa não é."""
    monkeypatch.setenv("OTM_API_KEY", "off")
    import otm_api.main as main

    with pytest.raises(ApiKeyConfigError, match="OTM_API_KEY"):
        importlib.reload(main)


def test_a_process_that_reaches_the_switch_like_value_at_request_time_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    O middleware relê a variável a cada pedido, por isso precisa de resposta para o estado
    que o arranque já recusaria — e essa resposta é o 401 documentado, não um 500.
    """
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setenv("OTM_API_KEY", "false")

    r = client.get("/v1/templates")

    assert r.status_code == 401, r.text


def test_that_fail_closed_rejection_keeps_the_documented_code(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setenv("OTM_API_KEY", "false")

    assert client.get("/v1/templates").json()["code"] == "API_KEY_MISCONFIGURED"


def test_the_switch_like_value_cannot_be_used_as_the_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    """A parte que interessa: `false` deixou de abrir a porta a quem escreva `false`."""
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setenv("OTM_API_KEY", "false")

    assert client.get("/v1/templates", headers={"X-OTM-API-Key": "false"}).status_code == 401


# --- o que a recusa **não** pode passar a apanhar ---------------------------------------


def test_a_real_secret_still_enforces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", _STRONG)
    perimeter = resolve_api_key_perimeter()

    assert (perimeter.enforced, perimeter.secret, perimeter.misconfigured) == (True, _STRONG, False)


@pytest.mark.parametrize(
    "value",
    ["s3cr3t", "not-a-real-key", "offsite-backup-2026", "none-of-your-business", "true-random-0f3a", "N0", "0ff"],
)
def test_secrets_that_merely_look_switch_like_are_still_accepted(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A recusa é por valor exato, não por substring nem por comprimento.

    `offsite-backup-2026` contém `off`, `none-of-your-business` contém `none`, e segredos
    curtos como `s3cr3t` estão em uso em deployments reais. Uma guarda contra falsos aceites
    que comece a recusar credenciais legítimas troca um defeito por outro.
    """
    monkeypatch.setenv("OTM_API_KEY", value)

    assert resolve_api_key_perimeter().secret == value


def test_a_short_but_real_secret_still_opens_the_door(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")

    assert TestClient(app).get("/v1/templates", headers={"X-OTM-API-Key": "s3cr3t"}).status_code == 200


def test_unset_still_means_the_perimeter_is_off() -> None:
    assert resolve_api_key_perimeter().enforced is False


def test_a_blank_value_still_fails_closed_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """`OTM_API_KEY="   "` continua a ser "ligado e nada serve" — não passa a abortar."""
    monkeypatch.setenv("OTM_API_KEY", "   ")
    perimeter = resolve_api_key_perimeter()

    assert (perimeter.enforced, perimeter.secret, perimeter.misconfigured) == (True, None, True)


# --- um segredo fraco é legítimo, mas não pode ser indistinguível de um forte ------------


def test_a_weak_secret_is_called_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")

    assert describe_weak_api_key_consequence(resolve_api_key_perimeter())


def test_the_weak_secret_line_says_how_to_generate_a_real_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", "x")
    line = describe_weak_api_key_consequence(resolve_api_key_perimeter())

    assert "token_urlsafe" in (line or "")


def test_the_weak_secret_line_never_prints_the_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """O aviso vai para o stdout do processo; o segredo não pode ir com ele."""
    monkeypatch.setenv("OTM_API_KEY", "hunter2")
    line = describe_weak_api_key_consequence(resolve_api_key_perimeter())

    assert "hunter2" not in (line or "")


def test_a_strong_secret_says_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", _STRONG)

    assert describe_weak_api_key_consequence(resolve_api_key_perimeter()) is None


def test_an_off_perimeter_says_nothing() -> None:
    assert describe_weak_api_key_consequence(resolve_api_key_perimeter()) is None


def test_a_blank_value_says_nothing_here(monkeypatch: pytest.MonkeyPatch) -> None:
    """O caso em branco já tem a sua própria linha (`api_key=misconfigured`); duas seria ruído."""
    monkeypatch.setenv("OTM_API_KEY", "   ")

    assert describe_weak_api_key_consequence(resolve_api_key_perimeter()) is None


def test_startup_warns_about_a_weak_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "api_key_weak" in caplog.text


def test_that_startup_line_is_a_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert [r.levelname for r in caplog.records if "api_key_weak" in r.message] == ["WARNING"]


def test_a_strong_secret_produces_no_such_line(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    restore_main_module: None,
) -> None:
    monkeypatch.setenv("OTM_API_KEY", _STRONG)
    import otm_api.main as main

    with caplog.at_level(logging.INFO, logger="otm.api"):
        importlib.reload(main)

    assert "api_key_weak" not in caplog.text


def test_the_perimeter_line_itself_is_unchanged_by_a_weak_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """A linha de perímetro tem consumidores; o aviso é uma linha nova, não uma alteração."""
    from otm_api.cors_settings import resolve_cors_profile
    from otm_api.perimeter_settings import describe_effective_perimeter, resolve_rate_limit_default

    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_API_KEY", "s3cr3t")
    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=resolve_rate_limit_default(),
    )

    assert line == "api_perimeter environment=production api_key=enforced rate_limit=120/minute cors_origins=0"
