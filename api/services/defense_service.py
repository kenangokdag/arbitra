"""F13-S7 6.2 Savunma Formatı — defense_session CRUD + question generation.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S7
RTF:  Page_Design/Sayfa_Plani_v2/6.2_savunma_formati.rtf §Plan-Detayı
Migration: db/migrations/0028_defense_session.sql

Pattern: progress_service / manuscript_service.

Akış:
  - upsert_session: yeni oturum veya mevcut güncelle (sahiplik kontrolü).
  - generate_questions: defense_session.jury_members[index] + manuscript_section
    5 bölüm + jüri paper'ları → Gemini Pro structured output → question_pool
    UPDATE (var olan diğer üyelerin soruları korunur).
  - suggest_jury: havuzdan field (theme_id) ile en aktif 5 yazar (Python-side
    aggregation papers.authors JSONB üzerinde).

UNIQUE constraint YOK (0028 schema) — bir proje birden fazla oturum
tutabilir; varsayılan select = en son created_at.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.defense import (
    DefenseQuestion,
    DefenseQuestionsLLMOutput,
    DefenseSession,
    DefenseSessionUpsert,
    GenerateQuestionsResponse,
    JuryMember,
    JurySuggestion,
    SuggestJuryResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_DEFENSE_TABLE = "defense_session"
_MANUSCRIPT_TABLE = "manuscript_section"
_PROJECTS_TABLE = "projects"
_TOPIC_TABLE = "fact_paper_topic"
_PAPERS_TABLE = "papers"

_SUGGEST_JURY_TOP_K = 5
_SUGGEST_THEME_PAPER_LIMIT = 50  # tema içinden top-N paper, sonra yazar agregasyonu
_QUESTIONS_MAX_TOKENS = 3000


# ── Ownership ───────────────────────────────────────────────────────────────


async def _assert_project_owner(user_id: UUID, project_id: UUID) -> None:
    """Sahiplik — projects.user_id eq filter (progress_service ile aynı)."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PROJECTS_TABLE)
            .select("id")
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise LookupError(f"project {project_id} not found or not owned by {user_id}")


async def _fetch_session_owned(
    user_id: UUID, session_id: UUID
) -> dict[str, Any]:
    """Session satırı + sahiplik tek-shot (projects JOIN)."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_DEFENSE_TABLE)
            .select(
                "id,project_id,session_type,scheduled_date,jury_size,title,field,"
                "preferred_lang,jury_members,question_pool,created_at,updated_at"
            )
            .eq("id", str(session_id))
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise LookupError(f"defense_session {session_id} not found")
    row = rows[0]
    await _assert_project_owner(user_id, UUID(str(row["project_id"])))
    return cast(dict[str, Any], row)


# ── 1) Upsert session ───────────────────────────────────────────────────────


def _serialize_jury_members(members: list[JuryMember]) -> list[dict[str, Any]]:
    return [m.model_dump(mode="json") for m in members]


async def upsert_session(
    user_id: UUID, payload: DefenseSessionUpsert
) -> DefenseSession:
    """POST /api/workshop/defense/session.

    `session_id` verilmemişse INSERT; verilmişse mevcut satır UPDATE (sahiplik
    + project_id eşleşmesi doğrulanır).
    """
    await _assert_project_owner(user_id, payload.project_id)
    db = get_supabase_admin()

    row: dict[str, Any] = {
        "project_id": str(payload.project_id),
        "session_type": payload.session_type,
        "scheduled_date": (
            payload.scheduled_date.isoformat() if payload.scheduled_date else None
        ),
        "jury_size": payload.jury_size,
        "title": payload.title,
        "field": payload.field,
        "preferred_lang": payload.preferred_lang,
        "jury_members": _serialize_jury_members(payload.jury_members),
    }

    if payload.session_id is None:

        def _q_insert() -> Any:
            return db.table(_DEFENSE_TABLE).insert(row).execute()

        resp = await supabase_call_async(_q_insert)
        rows = resp.data or []
        if not rows:
            raise RuntimeError(f"{_DEFENSE_TABLE} insert returned empty")
        return DefenseSession.model_validate(rows[0])

    existing = await _fetch_session_owned(user_id, payload.session_id)
    if str(existing["project_id"]) != str(payload.project_id):
        raise PermissionError("session_project_mismatch")

    def _q_update() -> Any:
        return (
            db.table(_DEFENSE_TABLE)
            .update(row)
            .eq("id", str(payload.session_id))
            .execute()
        )

    resp = await supabase_call_async(_q_update)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_DEFENSE_TABLE} update returned empty")
    return DefenseSession.model_validate(rows[0])


# ── 2) Generate questions ───────────────────────────────────────────────────


async def _fetch_manuscript_text(project_id: UUID) -> str:
    """5 bölümün içeriklerini etiketli blok olarak birleştir."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_MANUSCRIPT_TABLE)
            .select("section_type,content")
            .eq("project_id", str(project_id))
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        return ""
    by_type = {r["section_type"]: (r.get("content") or "") for r in rows}
    blocks: list[str] = []
    for stype in ("intro", "methods", "findings", "discussion", "conclusion"):
        content = by_type.get(stype, "").strip()
        if not content:
            continue
        blocks.append(f"[{stype.upper()}]\n{content}")
    return "\n\n".join(blocks)


