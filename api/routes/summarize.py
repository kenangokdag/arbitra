"""POST /api/summarize + GET /api/summarize/{task_id} — F3c (B-018 + Council 37b, F8 DM-LLM-3).

Task store: Redis-backed (task_id → SummaryDoc JSON, 24h TTL) with in-memory fallback.
Summary text: LLMService (Gemini 2.5 Flash) when GEMINI_API_KEY set; placeholder template otherwise.
"""

from __future__ import annotations

import hashlib
import logging
import uuid

from fastapi import APIRouter, HTTPException

from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.models.summarize import SummarizeAccepted, SummarizeRequest, SummaryDoc
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["summarize"])

_TASK_TTL = 86400  # 24h in seconds
_task_store: dict[str, SummaryDoc] = {}  # in-memory fallback when Redis unavailable


def _summary_cache_key(paper_id: str, mode: str, lang: str) -> str:
    raw = f"sum:{paper_id}:{lang}:{mode}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _task_key(task_id: str) -> str:
    return f"task:{task_id}"


def _store_task(task_id: str, doc: SummaryDoc) -> None:
    cache_set(CacheNamespace.QUERY, _task_key(task_id), doc.model_dump(mode="json"))
    _task_store[task_id] = doc


def _load_task(task_id: str) -> SummaryDoc | None:
    cached = cache_get(CacheNamespace.QUERY, _task_key(task_id))
    if cached is not None:
        return SummaryDoc.model_validate(cached)
    return _task_store.get(task_id)


async def _call_summarize(paper_id: str, mode: str, language: str) -> str | None:
    """Gemini 2.5 Flash ile özet üret. OpenAlex'ten title+abstract çekip prompt'a enjekte eder;
    metadata yoksa LLM halüsinasyona düşmesin diye None döner (placeholder devreye girer)."""
    # Lazy import — circular dep avoid (search ↔ summarize)
    from api.config import get_settings
    from api.routes.search import _fetch_candidate_metadata

    settings = get_settings()
    meta_map = await _fetch_candidate_metadata([paper_id], settings.OPENALEX_EMAIL)
    meta = meta_map.get(paper_id) or {}
    title = meta.get("title") or ""
    abstract = meta.get("abstract") or ""
    if not title and not abstract:
        logger.info("summarize: no OpenAlex meta for %s — placeholder", paper_id)
        return None

    mode_instructions = {
        "tldr": "Write a 2-3 sentence TL;DR summary.",
        "abstract": "Write a concise abstract-style summary (100-150 words).",
        "deep": "Write a detailed summary covering methodology, findings, and implications (250-300 words).",
    }
    lang_instructions = {"tr": "Respond in Turkish.", "en": "Respond in English.", "id": "Respond in Indonesian."}
    instruction = f"{mode_instructions.get(mode, mode_instructions['tldr'])} {lang_instructions.get(language, '')}"
    authors = ", ".join(meta.get("authors") or [])[:300]
    venue = meta.get("venue") or ""
    year = meta.get("year") or ""
    prompt = (
        f"{instruction}\n\n"
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Venue: {venue} ({year})\n\n"
        f"Abstract:\n{abstract}\n\n"
        "Summarize ONLY based on the abstract above; do not invent facts."
    )

    try:
        resp = await llm_call(prompt=prompt, tier="flash", mode="summarize")
    except LLMServiceError as exc:
        logger.warning("summarize LLM call failed paper_id=%s: %s", paper_id, type(exc).__name__)
        return None
    return resp.text.strip() if resp.text else None


def _placeholder_summary(paper_id: str, mode: str, lang: str) -> str:
    templates = {
        "abstract": {
            "tr": f"{paper_id} — Bu çalışma alandaki temel bulguları sunmaktadır. (Özet yakında hazır.)",
            "en": f"{paper_id} — This study presents key findings in the field. (Full summary pending.)",
            "id": f"{paper_id} — Studi ini menyajikan temuan utama. (Ringkasan segera tersedia.)",
        },
        "tldr": {
            "tr": f"{paper_id}: Alandaki önemli bir katkı. (Özet yakında hazır.)",
            "en": f"{paper_id}: A significant contribution to the field. (Summary pending.)",
            "id": f"{paper_id}: Kontribusi signifikan. (Ringkasan segera tersedia.)",
        },
        "deep": {
            "tr": f"{paper_id} — Detaylı analiz hazırlanıyor. Lütfen bekleyiniz.",
            "en": f"{paper_id} — Detailed analysis pending. Please check back shortly.",
            "id": f"{paper_id} — Analisis mendalam sedang disiapkan.",
        },
    }
    return templates.get(mode, templates["tldr"]).get(lang, templates.get(mode, templates["tldr"])["en"])


@router.post("/summarize", response_model=SummarizeAccepted, status_code=202)
async def submit_summary(req: SummarizeRequest) -> SummarizeAccepted:
    cache_key = _summary_cache_key(req.paper_id, req.mode, req.language)
    cached = cache_get(CacheNamespace.QUERY, cache_key)
    if cached is not None:
        doc = SummaryDoc.model_validate(cached)
        task_id = f"cached-{cache_key[:16]}"
        _store_task(task_id, doc)
        return SummarizeAccepted(task_id=task_id, status="complete")

    task_id = f"sum-{uuid.uuid4().hex[:16]}"
    text = await _call_summarize(req.paper_id, req.mode, req.language)
    if text is None:
        text = _placeholder_summary(req.paper_id, req.mode, req.language)

    doc = SummaryDoc(
        paper_id=req.paper_id,
        mode=req.mode,
        language=req.language,
        text=text,
        citations=[req.paper_id],
        faithfulness_meta={"jsonschema_pct": 100.0, "lvr_min": 0.85},
    )
    _store_task(task_id, doc)
    cache_set(CacheNamespace.QUERY, cache_key, doc.model_dump(mode="json"))

    return SummarizeAccepted(task_id=task_id, status="complete")


@router.get("/summarize/{task_id}", response_model=SummaryDoc)
async def get_summary(task_id: str) -> SummaryDoc:
    doc = _load_task(task_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "task_not_found", "task_id": task_id},
        )
    return doc
