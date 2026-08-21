"""F13-S10 6.5 Jüri Simülasyonu — jury_sim_service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S10
RTF:  Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf §Plan-Detayı

5 fonksiyon:
  1. jury_question(...)        → 5 persona paralel Flash
  2. hyde_fanout_rerank(...)   → HyDE üretim + Pinecone fanout + RRF + rerank (graceful)
  3. answer_score(...)         → bge-m3 cosine + heuristic clarity + reaction kalibre
  4. consistency_check(...)    → Flash second-pass conflict pairs
  5. jury_decision_band(...)   → weighted_score → kabul/minor/major/red

V1 sınırları:
  - Pilot validated dataset (Cohen κ ≥0.7) YOK — reaction_thresholds.json placeholder.
  - Cohere rerank-3 API key kanıtı YOK → bge-reranker fallback (mevcut).
  - HyDE fanout Pinecone canlı değilse → empty + fanout_used=False.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.journal_sim import Verdict
from api.models.jury_sim import (
    AnswerScoreRequest,
    AnswerScoreResponse,
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
    ConsistencyOutput,
    HydeChunk,
    HydeFanoutRequest,
    HydeFanoutResponse,
    HydeHypotheticalsOutput,
    JuryDecisionBandRequest,
    JuryDecisionBandResponse,
    JuryPersonaOutput,
    JuryQuestion,
    JuryQuestionRequest,
    JuryQuestionResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "engine"
_PERSONAS_DIR = _ENGINE_ROOT / "personas" / "jury"
_THRESHOLDS_PATH = _ENGINE_ROOT / "jury" / "reaction_thresholds.json"

_PERSONAS: tuple[str, ...] = (
    "canli",
    "anti_tez",
    "yontemci",
    "dis_disiplin",
    "pratisyen",
)


# ── ownership ───────────────────────────────────────────────────────────────


def _fetch_session(session_id: UUID, user_id: UUID) -> dict[str, Any]:
    """defense_session + sahiplik (projects.user_id JOIN)."""
    client = get_supabase_admin()
    resp = (
        client.table("defense_session")
        .select("id,project_id,scan_results")
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


def _merge_scan(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing or {})
    js_existing = cast(dict[str, Any], merged.get("jury_session") or {})
    js_patch = cast(dict[str, Any], patch.get("jury_session") or {})
    if js_patch:
        merged_js = dict(js_existing)
        merged_js.update(js_patch)
        merged["jury_session"] = merged_js
    return merged


async def _persist_scan(session_id: UUID, scan_results: dict[str, Any]) -> None:
    def _update() -> Any:
        return (
            get_supabase_admin()
            .table("defense_session")
            .update({"scan_results": scan_results})
            .eq("id", str(session_id))
            .execute()
        )

    await supabase_call_async(_update, timeout=8.0)


# ── 1) jury_question ────────────────────────────────────────────────────────


def _load_persona_config(key: str) -> dict[str, Any]:
    path = _PERSONAS_DIR / f"{key}.json"
    if not path.exists():
        raise LookupError(f"jury_persona_not_found:{key}")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _load_thresholds() -> dict[str, Any]:
    if not _THRESHOLDS_PATH.exists():
        raise LookupError("reaction_thresholds_not_found")
    return cast(dict[str, Any], json.loads(_THRESHOLDS_PATH.read_text(encoding="utf-8")))


def _build_jury_prompt(
    persona_cfg: dict[str, Any], manuscript_text: str, lang: str
) -> str:
    focus = ", ".join(persona_cfg.get("question_focus", []))
    lang_directive = "Türkçe yaz." if lang == "tr" else "Write in English."
    return (
        f"{lang_directive}\n\n"
        f"Persona seed: {persona_cfg.get('prompt_seed', '')}\n"
        f"Question focus: {focus}\n"
        f"Question count target: {persona_cfg.get('question_count', 4)}\n"
        f"Chain depth max: {persona_cfg.get('chain_max_depth', 2)}\n\n"
        f"Manuscript:\n```\n{manuscript_text}\n```\n\n"
        "Çıktı SADECE JSON: "
        '{"questions":[{"persona":str,"idx":int,"text":str,'
        '"depth":1|2,"parent_idx":int|null,"anchor":str|null}]}'
    )


def _trim_jury_depth(payload: JuryPersonaOutput) -> JuryPersonaOutput:
    safe = [q for q in payload.questions if q.depth <= 2]
    return payload.model_copy(update={"questions": safe})


async def _call_jury_persona(
    persona_key: str, manuscript_text: str, lang: str, idx_offset: int
) -> JuryPersonaOutput:
    cfg = _load_persona_config(persona_key)
    prompt = _build_jury_prompt(cfg, manuscript_text, lang)
    response = await llm_call(
        prompt,
        tier="flash",
        mode=f"jury_{persona_key}",
        structured_output_schema=JuryPersonaOutput,
        max_tokens=900,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, JuryPersonaOutput):
        raise ValueError(f"jury_{persona_key}_llm_output_invalid")
    trimmed = _trim_jury_depth(parsed)
    reindexed = []
    for i, q in enumerate(trimmed.questions):
        reindexed.append(
            q.model_copy(
                update={
                    "persona": cast(Any, persona_key),
                    "idx": idx_offset + i,
                    "parent_idx": None if q.depth == 1 else (idx_offset + i - 1),
                }
            )
        )
    return trimmed.model_copy(update={"questions": reindexed})


async def jury_question(
    user_id: UUID, req: JuryQuestionRequest
) -> JuryQuestionResponse:
    """5 persona paralel Flash; scan_results.jury_session.questions UPDATE."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    if str(row.get("project_id")) != str(req.project_id):
        raise PermissionError("session_project_mismatch")

    persona_results = await asyncio.gather(
        *(
            _call_jury_persona(p, req.manuscript_text, req.lang, idx_offset=i * 10)
            for i, p in enumerate(_PERSONAS)
        )
    )

    all_questions: list[JuryQuestion] = []
    for output in persona_results:
        all_questions.extend(output.questions)

    thresholds = _load_thresholds()
    timer = int(thresholds.get("answer_timeout_default_seconds", 60))

    scan = cast(dict[str, Any], row.get("scan_results") or {})
    patch = {
        "jury_session": {
            "questions": [q.model_dump() for q in all_questions],
            "generated_at": datetime.now(UTC).isoformat(),
        }
    }
    await _persist_scan(req.session_id, _merge_scan(scan, patch))

    return JuryQuestionResponse(
        session_id=req.session_id,
        questions=all_questions,
        active_idx=all_questions[0].idx if all_questions else 0,
        timer_seconds=timer,
    )


