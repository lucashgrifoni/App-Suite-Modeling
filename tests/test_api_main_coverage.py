"""Coverage — API root endpoint, rate-limit setup, observability logging/handler edges."""

from __future__ import annotations

import importlib
import logging

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_root_endpoint() -> None:
    from otm_api.main import app

    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert r.json()["service"]


def test_app_with_rate_limit_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_RATE_LIMIT", "10000/minute")
    import otm_api.main as m

    try:
        importlib.reload(m)  # rebuilds app with Limiter + SlowAPIMiddleware
        client = TestClient(m.app)
        assert client.get("/health").status_code == 200
    finally:
        monkeypatch.delenv("OTM_RATE_LIMIT", raising=False)
        importlib.reload(m)  # restore default app for other tests


def test_setup_logging_when_root_has_no_handlers() -> None:
    from otm_api.observability import setup_api_logging

    root = logging.getLogger()
    saved = root.handlers[:]
    try:
        root.handlers = []
        setup_api_logging()  # exercises the handler-installation branch
        assert root.handlers
    finally:
        root.handlers = saved


def test_exception_handler_http_exception_with_headers() -> None:
    from otm_api.observability import ObservabilityMiddleware, register_unhandled_exception_handler

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)
    register_unhandled_exception_handler(app)

    @app.get("/teapot")
    def teapot() -> None:
        raise HTTPException(status_code=418, detail="teapot", headers={"X-Teapot": "yes"})

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/teapot")
    assert r.status_code == 418
    assert r.headers.get("X-Teapot") == "yes"
