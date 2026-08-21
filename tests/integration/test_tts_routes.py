"""V1-S12-01 integration: /api/tts/literature-review.

kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §6
Akış: TestClient + FakeRedis + mock synthesize.

Kapsam:
  - anon happy path (audio/mpeg + 1 quota)
  - anon 2. istek → 429 (anon=1/gün)
  - authed 5 istek OK
  - content < 10 char → 422 (Pydantic min_length)
  - content > 5000 char → 422 (Pydantic max_length)
  - ElevenLabs hata → 502 tts_unavailable
  - HK-1: extra forbid
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from api.middleware.rate_limit import _window

pytestmark = pytest.mark.integration


class _FakePipe:
    def __init__(self, store: dict[str, int]) -> None:
        self._store = store
        self._next: int = 0

    def incr(self, key: str) -> _FakePipe:
        self._store[key] = self._store.get(key, 0) + 1
        self._next = self._store[key]
        return self

    def expire(self, key: str, ttl: int) -> _FakePipe:
        return self

    async def execute(self) -> list[Any]:
        return [self._next, True]


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def pipeline(self) -> _FakePipe:
        return _FakePipe(self.store)


@pytest.fixture(autouse=True)
def _stub_dependencies(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRedis]:
    """Redis + ElevenLabs synthesize mock'lanır."""
    _window.clear()
    fake = FakeRedis()
    monkeypatch.setattr("api.middleware.tier_gate._get_redis", lambda: fake)

    async def fake_synth(text: str, **_: Any) -> bytes:
        return b"\x00\x01fake-mp3-bytes"

    monkeypatch.setattr("api.routes.tts.synthesize", fake_synth)

    yield fake


@pytest.fixture
def auth_token() -> str:
    return jwt.encode({"sub": "user-tts-test"}, "x", algorithm="HS256")


VALID_CONTENT = "Bu bir literatür incelemesi metnidir, en az 10 karakter."


def test_tts_anon_happy_path_returns_audio(client: TestClient) -> None:
    """Anon 1 TTS → 200 audio/mpeg + bytes."""
    r = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"\x00\x01fake-mp3-bytes"
    assert r.headers["x-quota-remaining"] == "0"  # anon limit=1, 1 sayıldı


def test_tts_anon_second_request_returns_429(client: TestClient) -> None:
    """Anon 2. TTS → 429 (anon=1/gün quota cap)."""
    r1 = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr"},
    )
    assert r2.status_code == 429
    body = r2.json()
    assert body["detail"]["error"] == "quota_exceeded"
    assert body["detail"]["limit"] == 1
    assert body["detail"]["tier"] == "anon"


def test_tts_authed_five_requests_ok(client: TestClient, auth_token: str) -> None:
    """Authed 5 TTS → 5xx 200; 6. → 429."""
    for _ in range(5):
        r = client.post(
            "/api/tts/literature-review",
            json={"content": VALID_CONTENT, "lang": "tr"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert r.status_code == 200, r.text
    overflow = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert overflow.status_code == 429
    assert overflow.json()["detail"]["limit"] == 5


def test_tts_content_too_short_returns_422(client: TestClient) -> None:
    """content < 10 char → 422 (Pydantic min_length)."""
    r = client.post(
        "/api/tts/literature-review", json={"content": "kısa", "lang": "tr"}
    )
    assert r.status_code == 422


def test_tts_content_too_long_returns_422(client: TestClient) -> None:
    """content > 5000 char → 422 (Pydantic max_length)."""
    r = client.post(
        "/api/tts/literature-review",
        json={"content": "x" * 5001, "lang": "tr"},
    )
    assert r.status_code == 422


def test_tts_invalid_lang_returns_422(client: TestClient) -> None:
    """V1: lang Literal['tr'] — 'en'/'id' V1.5'te eklenecek; şimdi 422."""
    r = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "en"},
    )
    assert r.status_code == 422


def test_tts_extra_field_returns_422(client: TestClient) -> None:
    """HK-1: extra forbid — bilinmeyen alan 422."""
    r = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr", "evil": "x"},
    )
    assert r.status_code == 422


def test_tts_elevenlabs_failure_returns_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ElevenLabs ElevenLabsError → 502 tts_unavailable."""
    from api.services.elevenlabs_tts import ElevenLabsError

    async def bad_synth(*_a: Any, **_kw: Any) -> bytes:
        raise ElevenLabsError("elevenlabs http 401")

    monkeypatch.setattr("api.routes.tts.synthesize", bad_synth)

    r = client.post(
        "/api/tts/literature-review",
        json={"content": VALID_CONTENT, "lang": "tr"},
    )
    assert r.status_code == 502
    assert r.json()["detail"]["error"] == "tts_unavailable"
