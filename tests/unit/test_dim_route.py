"""GET /api/dim/* unit tests — F5-PRE contract (PROMPT #4-PRE).

Plan: PROMPT #4-PRE brief §4 (kabul kriteri 4 senaryo) + auth-gated default
- 401: GET /api/dim/fields without Bearer (P-PRE1.1 revert: auth-gated default)
- success: GET /api/dim/fields → 200 + sıralı liste + cache header
- success: GET /api/dim/subfields?field_ids=cs → 200 + parent ile filtre
- 422: GET /api/dim/subfields (no param)
- 422: GET /api/dim/subfields?field_ids=a,b,c,d (4 elem)
- 503: Supabase fail (mock SupabaseQueryError → 503)

Auth: middleware Bearer JWT zorunlu — onboarding pattern paraleli (authed_client).
FakeSupabase recorder: route'un table().select().order/in_().execute() çağrılarını yakalar.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


_FIELD_ROWS = [
    {
        "field_id": "computer_science",
        "name_en": "Computer Science",
        "slug": "computer-science",
        "paper_count_total": 1234,
    },
    {
        "field_id": "mathematics",
        "name_en": "Mathematics",
        "slug": "mathematics",
        "paper_count_total": 567,
    },
]

_SUBFIELD_ROWS = [
    {
        "subfield_id": "artificial_intelligence",
        "field_id": "computer_science",
        "name_en": "Artificial Intelligence",
        "slug": "artificial-intelligence",
        "paper_count_total": 100,
    },
    {
        "subfield_id": "computer_vision_and_pattern_recognition",
        "field_id": "computer_science",
        "name_en": "Computer Vision and Pattern Recognition",
        "slug": "computer-vision-and-pattern-recognition",
        "paper_count_total": 50,
    },
]


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._recorder = recorder
        self._table = table
        self._op: str | None = None
        self._filters: dict[str, tuple[str, Any]] = {}
        self._order: str | None = None

    def select(self, *_args: Any, **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def order(self, col: str, *_args: Any, **_kw: Any) -> _FakeBuilder:
        self._order = col
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._filters[col] = ("in_", vals)
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "order": self._order,
            "filters": dict(self._filters),
        }
        self._recorder.calls.append(call)
        return self._recorder.respond(call)


class _FakeSupabase:
    def __init__(self, *, raise_on: set[str] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._raise_on = raise_on or set()

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        if call["table"] in self._raise_on:
            raise RuntimeError(f"injected failure: {call['table']}")
        if call["table"] == "dim_field":
            return SimpleNamespace(data=list(_FIELD_ROWS))
        if call["table"] == "dim_subfield":
            in_filter = call["filters"].get("field_id")
            if in_filter and in_filter[0] == "in_":
                requested = set(in_filter[1])
                data = [r for r in _SUBFIELD_ROWS if r["field_id"] in requested]
                return SimpleNamespace(data=data)
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[])


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-dim-1"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase()
    monkeypatch.setattr("api.routes.dim._supabase", lambda: fake)

    async def _direct_call(fn: Any, *, timeout: float | None = None) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


@pytest.fixture
def failing_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    """Supabase çağrısı SupabaseQueryError fırlatır (transport/runtime fail)."""
    fake = _FakeSupabase(raise_on={"dim_field", "dim_subfield"})
    monkeypatch.setattr("api.routes.dim._supabase", lambda: fake)

    from api.db.supabase_client import SupabaseQueryError

    async def _failing_call(fn: Any, *, timeout: float | None = None) -> Any:
        del timeout
        try:
            return fn()
        except Exception as exc:
            raise SupabaseQueryError("injected") from exc

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _failing_call)
    yield fake


# ── 1. Success: GET /api/dim/fields ──────────────────────────────────────────


def test_dim_fields_success(authed_client: TestClient, fake_db: _FakeSupabase) -> None:
    response = authed_client.get("/api/dim/fields")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "fields" in body
    fields = body["fields"]
    assert len(fields) == 2
    assert fields[0]["field_id"] == "computer_science"
    assert fields[0]["name_en"] == "Computer Science"
    assert fields[0]["slug"] == "computer-science"
    assert fields[0]["paper_count_total"] == 1234
    assert "Cache-Control" in response.headers
    assert "max-age=3600" in response.headers["Cache-Control"]

    assert len(fake_db.calls) == 1
    call = fake_db.calls[0]
    assert call["table"] == "dim_field"
    assert call["op"] == "select"
    assert call["order"] == "name_en"


# ── 2. Success: GET /api/dim/subfields?field_ids=computer_science ────────────


def test_dim_subfields_success_filtered_by_parent(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.get("/api/dim/subfields?field_ids=computer_science")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "subfields" in body
    subs = body["subfields"]
    assert len(subs) == 2
    assert all(s["field_id"] == "computer_science" for s in subs)
    assert subs[0]["subfield_id"] == "artificial_intelligence"
    assert "Cache-Control" in response.headers

    assert len(fake_db.calls) == 1
    call = fake_db.calls[0]
    assert call["table"] == "dim_subfield"
    assert call["filters"]["field_id"] == ("in_", ["computer_science"])


# ── 3. 422: subfields no param (parent context zorunlu) ──────────────────────


def test_dim_subfields_no_param_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.get("/api/dim/subfields")
    assert response.status_code == 422
    assert fake_db.calls == []


# ── 4. 422: subfields >3 parent (max 3) ──────────────────────────────────────


def test_dim_subfields_too_many_parents_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.get("/api/dim/subfields?field_ids=a,b,c,d")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "too_many_field_ids"
    assert detail["max"] == 3
    assert detail["got"] == 4
    assert fake_db.calls == []


# ── 5. 503: Supabase fail (transport/runtime) ────────────────────────────────


def test_dim_fields_supabase_fail_returns_503(
    authed_client: TestClient, failing_db: _FakeSupabase
) -> None:
    response = authed_client.get("/api/dim/fields")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "dim_field_query_failed"


def test_dim_subfields_supabase_fail_returns_503(
    authed_client: TestClient, failing_db: _FakeSupabase
) -> None:
    response = authed_client.get("/api/dim/subfields?field_ids=computer_science")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "dim_subfield_query_failed"


# ── 6. Bonus: dev/test fallback (SUPABASE yok) → boş liste ──────────────────


def test_dim_fields_no_supabase_returns_empty(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """conftest SUPABASE_URL='' → _supabase() None → 200 + {fields: []}."""
    monkeypatch.setattr("api.routes.dim._supabase", lambda: None)
    response = authed_client.get("/api/dim/fields")
    assert response.status_code == 200
    assert response.json() == {"fields": []}


# ── 7. P-PRE1.1 revert: auth-gated default (no Bearer → 401) ────────────────


def test_dim_fields_without_bearer_returns_401(
    client: TestClient, fake_db: _FakeSupabase
) -> None:
    """PUBLIC_PATHS revert (P-PRE1.1) — Bearer header yok → 401, DB'ye gitmez."""
    response = client.get("/api/dim/fields")
    assert response.status_code == 401
    assert response.json()["error"] == "missing_or_invalid_authorization_header"
    assert fake_db.calls == []


def test_dim_subfields_without_bearer_returns_401(
    client: TestClient, fake_db: _FakeSupabase
) -> None:
    """PUBLIC_PATHS revert (P-PRE1.1) — Bearer header yok → 401, DB'ye gitmez."""
    response = client.get("/api/dim/subfields?field_ids=computer_science")
    assert response.status_code == 401
    assert fake_db.calls == []
