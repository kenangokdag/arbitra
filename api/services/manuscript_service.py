"""F13-S6 6.1 Yayın İçeriği — manuscript_section CRUD + quality + auto-draft.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S6
RTF:  Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı
Migration: db/migrations/0027_manuscript_section.sql

Pattern: progress_service.py — get_supabase_admin + supabase_call_async +
Python-level sahiplik kontrolü (RLS bypass + projects.user_id JOIN filter).

Akış:
  - get_sections(project_id):
      sahiplik kontrolü → 5 satır (boş slotlar dahil normalize) + gate hesabı.
  - upsert_section(project_id, section_type, content):
      sahiplik → word_count compute → ai_quality_flag NULL'a reset (içerik
      değişti → yeniden değerlendirme gerek) → upsert.
  - evaluate_quality(project_id, section_type):
      içerik çek → cache (ai_quality_flag != NULL) → Gemini Flash structured
      output → DB update.
  - auto_draft(project_id, section_type):
      project_progress.meta'dan kaynak adımları çek → Gemini Flash 1 paragraf
      → DB'ye YAZMA (kullanıcı kabul ederse PUT ile yazar).

Gate (RTF §Plan-Detayı + KULLANIM):
  filled_count = COUNT(content boş değil ve word_count >= 50)
  quality_blocked = ANY(ai_quality_flag == 'sahte')
  gate_open = filled_count >= 3 AND NOT quality_blocked
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.manuscript import (
    AutoDraftResponse,
    GateStatus,
    ManuscriptResponse,
    ManuscriptSection,
    QualityCheckResponse,
    QualityLLMOutput,
    SectionType,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_MANUSCRIPT_TABLE = "manuscript_section"
_PROGRESS_TABLE = "project_progress"
_PROJECTS_TABLE = "projects"

_SECTION_ORDER: tuple[SectionType, ...] = (
    "intro",
    "methods",
    "findings",
    "discussion",
    "conclusion",
)
_SECTION_SET: frozenset[SectionType] = frozenset(_SECTION_ORDER)

_GATE_MIN_WORDS = 50
_GATE_MIN_SECTIONS = 3

# RTF §Plan-Detayı (4): bölüm tipi → kaynak step_id mapping (nav-config.ts).
# 3.4 sentez = curation-4; 3.3 metod = curation-3; 4.4 gap = gapatlas-4;
# 4.5 etki = gapatlas-5; 5.1 advisor özet = authoring-1.
_AUTO_DRAFT_SOURCES: dict[SectionType, list[str]] = {
    "intro": ["curation-4", "gapatlas-4"],
    "methods": ["curation-3"],
    "findings": ["gapatlas-5"],
    "discussion": ["gapatlas-4", "gapatlas-5"],
    "conclusion": ["authoring-1"],
}

_QUALITY_MAX_TOKENS = 200
_AUTO_DRAFT_MAX_TOKENS = 600
_AUTO_DRAFT_EMPTY_TEMPLATE = (
    "Önceki adımlardan yeterli içerik bulunamadı; lütfen bu bölümü manuel "
    "doldurun veya ilgili adımları (3.3 / 3.4 / 4.4 / 4.5 / 5.1) tamamlayın."
)

_WORD_RE = re.compile(r"\S+")


# ── Pure helpers ────────────────────────────────────────────────────────────


def _word_count(text: str) -> int:
    """Whitespace-bazlı kelime sayısı — RTF §Plan-Detayı (2)."""
    return len(_WORD_RE.findall(text))


def _row_to_section(row: dict[str, Any]) -> ManuscriptSection:
    return ManuscriptSection.model_validate(
        {
            "section_type": row["section_type"],
            "content": row.get("content") or "",
            "word_count": row.get("word_count") or 0,
            "ai_quality_flag": row.get("ai_quality_flag"),
            "ai_quality_reason": row.get("ai_quality_reason"),
            "updated_at": row["updated_at"],
        }
    )


def _normalize_sections(
    rows: list[dict[str, Any]], fallback_updated_at: str
) -> list[ManuscriptSection]:
    """5 bölümü sabit sırada döndür; eksik slotları boş satırla doldur.

    Boş slot için updated_at olarak DB'den dönen herhangi bir satırı (ya da
    epoch fallback) kullanırız. UI buraya bakmıyor; sadece schema gereği.
    """
    by_type: dict[str, dict[str, Any]] = {r["section_type"]: r for r in rows}
    out: list[ManuscriptSection] = []
    for stype in _SECTION_ORDER:
        if stype in by_type:
            out.append(_row_to_section(by_type[stype]))
            continue
        out.append(
            ManuscriptSection(
                section_type=stype,
                content="",
                word_count=0,
                ai_quality_flag=None,
                ai_quality_reason=None,
                updated_at=fallback_updated_at,  # type: ignore[arg-type]
            )
        )
    return out


def _compute_gate(sections: list[ManuscriptSection]) -> GateStatus:
    filled = sum(
        1 for s in sections if s.content.strip() and s.word_count >= _GATE_MIN_WORDS
    )
    blocked = any(s.ai_quality_flag == "sahte" for s in sections)
    return GateStatus(
        filled_count=filled,
        gate_open=(filled >= _GATE_MIN_SECTIONS) and not blocked,
        quality_blocked=blocked,
    )


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


# ── 1) GET — list sections + gate ───────────────────────────────────────────


async def get_sections(user_id: UUID, project_id: UUID) -> ManuscriptResponse:
    """GET /api/workshop/manuscript?project_id=... — 5 bölüm + gate."""
    await _assert_project_owner(user_id, project_id)
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_MANUSCRIPT_TABLE)
            .select(
                "section_type,content,word_count,ai_quality_flag,"
                "ai_quality_reason,updated_at"
            )
            .eq("project_id", str(project_id))
            .execute()
        )

    resp = await supabase_call_async(_q)
    raw = resp.data or []
    fallback = raw[0]["updated_at"] if raw else "1970-01-01T00:00:00+00:00"
    sections = _normalize_sections(raw, fallback)
    gate = _compute_gate(sections)
    return ManuscriptResponse(
        project_id=project_id, sections=sections, gate_status=gate
    )


# ── 2) PUT — upsert one section (word_count + quality reset) ────────────────


async def upsert_section(
    user_id: UUID,
    project_id: UUID,
    section_type: SectionType,
    content: str,
) -> ManuscriptSection:
    """PUT /api/workshop/manuscript/{section_type} — content yaz.

    word_count Python-side hesaplanır (whitespace split).
    ai_quality_flag NULL'a sıfırlanır — içerik değişti, yeniden değerlendirme
    gerek (RTF §Plan-Detayı (2c)).
    """
    if section_type not in _SECTION_SET:
        raise ValueError(f"invalid_section_type:{section_type}")
    await _assert_project_owner(user_id, project_id)
    db = get_supabase_admin()

    row: dict[str, Any] = {
        "project_id": str(project_id),
        "section_type": section_type,
        "content": content,
        "word_count": _word_count(content),
        "ai_quality_flag": None,
        "ai_quality_reason": None,
    }

    def _q() -> Any:
        return (
            db.table(_MANUSCRIPT_TABLE)
            .upsert(row, on_conflict="project_id,section_type")
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_MANUSCRIPT_TABLE} upsert returned empty")
    return _row_to_section(rows[0])


# ── 3) POST quality-check — Gemini Flash ok/sahte ────────────────────────────


async def _fetch_one_section(
    project_id: UUID, section_type: SectionType
) -> dict[str, Any] | None:
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_MANUSCRIPT_TABLE)
            .select(
                "section_type,content,word_count,ai_quality_flag,ai_quality_reason"
            )
            .eq("project_id", str(project_id))
            .eq("section_type", section_type)
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    return rows[0] if rows else None


async def evaluate_quality(
    user_id: UUID, project_id: UUID, section_type: SectionType
) -> QualityCheckResponse:
    """POST /api/workshop/manuscript/quality-check.

    Cache: ai_quality_flag NULL değilse LLM çağrılmaz (idempotent — içerik
    değişince upsert_section flag'ı NULL'a resetler).
    İçerik boşsa → 'sahte' + uyarı, LLM çağrılmaz.
    """
    if section_type not in _SECTION_SET:
        raise ValueError(f"invalid_section_type:{section_type}")
    await _assert_project_owner(user_id, project_id)

    row = await _fetch_one_section(project_id, section_type)
    content = (row or {}).get("content") or ""
    if not content.strip():
        return QualityCheckResponse(
            section_type=section_type,
            flag="sahte",
            reason="Bölüm boş; lütfen akademik içerik girin.",
            cache_hit=False,
        )

    cached_flag = (row or {}).get("ai_quality_flag")
    cached_reason = (row or {}).get("ai_quality_reason")
    if cached_flag in ("ok", "sahte") and cached_reason:
        return QualityCheckResponse(
            section_type=section_type,
            flag=cached_flag,
            reason=cached_reason,
            cache_hit=True,
        )

    prompt = (
        f"Bölüm tipi: {section_type}\n\n"
        f"Metin (kullanıcı girdisi):\n---\n{content}\n---\n\n"
        'Çıktı: SADECE JSON {"flag": "ok"|"sahte", "reason": "tek cümle"}'
    )
    llm_resp = await llm_call(
        prompt=prompt,
        tier="flash",
        mode="manuscript_quality",
        structured_output_schema=QualityLLMOutput,
        max_tokens=_QUALITY_MAX_TOKENS,
    )
    parsed = llm_resp.parsed_output
    if not isinstance(parsed, QualityLLMOutput):
        raise ValueError("manuscript_quality_llm_output_invalid")

    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_MANUSCRIPT_TABLE)
            .update(
                {
                    "ai_quality_flag": parsed.flag,
                    "ai_quality_reason": parsed.reason,
                }
            )
            .eq("project_id", str(project_id))
            .eq("section_type", section_type)
            .execute()
        )

    await supabase_call_async(_q)
    return QualityCheckResponse(
        section_type=section_type,
        flag=parsed.flag,
        reason=parsed.reason,
        cache_hit=False,
    )


# ── 4) POST auto-draft — Gemini Flash 1 paragraf ─────────────────────────────


async def _fetch_progress_meta(
    project_id: UUID, step_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Belirli step_id'ler için completed satırların meta JSON'ını döndür."""
    if not step_ids:
        return {}
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PROGRESS_TABLE)
            .select("step_id,status,meta")
            .eq("project_id", str(project_id))
            .in_("step_id", step_ids)
            .execute()
        )

    resp = await supabase_call_async(_q)
    out: dict[str, dict[str, Any]] = {}
    for row in resp.data or []:
        if row.get("status") != "completed":
            continue
        meta = row.get("meta") or {}
        if isinstance(meta, dict) and meta:
            out[row["step_id"]] = meta
    return out


