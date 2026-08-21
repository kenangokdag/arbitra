"""F13-S1-P004 — canlı Gemini Flash smoke (defter pre-advisor özeti).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (1 live smoke Gemini)
Çalıştırma: GEMINI_API_KEY (.env) gerekli.
    python scripts/smoke_diary_pre_advisor.py

Strateji: Supabase'i bypass et, sabit mock olay listesini doğrudan llm_service'e
gönder. Gemini Flash gerçekten cevap verecek mi + prompt formatı tek paragraf
özet üretecek mi onu doğruluyoruz. DB bağımlılığı yok → smoke ortam-sade.
"""

from __future__ import annotations

import asyncio
import sys

from api.services import diary_service
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

_MOCK_EVENTS = [
    {
        "page_slug": "4.2_bosluk_profili",
        "event_type": "kayit",
        "payload": {"note": "M5 boşluğunu (yöntem-veri) işaretledim"},
        "created_at": "2026-04-15T10:00:00+00:00",
        "resolved_at": None,
    },
    {
        "page_slug": "5.2_yayin_taslagi",
        "event_type": "not",
        "payload": {"note": "3 araştırma sorusu (RQ) taslağı kurdum"},
        "created_at": "2026-04-22T14:30:00+00:00",
        "resolved_at": None,
    },
    {
        "page_slug": "6.1_yayin_icerigi_doldurma",
        "event_type": "danismana_sor",
        "payload": {"note": "Doluluk gate'i %60 — eksik bölümleri sor"},
        "created_at": "2026-05-01T09:15:00+00:00",
        "resolved_at": None,
    },
]


async def main() -> int:
    body = "Olaylar (eski → yeni):\n" + "\n".join(
        diary_service._format_event_line(e) for e in _MOCK_EVENTS
    )
    print("── Gönderilen olay listesi ──")
    print(body)
    print()

    try:
        resp = await llm_call(
            prompt=body,
            tier="flash",
            mode="diary_pre_advisor",
            max_tokens=1500,
        )
    except LLMServiceError as exc:
        print(f"FAIL: LLMServiceError → {exc}")
        return 1

    print("── Gemini Flash yanıtı ──")
    print(resp.text)
    print()
    print(
        f"model={resp.model_used} "
        f"tokens={resp.tokens_in}+{resp.tokens_out} "
        f"latency={resp.latency_ms}ms"
    )

    word_count = len(resp.text.split())
    if not (40 <= word_count <= 200):
        print(f"WARN: kelime sayısı {word_count}, beklenen 80-150 civarı")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
