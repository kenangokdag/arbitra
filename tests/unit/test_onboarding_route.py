"""POST /api/onboarding unit tests — F5-S1A + S1B contract.

Plan: docs/plans/F5_S1_user_profile_bridge_tier_enum.md §8
      docs/plans/F5_S1B_dim_subfield_bridge.md §8 (DM-9)
Cases: happy / missing-field / empty-list / >3-list / duplicate-field-ids /
       invalid-field-id / idempotent / KVKK-orcid-repr +
       subfields-skip / subfields-valid-composite / subfields-orphan /
       subfields-resubmit / subfields-composite-collision (13/13).

FakeSupabase recorder: route'un yaptığı table().select/upsert/delete/insert
çağrılarını yakalar; gerçek HTTP yok. dim_field pre-flight için
field_id whitelist + dim_subfield composite pair whitelist konfigüre edilebilir.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


class _FakeBuilder:
    def __init__(self, recorder: _FakeSupabase, table: str) -> None:
        self._recorder = recorder
        self._table = table
        self._op: str | None = None
        self._payload: Any = None
        self._on_conflict: str | None = None
        self._filters: dict[str, tuple[str, Any]] = {}

    def select(self, *_args: Any, **_kw: Any) -> _FakeBuilder:
        self._op = "select"
        return self

    def upsert(self, payload: Any, on_conflict: str | None = None) -> _FakeBuilder:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def insert(self, payload: Any) -> _FakeBuilder:
        self._op = "insert"
        self._payload = payload
        return self

    def delete(self) -> _FakeBuilder:
        self._op = "delete"
        return self

    def eq(self, col: str, val: Any) -> _FakeBuilder:
        self._filters[col] = ("eq", val)
        return self

    def in_(self, col: str, vals: list[Any]) -> _FakeBuilder:
        self._filters[col] = ("in_", vals)
        return self

    def execute(self) -> SimpleNamespace:
        call = {
            "table": self._table,
            "op": self._op,
            "payload": self._payload,
            "on_conflict": self._on_conflict,
            "filters": dict(self._filters),
        }
        self._recorder.calls.append(call)
        return self._recorder.respond(call)


class _FakeSupabase:
    def __init__(
        self,
        valid_field_ids: set[str],
        valid_subfield_pairs: set[tuple[str, str]] | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._valid_field_ids = valid_field_ids
        self._valid_subfield_pairs = valid_subfield_pairs or set()

    def table(self, name: str) -> _FakeBuilder:
        return _FakeBuilder(self, name)

    def respond(self, call: dict[str, Any]) -> SimpleNamespace:
        if call["table"] == "dim_field" and call["op"] == "select":
            in_filter = call["filters"].get("field_id")
            if in_filter and in_filter[0] == "in_":
                requested = in_filter[1]
                data = [
                    {"field_id": fid}
                    for fid in requested
                    if fid in self._valid_field_ids
                ]
                return SimpleNamespace(data=data)
        if call["table"] == "dim_subfield" and call["op"] == "select":
            in_filter = call["filters"].get("subfield_id")
            if in_filter and in_filter[0] == "in_":
                requested_subs = set(in_filter[1])
                data = [
                    {"subfield_id": sid, "field_id": fid}
                    for (sid, fid) in self._valid_subfield_pairs
                    if sid in requested_subs
                ]
                return SimpleNamespace(data=data)
        return SimpleNamespace(data=[])


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-onb-1"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase(
        valid_field_ids={
            "computer_science",
            "mathematics",
            "biology",
            "medicine",
            "pharmacology_toxicology_and_pharmaceutics",
        },
        valid_subfield_pairs={
            ("pharmacology", "medicine"),
            ("pharmacology", "pharmacology_toxicology_and_pharmaceutics"),
            ("surgery", "medicine"),
            ("ml", "computer_science"),
        },
    )
    monkeypatch.setattr("api.routes.onboarding._supabase", lambda: fake)

    async def _direct_call(fn: Any, *, timeout: float | None = None) -> Any:
        del timeout
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "full_name": "Ada Lovelace",
        "tier": "arastirmaci",
        "field_ids": ["computer_science", "mathematics"],
        "research_focus": "ML in academic literature retrieval",
    }
    base.update(overrides)
    return base


# ── 1. Happy path ─────────────────────────────────────────────────────────────


def test_onboarding_happy_path(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(orcid_raw="0000-0001-2345-6789"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user_id"] == "user-onb-1"
    assert body["tier"] == "arastirmaci"
    assert body["field_ids"] == ["computer_science", "mathematics"]
    assert body["subfields"] == []
    assert body["profile_complete"] is True

    ops = [(c["table"], c["op"]) for c in fake_db.calls]
    assert ops == [
        ("dim_field", "select"),
        ("user_profiles", "upsert"),
        ("user_profile_fields", "delete"),
        ("user_profile_fields", "insert"),
    ]

    upsert_call = fake_db.calls[1]
    payload = upsert_call["payload"]
    assert "language_pref" not in payload
    assert "field_primary" not in payload
    assert payload["tier"] == "arastirmaci"
    assert payload["onboarding_completed"] is True
    expected_hash = hashlib.sha256(b"0000-0001-2345-6789").hexdigest()
    assert payload["orcid_hash"] == expected_hash

    insert_call = fake_db.calls[3]
    bridge_rows = insert_call["payload"]
    assert len(bridge_rows) == 2
    assert bridge_rows[0] == {
        "user_id": "user-onb-1",
        "field_id": "computer_science",
        "position": 1,
    }
    assert bridge_rows[1]["position"] == 2


# ── 2. Missing field — Pydantic 422 ───────────────────────────────────────────


def test_onboarding_missing_required_field_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    payload = _payload()
    del payload["tier"]
    response = authed_client.post("/api/onboarding", json=payload)
    assert response.status_code == 422
    assert fake_db.calls == []


def test_onboarding_empty_field_ids_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post(
        "/api/onboarding", json=_payload(field_ids=[])
    )
    assert response.status_code == 422
    assert fake_db.calls == []


def test_onboarding_too_many_field_ids_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(field_ids=["computer_science", "mathematics", "biology", "x"]),
    )
    assert response.status_code == 422


def test_onboarding_duplicate_field_ids_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(field_ids=["computer_science", "computer_science"]),
    )
    assert response.status_code == 422
    assert fake_db.calls == []


# ── 3. Invalid field_id — route 422 ───────────────────────────────────────────


def test_onboarding_invalid_field_id_returns_422(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(field_ids=["computer_science", "ghost_field"]),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_field_ids"
    assert detail["missing"] == ["ghost_field"]

    ops = [(c["table"], c["op"]) for c in fake_db.calls]
    assert ops == [("dim_field", "select")]


# ── 4. Idempotent re-submit — DELETE+INSERT ──────────────────────────────────


def test_onboarding_idempotent_resubmit_replaces_bridge(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    r1 = authed_client.post(
        "/api/onboarding",
        json=_payload(field_ids=["computer_science", "mathematics"]),
    )
    assert r1.status_code == 200

    r2 = authed_client.post(
        "/api/onboarding",
        json=_payload(field_ids=["biology"]),
    )
    assert r2.status_code == 200
    assert r2.json()["field_ids"] == ["biology"]

    delete_calls = [c for c in fake_db.calls if c["op"] == "delete"]
    insert_calls = [c for c in fake_db.calls if c["op"] == "insert"]
    upsert_calls = [c for c in fake_db.calls if c["op"] == "upsert"]
    assert len(delete_calls) == 2
    assert len(insert_calls) == 2
    assert len(upsert_calls) == 2

    for d in delete_calls:
        assert d["table"] == "user_profile_fields"
        assert d["filters"]["user_id"] == ("eq", "user-onb-1")

    last_insert = insert_calls[-1]
    assert last_insert["payload"] == [
        {"user_id": "user-onb-1", "field_id": "biology", "position": 1}
    ]


# ── 5. KVKK — orcid_raw repr=False (raw log/exception sızdırma yasak) ─────────


def test_onboarding_request_repr_hides_orcid_raw() -> None:
    from api.models.onboarding import OnboardingRequest

    req = OnboardingRequest(
        full_name="Ada Lovelace",
        tier="arastirmaci",
        field_ids=["computer_science"],
        research_focus="ML in academic literature retrieval",
        orcid_raw="0000-0001-2345-6789",
    )
    rendered = repr(req)
    assert "0000-0001-2345-6789" not in rendered
    assert "orcid_raw" not in rendered


# ── 6. S1B — subfields skip path (default []) ─────────────────────────────────


def test_onboarding_subfields_skip_path(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Case 9: subfields=[] → 200, hiçbir user_profile_subfields op (skip)."""
    response = authed_client.post("/api/onboarding", json=_payload(subfields=[]))
    assert response.status_code == 200, response.text
    assert response.json()["subfields"] == []

    sub_ops = [c for c in fake_db.calls if c["table"] == "user_profile_subfields"]
    assert sub_ops == []
    sub_dim_ops = [c for c in fake_db.calls if c["table"] == "dim_subfield"]
    assert sub_dim_ops == []