def _build_questions_prompt(
    session: dict[str, Any],
    jury_index: int,
    manuscript_text: str,
) -> str:
    members_raw = session.get("jury_members") or []
    if not isinstance(members_raw, list) or jury_index >= len(members_raw):
        raise IndexError(f"jury_member_index_out_of_range:{jury_index}")
    member = members_raw[jury_index]

    papers_raw = member.get("found_papers") or []
    paper_lines: list[str] = []
    for p in papers_raw[:10]:
        title = (p.get("title") or "Untitled").strip()
        year = p.get("year") or "n/a"
        pid = p.get("paper_id") or ""
        paper_lines.append(f"- [{pid}] ({year}) {title}")
    paper_block = "\n".join(paper_lines) if paper_lines else "(paper bulunamadı — generic mode)"

    lang = session.get("preferred_lang") or "tr"
    return (
        f"Yayın türü: {session.get('session_type')}\n"
        f"Dil: {lang}\n"
        f"Yayın başlığı: {session.get('title')}\n"
        f"Alan: {session.get('field')}\n\n"
        f"Jüri üyesi (index {jury_index}):\n"
        f"  - İsim: {member.get('name')}\n"
        f"  - Alan: {member.get('field')}\n"
        f"  - Affiliation: {member.get('affiliation') or '(yok)'}\n"
        f"  - Generic fallback: {bool(member.get('generic_fallback'))}\n\n"
        f"Jüri üyesinin paper listesi (top 10):\n{paper_block}\n\n"
        f"Kullanıcı manuscript_section içerikleri:\n---\n"
        f"{manuscript_text or '(manuscript boş — 6.1 doldurulmamış)'}\n---\n\n"
        f"Çıktı: 8-12 soru JSON (schema role module'da)."
    )


def _merge_pool(
    existing: list[Any], new_questions: list[DefenseQuestion], jury_index: int
) -> list[dict[str, Any]]:
    """Aynı jury_member_index için var olan soruları sil, yenilerini ekle."""
    kept = [
        q
        for q in existing
        if isinstance(q, dict) and q.get("jury_member_index") != jury_index
    ]
    appended = [q.model_dump(mode="json") for q in new_questions]
    return [*kept, *appended]


async def generate_questions(
    user_id: UUID, session_id: UUID, jury_member_index: int
) -> GenerateQuestionsResponse:
    """POST /api/workshop/defense/generate-questions.

    Pro tier Gemini + structured output. Var olan diğer üyelerin soruları
    korunur; yalnız bu index'in soruları yeniden üretilip yerleşir.
    """
    session = await _fetch_session_owned(user_id, session_id)
    project_id = UUID(str(session["project_id"]))

    manuscript_text = await _fetch_manuscript_text(project_id)
    prompt = _build_questions_prompt(session, jury_member_index, manuscript_text)

    llm_resp = await llm_call(
        prompt=prompt,
        tier="pro",
        mode="defense_questions",
        structured_output_schema=DefenseQuestionsLLMOutput,
        max_tokens=_QUESTIONS_MAX_TOKENS,
    )
    parsed = llm_resp.parsed_output
    if not isinstance(parsed, DefenseQuestionsLLMOutput):
        raise ValueError("defense_questions_llm_output_invalid")

    fixed_questions = [
        q.model_copy(update={"jury_member_index": jury_member_index})
        for q in parsed.questions
    ]

    existing_pool = session.get("question_pool") or []
    if not isinstance(existing_pool, list):
        existing_pool = []
    merged = _merge_pool(existing_pool, fixed_questions, jury_member_index)

    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_DEFENSE_TABLE)
            .update({"question_pool": merged})
            .eq("id", str(session_id))
            .execute()
        )

    await supabase_call_async(_q)

    return GenerateQuestionsResponse(
        session_id=session_id,
        jury_member_index=jury_member_index,
        questions=fixed_questions,
        total_pool_size=len(merged),
    )


