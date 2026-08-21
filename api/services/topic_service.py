"""F13-S5 5.2 Yayın Taslağı — topic-proposals + draft-skeleton service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S5
RTF:  Page_Design/Sayfa_Plani_v2/5.2_yayin_taslagi.rtf §Plan-Detayı (1)+(2)+(3)+(4)+(5)

Akış (topic-proposals):
  1. Proje sahipliği doğrula (projects.user_id JOIN)
  2. Günlük kota kontrol (Redis: rate_limit:topic_proposal:{pid}:{date})
  3. Output cache kontrol (Redis: cache_get) — 1h TTL
  4. project_seed_papers ∪ gap hücresi → en güçlü 10 paper meta
  5. Gemini Pro çağrı + Pydantic structured output (3 kart)
  6. Cache yaz + count INCR

Akış (draft-skeleton):
  1. Sahiplik doğrula
  2. 4 paralel SQL: intro/methods/findings/discussion için top-5 paper
  3. 4 paralel Flash çağrı (asyncio.gather) — bölüm başına 1 paragraf
  4. Birleştir + dön
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, cast
from uuid import UUID

import redis as redis_pkg

from api.db.redis_client import (
    cache_get,
    cache_set,
    get_redis_async,
)
from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.topic import (
    DraftSection,
    DraftSectionLLMOutput,
    DraftSkeletonResponse,
    SectionName,
    SkeletonPaperRef,
    TopicLang,
    TopicProposal,
    TopicProposalsLLMOutput,
    TopicProposalsRequest,
    TopicProposalsResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_DAILY_QUOTA = 3
_CACHE_NAMESPACE = "topic_proposal"
_CACHE_TTL = 3600
_CANDIDATE_LIMIT = 10
_SECTION_TOP_K = 5


def _check_ownership(project_id: UUID, user_id: UUID) -> dict[str, Any]:
    client = get_supabase_admin()
    resp = (
        client.table("projects")
        .select("id,user_id,language")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise LookupError("project_not_found")
    row = rows[0]
    if str(row.get("user_id")) != str(user_id):
        raise PermissionError("project_not_owned")
    return row


def _resolve_lang(
    lang_arg: TopicLang | None, project_row: dict[str, Any]
) -> TopicLang:
    if lang_arg is not None:
        return lang_arg
    proj_lang = project_row.get("language")
    if proj_lang in ("tr", "en", "id"):
        return cast(TopicLang, proj_lang)
    return "tr"


def _fetch_seed_papers_meta(
    project_id: UUID, limit: int
) -> list[dict[str, Any]]:
    """project_seed_papers + papers JOIN: en yüksek citations_count'tan."""
    client = get_supabase_admin()
    seed_resp = (
        client.table("project_seed_papers")
        .select("paper_id")
        .eq("project_id", str(project_id))
        .execute()
    )
    seed_ids = [
        r["paper_id"] for r in cast(list[dict[str, Any]], seed_resp.data or [])
    ]
    if not seed_ids:
        return []
    paper_resp = (
        client.table("papers")
        .select("paper_id,title,abstract,year,citations_count,authors")
        .in_("paper_id", seed_ids)
        .order("citations_count", desc=True)
        .limit(limit)
        .execute()
    )
    return cast(list[dict[str, Any]], paper_resp.data or [])


def _short_authors(authors: list[Any] | None) -> str:
    if not authors:
        return "(bilinmiyor)"
    names: list[str] = []
    for a in authors[:2]:
        if isinstance(a, dict) and a.get("name"):
            names.append(str(a["name"]))
    if len(authors) > 2:
        names.append("et al.")
    return ", ".join(names) if names else "(bilinmiyor)"


def _build_candidate_block(papers: list[dict[str, Any]]) -> str:
    if not papers:
        return "(havuz boş — paper meta yok)"
    blocks: list[str] = []
    for p in papers:
        abstract = (p.get("abstract") or "")[:300]
        blocks.append(
            f"[{p.get('paper_id')}] {p.get('title') or 'Untitled'} "
            f"({p.get('year') or 'n/a'})\n"
            f"Authors: {_short_authors(p.get('authors'))}\n"
            f"Abstract excerpt: {abstract}"
        )
    return "\n\n".join(blocks)


