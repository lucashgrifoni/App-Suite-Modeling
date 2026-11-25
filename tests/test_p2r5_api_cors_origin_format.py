"""
Regressão: uma `OTM_CORS_ORIGINS` malformada era aceite em silêncio, e o servidor partido ficava
indistinguível de um servidor bom.

`resolve_cors_profile` partia a variável por vírgulas e só testava o wildcard `*`. Com uma barra
final — `https://app.example.com/` — o servidor responde 200 **sem**
`Access-Control-Allow-Origin` (o browser deita a resposta fora) e devolve 400 no preflight,
enquanto a linha de arranque diz `cors_origins=1`, byte a byte igual à de um servidor correto. O
preflight recusado nem aparece no log estruturado, porque o `CORSMiddleware` responde antes da
observabilidade. `'not a url'`, `'https//app.example.com'` e `'[1,2,3]'` (partido em
`['[1','2','3]']`) eram aceites da mesma maneira.

Uma gralha de um carater punha todos os clientes de browser offline sem deixar um único sinal.
`OTM_ENV`, `OTM_TRUSTED_PROXY`, `OTM_RATE_LIMIT` e `OTM_CORS_ORIGINS=*` já recusam arrancar; as
origens eram a excepção que faltava.

O risco oposto está coberto abaixo: o formato aceite não pode recusar origens legítimas —
`localhost` com porta, literais IPv6, e os esquemas próprios de extensões de browser e apps
empacotadas, que chegam mesmo a APIs como esta.
"""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("fastapi")
from otm_api.cors_settings import InvalidCorsOriginsError, resolve_cors_profile  # noqa: E402
from otm_api.perimeter_settings import describe_effective_perimeter, resolve_api_key_perimeter  # noqa: E402

_MALFORMED = [
    "https://app.example.com/",
    "https//app.example.com",
    "not a url",
    "garbage!!",
    "[1",
    "3]",
    "https://app.example.com/path",
    "https://app.example.com?tenant=1",
    "https://app.example.com#frag",
    "https://user:secret@app.example.com",
    "http://",
    "app.example.com",
]

_LEGITIMATE = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://app.example.com",
    "https://admin.example.com:8443",
    "https://[::1]:8080",
    "https://[2001:db8::1]",
    "chrome-extension://mnopqrstuvwxyzabcdef",
    "moz-extension://11111111-2222-3333-4444-555555555555",
    "capacitor://localhost",
    "tauri://localhost",
    "null",
]


def _profile(monkeypatch: pytest.MonkeyPatch, origins: str, environment: str = "production"):
    monkeypatch.setenv("OTM_ENV", environment)
    monkeypatch.setenv("OTM_CORS_ORIGINS", origins)
    return resolve_cors_profile()


# --- o defeito: a gralha deixa de arrancar --------------------------------------------


@pytest.mark.parametrize("origin", _MALFORMED)
def test_a_malformed_origin_refuses_to_start(monkeypatch: pytest.MonkeyPatch, origin: str) -> None:
    with pytest.raises(InvalidCorsOriginsError):
        _profile(monkeypatch, origin)


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_the_refusal_applies_in_every_environment(monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
    """Um browser em dev é tão incapaz de igualar a origem partida como um em produção."""
    with pytest.raises(InvalidCorsOriginsError):
        _profile(monkeypatch, "https://app.example.com/", environment)


def test_a_malformed_entry_hidden_among_good_ones_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Descartar a má e arrancar repunha o servidor meio-partido que este erro torna visível."""
    with pytest.raises(InvalidCorsOriginsError):
        _profile(monkeypatch, "https://ok.example.com,not a url")


def test_a_json_looking_value_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """`'[1,2,3]'` partia em `['[1','2','3]']` e era anunciado como `cors_origins=3`."""
    with pytest.raises(InvalidCorsOriginsError):
        _profile(monkeypatch, "[1,2,3]")


def test_the_refusal_names_only_the_offending_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quem lê isto está a meio de um deploy com uma lista de dez origens."""
    with pytest.raises(InvalidCorsOriginsError) as excinfo:
        _profile(monkeypatch, "https://ok.example.com,https://typo.example.com/")

    listed = str(excinfo.value).partition("match: ")[2].partition(". An origin")[0]
    assert listed == "'https://typo.example.com/'"


def test_the_refusal_says_what_a_correct_value_looks_like(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(InvalidCorsOriginsError) as excinfo:
        _profile(monkeypatch, "https://app.example.com/")

    assert "scheme://host[:port]" in str(excinfo.value)


def test_the_refusal_explains_the_symptom_the_operator_would_have_seen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(InvalidCorsOriginsError) as excinfo:
        _profile(monkeypatch, "https://app.example.com/")

    assert "Access-Control-Allow-Origin" in str(excinfo.value)


def test_the_broken_server_can_no_longer_log_a_healthy_perimeter_line(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """O núcleo do defeito: `cors_origins=1` era emitido pelos dois servidores."""
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "https://app.example.com/")

    with caplog.at_level(logging.INFO, logger="otm.api"), pytest.raises(InvalidCorsOriginsError):
        resolve_cors_profile()

    assert "cors_origins=1" not in caplog.text


# --- o que não pode partir: as origens legítimas ---------------------------------------


@pytest.mark.parametrize("origin", _LEGITIMATE)
def test_a_legitimate_origin_still_starts(monkeypatch: pytest.MonkeyPatch, origin: str) -> None:
    assert _profile(monkeypatch, origin).origins == [origin]


def test_a_multi_origin_list_still_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(monkeypatch, "https://app.example.com,https://admin.example.com:8443")

    assert profile.origins == ["https://app.example.com", "https://admin.example.com:8443"]


def test_surrounding_whitespace_is_still_forgiven(monkeypatch: pytest.MonkeyPatch) -> None:
    """A lista vem de YAML e de ficheiros `.env`; espaços à volta da vírgula são normais."""
    profile = _profile(monkeypatch, " https://app.example.com , https://admin.example.com ")

    assert profile.origins == ["https://app.example.com", "https://admin.example.com"]


def test_a_trailing_comma_is_still_forgiven(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _profile(monkeypatch, "https://app.example.com,").origins == ["https://app.example.com"]


def test_the_development_defaults_still_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    """Controlo: o par que o dev server do frontend usa não pode passar a abortar o arranque."""
    monkeypatch.setenv("OTM_ENV", "development")
    monkeypatch.delenv("OTM_CORS_ORIGINS", raising=False)

    assert resolve_cors_profile().origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_production_without_the_variable_still_serves_no_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "production")
    monkeypatch.delenv("OTM_CORS_ORIGINS", raising=False)

    assert resolve_cors_profile().origins == []


def test_the_wildcard_still_has_its_own_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """`*` não é uma origem malformada: tem uma mensagem própria, e ela não pode ser roubada."""
    with pytest.raises(InvalidCorsOriginsError) as excinfo:
        _profile(monkeypatch, "*")

    assert "every origin on the web" in str(excinfo.value)


def test_the_wildcard_is_still_honoured_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _profile(monkeypatch, "*", "development").origins == ["*"]


def test_a_good_list_still_logs_the_unchanged_perimeter_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "development")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "http://localhost:5173")

    line = describe_effective_perimeter(
        profile=resolve_cors_profile(),
        api_key=resolve_api_key_perimeter(),
        rate_limit=None,
    )

    assert line == "api_perimeter environment=development api_key=off rate_limit=off cors_origins=1"
