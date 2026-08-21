"""F13-S13 S2 Proje Tamamlama — completion_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
RTF:  Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf

2 fonksiyon:
  1. create_snapshot(...) → adım sinyalleri topla + skor + rozet + LLM yorum
  2. record_feedback(...) → 5-soru feedback JSONB yaz

V1 sınırları:
  - PDF render (mezun rapor) ertelendi; pdf_url NULL kalır.
  - Cron 3-ay-sil F13-S14'te bağlanır; bu service sadece delete_after yazar.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.completion import (
    CompletionBadges,
    CompletionFeedback,
    CompletionSnapshot,
    FeedbackResponse,
    SnapshotResponse,
    StepReview,
    StepReviewLLMOutput,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_TABLE = "project_completion"
_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "engine"
_BADGE_PATH = _ENGINE_ROOT / "completion" / "badge_thresholds.json"
_ONERI_PATH = _ENGINE_ROOT / "completion" / "oneri_kurali.json"


# ── ownership ───────────────────────────────────────────────────────────────


def _verify_project_ownership(project_id: UUID, user_id: UUID) -> None:
    """projects.user_id eşitlik kontrolü."""
    client = get_supabase_admin()
    resp = (
        client.table("projects")
        .select("id")
        .eq("id", str(project_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not (resp.data or []):
        raise LookupError("project_not_found")


# ── engine config ───────────────────────────────────────────────────────────


def _load_badge_config() -> dict[str, Any]:
    if not _BADGE_PATH.exists():
        raise LookupError("badge_thresholds_not_found")
    return cast(dict[str, Any], json.loads(_BADGE_PATH.read_text(encoding="utf-8")))


def _load_oneri_rules() -> dict[str, Any]:
    if not _ONERI_PATH.exists():
        raise LookupError("oneri_kurali_not_found")
    return cast(dict[str, Any], json.loads(_ONERI_PATH.read_text(encoding="utf-8")))


# ── sinyal toplama ──────────────────────────────────────────────────────────


def _count_events_by_page(
    user_id: UUID, project_id: UUID
) -> dict[str, dict[str, int]]:
    """project_event tablo: page_slug → {total, resolved} dict."""
    client = get_supabase_admin()
    resp = (
        client.table("project_event")
        .select("page_slug,resolved_at")
        .eq("user_id", str(user_id))
        .eq("project_id", str(project_id))
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        slug = str(r.get("page_slug", ""))
        out.setdefault(slug, {"total": 0, "resolved": 0})
        out[slug]["total"] += 1
        if r.get("resolved_at"):
            out[slug]["resolved"] += 1
    return out


def _fetch_manuscript_sections(project_id: UUID) -> list[dict[str, Any]]:
    client = get_supabase_admin()
    resp = (
        client.table("manuscript_section")
        .select("section_type,word_count,ai_quality_flag")
        .eq("project_id", str(project_id))
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_defense_session(project_id: UUID) -> dict[str, Any] | None:
    client = get_supabase_admin()
    resp = (
        client.table("defense_session")
        .select("id,scan_results,jury_members,question_pool")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], resp.data or [])
    return rows[0] if rows else None


# ── skor hesaplama ─────────────────────────────────────────────────────────


def _score_event_step(
    events_by_page: dict[str, dict[str, int]], page_slug: str
) -> float:
    """event sayısı + resolved oranı → [0..1] skor. 3+ event = 1.0 baz."""
    counts = events_by_page.get(page_slug)
    if not counts or counts["total"] == 0:
        return 0.0
    base = min(counts["total"] / 3.0, 1.0)
    # resolved oranı küçük bonus (max 0.2)
    resolved_ratio = counts["resolved"] / counts["total"] if counts["total"] else 0
    return min(base + 0.2 * resolved_ratio, 1.0)


def _score_manuscript_step(
    sections: list[dict[str, Any]], min_filled: int, min_words: int
) -> float:
    """6.1 — 5 bölümden kaçı min_filled doluluk + word_count >= min_words?"""
    if not sections:
        return 0.0
    filled = sum(
        1
        for s in sections
        if int(s.get("word_count", 0)) >= min_words
        and s.get("ai_quality_flag") != "sahte"
    )
    return min(filled / max(1, min_filled), 1.0)


def _score_defense_step(session: dict[str, Any] | None) -> float:
    """6.2 — defense_session var mı + jury_members + question_pool dolu mu?"""
    if not session:
        return 0.0
    jury_count = len(cast(list[Any], session.get("jury_members") or []))
    qpool = len(cast(list[Any], session.get("question_pool") or []))
    score = 0.0
    if jury_count > 0:
        score += 0.5
    if qpool > 0:
        score += 0.5
    return score


def _score_scan_step(
    session: dict[str, Any] | None, path: list[str]
) -> float:
    """defense_session.scan_results.<path>.* dolu mu? 0/0.5/1.0 üç-seviye."""
    if not session:
        return 0.0
    cur: Any = session.get("scan_results") or {}
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return 0.0
        cur = cur[key]
    if not cur:
        return 0.0
    return 1.0 if isinstance(cur, dict) and len(cur) >= 2 else 0.5


def _score_jury_decision(session: dict[str, Any] | None) -> float:
    """6.5 — jury_session.decision_band.confidence değeri (0..1)."""
    if not session:
        return 0.0
    scan = cast(dict[str, Any], session.get("scan_results") or {})
    js = cast(dict[str, Any], scan.get("jury_session") or {})
    db = cast(dict[str, Any], js.get("decision_band") or {})
    if not db:
        return 0.0
    conf = db.get("confidence")
    if isinstance(conf, int | float):
        return min(max(float(conf), 0.0), 1.0)
    return 0.0


def _score_step(
    step_cfg: dict[str, Any],
    events_by_page: dict[str, dict[str, int]],
    sections: list[dict[str, Any]],
    defense: dict[str, Any] | None,
) -> float:
    """Step config'e göre sinyal kaynağı seç + skor."""
    src = str(step_cfg.get("signal_source", ""))
    if src == "project_event":
        return _score_event_step(events_by_page, str(step_cfg.get("page_slug", "")))
    if src == "manuscript_section":
        return _score_manuscript_step(
            sections,
            int(step_cfg.get("min_filled_sections", 3)),
            int(step_cfg.get("min_word_count_per_section", 50)),
        )
    if src == "defense_session":
        return _score_defense_step(defense)
    if src == "defense_session.scan_results.individual_check":
        return _score_scan_step(defense, ["individual_check"])
    if src == "defense_session.scan_results.journal_calibration":
        return _score_scan_step(defense, ["journal_calibration"])
    if src == "defense_session.scan_results.jury_session.decision_band":
        return _score_jury_decision(defense)
    return 0.0


