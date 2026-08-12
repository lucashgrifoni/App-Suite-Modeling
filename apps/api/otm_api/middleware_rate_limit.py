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

Caller identity: see `client_key`. The short version is that by the time this
middleware runs, `request.client` may already have been rewritten from a
client-controlled header by uvicorn, so it is not trusted unless the operator
says a proxy is in front — `OTM_TRUSTED_PROXY`, documented in
`docs/architecture/DEPLOYMENT_INVARIANTS.md`.
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

# One shared bucket for every request whose apparent client address may have been
# derived from a forwarding header we were not told to trust. Deliberately not a
# valid host, so it can never collide with a real peer address.
_UNTRUSTED_FORWARDED_CLIENT = "<forwarded>"


def parse_rate_limit(spec: str) -> RateLimitItem:
    """Parse a rate-limit spec such as ``120/minute``.

    Raises `ValueError` on a malformed spec, and on a spec that parses but
    allows nothing (``0/minute``). Failing fast at startup is deliberate: a typo
    in `OTM_RATE_LIMIT` must not silently degrade into "no limit at all", which
    is the exact failure mode this module exists to fix — and `0` (the value
    many tools read as "unlimited", and what ``${LIMIT}/minute`` produces when
    `LIMIT` is unset) must not silently degrade into "no requests at all",
    which 429s even `/health` and turns a deploy into a restart loop.
    """
    item = parse(spec)
    if item.amount < 1:
        raise ValueError(
            f"OTM_RATE_LIMIT={spec!r} allows no requests at all: every caller, including the "
            "/health probe, would receive 429. To turn the limit off, set OTM_RATE_LIMIT_DISABLED=1."
        )
    return item


def _forwarded_for(request: Request) -> str:
    """Every ``X-Forwarded-For`` value, joined exactly as uvicorn joins them.

    Reading only the first header would miss the split form (`X-Forwarded-For: a`
    plus `X-Forwarded-For: b`), which uvicorn concatenates before choosing the
    client address — and a check that misses it is a check an attacker can walk
    around by sending the header twice.
    """
    return ", ".join(request.headers.getlist("x-forwarded-for"))


def client_key(request: Request, *, trust_forwarded: bool = False) -> str:
    """Identify the caller, refusing to let a header mint a fresh bucket.

    `request.client` is not necessarily the TCP peer. uvicorn 0.52 runs
    `ProxyHeadersMiddleware` **by default** (`proxy_headers=True`,
    `forwarded_allow_ips="127.0.0.1"`), outside this app, and it rewrites
    `scope["client"]` from `X-Forwarded-For` whenever the peer is loopback —
    which is every request in the same-host reverse-proxy deployment that
    `DEPLOYMENT_INVARIANTS.md` mandates. By the time this function runs the real
    peer is gone, so "just read the real IP" is not available to us.

    Hence an explicit trust decision, defaulting to distrust:

    - `trust_forwarded` (operator sets `OTM_TRUSTED_PROXY`): the address uvicorn
      resolved from the proxy chain is the caller. Correct only when a proxy the
      operator controls is actually in front — see `DEPLOYMENT_INVARIANTS.md`
      for the required uvicorn flags.
    - otherwise: a request carrying a forwarding header that could have produced
      the address we see is counted in one shared bucket. It still bounds abuse,
      and unlike a per-caller bucket it cannot be reset by rotating a header — a
      per-IP limit any caller can reset is worse than an honest global one.
    - a request with no forwarding header keeps its own per-peer bucket, which
      is the common direct-exposure case.

    The containment test cannot produce a false negative: uvicorn derives the
    address it installs by slicing one entry of this same header, so a rewritten
    address is always a substring of it. A false positive only costs a direct
    caller its own bucket, which fails closed.
    """
    client = request.client
    host = client.host if client and client.host else _UNKNOWN_CLIENT
    if trust_forwarded:
        return host
    forwarded = _forwarded_for(request)
    if forwarded and host in forwarded:
        return _UNTRUSTED_FORWARDED_CLIENT
    return host


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies one global limit to every request, keyed by client address."""

    def __init__(self, app, *, limit: RateLimitItem, trust_forwarded: bool = False) -> None:
        super().__init__(app)
        self._limit = limit
        self._trust_forwarded = trust_forwarded
        self._limiter = MovingWindowRateLimiter(MemoryStorage())
        self._reported_untrusted_forwarding = False

    def _report_untrusted_forwarding_once(self) -> None:
        """Say it in the log the first time, then stay quiet.

        Sharing one bucket is the safe answer, but it is also indistinguishable
        from "the limit is far too strict" unless the log says why. Once per
        process: a per-request line would be an attacker-controlled log flood.
        """
        if self._reported_untrusted_forwarding:
            return
        self._reported_untrusted_forwarding = True
        logger.warning(
            "rate_limit_forwarded_client_untrusted",
            extra={"event_name": "rate_limit_forwarded_client_untrusted"},
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        key = client_key(request, trust_forwarded=self._trust_forwarded)
        if key == _UNTRUSTED_FORWARDED_CLIENT:
            self._report_untrusted_forwarding_once()
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
