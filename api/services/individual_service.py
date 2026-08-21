"""F13-S8 6.3 Bireysel Kontrol — individual_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S8
RTF:  Page_Design/Sayfa_Plani_v2/6.3_bireysel_kontrol.rtf §Plan-Detayı

4 fonksiyon:
  1. load_checklist(doc_type, lang)         → engine/checklist/*.json
  2. upsert_individual_check(...)           → defense_session.individual_check
                                                merge (replace by item_id)
  3. suggest_journals(project_id, field)    → V1 fallback (engine/journals)
  4. generate_personal_feedback(...)        → Flash 1 paragraf

V1 not'u: coherence-check (sentence-transformers) henüz yok — calibration
bound olarak sabaha bırakıldı (overnight raporu).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.individual import (
    ChecklistLang,
    ChecklistResponse,
    ChecklistResponseModel,
    DocType,
    IndividualCheckResponse,
    JournalSuggestion,
    JournalSuggestResponse,
    PersonalFeedbackLLMOutput,
    PersonalFeedbackResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_CHECKLIST_DIR = Path(__file__).resolve().parents[2] / "engine" / "checklist"
_JOURNALS_PATH = (
    Path(__file__).resolve().parents[2] / "engine" / "journals" / "seed.json"
)


# ── 1) load_checklist ───────────────────────────────────────────────────────


def load_checklist(doc_type: DocType, lang: ChecklistLang) -> ChecklistResponseModel:
    """engine/checklist/{doc_type}_{lang}.json yükle; pydantic validate."""
    path = _CHECKLIST_DIR / f"{doc_type}_{lang}.json"
    if not path.exists():
        raise LookupError(f"checklist_not_found:{doc_type}_{lang}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ChecklistResponseModel.model_validate(raw)


# ── 2) upsert_individual_check ──────────────────────────────────────────────


def _fetch_session(session_id: UUID, user_id: UUID) -> dict[str, Any]:
    """defense_session + sahiplik (projects.user_id JOIN)."""
    client = get_supabase_admin()
    resp = (
        client.table("defense_session")
        .select("id,project_id,individual_check")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise LookupError("session_not_found")
    row = rows[0]
    proj_resp = (
        client.table("projects")
        .select("id")
        .eq("id", str(row["project_id"]))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not (proj_resp.data or []):
        raise PermissionError("session_not_owned")
    return row


def _merge_checklist_entry(
    existing: list[dict[str, Any]],
    checklist_id: str,
    item_id: str,
    response: ChecklistResponse,
) -> list[dict[str, Any]]:
    """Aynı (checklist_id, item_id) entry'sini değiştir; gerisini koru."""
    keep = [
        e
        for e in existing
        if not (e.get("checklist_id") == checklist_id and e.get("item_id") == item_id)
    ]
    keep.append(
        {
            "checklist_id": checklist_id,
            "item_id": item_id,
            "response": response,
            "noted_at": datetime.now(UTC).isoformat(),
        }
    )
    return keep


def _count_responses(entries: list[dict[str, Any]]) -> tuple[int, int, int]:
    """(evet, hayir, yapamadim) sayımları."""
    e_n = sum(1 for e in entries if e.get("response") == "evet")
    h_n = sum(1 for e in entries if e.get("response") == "hayir")
    y_n = sum(1 for e in entries if e.get("response") == "yapamadim")
    return e_n, h_n, y_n


def _critical_blocked(
    entries: list[dict[str, Any]], checklist: ChecklistResponseModel
) -> bool:
    """Kritik maddede 'hayir' veya 'yapamadim' varsa True (RTF (7) koruyucu kap)."""
    critical_ids: set[str] = set()
    for cat in checklist.categories:
        for it in cat.items:
            if it.kritik:
                critical_ids.add(it.id)
    for e in entries:
        if e.get("item_id") in critical_ids and e.get("response") in (
            "hayir",
            "yapamadim",
        ):
            return True
    return False


async def upsert_individual_check(
    user_id: UUID,
    session_id: UUID,
    checklist_id: str,
    item_id: str,
    response: ChecklistResponse,
    doc_type: DocType,
    lang: ChecklistLang,
) -> IndividualCheckResponse:
    """Tek cevabı defense_session.individual_check'e merge et + kritik kapı."""
    row = await supabase_call_async(
        lambda: _fetch_session(session_id, user_id), timeout=8.0
    )
    existing = cast(list[dict[str, Any]], row.get("individual_check") or [])
    merged = _merge_checklist_entry(existing, checklist_id, item_id, response)

    def _update() -> Any:
        return (
            get_supabase_admin()
            .table("defense_session")
            .update({"individual_check": merged})
            .eq("id", str(session_id))
            .execute()
        )

    await supabase_call_async(_update, timeout=8.0)

    checklist = load_checklist(doc_type, lang)
    e_n, h_n, y_n = _count_responses(merged)
    blocked = _critical_blocked(merged, checklist)

    return IndividualCheckResponse(
        session_id=session_id,
        total_items_answered=e_n + h_n + y_n,
        evet_count=e_n,
        hayir_count=h_n,
        yapamadim_count=y_n,
        critical_blocked=blocked,
    )


