"""V1-S4 waitlist route integration tests.

kaynak: docs/plans/V1_S4_waitlist_capture.md §7 (5 senaryo → 4 aktif)

Kapsam:
  - Happy path: valid email + name → 200 + DB row
  - Duplicate email → 409 already_queued (Postgres UNIQUE simülasyonu)
  - Invalid email format → 422 (Pydantic EmailStr)
  - Honeypot doluysa → 200 OK (silent drop, DB'ye yazılmaz)

Not: Rate limit testi global RateLimitMiddleware kapsamında (60/min/IP);
     bu suite endpoint-spesifik mantığa odaklanır.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.db.supabase_client import SupabaseQueryError

pytestmark = pytest.mark.integration


# ───── Fake Supabase: in-memory waitlist store ─────


class _FakeWaitlistStore:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.emails: set[str] = set()


@pytest.fixture(autouse=True)
def _stub_supabase(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeWaitlistStore]:
    """`_supabase()` sentinel + supabase_call_async fake insert."""
    store = _FakeWaitlistStore()

    # _supabase() None döndürmemeli (insert path test edilmeli) →
    # sentinel object yeterli (db.table().insert().execute() çağrısı lambda içinde,
    # supabase_call_async fake'ledigimiz için lambda execute edilmez).
    monkeypatch.setattr(
        "api.routes.waitlist._supabase", lambda: object()
    )

    async def fake_call(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ARG001
        # Lambda body'si (db.table('waitlist').insert(payload).execute()) çağırmıyoruz;
        # bunun yerine kapanış üzerinden payload'a closure ile erişemediğimiz için
        # fn() çağrısı yerine doğrudan payload-aware logic test edemeyiz.
        # Çözüm: monkeypatch.setattr ile waitlist route içindeki _supabase ve
        # supabase_call_async birlikte sahte; payload'ı route içinde yakalayan
        # alternatif bir hook gerekir.
        # Pratik: route SupabaseQueryError fırlattığında 409 dönüyor — store'u
        # email-bazlı ayrı bir mock ile yönetiriz (aşağıda override).
        raise NotImplementedError("override per-test via monkeypatch")

    monkeypatch.setattr("api.routes.waitlist.supabase_call_async", fake_call)

    yield store


def _install_insert_handler(
    monkeypatch: pytest.MonkeyPatch, store: _FakeWaitlistStore
) -> None:
    """Insert akışı: payload'ı yakalayıp store'a yaz; UNIQUE çakışınca SupabaseQueryError."""
    # Route _supabase()'i bir client gibi kullanır (db.table('waitlist').insert(payload))
    # — lambda içinde execute edilir. Lambda'yı çağırmadan payload alamayız.
    # Çözüm: db sentinel yerine FakeClient döndür; lambda execute olunca payload yakalanır.

    class _FakeExec:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def execute(self) -> Any:
            email = self.payload["email"]
            if email in store.emails:
                raise RuntimeError("duplicate key value violates unique constraint")
            store.emails.add(email)
            store.rows.append(self.payload)
            return type("R", (), {"data": [self.payload]})()

    class _FakeTable:
        def insert(self, payload: dict[str, Any]) -> _FakeExec:
            return _FakeExec(payload)

    class _FakeClient:
        def table(self, _name: str) -> _FakeTable:
            return _FakeTable()

    monkeypatch.setattr("api.routes.waitlist._supabase", lambda: _FakeClient())

    async def fake_call(fn: Any, *, timeout: float | None = None) -> Any:  # noqa: ARG001
        try:
            return fn()
        except Exception as exc:
            raise SupabaseQueryError(f"supabase call failed: {type(exc).__name__}") from exc

    monkeypatch.setattr("api.routes.waitlist.supabase_call_async", fake_call)


# ───── Tests ─────


def test_waitlist_happy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    _stub_supabase: _FakeWaitlistStore,
) -> None:
    _install_insert_handler(monkeypatch, _stub_supabase)
    response = client.post(
        "/api/waitlist",
        json={
            "email": "user@example.com",
            "name": "Ada Lovelace",
            "source": "landing_hero",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["queued_at"].endswith("Z")
    assert len(_stub_supabase.rows) == 1
    assert _stub_supabase.rows[0]["email"] == "user@example.com"
    assert _stub_supabase.rows[0]["source"] == "landing_hero"


def test_waitlist_duplicate_email_returns_409(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    _stub_supabase: _FakeWaitlistStore,
) -> None:
    _install_insert_handler(monkeypatch, _stub_supabase)
    payload = {
        "email": "dup@example.com",
        "name": "Dup User",
        "source": "landing_pricing",
    }
    r1 = client.post("/api/waitlist", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/api/waitlist", json=payload)
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"]["error"] == "already_queued"
    assert len(_stub_supabase.rows) == 1  # ikinci insert atılmadı


def test_waitlist_invalid_email_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/waitlist",
        json={
            "email": "not-an-email",
            "name": "X User",
            "source": "landing_hero",
        },
    )
    assert response.status_code == 422


def test_waitlist_honeypot_silent_drop(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    _stub_supabase: _FakeWaitlistStore,
) -> None:
    _install_insert_handler(monkeypatch, _stub_supabase)
    response = client.post(
        "/api/waitlist",
        json={
            "email": "bot@example.com",
            "name": "Bot Name",
            "source": "landing_hero",
            "website": "http://spam.example",
        },
    )
    # Bot'a sinyal verme: 200 fake-OK
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # Ama DB'ye yazılmadı
    assert len(_stub_supabase.rows) == 0
