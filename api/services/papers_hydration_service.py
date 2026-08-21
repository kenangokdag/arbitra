"""F13-S11-P000 — papers tablosu lazy hydration servisi.

kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md (S11.0 — papers metadata altyapısı)

Senaryo:
- project_seed_papers'ta paper_id (OpenAlex W-id) var ama papers tablosunda metadata yok.
- synthesis_service._fetch_papers, originality_service, impact_curve UI gerçek title/year/venue ister.
- "Bu projenin makaleleri" endpoint'i papers.title üzerinden okur.

Akış:
1. Input paper_ids → bare W-id'ye normalize (rsplit "/").
2. papers tablosunda mevcut olanları çıkar (set diff).
3. Eksikleri OpenAlex polite-pool batch endpoint'inden çek (max 25/req, gerekirse chunk).
4. UPSERT papers (paper_id PK). created_at default, updated_at trigger ile güncellenir.

HK-3: yazma operasyonu — service-role bypass (RLS papers_write_service).
HK-6: no Any (cast'li sınırda).
"""

from __future__ import annotations

import logging
from typing import Any, cast

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.services.openalex_polite import OpenAlexError, fetch_papers_by_ids

logger = logging.getLogger(__name__)

_OPENALEX_BATCH = 25


def _normalize_ids(paper_ids: list[str]) -> list[str]:
    """OpenAlex URL veya bare W-id → bare W-id (deduplicated, order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in paper_ids:
        if not raw:
            continue
        bare = raw.rsplit("/", 1)[-1].strip()
        if not bare or bare in seen:
            continue
        seen.add(bare)
        out.append(bare)
    return out


async def _fetch_existing(paper_ids: list[str]) -> set[str]:
    """papers tablosunda zaten kayıtlı paper_id'leri döner."""
    if not paper_ids:
        return set()
    db = get_supabase_admin()
    resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id")
        .in_("paper_id", paper_ids)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return {str(r["paper_id"]) for r in rows}


def _preview_to_row(preview: Any) -> dict[str, Any]:
    """PaperPreview → papers tablosu satırı (UPSERT payload)."""
    bare = preview.openalex_id.rsplit("/", 1)[-1] if preview.openalex_id else ""
    authors_json = [{"name": name} for name in (preview.authors or [])]
    return {
        "paper_id": bare,
        "doi": preview.doi,
        "title": preview.title or "(başlıksız)",
        "abstract": preview.abstract,
        "authors": authors_json,
        "year": preview.year,
        "year_verified": False,
        "venue": preview.venue,
        "citations_count": preview.cited_by_count or 0,
    }


async def hydrate_paper_ids(paper_ids: list[str]) -> int:
    """Eksik paper_id'leri OpenAlex'ten çekip papers tablosuna UPSERT eder.

    Returns: yazılan/güncellenen satır sayısı (0 = hepsi zaten vardı veya OpenAlex
    bilmiyor). Hata durumunda log + raise (caller endpoint 503 atar).
    """
    normalized = _normalize_ids(paper_ids)
    if not normalized:
        return 0

    existing = await _fetch_existing(normalized)
    missing = [pid for pid in normalized if pid not in existing]
    if not missing:
        return 0

    rows: list[dict[str, Any]] = []
    for start in range(0, len(missing), _OPENALEX_BATCH):
        chunk = missing[start : start + _OPENALEX_BATCH]
        try:
            previews = await fetch_papers_by_ids(chunk)
        except OpenAlexError:
            logger.warning("hydrate: openalex batch failed (chunk=%d)", len(chunk))
            raise
        rows.extend(_preview_to_row(p) for p in previews)

    if not rows:
        # OpenAlex hiçbirini bilmiyor (silinmiş W-id?) — sessiz dön.
        logger.info("hydrate: openalex returned 0 papers for %d missing ids", len(missing))
        return 0

    db = get_supabase_admin()
    upserted = await supabase_call_async(
        lambda: db.table("papers").upsert(rows, on_conflict="paper_id").execute()
    )
    data = cast(list[dict[str, Any]], upserted.data or [])
    return len(data)


__all__ = ["hydrate_paper_ids"]
