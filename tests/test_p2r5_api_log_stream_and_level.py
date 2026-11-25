"""
Regressão: o stdout da API era só meio JSON, e `OTM_LOG_LEVEL` não tinha validação nenhuma.

**Stream.** `setup_api_logging()` prometia "uma linha JSON por evento" mas só configurava o
logger raiz. O uvicorn instala handlers próprios em `uvicorn.access` e `uvicorn.error` com
`propagate` desligado, por isso as linhas dele nunca passavam pelo `_JsonFormatter`. Medido num
único stdout: 172 linhas JSON contra 175 de texto simples. Três consequências: um coletor que
faça `json.loads` por linha falha em metade do stream; cada pedido era registado duas vezes e a
cópia não trazia `request_id`; e a linha do uvicorn escrevia o URL completo, com query string,
ao lado da linha da app que a retira de propósito. Os stack traces iam também em texto simples,
com caminhos absolutos do host e sem `request_id`.

**Nível.** `getattr(logging, _OTM_LOG_LEVEL, logging.INFO)` resolvia qualquer atributo em
maiúsculas do módulo `logging`. `trace` e `10` caíam em INFO em silêncio; `NOTSET` punha o raiz
a 0, que significa "emite tudo" e dava DEBUG completo em produção a quem o lesse como "deixa no
default"; `BASIC_FORMAT` resolvia para uma string de formato e abortava a API no import com um
`ValueError: Unknown level` cru.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402
from otm_api.observability import (  # noqa: E402
    InvalidLogLevelError,
    _JsonFormatter,
    resolve_log_level,
    setup_api_logging,
)

_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _run_with_level(value: str) -> subprocess.CompletedProcess[str]:
    """Importa a API num processo limpo com `OTM_LOG_LEVEL=<value>`."""
    script = (
        "import logging\n"
        "import otm_api.main  # noqa: F401\n"
        "print('LEVEL', logging.getLogger().level, logging.getLogger().isEnabledFor(logging.DEBUG))\n"
    )
    env = {
        "PATH": "",
        "SYSTEMROOT": "C:\\Windows",
        "PYTHONPATH": str(_REPO / "apps" / "api"),
        "PYTHONIOENCODING": "utf-8",
        "OTM_LOG_LEVEL": value,
    }
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO,
        env=env,
        check=False,
    )


# --- nível de log: valores aceites ----------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("DEBUG", logging.DEBUG),
        ("debug", logging.DEBUG),
        ("10", logging.DEBUG),
        ("INFO", logging.INFO),
        ("20", logging.INFO),
        ("WARNING", logging.WARNING),
        ("WARN", logging.WARNING),
        ("30", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("40", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
        ("FATAL", logging.CRITICAL),
        ("50", logging.CRITICAL),
        ("  info  ", logging.INFO),
    ],
)
def test_a_recognised_level_resolves(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    monkeypatch.setenv("OTM_LOG_LEVEL", value)

    assert resolve_log_level() == expected


def test_an_unset_variable_still_means_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTM_LOG_LEVEL", raising=False)

    assert resolve_log_level() == logging.INFO


def test_an_empty_variable_still_means_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret de CI que resolveu para vazio: o default é a leitura certa, não um erro."""
    monkeypatch.setenv("OTM_LOG_LEVEL", "")

    assert resolve_log_level() == logging.INFO


# --- nível de log: valores recusados --------------------------------------------------


