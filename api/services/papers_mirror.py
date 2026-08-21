"""public.papers lazy mirror upsert — OpenAlex meta → DB.

reading_list / notes endpoint'leri W-id'leri Supabase'e yazmadan önce
public.papers'ta satır olduğundan emin olmak için (FK + trigger requirement)
bu helper'ı çağırır. Mevcut satır varsa no-op (ON CONFLICT DO NOTHING).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from api.db.supabase_client import get_supabase_admin, supabase_call_async

logger = logging.getLogger(__name__)

_TABLE = "papers"


async def ensure_paper_row(paper_id: str) -> bool:
    """public.papers'a paper_id için satır garantile.

    Returns True if a row exists (preexisting or just inserted), False on failure.
    Failure'lar log + False döner; caller karar verir (genellikle 502/raise).
    """
    if not paper_id:
        return False
    db = get_supabase_admin()

    # 1) Already there?
    def _select() -> Any:
        return db.from_(_TABLE).select("paper_id").eq("paper_id", paper_id).limit(1).execute()

    try:
        r = await supabase_call_async(_select)
    except Exception as exc:
        logger.warning("papers_mirror select failed paper_id=%s: %s", paper_id, exc)
        return False
    if r.data:
        return True

    # 2) Not there — fetch metadata from OpenAlex and insert
    # Lazy import to avoid circular dep (papers_mirror ↔ search route).
    from api.config import get_settings
    from api.routes.search import _fetch_candidate_metadata

    settings = get_settings()
    meta_map = await _fetch_candidate_metadata([paper_id], settings.OPENALEX_EMAIL)
    meta = meta_map.get(paper_id)
    if not meta or not meta.get("title"):
        logger.info("papers_mirror: no OpenAlex meta for %s — cannot upsert", paper_id)
        return False

    authors_json: list[dict[str, str]] = []
    for name in meta.get("authors") or []:
        if isinstance(name, str) and name.strip():
            authors_json.append({"name": name})

    row = {
        "paper_id": paper_id,
        "title": meta.get("title") or paper_id,
        "doi": meta.get("doi"),
        "abstract": meta.get("abstract"),
        "authors": json.dumps(authors_json) if authors_json else None,
        "year": meta.get("year") if isinstance(meta.get("year"), int) else None,
        "year_verified": isinstance(meta.get("year"), int),
        "venue": meta.get("venue"),
        "lang": meta.get("language"),
        "citations_count": meta.get("cited_by_count") if isinstance(meta.get("cited_by_count"), int) else 0,
    }

    def _insert() -> Any:
        return db.from_(_TABLE).upsert(row, on_conflict="paper_id").execute()

    try:
        await supabase_call_async(_insert)
    except Exception as exc:
        logger.warning("papers_mirror upsert failed paper_id=%s: %s", paper_id, exc)
        return False
    return True
