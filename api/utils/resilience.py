"""P011 — Native asyncio resilience primitives (no tenacity/pybreaker dep).

Council 39 K4 YELLOW: in-house timeout + retry+jitter; circuit breaker (P014)
KD-36 olarak F7 P065'e ertelendi (1-kişi MVP'de pilot trafiği yokken erken).

API:
- with_timeout(coro, timeout)        — asyncio.wait_for sarmalayıcı, ResilienceTimeoutError raise eder
- with_retry(fn, ...)                — exponential backoff + jitter, retry_on tip filtresi
- call_resilient(fn, ..., timeout=)  — timeout + retry birleşik

Thread-cancel notu: asyncio.wait_for arka plandaki to_thread iş parçacığını öldüremez
(Python thread cancel kooperatif değil), ancak event loop bloke olmaz; pratik olarak
dış servis hang'lerinde worker iş kabul etmeye devam eder.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ResilienceError(Exception):
    """Resilience wrapper base hata sınıfı."""


class ResilienceTimeoutError(ResilienceError):
    """with_timeout süresi aşıldığında."""


class ResilienceRetryError(ResilienceError):
    """with_retry tüm denemeler tükendiğinde — son hatayı __cause__'a koyar."""


async def with_timeout[T](
    awaitable: Awaitable[T],
    timeout: float,  # noqa: ASYNC109
) -> T:
    """Awaitable'i `timeout` saniye sınırla. Aşılırsa ResilienceTimeoutError."""
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout)
    except TimeoutError as exc:
        raise ResilienceTimeoutError(f"operation exceeded {timeout}s") from exc


def _backoff_delay(
    attempt: int,
    base: float,
    cap: float,
    jitter: bool,
) -> float:
    """Exponential backoff with optional 50%-100% jitter (full-jitter style)."""
    raw: float = min(cap, base * float(2 ** attempt))
    if jitter:
        raw *= 0.5 + random.random() * 0.5  # noqa: S311 (jitter, not security)
    return raw


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay: float,
    max_delay: float,
    jitter: bool = True,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """fn() coroutine factory'sini en fazla `attempts` kez çağır.

    İlk başarılı çağrıda döner; tüm denemeler `retry_on` ile uyumlu hata
    fırlatırsa ResilienceRetryError raise edilir (cause son hatadır).
    `retry_on` dışı bir hata fırlatılırsa ANINDA propagate olur (retry yok).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            delay = _backoff_delay(attempt, base_delay, max_delay, jitter)
            logger.warning(
                "retry attempt=%d/%d delay=%.2fs error=%s",
                attempt + 1,
                attempts,
                delay,
                exc.__class__.__name__,
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise ResilienceRetryError(
        f"all {attempts} attempts failed; last={last_exc.__class__.__name__}"
    ) from last_exc


async def call_resilient[T](
    fn: Callable[[], Awaitable[T]],
    *,
    timeout: float,  # noqa: ASYNC109
    settings: Settings | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """timeout + retry+jitter birleşik çağrı; her deneme `timeout` ile sınırlanır."""
    cfg = settings or get_settings()

    async def _attempt() -> T:
        return await with_timeout(fn(), timeout=timeout)

    return await with_retry(
        _attempt,
        attempts=cfg.RETRY_ATTEMPTS,
        base_delay=cfg.RETRY_BASE_DELAY_SECONDS,
        max_delay=cfg.RETRY_MAX_DELAY_SECONDS,
        jitter=cfg.RETRY_JITTER,
        retry_on=retry_on,
    )


__all__ = [
    "ResilienceError",
    "ResilienceRetryError",
    "ResilienceTimeoutError",
    "call_resilient",
    "with_retry",
    "with_timeout",
]