def _status_from_score(score: float, basarili_min: float) -> str:
    return "basarili" if score >= basarili_min else "gelistirilmeli"


# ── öneri kuralları ────────────────────────────────────────────────────────


def _evaluate_advice_rules(
    rules_cfg: dict[str, Any], step_statuses: dict[str, str]
) -> list[str]:
    """oneri_kurali.json kurallarını step rozetlerine uygula."""
    advice: list[str] = []
    rules = cast(list[dict[str, Any]], rules_cfg.get("rules", []))
    max_n = int(rules_cfg.get("max_advice_in_snapshot", 3))
    has_any_basarili = "basarili" in step_statuses.values()
    for rule in rules:
        trig_step = str(rule.get("trigger_step", ""))
        trig_status = str(rule.get("trigger_status", ""))
        if trig_step == "__any__":
            if trig_status == "basarili" and has_any_basarili:
                advice.append(str(rule.get("advice", "")))
        else:
            actual = step_statuses.get(trig_step)
            if actual == trig_status:
                advice.append(str(rule.get("advice", "")))
        if len(advice) >= max_n:
            break
    return advice[:max_n]


# ── LLM step yorumları ─────────────────────────────────────────────────────


def _build_step_review_prompt(
    step_reviews_raw: list[dict[str, Any]],
    project_id: UUID,
) -> str:
    """Tek bir Flash çağrısı — tüm adımların yorumları + özet paragraf."""
    rows = "\n".join(
        f"- {r['step_id']} ({r['label']}): "
        f"skor={r['score']:.2f}, durum={r['status']}"
        for r in step_reviews_raw
    )
    return (
        "Aşağıdaki adım skorları + durumlar (basarili / gelistirilmeli) için "
        "her adıma 1 cümle akademik öğretici yorum üret. Yorum yapıcı muhalefet "
        "üslubunda olsun: önce destekle, sonra somut risk + iyileştirme öner. "
        "Mezun olan adımlar için cesaret ver, geliştirilmeli adımlar için "
        "somut tavsiye + sonraki tur ipucu.\n\n"
        f"Proje id: {project_id}\n"
        f"Adım skorları:\n{rows}\n\n"
        "Ayrıca tüm projeye 1 paragraf (~80-150 kelime) genel özet yaz; "
        "güçlü yönü + geliştirme alanını dengeli yansıt.\n\n"
        'Çıktı SADECE JSON: {"reviews":[{"step_id":str,"comment":str}],'
        '"summary_paragraph":str}'
    )


async def _generate_step_comments(
    step_reviews_raw: list[dict[str, Any]],
    project_id: UUID,
) -> tuple[dict[str, str], str]:
    """LLM çağrısı; step_id → comment dict + summary döndür."""
    prompt = _build_step_review_prompt(step_reviews_raw, project_id)
    resp = await llm_call(
        prompt,
        tier="flash",
        mode="completion_step_review",
        structured_output_schema=StepReviewLLMOutput,
        max_tokens=1500,
    )
    parsed = resp.parsed_output
    if not isinstance(parsed, StepReviewLLMOutput):
        raise ValueError("completion_step_review_llm_output_invalid")
    comments = {item.step_id: item.comment for item in parsed.reviews}
    return comments, parsed.summary_paragraph


