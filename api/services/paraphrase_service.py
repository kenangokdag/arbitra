"""F13-S3 5.3 Akademik Dil — paraphrase service (Gemini Flash + sessiz öğrenme).

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S3-P002/P003
RTF: Page_Design/Sayfa_Plani_v2/5.3_akademik_dil_uslup.rtf §Plan-Detayı (3)+(4)
Karar (R6 + Omer pattern): Gemini Flash + prompt mühendisliği (Pro değil, $$$
patlamasını önle). Anlam koruma: word-Jaccard token-overlap (sentence-transformers
modeli yüklemek için lazy default kaldırıldı — hızlı CI + minimal bağımlılık).
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.paraphrase import (
    Decision,
    Lang,
    LangAuto,
    ParaphraseDecisionResponse,
    ParaphraseResponse,
    ParaphraseSentence,
    SectionContext,
)
from api.services.llm_service import LLMServiceError
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_LOG_TABLE = "user_silent_learning_log"
_PROFILE_TABLE = "user_style_profile"

_STYLE_DIR = Path(__file__).resolve().parents[2] / "engine" / "style"
_MEANING_DRIFT_THRESHOLD = 0.55  # Jaccard token overlap — RTF cosine 0.85 proxy
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZĞÜŞİÖÇ])")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@lru_cache(maxsize=3)
def _load_style_rules(lang: Lang) -> dict[str, Any]:
    """engine/style/{lang}.json yükle — lru_cache prompt çağrı maliyeti yok."""
    path = _STYLE_DIR / f"{lang}.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _detect_lang(text: str) -> Lang:
    """Hafif dil tespit: TR diakritik + EN/ID stop-word eşleşmesi.

    langdetect bağımlılığı yerine kural-tabanlı; pilot için yeterli.
    fallback = en.
    """
    sample = text[:1000].lower()
    tr_chars = sum(1 for c in sample if c in "ğüşıöçâî")
    if tr_chars >= 5:
        return "tr"
    id_markers = (" yang ", " dan ", " dengan ", " adalah ", " untuk ")
    if any(m in f" {sample} " for m in id_markers):
        return "id"
    return "en"


def _resolve_lang(lang: LangAuto, text: str) -> Lang:
    if lang == "auto":
        return _detect_lang(text)
    return lang


def _split_sentences(text: str) -> list[str]:
    """Basit cümle ayrıştırma — period/exclaim/question + büyük harf devamı."""
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text)}


def _jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard — anlam koruma proxy.

    Why: sentence-transformers paraphrase-multilingual yüklemek 250MB+ memory +
    cold-start sıkıntı. Jaccard pilot için yeterli güvenli alt sınır.
    """
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _detect_change_type(original: str, proposed: str, rules: dict[str, Any]) -> str:
    """Heuristik change_type — LLM çıktısı meta açıklaması için."""
    orig_low = original.lower()
    prop_low = proposed.lower()
    forbidden = rules.get("forbidden_definitive", [])
    if any(w in orig_low for w in forbidden) and not any(
        w in prop_low for w in forbidden
    ):
        return "definitive_removed"
    hedge_terms = rules.get("hedge_terms", []) or list(
        rules.get("hedge_alternatives", {}).values()
    )
    if any(h in prop_low for h in hedge_terms) and not any(
        h in orig_low for h in hedge_terms
    ):
        return "hedge_added"
    passive = rules.get("preferred_passive_endings", []) + rules.get(
        "passive_voice_triggers", []
    )
    if any(p in prop_low for p in passive) and not any(p in orig_low for p in passive):
        return "passive_voice"
    if len(proposed) < len(original) * 0.85:
        return "shortened"
    if len(proposed) > len(original) * 1.15:
        return "extended"
    return "other"


async def _fetch_style_profile(
    user_id: UUID, lang: Lang
) -> dict[str, Any] | None:
    """user_style_profile satırı (None = ilk kullanım)."""
    db = get_supabase_admin()

    def _q() -> Any:
        return (
            db.table(_PROFILE_TABLE)
            .select("profile, sample_size")
            .eq("user_id", str(user_id))
            .eq("lang", lang)
            .limit(1)
            .execute()
        )

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        return None
    return cast(dict[str, Any], rows[0])


def _build_style_note(profile_row: dict[str, Any] | None) -> str:
    """Stil profili → tek satır LLM hint."""
    if not profile_row:
        return ""
    profile = profile_row.get("profile", {}) or {}
    n = profile_row.get("sample_size", 0)
    if n < 10:
        return ""
    bits: list[str] = []
    pv = profile.get("passive_voice_pref")
    if isinstance(pv, int | float) and pv >= 0.6:
        bits.append("yoğun pasif çatı")
    if isinstance(pv, int | float) and pv <= 0.3:
        bits.append("aktif çatı tercihli")
    hf = profile.get("hedge_term_freq")
    if hf in ("high", "medium", "low"):
        bits.append(f"hedge sıklığı={hf}")
    asl = profile.get("avg_sentence_length")
    if isinstance(asl, int | float) and asl > 0:
        bits.append(f"ort. cümle uzunluğu≈{int(asl)} kelime")
    if not bits:
        return ""
    return f"Kullanıcı tercihi (n={n}): {', '.join(bits)}."