def _build_proposals_prompt(
    req: TopicProposalsRequest,
    lang: TopicLang,
    candidate_papers: list[dict[str, Any]],
) -> str:
    method_str = (
        ", ".join(req.method_profile) if req.method_profile else "(profil boş)"
    )
    synth_block = (
        f"\n\nLiteratür sentezi (3.4):\n{req.synthesis_text.strip()}"
        if req.synthesis_text
        else ""
    )
    lang_directive = {
        "tr": "Türkçe yaz.",
        "en": "Write in English.",
        "id": "Tulis dalam Bahasa Indonesia.",
    }[lang]
    return (
        f"{lang_directive}\n\n"
        f"Gap matrix: {req.gap_matrix_id}\n"
        f"Gap axis X: {req.gap_axis_x}\n"
        f"Gap axis Y: {req.gap_axis_y}\n"
        f"Method profile (3.3): {method_str}{synth_block}\n\n"
        f"Candidate papers (havuzdan):\n{_build_candidate_block(candidate_papers)}\n\n"
        'Çıktı SADECE JSON: {"proposals": [...3 kart...]}'
    )


async def _quota_state(project_id: UUID) -> tuple[int, int]:
    """(generation_count, remaining) — Redis günlük sayaç. Redis yoksa (0, max)."""
    key = f"rate_limit:topic_proposal:{project_id}:{date.today().isoformat()}"
    try:
        client = get_redis_async()
        raw = await client.get(key)
    except redis_pkg.RedisError as exc:
        logger.warning("topic_proposal quota get failed: %s", exc)
        return 0, _DAILY_QUOTA
    count = int(raw) if raw is not None else 0
    remaining = max(_DAILY_QUOTA - count, 0)
    return count, remaining


async def _quota_increment(project_id: UUID) -> None:
    """INCR + 24h TTL — Redis yoksa sessiz."""
    key = f"rate_limit:topic_proposal:{project_id}:{date.today().isoformat()}"
    try:
        client = get_redis_async()
        await client.incr(key)
        await client.expire(key, 86400)
    except redis_pkg.RedisError as exc:
        logger.warning("topic_proposal quota incr failed: %s", exc)


def _cache_key(req: TopicProposalsRequest) -> str:
    parts = [
        str(req.project_id),
        req.gap_matrix_id,
        req.gap_axis_x,
        req.gap_axis_y,
        ",".join(req.method_profile),
    ]
    return "|".join(parts)


async def propose_topics(
    user_id: UUID, req: TopicProposalsRequest
) -> TopicProposalsResponse:
    """5.2 (1) — 3 gap-uyumlu konu kartı (Pro + structured output + cache + quota)."""
    project_row = await supabase_call_async(
        lambda: _check_ownership(req.project_id, user_id), timeout=8.0
    )
    lang = _resolve_lang(req.lang, project_row)

    count, remaining = await _quota_state(req.project_id)
    cache_key = _cache_key(req)
    cached = cache_get(_CACHE_NAMESPACE, cache_key)
    if cached:
        parsed = TopicProposalsLLMOutput.model_validate(cached)
        return TopicProposalsResponse(
            proposals=parsed.proposals,
            generation_count=count,
            daily_quota_remaining=remaining,
            lang=lang,
        )

    if remaining <= 0:
        raise PermissionError("daily_quota_exceeded")

    candidate_papers = await supabase_call_async(
        lambda: _fetch_seed_papers_meta(req.project_id, _CANDIDATE_LIMIT),
        timeout=8.0,
    )

    prompt = _build_proposals_prompt(req, lang, candidate_papers)
    response = await llm_call(
        prompt,
        tier="pro",
        mode="topic_proposals",
        structured_output_schema=TopicProposalsLLMOutput,
        max_tokens=2400,
    )
    parsed_out = response.parsed_output
    if not isinstance(parsed_out, TopicProposalsLLMOutput):
        raise ValueError("topic_proposals_llm_output_invalid")
    parsed = parsed_out

    cache_set(
        _CACHE_NAMESPACE,
        cache_key,
        parsed.model_dump(mode="json"),
        ttl=_CACHE_TTL,
    )
    await _quota_increment(req.project_id)
    new_count = count + 1
    new_remaining = max(_DAILY_QUOTA - new_count, 0)

    return TopicProposalsResponse(
        proposals=parsed.proposals,
        generation_count=new_count,
        daily_quota_remaining=new_remaining,
        lang=lang,
    )


# ── draft-skeleton ───────────────────────────────────────────────────────────