# ── 2) hyde_fanout_rerank ───────────────────────────────────────────────────


def _build_hyde_prompt(question_text: str, lang: str) -> str:
    lang_directive = "Türkçe yaz." if lang == "tr" else "Write in English."
    return (
        f"{lang_directive}\n\n"
        f"Jüri sorusu:\n{question_text}\n\n"
        "Bu soruya akademik 5 farklı hipotetik MÜKEMMEL cevap üret. Her cevap "
        "farklı bakış/yöntem/sonuç vurgusuyla, 30-100 kelime, soyut+kavramsal "
        "(belirli paper/yıl/yazar UYDURMA). key_concepts: 5-10 anahtar kavram.\n\n"
        'Çıktı SADECE JSON: {"hypotheticals":[str,...],"key_concepts":[str,...]}'
    )


async def _pinecone_fanout(
    hypotheticals: list[str], project_id: UUID
) -> tuple[list[HydeChunk], bool]:
    """Pinecone fanout — V1: graceful fallback, canlı değilse empty.

    Pinecone canlı entegrasyonu V1-S15+ sonrası bağlanır; şu an
    pool_router._QueryEncoder lazy-load yeterli ancak yeni endpoint için
    namespace seçimi+chunk schema henüz tam belirli değil.
    """
    try:
        from api.config import get_settings

        s = get_settings()
        if not getattr(s, "PINECONE_API_KEY", None):
            return [], False
    except Exception:
        return [], False
    # V1: fanout entegrasyonu V2'ye ertelendi (chunk-level index + Cohere
    # rerank-3 billing kanıtı bekleniyor). Boş + fanout_used=False.
    return [], False


