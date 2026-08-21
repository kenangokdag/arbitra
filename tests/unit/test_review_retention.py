"""F14 KVKK retention — review_job delete_after kanıtı.

İki uç doğrulanır:
  1. review_service._insert_job insert anında delete_after = now + retention_days
     yazar (custom privacy.retention_days VE privacy=None default 30). Migration
     0044 + UI sözü ("bu süre sonunda yüklenen dosya silinir") backend tarafı.
  2. review_retention_delete_expired cron _count_expired/_delete_expired
     delete_after < now() satırlarını sayar/siler (completion deseni aynası).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from api.models.review import PrivacyConfig

pytestmark = pytest.mark.unit


# --- _insert_job delete_after ----------------------------------------------


class _CapturingQuery:
    """db.table().insert(row).execute() zincirini taklit + row'u yakalar."""

    def __init__(self, captured: dict[str, Any], job_id: str) -> None:
        self._captured = captured
        self._job_id = job_id

    def insert(self, row: dict[str, Any]) -> _CapturingQuery:
        self._captured["row"] = row
        return self

    def execute(self) -> Any:
        return SimpleNamespace(data=[{"job_id": self._job_id}])


class _CapturingDB:
    def __init__(self, captured: dict[str, Any], job_id: str) -> None:
        self._q = _CapturingQuery(captured, job_id)

    def table(self, _name: str) -> _CapturingQuery:
        return self._q


async def _passthrough(fn: Any, *_a: Any, **_k: Any) -> Any:
    return fn()


def _assert_delta(iso_value: str, retention_days: int) -> None:
    parsed = datetime.fromisoformat(iso_value)
    assert parsed.tzinfo is not None, "delete_after tz-aware olmalı (UTC)"
    expected = datetime.now(UTC) + timedelta(days=retention_days)
    drift = abs((parsed - expected).total_seconds())
    assert drift < 120, f"delete_after {retention_days}g eşiğinden {drift:.0f}s kaymış"


@pytest.mark.asyncio
async def test_insert_job_sets_delete_after_custom_retention(monkeypatch):
    from api.services import review_service as svc

    captured: dict[str, Any] = {}
    job_id = str(uuid4())
    monkeypatch.setattr(
        svc, "get_review_supabase_admin", lambda: _CapturingDB(captured, job_id)
    )
    monkeypatch.setattr(svc, "supabase_call_async", _passthrough)

    out = await svc._insert_job(
        user_id="u1",
        mode="author",
        language="tr",
        source_name="f.pdf",
        source_kind="pdf",
        privacy=PrivacyConfig(retention_days=7),
    )
    assert str(out) == job_id
    row = captured["row"]
    assert "delete_after" in row, "delete_after insert row'unda yok (retention yok!)"
    _assert_delta(row["delete_after"], 7)


@pytest.mark.asyncio
async def test_insert_job_default_30_when_privacy_none(monkeypatch):
    from api.services import review_service as svc

    captured: dict[str, Any] = {}
    job_id = str(uuid4())
    monkeypatch.setattr(
        svc, "get_review_supabase_admin", lambda: _CapturingDB(captured, job_id)
    )
    monkeypatch.setattr(svc, "supabase_call_async", _passthrough)

    await svc._insert_job(
        user_id="u1",
        mode="author",
        language="tr",
        source_name="f.pdf",
        source_kind="pdf",
        privacy=None,
    )
    row = captured["row"]
    assert "delete_after" in row
    _assert_delta(row["delete_after"], 30)


# --- cron _count_expired / _delete_expired ----------------------------------
# Non-vacuous: fake RECORDS the .lt(column, value) call AND actually applies the
# predicate at .execute() (ISO string compare). Flipping lt→gt, renaming the
# column, or dropping the cutoff would change counts and FAIL these tests.

_PAST = (datetime.now(UTC) - timedelta(days=10)).isoformat()
_FUTURE = (datetime.now(UTC) + timedelta(days=10)).isoformat()
# 3-row fixture: 1 expired (past) · 1 not-yet (future) · 1 never-set (None).
_SEED: list[dict[str, Any]] = [
    {"job_id": "expired", "delete_after": _PAST},
    {"job_id": "future", "delete_after": _FUTURE},
    {"job_id": "no_threshold", "delete_after": None},
]