def _format_source_block(meta_by_step: dict[str, dict[str, Any]]) -> str:
    """LLM body'sine sıkıştırılmış bağlam — meta key=val string'leri."""
    if not meta_by_step:
        return ""
    lines: list[str] = []
    for step_id, meta in meta_by_step.items():
        kv = " | ".join(
            f"{k}={str(v)[:240]}" for k, v in meta.items() if v not in (None, "")
        )
        if kv:
            lines.append(f"- {step_id}: {kv}")
    return "\n".join(lines)


async def auto_draft(
    user_id: UUID, project_id: UUID, section_type: SectionType
) -> AutoDraftResponse:
    """POST /api/workshop/manuscript/auto-draft.

    Önceki adımlardan kaynak çek → Gemini Flash → 1 paragraf taslak.
    DB'ye YAZILMAZ; kullanıcı kabul ederse PUT /manuscript/{section_type} ile.
    """
    if section_type not in _SECTION_SET:
        raise ValueError(f"invalid_section_type:{section_type}")
    await _assert_project_owner(user_id, project_id)

    sources = _AUTO_DRAFT_SOURCES[section_type]
    meta_by_step = await _fetch_progress_meta(project_id, sources)
    used_steps = sorted(meta_by_step.keys())

    if not meta_by_step:
        return AutoDraftResponse(
            section_type=section_type,
            draft_content=_AUTO_DRAFT_EMPTY_TEMPLATE,
            source_steps=[],
        )

    body = (
        f"Bölüm: {section_type}\n\n"
        "Önceki adım çıktıları:\n"
        f"{_format_source_block(meta_by_step)}\n\n"
        "Çıktı: 1 paragraf akademik taslak (80-180 kelime)."
    )
    llm_resp = await llm_call(
        prompt=body,
        tier="flash",
        mode="manuscript_auto_draft",
        max_tokens=_AUTO_DRAFT_MAX_TOKENS,
    )
    return AutoDraftResponse(
        section_type=section_type,
        draft_content=llm_resp.text.strip(),
        source_steps=used_steps,
    )


__all__ = [
    "auto_draft",
    "evaluate_quality",
    "get_sections",
    "upsert_section",
]
