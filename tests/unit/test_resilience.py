"""P011 — Native asyncio resilience primitives unit tests.

Kapsam:
- with_timeout pass / fail
- with_retry success / exhaust / retry_on filtering
- _backoff_delay full-jitter range
- call_resilient combined timeout+retry
"""

from __future__ import annotations

import asyncio

import pytest

from api.utils.resilience import (
    ResilienceRetryError,
    ResilienceTimeoutError,
    _backoff_delay,
    call_resilient,
    with_retry,
    with_timeout,
)

pytestmark = pytest.mark.unit


# ---------- with_timeout ----------


@pytest.mark.asyncio
async def test_with_timeout_returns_value_under_limit() -> None:
    async def quick() -> int:
        await asyncio.sleep(0.01)
        return 42

    result = await with_timeout(quick(), timeout=0.5)
    assert result == 42


@pytest.mark.asyncio
async def test_with_timeout_raises_resilience_timeout() -> None:
    async def slow() -> int:
        await asyncio.sleep(1.0)
        return 0

    with pytest.raises(ResilienceTimeoutError):
        await with_timeout(slow(), timeout=0.05)


# ---------- with_retry ----------


@pytest.mark.asyncio
async def test_with_retry_succeeds_first_attempt() -> None:
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        return "ok"

    result = await with_retry(fn, attempts=3, base_delay=0.0, max_delay=0.0)
    assert result == "ok"
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_recovers_after_transient_failures() -> None:
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = await with_retry(
        fn, attempts=3, base_delay=0.0, max_delay=0.0, jitter=False
    )
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_with_retry_raises_after_exhaustion() -> None:
    async def fn() -> str:
        raise ConnectionError("permanent")

    with pytest.raises(ResilienceRetryError) as exc_info:
        await with_retry(
            fn, attempts=3, base_delay=0.0, max_delay=0.0, jitter=False
        )
    assert isinstance(exc_info.value.__cause__, ConnectionError)


@pytest.mark.asyncio
async def test_with_retry_propagates_non_matching_exception_immediately() -> None:
    """retry_on dışı hata anında raise — retry yok."""
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        await with_retry(
            fn,
            attempts=5,
            base_delay=0.0,
            max_delay=0.0,
            retry_on=(ConnectionError,),
        )
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_invalid_attempts_raises() -> None:
    async def fn() -> str:
        return "x"

    with pytest.raises(ValueError, match="attempts"):
        await with_retry(fn, attempts=0, base_delay=0.0, max_delay=0.0)


# ---------- _backoff_delay ----------


def test_backoff_delay_no_jitter_is_deterministic() -> None:
    assert _backoff_delay(0, base=0.2, cap=5.0, jitter=False) == 0.2
    assert _backoff_delay(1, base=0.2, cap=5.0, jitter=False) == 0.4
    assert _backoff_delay(2, base=0.2, cap=5.0, jitter=False) == 0.8


def test_backoff_delay_caps_at_max() -> None:
    assert _backoff_delay(10, base=0.2, cap=5.0, jitter=False) == 5.0


def test_backoff_delay_full_jitter_within_50_to_100_pct() -> None:
    raw = 0.2 * (2 ** 2)  # 0.8
    for _ in range(50):
        d = _backoff_delay(2, base=0.2, cap=5.0, jitter=True)
        assert 0.5 * raw <= d <= raw


# ---------- call_resilient ----------


@pytest.mark.asyncio
async def test_call_resilient_combined_timeout_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """İlk deneme timeout, ikinci deneme başarılı → call_resilient sonucu döner."""
    monkeypatch.setenv("RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("RETRY_BASE_DELAY_SECONDS", "0.0")
    monkeypatch.setenv("RETRY_MAX_DELAY_SECONDS", "0.0")
    monkeypatch.setenv("RETRY_JITTER", "false")
    from api.config import get_settings

    get_settings.cache_clear()

    state = {"n": 0}

    async def fn() -> str:
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(1.0)
        return "ok"

    result = await call_resilient(
        fn,
        timeout=0.05,
        retry_on=(ResilienceTimeoutError,),
    )
    assert result == "ok"
    assert state["n"] == 2
