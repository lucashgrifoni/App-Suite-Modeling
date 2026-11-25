"""Middleware opcional: exige chave de API para ``/v1/*`` quando ``OTM_API_KEY`` está definido."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# A **mesma** função com que o `Router` do Starlette resolve o caminho antes de casar a rota
# (ver `starlette.routing.Router.app`). Importada do módulo público onde o router a consome, e
# não de `starlette._utils`, onde é definida: se uma versão futura a mover, renomear ou mudar
# a semântica, isto falha no import ou no teste que fixa a identidade — em vez de o perímetro
# voltar a divergir do router em silêncio. Ver `tests/test_p3_api_root_path_perimeter.py`.
from starlette.routing import get_route_path

from otm_api.api_error_messages import msg_api_key_misconfigured, msg_api_key_required, msg_api_key_unusable
from otm_api.perimeter_settings import ApiKeyConfigError, ApiKeyPerimeter, resolve_api_key_perimeter

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


def _rejection(code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=401, content={"code": code, "message": message}, headers=_CHALLENGE)


def _unauthorized(perimeter: ApiKeyPerimeter) -> JSONResponse:
    if perimeter.misconfigured:
        return _rejection("API_KEY_MISCONFIGURED", msg_api_key_misconfigured())
    return _rejection("API_KEY_REQUIRED", msg_api_key_required())


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """
    Lê ``OTM_API_KEY`` em cada pedido (permite testes com ``monkeypatch`` sem recarregar a app).

    ``OPTIONS`` e rotas fora de ``/v1`` não exigem chave.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        # `request.url.path` é `scope["path"]`, o caminho **na rede** — que num deployment em
        # sub-caminho (proxy que corta o prefixo + `uvicorn --root-path /api`, ou
        # `FastAPI(root_path=...)`) traz o prefixo à frente. O router resolve com
        # `get_route_path`, que o remove antes de casar, por isso qualquer `root_path` não
        # vazio caía entre os dois: `/api/v1/templates` não começava por `/v1` e o middleware
        # deixava passar, enquanto a rota `/v1/templates` casava e executava à mesma. Medido:
        # as 17 operações `/v1` respondiam sem credencial, e uma chave errada também, com o
        # arranque a escrever `api_key=enforced`. Decidir no mesmo caminho em que o router
        # decide é o que fecha a divergência — e mantê-la fechada é responsabilidade do teste
        # que fixa a origem do caminho.
        path = get_route_path(request.scope)
        if not path.startswith("/v1"):
            return await call_next(request)
        try:
            perimeter = resolve_api_key_perimeter()
        except ApiKeyConfigError:
            # `resolve_api_key_perimeter` recusa um valor que é um interruptor e não uma
            # credencial (`OTM_API_KEY=false`), o que normalmente aborta o arranque — este
            # middleware relê a variável a cada pedido, por isso tem de ter resposta para o
            # estado que o processo não deveria conseguir alcançar. É o 401 documentado e não
            # um 500: a variável está definida e inutilizável, exatamente como quando está em
            # branco, e a diferença não é do cliente.
            return _rejection("API_KEY_MISCONFIGURED", msg_api_key_unusable())
        if not perimeter.enforced:
            return await call_next(request)
        # `secret is None` com o perímetro ligado = variável definida mas em branco: nenhuma
        # credencial pode servir, por construção. Ver `resolve_api_key_perimeter`.
        if perimeter.secret is not None and _keys_match(_extract_api_key(request), perimeter.secret):
            return await call_next(request)
        return _unauthorized(perimeter)
