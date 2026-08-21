"""F13-S14 unit tests — cron job smoke + behavior coverage.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14

Cron job'ları minimal mock'larla doğrular:
  * `_common.py` helper'ları
  * Her job'un main() return code'u (success path)
  * Job-specific davranış (dry-run, staleness, empty)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.cron import _common

pytestmark = pytest.mark.unit


# ── _common helpers ─────────────────────────────────────────────────────────


def test_bootstrap_repo_path_idempotent() -> None:
    _common.bootstrap_repo_path()
    n_before = sum(1 for p in sys.path if p == str(_common.REPO_ROOT))
    _common.bootstrap_repo_path()
    n_after = sum(1 for p in sys.path if p == str(_common.REPO_ROOT))
    assert n_before == n_after
    assert n_after >= 1


def test_cron_logger_single_handler() -> None:
    log1 = _common.cron_logger("test_job_x")
    log2 = _common.cron_logger("test_job_x")
    assert log1 is log2
    assert len(log1.handlers) == 1
    assert log1.level == logging.INFO
    assert log1.propagate is False


def test_build_cron_arg_parser_has_dry_run() -> None:
    parser = _common.build_cron_arg_parser("test_job_y")
    assert isinstance(parser, argparse.ArgumentParser)
    ns = parser.parse_args([])
    assert ns.dry_run is False
    ns2 = parser.parse_args(["--dry-run"])
    assert ns2.dry_run is True


# ── completion_delete_expired ───────────────────────────────────────────────


class _FakeQuery:
    """Supabase table().select().lt().execute() zincirini taklit."""

    def __init__(self, data: list[dict[str, Any]], count: int | None = None) -> None:
        self._data = data
        self._count = count

    def select(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def delete(self) -> _FakeQuery:
        return self

    def lt(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def gte(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def is_(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def order(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def limit(self, *_a: Any, **_kw: Any) -> _FakeQuery:
        return self

    def execute(self) -> Any:
        return SimpleNamespace(data=self._data, count=self._count)


class _FakeClient:
    def __init__(
        self, data: list[dict[str, Any]], count: int | None = None
    ) -> None:
        self._data = data
        self._count = count

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self._data, self._count)


def test_completion_delete_expired_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.cron import completion_delete_expired as job

    client = _FakeClient([{"id": "a"}, {"id": "b"}], count=2)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["completion_delete_expired", "--dry-run"])
    rc = job.main()
    assert rc == 0


def test_completion_delete_expired_delete_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.cron import completion_delete_expired as job

    client = _FakeClient([{"id": "a"}], count=1)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["completion_delete_expired"])
    rc = job.main()
    assert rc == 0


def test_completion_delete_expired_count_fallback() -> None:
    from scripts.cron import completion_delete_expired as job

    client = _FakeClient([{"id": "x"}, {"id": "y"}, {"id": "z"}], count=None)
    n = job._count_expired(client)
    assert n == 3


# ── health_heartbeat ────────────────────────────────────────────────────────


def test_health_heartbeat_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import health_heartbeat as job

    captured: dict[str, Any] = {}

    def _fake_get(url: str, timeout: float) -> Any:
        captured["url"] = url
        captured["timeout"] = timeout
        return SimpleNamespace(
            status_code=200,
            text='{"status":"ok"}',
            json=lambda: {"status": "ok", "version": "0.1.0", "env": "production"},
        )

    monkeypatch.setattr(job.httpx, "get", _fake_get)
    monkeypatch.setenv("PAPERMIND_API_BASE", "https://example.test/")
    monkeypatch.setattr(sys, "argv", ["health_heartbeat"])
    rc = job.main()
    assert rc == 0
    assert captured["url"] == "https://example.test/healthz"
    assert captured["timeout"] == job._TIMEOUT


def test_health_heartbeat_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import health_heartbeat as job

    def _fake_get(url: str, timeout: float) -> Any:
        return SimpleNamespace(status_code=503, text="upstream down", json=lambda: {})

    monkeypatch.setattr(job.httpx, "get", _fake_get)
    monkeypatch.delenv("PAPERMIND_API_BASE", raising=False)
    monkeypatch.setattr(sys, "argv", ["health_heartbeat"])
    rc = job.main()
    assert rc == 1


def test_health_heartbeat_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import health_heartbeat as job

    def _fake_get(url: str, timeout: float) -> Any:
        raise job.httpx.ConnectError("dns fail")

    monkeypatch.setattr(job.httpx, "get", _fake_get)
    monkeypatch.setattr(sys, "argv", ["health_heartbeat"])
    rc = job.main()
    assert rc == 1


def test_health_heartbeat_non_json_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.cron import health_heartbeat as job

    def _fake_get(url: str, timeout: float) -> Any:
        def _raise_json() -> dict[str, Any]:
            raise ValueError("not json")

        return SimpleNamespace(status_code=200, text="<html/>", json=_raise_json)

    monkeypatch.setattr(job.httpx, "get", _fake_get)
    monkeypatch.setattr(sys, "argv", ["health_heartbeat"])
    rc = job.main()
    assert rc == 0


# ── method_centrality_refresh ───────────────────────────────────────────────


def test_method_centrality_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import method_centrality_refresh as job

    recent = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    client = _FakeClient([{"computed_at": recent}])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["method_centrality_refresh"])
    rc = job.main()
    assert rc == 0


def test_method_centrality_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import method_centrality_refresh as job

    old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    client = _FakeClient([{"computed_at": old}])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["method_centrality_refresh"])
    rc = job.main()
    assert rc == 0


def test_method_centrality_empty_table(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import method_centrality_refresh as job

    client = _FakeClient([])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["method_centrality_refresh"])
    rc = job.main()
    assert rc == 0


def test_method_centrality_freshness_check_pure() -> None:
    from scripts.cron import method_centrality_refresh as job

    recent = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    fresh, last = job._check_freshness(_FakeClient([{"computed_at": recent}]))
    assert fresh is True
    assert last == recent


# ── neighbor_bibcoupling_refresh ────────────────────────────────────────────


def test_neighbor_bibcoupling_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import neighbor_bibcoupling_refresh as job

    recent = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    client = _FakeClient([{"computed_at": recent}])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["neighbor_bibcoupling_refresh"])
    rc = job.main()
    assert rc == 0


def test_neighbor_bibcoupling_stale_threshold_21() -> None:
    from scripts.cron import neighbor_bibcoupling_refresh as job

    just_over = (datetime.now(UTC) - timedelta(days=22)).isoformat()
    fresh, _ = job._check_freshness(_FakeClient([{"computed_at": just_over}]))
    assert fresh is False


# ── diary_unresolved_weekly ─────────────────────────────────────────────────


def test_diary_unresolved_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import diary_unresolved_weekly as job

    client = _FakeClient([])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["diary_unresolved_weekly"])
    rc = job.main()
    assert rc == 0


def test_diary_unresolved_groups_by_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.cron import diary_unresolved_weekly as job

    rows = [
        {"user_id": "u1", "project_id": "p1", "page_slug": "2.1", "created_at": "x"},
        {"user_id": "u1", "project_id": "p1", "page_slug": "2.2", "created_at": "x"},
        {"user_id": "u2", "project_id": "p2", "page_slug": "3.1", "created_at": "x"},
    ]
    client = _FakeClient(rows)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["diary_unresolved_weekly"])
    rc = job.main()
    assert rc == 0


# ── diary_monthly_digest ────────────────────────────────────────────────────


def test_diary_monthly_digest_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.cron import diary_monthly_digest as job

    client = _FakeClient([])
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["diary_monthly_digest"])
    rc = job.main()
    assert rc == 0


def test_diary_monthly_digest_distinct_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.cron import diary_monthly_digest as job

    rows = [
        {"user_id": "u1", "project_id": "p", "page_slug": "2.1", "created_at": "x"},
        {"user_id": "u1", "project_id": "p", "page_slug": "2.1", "created_at": "x"},
        {"user_id": "u1", "project_id": "p", "page_slug": "3.4", "created_at": "x"},
        {"user_id": "u2", "project_id": "p", "page_slug": "S1", "created_at": "x"},
    ]
    client = _FakeClient(rows)
    import api.db.supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_supabase_admin", lambda: client)
    monkeypatch.setattr(sys, "argv", ["diary_monthly_digest"])
    rc = job.main()
    assert rc == 0