def _build_prompt(
    sentences: list[str],
    rules: dict[str, Any],
    section_context: SectionContext | None,
    style_note: str,
) -> str:
    """LLM prompt'u — cümleler numaralı liste + JSON çıktı sözleşmesi."""
    section_hint = ""
    if section_context:
        section_hint = rules.get("section_hints", {}).get(section_context, "")
    template = rules.get("llm_prompt_template", "")
    instruction = template.format(
        section_hint=f"Bölüm bağlamı: {section_hint}" if section_hint else "",
        user_style_note=style_note,
    )
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(sentences))
    return (
        f"{instruction}\n\n"
        "Yanıtı SADECE şu JSON yapısında ver — code-fence yok, açıklama yok:\n"
        '{"sentences":[{"index":0,"original":"...","proposed":"...","confidence":0.85}]}\n\n'
        f"Cümleler:\n{numbered}"
    )


async def paraphrase_text(
    user_id: UUID,
    project_id: UUID,
    document_text: str,
    lang: LangAuto = "auto",
    section_context: SectionContext | None = None,
) -> ParaphraseResponse:
    """POST /api/workshop/paraphrase — Gemini Flash batch + meaning-drift kontrol.

    1) Dil tespit (auto ise heuristic)
    2) Cümle ayrıştır
    3) Stil profili çek (varsa LLM'e ipucu)
    4) Style rules + prompt'u kur
    5) LLM çağır (Flash)
    6) Word-Jaccard ile anlam-kayması bayrağı
    """
    resolved_lang = _resolve_lang(lang, document_text)
    sentences = _split_sentences(document_text)
    if not sentences:
        return ParaphraseResponse(
            session_id=uuid4(),
            lang=resolved_lang,
            sentences=[],
            total_sentences=0,
            meaning_drift_count=0,
            profile_applied=False,
        )

    rules = _load_style_rules(resolved_lang)
    profile_row = await _fetch_style_profile(user_id, resolved_lang)
    style_note = _build_style_note(profile_row)
    prompt = _build_prompt(sentences, rules, section_context, style_note)

    llm_resp = await llm_call(
        prompt=prompt,
        tier="flash",
        mode="default",
        max_tokens=max(800, len(sentences) * 120),
    )

    try:
        raw = json.loads(_strip_fence(llm_resp.text))
        items = raw.get("sentences", []) if isinstance(raw, dict) else []
    except json.JSONDecodeError as exc:
        logger.exception("paraphrase LLM çıktı JSON parse edilemedi")
        raise LLMServiceError(f"paraphrase JSON parse: {exc}") from exc

    out_sentences: list[ParaphraseSentence] = []
    drift_count = 0
    seen_idx: set[int] = set()
    by_index: dict[int, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        idx_raw = item.get("index")
        if not isinstance(idx_raw, int):
            continue
        by_index[idx_raw] = item

    for i, original in enumerate(sentences):
        item = by_index.get(i, {})
        proposed = str(item.get("proposed") or original).strip()
        confidence_raw = item.get("confidence", 0.7)
        confidence = float(confidence_raw) if isinstance(confidence_raw, int | float) else 0.7
        confidence = max(0.0, min(1.0, confidence))
        sim = _jaccard_similarity(original, proposed)
        drift = sim < _MEANING_DRIFT_THRESHOLD
        if drift:
            drift_count += 1
        change_type_raw = _detect_change_type(original, proposed, rules)
        change_type = cast(Any, change_type_raw)
        out_sentences.append(
            ParaphraseSentence(
                index=i,
                original=original,
                proposed=proposed,
                change_type=change_type,
                confidence=confidence,
                meaning_drift_risk=drift,
                similarity=round(sim, 3),
            )
        )
        seen_idx.add(i)

    return ParaphraseResponse(
        session_id=uuid4(),
        lang=resolved_lang,
        sentences=out_sentences,
        total_sentences=len(sentences),
        meaning_drift_count=drift_count,
        profile_applied=bool(style_note),
    )


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|```\s*$", re.IGNORECASE | re.MULTILINE)


def _strip_fence(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


async def record_decision(
    user_id: UUID,
    session_id: UUID,
    sentence_index: int,
    sentence_original: str,
    sentence_proposed: str,
    decision: Decision,
    edited_text: str | None,
    lang: Lang,
    section_context: SectionContext | None,
    meta: dict[str, Any],
) -> ParaphraseDecisionResponse:
    """POST /api/workshop/paraphrase-decision — user_silent_learning_log INSERT."""
    db = get_supabase_admin()

    row: dict[str, Any] = {
        "user_id": str(user_id),
        "session_id": str(session_id),
        "sentence_original": sentence_original,
        "sentence_proposed": sentence_proposed,
        "decision": decision,
        "edited_text": edited_text,
        "lang": lang,
        "section_context": section_context,
        "meta": {**meta, "sentence_index": sentence_index},
    }

    def _q() -> Any:
        return db.table(_LOG_TABLE).insert(row).execute()

    resp = await supabase_call_async(_q)
    rows = resp.data or []
    if not rows:
        raise RuntimeError(f"{_LOG_TABLE} insert returned empty")
    log_id = UUID(rows[0]["id"])
    return ParaphraseDecisionResponse(logged=True, log_id=log_id)
