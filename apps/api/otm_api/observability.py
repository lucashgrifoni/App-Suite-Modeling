"""
Observabilidade: request_id, duração e logs JSON estruturados.

Não regista corpo de pedidos nem payloads de documento/análise.
"""

from __future__ import annotations

import json
import logging
import os
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
_OTM_LOG_LEVEL = os.environ.get("OTM_LOG_LEVEL", "INFO").upper()


def setup_api_logging() -> None:
    """Configura logging JSON para stdout (uma linha JSON por evento)."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        root.addHandler(handler)
    root.setLevel(getattr(logging, _OTM_LOG_LEVEL, logging.INFO))
    LOG.setLevel(getattr(logging, _OTM_LOG_LEVEL, logging.INFO))


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
            "status_code",
            "duration_ms",
            "event_name",
            "exc_type",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception_only(record.exc_info[1])).strip()
        return json.dumps(payload, ensure_ascii=False)


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
) -> None:
    extra = {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 3),
        "event_name": event_name,
    }
    if exc_type:
        extra["exc_type"] = exc_type
    LOG.log(level, "http_request", extra=extra)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Gera `request_id`, mede duração e regista `http_request` (sem corpo)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        header_rid = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
        request_id = header_rid.strip() if header_rid else str(uuid.uuid4())
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
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
            )
            return response
        finally:
            reset_api_error_locale(loc_token)


def register_unhandled_exception_handler(app: FastAPI) -> None:
    """HTTPException passa; outros erros → JSON genérico com `request_id` (sem stack no cliente)."""

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
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
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": msg_internal_error(),
                "request_id": rid,
            },
        )
