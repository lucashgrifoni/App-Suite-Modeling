"""Middleware opcional: exige chave de API para ``/v1/*`` quando ``OTM_API_KEY`` está definido."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from otm_api.perimeter_settings import resolve_optional_api_secret


def _extract_api_key(request: Request) -> str | None:
    direct = (request.headers.get("x-otm-api-key") or "").strip()
    if direct:
        return direct
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        return tok or None
    return None


def _keys_match(presented: str | None, expected: str) -> bool:
    if presented is None:
        presented = ""
    try:
        return secrets.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))
    except ValueError:  # pragma: no cover - defensive: utf-8 encode of validated str does not raise
        return False


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """
    Lê ``OTM_API_KEY`` em cada pedido (permite testes com ``monkeypatch`` sem recarregar a app).

    ``OPTIONS`` e rotas fora de ``/v1`` não exigem chave.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if not path.startswith("/v1"):
            return await call_next(request)
        secret = resolve_optional_api_secret()
        if not secret:
            return await call_next(request)
        if _keys_match(_extract_api_key(request), secret):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={
                "code": "API_KEY_REQUIRED",
                "message": "Invalid or missing API key. Send X-OTM-API-Key or Authorization: Bearer.",
            },
        )
