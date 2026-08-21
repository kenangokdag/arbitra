"""V1-S12 TTS Pydantic models — sesli dinlet.

kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §3
HK-1: extra="forbid" tüm dış-yüz modellerde.
V1: TR-only (Omer 2026-05-10). EN/ID V1.5+.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TTSReviewRequest(BaseModel):
    """Literatür özeti → ElevenLabs TTS audio/mpeg.

    `content`: review.content metni (LiteratureReviewLLM çıktısı).
    `lang`: V1 sadece "tr"; EN/ID V1.5'te eklenecek.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    content: str = Field(min_length=10, max_length=5000)
    lang: Literal["tr"] = "tr"


__all__ = ["TTSReviewRequest"]
