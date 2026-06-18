"""In-process fixed-window rate limiting.

Dependency-free: a per-client fixed-window counter guarded by a lock. Limits are enforced
per *worker process* (state is in memory), which is sufficient at hackathon scale. Swap in a
Redis-backed limiter if you later need exact cluster-wide accuracy.
"""
from __future__ import annotations

import threading
import time
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

def _client_identity(request: Request) -> str:
    """Identify the caller: bearer token if present (per-credential), else the originating IP
    (first X-Forwarded-For hop behind Render's proxy, falling back to the socket peer)."""
    auth = request.headers.get("authorization")
    if auth:
        return f"tok:{auth.strip()}"
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return f"ip:{fwd.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter: at most `limit` requests per `window_seconds` per client.

    A request beyond the limit short-circuits with HTTP 429 (plus a Retry-After header) before it
    reaches any route handler or the database. Exempt paths (e.g. health checks) are never
    limited. The in-memory map is pruned of expired windows so it can't grow without bound.
    """

    def __init__(
        self,
        app,
        *,
        limit: int,
        window_seconds: int,
        exempt_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        self._limit = max(1, int(limit))
        self._window = max(1, int(window_seconds))
        self._exempt = set(exempt_paths)
        self._lock = threading.Lock()
        self._hits: dict[str, tuple[float, int]] = {}

    def _prune(self, now: float) -> None:
        # Opportunistic cleanup so the map can't grow unbounded under many distinct clients.
        if len(self._hits) < 10000:
            return
        stale = [k for k, (ws, _) in self._hits.items() if now - ws >= self._window]
        for k in stale:
            self._hits.pop(k, None)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt:
            return await call_next(request)
        key = _client_identity(request)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            window_start, count = self._hits.get(key, (now, 0))
            if now - window_start >= self._window:
                window_start, count = now, 0
            count += 1
            self._hits[key] = (window_start, count)
            over_limit = count > self._limit
            retry_after = max(1, int(self._window - (now - window_start)))
        if over_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "rate limit exceeded",
                    "limit": self._limit,
                    "window_seconds": self._window,
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
