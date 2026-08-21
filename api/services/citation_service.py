"""F13-S4 5.4 Atıf Stil — citation service (SQL search + verify + format + balance).

RTF: Page_Design/Sayfa_Plani_v2/5.4_atif_stil_kilavuzu.rtf §Plan-Detayı
Felsefe: hiçbir atıf icat edilmez; SQL deterministic + Python template.
Halüsinasyon kontrolü: regex extract → papers fuzzy match → bulamazsa 'hallucinated'.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.citation import (
    CitationFinding,
    CitationPaper,
    CitationSearchResponse,
    CitationStyle,
    CitationVerifyResponse,
    FormatCitationResponse,
    Lang,
    SentenceStatus,
    SentenceVerification,
)
from engine.citation import format_citation, to_bibtex
from engine.citation.types import PaperMeta

logger = logging.getLogger(__name__)

_PAPERS_TABLE = "papers"
_DICT_DIR = Path(__file__).resolve().parents[2] / "engine" / "dictionary"

# Author, Year veya Author et al., Year — basit kalıp
_CITATION_RE = re.compile(
    r"([A-ZÇĞİÖŞÜ][a-zçğıöşü\-']+)(?:\s+et\s+al\.?)?[,\s]+\(?\s*(\d{4})\)?",
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜ])")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_RECENT_THRESHOLD_YEARS = 5
_TOPIC_SIM_THRESHOLD = 0.10  # token-Jaccard proxy — sentence-transformers proxy


@lru_cache(maxsize=3)
def _load_dictionary(lang: Lang) -> dict[str, list[str]]:
    path = _DICT_DIR / f"{lang}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, list[str]], data.get("synonyms", {}))


def _paper_to_meta(row: dict[str, Any]) -> PaperMeta:
    """papers row → PaperMeta (engine/citation girdisi)."""
    authors_raw = row.get("authors") or []
    if isinstance(authors_raw, str):
        try:
            authors_raw = json.loads(authors_raw)
        except json.JSONDecodeError:
            authors_raw = []
    authors_list: list[str] = []
    if isinstance(authors_raw, list):
        for a in authors_raw:
            if isinstance(a, dict):
                name = a.get("name")
                if isinstance(name, str):
                    authors_list.append(name)
            elif isinstance(a, str):
                authors_list.append(a)
    meta_json = row.get("metadata") or {}
    if isinstance(meta_json, str):
        try:
            meta_json = json.loads(meta_json)
        except json.JSONDecodeError:
            meta_json = {}
    return cast(
        PaperMeta,
        {
            "paper_id": row.get("paper_id", ""),
            "title": row.get("title", ""),
            "authors": authors_list,
            "year": row.get("year"),
            "venue": row.get("venue"),
            "doi": row.get("doi"),
            "volume": meta_json.get("volume") if isinstance(meta_json, dict) else None,
            "issue": meta_json.get("issue") if isinstance(meta_json, dict) else None,
            "pages": meta_json.get("pages") if isinstance(meta_json, dict) else None,
        },
    )


def _row_to_card(row: dict[str, Any]) -> CitationPaper:
    meta = _paper_to_meta(row)
    return CitationPaper(
        paper_id=meta["paper_id"],
        title=meta["title"],
        authors=meta["authors"],
        year=meta.get("year"),
        venue=meta.get("venue"),
        doi=meta.get("doi"),
        citations_count=row.get("citations_count") or 0,
    )


async def _query_papers_ilike(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """papers.title trigram (gin_trgm_ops, 0001_init_schema_v1.sql:57) ILIKE arama."""
    db = get_supabase_admin()
    pattern = f"%{query}%"

    def _q() -> Any:
        return (
            db.table(_PAPERS_TABLE)
            .select(
                "paper_id, title, abstract, authors, year, venue, doi, citations_count, metadata"
            )
            .or_(f"title.ilike.{pattern},abstract.ilike.{pattern}")
            .order("citations_count", desc=True)
            .limit(limit)
            .execute()
        )

    resp = await supabase_call_async(_q)
    return cast(list[dict[str, Any]], resp.data or [])


async def search_citations(
    project_id: UUID, query: str, lang: Lang = "tr"
) -> CitationSearchResponse:
    """Kelime/iddia → havuzdan top-20 paper. Synonym fallback engine/dictionary/{lang}.json."""
    rows = await _query_papers_ilike(query)
    synonyms_tried: list[str] = []
    if not rows:
        synonyms = _load_dictionary(lang).get(query.lower(), [])
        for syn in synonyms[:3]:
            synonyms_tried.append(syn)
            rows = await _query_papers_ilike(syn)
            if rows:
                break
    papers = [_row_to_card(r) for r in rows]
    return CitationSearchResponse(
        papers=papers,
        synonyms_tried=synonyms_tried,
        total_results=len(papers),
    )


async def fetch_paper(paper_id: str) -> dict[str, Any] | None:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PAPERS_TABLE)
            .select("*")
            .eq("paper_id", paper_id)
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    return cast(dict[str, Any], rows[0]) if rows else None


async def format_one_citation(
    paper_id: str, style: CitationStyle
) -> FormatCitationResponse:
    """GET /api/workshop/format-citation."""
    row = await fetch_paper(paper_id)
    if not row:
        raise LookupError(f"paper {paper_id} not found")
    meta = _paper_to_meta(row)
    formatted = format_citation(meta, style)
    bib = to_bibtex(meta)
    return FormatCitationResponse(
        paper_id=paper_id,
        style=style,
        formatted_citation=formatted,
        bibtex_entry=bib,
    )


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _extract_citations(sentence: str) -> list[tuple[str, int]]:
    """(author_guess, year) listesini regex ile çıkar."""
    out: list[tuple[str, int]] = []
    for m in _CITATION_RE.finditer(sentence):
        author = m.group(1)
        try:
            year = int(m.group(2))
        except ValueError:
            continue
        if 1900 <= year <= datetime.now(UTC).year + 1:
            out.append((author, year))
    return out


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


async def _match_citation(author: str, year: int) -> dict[str, Any] | None:
    """authors JSONB içinde author yüzeysel arama + year eşleşme."""
    db = get_supabase_admin()
    author_pattern = f"%{author}%"

    def _q() -> Any:
        return (
            db.table(_PAPERS_TABLE)
            .select("paper_id, title, abstract, authors, year, venue, doi")
            .eq("year", year)
            .ilike("authors::text", author_pattern)
            .limit(1)
            .execute()
        )

    try:
        resp = await supabase_call_async(_q)
    except Exception:
        logger.exception("citation author match query failed")
        return None
    rows = resp.data or []
    return cast(dict[str, Any], rows[0]) if rows else None


def _looks_like_claim(sentence: str) -> bool:
    """Heuristik: iddia-içerici cümleler (%, sayı, 'gösterdi'/'showed' vb.)."""
    lowered = sentence.lower()
    triggers = (
        "%",
        "gösterdi",
        "göstermiştir",
        "kanıtl",
        "ortaya koy",
        "showed",
        "demonstrate",
        "evidence",
        "found that",
    )
    if any(t in lowered for t in triggers):
        return True
    return bool(re.search(r"\b\d+([.,]\d+)?\s*(%|kez|kat)?\b", sentence))


async def verify_citations(
    project_id: UUID, document_text: str
) -> CitationVerifyResponse:
    """POST /api/workshop/citation-verify — cümle-başı 4-sınıf doğrulama.

    Halüsinasyon kapısı: regex'ten gelen (Author, Year) papers'ta yoksa
    'hallucinated' bayrak. Konu-uyum: cümle ↔ paper.title+abstract token-Jaccard
    < threshold → 'topic_mismatch'. İddia-içerikli cümlede atıf yoksa 'needs_citation'.
    """
    sentences = _split_sentences(document_text)
    out: list[SentenceVerification] = []
    total_cites = 0
    hall = 0
    mismatch = 0
    needs = 0

    for i, sent in enumerate(sentences):
        cite_pairs = _extract_citations(sent)
        findings: list[CitationFinding] = []
        status: SentenceStatus = "ok"
        sentence_tokens = _tokens(sent)

        for author, year in cite_pairs:
            total_cites += 1
            row = await _match_citation(author, year)
            paper_id = row.get("paper_id") if row else None
            findings.append(
                CitationFinding(
                    raw=f"{author}, {year}",
                    author_guess=author,
                    year_guess=year,
                    matched_paper_id=paper_id,
                )
            )
            if not row:
                status = "hallucinated"
                hall += 1
                continue
            paper_tokens = _tokens(
                f"{row.get('title', '')} {row.get('abstract', '') or ''}"
            )
            sim = _jaccard(sentence_tokens, paper_tokens)
            if sim < _TOPIC_SIM_THRESHOLD and status == "ok":
                status = "topic_mismatch"
                mismatch += 1

        if not cite_pairs and _looks_like_claim(sent):
            status = "needs_citation"
            needs += 1

        out.append(
            SentenceVerification(
                index=i, text=sent, citations=findings, status=status
            )
        )

    return CitationVerifyResponse(
        sentences=out,
        total_citations=total_cites,
        hallucinated_count=hall,
        topic_mismatch_count=mismatch,
        needs_citation_count=needs,
    )


async def compute_balance(
    project_id: UUID, paper_ids: list[str]
) -> dict[str, Any]:
    """POST /api/workshop/citation-balance — yıl histogram + öneri.

    eski_pct > 70 → son 5 yıl top-10 öneri.
    yeni_pct > 90 → klasik temeller (en eski + en cited 10) öneri.
    """
    db = get_supabase_admin()
    now_year = datetime.now(UTC).year
    cutoff = now_year - _RECENT_THRESHOLD_YEARS

    def _q_years() -> Any:
        return (
            db.table(_PAPERS_TABLE)
            .select("paper_id, year, title, authors, venue, doi, citations_count")
            .in_("paper_id", paper_ids)
            .execute()
        )

    resp = await supabase_call_async(_q_years)
    rows = cast(list[dict[str, Any]], resp.data or [])
    total = len(rows)
    if total == 0:
        return {
            "total": 0,
            "old_count": 0,
            "recent_count": 0,
            "old_pct": 0.0,
            "recent_pct": 0.0,
            "suggested_papers": [],
            "balance_advice": "Atıf listesi boş veya havuzda eşleşme yok.",
        }
    old = [r for r in rows if (r.get("year") or 0) < cutoff]
    recent = [r for r in rows if (r.get("year") or 0) >= cutoff]
    old_pct = 100.0 * len(old) / total
    recent_pct = 100.0 * len(recent) / total

    suggested: list[CitationPaper] = []
    advice = "Eski-yeni atıf dengesi makul görünüyor."

    if old_pct > 70:
        def _q_recent() -> Any:
            return (
                db.table(_PAPERS_TABLE)
                .select(
                    "paper_id, title, authors, year, venue, doi, citations_count"
                )
                .gte("year", cutoff)
                .order("citations_count", desc=True)
                .limit(10)
                .execute()
            )

        sresp = await supabase_call_async(_q_recent)
        suggested = [_row_to_card(r) for r in (sresp.data or [])]
        advice = (
            f"Atıfların %{old_pct:.0f}'i {cutoff} öncesinde — son 5 yıldan ek "
            "referans önerilir."
        )
    elif recent_pct > 90:
        def _q_classics() -> Any:
            return (
                db.table(_PAPERS_TABLE)
                .select(
                    "paper_id, title, authors, year, venue, doi, citations_count"
                )
                .lt("year", cutoff)
                .order("citations_count", desc=True)
                .limit(10)
                .execute()
            )

        cresp = await supabase_call_async(_q_classics)
        suggested = [_row_to_card(r) for r in (cresp.data or [])]
        advice = (
            f"Atıfların %{recent_pct:.0f}'i son 5 yılda — klasik temellere "
            "(yüksek citations_count) yer verilmesi önerilir."
        )

    return {
        "total": total,
        "old_count": len(old),
        "recent_count": len(recent),
        "old_pct": round(old_pct, 2),
        "recent_pct": round(recent_pct, 2),
        "suggested_papers": suggested,
        "balance_advice": advice,
    }
