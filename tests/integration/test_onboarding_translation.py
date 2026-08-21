"""F5-S2 onboarding+translation integration tests — PROMPT #4 §4 DoD.

  1. success — TR research_focus POST → 200 + metadata.research_focus_en
     + metadata.translation_meta.fallback=false (jsonb yazıldı)
  2. fallback — translator fallback simule → 200 + translation_meta.fallback=true
     + research_focus_en=research_focus (raw kalır, K-015 graceful)

FakeSupabase recorder: tests/unit/test_onboarding_route.py:29 paterninden port.
Translator route-level mock — translator unit test'leri 5 senaryoyu (success / timeout /
provider fail / empty input / empty response) zaten kapsıyor; bu integration sadece
"hook çağrıldı + metadata jsonb doğru yazıldı + endpoint 200 döner" doğrular.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from api.services.translator import TranslationResult

pytestmark = pytest.mark.integration


# ─── FakeSupabase (test_onboarding_route.py paterni — minimal port) ──────────


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
    def __init__(self, valid_field_ids: set[str]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._valid_field_ids = valid_field_ids

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
        return SimpleNamespace(data=[])


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-tr-1"}, "x", algorithm="HS256")


@pytest.fixture
def authed_client(client: TestClient, auth_token: str) -> TestClient:
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSupabase]:
    fake = _FakeSupabase(valid_field_ids={"computer_science", "medicine"})
    monkeypatch.setattr("api.routes.onboarding._supabase", lambda: fake)

    async def _direct_call(fn: Any, **_kwargs: Any) -> Any:
        return fn()

    monkeypatch.setattr("api.db.supabase_client.supabase_call_async", _direct_call)
    yield fake


_TR_FOCUS = (
    "çok kriterli karar verme yöntemleriyle hastane personeli "
    "performans değerlendirmesi"
)


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "full_name": "Ada Lovelace",
        "tier": "arastirmaci",
        "field_ids": ["computer_science"],
        "research_focus": _TR_FOCUS,
    }
    base.update(overrides)
    return base


def _extract_metadata(fake_db: _FakeSupabase) -> dict[str, Any]:
    """user_profiles upsert call'undan metadata jsonb (json.dumps) parse et."""
    upsert_calls = [c for c in fake_db.calls if c["table"] == "user_profiles"]
    assert len(upsert_calls) == 1, f"expected 1 user_profiles upsert, got {len(upsert_calls)}"
    payload = upsert_calls[0]["payload"]
    metadata_raw = payload["metadata"]
    parsed: dict[str, Any] = json.loads(metadata_raw)
    return parsed


# ─── Test 1: success path (translation_meta.fallback=false) ──────────────────


def test_onboarding_translation_success(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TR research_focus POST → translator çağrılır → metadata.research_focus_en
    yazılır + translation_meta.fallback=false."""

    translated_en = (
        "Multi-criteria decision making methods for hospital staff "
        "performance evaluation"
    )

    async def fake_translate(
        text_raw: str, source_lang_hint: str | None = None
    ) -> TranslationResult:
        del text_raw, source_lang_hint
        return TranslationResult(
            text_en=translated_en,
            source_lang="tr",
            duration_ms=1240,
            fallback=False,
        )

    monkeypatch.setattr(
        "api.routes.onboarding.translate_to_academic_en", fake_translate
    )

    response = authed_client.post("/api/onboarding", json=_payload())
    assert response.status_code == 200, response.text

    metadata = _extract_metadata(fake_db)
    assert metadata["research_focus"] == _TR_FOCUS
    assert metadata["research_focus_en"] == translated_en
    tmeta = metadata["translation_meta"]
    assert tmeta["fallback"] is False
    assert tmeta["source_lang"] == "tr"
    assert tmeta["duration_ms"] == 1240
    # K-014: model alanı static label (Settings.GEMINI_FLASH_MODEL)
    assert tmeta["model"] == "gemini-2.5-flash"


# ─── Test 2: graceful fallback (timeout/provider fail simule) ────────────────


def test_onboarding_translation_fallback(
    authed_client: TestClient,
    fake_db: _FakeSupabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translator timeout/fail → fallback=True + research_focus_en=research_focus
    + endpoint 200 (K-015 graceful, 502 yasak — onboarding tıkanmaz)."""

    async def fake_translate(
        text_raw: str, source_lang_hint: str | None = None
    ) -> TranslationResult:
        del source_lang_hint
        # K-015 fallback: text_en = text_raw kalır
        return TranslationResult(
            text_en=text_raw,
            source_lang="unknown",
            duration_ms=5012,
            fallback=True,
        )

    monkeypatch.setattr(
        "api.routes.onboarding.translate_to_academic_en", fake_translate
    )

    response = authed_client.post("/api/onboarding", json=_payload())
    assert response.status_code == 200, response.text

    metadata = _extract_metadata(fake_db)
    assert metadata["research_focus"] == _TR_FOCUS
    # K-015 kanıtı: fallback path → research_focus_en raw'a eşit
    assert metadata["research_focus_en"] == _TR_FOCUS
    tmeta = metadata["translation_meta"]
    assert tmeta["fallback"] is True
    assert tmeta["source_lang"] == "unknown"
    assert tmeta["duration_ms"] == 5012
    assert tmeta["model"] == "gemini-2.5-flash"
