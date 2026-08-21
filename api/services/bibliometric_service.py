"""V1-S14 P005 — Bibliometric aggregate service.

Plan: docs/plans/V1_S14_mock_to_live.md §3 P005 (REVİZE 2026-05-10, B-029).

Tasarım:
- Supabase IN filter max 100 → batch (curator.py pattern, 100'erli).
- PostgREST aggregate desteği sınırlı (RPC gerektirir); aggregate Python-side.
- 24M satır taraması yok — sorgu paper_id PRIMARY KEY üzerinden filter.
- Hata graceful: tablo yoksa / boş döner ise alan default'a düşer
  (median_year=None, mean_citations=0.0, most_cited=None, listeler boş).

Kolonlar (migration kanıtlı):
- fact_paper_id_card: paper_id, year, language, pmid (`0003:31-48`)
- fact_paper_beauty:  paper_id, total_cites (`0005:140-152`)
- fact_paper_field:   paper_id, primary_field (`0006:21-27`)
- dim_field:          field_id, name_en (`0011`)
- fact_paper_sentence_role: paper_id, dominant_role (`0004:21-37`)
"""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from typing import Any, cast

from supabase import Client

from api.db.supabase_client import supabase_call_async
from api.models.bibliometric import (
    BibliometricConfidence,
    BibliometricSummary,
    LangCount,
    MostCited,
    NamedCount,
    YearCount,
)

logger = logging.getLogger(__name__)

_BATCH = 100  # Supabase PostgREST IN max


def _chunks(items: list[str], size: int = _BATCH) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _select_in(
    db: Client, table: str, columns: str, paper_ids: list[str]
) -> list[dict[str, Any]]:
    """Batched SELECT ... WHERE paper_id IN (...). Hata = boş liste (graceful)."""
    rows: list[dict[str, Any]] = []
    for batch in _chunks(paper_ids):
        def _q(b: list[str] = batch) -> Any:
            return db.table(table).select(columns).in_("paper_id", b).execute()

        try:
            resp = await supabase_call_async(_q)
            rows.extend(cast(list[dict[str, Any]], resp.data or []))
        except Exception as exc:
            logger.warning("supabase select %s failed: %s", table, exc)
    return rows


def _year_dist(card_rows: list[dict[str, Any]]) -> list[YearCount]:
    counter: Counter[int] = Counter()
    for r in card_rows:
        y = r.get("year")
        if isinstance(y, int) and 1900 <= y <= 2100:
            counter[y] += 1
    return [YearCount(year=y, count=c) for y, c in sorted(counter.items())]


def _median_year(card_rows: list[dict[str, Any]]) -> int | None:
    years = [r["year"] for r in card_rows if isinstance(r.get("year"), int)]
    if not years:
        return None
    return int(statistics.median(years))


def _lang_dist(card_rows: list[dict[str, Any]]) -> list[LangCount]:
    counter: Counter[str] = Counter()
    for r in card_rows:
        code = r.get("language") or "unknown"
        counter[str(code)] += 1
    return [
        LangCount(code=c, count=n)
        for c, n in sorted(counter.items(), key=lambda x: -x[1])
    ]


def _mean_citations(beauty_rows: list[dict[str, Any]]) -> float:
    cites = [
        int(r["total_cites"]) for r in beauty_rows if isinstance(r.get("total_cites"), int)
    ]
    if not cites:
        return 0.0
    return round(sum(cites) / len(cites), 2)


def _most_cited(
    beauty_rows: list[dict[str, Any]], pmid_map: dict[str, str]
) -> MostCited | None:
    best: tuple[str, int] | None = None
    for r in beauty_rows:
        cites = r.get("total_cites")
        pid = r.get("paper_id")
        if (
            isinstance(cites, int)
            and isinstance(pid, str)
            and (best is None or cites > best[1])
        ):
            best = (pid, cites)
    if best is None:
        return None
    return MostCited(paper_id=best[0], pmid=pmid_map.get(best[0]), citations=best[1])


