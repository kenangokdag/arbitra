"""V1-S18-P014 pilot allowlist gate unit + integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest

from api.services.waitlist_gate import is_email_allowed

pytestmark = pytest.mark.unit


# ---------- Servis: is_email_allowed ----------


class _FakeBuilder:
    """Minimal supabase-py chain mock: .table(t).select(c).eq(c, v).limit(n).execute()."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def table(self, _name: str) -> "_FakeBuilder":  # pragma: no cover - chain
        return self

    def select(self, _cols: str) -> "_FakeBuilder":
        return self

    def eq(self, _col: str, _val: str) -> "_FakeBuilder":
        return self

    def limit(self, _n: int) -> "_FakeBuilder":
        return self

    def execute(self) -> Any:
        return MagicMock(data=self._rows)


def _fake_db(rows: list[dict[str, Any]]) -> Any:
    return _FakeBuilder(rows)


@pytest.mark.asyncio
async def test_is_email_allowed_invited_true() -> None:
    db = _fake_db([{"status": "invited"}])
    assert await is_email_allowed("a@b.com", db) is True


@pytest.mark.asyncio
async def test_is_email_allowed_active_true() -> None:
    db = _fake_db([{"status": "active"}])
    assert await is_email_allowed("a@b.com", db) is True


@pytest.mark.asyncio
async def test_is_email_allowed_pending_false() -> None:
    db = _fake_db([{"status": "pending"}])
    assert await is_email_allowed("a@b.com", db) is False


@pytest.mark.asyncio
async def test_is_email_allowed_declined_false() -> None:
    db = _fake_db([{"status": "declined"}])
    assert await is_email_allowed("a@b.com", db) is False


@pytest.mark.asyncio
async def test_is_email_allowed_no_row_false() -> None:
    db = _fake_db([])
    assert await is_email_allowed("nope@x.com", db) is False


@pytest.mark.asyncio
async def test_is_email_allowed_empty_email_false() -> None:
    db = _fake_db([{"status": "active"}])
    assert await is_email_allowed("", db) is False


@pytest.mark.asyncio
async def test_is_email_allowed_normalizes_case() -> None:
    captured: dict[str, str] = {}

    class _CaptureBuilder(_FakeBuilder):
        def eq(self, col: str, val: str) -> "_CaptureBuilder":  # type: ignore[override]
            captured[col] = val
            return self

    db = _CaptureBuilder([{"status": "active"}])
    await is_email_allowed("  USER@EXAMPLE.COM  ", db)
    assert captured["email"] == "user@example.com"


# ---------- Middleware integrasyonu: WAITLIST_BYPASS=false ----------


@pytest.fixture
def app_with_gate(monkeypatch: pytest.MonkeyPatch) -> Any:
    """WAITLIST_BYPASS=false + fake supabase admin enjekte edilmiş app."""
    monkeypatch.setenv("WAITLIST_BYPASS", "false")
    from api.config import get_settings

    get_settings.cache_clear()

    from api import middleware
    from api.middleware import auth as auth_module

    # get_supabase_admin'i FakeSupabase ile değiştir (lazy import middleware'de
    # yapıldığı için modül attribute'unu patch'liyoruz değil, supabase_client
    # modülünün attribute'unu patch'liyoruz).
    from api.db import supabase_client

    rows_box: dict[str, list[dict[str, Any]]] = {"rows": []}

    def _fake_admin() -> Any:
        return _FakeBuilder(rows_box["rows"])

    monkeypatch.setattr(supabase_client, "get_supabase_admin", _fake_admin)

    from api.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    return TestClient(app), rows_box


def _bearer(email: str) -> dict[str, str]:
    token = jwt.encode({"sub": "user-x", "email": email}, "x", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_gate_403_when_email_not_in_waitlist(app_with_gate: Any) -> None:
    client, rows_box = app_with_gate
    rows_box["rows"] = []
    resp = client.get("/api/anywhere", headers=_bearer("ghost@example.com"))
    assert resp.status_code == 403
    assert resp.json()["error"] == "not_invited"


def test_gate_403_when_email_status_pending(app_with_gate: Any) -> None:
    client, rows_box = app_with_gate
    rows_box["rows"] = [{"status": "pending"}]
    resp = client.get("/api/anywhere", headers=_bearer("pending@example.com"))
    assert resp.status_code == 403


def test_gate_passes_when_email_status_invited(app_with_gate: Any) -> None:
    client, rows_box = app_with_gate
    rows_box["rows"] = [{"status": "invited"}]
    resp = client.get("/api/anywhere", headers=_bearer("invited@example.com"))
    # Auth + gate passed; route 404 because /api/anywhere does not exist
    assert resp.status_code == 404


def test_gate_passes_when_email_status_active(app_with_gate: Any) -> None:
    client, rows_box = app_with_gate
    rows_box["rows"] = [{"status": "active"}]
    resp = client.get("/api/anywhere", headers=_bearer("active@example.com"))
    assert resp.status_code == 404