def _fetch_section_papers(
    project_id: UUID,
    section: SectionName,
    method_metod_ids: list[str],
) -> list[dict[str, Any]]:
    """RTF Plan Akışı (4): bölüm-bazlı kaynak SQL."""
    client = get_supabase_admin()
    seed_resp = (
        client.table("project_seed_papers")
        .select("paper_id")
        .eq("project_id", str(project_id))
        .execute()
    )
    seed_ids = [
        r["paper_id"] for r in cast(list[dict[str, Any]], seed_resp.data or [])
    ]
    if not seed_ids:
        return []

    if section == "methods" and method_metod_ids:
        metod_resp = (
            client.table("fact_paper_metod")
            .select("paper_id,score")
            .in_("paper_id", seed_ids)
            .in_("metod_id", method_metod_ids)
            .order("score", desc=True)
            .limit(_SECTION_TOP_K * 4)
            .execute()
        )
        candidate_ids = [
            r["paper_id"]
            for r in cast(list[dict[str, Any]], metod_resp.data or [])
        ]
    elif section == "discussion":
        disrupt_resp = (
            client.table("fact_paper_disruption")
            .select("paper_id,cd_5")
            .in_("paper_id", seed_ids)
            .eq("cd_undefined", False)
            .order("cd_5", desc=True)
            .limit(_SECTION_TOP_K * 4)
            .execute()
        )
        candidate_ids = [
            r["paper_id"]
            for r in cast(list[dict[str, Any]], disrupt_resp.data or [])
        ]
    else:
        candidate_ids = seed_ids

    if not candidate_ids:
        return []
    paper_resp = (
        client.table("papers")
        .select("paper_id,title,year,authors,citations_count")
        .in_("paper_id", candidate_ids)
        .order("citations_count", desc=True)
        .limit(_SECTION_TOP_K)
        .execute()
    )
    return cast(list[dict[str, Any]], paper_resp.data or [])


def _papers_to_refs(papers: list[dict[str, Any]]) -> list[SkeletonPaperRef]:
    refs: list[SkeletonPaperRef] = []
    for p in papers:
        refs.append(
            SkeletonPaperRef(
                paper_id=str(p.get("paper_id") or ""),
                title=str(p.get("title") or "Untitled"),
                year=p.get("year"),
                authors_short=_short_authors(p.get("authors")),
                citations_count=int(p.get("citations_count") or 0),
            )
        )
    return refs


def _build_section_prompt(
    section: SectionName,
    topic: TopicProposal,
    section_papers: list[dict[str, Any]],
    lang: TopicLang,
) -> str:
    lang_directive = {
        "tr": "Türkçe yaz.",
        "en": "Write in English.",
        "id": "Tulis dalam Bahasa Indonesia.",
    }[lang]
    hints = (
        "\n".join(
            f"- [{p.get('paper_id')}] {_short_authors(p.get('authors'))} "
            f"({p.get('year') or 'n/a'}): {p.get('title') or 'Untitled'}"
            for p in section_papers
        )
        or "(uygun paper bulunamadı — section_paper_hints boş)"
    )
    return (
        f"{lang_directive}\n\n"
        f"section_name: {section}\n"
        f"topic_title: {topic.title}\n"
        f"topic_balanced_question: {topic.sub_questions.balanced}\n"
        f"method_suggestion: {topic.method_suggestion}\n"
        f"evidence_chain.gap_summary: {topic.evidence_chain.gap_summary}\n"
        f"evidence_chain.method_summary: {topic.evidence_chain.method_summary}\n"
        f"evidence_chain.synthesis_summary: {topic.evidence_chain.synthesis_summary}\n\n"
        f"section_paper_hints:\n{hints}\n\n"
        'Çıktı SADECE JSON: {"draft_paragraph": str, "why_explanation": str}'
    )


async def _draft_one_section(
    project_id: UUID,
    section: SectionName,
    topic: TopicProposal,
    method_metod_ids: list[str],
    lang: TopicLang,
) -> DraftSection:
    section_papers = await supabase_call_async(
        lambda: _fetch_section_papers(project_id, section, method_metod_ids),
        timeout=8.0,
    )
    prompt = _build_section_prompt(section, topic, section_papers, lang)
    response = await llm_call(
        prompt,
        tier="flash",
        mode="draft_skeleton",
        structured_output_schema=DraftSectionLLMOutput,
        max_tokens=600,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, DraftSectionLLMOutput):
        raise ValueError(f"draft_skeleton_llm_output_invalid:{section}")
    return DraftSection(
        name=section,
        draft_paragraph=parsed.draft_paragraph,
        why_explanation=parsed.why_explanation,
        top_5_papers=_papers_to_refs(section_papers),
    )


async def draft_skeleton(
    user_id: UUID,
    project_id: UUID,
    selected_topic: TopicProposal,
    method_metod_ids: list[str],
    sections: list[SectionName],
    lang: TopicLang | None,
) -> DraftSkeletonResponse:
    """5.2 (4) — IMRaD 4 paralel Flash + bölüm-bazlı kaynak SQL."""
    project_row = await supabase_call_async(
        lambda: _check_ownership(project_id, user_id), timeout=8.0
    )
    resolved_lang = _resolve_lang(lang, project_row)

    drafts = await asyncio.gather(
        *[
            _draft_one_section(
                project_id, s, selected_topic, method_metod_ids, resolved_lang
            )
            for s in sections
        ]
    )

    return DraftSkeletonResponse(sections=list(drafts), lang=resolved_lang)


__all__ = ["draft_skeleton", "propose_topics"]
