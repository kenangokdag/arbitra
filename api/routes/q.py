"""V1 Vitrin rotaları — /api/q (25 mk preview) · /api/q/literature-review · /api/q2.

kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md
HK-1: Pydantic forbid (modeller q.py'de).
HK-3: canlı OpenAlex/Gemini Flash smoke test zorunlu.

Akış (per endpoint):
  Depends(tier_gate) → quota dict (tier/quota_remaining/quota_reset)
                    → 401/403/429 raise edebilir
  → openalex_polite.search_papers / fetch_papers_by_ids / llm_service.call
  → Pydantic response (kota meta dahil)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.tier_gate import Tier, tier_gate
from api.models.q import (
    LiteratureReviewLLM,
    LiteratureReviewRequest,
    LiteratureReviewResponse,
    PaperPreview,
    QRequest,
    QResponse,
    QueryTranslation,
    QueryTranslationLLM,
)
from api.services import llm_service
from api.services.openalex_polite import (
    OpenAlexError,
    fetch_papers_by_ids,
    search_papers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["vitrin"])


# ───── /api/q (anon/authed — 25 makale preview, no LLM) ─────


_Q_LIMIT = 25  # KD-V1-S10-01: tier-bağımsız sabit liste boyutu.


async def _translate_query(query: str) -> QueryTranslation | None:
    """KD-V1-S11-02: kullanıcı sorgusu → İngilizce + dil tespiti.

    Translate fail (timeout, parse hatası, exception) → None döner; caller
    1 query (sadece kullanıcı dili) çalıştırır (KD-V1-S11-04 graceful degrade).
    """
    try:
        resp = await llm_service.call(
            prompt=query,
            tier="flash",
            mode="translate_query",
            structured_output_schema=QueryTranslationLLM,
            max_tokens=200,
        )
    except Exception as exc:
        logger.warning("translate_query llm call failed: %s", exc)
        sentry_sdk.add_breadcrumb(
            category="llm",
            level="warning",
            message="translate_query_call_failed",
            data={"exception_type": type(exc).__name__, "query_len": len(query)},
        )
        return None

    parsed = resp.parsed_output
    if not isinstance(parsed, QueryTranslationLLM):
        logger.warning("translate_query parsed_output not QueryTranslationLLM")
        sentry_sdk.add_breadcrumb(
            category="llm",
            level="warning",
            message="translate_query_parsed_output_missing",
            data={"query_len": len(query), "text_len": len(resp.text or "")},
        )
        return None

    return QueryTranslation(
        original=query,
        detected_lang=parsed.detected_lang,
        english_query=parsed.english_query,
    )


def _dedup_and_rank(
    results_lists: list[list[PaperPreview]], top_k: int
) -> list[PaperPreview]:
    """B-6 sonrası: OpenAlex relevance_score sırasını koru, dedup et, top_k al.

    OpenAlex'ten gelen `papers` listesi `sort=relevance_score:desc` ile sıralı.
    Çift dil aramada (orijinal + EN translate) interleave + ilk-görme öncelikli
    dedup ile her dilden sırayla en alakalı sonuç katılır; ardından OpenAlex'in
    ilgililik sırası bozulmadan top_k kesilir.

    Audit referansı: AUDIT_REPORT.md §11 B-6 (cited_by_count override topical
    relevance'ı eziyordu).
    """
    merged: list[PaperPreview] = []
    seen: set[str] = set()
    # Interleave: lang1[0], lang2[0], lang1[1], lang2[1], ...
    max_len = max((len(lst) for lst in results_lists), default=0)
    for i in range(max_len):
        for papers in results_lists:
            if i >= len(papers):
                continue
            p = papers[i]
            if p.openalex_id in seen:
                continue
            seen.add(p.openalex_id)
            merged.append(p)
            if len(merged) >= top_k:
                return merged
    return merged[:top_k]


@router.post("/q", response_model=QResponse)
async def q(
    req: QRequest,
    quota: Annotated[dict[str, Any], Depends(tier_gate)],
) -> QResponse:
    """Anonim/üye arama — 25 makale liste (KD-V1-S11 çift dil paralel arama).

    KD-V1-S11-01: language filter default kullanılmaz (recall için).
    KD-V1-S11-02: LLM translate → kullanıcı dili + İngilizce paralel.
    KD-V1-S11-03: paralel search + dedup by openalex_id + cited_by_count desc.
    KD-V1-S11-04: translate fail → 1 query (graceful degrade, translation=None).
    """
    translation = await _translate_query(req.query)

    queries: list[str] = [req.query]
    if translation is not None and translation.detected_lang != "en":
        queries.append(translation.english_query)

    results_lists = await asyncio.gather(
        *[
            search_papers(
                q_str,
                limit=_Q_LIMIT,
                year_from=req.year_from,
                year_to=req.year_to,
            )
            for q_str in queries
        ],
        return_exceptions=True,
    )

    successful: list[list[PaperPreview]] = []
    last_exc: BaseException | None = None
    for r in results_lists:
        if isinstance(r, BaseException):
            last_exc = r
            logger.warning("Q openalex query failed: %s", r)
            continue
        successful.append(r)

    if not successful:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "openalex_unavailable"},
        ) from last_exc

    papers = _dedup_and_rank(successful, top_k=_Q_LIMIT)

    return QResponse(
        papers=papers,
        translation=translation,
        quota_remaining=int(quota["quota_remaining"]),
        quota_reset=str(quota["quota_reset"]),
    )


# ───── /api/q/literature-review (akademik makale formatlı sentez) ─────


_ANON_PAPER_LIMIT = 3  # KD-V1-S10-02: anon max 3 makale seçimi.

def _ref(idx: int) -> str:
    """1-indexed → 'NN' rank string ('01', '02', ..., '25')."""
    return f"{idx:02d}"


# M-7: EN/TR asimetri — `lang_line` İngilizce ama gövde Türkçe-only iken LLM
# çoğu zaman gövdenin diline kayıyor ya da empty döndürüyordu. Her dil için
# tam-doldurulmuş ayrı şablon: kullanıcıya gönderilen prompt dış görüntüsü o dilde.
# Audit referansı: AUDIT_REPORT.md §11 M-7 / finding-H-LANG-1.
def _build_review_prompt(lang: str, papers: list[PaperPreview]) -> str:
    """Seçili paper abstract'ları → akademik literatür inceleme bölümü prompt'u."""
    n = len(papers)
    target_words = n * 35  # ~30-40 kelime per kaynak (KD-V1-S10-04 revize)
    ref_first = _ref(1)
    ref_second = _ref(2)
    ref_last = _ref(n)

    if lang == "en":
        paper_blocks = "\n\n".join(
            f"[{_ref(i + 1)}] {p.title}\n"
            f"Authors: {', '.join(p.authors[:6]) or '(unknown)'}\n"
            f"Year: {p.year or 'n/a'} · Venue: {p.venue or 'n/a'}\n"
            f"Abstract: {p.abstract or '(no abstract)'}"
            for i, p in enumerate(papers)
        )
        return (
            "Write in English.\n\n"
            f"Synthesize the following {n} academic papers into the "
            f"**literature review section** of an academic article. Not the "
            "whole article — only the review paragraphs plus a numbered "
            "reference list.\n"
            f"Target length: ~{target_words} words "
            "(~30-40 words / ~2 lines per source).\n\n"
            f"In-text citation format: [{ref_first}], [{ref_second}], ... "
            f"the last paper [{ref_last}]. The references list must include "
            f"every paper from 1 to {n}.\n\n"
            f"{paper_blocks}\n\n"
            'Return JSON: { "content": str, "references": [{"index": int, "citation": str}] }'
        )

    if lang == "id":
        paper_blocks = "\n\n".join(
            f"[{_ref(i + 1)}] {p.title}\n"
            f"Penulis: {', '.join(p.authors[:6]) or '(tidak diketahui)'}\n"
            f"Tahun: {p.year or 'n/a'} · Venue: {p.venue or 'n/a'}\n"
            f"Abstrak: {p.abstract or '(tidak ada abstrak)'}"
            for i, p in enumerate(papers)
        )
        return (
            "Tulis dalam Bahasa Indonesia.\n\n"
            f"Sintesis {n} makalah akademis berikut menjadi **bagian tinjauan "
            "literatur** sebuah artikel akademis. Bukan artikel lengkap — "
            "hanya paragraf tinjauan plus daftar referensi bernomor.\n"
            f"Panjang target: ~{target_words} kata "
            "(~30-40 kata / ~2 baris per sumber).\n\n"
            f"Format kutipan dalam teks: [{ref_first}], [{ref_second}], ... "
            f"makalah terakhir [{ref_last}]. Daftar references harus memuat "
            f"setiap makalah dari 1 sampai {n}.\n\n"
            f"{paper_blocks}\n\n"
            'Kembalikan JSON: { "content": str, "references": [{"index": int, "citation": str}] }'
        )

    # default: tr
    paper_blocks = "\n\n".join(
        f"[{_ref(i + 1)}] {p.title}\n"
        f"Yazarlar: {', '.join(p.authors[:6]) or '(bilinmiyor)'}\n"
        f"Yıl: {p.year or 'n/a'} · Venue: {p.venue or 'n/a'}\n"
        f"Abstract: {p.abstract or '(abstract yok)'}"
        for i, p in enumerate(papers)
    )
    return (
        "Türkçe yaz.\n\n"
        f"Aşağıdaki {n} akademik makaleyi sentezleyerek bir akademik makalenin "
        "**literatür inceleme bölümünü** yaz. Komple makale değil, sadece "
        "inceleme paragrafları + numaralı kaynaklar.\n"
        f"Hedef uzunluk: ~{target_words} kelime "
        "(kaynak başına ~30-40 kelime / ~2 satır).\n\n"
        f"Cümle içi atıf formatı: [{ref_first}], [{ref_second}], ... son makale "
        f"[{ref_last}]. references listesinde 1'den {n}'e kadar her makale yer alsın.\n\n"
        f"{paper_blocks}\n\n"
        'JSON şemasında dön: { "content": str, "references": [{"index": int, "citation": str}] }'
    )


@router.post("/q/literature-review", response_model=LiteratureReviewResponse)
async def literature_review(
    req: LiteratureReviewRequest,
    quota: Annotated[dict[str, Any], Depends(tier_gate)],
) -> LiteratureReviewResponse:
    """Seçilen makalelerden akademik makale formatlı literatür özeti.

    KD-V1-S10-02: Anon max 3 paper_ids; authed max 25.
    KD-V1-S10-04: 4 bölüm + numaralı references (LiteratureReviewLLM).
    """
    is_anon = quota["tier"] == Tier.ANON.value
    if is_anon and len(req.paper_ids) > _ANON_PAPER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "tier_paper_limit",
                "tier": "anon",
                "max_papers": _ANON_PAPER_LIMIT,
                "submitted": len(req.paper_ids),
            },
        )

    try:
        papers = await fetch_papers_by_ids(req.paper_ids)
    except OpenAlexError as exc:
        logger.warning("literature-review openalex by_ids failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "openalex_unavailable"},
        ) from exc

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "no_papers_found", "submitted_ids": req.paper_ids},
        )

    prompt = _build_review_prompt(req.lang, papers)

    parsed: LiteratureReviewLLM | None = None
    last_err: str | None = None
    for attempt in (1, 2):  # 1 retry kapısı (Q1 paterni)
        try:
            resp = await llm_service.call(
                prompt,
                tier="flash",
                mode="vitrin_literature",
                structured_output_schema=LiteratureReviewLLM,
                max_tokens=8000,
            )
        except Exception as exc:
            last_err = f"llm_call_failed:{exc}"
            logger.warning(
                "literature-review llm call attempt=%d failed: %s", attempt, exc
            )
            continue

        candidate = resp.parsed_output
        if not isinstance(candidate, LiteratureReviewLLM):
            last_err = "structured_output_missing"
            logger.warning(
                "literature-review attempt=%d: parsed_output not LiteratureReviewLLM",
                attempt,
            )
            continue

        parsed = candidate
        break

    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "empty_llm_output", "reason": last_err or "unknown"},
        )

    return LiteratureReviewResponse(
        review=parsed,
        quota_remaining=int(quota["quota_remaining"]),
        quota_reset=str(quota["quota_reset"]),
    )


# ───── /api/q2 (V1'de "yakında" — DM-054 sonsuza dek) ─────


@router.post("/q2")
async def q2(
    quota: Annotated[dict[str, Any], Depends(tier_gate)],
) -> dict[str, Any]:
    """V1: yakında — tier_gate 403 üretir, buraya ulaşılmaz (defansif)."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "tier_locked_soon", "soon": True},
    )


__all__ = ["router"]
