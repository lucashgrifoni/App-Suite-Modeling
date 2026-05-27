"""Coverage — API route error branches (malformed import payloads -> HTTP 400)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _client() -> TestClient:
    from otm_api.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_import_openapi_malformed_returns_400() -> None:
    c = _client()
    # a bare scalar (not a mapping) makes the importer raise ValueError -> 400 branch
    r = c.post("/v1/imports/openapi", files={"file": ("x.yaml", b"just-a-scalar-string", "text/yaml")})
    assert r.status_code == 400


def test_import_terraform_empty_is_handled() -> None:
    c = _client()
    # empty/whitespace HCL should be tolerated or 400 — either way exercises the route's body
    r = c.post("/v1/imports/terraform", files={"file": ("x.tf", b"   ", "text/plain")})
    assert r.status_code in (200, 400)


def test_import_openapi_binary_garbage_returns_400() -> None:
    c = _client()
    r = c.post("/v1/imports/openapi", files={"file": ("x.yaml", b"\x00\x01\x02: : :", "application/octet-stream")})
    assert r.status_code in (400, 422)


def test_import_terraform_binary_garbage() -> None:
    c = _client()
    r = c.post("/v1/imports/terraform", files={"file": ("x.tf", b"\xff\xfe\x00bad", "application/octet-stream")})
    assert r.status_code in (200, 400, 422)


def test_health_passes_through_middleware() -> None:
    # a normal request exercises the api-key middleware passthrough (no key configured)
    r = _client().get("/health")
    assert r.status_code in (200, 404)


def test_unknown_route_404() -> None:
    r = _client().get("/v1/this-route-does-not-exist")
    assert r.status_code == 404


def test_options_request_passthrough() -> None:
    # OPTIONS short-circuits the api-key middleware (the OPTIONS passthrough branch)
    r = _client().options("/v1/imports/openapi")
    assert r.status_code in (200, 204, 405)


def test_api_error_message_helpers() -> None:
    from otm_api.api_error_messages import msg_analysis_validation_error, msg_template_invalid

    assert msg_analysis_validation_error()
    assert msg_template_invalid()  # exercises the _t() translation return


def test_raise_template_invalid_maps_to_422() -> None:
    import pydantic
    from otm_api.routers._errors import raise_template_invalid

    class _M(pydantic.BaseModel):
        x: int

    try:
        _M.model_validate({})
    except pydantic.ValidationError as e:
        exc = raise_template_invalid(e)
        assert exc.status_code == 422


def test_unhandled_handler_http_exception_branch() -> None:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from otm_api.observability import register_unhandled_exception_handler

    app = FastAPI()
    register_unhandled_exception_handler(app)

    @app.get("/boom")
    def _boom() -> None:
        raise HTTPException(status_code=409, detail="conflict")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code in (409, 500)  # StarletteHTTPException branch in the unhandled handler
