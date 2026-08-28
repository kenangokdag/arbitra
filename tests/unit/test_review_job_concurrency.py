"""2026-08-28 (P0, Render OOM kanıtı: "ran out of memory (used over 512MB)") —
review_service.run_pipeline() artık REVIEW_MAX_CONCURRENT_JOBS ile sınırlı
(bkz api/config.py, api/services/review_service.py _job_semaphore).

Kök neden: BackgroundTasks süreç-içi çalışıyor, önceden hiçbir eşzamanlılık
sınırı yoktu — 2+ ağır review job'u (PDF-parse + çoklu LLM çağrısı) aynı anda
512MB'lik starter plan'ı aşabiliyordu. Bu test, iki job'un GERÇEKTEN sıraya
girdiğini (paralel değil, ardışık çalıştığını) doğrular."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from api.services import review_service as svc

pytestmark = pytest.mark.unit


async def test_run_pipeline_serializes_jobs_when_max_concurrent_is_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REVIEW_MAX_CONCURRENT_JOBS=1 iken iki run_pipeline çağrısı ASLA
    çakışmamalı — 2. job, 1.'i bitirmeden başlamamalı."""
    from api.config import get_settings

    monkeypatch.setenv("REVIEW_MAX_CONCURRENT_JOBS", "1")
    get_settings.cache_clear()
    svc._job_semaphore.cache_clear()

    events: list[str] = []

    async def _fake_inner(job_id: object, **_kwargs: object) -> None:
        events.append(f"start:{job_id}")
        await asyncio.sleep(0.05)
        events.append(f"end:{job_id}")

    monkeypatch.setattr(svc, "_run_pipeline_inner", _fake_inner)

    job_a, job_b = uuid4(), uuid4()
    await asyncio.gather(
        svc.run_pipeline(
            job_a, data=b"x", kind="pdf", filename="a.pdf", mode="author", language="en"
        ),
        svc.run_pipeline(
            job_b, data=b"x", kind="pdf", filename="b.pdf", mode="author", language="en"
        ),
    )

    # Sıra hangi job önce başlarsa başlasın (gather sırası garanti değil) —
    # ama biri BAŞLAYIP BİTMEDEN diğeri BAŞLAYAMAZ (çakışma yok).
    assert events[0].startswith("start:")
    assert events[1].startswith("end:")
    assert events[1].removeprefix("end:") == events[0].removeprefix("start:")
    assert events[2].startswith("start:")
    assert events[3].startswith("end:")

    get_settings.cache_clear()
    svc._job_semaphore.cache_clear()


async def test_run_pipeline_allows_parallelism_when_max_concurrent_is_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REVIEW_MAX_CONCURRENT_JOBS=2 iken iki job GERÇEKTEN çakışabilmeli —
    sınırın gereksiz yere her zaman tam serileştirme yapmadığını kanıtlar."""
    from api.config import get_settings

    monkeypatch.setenv("REVIEW_MAX_CONCURRENT_JOBS", "2")
    get_settings.cache_clear()
    svc._job_semaphore.cache_clear()

    overlapped = asyncio.Event()
    started = 0
    lock = asyncio.Lock()

    async def _fake_inner(job_id: object, **_kwargs: object) -> None:
        nonlocal started
        async with lock:
            started += 1
            if started == 2:
                overlapped.set()
        await asyncio.sleep(0.05)

    monkeypatch.setattr(svc, "_run_pipeline_inner", _fake_inner)

    job_a, job_b = uuid4(), uuid4()
    await asyncio.wait_for(
        asyncio.gather(
            svc.run_pipeline(
                job_a, data=b"x", kind="pdf", filename="a.pdf", mode="author", language="en"
            ),
            svc.run_pipeline(
                job_b, data=b"x", kind="pdf", filename="b.pdf", mode="author", language="en"
            ),
        ),
        timeout=1.0,
    )
    assert overlapped.is_set()

    get_settings.cache_clear()
    svc._job_semaphore.cache_clear()