def _detect_missing_concepts(
    key_concepts: list[str], manuscript_text: str | None
) -> list[str]:
    if not manuscript_text:
        return []
    text_lower = manuscript_text.lower()
    missing = [c for c in key_concepts if c.strip() and c.lower() not in text_lower]
    return missing[:20]


async def hyde_fanout_rerank(
    user_id: UUID, req: HydeFanoutRequest
) -> HydeFanoutResponse:
    """HyDE 5 hipotetik üret + Pinecone fanout (V1 graceful) + missing concept tespit."""
    # Ownership: project_id'nin user'a ait olduğunu doğrula
    def _check_project() -> Any:
        return (
            get_supabase_admin()
            .table("projects")
            .select("id")
            .eq("id", str(req.project_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_check_project, timeout=8.0)
    if not (resp.data or []):
        raise LookupError("project_not_found")

    response = await llm_call(
        _build_hyde_prompt(req.question_text, req.lang),
        tier="flash",
        mode="jury_hyde",
        structured_output_schema=HydeHypotheticalsOutput,
        max_tokens=700,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, HydeHypotheticalsOutput):
        raise ValueError("jury_hyde_llm_output_invalid")

    rerank_top, fanout_used = await _pinecone_fanout(
        parsed.hypotheticals, req.project_id
    )
    missing = _detect_missing_concepts(parsed.key_concepts, req.manuscript_text)

    return HydeFanoutResponse(
        hyde_hypotheticals=parsed.hypotheticals,
        rerank_top=rerank_top,
        missing_concepts=missing,
        fanout_used=fanout_used,
        rerank_used=False,
    )


# ── 3) answer_score ─────────────────────────────────────────────────────────


_SENTENCE_END = re.compile(r"[\.!?…]\s*$")
_CITATION_RE = re.compile(r"\b[A-Z][a-zA-Zığşçöü]+,?\s+\d{4}\b")


def _clarity_score(answer: str) -> float:
    """Heuristic: cümle tamlığı + uzunluk + atıf izi (regex)."""
    if not answer.strip():
        return 0.0
    score = 0.0
    if _SENTENCE_END.search(answer.strip()):
        score += 0.4
    word_count = len(answer.split())
    if word_count >= 30:
        score += 0.4
    elif word_count >= 10:
        score += 0.2
    if _CITATION_RE.search(answer):
        score += 0.2
    return min(score, 1.0)


def _depth_score_from_hypotheticals(
    answer: str, hypotheticals: list[str]
) -> float:
    """Cevap kaç hipotetik kavramı içeriyor (basit token overlap V1)."""
    if not hypotheticals or not answer.strip():
        return 0.0
    answer_tokens = set(_tokenize(answer))
    matched = 0
    for h in hypotheticals:
        h_tokens = set(_tokenize(h))
        if h_tokens and len(h_tokens & answer_tokens) / max(1, len(h_tokens)) >= 0.15:
            matched += 1
    return min(matched / max(1, len(hypotheticals)), 1.0)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"\w{3,}", text)]


def _evidence_coverage(
    answer: str, hyde_top: list[HydeChunk]
) -> float:
    """V1 token-overlap heuristic; sentence-transformers embed entegrasyonu V2'de.

    bge-m3 cosine kalibrasyonu pilot dataset gerektirir (RTF (2)); placeholder
    olarak top chunk cümleleri ile token overlap kullanırız.
    """
    if not hyde_top or not answer.strip():
        return 0.0
    answer_tokens = set(_tokenize(answer))
    scores: list[float] = []
    for ch in hyde_top:
        ch_tokens = set(_tokenize(ch.sentence))
        if not ch_tokens:
            continue
        scores.append(len(ch_tokens & answer_tokens) / len(ch_tokens))
    if not scores:
        return 0.0
    scores.sort(reverse=True)
    top3 = scores[:3]
    return min(sum(top3) / len(top3), 1.0)


