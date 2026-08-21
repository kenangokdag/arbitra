"""F9 P095 BÖLÜM 2 anchor_finder — 3 çapa adayı orkestrasyonu.

Plan: docs/plans/F9_kesif_workbench.md §3 P095 + §9 BÖLÜM 2 + §11 R4 R7

Pipeline:
  1. Proje + son adviser turn parsed_understanding (Stage A) — K-031 zırh.
  2. HyDE: LLMService.call(mode="hyde_packet", structured_output_schema=HydePacket).
  3. Paralel fan-out (asyncio.gather):
       a) Pinecone vec havuz: BGE-M3 encode(packet_p) → top-80 (filter=None DEFERRED §16-1).
       b) Supabase tsvector havuz: lexical_tsvector_pool(packet_s, top-80).
  4. RRF k=60 (Cormack 2009 SIGIR) — `_rrf_merge` reuse → top-50.
  5. Enrich: papers + fact_paper_id_card + fact_paper_quality_v3 — `is_suspicious=false`
     HARD filter (Plan §11 satır 418, RISK_7 v1.2).
  6. BGE-reranker-v2-m3: candidate_texts = title + abstract preview → top-3.
  7. AnchorCandidatesResponse (3 × AnchorCandidate + packet_p + packet_s).

Hatalar:
- ProjectNotFoundError (K-031): proje yok / başkasının → route 404
- ParsedUnderstandingMissingError: Stage A henüz tamamlanmamış → route 409
- LLMServiceError: HyDE fail → route 503
- Empty pool union → AnchorCandidatesEmptyError → route 504 (havuzlar boş)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, cast

from pydantic import ValidationError
from supabase import Client

from api.models.llm import ProjectContext
from api.models.research_area import (
    AnchorCandidate,
    AnchorCandidatesResponse,
    HydePacket,
    ParsedUnderstanding,
)
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call
from api.services.pool_router import _QueryEncoder, _rrf_merge, lexical_tsvector_pool
from api.services.reranker import Reranker

logger = logging.getLogger(__name__)

# Sabitler — Plan §3 P095 satırı + §9 BÖLÜM 2.
# V1-S17 P005 (KD-V1-S17-04): _FINAL_TOP_K 3 → 5 (Omer 1.a kararı).
_VEC_TOP_K = 80
_LEX_TOP_K = 80
_RRF_TOP_K = 50
_FINAL_TOP_K = 5
_HYDE_MAX_TOKENS = 1800  # P094 K-032 paralel: Gemini Flash 600/1200 truncate ediyor


class ProjectNotFoundError(Exception):
    """Proje bulunamadı veya kullanıcının değil (K-031)."""


class ParsedUnderstandingMissingError(Exception):
    """Stage A Tur 2 parsed_understanding henüz Supabase'de yok."""


class AnchorCandidatesEmptyError(Exception):
    """Pinecone + tsvector birleşimi boş döndü (havuz fail)."""


