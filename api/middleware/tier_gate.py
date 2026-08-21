"""V1 Tier Gate — FastAPI dependency: tier tespit + günlük kota + erişim kontrolü.

kaynak: db/migrations/0012_user_profile_fields_and_tier_refactor.sql §3 ENUM
        + docs/plans/V1_S5_backend_tier_canon.md §1
HK-2: Kotalar yorumda kaynaklı.
HK-4: Tier StrEnum + kota tablosu sabit.

Akış (per request):
  1) tier_for_request(request) → anon/ogrenci (user_id var mı?)
  2) check_path_access(path, tier) → tier yetersizse 403 tier_locked_soon
  3) enforce_quota(user_id_or_ip, path, tier) → Redis INCR + günlük TTL; aşılırsa 429

Redis key formatı: q:v1:<path-key>:<user_id|ip>:<YYYY-MM-DD>
TTL: gün sonuna kadar (UTC).
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from api.config import get_settings

logger = logging.getLogger(__name__)


class Tier(StrEnum):
    # kaynak: db/migrations/0012_user_profile_fields_and_tier_refactor.sql ENUM
    # ANON DB'de yok (sadece in-memory); OGRENCI default authed tier.
    ANON = "anon"
    OGRENCI = "ogrenci"
    ARASTIRMACI = "arastirmaci"
    PROFESYONEL = "profesyonel"


# V1 scope'unda 3 authed tier aynı kotada; ayrıştırma V2 iş kararı (KD-V1-S5-03).
AUTHED_TIERS: tuple[Tier, ...] = (
    Tier.OGRENCI,
    Tier.ARASTIRMACI,
    Tier.PROFESYONEL,
)


def _authed_quota(limit: int | None) -> dict[Tier, int | None]:
    """3 authed tier için aynı limit'i döner (V1 scope)."""
    return dict.fromkeys(AUTHED_TIERS, limit)


# Path → kota tablosu. -1 = sınırsız. None = tier'da erişim yok.
# kaynak: docs/plans/V1_S5_backend_tier_canon.md §1
QUOTA: dict[str, dict[Tier, int | None]] = {
    "/api/q":  {Tier.ANON: 3, **_authed_quota(5)},
    "/api/q/literature-review": {Tier.ANON: 3, **_authed_quota(10)},
    # V1-S12 ElevenLabs TTS (KD-V1-S12-03 cost cap):
    # ~$0.07/özet — anon=1/gün ($0.07), authed=5/gün ($0.35) worst-case.
    # Replay frontend blob cache'inden — quota = yeni audio generate.
    "/api/tts/literature-review": {Tier.ANON: 1, **_authed_quota(5)},
}

# Tier ne olursa olsun "yakında" döndürülen path'ler (DM-054).
LOCKED_SOON_PATHS: frozenset[str] = frozenset({"/api/q2"})

# M-14 — atölye (workshop) endpoint'leri "Pro" tier amaçlı tasarlandı; KD-V1-S5-01
# gereği V1'de tüm authed kullanıcılar OGRENCI sayıldığı için sert "Pro required"
# uygulanmıyor. Bunun yerine prefix-quota ile (a) anon kesin reddedilir, (b) authed
# kullanıcılara günlük makul tavan uygulanır, (c) V2 hardening tek satır değişir.
# Audit referansı: AUDIT_REPORT.md §11 M-14 / POL-COST-1.
WORKSHOP_PREFIX: str = "/api/workshop"
WORKSHOP_PREFIX_QUOTA: dict[Tier, int | None] = {
    Tier.ANON: None,       # 401 (auth_required_for_tier)
    Tier.OGRENCI: 50,
    Tier.ARASTIRMACI: 100,
    Tier.PROFESYONEL: -1,  # sınırsız
}


_redis_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis | None:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if settings.REDIS_URL:
            with contextlib.suppress(Exception):
                _redis_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1,
                )
    return _redis_client


def _today_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _seconds_to_midnight_utc() -> int:
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds())


