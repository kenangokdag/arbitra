"""V1-S12 TTS rotası — /api/tts/literature-review (sesli dinlet).

kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §2 KD-V1-S12-02..03
HK-1: Pydantic forbid (TTSReviewRequest).
HK-2: ElevenLabs API key Settings'ten; client'a sızmaz.
HK-3: Quota tier_gate üzerinden (anon=1/gün, authed=5/gün).

Akış:
  Depends(tier_gate) → quota check (429 aşılırsa)
  → elevenlabs_tts.synthesize(content) → mp3 bytes
  → Response(audio/mpeg)
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.middleware.tier_gate import tier_gate
from api.models.tts import TTSReviewRequest
from api.services.elevenlabs_tts import ElevenLabsError, synthesize

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])

_CITATION_RE = re.compile(r"\s*\[\d+\]")


def _strip_citations(text: str) -> str:
    """[02], [10] gibi numaralı kaynak işaretlerini sesli okumadan önce siler.

    ElevenLabs aksi halde "köşeli parantez sıfır iki" diye okur.
    """
    cleaned = _CITATION_RE.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip()


@router.post(
    "/literature-review",
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio stream"},
    },
)
async def tts_literature_review(
    req: TTSReviewRequest,
    quota: Annotated[dict[str, Any], Depends(tier_gate)],
) -> Response:
    """Literatür özeti metnini ElevenLabs ile seslendir → mp3 stream döner.

    KD-V1-S12-02: ElevenLabs API key gizli (backend proxy).
    KD-V1-S12-03: tier_gate quota anon=1/gün, authed=5/gün.
    """
    try:
        audio = await synthesize(_strip_citations(req.content))
    except ElevenLabsError as exc:
        logger.warning("tts elevenlabs failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "tts_unavailable", "reason": str(exc)},
        ) from exc

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Quota-Remaining": str(quota["quota_remaining"]),
            "X-Quota-Reset": str(quota["quota_reset"]),
        },
    )


__all__ = ["router"]