# ── 3) suggest_journals — V1 placeholder ────────────────────────────────────


def _load_seed_journals() -> list[dict[str, Any]]:
    if not _JOURNALS_PATH.exists():
        return []
    raw = json.loads(_JOURNALS_PATH.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], raw.get("journals") or [])


async def suggest_journals(
    user_id: UUID, project_id: UUID, field: str
) -> JournalSuggestResponse:
    """RTF §Plan-Detayı (3) — V1 fallback: dim_journal yok → seed JSON.

    dim_journal Supabase'de canlı değilse boş dönerse fallback_used=True.
    HF dergitarama entegrasyonu V2'ye ertelendi (envanter kanıtı yok).
    """

    def _check() -> Any:
        return (
            get_supabase_admin()
            .table("projects")
            .select("id")
            .eq("id", str(project_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_check, timeout=8.0)
    if not (resp.data or []):
        raise LookupError("project_not_found")

    seeds = _load_seed_journals()
    matched = [
        s for s in seeds
        if not field
        or field.lower() in (s.get("scope_label", "") or "").lower()
    ]
    suggestions: list[JournalSuggestion] = []
    for s in matched[:5]:
        suggestions.append(
            JournalSuggestion(
                journal_id=str(s.get("issn") or s.get("id") or s.get("name", "")),
                name=str(s.get("name") or "Unknown"),
                indices=list(s.get("indices") or []),
                sjr_quartile=s.get("sjr_quartile"),
                scope_match=s.get("scope_match"),
                source="seed_json",
            )
        )

    return JournalSuggestResponse(
        journals=suggestions,
        source_attribution=["engine/journals/seed.json"] if suggestions else [],
        fallback_used=not bool(suggestions),
    )


# ── 4) generate_personal_feedback ───────────────────────────────────────────


def _build_feedback_prompt(
    doc_type: DocType,
    lang: ChecklistLang,
    hayir_items: list[dict[str, Any]],
    yapamadim_items: list[dict[str, Any]],
    manuscript_summary: str | None,
) -> str:
    lang_directive = {
        "tr": "Türkçe yaz.",
        "en": "Write in English.",
    }[lang]
    hayir_block = (
        "\n".join(f"- {i.get('item_id')}: {i.get('soru', '')}" for i in hayir_items)
        or "(yok)"
    )
    yapamadim_block = (
        "\n".join(f"- {i.get('item_id')}: {i.get('soru', '')}" for i in yapamadim_items)
        or "(yok)"
    )
    summary_block = (
        f"\n\nManuscript summary:\n{manuscript_summary.strip()}"
        if manuscript_summary
        else ""
    )
    return (
        f"{lang_directive}\n\n"
        f"doc_type: {doc_type}\n"
        f"Hayır işaretlenen maddeler:\n{hayir_block}\n\n"
        f"Yapamadım işaretlenen maddeler:\n{yapamadim_block}"
        f"{summary_block}\n\n"
        'Çıktı SADECE JSON: '
        '{"feedback_paragraph": str, "weak_areas": [str, ...]}'
    )


async def generate_personal_feedback(
    user_id: UUID,
    project_id: UUID,
    session_id: UUID,
    doc_type: DocType,
    lang: ChecklistLang,
    manuscript_summary: str | None,
) -> PersonalFeedbackResponse:
    """RTF §Plan-Detayı (5) — Flash 1 paragraf zayıf alan yorumu."""
    row = await supabase_call_async(
        lambda: _fetch_session(session_id, user_id), timeout=8.0
    )
    if str(row.get("project_id")) != str(project_id):
        raise PermissionError("session_project_mismatch")

    entries = cast(list[dict[str, Any]], row.get("individual_check") or [])
    checklist = load_checklist(doc_type, lang)
    item_meta: dict[str, dict[str, Any]] = {}
    for cat in checklist.categories:
        for it in cat.items:
            item_meta[it.id] = {"soru": it.soru, "kritik": it.kritik}

    hayir_items = [
        {"item_id": e["item_id"], "soru": item_meta.get(e["item_id"], {}).get("soru", "")}
        for e in entries
        if e.get("response") == "hayir"
    ]
    yapamadim_items = [
        {"item_id": e["item_id"], "soru": item_meta.get(e["item_id"], {}).get("soru", "")}
        for e in entries
        if e.get("response") == "yapamadim"
    ]

    prompt = _build_feedback_prompt(
        doc_type, lang, hayir_items, yapamadim_items, manuscript_summary
    )
    response = await llm_call(
        prompt,
        tier="flash",
        mode="personal_feedback",
        structured_output_schema=PersonalFeedbackLLMOutput,
        max_tokens=600,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, PersonalFeedbackLLMOutput):
        raise ValueError("personal_feedback_llm_output_invalid")

    return PersonalFeedbackResponse(
        session_id=session_id,
        feedback_paragraph=parsed.feedback_paragraph,
        weak_areas=parsed.weak_areas,
    )


__all__ = [
    "generate_personal_feedback",
    "load_checklist",
    "suggest_journals",
    "upsert_individual_check",
]
