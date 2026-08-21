"""Plan: docs/plans/VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17.md §4.3.

Coverage: create_and_dispatch'in parent_job_id BOLA kontrolü (sahiplik
doğrulaması insert'ten ÖNCE), get_parent_job_id, list_user_jobs.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_and_dispatch_rejects_parent_job_not_owned(monkeypatch):
    from api.services import review_service as svc

    parent_id = uuid4()

    async def _fetch(job_id):
        assert job_id == parent_id
        return {"job_id": str(parent_id), "user_id": "other-user"}

    async def _insert(*a, **k):
        raise AssertionError("BOLA ihlali: sahiplik reddedilmeden insert çağrıldı")

    monkeypatch.setattr(svc, "_fetch_job", _fetch)
    monkeypatch.setattr(svc, "_insert_job", _insert)

    with pytest.raises(LookupError):
        await svc.create_and_dispatch(
            user_id="u1", mode="author", language="tr",
            data=b"x", kind="pdf", filename="f.pdf",
            parent_job_id=parent_id,
        )


async def test_create_and_dispatch_rejects_parent_job_not_found(monkeypatch):
    from api.services import review_service as svc

    async def _fetch(job_id):
        return None

    monkeypatch.setattr(svc, "_fetch_job", _fetch)

    with pytest.raises(LookupError):
        await svc.create_and_dispatch(
            user_id="u1", mode="author", language="tr",
            data=b"x", kind="pdf", filename="f.pdf",
            parent_job_id=uuid4(),
        )


async def test_create_and_dispatch_accepts_owned_parent_job(monkeypatch):
    from api.services import review_service as svc

    parent_id = uuid4()
    new_id = uuid4()

    async def _fetch(job_id):
        return {"job_id": str(parent_id), "user_id": "u1"}

    async def _find(user_id, key):
        return None

    seen = {}

    async def _insert(*a, **k):
        seen["args"] = a
        return new_id

    monkeypatch.setattr(svc, "_fetch_job", _fetch)
    monkeypatch.setattr(svc, "_find_by_idempotency_key", _find)
    monkeypatch.setattr(svc, "_insert_job", _insert)

    job_id, is_new = await svc.create_and_dispatch(
        user_id="u1", mode="author", language="tr",
        data=b"x", kind="pdf", filename="f.pdf",
        idempotency_key="k1", parent_job_id=parent_id,
    )
    assert job_id == new_id
    assert is_new is True
    assert seen["args"][-1] == parent_id  # parent_job_id _insert_job'a iletildi


async def test_get_parent_job_id_none_when_not_set(monkeypatch):
    from api.services import review_service as svc

    job_id = uuid4()

    async def _fetch(jid):
        return {"job_id": str(job_id), "user_id": "u1", "parent_job_id": None}

    monkeypatch.setattr(svc, "_fetch_job", _fetch)

    result = await svc.get_parent_job_id("u1", job_id)
    assert result is None


async def test_get_parent_job_id_returns_uuid_when_set(monkeypatch):
    from api.services import review_service as svc

    job_id = uuid4()
    parent_id = uuid4()

    async def _fetch(jid):
        return {"job_id": str(job_id), "user_id": "u1", "parent_job_id": str(parent_id)}

    monkeypatch.setattr(svc, "_fetch_job", _fetch)

    result = await svc.get_parent_job_id("u1", job_id)
    assert result == parent_id


async def test_get_parent_job_id_bola_not_owned_raises(monkeypatch):
    from api.services import review_service as svc

    job_id = uuid4()

    async def _fetch(jid):
        return {"job_id": str(job_id), "user_id": "other-user", "parent_job_id": None}

    monkeypatch.setattr(svc, "_fetch_job", _fetch)

    with pytest.raises(LookupError):
        await svc.get_parent_job_id("u1", job_id)
