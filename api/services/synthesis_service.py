"""F13-S11 3.4 Literatür Sentezi — synthesize service.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
RTF:  Page_Design/Sayfa_Plani_v2/3.4_literatur_sentezi.rtf §Plan-Detayı (2)

Akış:
  1. Proje sahipliği doğrula (projects.user_id JOIN)
  2. paper_ids → papers tablosundan title+abstract+authors+year çek
  3. fact_paper_id_card.topic_profile ile tema dağılımı (>%80 → warning)
  4. Mode-spesifik prompt + Gemini Pro structured output
  5. Cümle-bazlı word-Jaccard faithfulness (RTF cosine 0.6 proxy)
  6. Numaralı references + synthesis_text + total_faithfulness
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, cast
from uuid import UUID

from api.db.supabase_client import get_supabase_admin, supabase_call_async
from api.models.synthesis import (
    SynthesisFlag,
    SynthesisLang,
    SynthesisLLMOutput,
    SynthesisReference,
    SynthesisSentence,
    SynthesizeMode,
    SynthesizeResponse,
)
from api.services.llm_service import call as llm_call

logger = logging.getLogger(__name__)

_FAITHFULNESS_GREEN = 0.6
_FAITHFULNESS_YELLOW = 0.4
_THEME_DOMINANCE_THRESHOLD = 0.8

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_LANG_INSTRUCTION: dict[SynthesisLang, str] = {
    "tr": "Türkçe yaz.",
    "en": "Write in English.",
    "id": "Tulis dalam Bahasa Indonesia.",
}
_MODE_HINT: dict[SynthesizeMode, str] = {
    "neutral": "Mode: NEUTRAL — dengeli, bilgilendirici sentez (~600-800 kelime).",
    "critical": (
        "Mode: CRITICAL — yöntem/bulgu zayıflıklarını, çelişen sonuçları ve "
        "kapatılmamış soruları öne çıkar (~600-800 kelime)."
    ),
    "short": (
        "Mode: SHORT — sıkıştırılmış varyant (~300-400 kelime); her cümle ≥ 2 paper "
        "ile bağlantılı."
    ),
}


def _ref(idx: int) -> str:
    """1-tabanlı index → '01'..'25' rank string."""
    return f"{idx:02d}"


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _jaccard(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _flag_for(score: float) -> SynthesisFlag:
    if score >= _FAITHFULNESS_GREEN:
        return "green"
    if score >= _FAITHFULNESS_YELLOW:
        return "yellow"
    return "red"


def _format_citation(row: dict[str, Any]) -> str:
    """APA-benzeri tek satır referans (papers row → string)."""
    authors_raw = row.get("authors") or []
    names: list[str] = []
    for a in authors_raw[:3]:
        if isinstance(a, dict) and a.get("name"):
            names.append(str(a["name"]))
    if len(authors_raw) > 3:
        names.append("et al.")
    author_str = ", ".join(names) if names else "Anonymous"
    year = row.get("year") or "n.d."
    title = row.get("title") or "Untitled"
    venue = row.get("venue") or ""
    base = f"{author_str} ({year}). {title}."
    if venue:
        base += f" {venue}."
    return base


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


def _fetch_papers(paper_ids: list[str]) -> list[dict[str, Any]]:
    client = get_supabase_admin()
    resp = (
        client.table("papers")
        .select("paper_id,title,abstract,authors,year,venue")
        .in_("paper_id", paper_ids)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _fetch_topic_profiles(paper_ids: list[str]) -> list[dict[str, Any]]:
    client = get_supabase_admin()
    resp = (
        client.table("fact_paper_id_card")
        .select("paper_id,topic_profile")
        .in_("paper_id", paper_ids)
        .execute()
    )
    return cast(list[dict[str, Any]], resp.data or [])


def _theme_warning(profiles: list[dict[str, Any]], lang: SynthesisLang) -> str | None:
    """Dominant tema >%80 ise dilde uyarı döner."""
    weights: dict[str, float] = defaultdict(float)
    total_weight = 0.0
    for row in profiles:
        prof = row.get("topic_profile") or {}
        ids = prof.get("theme_ids") or []
        scores = prof.get("theme_scores") or []
        for tid, score in zip(ids, scores, strict=False):
            if not isinstance(score, int | float):
                continue
            weights[str(tid)] += float(score)
            total_weight += float(score)
    if total_weight <= 0:
        return None
    top_theme, top_weight = max(weights.items(), key=lambda kv: kv[1])
    ratio = top_weight / total_weight
    if ratio < _THEME_DOMINANCE_THRESHOLD:
        return None
    pct = round(ratio * 100, 1)
    if lang == "en":
        return (
            f"Synthesis is dominated by a single theme ({top_theme}: {pct}%); "
            "diversity is low."
        )
    if lang == "id":
        return (
            f"Sintesis didominasi oleh satu tema ({top_theme}: {pct}%); "
            "keragaman rendah."
        )
    return (
        f"Sentez tek temaya dayanıyor ({top_theme}: %{pct}); çeşitlilik düşük."
    )


def _resolve_lang(
    lang_arg: SynthesisLang | None, project_row: dict[str, Any]
) -> SynthesisLang:
    if lang_arg is not None:
        return lang_arg
    proj_lang = project_row.get("language")
    if proj_lang in ("tr", "en", "id"):
        return cast(SynthesisLang, proj_lang)
    return "tr"


def _build_prompt(
    lang: SynthesisLang,
    mode: SynthesizeMode,
    papers: list[dict[str, Any]],
) -> str:
    paper_blocks = "\n\n".join(
        f"[{_ref(i + 1)}] {p.get('title') or 'Untitled'}\n"
        f"Yazarlar: "
        f"{', '.join(a.get('name', '') for a in (p.get('authors') or [])[:6]) or '(bilinmiyor)'}\n"
        f"Yıl: {p.get('year') or 'n/a'} · Venue: {p.get('venue') or 'n/a'}\n"
        f"Abstract: {p.get('abstract') or '(abstract yok)'}"
        for i, p in enumerate(papers)
    )
    target = "300-400" if mode == "short" else "600-800"
    return (
        f"{_LANG_INSTRUCTION[lang]}\n\n"
        f"{_MODE_HINT[mode]}\n\n"
        f"Aşağıdaki {len(papers)} akademik makaleyi sentezleyerek bir akademik "
        f"makalenin literatür inceleme bölümünü yaz. Hedef uzunluk: ~{target} "
        f"kelime. Her cümle citation_indices ile ≥ 1 makaleye bağlanmalı.\n\n"
        f"{paper_blocks}\n\n"
        'Çıktı SADECE JSON: {"sentences": [{"text": str, "citation_indices": [int]}]}'
    )


def _build_sentences(
    llm_out: SynthesisLLMOutput,
    paper_id_by_index: dict[int, str],
    abstract_by_paper_id: dict[str, str],
) -> tuple[list[SynthesisSentence], float]:
    sentences: list[SynthesisSentence] = []
    scores: list[float] = []
    for s in llm_out.sentences:
        cited_ids = [
            paper_id_by_index[i] for i in s.citation_indices if i in paper_id_by_index
        ]
        if not cited_ids:
            sentences.append(
                SynthesisSentence(
                    text=s.text, citations=[], faithfulness_score=0.0, flag="red"
                )
            )
            scores.append(0.0)
            continue
        joined_abs = " ".join(abstract_by_paper_id.get(pid, "") for pid in cited_ids)
        score = _jaccard(s.text, joined_abs)
        sentences.append(
            SynthesisSentence(
                text=s.text,
                citations=cited_ids,
                faithfulness_score=round(score, 4),
                flag=_flag_for(score),
            )
        )
        scores.append(score)
    avg = round(sum(scores) / len(scores), 4) if scores else 0.0
    return sentences, avg


def _compose_text(
    sentences: list[SynthesisSentence], paper_index_by_id: dict[str, int]
) -> str:
    """Cümleleri inline [NN][NN] atıflarıyla birleştir."""
    out: list[str] = []
    for s in sentences:
        tag = "".join(
            f"[{_ref(paper_index_by_id[c])}]"
            for c in s.citations
            if c in paper_index_by_id
        )
        text = s.text.strip()
        if tag and not text.endswith(tag):
            out.append(f"{text} {tag}")
        else:
            out.append(text)
    return " ".join(out)


async def synthesize(
    user_id: UUID,
    project_id: UUID,
    paper_ids: list[str],
    mode: SynthesizeMode,
    lang: SynthesisLang | None,
) -> SynthesizeResponse:
    """Atölye 3.4 sentez orkestrasyonu."""
    project_row = await supabase_call_async(
        lambda: _check_ownership(project_id, user_id), timeout=8.0
    )
    resolved_lang = _resolve_lang(lang, project_row)

    papers = await supabase_call_async(
        lambda: _fetch_papers(paper_ids), timeout=10.0
    )
    if len(papers) < len(paper_ids):
        found = {p["paper_id"] for p in papers}
        missing = [pid for pid in paper_ids if pid not in found]
        raise LookupError(f"papers_not_found:{','.join(missing[:5])}")

    papers_sorted = sorted(papers, key=lambda r: paper_ids.index(r["paper_id"]))
    paper_id_by_index = {i + 1: p["paper_id"] for i, p in enumerate(papers_sorted)}
    paper_index_by_id = {pid: i for i, pid in paper_id_by_index.items()}
    abstract_by_paper_id = {
        p["paper_id"]: (p.get("abstract") or "") for p in papers_sorted
    }

    profiles = await supabase_call_async(
        lambda: _fetch_topic_profiles(paper_ids), timeout=8.0
    )
    warning = _theme_warning(profiles, resolved_lang)

    prompt = _build_prompt(resolved_lang, mode, papers_sorted)
    response = await llm_call(
        prompt,
        tier="pro",
        mode="synthesize_workshop",
        structured_output_schema=SynthesisLLMOutput,
        max_tokens=4000,
    )
    parsed = response.parsed_output
    if not isinstance(parsed, SynthesisLLMOutput):
        raise ValueError("synthesize_llm_output_invalid")

    sentences, total_faith = _build_sentences(
        parsed, paper_id_by_index, abstract_by_paper_id
    )
    references = [
        SynthesisReference(
            index=i + 1,
            paper_id=p["paper_id"],
            citation=_format_citation(p),
        )
        for i, p in enumerate(papers_sorted)
    ]
    synthesis_text = _compose_text(sentences, paper_index_by_id)

    return SynthesizeResponse(
        synthesis_text=synthesis_text,
        sentences=sentences,
        references=references,
        total_faithfulness=total_faith,
        theme_warning=warning,
        mode=mode,
        lang=resolved_lang,
    )


__all__ = ["synthesize"]
