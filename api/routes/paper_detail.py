"""GET /api/paper/{paper_id} — Paper detail endpoint.
GET /api/paper/{paper_id}/export?fmt=bibtex|ris — Export endpoint.

Supabase fact_paper_id_card lookup + graceful fallback placeholder.
papers table is empty (lazy mirror); title/abstract placeholder until Faz 2.
Export: server-side BibTeX / RIS generation from available metadata.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from api.config import get_settings
from api.models.paper_detail import PaperDetail
from api.models.search import DecisionBand
from api.services.curator import _fetch_paper_cards

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["paper"])


def _build_detail(paper_id: str, row: dict, meta: dict) -> PaperDetail:
    """Build PaperDetail merging Supabase row + OpenAlex meta. Either may be empty."""
    db_year = row.get("year")
    meta_year = meta.get("year") if isinstance(meta.get("year"), int) else None
    year = db_year if db_year is not None else meta_year
    year_verified = db_year is not None
    lang = row.get("language") or (meta.get("language") if isinstance(meta.get("language"), str) else None) or "en"
    is_oa = row.get("is_oa")
    if is_oa is None and isinstance(meta.get("is_oa"), bool):
        is_oa = meta.get("is_oa")
    pmid = row.get("pmid") or f"PM-{paper_id[:8]}"

    meta_title = meta.get("title")
    title = meta_title if isinstance(meta_title, str) and meta_title.strip() else f"Paper {paper_id}"
    meta_authors = meta.get("authors") if isinstance(meta.get("authors"), list) else []
    authors = [a for a in meta_authors if isinstance(a, str) and a.strip()]
    abstract = meta.get("abstract") if isinstance(meta.get("abstract"), str) else None
    abstract_excerpt = abstract[:400] if abstract else None
    journal = meta.get("venue") if isinstance(meta.get("venue"), str) else None
    doi = meta.get("doi") if isinstance(meta.get("doi"), str) else None
    cited = meta.get("cited_by_count") if isinstance(meta.get("cited_by_count"), int) else 0
    url = meta.get("url") if isinstance(meta.get("url"), str) else None

    return PaperDetail(
        paper_id=paper_id,
        pmid=pmid,
        title=title,
        authors=authors,
        year=year,
        year_verified=year_verified,
        doi=doi,
        abstract=abstract,
        abstract_excerpt=abstract_excerpt,
        journal=journal,
        n_cited=cited,
        decision_band=DecisionBand.FRONTIER,
        is_ghost=False,
        language=lang,
        is_open_access=is_oa,
        keywords=[],
        references_count=0,
        cited_by_count=cited,
        url=url,
    )


async def _load_paper(paper_id: str) -> PaperDetail:
    """Supabase row + OpenAlex meta merged; 404 ancak ikisi de boşsa."""
    # Lazy import to avoid circular dependency (paper_detail ↔ search).
    from api.routes.search import _fetch_candidate_metadata

    settings = get_settings()
    card_data = _fetch_paper_cards([paper_id])
    row = card_data.get(paper_id) or {}
    meta_map = await _fetch_candidate_metadata([paper_id], settings.OPENALEX_EMAIL)
    meta = meta_map.get(paper_id) or {}

    # İkisi de boşsa gerçekten yok demektir.
    if not row and not meta:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    return _build_detail(paper_id, row, meta)


@router.get("/paper/{paper_id}", response_model=PaperDetail)
async def get_paper(paper_id: str) -> PaperDetail:
    """Return paper detail from Supabase fact_paper_id_card + OpenAlex; 404 if neither has it."""
    return await _load_paper(paper_id)


# ── Export ─────────────────────────────────────────────────────────────────


def _to_bibtex(d: PaperDetail) -> str:
    authors_str = " and ".join(d.authors) if d.authors else "Unknown"
    key = f"{d.paper_id.replace('/', '_')[:20]}"
    lines = [
        f"@article{{{key},",
        f"  author    = {{{authors_str}}},",
        f"  title     = {{{d.title}}},",
        f"  year      = {{{d.year or 'n.d.'}}},",
    ]
    if d.journal:
        lines.append(f"  journal   = {{{d.journal}}},")
    if d.doi:
        lines.append(f"  doi       = {{{d.doi}}},")
    if d.url:
        lines.append(f"  url       = {{{d.url}}},")
    lines.append("}")
    return "\n".join(lines)


def _to_ris(d: PaperDetail) -> str:
    lines = ["TY  - JOUR"]
    for au in d.authors or []:
        lines.append(f"AU  - {au}")
    lines.append(f"TI  - {d.title}")
    if d.year:
        lines.append(f"PY  - {d.year}")
    if d.journal:
        lines.append(f"JO  - {d.journal}")
    if d.doi:
        lines.append(f"DO  - {d.doi}")
    if d.url:
        lines.append(f"UR  - {d.url}")
    lines.append("ER  -")
    return "\n".join(lines)


@router.get("/paper/{paper_id}/export")
async def export_paper(
    paper_id: str,
    fmt: Literal["bibtex", "ris"] = Query(default="bibtex"),
) -> PlainTextResponse:
    """Export paper as BibTeX or RIS."""
    detail = await _load_paper(paper_id)

    if fmt == "bibtex":
        content = _to_bibtex(detail)
        media = "application/x-bibtex"
        filename = f"{paper_id}.bib"
    else:
        content = _to_ris(detail)
        media = "application/x-research-info-systems"
        filename = f"{paper_id}.ris"

    return PlainTextResponse(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
