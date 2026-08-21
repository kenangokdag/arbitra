"""V1-S12 ElevenLabs TTS adapter — text → mp3 bytes.

kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §2 KD-V1-S12-02..05
HK-2: API key Settings'ten okunur, asla client'a sızmaz.
HK-5: Cost log her çağrıda (char_count + tahmini USD).

ElevenLabs API:
  POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
  Headers: xi-api-key: <key>, Accept: audio/mpeg
  Body: {text, model_id, voice_settings}
  Response: audio/mpeg bytes (mp3)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from api.config import Settings, get_settings

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1/text-to-speech"

# Cost: multilingual_v2 ~$0.30 / 1K karakter (2026-05 pricing).
# 400-kelime özet ≈ 2400 karakter ≈ $0.072 / istek.
USD_PER_CHAR = 0.0003


class ElevenLabsError(Exception):
    """ElevenLabs API çağrı hatası."""


async def synthesize(
    text: str,
    *,
    voice_id: str | None = None,
    model_id: str | None = None,
    settings: Settings | None = None,
) -> bytes:
    """Text → mp3 bytes (audio/mpeg).

    Args:
        text: TTS edilecek metin (10-5000 char önerilir).
        voice_id: ElevenLabs voice ID; default Settings.ELEVENLABS_VOICE_ID.
        model_id: ElevenLabs model; default Settings.ELEVENLABS_MODEL.
        settings: Test override için.

    Raises:
        ElevenLabsError: API key eksik / HTTP hata / boş yanıt.
    """
    cfg = settings or get_settings()
    if not cfg.ELEVENLABS_API_KEY:
        raise ElevenLabsError("ELEVENLABS_API_KEY not configured")

    vid = voice_id or cfg.ELEVENLABS_VOICE_ID
    if not vid:
        raise ElevenLabsError("ELEVENLABS_VOICE_ID not configured")

    url = f"{ELEVENLABS_BASE}/{vid}"
    payload: dict[str, Any] = {
        "text": text,
        "model_id": model_id or cfg.ELEVENLABS_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {
        "xi-api-key": cfg.ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    char_count = len(text)
    est_cost_usd = char_count * USD_PER_CHAR
    logger.info(
        "elevenlabs_tts call voice=%s chars=%d est_cost_usd=%.4f",
        vid,
        char_count,
        est_cost_usd,
    )

    try:
        async with httpx.AsyncClient(timeout=cfg.ELEVENLABS_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio = resp.content
    except httpx.HTTPStatusError as exc:
        logger.error(
            "elevenlabs http error status=%d body=%s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise ElevenLabsError(
            f"elevenlabs http {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("elevenlabs network error: %s", exc)
        raise ElevenLabsError(f"elevenlabs network: {exc}") from exc

    if not audio:
        raise ElevenLabsError("elevenlabs returned empty audio body")

    return audio


__all__ = ["ElevenLabsError", "USD_PER_CHAR", "synthesize"]