def _client_id(request: Request) -> str:
    """Authed → user_id; anonim → IP."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"u:{user_id}"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _tier_for_request(request: Request) -> Tier:
    """user_id var → OGRENCI (default authed); yok → ANON.

    KD-V1-S5-01: V1'de DB'den profil fetch YOK; tüm authed kullanıcılar
    OGRENCI olarak ele alınır. V2'de gerçek tier `auth.users.tier` ile.
    """
    return (
        Tier.OGRENCI
        if getattr(request.state, "user_id", None)
        else Tier.ANON
    )


def _quota_backend_unavailable(reason: str) -> int:
    """Redis yokken kota davranışı (SEC-1 / P01-T04).

    Production: FAIL-CLOSED → 503 (pahalı uçlar kontrolsüz çağrılamaz; cost/abuse
    kapısı sessizce açılmaz). Dev/staging: permissive (return 1) → yerel geliştirme
    Redis'siz çalışsın. observability: her iki durumda da warn loglanır (yutma yok)."""
    if get_settings().APP_ENV == "production":
        logger.warning("tier_gate: redis unavailable in production (%s) → fail-closed 503", reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "quota_backend_unavailable",
                "retryable": True,
            },
            headers={"Retry-After": "30"},
        )
    logger.warning("tier_gate: redis unavailable (%s), quota check skipped (non-prod)", reason)
    return 1


async def _incr_and_get_quota(
    key: str, ttl_seconds: int
) -> int:
    """Redis INCR + EXPIRE; sayacı döndürür. Redis yoksa prod'da fail-closed,
    dev'de permissive (bkz _quota_backend_unavailable)."""
    redis = _get_redis()
    if redis is None:
        return _quota_backend_unavailable("client_none")
    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        results = await pipe.execute()
        count: int = results[0]
        return count
    except Exception as exc:
        return _quota_backend_unavailable(f"redis_error:{type(exc).__name__}")


async def tier_gate(request: Request) -> dict[str, str | int]:
    """FastAPI Depends: tier tespit + erişim + kota.

    Returns: {"tier": "anon"|"ogrenci"|..., "quota_remaining": int, "quota_reset": ISO}
    Raises: HTTPException 401 / 403 / 429
    """
    path = request.url.path
    tier = _tier_for_request(request)

    # 1) Locked-soon path'ler: tier ne olursa olsun "yakında"
    if path in LOCKED_SOON_PATHS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "tier_locked_soon", "soon": True},
        )

    # 2) Path bilinmiyorsa: önce workshop prefix-quota'sına bak; o da değilse geç.
    if path not in QUOTA:
        if path.startswith(WORKSHOP_PREFIX):
            path_quota = WORKSHOP_PREFIX_QUOTA
        else:
            return {"tier": tier.value, "quota_remaining": -1, "quota_reset": ""}
    else:
        path_quota = QUOTA[path]

    # 3) Tier'ın bu path'e erişimi var mı?
    limit = path_quota.get(tier)
    if limit is None:
        # Q1 anon örneği: auth iste
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required_for_tier", "min_tier": "ogrenci"},
        )

    if limit == -1:  # sınırsız — V2 iş kararı, V1'de kullanılmaz
        return {
            "tier": tier.value,
            "quota_remaining": -1,
            "quota_reset": "",
        }

    # 4) Günlük kota sayacı
    today = _today_utc()
    client = _client_id(request)
    path_key = path.lstrip("/").replace("/", ":")
    redis_key = f"q:v1:{path_key}:{client}:{today}"
    ttl = _seconds_to_midnight_utc()

    count = await _incr_and_get_quota(redis_key, ttl)

    if count > limit:
        reset_iso = (
            datetime.now(UTC) + timedelta(seconds=ttl)
        ).replace(microsecond=0).isoformat()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "next_reset": reset_iso,
                "soon": True,
                "limit": limit,
                "tier": tier.value,
            },
            headers={"Retry-After": str(ttl)},
        )

    remaining = max(0, limit - count)
    reset_iso = (
        datetime.now(UTC) + timedelta(seconds=ttl)
    ).replace(microsecond=0).isoformat()
    return {
        "tier": tier.value,
        "quota_remaining": remaining,
        "quota_reset": reset_iso,
    }


__all__ = ["AUTHED_TIERS", "LOCKED_SOON_PATHS", "QUOTA", "Tier", "tier_gate"]