async def _fetch_project_and_understanding(
    db: Client, project_id: str, user_id: str
) -> tuple[dict[str, Any], ParsedUnderstanding]:
    """projects (K-031 zırh) + project_chat_messages son adviser parsed."""
    from api.db.supabase_client import supabase_call_async

    proj_resp = await supabase_call_async(
        lambda: db.table("projects")
        .select("id,inherited_research_focus")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    proj_rows = cast(list[dict[str, Any]], proj_resp.data or [])
    if not proj_rows:
        raise ProjectNotFoundError(f"project {project_id} not found for user {user_id}")
    project = proj_rows[0]

    msg_resp = await supabase_call_async(
        lambda: db.table("project_chat_messages")
        .select("parsed_understanding,attempt_no,turn_no")
        .eq("project_id", project_id)
        .eq("role", "adviser")
        .order("attempt_no", desc=True)
        .order("turn_no", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], msg_resp.data or [])
    if not rows:
        raise ParsedUnderstandingMissingError(
            f"no adviser turn for project {project_id}"
        )
    raw = rows[0].get("parsed_understanding")
    if not isinstance(raw, dict):
        raise ParsedUnderstandingMissingError(
            f"parsed_understanding missing for project {project_id}"
        )
    try:
        parsed = ParsedUnderstanding.model_validate(raw)
    except ValidationError as exc:
        raise ParsedUnderstandingMissingError(
            f"parsed_understanding invalid: {exc}"
        ) from exc
    return project, parsed


async def _call_hyde(
    *, project_id: str, user_id: str, parsed: ParsedUnderstanding
) -> HydePacket:
    """Gemini Flash mode='hyde_packet' → HydePacket (structured output)."""
    project_ctx = ProjectContext(project_id=project_id, user_id=user_id)
    page_state: dict[str, Any] = {
        "focuses": parsed.focuses,
        "field": parsed.field,
        "subfield": parsed.subfield,
        "interdisc": parsed.interdisc,
        "confidence": parsed.confidence,
        "adviser_text": parsed.adviser_text,
    }
    # HyDE prompt: parsed_understanding'i serialize ederek HydePacket iste.
    prompt = (
        "Bu Tur 2 parsed_understanding'ten BÖLÜM 2 arama paketini üret. "
        "Sadece JSON döndür: {pseudo_paragraph, keywords}."
    )
    try:
        response = await llm_call(
            prompt=prompt,
            tier="flash",
            mode="hyde_packet",
            project_ctx=project_ctx,
            page_state=page_state,
            structured_output_schema=HydePacket,
            max_tokens=_HYDE_MAX_TOKENS,
        )
    except ValidationError as exc:
        raise LLMServiceError(f"hyde_packet schema invalid: {exc}") from exc

    if not isinstance(response.parsed_output, HydePacket):
        raise LLMServiceError("hyde_packet parsed_output missing")
    return response.parsed_output


async def _vec_pool(
    encoder: _QueryEncoder, pseudo_paragraph: str, top_k: int = _VEC_TOP_K
) -> list[tuple[str, float]]:
    """BGE-M3 encode + Pinecone top-k. Hata → boş liste (graceful degrade).

    DEFERRED §16-1: filter=None — Pinecone B-012 metadata HARD filter 1.2'de zorunlu.
    """
    from api.db.pinecone_client import PineconeQueryError, get_pinecone_index
    from api.utils.resilience import ResilienceTimeoutError

    vectors = await asyncio.to_thread(encoder.encode, [pseudo_paragraph])
    vec = vectors[0]
    idx = get_pinecone_index()
    try:
        result = await idx.query_async(
            vector=vec, top_k=top_k, filter=None, include_metadata=False
        )
    except (ResilienceTimeoutError, PineconeQueryError) as exc:
        logger.warning("vec_pool degraded error=%s", exc.__class__.__name__)
        return []
    matches = result.get("matches") or []
    out: list[tuple[str, float]] = []
    for m in matches:
        pid = getattr(m, "id", None)
        score = getattr(m, "score", None)
        if isinstance(pid, str) and isinstance(score, (int, float)):
            out.append((pid, float(score)))
    return out


def _decision_band(q_weak: float | None) -> Literal["high", "med", "low"]:
    if q_weak is None:
        return "med"
    if q_weak >= 0.66:
        return "high"
    if q_weak < 0.33:
        return "low"
    return "med"


async def _enrich_candidates(
    db: Client, paper_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """papers + fact_paper_id_card + fact_paper_quality_v3 batch JOIN.

    HARD filter: fact_paper_id_card.is_suspicious=false (Plan §11 satır 418).
    Suspicious paper'lar dictionary'den hariç tutulur (eşit `paper_id` yok =
    aday düşer; reranker zaten kalan 50'den top-3 seçer).
    """
    from api.db.supabase_client import supabase_call_async

    if not paper_ids:
        return {}

    papers_resp = await supabase_call_async(
        lambda: db.table("papers")
        .select("paper_id,title,abstract,year,lang")
        .in_("paper_id", paper_ids)
        .execute()
    )
    papers_rows = cast(list[dict[str, Any]], papers_resp.data or [])

    card_resp = await supabase_call_async(
        lambda: db.table("fact_paper_id_card")
        .select("paper_id,language,year,is_suspicious")
        .in_("paper_id", paper_ids)
        .eq("is_suspicious", False)
        .execute()
    )
    card_rows = cast(list[dict[str, Any]], card_resp.data or [])
    safe_ids = {r["paper_id"] for r in card_rows if isinstance(r.get("paper_id"), str)}

    quality_resp = await supabase_call_async(
        lambda: db.table("fact_paper_quality_v3")
        .select("paper_id,q_weak")
        .in_("paper_id", paper_ids)
        .execute()
    )
    quality_rows = cast(list[dict[str, Any]], quality_resp.data or [])
    q_map: dict[str, float | None] = {}
    for r in quality_rows:
        pid = r.get("paper_id")
        if isinstance(pid, str):
            qw = r.get("q_weak")
            q_map[pid] = float(qw) if isinstance(qw, (int, float)) else None

    card_map: dict[str, dict[str, Any]] = {
        r["paper_id"]: r for r in card_rows if isinstance(r.get("paper_id"), str)
    }

    enriched: dict[str, dict[str, Any]] = {}
    for row in papers_rows:
        pid = row.get("paper_id")
        if not isinstance(pid, str):
            continue
        if pid not in safe_ids:
            continue  # is_suspicious=true filtrelendi
        card = card_map.get(pid, {})
        title = row.get("title") or ""
        abstract = row.get("abstract") or ""
        enriched[pid] = {
            "paper_id": pid,
            "title": title,
            "abstract_preview": abstract[:1200] if abstract else "",
            "rerank_text": (title + " " + abstract)[:2000].strip(),
            "language": row.get("lang") or card.get("language"),
            "year": row.get("year") or card.get("year"),
            "q_weak": q_map.get(pid),
        }
    return enriched


async def _metadata_fallback(
    enriched: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """V1-S17 P006 RC2 (KD-V1-S17-06) — Supabase title boş ise OpenAlex backfill.

    `_enrich_candidates` çıktısı üzerinde in-place: title NULL/boş paper_id'leri
    tek OpenAlex batch çağrısıyla (`_fetch_candidate_metadata`, per-page 50) doldur.
    Supabase önceliği korunur — sadece eksik alanlar overwrite edilir.

    Plan §6 A1 (Sercan): tek batch (asyncio.gather GEREK YOK çünkü
    _fetch_candidate_metadata zaten 50 paper'ı tek HTTP istekte alır).
    """
    missing_ids = [
        pid
        for pid, e in enriched.items()
        if not (isinstance(e.get("title"), str) and e["title"].strip())
    ]
    if not missing_ids:
        return enriched

    from api.config import get_settings
    from api.routes.search import _fetch_candidate_metadata

    settings = get_settings()
    meta_map = await _fetch_candidate_metadata(missing_ids, settings.OPENALEX_EMAIL)
    if not meta_map:
        return enriched

    for pid in missing_ids:
        meta = meta_map.get(pid)
        if not isinstance(meta, dict):
            continue
        e = enriched[pid]
        oa_title = meta.get("title")
        oa_abs = meta.get("abstract")
        if isinstance(oa_title, str) and oa_title.strip() and not e.get("title"):
            e["title"] = oa_title
        if (
            isinstance(oa_abs, str)
            and oa_abs.strip()
            and not e.get("abstract_preview")
        ):
            e["abstract_preview"] = oa_abs[:1200]
        title_now = e.get("title") or ""
        abs_now = oa_abs if isinstance(oa_abs, str) else ""
        rerank = (title_now + " " + abs_now)[:2000].strip()
        if rerank:
            e["rerank_text"] = rerank
        if not e.get("language"):
            lang = meta.get("language")
            if isinstance(lang, str) and lang:
                e["language"] = lang
        if not e.get("year"):
            yr = meta.get("year")
            if isinstance(yr, int):
                e["year"] = yr
    return enriched


async def run(
    *,
    db: Client,
    project_id: str,
    user_id: str,
    encoder: _QueryEncoder | None = None,
    reranker: Reranker | None = None,
) -> AnchorCandidatesResponse:
    """Stage B BÖLÜM 2 — 3 çapa adayı pipeline."""
    project, parsed = await _fetch_project_and_understanding(db, project_id, user_id)
    del project  # şu an kullanılmıyor; ileride field default için

    packet = await _call_hyde(project_id=project_id, user_id=user_id, parsed=parsed)

    enc = encoder or _QueryEncoder()

    vec_task = asyncio.create_task(_vec_pool(enc, packet.pseudo_paragraph))
    lex_task = asyncio.create_task(lexical_tsvector_pool(db, packet.keywords, _LEX_TOP_K))
    vec_results, lex_results = await asyncio.gather(
        vec_task, lex_task, return_exceptions=True
    )

    if isinstance(vec_results, BaseException):
        logger.warning("vec_pool failed (graceful): %s", vec_results)
        vec_results = []
    if isinstance(lex_results, BaseException):
        logger.warning("lex_pool failed (graceful): %s", lex_results)
        lex_results = []

    pools = [p for p in (vec_results, lex_results) if p]
    if not pools:
        raise AnchorCandidatesEmptyError("both pools empty (Pinecone+tsvector)")

    merged = _rrf_merge(*pools)[:_RRF_TOP_K]
    candidate_ids = [pid for pid, _ in merged]

    enriched = await _enrich_candidates(db, candidate_ids)
    if not enriched:
        raise AnchorCandidatesEmptyError(
            "all RRF candidates filtered (is_suspicious=true)"
        )

    # V1-S17 P006 (KD-V1-S17-06): Supabase title boş → OpenAlex backfill.
    enriched = await _metadata_fallback(enriched)

    # Reranker: text-aware top-3.
    if reranker is None:
        from api.services.reranker import BgeReranker
        reranker = BgeReranker()
    candidate_texts = {pid: enriched[pid]["rerank_text"] for pid in enriched}
    top = await reranker.rerank(
        candidates=list(enriched.keys()),
        query=packet.pseudo_paragraph,
        top_k=_FINAL_TOP_K,
        candidate_texts=candidate_texts,
    )

    # V1-S17 P005: curator._signals_13 paterni — her aday üstüne attach
    from api.services.curator import _signals_13

    candidates: list[AnchorCandidate] = []
    for pid, _score in top:
        e = enriched.get(pid)
        if e is None:
            continue
        q_weak = e["q_weak"]
        q_weak_f = float(q_weak) if isinstance(q_weak, (int, float)) else 0.0
        candidates.append(
            AnchorCandidate(
                paper_id=pid,
                title=e["title"][:600] if e["title"] else pid,
                abstract_preview=e["abstract_preview"],
                field=None,  # Pinecone B-012 F-meta filter 1.2'de zorunlu
                language=e["language"],
                year=e["year"] if isinstance(e["year"], int) else None,
                decision_band=_decision_band(q_weak),
                q_weak=q_weak_f,
                signals_13=_signals_13(q_weak_f),
            )
        )

    if not candidates:
        raise AnchorCandidatesEmptyError("reranker returned no candidates")

    return AnchorCandidatesResponse(
        candidates=candidates,
        packet_p=packet.pseudo_paragraph,
        packet_s=packet.keywords,
    )


__all__ = [
    "AnchorCandidatesEmptyError",
    "ParsedUnderstandingMissingError",
    "ProjectNotFoundError",
    "run",
]
