"""V1-S12-01 unit: ElevenLabs TTS adapter — synthesize() httpx mock.

kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §6 (backend unit)
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from api.config import Settings
from api.services.elevenlabs_tts import ElevenLabsError, synthesize


def _settings(api_key: str = "sk_test", voice_id: str = "vid_test") -> Settings:
    s = Settings()
    s.ELEVENLABS_API_KEY = api_key
    s.ELEVENLABS_VOICE_ID = voice_id
    s.ELEVENLABS_MODEL = "eleven_multilingual_v2"
    return s


@pytest.mark.asyncio
async def test_synthesize_calls_elevenlabs_with_correct_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """synthesize → POST /v1/text-to-speech/{voice_id} + xi-api-key header + mp3 döner."""
    captured: dict[str, Any] = {}

    class _Resp:
        status_code = 200
        content = b"\x00\x01mp3-bytes"
        text = ""

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, **_: Any) -> None: ...

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def post(self, url: str, *, json: Any, headers: Any) -> _Resp:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Resp()

    monkeypatch.setattr(
        "api.services.elevenlabs_tts.httpx.AsyncClient", _Client
    )

    audio = await synthesize(
        "Merhaba dünya bu bir testtir.", settings=_settings()
    )

    assert audio == b"\x00\x01mp3-bytes"
    assert captured["url"].endswith("/v1/text-to-speech/vid_test")
    assert captured["headers"]["xi-api-key"] == "sk_test"
    assert captured["headers"]["Accept"] == "audio/mpeg"
    assert captured["json"]["text"] == "Merhaba dünya bu bir testtir."
    assert captured["json"]["model_id"] == "eleven_multilingual_v2"
    assert "voice_settings" in captured["json"]


@pytest.mark.asyncio
async def test_synthesize_missing_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ELEVENLABS_API_KEY boş → ElevenLabsError."""
    with pytest.raises(ElevenLabsError, match="API_KEY"):
        await synthesize("test", settings=_settings(api_key=""))


@pytest.mark.asyncio
async def test_synthesize_http_error_raises_elevenlabs_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ElevenLabs 401 → ElevenLabsError (error masked)."""

    class _BadResp:
        status_code = 401
        content = b""
        text = "Unauthorized"

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError(
                "401", request=httpx.Request("POST", "x"), response=self  # type: ignore[arg-type]
            )

    class _Client:
        def __init__(self, **_: Any) -> None: ...

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def post(self, *_a: Any, **_kw: Any) -> _BadResp:
            return _BadResp()

    monkeypatch.setattr(
        "api.services.elevenlabs_tts.httpx.AsyncClient", _Client
    )

    with pytest.raises(ElevenLabsError, match="401"):
        await synthesize("test", settings=_settings())


@pytest.mark.asyncio
async def test_synthesize_empty_audio_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ElevenLabs boş body döndürse → ElevenLabsError."""

    class _Resp:
        status_code = 200
        content = b""
        text = ""

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, **_: Any) -> None: ...

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def post(self, *_a: Any, **_kw: Any) -> _Resp:
            return _Resp()

    monkeypatch.setattr(
        "api.services.elevenlabs_tts.httpx.AsyncClient", _Client
    )

    with pytest.raises(ElevenLabsError, match="empty"):
        await synthesize("test", settings=_settings())
