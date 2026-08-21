"""V1-S15.pre A1-P002 — api/services/anchor_lock.py unit tests.

Coverage (Omer 2026-05-26 karar matrisi):
1. Ownership zırh: başka user → ProjectNotFoundError
2. Frozen stage '3.1' → FrozenStageError
3. Frozen stage '4.5' → FrozenStageError
4. İlk lock (current_stage='1.1'): UPSERT + projects.current_stage='2.2'
5. Idempotent re-lock (current_stage='2.2'): UPSERT, current_stage UPDATE YOK
6. Re-lock (current_stage='2.5'): UPSERT, current_stage UPDATE YOK
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from api.services import anchor_lock

pytestmark = pytest.mark.unit


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._payload: Any = None
        self._filters: dict[str, Any] = {}
        self._limit: int | None = None
        self._on_conflict: str | None = None

    def select(self, _cols: str = "*", **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def upsert(
        self, payload: Any, *, on_conflict: str | None = None
    ) -> _FakeBuilder:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload: Any) -> _FakeBuilder:
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = val
        return self

    def limit(self, n: int) -> _FakeBuilder:
        self._limit = n
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "payload": self._payload,
            "filters": dict(self._filters),
            "limit": self._limit,
            "on_conflict": self._on_conflict,
        }
        self._rec.calls.append(call)
        return self._rec.respond(call)


class _FakeSupabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.anchors: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        t, op, f = call["table"], call["op"], call["filters"]
        if t == "projects" and op == "select":
            rows = [
                p for p in self.projects
                if p["id"] == f.get("id") and p["user_id"] == f.get("user_id")
            ]
            return SimpleNamespace(data=rows)
        if t == "projects" and op == "update":
            for p in self.projects:
                if p["id"] == f.get("id"):
                    p.update(call["payload"])
            return SimpleNamespace(data=[])
        if t == "project_anchor" and op == "upsert":
            payload = call["payload"]
            pid = payload["project_id"]
            existing = next(
                (a for a in self.anchors if a["project_id"] == pid), None
            )
            if existing is None:
                self.anchors.append(dict(payload))
            else:
                existing.update(payload)
            return SimpleNamespace(data=[payload])
        return SimpleNamespace(data=[])


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase()

    async def _direct_call(
        fn: Any,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr(
        "api.db.supabase_client.supabase_call_async", _direct_call
    )
    yield fake


# ── 1. Ownership: başka user → ProjectNotFoundError ──────────────────────────


async def test_anchor_lock_ownership_missing(fake_db: _FakeSupabase) -> None:
    fake_db.projects = [{"id": "prj-1", "user_id": "user-A", "current_stage": "1.1"}]
    with pytest.raises(anchor_lock.ProjectNotFoundError):
        await anchor_lock.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            user_id="user-B",
            paper_id="W123",
        )
    assert fake_db.anchors == []


# ── 2-3. Frozen stage ────────────────────────────────────────────────────────


@pytest.mark.parametrize("frozen_stage", ["3.1", "4.5", "5.6"])
async def test_anchor_lock_frozen_stage(
    fake_db: _FakeSupabase, frozen_stage: str
) -> None:
    fake_db.projects = [
        {"id": "prj-1", "user_id": "user-1", "current_stage": frozen_stage}
    ]
    with pytest.raises(anchor_lock.FrozenStageError):
        await anchor_lock.run(
            db=fake_db,  # type: ignore[arg-type]
            project_id="prj-1",
            user_id="user-1",
            paper_id="W123",
        )
    assert fake_db.anchors == []
    assert fake_db.projects[0]["current_stage"] == frozen_stage


# ── 4. İlk lock 1.1 → 2.2 advance + UPSERT ──────────────────────────────────


async def test_anchor_lock_first_lock_advances_stage(
    fake_db: _FakeSupabase,
) -> None:
    fake_db.projects = [
        {"id": "prj-1", "user_id": "user-1", "current_stage": "1.1"}
    ]
    resp = await anchor_lock.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        paper_id="W123",
    )
    assert resp.anchor_paper_id == "W123"
    assert resp.cluster_status == "pending"
    assert resp.locked_at  # ISO-8601 string

    assert len(fake_db.anchors) == 1
    anchor = fake_db.anchors[0]
    assert anchor["project_id"] == "prj-1"
    assert anchor["anchor_paper_id"] == "W123"
    assert anchor["cluster_status"] == "pending"
    assert fake_db.projects[0]["current_stage"] == "2.2"


# ── 5. Idempotent re-lock 2.2: UPSERT, current_stage dokunulmaz ──────────────


async def test_anchor_lock_idempotent_relock_at_2_2(
    fake_db: _FakeSupabase,
) -> None:
    fake_db.projects = [
        {"id": "prj-1", "user_id": "user-1", "current_stage": "2.2"}
    ]
    fake_db.anchors = [
        {
            "project_id": "prj-1",
            "anchor_paper_id": "W_OLD",
            "locked_at": "2026-05-25T10:00:00+00:00",
            "cluster_status": "pending",
        }
    ]
    resp = await anchor_lock.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        paper_id="W_NEW",
    )
    assert resp.anchor_paper_id == "W_NEW"
    assert fake_db.anchors[0]["anchor_paper_id"] == "W_NEW"
    # current_stage geriye gitmedi/ileriye sıçramadı
    assert fake_db.projects[0]["current_stage"] == "2.2"
    # update tablo çağrısı projects'e gitmedi
    project_updates = [
        c for c in fake_db.calls if c["table"] == "projects" and c["op"] == "update"
    ]
    assert project_updates == []


# ── 6. Re-lock 2.5 (kavram ağı sayfası): UPSERT + stage dokunulmaz ──────────


async def test_anchor_lock_relock_at_2_5_keeps_stage(
    fake_db: _FakeSupabase,
) -> None:
    fake_db.projects = [
        {"id": "prj-1", "user_id": "user-1", "current_stage": "2.5"}
    ]
    fake_db.anchors = [
        {
            "project_id": "prj-1",
            "anchor_paper_id": "W_OLD",
            "locked_at": "2026-05-25T10:00:00+00:00",
            "cluster_status": "pending",
        }
    ]
    await anchor_lock.run(
        db=fake_db,  # type: ignore[arg-type]
        project_id="prj-1",
        user_id="user-1",
        paper_id="W_NEW",
    )
    assert fake_db.anchors[0]["anchor_paper_id"] == "W_NEW"
    assert fake_db.projects[0]["current_stage"] == "2.5"
