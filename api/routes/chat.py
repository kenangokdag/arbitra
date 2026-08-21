"""POST /api/chat — F3b concrete (B42-052 + Council 37a, F8 DM-LLM-3/7/8).

F8 unification: doğrudan provider SDK çağrıları kaldırıldı; LLMService.call() tek abstraction.
ROLE_MODULES[mode] + ProjectContext + page_state otomatik prompt injection.
K11 fallback: LLMServiceError → deterministic template.

DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16: report_id → _build_report_context
eklendi — Danışman panelinin incelenen makalenin hakem raporuna (Finding/verdict/
risk_radar/citation_integrity) bağlanması için. Auth: AuthMiddleware
request.state.user_id zorunlu (review._user_id helper'ı reuse eder, account.py'deki
desenle aynı).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from api.config import get_settings
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.models.chat import ChatChunk, ChatRequest
from api.models.llm import ProjectContext
from api.models.review import ReviewReport
from api.routes.review import _user_id
from api.routes.search import _fetch_candidate_metadata
from api.services import review_service
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


def _cache_key(req: ChatRequest) -> str:
    last_msg = req.messages[-1].content
    ctx_ids = ",".join(sorted(req.paper_context_ids))
    report_id = str(req.report_id) if req.report_id else ""
    raw = f"{req.session_id}:{req.language}:{req.mode}:{ctx_ids}:{report_id}:{last_msg}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _build_paper_context(paper_ids: list[str]) -> list[dict[str, Any]] | None:
    """paper_context_ids → OpenAlex meta projeksiyonu (title/year/venue/authors/abstract).

    OpenAlex hatası ya da non-W ID → None (silent fallback; citation echo bozulmaz).
    """
    if not paper_ids:
        return None
    settings = get_settings()
    meta_map = await _fetch_candidate_metadata(paper_ids, settings.OPENALEX_EMAIL)
    if not meta_map:
        return None
    return [
        {
            "title": m.get("title"),
            "year": m.get("year"),
            "venue": m.get("venue"),
            "authors": m.get("authors") or [],
            "abstract": m.get("abstract") or "",
        }
        for pid, m in meta_map.items()
    ]


async def _fetch_project_context(project_id: str) -> ProjectContext | None:
    """Supabase'den project state çek. F9-S0 sprint'inde gerçek implementasyon."""
    return None


async def _build_report_context(user_id: str, report_id: UUID | None) -> ReviewReport | None:
    """report_id → sahip-kapsamlı ReviewReport (review_service.get_report reuse).

    review_service.get_report zaten BOLA-safe (row.get("user_id") != user_id →
    LookupError, review_service.py:723-730) — burada YENİ bir yetki kontrolü
    YAZILMIYOR, mevcut güvenli yol miras alınıyor.

    Rapor yoksa/henüz hazır değilse/başka kullanıcıya aitse → None (silent
    fallback; _build_paper_context'in "citation echo bozulmaz" deseniyle TUTARLI —
    chat.py:36-46). Sohbet, rapor bağlamı olmadan devam eder, çökmez.
    """
    if report_id is None:
        return None
    try:
        return await review_service.get_report(user_id, report_id)
    except LookupError:
        logger.info("chat report_context: report not found/owned (report_id=%s)", report_id)
        return None


@router.post("/chat", response_model=ChatChunk)
async def chat(request: Request, req: ChatRequest) -> ChatChunk:
    """Chat completion via LLMService (Gemini 2.5 Flash); K11 template fallback."""
    key = _cache_key(req)
    cached = cache_get(CacheNamespace.QUERY, f"chat:{key}")
    if cached is not None:
        return ChatChunk.model_validate(cached)

    last_user = req.messages[-1].content if req.messages else ""

    project_ctx = None
    if req.project_id:
        project_ctx = await _fetch_project_context(req.project_id)

    paper_context = await _build_paper_context(req.paper_context_ids)
    report_context = await _build_report_context(_user_id(request), req.report_id)
    # Gözlemlenebilirlik (2026-08-19): önceden başarı yolunda hiç log yoktu —
    # "chat rapora bağlı mı" sorusu loglardan cevaplanamıyordu. mode/report_id
    # istekten geldi mi + gerçekten rapor bulundu mu, HER istekte görünür.
    logger.info(
        "chat: mode=%s report_id=%s report_context_found=%s",
        req.mode, req.report_id, report_context is not None,
    )

    delta: str
    try:
        resp = await llm_call(
            prompt=last_user,
            tier="flash",
            mode=req.mode,
            project_ctx=project_ctx,
            page_state=req.page_state,
            paper_context=paper_context,
            report_context=report_context,
        )
        delta = resp.text
    except LLMServiceError as exc:
        logger.warning("chat LLM call failed (K11 fallback): %s", type(exc).__name__)
        templates = {
            "tr": (
                f"'{last_user}' sorgunuz icin literatur taramasi hazirlaniyor. "
                "Detayli sonuclar icin /api/search endpoint'ini kullanabilirsiniz."
            ),
            "en": (
                f"Preparing literature review for '{last_user}'. "
                "Use /api/search endpoint for detailed results."
            ),
            "id": (
                f"Mempersiapkan tinjauan literatur untuk '{last_user}'. "
                "Gunakan endpoint /api/search untuk hasil detail."
            ),
        }
        delta = templates.get(req.language, templates["tr"])

    chunk = ChatChunk(
        delta=delta,
        finished=True,
        citation_paper_ids=req.paper_context_ids[:5],
    )

    cache_set(CacheNamespace.QUERY, f"chat:{key}", chunk.model_dump(mode="json"))
    return chunk
