"""Coverage — API perimeter/CORS env-driven configuration."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from otm_api.cors_settings import resolve_cors_profile  # noqa: E402
from otm_api.perimeter_settings import (  # noqa: E402
    _truthy,
    resolve_optional_api_secret,
    resolve_rate_limit_default,
)

_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in _ENVS:
        monkeypatch.delenv(v, raising=False)


def test_cors_development_default() -> None:
    p = resolve_cors_profile()
    assert p.environment == "development"
    assert p.allow_methods == ["*"]
    assert any("localhost" in o for o in p.origins)


def test_cors_production_no_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "production")
    p = resolve_cors_profile()
    assert p.environment == "production"
    assert p.origins == []
    assert "GET" in p.allow_methods and "*" not in p.allow_methods


def test_cors_production_explicit_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "prod")
    monkeypatch.setenv("OTM_CORS_ORIGINS", "https://a.example.com, https://b.example.com ,")
    p = resolve_cors_profile()
    assert p.origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "staging")
    p = resolve_cors_profile()
    assert p.environment == "staging"


def test_truthy_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    for val in ("1", "true", "YES", "on"):
        monkeypatch.setenv("OTM_RATE_LIMIT_DISABLED", val)
        assert _truthy("OTM_RATE_LIMIT_DISABLED") is True
    monkeypatch.setenv("OTM_RATE_LIMIT_DISABLED", "no")
    assert _truthy("OTM_RATE_LIMIT_DISABLED") is False


def test_api_secret_set_and_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_optional_api_secret() is None
    monkeypatch.setenv("OTM_API_KEY", "  s3cr3t  ")
    assert resolve_optional_api_secret() == "s3cr3t"


def test_rate_limit_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_RATE_LIMIT_DISABLED", "1")
    assert resolve_rate_limit_default() is None


def test_rate_limit_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_RATE_LIMIT", "60/minute")
    assert resolve_rate_limit_default() == "60/minute"


def test_rate_limit_production_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", "production")
    assert resolve_rate_limit_default() == "120/minute"


def test_rate_limit_development_none() -> None:
    assert resolve_rate_limit_default() is None