# ── snapshot persist ───────────────────────────────────────────────────────


def _build_step_reviews(
    badge_cfg: dict[str, Any],
    events_by_page: dict[str, dict[str, int]],
    sections: list[dict[str, Any]],
    defense: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Adım listesi + skor + status; LLM yorum henüz boş."""
    steps_cfg = cast(list[dict[str, Any]], badge_cfg.get("steps", []))
    out: list[dict[str, Any]] = []
    for step in steps_cfg:
        score = _score_step(step, events_by_page, sections, defense)
        thr = float(step.get("basarili_min", 0.6))
        out.append(
            {
                "step_id": str(step["step_id"]),
                "label": str(step["label"]),
                "score": score,
                "status": _status_from_score(score, thr),
            }
        )
    return out


async def create_snapshot(
    user_id: UUID, project_id: UUID
) -> SnapshotResponse:
    """POST /api/completion/snapshot — sinyal topla + skor + LLM yorum + persist."""
    await supabase_call_async(
        lambda: _verify_project_ownership(project_id, user_id), timeout=8.0
    )

    events_by_page = await supabase_call_async(
        lambda: _count_events_by_page(user_id, project_id), timeout=8.0
    )
    sections = await supabase_call_async(
        lambda: _fetch_manuscript_sections(project_id), timeout=8.0
    )
    defense = await supabase_call_async(
        lambda: _fetch_defense_session(project_id), timeout=8.0
    )

    badge_cfg = _load_badge_config()
    rules_cfg = _load_oneri_rules()

    raw_reviews = _build_step_reviews(badge_cfg, events_by_page, sections, defense)
    step_statuses = {r["step_id"]: r["status"] for r in raw_reviews}
    graduate_advice = _evaluate_advice_rules(rules_cfg, step_statuses)

    comments, summary = await _generate_step_comments(raw_reviews, project_id)
    step_reviews = [
        StepReview(
            step_id=r["step_id"],
            label=r["label"],
            score=float(r["score"]),
            status=cast(Any, r["status"]),
            comment=comments.get(r["step_id"], "Bu adım için yorum üretilemedi."),
        )
        for r in raw_reviews
    ]
    basarili_count = sum(1 for r in step_reviews if r.status == "basarili")
    gelistirilmeli_count = len(step_reviews) - basarili_count

    snapshot = CompletionSnapshot(
        step_reviews=step_reviews,
        badges=CompletionBadges(
            basarili=basarili_count, gelistirilmeli=gelistirilmeli_count
        ),
        graduate_advice=graduate_advice,
        summary_paragraph=summary,
    )

    def _upsert() -> Any:
        return (
            get_supabase_admin()
            .table(_TABLE)
            .upsert(
                {
                    "project_id": str(project_id),
                    "user_id": str(user_id),
                    "snapshot": snapshot.model_dump(),
                },
                on_conflict="project_id",
            )
            .execute()
        )

    resp = await supabase_call_async(_upsert, timeout=8.0)
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise RuntimeError("project_completion upsert returned empty")
    row = rows[0]
    return SnapshotResponse(
        completion_id=UUID(str(row["id"])),
        project_id=project_id,
        completed_at=_parse_iso(row.get("completed_at")),
        snapshot=snapshot,
        delete_after=_parse_iso(row.get("delete_after")),
    )


# ── feedback persist ───────────────────────────────────────────────────────


async def record_feedback(
    user_id: UUID, project_id: UUID, feedback: CompletionFeedback
) -> FeedbackResponse:
    """POST /api/feedback/project-completion — 5-soru jsonb UPDATE.

    Snapshot oluşturulmamışsa LookupError. Üst-kat 404.
    """
    await supabase_call_async(
        lambda: _verify_project_ownership(project_id, user_id), timeout=8.0
    )

    def _update() -> Any:
        return (
            get_supabase_admin()
            .table(_TABLE)
            .update(
                {
                    "feedback": feedback.model_dump(),
                    "updated_at": "now()",
                }
            )
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )

    resp = await supabase_call_async(_update, timeout=8.0)
    rows = cast(list[dict[str, Any]], resp.data or [])
    if not rows:
        raise LookupError("completion_not_found_run_snapshot_first")
    row = rows[0]
    return FeedbackResponse(
        completion_id=UUID(str(row["id"])),
        project_id=project_id,
        feedback=feedback,
        updated_at=_parse_iso(row.get("updated_at")),
    )


# ── helpers ────────────────────────────────────────────────────────────────


def _parse_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"invalid_iso_timestamp:{value!r}")


__all__ = [
    "create_snapshot",
    "record_feedback",
]
