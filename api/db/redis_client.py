"""Redis client (sync + async) — 3-katlı cache namespaces.

DM-006: L1 Redis (90 gün) — MVP'de F-spec'lere göre kısaltıldı:
- q:    1h    (search results — DM-006'dan kısaltma F3a sözleşmesi)
- sum:  24h   (paper summaries — F3c)
- enrich: 7d  (ghost enrichment — F3d, OPEN-006 nihai onay sonrası ayar)
"""

import json
import logging
import time
from functools import lru_cache
from typing import Any, ClassVar

import redis
import redis.asyncio as aredis
import sentry_sdk

from api.config import get_settings

_logger = logging.getLogger(__name__)


# P3: cache_enabled state (CLAUDE.md §3.4 — sığınak yasak, sessiz spam yerine
# tek transition log + 5dk re-arm window).
_CACHE_DISABLED = False
_DISABLED_UNTIL: float = 0.0
_REARM_SECONDS = 300.0


def _breadcrumb_redis_failure(op: str, namespace: str, key: str, exc: Exception) -> None:
    """KVKK-aware Sentry breadcrumb for Redis failure (cache miss/set skip)."""
    sentry_sdk.add_breadcrumb(
        category="cache.redis",
        level="warning",
        message=f"Redis {op} failed",
        data={"namespace": namespace, "key_prefix": key[:8], "exc": type(exc).__name__},
    )


def _mark_disabled(exc: Exception, op: str, namespace: str, key: str) -> None:
    """P3: flag set + breadcrumb; warn yalnız transition'da (her request'te spam yok)."""
    global _CACHE_DISABLED, _DISABLED_UNTIL
    was_enabled = not _CACHE_DISABLED
    _CACHE_DISABLED = True
    _DISABLED_UNTIL = time.monotonic() + _REARM_SECONDS
    if was_enabled:
        _logger.warning(
            "Redis %s failed → cache disabled (%ds). Set REDIS_URL or run "
            "`brew services start redis` (%s)",
            op,
            int(_REARM_SECONDS),
            exc,
        )
    _breadcrumb_redis_failure(op, namespace, key, exc)


def _cache_disabled() -> bool:
    """True ise cache çağrısı no-op. Re-arm penceresi dolduysa False döner (yeniden dene)."""
    global _CACHE_DISABLED
    if not _CACHE_DISABLED:
        return False
    if time.monotonic() >= _DISABLED_UNTIL:
        _CACHE_DISABLED = False
        return False
    return True


def cache_health_probe() -> bool:
    """Startup ping; ulaşılmazsa flag set + tek warn. Lifespan'dan çağrılır."""
    try:
        client = get_redis_sync()
        client.ping()
    except redis.RedisError as exc:
        _mark_disabled(exc, "ping", "<startup>", "")
        return False
    return True


def _from_url_or_degrade(factory: Any, url: str) -> Any:
    """from_url'ü çağırır; boş/geçersiz REDIS_URL (ValueError) → ulaşılamaz Redis gibi
    davran (redis.ConnectionError). Böylece tüm `except redis.RedisError` degrade yolları
    bunu yakalar — boot ÇÖKMEZ. config_validation boş Redis'i 'uyarı, devam' sayar; bu
    sözleşmeyi from_url'ün ham ValueError'ı kırıyordu (boot-time crash). Global fix."""
    try:
        return factory(url, decode_responses=True)
    except ValueError as exc:
        raise redis.ConnectionError(f"invalid REDIS_URL: {exc}") from exc


@lru_cache
def get_redis_sync() -> redis.Redis:
    """Sync Redis (Celery worker + cache helpers)."""
    settings = get_settings()
    client: redis.Redis = _from_url_or_degrade(redis.Redis.from_url, settings.REDIS_URL)
    return client


@lru_cache
def get_redis_async() -> aredis.Redis:
    """Async Redis (FastAPI request path)."""
    settings = get_settings()
    client: aredis.Redis = _from_url_or_degrade(aredis.Redis.from_url, settings.REDIS_URL)
    return client


class CacheNamespace:
    """3-katlı Redis cache namespaces + default TTL'ler (DM-006 + F3a/c/d sözleşmeleri)."""

    QUERY = "q"
    SUMMARY = "sum"
    ENRICH = "enrich"

    TTL_SECONDS: ClassVar[dict[str, int]] = {
        QUERY: 3_600,
        SUMMARY: 86_400,
        ENRICH: 604_800,
    }


def cache_get(namespace: str, key: str) -> Any | None:
    """Sync cache get; Redis unreachable ise no-op (tek transition warn + breadcrumb) — graceful degrade.

    P3 (CLAUDE.md §3.4): sığınak yasak. Önceki sürüm her isteğe iki satır
    "Connection refused" logu üretiyordu; bu sürüm _cache_disabled() flag ile
    sessizleştirir, ilk düşüşte bir kere warn yazar, 5 dk re-arm penceresi sonra
    yeniden dener.
    """
    if _cache_disabled():
        return None
    try:
        client = get_redis_sync()
        raw: Any = client.get(f"{namespace}:{key}")
    except redis.RedisError as exc:
        _mark_disabled(exc, "get", namespace, key)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw


def cache_set(namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
    """Sync cache set; Redis unreachable ise sessizce skip (P3 transition warn) — graceful degrade."""
    if _cache_disabled():
        return
    payload = json.dumps(value) if not isinstance(value, str) else value
    effective_ttl = ttl if ttl is not None else CacheNamespace.TTL_SECONDS.get(namespace, 3_600)
    try:
        client = get_redis_sync()
        client.setex(f"{namespace}:{key}", effective_ttl, payload)
    except redis.RedisError as exc:
        _mark_disabled(exc, "set", namespace, key)
