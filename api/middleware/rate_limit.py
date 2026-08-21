"""Tier-bazlı sliding window rate limit.

P001: in-memory dict fallback (Redis yok veya bağlantı hatası).
P002: Redis sorted-set sliding window — multi-worker safe, restart-safe.
      REDIS_URL env set edilince otomatik aktif.
"""

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import get_settings

_window: dict[str, list[float]] = defaultdict(list)
_redis_client: aioredis.Redis | None = None
_redis_disabled_until: float = 0.0
_REDIS_DISABLE_SECONDS: float = 300.0  # redis_client.py ile ayni desen (circuit breaker)
_BYPASS_PATHS: frozenset[str] = frozenset({"/healthz", "/docs", "/openapi.json", "/redoc"})


def _get_redis() -> aioredis.Redis | None:
    global _redis_client, _redis_disabled_until
    if time.time() < _redis_disabled_until:
        return None
    if _redis_client is None:
        settings = get_settings()
        if settings.REDIS_URL:
            try:
                _redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1,
                )
            except Exception:
                pass
    return _redis_client


async def _redis_check(client: aioredis.Redis, key: str, limit: int) -> tuple[bool, int]:
    """Returns (is_limited, retry_after_seconds)."""
    now = time.time()
    window_start = now - 60.0
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 61)
    results = await pipe.execute()
    count: int = results[2]
    if count > limit:
        oldest = await client.zrange(key, 0, 0, withscores=True)
        retry_after = int(60.0 - (now - oldest[0][1])) + 1 if oldest else 60
        return True, retry_after
    return False, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window: 60 req/dk Öğrenci tier (B42-049 §1). Redis-first, in-memory fallback."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        settings = get_settings()
        limit = settings.RATE_LIMIT_OGRENCI_PER_MIN
        user_id = getattr(request.state, "user_id", None) or self._client_ip(request)
        key = f"rl:{user_id}"

        redis = _get_redis()
        if redis is not None:
            try:
                limited, retry_after = await _redis_check(redis, key, limit)
                if limited:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                        headers={"Retry-After": str(retry_after)},
                    )
                return await call_next(request)
            except Exception:
                pass  # Redis unavailable → fall through to in-memory
                global _redis_disabled_until
                _redis_disabled_until = time.time() + _REDIS_DISABLE_SECONDS

        # In-memory fallback
        now = time.monotonic()
        window_start = now - 60.0
        _window[key] = [t for t in _window[key] if t > window_start]
        if len(_window[key]) >= limit:
            retry_after = int(60.0 - (now - _window[key][0])) + 1
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        _window[key].append(now)
        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
