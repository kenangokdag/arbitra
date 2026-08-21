"""BE-1 / P02-T02 — idempotency dedup + orphan-job dürüstlüğü.

İki dayanıklılık garantisi backend kanıtı:
  1. idempotency: aynı (user, key) ikinci submit → YENİ iş açılmaz, var olan
     döner, boru hattı re-dispatch edilmez (çift quota/LLM maliyeti yok).
  2. stale sweep: yarıda kalmış (restart kurbanı) iş failed("interrupted")
     olur → kullanıcı sonsuz dönen çark değil, dürüst terminal durum görür.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

# --- idempotency ------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_hit_returns_existing_no_insert(monkeypatch):
    from api.services import review_service as svc

    existing = uuid4()

    async def _found(user_id, key):
        return existing

    inserted = {"n": 0}

    async def _insert(*a, **k):
        inserted["n"] += 1
        return uuid4()

    monkeypatch.setattr(svc, "_find_by_idempotency_key", _found)
    monkeypatch.setattr(svc, "_insert_job", _insert)

    job_id, is_new = await svc.create_and_dispatch(
        user_id="u1", mode="author", language="tr",
        data=b"x", kind="pdf", filename="f.pdf", idempotency_key="k1",
    )
    assert job_id == existing
    assert is_new is False
    assert inserted["n"] == 0, "idempotent tekrar yeni iş açtı (çift maliyet!)"


@pytest.mark.asyncio
async def test_idempotent_miss_inserts_new(monkeypatch):
    from api.services import review_service as svc

    new_id = uuid4()

    async def _not_found(user_id, key):
        return None

    async def _insert(user_id, mode, language, filename, kind, privacy, key, parent_job_id=None):
        assert key == "k2"  # key insert'e iletildi
        return new_id

    monkeypatch.setattr(svc, "_find_by_idempotency_key", _not_found)
    monkeypatch.setattr(svc, "_insert_job", _insert)

    job_id, is_new = await svc.create_and_dispatch(
        user_id="u1", mode="author", language="tr",
        data=b"x", kind="pdf", filename="f.pdf", idempotency_key="k2",
    )
    assert job_id == new_id
    assert is_new is True


@pytest.mark.asyncio
async def test_idempotent_race_insert_conflict_returns_existing(monkeypatch):
    """TOCTOU: ön-kontrol boş, ama insert DB unique index'e çarpar → 500 DEĞİL,
    yarışı kazanan var olan iş dürüstçe döner."""
    from api.services import review_service as svc

    winner = uuid4()
    calls = {"find": 0}

    async def _find(user_id, key):
        calls["find"] += 1
        # 1. çağrı (ön-kontrol): yok. 2. çağrı (insert sonrası): yarış kazananı var.
        return None if calls["find"] == 1 else winner

    async def _insert_conflict(*a, **k):
        raise RuntimeError("duplicate key value violates unique constraint")

    monkeypatch.setattr(svc, "_find_by_idempotency_key", _find)
    monkeypatch.setattr(svc, "_insert_job", _insert_conflict)

    job_id, is_new = await svc.create_and_dispatch(
        user_id="u1", mode="author", language="tr",
        data=b"x", kind="pdf", filename="f.pdf", idempotency_key="k3",
    )
    assert job_id == winner
    assert is_new is False
    assert calls["find"] == 2  # ön-kontrol + yarış-çözümü


@pytest.mark.asyncio
async def test_insert_failure_without_race_reraises(monkeypatch):
    """Gerçek hata (yarış değil): insert sonrası hâlâ kayıt yok → hata YUTULMAZ."""
    from api.services import review_service as svc

    async def _find(user_id, key):
        return None  # hiç yarış yok

    async def _insert_boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(svc, "_find_by_idempotency_key", _find)
    monkeypatch.setattr(svc, "_insert_job", _insert_boom)

    with pytest.raises(RuntimeError, match="db down"):
        await svc.create_and_dispatch(
            user_id="u1", mode="author", language="tr",
            data=b"x", kind="pdf", filename="f.pdf", idempotency_key="k4",
        )


@pytest.mark.asyncio
async def test_no_key_skips_lookup_and_inserts(monkeypatch):
    from api.services import review_service as svc

    looked = {"n": 0}

    async def _find(user_id, key):
        looked["n"] += 1
        return None

    async def _insert(*a, **k):
        return uuid4()

    monkeypatch.setattr(svc, "_find_by_idempotency_key", _find)
    monkeypatch.setattr(svc, "_insert_job", _insert)

    _, is_new = await svc.create_and_dispatch(
        user_id="u1", mode="author", language="tr",
        data=b"x", kind="pdf", filename="f.pdf",  # idempotency_key yok
    )
    assert is_new is True
    assert looked["n"] == 0, "key yokken lookup yapılmamalı"


# --- stale sweep ------------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_marks_orphans_failed(monkeypatch):
    from api.services import review_service as svc

    monkeypatch.setattr(svc, "get_review_supabase_admin", lambda: object())

    orphan_a, orphan_b = uuid4(), uuid4()

    async def _fake_call(thunk, *a, **k):
        return SimpleNamespace(
            data=[{"job_id": str(orphan_a)}, {"job_id": str(orphan_b)}]
        )

    monkeypatch.setattr(svc, "supabase_call_async", _fake_call)

    failed: list[tuple[str, str]] = []

    async def _set_step(job_id, status, **extra):
        failed.append((str(job_id), status))
        assert extra.get("error", "").startswith("interrupted")

    monkeypatch.setattr(svc, "_set_step", _set_step)

    swept = await svc.mark_stale_jobs_failed(older_than_minutes=30)
    assert set(swept) == {str(orphan_a), str(orphan_b)}
    assert all(status == "failed" for _, status in failed)


@pytest.mark.asyncio
async def test_sweep_noop_when_none(monkeypatch):
    from api.services import review_service as svc

    monkeypatch.setattr(svc, "get_review_supabase_admin", lambda: object())

    async def _fake_call(thunk, *a, **k):
        return SimpleNamespace(data=[])

    monkeypatch.setattr(svc, "supabase_call_async", _fake_call)

    swept = await svc.mark_stale_jobs_failed()
    assert swept == []
