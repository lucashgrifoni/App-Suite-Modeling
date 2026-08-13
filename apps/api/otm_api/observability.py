"""
Observabilidade: request_id, duração e logs JSON estruturados.

Não regista corpo de pedidos nem payloads de documento/análise.

Uma linha JSON por evento — e isso passou a incluir o que o uvicorn escreve. `setup_api_logging`
só configurava o logger raiz, e o uvicorn instala handlers próprios em ``uvicorn.access`` e
``uvicorn.error`` com `propagate` desligado. Medido no mesmo stdout: 172 linhas JSON contra 175
de texto simples, ou seja um coletor que faça `json.loads` por linha falha em metade do stream.
Ver `_route_uvicorn_through_the_json_handler` para o que muda e para o que se perderia se
mudasse a mais.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import traceback
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from otm_api.api_error_messages import msg_internal_error
from otm_api.error_locale import (
    reset_api_error_locale,
    resolve_api_error_locale_from_accept_language,
    set_api_error_locale_for_request,
)

LOG = logging.getLogger("otm.api")


class InvalidLogLevelError(ValueError):
    """``OTM_LOG_LEVEL`` tem um valor que não nomeia um nível de log."""


#: Níveis aceites. `getattr(logging, value, logging.INFO)` resolvia **qualquer** atributo em
#: maiúsculas do módulo `logging`, e o default só cobre nomes que não existem lá — nunca um nome
#: que existe e não é um nível. Três modos de falha, todos medidos:
#:
#: * `trace` e `10` caíam em INFO sem uma linha de aviso (o número é o que muitas ferramentas
#:   aceitam, por isso está aqui como forma válida em vez de ser mais uma queda silenciosa);
#: * `NOTSET` punha o nível do logger raiz a 0, que para o raiz significa "emite tudo" — quem o
#:   lesse como "deixa no default" ficava com DEBUG completo em produção;
#: * `BASIC_FORMAT` resolvia para a *string de formato* `logging.BASIC_FORMAT`, e o `setLevel`
#:   rebentava com `ValueError: Unknown level`, abortando a API no import com um erro cru.
#:
#: `OTM_ENV`, `OTM_TRUSTED_PROXY`, `OTM_RATE_LIMIT` e `OTM_MAX_YAML_NODES` recusam valores
#: desconhecidos com um erro nomeado; esta era a única variável sem história de validação.
_LOG_LEVEL_BY_VALUE: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.CRITICAL,
    "50": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "40": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "30": logging.WARNING,
    "INFO": logging.INFO,
    "20": logging.INFO,
    "DEBUG": logging.DEBUG,
    "10": logging.DEBUG,
}

# Propagar um trace id do cliente é deliberado, mas adotá-lo *sem validar* não: um id de
# 4000 carateres inflaciona todas as linhas de log do pedido e um valor arbitrário
# (chavetas, newlines, texto livre) suja o campo pelo qual a auditoria correlaciona. Formato
# aceite: até 128 carateres imprimíveis do conjunto usado por UUID, W3C `traceparent` e ids
# de serviço; qualquer outra coisa é descartada e o servidor gera o seu.
_ACCEPTABLE_REQUEST_ID = re.compile(r"[A-Za-z0-9._:+/=-]{1,128}")


def resolve_request_id(header_value: str | None) -> str:
    """Trace id do cliente quando é aceitável; caso contrário, um `uuid4` do servidor."""
    candidate = (header_value or "").strip()
    if _ACCEPTABLE_REQUEST_ID.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def resolve_log_level() -> int:
    """Nível efetivo de ``OTM_LOG_LEVEL``, ou erro nomeado se o valor não for um nível.

    Lido aqui e não no import do módulo para que o valor seja o que o processo tem no arranque,
    e para que um teste o possa variar sem recarregar o pacote.
    """
    raw = (os.environ.get("OTM_LOG_LEVEL") or "INFO").strip().upper()
    level = _LOG_LEVEL_BY_VALUE.get(raw)
    if level is None:
        accepted = ", ".join(sorted(_LOG_LEVEL_BY_VALUE))
        raise InvalidLogLevelError(
            f"OTM_LOG_LEVEL={raw!r} does not name a log level. Accepted values: {accepted} "
            "(unset = INFO). Refusing to fall back to INFO, which hid typos such as `trace`, and "
            "refusing NOTSET, which on the root logger means `emit everything` and would turn a "
            "production process to full DEBUG output without the operator asking for it."
        )
    return level


#: Loggers que o uvicorn configura por dictConfig com handlers próprios e `propagate` desligado.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi")


def _route_uvicorn_through_the_json_handler() -> None:
    """Faz o uvicorn escrever no mesmo handler JSON, e cala a linha de acesso duplicada.

    Três defeitos no mesmo stream, todos com a mesma origem — o uvicorn nunca passava pelo
    `_JsonFormatter`:

    1. metade das linhas não era JSON, por isso um coletor que faça `json.loads` por linha
       falhava em metade delas;
    2. cada pedido era registado **duas** vezes, e a cópia do uvicorn não trazia `request_id`,
       logo não se correlacionava com nada;
    3. o `ObservabilityMiddleware` regista `request.url.path` (sem query) de propósito, e a
       linha de acesso do uvicorn ao lado escrevia o URL completo — o cuidado de não registar
       dados do pedido era desfeito na linha seguinte.

    O que se perderia se isto fosse só "desligar o access log": a linha do uvicorn era a única
    a nomear o endereço do cliente, e era a única a registar o preflight CORS recusado, que o
    `CORSMiddleware` responde sem chamar `call_next`. Por isso o `client` passou a ir na linha
    estruturada (ver `_log_http_request`) e o `ObservabilityMiddleware` passou a correr por fora
    do `CORSMiddleware` (ver `main.py`). Só depois de as duas coisas serem verdade é que calar
    `uvicorn.access` deixa de custar informação.

    Erros e avisos do próprio servidor (`uvicorn.error`, `uvicorn.asgi`) continuam a ser
    emitidos — apenas em JSON.
    """
    for name in _UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


def setup_api_logging() -> None:
    """Configura logging JSON para stdout (uma linha JSON por evento)."""
    level = resolve_log_level()
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)
    LOG.setLevel(level)
    _route_uvicorn_through_the_json_handler()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "path",
            "client",
            "status_code",
            "duration_ms",
            "event_name",
            "exc_type",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception_only(record.exc_info[1])).strip()
            # A stack ia inteira para o stdout como texto simples de várias linhas, escrita pelo
            # `ServerErrorMiddleware` do Starlette e pelo uvicorn — o pedaço menos parseável do
            # stream, e o único sítio onde ela existia. Encaminhar esses loggers para este
            # formatter sem a trazer para dentro trocava "log meio JSON" por "log sem stack",
            # que é pior. Vai como valor de uma chave, por isso continua a ser uma linha só.
            payload["traceback"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        return json.dumps(payload, ensure_ascii=False)


def _client_host(request: Request) -> str | None:
    """Endereço aparente de quem chama, ou ``None`` quando o transporte não o dá.

    Estava só na linha de acesso do uvicorn, que deixou de ser emitida por duplicar esta (ver
    `_route_uvicorn_through_the_json_handler`). Era o único campo que ela trazia e este registo
    não tinha, e é o que liga um 401 ou um 429 a uma origem — calar a linha sem o trazer para
    aqui teria trocado ruído por perda de informação.
    """
    client = request.client
    return client.host if client else None


def _log_http_request(
    *,
    event_name: str,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    level: int = logging.INFO,
    exc_type: str | None = None,
    client: str | None = None,
) -> None:
    extra: dict[str, Any] = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 3),
        "event_name": event_name,
    }
    if client:
        extra["client"] = client
    if exc_type:
        extra["exc_type"] = exc_type
    LOG.log(level, "http_request", extra=extra)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Gera `request_id`, mede duração e regista `http_request` (sem corpo)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = resolve_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        client = _client_host(request)
        start = time.perf_counter()
        loc_token = set_api_error_locale_for_request(
            resolve_api_error_locale_from_accept_language(request.headers.get("accept-language")),
        )
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                _log_http_request(
                    event_name="http_request_failed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=500,
                    duration_ms=duration_ms,
                    level=logging.ERROR,
                    exc_type=type(exc).__name__,
                    client=client,
                )
                raise
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Request-ID"] = request_id
            _log_http_request(
                event_name="http_request_completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client=client,
            )
            return response
        finally:
            reset_api_error_locale(loc_token)


def register_unhandled_exception_handler(app: FastAPI) -> None:
    """HTTPException passa; outros erros → JSON genérico com `request_id` (sem stack no cliente)."""

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):  # noqa: E501  # pragma: no cover - FastAPI's HTTPException handler intercepts first
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=dict(exc.headers) if exc.headers else {},
            )
        rid = getattr(request.state, "request_id", None)
        # Duração/status final já registados pelo `ObservabilityMiddleware` na resposta 500.
        LOG.exception(
            "unhandled_route_exception",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "event_name": "unhandled_route_exception",
            },
        )
        # A 500 sai por fora do `ObservabilityMiddleware` (o `ServerErrorMiddleware` do
        # Starlette é o mais exterior de todos), por isso era a única resposta desta API sem
        # `X-Request-ID` — presente em 200, 401, 422, 429. Um cliente que só tenha o cabeçalho
        # para correlacionar ficava exatamente sem ele no estado em que mais precisa dele.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": msg_internal_error(),
                "request_id": rid,
            },
            headers={"X-Request-ID": rid} if rid else None,
        )