# ── 3) Suggest jury ─────────────────────────────────────────────────────────


async def _fetch_topic_papers(theme_id: str, limit: int) -> list[str]:
    """fact_paper_topic'ten theme_id için top-N paper_id (score DESC)."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_TOPIC_TABLE)
            .select("paper_id,score")
            .eq("theme_id", theme_id)
            .order("score", desc=True)
            .limit(limit)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    return [r["paper_id"] for r in rows if r.get("paper_id")]


async def _fetch_papers_with_authors(
    paper_ids: list[str],
) -> list[dict[str, Any]]:
    if not paper_ids:
        return []
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PAPERS_TABLE)
            .select("paper_id,authors,citations_count")
            .in_("paper_id", paper_ids)
            .execute()
        )

    resp = await supabase_call_async(_q)
    return cast(list[dict[str, Any]], resp.data or [])


def _aggregate_authors(papers: list[dict[str, Any]]) -> list[JurySuggestion]:
    """papers.authors JSONB üzerinde Python-side aggregation.

    Aynı yazar adına denk gelen tüm paper'ları toplar; en aktif (paper_count
    DESC, total_citations DESC) top-5 döndürür.
    """
    by_name: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "name": "",
            "affiliation": None,
            "paper_count": 0,
            "total_citations": 0,
            "top_paper_ids": [],
        }
    )

    for p in papers:
        authors = p.get("authors") or []
        if not isinstance(authors, list):
            continue
        cites = int(p.get("citations_count") or 0)
        pid = p.get("paper_id")
        for a in authors:
            if not isinstance(a, dict):
                continue
            name = (a.get("name") or "").strip()
            if not name:
                continue
            slot = by_name[name]
            if not slot["name"]:
                slot["name"] = name
            if not slot["affiliation"] and a.get("affiliation"):
                slot["affiliation"] = a["affiliation"]
            slot["paper_count"] = int(slot["paper_count"]) + 1
            slot["total_citations"] = int(slot["total_citations"]) + cites
            ids = cast(list[str], slot["top_paper_ids"])
            if pid and len(ids) < 3:
                ids.append(pid)

    ranked = sorted(
        by_name.values(),
        key=lambda s: (-int(s["paper_count"]), -int(s["total_citations"])),
    )
    out: list[JurySuggestion] = []
    for s in ranked[:_SUGGEST_JURY_TOP_K]:
        out.append(
            JurySuggestion(
                name=str(s["name"]),
                affiliation=s["affiliation"],
                paper_count=int(s["paper_count"]),
                total_citations=int(s["total_citations"]),
                top_paper_ids=cast(list[str], s["top_paper_ids"]) or [str(s["name"])],
            )
        )
    return out


async def suggest_jury(
    user_id: UUID, project_id: UUID, theme_id: str
) -> SuggestJuryResponse:
    """GET /api/workshop/defense/suggest-jury — havuzdan en aktif 5 yazar."""
    await _assert_project_owner(user_id, project_id)

    paper_ids = await _fetch_topic_papers(theme_id, _SUGGEST_THEME_PAPER_LIMIT)
    papers = await _fetch_papers_with_authors(paper_ids)
    suggestions = _aggregate_authors(papers)
    return SuggestJuryResponse(
        project_id=project_id, field=theme_id, suggestions=suggestions
    )


__all__ = [
    "generate_questions",
    "suggest_jury",
    "upsert_session",
]