@pytest.mark.parametrize("value", ["trace", "verbose", "garbage", "-1", "0", "NOTSET", "BASIC_FORMAT", "true"])
def test_an_unrecognised_level_is_refused(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("OTM_LOG_LEVEL", value)

    with pytest.raises(InvalidLogLevelError):
        resolve_log_level()


def test_notset_is_refused_rather_than_enabling_full_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    """`NOTSET` no logger raiz significa "emite tudo"; lê-se como "deixa no default"."""
    monkeypatch.setenv("OTM_LOG_LEVEL", "NOTSET")

    with pytest.raises(InvalidLogLevelError, match="NOTSET"):
        resolve_log_level()


def test_the_refusal_lists_the_accepted_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_LOG_LEVEL", "trace")

    with pytest.raises(InvalidLogLevelError, match="DEBUG"):
        resolve_log_level()


def test_the_refusal_names_the_offending_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_LOG_LEVEL", "trace")

    with pytest.raises(InvalidLogLevelError, match="TRACE"):
        resolve_log_level()


def test_a_format_string_attribute_no_longer_crashes_with_a_raw_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`BASIC_FORMAT` existe em `logging` e não é um nível; o `setLevel` rebentava."""
    monkeypatch.setenv("OTM_LOG_LEVEL", "BASIC_FORMAT")

    with pytest.raises(InvalidLogLevelError):
        setup_api_logging()


# --- nível de log: o processo real -----------------------------------------------------


def test_the_api_starts_with_a_recognised_level() -> None:
    completed = _run_with_level("WARNING")

    assert completed.returncode == 0, completed.stderr


def test_the_recognised_level_is_the_one_applied() -> None:
    completed = _run_with_level("WARNING")

    assert "LEVEL 30 False" in completed.stdout


def test_the_api_refuses_to_start_on_an_unrecognised_level() -> None:
    """Antes: arrancava calado em INFO, ou abortava com um `ValueError` cru."""
    completed = _run_with_level("trace")

    assert completed.returncode != 0


def test_the_startup_failure_names_the_variable() -> None:
    completed = _run_with_level("trace")

    assert "OTM_LOG_LEVEL" in completed.stderr


def test_notset_no_longer_turns_production_to_full_debug() -> None:
    completed = _run_with_level("NOTSET")

    assert "LEVEL 0 True" not in completed.stdout


# --- stream: uma linha JSON por evento -------------------------------------------------


def test_uvicorn_loggers_are_routed_through_the_json_handler() -> None:
    setup_api_logging()

    assert logging.getLogger("uvicorn.error").handlers == []


def test_uvicorn_loggers_propagate_to_the_root_handler() -> None:
    setup_api_logging()

    assert logging.getLogger("uvicorn.error").propagate is True


def test_the_duplicate_access_logger_is_silenced() -> None:
    """Uma linha por pedido: a cópia do uvicorn não trazia `request_id` e trazia a query string."""
    setup_api_logging()

    assert logging.getLogger("uvicorn.access").disabled is True


def test_the_server_error_logger_is_not_silenced() -> None:
    """Calar o access log não pode calar os erros do próprio servidor."""
    setup_api_logging()

    assert logging.getLogger("uvicorn.error").disabled is False


def test_a_uvicorn_line_is_emitted_as_json() -> None:
    """A linha do uvicorn passava ao lado do `_JsonFormatter`; agora é ele que a escreve."""
    record = logging.getLogger("uvicorn.error").makeRecord(
        "uvicorn.error", logging.INFO, __file__, 1, "Application startup complete.", (), None
    )

    assert json.loads(_JsonFormatter().format(record))["logger"] == "uvicorn.error"


# --- stream: o que a linha estruturada tem de continuar a dizer ------------------------


def test_the_request_line_names_the_client(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Era o único campo que a linha de acesso do uvicorn trazia e esta não."""
    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.get("/health")

    assert [r for r in caplog.records if getattr(r, "client", None)]


def test_the_request_line_still_strips_the_query_string(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """O cuidado de não registar dados do pedido era desfeito pela linha do uvicorn ao lado."""
    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.get("/v1/templates", params={"q": "SENSITIVE-QUERY-VALUE-abc123"})

    emitted = [r for r in caplog.records if r.name == "otm.api"]
    assert all("SENSITIVE-QUERY-VALUE-abc123" not in getattr(r, "path", "") for r in emitted)


def test_the_request_line_still_carries_the_request_id(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.get("/health")

    assert [r for r in caplog.records if getattr(r, "request_id", None)]


def test_a_rejected_cors_preflight_now_reaches_the_structured_log(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """O `CORSMiddleware` responde sem chamar `call_next`; era o único estado só no access log."""
    with caplog.at_level(logging.INFO, logger="otm.api"):
        client.options(
            "/v1/templates",
            headers={
                "Origin": "https://unlisted.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert [r for r in caplog.records if getattr(r, "path", None) == "/v1/templates"]


def test_the_rejected_preflight_response_carries_a_request_id(client: TestClient) -> None:
    r = client.options(
        "/v1/templates",
        headers={
            "Origin": "https://unlisted.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert r.headers.get("x-request-id")


# --- stream: a stack deixa de ir em texto simples --------------------------------------


def _failure_record() -> logging.LogRecord:
    try:
        raise ValueError("boom")
    except ValueError:
        return logging.getLogger("otm.api").makeRecord(
            "otm.api", logging.ERROR, __file__, 1, "unhandled_route_exception", (), sys.exc_info()
        )


def test_an_exception_record_keeps_its_full_stack() -> None:
    """Trocar "log meio JSON" por "log sem stack" seria pior do que o defeito."""
    payload = json.loads(_JsonFormatter().format(_failure_record()))

    assert "Traceback (most recent call last)" in payload["traceback"]


def test_the_stack_is_a_single_json_line() -> None:
    assert "\n" not in _JsonFormatter().format(_failure_record())


def test_the_short_exception_summary_is_kept() -> None:
    """`exception` continua a ser a linha curta que as consultas existentes leem."""
    assert json.loads(_JsonFormatter().format(_failure_record()))["exception"] == "ValueError: boom"
