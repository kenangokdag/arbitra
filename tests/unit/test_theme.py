"""Global app teması (FAZ 4A) — service + route testleri (mocked supabase).

Kapsam:
  - get-default-when-no-supabase / when-empty-row (ASLA çökme, kod-varsayılanı)
  - get reads existing row
  - admin set_theme upsert roundtrip (id=1, updated_by)
  - GET /api/app/theme PUBLIC (auth yok → 200)
  - PATCH non-admin → 403 · invalid hex → 422 · off-allowlist font → 422
  - PATCH admin upsert roundtrip → 200 + updated_by

Mock deseni: dim route testi ile aynı (FakeSupabase recorder + direct
supabase_call_async). Gerçek DB yok.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


# --- fake supabase recorder -------------------------------------------------


class _FakeBuilder:
    def __init__(self, fake: _FakeSupabase, table: str) -> None:
        self._fake = fake
        self._table = table
        self._op: str | None = None
        self._row: dict[str, Any] | None = None

    def select(self, *_a: Any, **_k: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def eq(self, _col: str, _val: Any) -> _FakeBuilder:
        return self

    def limit(self, _n: int) -> _FakeBuilder:
        return self

    def upsert(self, row: dict[str, Any]) -> _FakeBuilder:
        self._op = "upsert"
        self._row = row
        return self

    def execute(self) -> SimpleNamespace:
        self._fake.calls.append({"table": self._table, "op": self._op, "row": self._row})
        if self._op == "upsert" and self._row is not None:
            self._fake.rows = [dict(self._row)]
            return SimpleNamespace(data=[dict(self._row)])
        return SimpleNamespace(data=list(self._fake.rows))


class _FakeSupabase:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows: list[dict[str, Any]] = rows or []
        self.calls: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)


@pytest.fixture
def direct_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """supabase_call_async → senkron direct çağrı (thread/timeout bypass)."""

    async def _direct(fn: Any, *, timeout: float | None = None) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct)


def _bind_db(monkeypatch: pytest.MonkeyPatch, fake: _FakeSupabase | None) -> None:
    monkeypatch.setattr("api.services.theme_service._supabase", lambda: fake)


def _token(sub: str) -> str:
    return jwt.encode({"sub": sub}, "x", algorithm="HS256")


def _set_admin(monkeypatch: pytest.MonkeyPatch, ids: str) -> None:
    monkeypatch.setenv("ADMIN_USER_IDS", ids)
    from api.config import get_settings

    get_settings.cache_clear()


_VALID_BODY = {
    "accent_color": "#112233",
    "bg_color": "#ffffff",
    "ink_color": "#000000",
    "font_sans": "source-sans",
    "font_serif": "newsreader",
}

_DB_ROW = {
    "id": 1,
    "accent_color": "#abcdef",
    "bg_color": "#f8fafc",
    "ink_color": "#0f172a",
    "font_sans": "inter",
    "font_serif": "lora",
    "updated_by": "admin-7",
    "updated_at": "2026-06-26T10:00:00+00:00",
}


# --- service: get_theme -----------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_when_no_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.models.theme import default_theme
    from api.services import theme_service

    _bind_db(monkeypatch, None)  # Supabase yok (dev) → kod-varsayılanı
    theme = await theme_service.get_theme()
    assert theme.model_dump() == default_theme().model_dump()
    assert theme.accent_color == "#4F46E5"


@pytest.mark.asyncio
async def test_get_default_when_empty_row(
    monkeypatch: pytest.MonkeyPatch, direct_call: None
) -> None:
    from api.models.theme import default_theme
    from api.services import theme_service

    _bind_db(monkeypatch, _FakeSupabase(rows=[]))
    theme = await theme_service.get_theme()
    assert theme.model_dump() == default_theme().model_dump()


@pytest.mark.asyncio
async def test_get_reads_existing_row(
    monkeypatch: pytest.MonkeyPatch, direct_call: None
) -> None:
    from api.services import theme_service

    _bind_db(monkeypatch, _FakeSupabase(rows=[dict(_DB_ROW)]))
    theme = await theme_service.get_theme()
    assert theme.accent_color == "#abcdef"
    assert theme.font_sans == "inter"
    assert theme.updated_by == "admin-7"


# --- service: set_theme -----------------------------------------------------


@pytest.mark.asyncio
async def test_admin_set_theme_upsert_roundtrip(
    monkeypatch: pytest.MonkeyPatch, direct_call: None
) -> None:
    from api.models.theme import ThemeSettings
    from api.services import theme_service

    fake = _FakeSupabase()
    _bind_db(monkeypatch, fake)

    incoming = ThemeSettings(**_VALID_BODY)
    out = await theme_service.set_theme(incoming, "admin-1")

    # döndürülen tema güncel künyeyi taşır
    assert out.accent_color == "#112233"
    assert out.updated_by == "admin-1"
    assert out.updated_at is not None

    # tam bir upsert çağrısı; satır id=1 + updated_by yazıldı
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["op"] == "upsert"
    assert call["table"] == "app_theme_settings"
    assert call["row"]["id"] == 1
    assert call["row"]["updated_by"] == "admin-1"
    assert "updated_at" in call["row"]


# --- route: GET public ------------------------------------------------------


def test_get_theme_public_no_auth(client: TestClient) -> None:
    # Auth header YOK → 200 (PUBLIC). Test env'de Supabase yok → kod-varsayılanı.
    resp = client.get("/api/app/theme")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accent_color"] == "#4F46E5"
    assert body["font_sans"] == "inter"
    assert body["font_serif"] == "lora"


# --- route: PATCH admin gate ------------------------------------------------


def test_patch_theme_non_admin_403(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_admin(monkeypatch, "admin-1")  # allowlist set, requester farklı
    client.headers["Authorization"] = f"Bearer {_token('intruder')}"
    resp = client.patch("/api/app/theme", json=_VALID_BODY)
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "admin_only"


def test_patch_theme_invalid_hex_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_admin(monkeypatch, "admin-1")  # admin → 422 yalnız body'den gelir
    client.headers["Authorization"] = f"Bearer {_token('admin-1')}"
    bad = {**_VALID_BODY, "accent_color": "indigo"}  # hex değil
    resp = client.patch("/api/app/theme", json=bad)
    assert resp.status_code == 422, resp.text


def test_patch_theme_off_allowlist_font_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_admin(monkeypatch, "admin-1")
    client.headers["Authorization"] = f"Bearer {_token('admin-1')}"
    bad = {**_VALID_BODY, "font_sans": "comic-sans"}  # allowlist dışı
    resp = client.patch("/api/app/theme", json=bad)
    assert resp.status_code == 422, resp.text


def test_patch_theme_serif_in_sans_slot_rejected_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_admin(monkeypatch, "admin-1")
    client.headers["Authorization"] = f"Bearer {_token('admin-1')}"
    # 'lora' geçerli bir serif ama sans slotunda geçersiz (set ayrımı).
    bad = {**_VALID_BODY, "font_sans": "lora"}
    resp = client.patch("/api/app/theme", json=bad)
    assert resp.status_code == 422, resp.text


def test_patch_theme_admin_upsert_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, direct_call: None
) -> None:
    _set_admin(monkeypatch, "admin-1,admin-2")
    fake = _FakeSupabase()
    _bind_db(monkeypatch, fake)
    client.headers["Authorization"] = f"Bearer {_token('admin-2')}"

    resp = client.patch("/api/app/theme", json=_VALID_BODY)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accent_color"] == "#112233"
    assert body["font_serif"] == "newsreader"
    assert body["updated_by"] == "admin-2"

    assert fake.calls[0]["op"] == "upsert"
    assert fake.calls[0]["row"]["updated_by"] == "admin-2"