def _classify_reaction(
    weighted: float, thresholds: dict[str, Any]
) -> str:
    wst = cast(dict[str, float], thresholds.get("weighted_sum_thresholds", {}))
    sat = float(wst.get("satisfied_min", 0.65))
    diss = float(wst.get("dissatisfied_max", 0.35))
    if weighted >= sat:
        return "satisfied"
    if weighted < diss:
        return "dissatisfied"
    return "probing"


async def answer_score(
    user_id: UUID, req: AnswerScoreRequest
) -> AnswerScoreResponse:
    """Multi-dim rubric → jury reaction; scan_results.jury_session güncelle."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    thresholds = _load_thresholds()
    weights = cast(dict[str, float], thresholds.get("weights", {}))

    evidence = _evidence_coverage(req.user_answer, req.hyde_top)
    depth = _depth_score_from_hypotheticals(req.user_answer, req.hyde_hypotheticals)
    clarity = _clarity_score(req.user_answer)

    if req.answer_seconds <= 0 and not req.user_answer.strip():
        evidence = 0.0
        depth = 0.0
        clarity = 0.0

    w_e = float(weights.get("evidence_coverage", 0.5))
    w_d = float(weights.get("depth_score", 0.3))
    w_c = float(weights.get("clarity_score", 0.2))
    weighted = min(1.0, max(0.0, w_e * evidence + w_d * depth + w_c * clarity))

    reaction = _classify_reaction(weighted, thresholds)
    missing = [c for c in req.key_concepts if c.lower() not in req.user_answer.lower()]
    follow_up = reaction == "probing" and bool(missing)

    scan = cast(dict[str, Any], row.get("scan_results") or {})
    jury_session = cast(dict[str, Any], scan.get("jury_session") or {})
    questions = cast(list[dict[str, Any]], jury_session.get("questions") or [])
    for q in questions:
        if int(q.get("idx", -1)) == req.question_idx:
            q.update(
                {
                    "user_answer": req.user_answer,
                    "answer_seconds": req.answer_seconds,
                    "evidence_coverage": evidence,
                    "depth_score": depth,
                    "clarity_score": clarity,
                    "weighted_score": weighted,
                    "jury_reaction": reaction,
                    "missing_concepts": missing[:20],
                    "answered_at": datetime.now(UTC).isoformat(),
                }
            )
            break

    jury_session["questions"] = questions
    scan["jury_session"] = jury_session
    await _persist_scan(req.session_id, scan)

    return AnswerScoreResponse(
        session_id=req.session_id,
        question_idx=req.question_idx,
        evidence_coverage=evidence,
        depth_score=depth,
        clarity_score=clarity,
        weighted_score=weighted,
        jury_reaction=cast(Any, reaction),
        missing_concepts=missing[:20],
        follow_up_triggered=follow_up,
    )


# ── 4) consistency_check ────────────────────────────────────────────────────


async def consistency_check(
    user_id: UUID, req: ConsistencyCheckRequest
) -> ConsistencyCheckResponse:
    """Flash second-pass tüm cevapları al; çelişen çiftleri raporla."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    scan = cast(dict[str, Any], row.get("scan_results") or {})
    jury_session = cast(dict[str, Any], scan.get("jury_session") or {})
    questions = cast(list[dict[str, Any]], jury_session.get("questions") or [])
    answered = [q for q in questions if q.get("user_answer")]
    if len(answered) < 2:
        return ConsistencyCheckResponse(
            session_id=req.session_id,
            conflicts=[],
            summary="Çelişki taraması için yeterli cevaplı soru yok.",
        )

    qa_block = "\n".join(
        f"[{q['idx']}] Soru: {q.get('text','')}\n   Cevap: {q.get('user_answer','')}"
        for q in answered
    )
    prompt = (
        "Aşağıdaki soru-cevap çiftlerinde semantik olarak çelişen çiftleri tespit et. "
        "Üslup farkı değil ANLAM çelişkisi.\n\n"
        f"{qa_block}\n\n"
        'Çıktı SADECE JSON: {"conflicts":[{"q_idx_a":int,"q_idx_b":int,'
        '"conflict_text":str}],"summary":str}'
    )
    response = await llm_call(
        prompt,
        tier="flash",
        mode="jury_consistency",
        structured_output_schema=ConsistencyOutput,
        max_tokens=800,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, ConsistencyOutput):
        raise ValueError("consistency_llm_output_invalid")

    jury_session["consistency_check"] = {
        "conflicts": [c.model_dump() for c in parsed.conflicts],
        "summary": parsed.summary,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    scan["jury_session"] = jury_session
    await _persist_scan(req.session_id, scan)

    return ConsistencyCheckResponse(
        session_id=req.session_id,
        conflicts=parsed.conflicts,
        summary=parsed.summary,
    )


# ── 5) jury_decision_band ───────────────────────────────────────────────────


def _predict_band(
    avg_weighted: float, conflict_count: int
) -> tuple[Verdict, float, str]:
    """V1 heuristic band map; pilot validated rubric V2'de override eder."""
    score = max(0.0, avg_weighted - 0.05 * conflict_count)
    if score >= 0.75:
        return "accept", min(1.0, score), "Cevaplar tutarlı + yüksek kanıt-kapsamı."
    if score >= 0.6:
        return (
            "minor",
            score,
            "Çoğu cevap doyurucu; küçük düzeltmelerle savunma kabul edilebilir.",
        )
    if score >= 0.4:
        return (
            "major",
            score,
            "Birkaç temel boşluk var; majör revizyon önerilir.",
        )
    return (
        "reject",
        max(0.05, score),
        "Cevap kanıt-kapsamı + tutarlılık eşik altı; ek hazırlık gerekli.",
    )


async def jury_decision_band(
    user_id: UUID, req: JuryDecisionBandRequest
) -> JuryDecisionBandResponse:
    """Toplu weighted_score + tutarlılık penalty → verdict band."""
    row = await supabase_call_async(
        lambda: _fetch_session(req.session_id, user_id), timeout=8.0
    )
    scan = cast(dict[str, Any], row.get("scan_results") or {})
    jury_session = cast(dict[str, Any], scan.get("jury_session") or {})
    questions = cast(list[dict[str, Any]], jury_session.get("questions") or [])
    scored = [
        float(q["weighted_score"])
        for q in questions
        if "weighted_score" in q and isinstance(q.get("weighted_score"), int | float)
    ]
    avg = sum(scored) / len(scored) if scored else 0.0
    conflicts = cast(
        list[dict[str, Any]],
        cast(dict[str, Any], jury_session.get("consistency_check") or {}).get(
            "conflicts"
        )
        or [],
    )
    prediction, confidence, advice = _predict_band(avg, len(conflicts))

    score_summary = {
        "answered_count": float(len(scored)),
        "avg_weighted_score": avg,
        "conflict_count": float(len(conflicts)),
    }
    jury_session["decision_band"] = {
        "prediction": prediction,
        "confidence": confidence,
        "score_summary": score_summary,
        "advice": advice,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    scan["jury_session"] = jury_session
    await _persist_scan(req.session_id, scan)

    return JuryDecisionBandResponse(
        session_id=req.session_id,
        prediction=prediction,
        confidence=confidence,
        score_summary=score_summary,
        advice=advice,
    )


__all__ = [
    "answer_score",
    "consistency_check",
    "hyde_fanout_rerank",
    "jury_decision_band",
    "jury_question",
]
