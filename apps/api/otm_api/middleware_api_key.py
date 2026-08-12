"""Middleware opcional: exige chave de API para ``/v1/*`` quando ``OTM_API_KEY`` está definido."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from otm_api.api_error_messages import msg_api_key_misconfigured, msg_api_key_required
from otm_api.perimeter_settings import ApiKeyPerimeter, resolve_api_key_perimeter

# RFC 9110 11.6.1: um 401 **tem** de trazer pelo menos um desafio. Sem ele, clientes HTTP,
# gateways e SDKs gerados a partir do OpenAPI não sabem como autenticar na tentativa seguinte.
_CHALLENGE = {"WWW-Authenticate": "Bearer"}


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


def _unauthorized(perimeter: ApiKeyPerimeter) -> JSONResponse:
    if perimeter.misconfigured:
        code, message = "API_KEY_MISCONFIGURED", msg_api_key_misconfigured()
    else:
        code, message = "API_KEY_REQUIRED", msg_api_key_required()
    return JSONResponse(status_code=401, content={"code": code, "message": message}, headers=_CHALLENGE)


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
        perimeter = resolve_api_key_perimeter()
        if not perimeter.enforced:
            return await call_next(request)
        # `secret is None` com o perímetro ligado = variável definida mas em branco: nenhuma
        # credencial pode servir, por construção. Ver `resolve_api_key_perimeter`.
        if perimeter.secret is not None and _keys_match(_extract_api_key(request), perimeter.secret):
            return await call_next(request)
        return _unauthorized(perimeter)
