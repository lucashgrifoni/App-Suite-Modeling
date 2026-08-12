"""Global per-IP rate limit for every HTTP route.

This replaces `slowapi.middleware.SlowAPIMiddleware`, which silently enforced
nothing on this app. That middleware resolves the matching route by scanning
`app.routes` for an object carrying an `endpoint` attribute; when it finds none
it treats the request as exempt. Since FastAPI 0.141 an `app.include_router(...)`
call leaves an opaque `_IncludedRouter` wrapper in `app.routes` instead of the
flattened `APIRoute` objects, so every route registered that way — which here is
all of `/health` and all of `/v1/*` — resolved to `None` and skipped the limit
entirely. Only `/`, declared with a bare `@app.get`, was ever limited.

The failure was silent, produced no warning, and depended on the internal route
representation of two libraries at once. This module therefore does the one
thing the app actually needs — a global per-IP limit on every request — against
the public API of `limits` (the library slowapi itself builds on), so no route
introspection is involved and nothing can quietly opt a route out.

Scope: the counter lives in process memory, so with multiple workers the
effective limit is per worker, exactly as the previous in-memory configuration
behaved. It is an abuse-mitigation control, not a quota system; a shared
backend would be required for the latter.
"""

from __future__ import annotations

import logging
import time

from limits import RateLimitItem, parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("otm.api")

_UNKNOWN_CLIENT = "unknown"


def parse_rate_limit(spec: str) -> RateLimitItem:
    """Parse a rate-limit spec such as ``120/minute``.

    Raises `ValueError` on a malformed spec. Failing fast at startup is
    deliberate: a typo in `OTM_RATE_LIMIT` must not silently degrade into "no
    limit at all", which is the exact failure mode this module exists to fix.
    """
    return parse(spec)


def client_key(request: Request) -> str:
    """Identify the caller by peer address.

    Deliberately does NOT read `X-Forwarded-For`: that header is attacker
    controlled unless a trusted proxy overwrites it, and honouring it blindly
    would let any caller bypass the limit by varying one header. Behind a proxy,
    run the app with uvicorn's `--proxy-headers` and the appropriate
    `--forwarded-allow-ips`, which rewrites `request.client` from a trusted hop.
    """
    client = request.client
    return client.host if client and client.host else _UNKNOWN_CLIENT


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies one global limit to every request, keyed by client address."""

    def __init__(self, app, *, limit: RateLimitItem) -> None:
        super().__init__(app)
        self._limit = limit
        self._limiter = MovingWindowRateLimiter(MemoryStorage())

    async def dispatch(self, request: Request, call_next) -> Response:
        key = client_key(request)
        allowed = self._limiter.hit(self._limit, key)
        stats = self._limiter.get_window_stats(self._limit, key)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                extra={"event_name": "rate_limit_exceeded", "path": request.url.path},
            )
            response: Response = JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded: {self._limit}. Retry later.",
                },
            )
        else:
            response = await call_next(request)

        _apply_headers(response, limit=self._limit, remaining=stats.remaining, reset_time=stats.reset_time)
        return response


def _apply_headers(response: Response, *, limit: RateLimitItem, remaining: int, reset_time: float) -> None:
    response.headers["X-RateLimit-Limit"] = str(limit.amount)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    response.headers["X-RateLimit-Reset"] = str(int(reset_time))
    if response.status_code == 429:
        # Seconds, per RFC 9110 - never negative, and never 0 (which reads as
        # "retry immediately" and would encourage a hot loop).
        response.headers["Retry-After"] = str(max(1, int(reset_time - time.time())))