class _RecordingQuery:
    """Filtreyi KAYDEDER + execute()'da gerçekten uygular (ISO string compare)."""

    def __init__(
        self,
        rows: list[dict[str, Any]],
        recorder: dict[str, Any],
        *,
        force_count_none: bool,
    ) -> None:
        self._rows = rows
        self._recorder = recorder
        self._force_count_none = force_count_none
        self._is_count = False
        self._predicate: tuple[str, str] | None = None

    def select(self, *_a: Any, **_kw: Any) -> _RecordingQuery:
        self._is_count = True
        return self

    def delete(self) -> _RecordingQuery:
        return self

    def lt(self, column: str, value: str) -> _RecordingQuery:
        self._recorder["column"] = column
        self._recorder["value"] = value
        self._predicate = (column, value)
        return self

    def execute(self) -> Any:
        assert self._predicate is not None, "lt() çağrılmadan execute()"
        col, cutoff = self._predicate
        matched = [
            r for r in self._rows if r.get(col) is not None and r[col] < cutoff
        ]
        count = None if self._force_count_none else (len(matched) if self._is_count else None)
        return SimpleNamespace(data=matched, count=count)


class _RecordingClient:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        recorder: dict[str, Any],
        *,
        force_count_none: bool = False,
    ) -> None:
        self._rows = rows
        self._recorder = recorder
        self._force_count_none = force_count_none

    def table(self, _name: str) -> _RecordingQuery:
        return _RecordingQuery(
            self._rows, self._recorder, force_count_none=self._force_count_none
        )


def _assert_cutoff_recorded(recorder: dict[str, Any]) -> None:
    """lt() doğru kolon + now-civarı ISO cutoff ile çağrıldı (Fix A kanıtı)."""
    assert recorder["column"] == "delete_after", "yanlış kolon filtrelendi"
    parsed = datetime.fromisoformat(recorder["value"])
    drift = abs((parsed - datetime.now(UTC)).total_seconds())
    assert drift < 120, f"cutoff now'dan {drift:.0f}s sapmış (Python-hesaplı değil?)"


def test_count_expired_applies_cutoff_only_past() -> None:
    from scripts.cron import review_retention_delete_expired as job

    recorder: dict[str, Any] = {}
    client = _RecordingClient(_SEED, recorder)
    cutoff = datetime.now(UTC).isoformat()

    n = job._count_expired(client, cutoff)

    assert n == 1, "yalnız süresi geçmiş satır sayılmalı (future + None hariç)"
    assert recorder["column"] == "delete_after"
    assert recorder["value"] == cutoff


def test_delete_expired_applies_cutoff_only_past() -> None:
    from scripts.cron import review_retention_delete_expired as job

    recorder: dict[str, Any] = {}
    client = _RecordingClient(_SEED, recorder)
    cutoff = datetime.now(UTC).isoformat()

    deleted = job._delete_expired(client, cutoff)

    assert deleted == 1, "yalnız süresi geçmiş satır silinmeli (future + None hariç)"
    assert recorder["column"] == "delete_after"
    assert recorder["value"] == cutoff


def test_count_expired_falls_back_to_len_when_no_count() -> None:
    from scripts.cron import review_retention_delete_expired as job

    recorder: dict[str, Any] = {}
    # PG exact-count dönmezse (count=None) → len(data) fallback; yine yalnız expired.
    client = _RecordingClient(_SEED, recorder, force_count_none=True)
    n = job._count_expired(client, datetime.now(UTC).isoformat())
    assert n == 1


def test_cron_main_dry_run_computes_now_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    from scripts.cron import review_retention_delete_expired as job

    recorder: dict[str, Any] = {}
    client = _RecordingClient(_SEED, recorder)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_review_supabase_admin", lambda: client)
    monkeypatch.setattr(
        sys, "argv", ["review_retention_delete_expired", "--dry-run"]
    )
    assert job.main() == 0
    _assert_cutoff_recorded(recorder)


def test_cron_main_delete_computes_now_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    from scripts.cron import review_retention_delete_expired as job

    recorder: dict[str, Any] = {}
    client = _RecordingClient(_SEED, recorder)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_review_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["review_retention_delete_expired"])
    assert job.main() == 0
    _assert_cutoff_recorded(recorder)
