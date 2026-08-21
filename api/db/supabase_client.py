"""Supabase client singletons + async resilience helpers.

P002: get_supabase_admin/anon singletons (RLS bypass vs RLS-enforced).
P012 (2026-05-01): postgrest_client_timeout from settings (default 120s → 10s);
                   `supabase_call_async()` async helper (to_thread + with_timeout
                   + SupabaseQueryError zarfı). Read-only çağrılarda retry için
                   `call_resilient` opsiyonel — write/RPC default off (idempotency
                   tartışmalı).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import lru_cache

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from api.config import get_settings
from api.utils.resilience import ResilienceTimeoutError, with_timeout

logger = logging.getLogger(__name__)


class SupabaseQueryError(Exception):
    """Supabase query başarısızlık zarfı (transport/runtime hatası __cause__)."""


def _client_options(timeout: float) -> SyncClientOptions:
    """SyncClientOptions: postgrest timeout + saglikli default'lar."""
    return SyncClientOptions(postgrest_client_timeout=int(timeout))


@lru_cache
def get_supabase_admin() -> Client:
    """Service-role client. RLS BYPASS — sadece backend'te kullan."""
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
        options=_client_options(settings.SUPABASE_TIMEOUT_SECONDS),
    )


@lru_cache
def get_review_supabase_admin() -> Client:
    """F14 hakemlik review_job için izole Supabase (Clarus, B-F14-09).

    REVIEW_SUPABASE_* set ise oraya bağlanır (ayrı proje, izole tablo); set değilse
    default SUPABASE_* (dev/test). Service-role — RLS bypass; sahiplik app-katmanında
    (review_service user_id kontrolü) doğrulanır.
    """
    settings = get_settings()
    url = settings.REVIEW_SUPABASE_URL or settings.SUPABASE_URL
    key = settings.REVIEW_SUPABASE_SECRET_KEY or settings.SUPABASE_SECRET_KEY
    if not url or not key:
        raise RuntimeError(
            "REVIEW_SUPABASE_* veya SUPABASE_* (URL+SECRET_KEY) set edilmeli"
        )
    return create_client(
        url, key, options=_client_options(settings.SUPABASE_TIMEOUT_SECONDS)
    )


@lru_cache
def get_supabase_anon() -> Client:
    """Publishable (anon) client. RLS-enforced — auth flows + public reads."""
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set")
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_PUBLISHABLE_KEY,
        options=_client_options(settings.SUPABASE_TIMEOUT_SECONDS),
    )


async def supabase_call_async[T](
    fn: Callable[[], T],
    *,
    timeout: float | None = None,  # noqa: ASYNC109
) -> T:
    """Sync Supabase çağrısını thread-offload + asyncio timeout ile sarmalar.

    `fn`: sıfır-argümanlı sync callable (örn `lambda: client.table('x').select('*').execute()`).
    Timeout aşılırsa ResilienceTimeoutError; transport/runtime hatası
    SupabaseQueryError olarak zarflanır (cause orijinal hata).
    """
    settings = get_settings()
    eff_timeout = timeout if timeout is not None else settings.SUPABASE_TIMEOUT_SECONDS

    coro = asyncio.to_thread(fn)
    try:
        return await with_timeout(coro, timeout=eff_timeout)
    except ResilienceTimeoutError:
        logger.warning("supabase call timeout=%.1fs", eff_timeout)
        raise
    except Exception as exc:
        logger.warning(
            "supabase call failed error=%s",
            exc.__class__.__name__,
        )
        raise SupabaseQueryError(
            f"supabase call failed: {exc.__class__.__name__}"
        ) from exc


__all__ = [
    "SupabaseQueryError",
    "get_review_supabase_admin",
    "get_supabase_admin",
    "get_supabase_anon",
    "supabase_call_async",
]
