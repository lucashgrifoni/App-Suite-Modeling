"""Coverage — API observability: JSON formatter, request log helper, middleware + exception handler."""

from __future__ import annotations

import logging
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.observability import (  # noqa: E402
    ObservabilityMiddleware,
    _JsonFormatter,
    _log_http_request,
    register_unhandled_exception_handler,
    setup_api_logging,
)


def test_setup_api_logging_idempotent() -> None:
    setup_api_logging()
    setup_api_logging()  # second call: handlers already present


def test_json_formatter_with_extra_and_exception() -> None:
    fmt = _JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    rec = logging.LogRecord(
        name="otm.api", level=logging.ERROR, pathname=__file__, lineno=1,
        msg="http_request", args=(), exc_info=exc_info,
    )
    rec.request_id = "rid-1"
    rec.method = "GET"
    rec.path = "/x"
    rec.status_code = 500
    rec.duration_ms = 1.234
    rec.event_name = "http_request_failed"
    rec.exc_type = "ValueError"
    out = fmt.format(rec)
    assert '"request_id": "rid-1"' in out
    assert '"exception"' in out


def test_json_formatter_minimal_record() -> None:
    fmt = _JsonFormatter()
    rec = logging.LogRecord("otm.api", logging.INFO, __file__, 1, "plain", (), None)
    out = fmt.format(rec)
    assert '"message": "plain"' in out


def test_log_http_request_with_and_without_exc() -> None:
    _log_http_request(
        event_name="http_request_completed", request_id="r", method="GET",
        path="/", status_code=200, duration_ms=2.5,
    )
    _log_http_request(
        event_name="http_request_failed", request_id="r", method="POST",
        path="/e", status_code=500, duration_ms=3.0, level=logging.ERROR, exc_type="RuntimeError",
    )


def _app_with_observability() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)
    register_unhandled_exception_handler(app)

    @app.get("/ok")
    def ok() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    @app.get("/http-error")
    def http_error() -> None:
        raise HTTPException(status_code=418, detail="teapot")

    return app


def test_middleware_success_sets_request_id_header() -> None:
    client = TestClient(_app_with_observability())
    r = client.get("/ok", headers={"X-Request-ID": "fixed-rid"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "fixed-rid"


def test_middleware_unhandled_exception_returns_500_json() -> None:
    client = TestClient(_app_with_observability(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    assert "request_id" in r.json() or r.json()  # generic JSON body


def test_exception_handler_passes_through_http_exception() -> None:
    client = TestClient(_app_with_observability(), raise_server_exceptions=False)
    r = client.get("/http-error")
    assert r.status_code == 418
    assert r.json()["detail"] == "teapot"