# ── 7. S1B — subfields valid composite (full happy) ───────────────────────────


def test_onboarding_subfields_valid_composite_happy(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Case 10: field=[medicine], subfields=[(pharmacology, medicine)] → 200, bridge 1 satır."""
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(
            field_ids=["medicine"],
            subfields=[{"subfield_id": "pharmacology", "field_id": "medicine"}],
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subfields"] == [
        {"subfield_id": "pharmacology", "field_id": "medicine"}
    ]

    ops = [(c["table"], c["op"]) for c in fake_db.calls]
    assert ops == [
        ("dim_field", "select"),
        ("dim_subfield", "select"),
        ("user_profiles", "upsert"),
        ("user_profile_fields", "delete"),
        ("user_profile_fields", "insert"),
        ("user_profile_subfields", "delete"),
        ("user_profile_subfields", "insert"),
    ]

    sub_insert = fake_db.calls[6]
    assert sub_insert["payload"] == [
        {"user_id": "user-onb-1", "subfield_id": "pharmacology", "field_id": "medicine"}
    ]


# ── 8. S1B — orphan subfield (parent yok, payload-level) → 422, DB'siz ───────


def test_onboarding_subfields_orphan_returns_422_without_db(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Case 11: field=[medicine], subfields=[(ml, computer_science)] → 422 orphan, DB'ye gitmez."""
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(
            field_ids=["medicine"],
            subfields=[{"subfield_id": "ml", "field_id": "computer_science"}],
        ),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "orphan_subfield_ids"
    assert detail["orphan"] == [["ml", "computer_science"]]

    # Hiç DB çağrısı olmamalı (payload-level check, DB'siz)
    assert fake_db.calls == []


# ── 9. S1B — re-submit subfield değişikliği (idempotent composite) ───────────


def test_onboarding_subfields_resubmit_replaces_bridge(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Case 12: 1. POST [(pharmacology, medicine)] → 2. POST [(surgery, medicine)]
    → 2× user_profile_subfields delete + 2× insert."""
    r1 = authed_client.post(
        "/api/onboarding",
        json=_payload(
            field_ids=["medicine"],
            subfields=[{"subfield_id": "pharmacology", "field_id": "medicine"}],
        ),
    )
    assert r1.status_code == 200, r1.text

    r2 = authed_client.post(
        "/api/onboarding",
        json=_payload(
            field_ids=["medicine"],
            subfields=[{"subfield_id": "surgery", "field_id": "medicine"}],
        ),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["subfields"] == [
        {"subfield_id": "surgery", "field_id": "medicine"}
    ]

    sub_deletes = [
        c for c in fake_db.calls
        if c["table"] == "user_profile_subfields" and c["op"] == "delete"
    ]
    sub_inserts = [
        c for c in fake_db.calls
        if c["table"] == "user_profile_subfields" and c["op"] == "insert"
    ]
    assert len(sub_deletes) == 2
    assert len(sub_inserts) == 2

    for d in sub_deletes:
        assert d["filters"]["user_id"] == ("eq", "user-onb-1")

    last_sub_insert = sub_inserts[-1]
    assert last_sub_insert["payload"] == [
        {"user_id": "user-onb-1", "subfield_id": "surgery", "field_id": "medicine"}
    ]


# ── 10. S1B — composite collision happy (aynı subfield_id 2 farklı parent) ───


def test_onboarding_subfields_composite_collision_happy(
    authed_client: TestClient, fake_db: _FakeSupabase
) -> None:
    """Case 13 (bonus): field=[medicine, pharmacology_toxicology_and_pharmaceutics],
    subfields=[(pharmacology, medicine), (pharmacology, pharmacology_toxicology_and_pharmaceutics)]
    → 200, bridge 2 satır (composite PK ayırıyor)."""
    response = authed_client.post(
        "/api/onboarding",
        json=_payload(
            field_ids=["medicine", "pharmacology_toxicology_and_pharmaceutics"],
            subfields=[
                {"subfield_id": "pharmacology", "field_id": "medicine"},
                {
                    "subfield_id": "pharmacology",
                    "field_id": "pharmacology_toxicology_and_pharmaceutics",
                },
            ],
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subfields"] == [
        {"subfield_id": "pharmacology", "field_id": "medicine"},
        {
            "subfield_id": "pharmacology",
            "field_id": "pharmacology_toxicology_and_pharmaceutics",
        },
    ]

    sub_inserts = [
        c for c in fake_db.calls
        if c["table"] == "user_profile_subfields" and c["op"] == "insert"
    ]
    assert len(sub_inserts) == 1
    rows = sub_inserts[0]["payload"]
    assert len(rows) == 2
    assert rows[0] == {
        "user_id": "user-onb-1",
        "subfield_id": "pharmacology",
        "field_id": "medicine",
    }
    assert rows[1] == {
        "user_id": "user-onb-1",
        "subfield_id": "pharmacology",
        "field_id": "pharmacology_toxicology_and_pharmaceutics",
    }
