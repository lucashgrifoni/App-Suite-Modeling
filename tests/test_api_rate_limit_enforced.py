"""The global rate limit must actually return 429 — on every route.

`slowapi.middleware.SlowAPIMiddleware` enforced nothing here. It resolves the
matching route by scanning `app.routes` for an object with an `endpoint`
attribute, and FastAPI 0.141 leaves an opaque `_IncludedRouter` wrapper there
instead of flattened `APIRoute`s. Every route added via `include_router` —
`/health` and all of `/v1/*` — therefore resolved to `None` and was treated as
exempt. Only `/`, declared with a bare `@app.get`, was ever limited.

The existing tests only asserted that the app *builds* with a limit configured
(`tests/test_api_main_coverage.py` sets `10000/minute` and checks startup), so
CI could not see it. These tests assert observed 429s instead, which stays
valid whatever the implementation underneath.
"""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi.testclient import TestClient


def _client_with_limit(monkeypatch: pytest.MonkeyPatch, spec: str) -> TestClient:
    monkeypatch.setenv("OTM_RATE_LIMIT", spec)
    monkeypatch.delenv("OTM_RATE_LIMIT_DISABLED", raising=False)
    monkeypatch.delenv("OTM_API_KEY", raising=False)

    import otm_api.main as main

    importlib.reload(main)
    return TestClient(main.app)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/", None),
        ("GET", "/health", None),
        ("GET", "/v1/templates", None),
        ("POST", "/v1/models", {}),
    ],
)
def test_every_route_is_rate_limited(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str, payload: dict | None
) -> None:
    """`/health` and `/v1/*` were silently exempt; only `/` was ever limited."""
    client = _client_with_limit(monkeypatch, "3/minute")

    codes = [(client.get(path) if method == "GET" else client.post(path, json=payload)).status_code for _ in range(6)]

    assert 429 in codes, f"{method} {path} was never limited: {codes}"
    assert 429 not in codes[:3], f"{method} {path} limited before the budget ran out: {codes}"
    assert codes[-1] == 429, f"{method} {path} stopped limiting: {codes}"


def test_requests_below_the_limit_are_not_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_limit(monkeypatch, "50/minute")

    codes = [client.get("/health").status_code for _ in range(5)]

    assert codes == [200] * 5


def test_limit_response_is_the_documented_error_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_limit(monkeypatch, "1/minute")

    client.get("/health")
    blocked = client.get("/health")

    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "RATE_LIMITED"
    assert "message" in body
    # A client that cannot tell when to retry will just hammer the endpoint.
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.headers["X-RateLimit-Limit"] == "1"
    assert blocked.headers["X-RateLimit-Remaining"] == "0"


def test_rate_limit_headers_are_present_on_successful_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client_with_limit(monkeypatch, "10/minute")

    ok = client.get("/health")

    assert ok.status_code == 200
    assert ok.headers["X-RateLimit-Limit"] == "10"
    assert int(ok.headers["X-RateLimit-Remaining"]) == 9


def test_disabled_flag_turns_the_limit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_RATE_LIMIT", "1/minute")
    monkeypatch.setenv("OTM_RATE_LIMIT_DISABLED", "1")
    monkeypatch.delenv("OTM_API_KEY", raising=False)

    import otm_api.main as main

    importlib.reload(main)
    client = TestClient(main.app)

    assert [client.get("/health").status_code for _ in range(4)] == [200] * 4


def test_a_malformed_limit_fails_fast_instead_of_disabling_the_control(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo must not silently degrade into "no limit at all"."""
    monkeypatch.setenv("OTM_RATE_LIMIT", "onehundred-per-minute")
    monkeypatch.delenv("OTM_RATE_LIMIT_DISABLED", raising=False)

    import otm_api.main as main

    with pytest.raises(ValueError):
        importlib.reload(main)


@pytest.fixture(autouse=True)
def _restore_app_module() -> object:
    """Other test modules import `otm_api.main`; give them back the default app.

    The env is cleared here rather than relying on `monkeypatch` teardown
    ordering — the malformed-spec test leaves the module half-imported, and a
    reload while `OTM_RATE_LIMIT` still held garbage would raise during
    teardown and cascade into unrelated tests.
    """
    yield
    os.environ.pop("OTM_RATE_LIMIT", None)
    os.environ.pop("OTM_RATE_LIMIT_DISABLED", None)

    import otm_api.main as main

    importlib.reload(main)
