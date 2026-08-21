"""F13-S2-P004 — canlı Gemini Flash smoke ("Danışmana Gitmeden Evvel").

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S2-P004 smoke)
Çalıştırma: GEMINI_API_KEY (.env) gerekli.
    python scripts/smoke_advisor_summary.py

Strateji: Supabase'i bypass et, sabit mock completed-step listesini progress_service
_format_step_block ile sıkıştır + advisor_summary mode'uyla llm_call. Çıktının
4-5 paragraf akademik Türkçe olduğunu gözle doğrula.
"""

from __future__ import annotations

import asyncio
import sys

from api.services import progress_service
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

_MOCK_COMPLETED = [
    {
        "step_id": "discovery-1",
        "completed_at": "2026-04-10T10:00:00+00:00",
        "meta": {
            "anchor": "Eğitim teknolojisi",
            "sub_field": "Adaptif öğrenme sistemleri",
            "research_sentence": (
                "Adaptif öğrenme sistemlerinin K-12 matematik başarısına etkisi"
            ),
        },
    },
    {
        "step_id": "discovery-3",
        "completed_at": "2026-04-12T11:30:00+00:00",
        "meta": {
            "top_journals": "Computers & Education; British Journal of Educational Tech",
            "top_authors": "Kizilcec, Pardos",
            "year_range": "2014-2024",
        },
    },
    {
        "step_id": "curation-1",
        "completed_at": "2026-04-15T14:00:00+00:00",
        "meta": {"paper_count": 12, "selected": "12 paper, OA 8/12"},
    },
    {
        "step_id": "curation-4",
        "completed_at": "2026-04-18T09:00:00+00:00",
        "meta": {
            "note": (
                "Sentez: adaptif sistemler kavramsal düzeyde başarıyı %12-18 artırıyor; "
                "uzun-dönem retention belirsiz"
            ),
        },
    },
    {
        "step_id": "gapatlas-1",
        "completed_at": "2026-04-22T16:00:00+00:00",
        "meta": {"selected_gap": "M5: yöntem-veri", "heatmap_score": 0.83},
    },
    {
        "step_id": "gapatlas-4",
        "completed_at": "2026-04-25T10:00:00+00:00",
        "meta": {"compare_n": 4, "overlap_pct": 43},
    },
]


async def main() -> int:
    publication_type = "makale"
    body = (
        f"Yayın türü: {publication_type}\n\n"
        "Tamamlanan adımlar (eski → yeni):\n"
        + progress_service._format_step_block(_MOCK_COMPLETED)
    )
    print("── Gönderilen body ──")
    print(body)
    print()

    try:
        resp = await llm_call(
            prompt=body,
            tier="flash",
            mode="advisor_summary",
            max_tokens=3000,
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

    paragraphs = [p for p in resp.text.split("\n\n") if p.strip()]
    word_count = len(resp.text.split())
    print(f"paragraf={len(paragraphs)} | kelime={word_count}")

    if not (3 <= len(paragraphs) <= 6):
        print(f"WARN: paragraf sayısı {len(paragraphs)}, beklenen 4-5")
    if not (250 <= word_count <= 600):
        print(f"WARN: kelime sayısı {word_count}, beklenen 300-500")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