async def _top_areas(
    db: Client, paper_ids: list[str], k: int = 10
) -> list[NamedCount]:
    field_rows = await _select_in(
        db, "fact_paper_field", "paper_id,primary_field", paper_ids
    )
    counter: Counter[str] = Counter()
    for r in field_rows:
        f = r.get("primary_field")
        if isinstance(f, str) and f:
            counter[f] += 1
    if not counter:
        return []

    field_ids = list(counter.keys())
    name_map: dict[str, str] = {fid: fid for fid in field_ids}

    def _q() -> Any:
        return (
            db.table("dim_field")
            .select("field_id,name_en")
            .in_("field_id", field_ids)
            .execute()
        )

    try:
        resp = await supabase_call_async(_q)
        for r in cast(list[dict[str, Any]], resp.data or []):
            fid = r.get("field_id")
            nm = r.get("name_en")
            if isinstance(fid, str) and isinstance(nm, str):
                name_map[fid] = nm
    except Exception as exc:
        logger.warning("dim_field lookup failed: %s", exc)

    return [
        NamedCount(name=name_map.get(fid, fid), count=cnt)
        for fid, cnt in counter.most_common(k)
    ]


_ROLE_LABEL = {
    "BACKGROUND": "Arka plan",
    "OBJECTIVE": "Amaç",
    "METHOD": "Yöntem",
    "RESULT": "Sonuç",
    "CONCLUSION": "Çıkarım",
    "NONE": "Belirsiz",
}


async def _top_methods(
    db: Client, paper_ids: list[str], k: int = 10
) -> list[NamedCount]:
    rows = await _select_in(
        db, "fact_paper_sentence_role", "paper_id,dominant_role", paper_ids
    )
    counter: Counter[str] = Counter()
    for r in rows:
        role = r.get("dominant_role")
        if isinstance(role, str) and role:
            counter[role] += 1
    return [
        NamedCount(name=_ROLE_LABEL.get(role, role), count=cnt)
        for role, cnt in counter.most_common(k)
    ]


async def compute_bibliometric_summary(
    db: Client, paper_ids: list[str]
) -> BibliometricSummary:
    """Tek endpoint, paper_ids üzerinden 7 alan hesaplar."""
    if not paper_ids:
        return BibliometricSummary(
            total_papers=0,
            median_year=None,
            mean_citations=0.0,
            most_cited=None,
            publications_by_year=[],
            language_dist=[],
            top_areas=[],
            top_methods=[],
            confidence=BibliometricConfidence(
                card_metrics="C",
                beauty_metrics="C",
                top_areas="C",
                top_methods="C",
            ),
        )

    card_rows = await _select_in(
        db, "fact_paper_id_card", "paper_id,year,language,pmid", paper_ids
    )
    beauty_rows = await _select_in(
        db, "fact_paper_beauty", "paper_id,total_cites", paper_ids
    )

    pmid_map: dict[str, str] = {
        r["paper_id"]: r["pmid"]
        for r in card_rows
        if isinstance(r.get("paper_id"), str) and isinstance(r.get("pmid"), str)
    }

    top_areas = await _top_areas(db, paper_ids)
    top_methods = await _top_methods(db, paper_ids)

    # N-13: warehouse aggregate erişildi mi? (boş = C tahmin/uygulanmaz)
    confidence = BibliometricConfidence(
        card_metrics="A" if card_rows else "C",
        beauty_metrics="A" if beauty_rows else "C",
        top_areas="A" if top_areas else "C",
        top_methods="A" if top_methods else "C",
    )

    return BibliometricSummary(
        total_papers=len(paper_ids),
        median_year=_median_year(card_rows),
        mean_citations=_mean_citations(beauty_rows),
        most_cited=_most_cited(beauty_rows, pmid_map),
        publications_by_year=_year_dist(card_rows),
        language_dist=_lang_dist(card_rows),
        top_areas=top_areas,
        top_methods=top_methods,
        confidence=confidence,
    )
