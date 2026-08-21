"""F14-S4 — hakemlik ORKESTRASYON motoru (yazar + eleştirenler + editör).

KAVRAM (Omer direktifi): bir ajan raporu YAZAR, diğerleri ELEŞTİRİR, editör
SENTEZLER. Stanford kalitesinin sırrı tek-geçiş değil, çekişmeli rafine.

Akış (1 tur, parametrik):
  (a) writer   → mode="review_writer", tier="pro"  → DraftReport taslağı
  (b) critics  → asyncio.gather PARALEL:
         skeptik / yontemci / sempatik (mevcut reviewer_* modları) +
         citation_critic + novelty_critic  → her biri Critique
  (c) editor   → mode="review_editor", tier="pro" → nihai DraftReport
  (d) montaj   → DraftReport + EvidencePack + ReviewProvenance → ReviewReport

KANUN:
  - KANIT PAKETİ promptlara açıkça serialize edilir; LLM olgu uyduramaz (HK-5).
  - Çıpasız (grounded=false) iddiayı editör SİLER; pipeline bunu prompt'la
    zorlar, ek olarak ham hesapta da görünür kılar (deterministik özet).
  - Hata-yutma YOK (observability canon): writer/editor LLM hatası → yükselt.
    Tek bir eleştirmen düşerse pipeline devam eder ama rapora DÜRÜST not düşer.
  - provenance.judgment_reproducible=False (HK-6): LLM yargısı bit-kararlı değil.

HK-1: tüm ara şemalar extra="forbid".
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from api.models.review import (
    Critique,
    DetailedComment,
    DimensionScore,
    EvidencePack,
    ExecutiveVerdict,
    GroupedPoints,
    Manuscript,
    ReviewLang,
    ReviewMode,
    ReviewProvenance,
    ReviewReport,
    Verdict,
)
from api.services.llm_service import LLMServiceError, call
from engine.academic.council import build_council
from engine.academic.evidence_context import serialize_evidence_pack
from engine.academic.hivemind_metrics import compute_critic_agreement

logger = logging.getLogger(__name__)

ENGINE_VERSION = "f14-s4"

# Etik guardrail (R-4). İki dil seviyesi: editör modunda GÜÇLÜ + zorunlu,
# yazar modunda hafif disclaimer. Editör modu yayımlanmamış 3. taraf makaleyi
# inceler → gizlilik + insan-karar dili belirgin olmalı.
_ETHICS_NOTICE_EDITOR = (
    "Bu otomatik değerlendirme YOL GÖSTERİCİDİR; insan hakemin ve editör "
    "kararının yerine GEÇMEZ. Yayın kararı sizindir. Gizlilik sorumluluğu "
    "sizdedir: yayımlanmamış makale gizli tutulmalı, üçüncü kişilerle "
    "paylaşılmamalıdır. Bu aracı kullanmadan önce derginizin/konferansınızın "
    "LLM-hakemlik politikasını kontrol edin; bazı dergiler otomatik "
    "değerlendirme kullanımını sınırlar veya yasaklar."
)
_ETHICS_NOTICE_AUTHOR = (
    "Bu otomatik değerlendirme yol göstericidir; insan hakemin yerine geçmez. "
    "Göndereceğiniz dergi/konferansın değerlendirme politikasını kontrol edin."
)


def _ethics_notice(mode: ReviewMode) -> str:
    return _ETHICS_NOTICE_EDITOR if mode == "editor" else _ETHICS_NOTICE_AUTHOR


# Editör-spesifik prompt çerçeveleri (mode parametresiyle koşullandırılır;
# YENİ persona modu EKLENMEZ — review_writer/review_editor briefleri korunur,
# user-prompt'a editör-yönelimli yönerge eklenir).
_EDITOR_WRITER_FRAME = (
    "EDİTÖR MODU (dergi/editör tarafı): Bu rapor bir YAZARA öğüt için değil, "
    "bir EDİTÖRE KARAR DESTEĞİ için yazılıyor. Tonu editöre-rapor yap "
    "(yazara-öğüt değil). Hakem-bulma/atama tavsiyesi VERME; yalnız makaleyi "
    "değerlendir. overall_assessment'i editörün hızlı okuyabileceği, "
    "karar-odaklı bir dille yaz (savunulabilir, gerekçeli)."
)
_EDITOR_EDITOR_FRAME = (
    "EDİTÖR MODU (dergi/editör tarafı): Nihai raporu bir EDİTÖRE KARAR DESTEĞİ "
    "olarak sentezle. ZORUNLU EK: 'editor_digest' alanını doldur — kısa "
    "(2-4 cümle), karar-odaklı üst-özet: (a) yayın kararı önerisi "
    "(accept/minor/major/reject) verdict ile tutarlı, (b) güven düzeyi "
    "(yüksek/orta/düşük) ve gerekçesi, (c) kararın 'neden'i tek-iki cümlede "
    "(en kritik güçlü/zayıf yön + KANIT PAKETİ'ndeki belirleyici olgu). "
    "Editör digesti, uzun yazar-geri-bildirimi DEĞİL; editörün 10 saniyede "
    "okuyacağı karar gerekçesidir. Hakem-atama tavsiyesi YOK."
)

_PERSONA_DIR = Path(__file__).resolve().parents[2] / "engine" / "personas" / "review"

# Eleştirmen mode → CriticKey eşlemesi (paralel geçiş).
# critic_skeptik/yontemci/sempatik (F14-S4, Critique şeması) — DİKKAT:
# reviewer_skeptik/sempatik/yontemci DEĞİL; o mode'lar journal_sim_service'in
# F13 "dergi simülasyonu" özelliğine ait, farklı bir şema (ReviewerPersonaOutput/
# questions[]) bekler. Aynı isim aynı ROLE_MODULES brief'i çeker ama farklı
# structured_output_schema ile çağrılırsa LLM hangi şekli üreteceğini bilemez
# (2026-08-04'te bulunan gerçek bug — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md).
_CRITIC_MODES: tuple[tuple[str, str], ...] = (
    ("critic_skeptik", "skeptik"),
    ("critic_yontemci", "yontemci"),
    ("critic_sempatik", "sempatik"),
    ("citation_critic", "citation_critic"),
    ("novelty_critic", "novelty_critic"),
)


# --- ara şemalar (orchestration-local, extra=forbid) ------------------------


class _DraftReport(BaseModel):
    """Writer + editor'ün structured çıktısı (ReviewReport'un yargı çekirdeği)."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    strengths: list[GroupedPoints] = Field(default_factory=list)
    weaknesses: list[GroupedPoints] = Field(default_factory=list)
    detailed_comments: list[DetailedComment] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    overall_assessment: str
    verdict: Verdict
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    editor_digest: str | None = None  # yalnız editör modunda editör doldurur


# --- persona versiyonu ------------------------------------------------------


def _persona_versions() -> str:
    """review/*.json version alanlarını birleştirip provenance dizesi üret.

    Dosya okunamazsa sessiz geçmez — uyarı loglar, "unknown" damgalar (HK-6).
    """
    parts: list[str] = []
    for name in ("writer", "citation_critic", "novelty_critic", "editor"):
        path = _PERSONA_DIR / f"{name}.json"
        try:
            data = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
            parts.append(f"{name}={data.get('version', 'unknown')}")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("persona version read failed (%s): %s", path, exc)
            parts.append(f"{name}=unknown")
    return ", ".join(parts)


# --- KANIT PAKETİ serileştirme (LLM uydurmasın diye olgular açık) ----------


def _serialize_manuscript(ms: Manuscript) -> str:
    """Manuscript → prompt bloğu (künye + metin; metin uzunsa kırpılır)."""
    meta = ms.meta
    head = [
        "MAKALE:",
        f"  Başlık: {meta.title or '(başlık yok)'}",
        f"  Dil: {meta.language}, kelime≈{meta.word_count}, "
        f"referans={meta.reference_count}",
    ]
    if meta.abstract:
        head.append(f"  Özet: {meta.abstract}")
    if meta.section_titles:
        head.append(f"  Bölümler: {', '.join(meta.section_titles)}")
    if meta.parse_warnings:
        head.append(f"  Parse uyarıları: {'; '.join(meta.parse_warnings)}")
    body = ms.full_text.strip()
    head.append("  Tam metin:")
    head.append(body)
    return "\n".join(head)


def _serialize_draft(draft: _DraftReport) -> str:
    """Taslak → eleştirmen/editör prompt bloğu (JSON, eksiksiz)."""
    return "HAKEM TASLAĞI (JSON):\n" + draft.model_dump_json(indent=2)


def _serialize_critiques(critiques: list[Critique]) -> str:
    """Eleştirmen raporları → editör prompt bloğu (JSON)."""
    if not critiques:
        return "ELEŞTİRMEN RAPORLARI: yok."
    payload = [c.model_dump() for c in critiques]
    return "ELEŞTİRMEN RAPORLARI (JSON):\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )


def serialize_executive_verdict(verdict: ExecutiveVerdict) -> str:
    """ExecutiveVerdict (risk_radar'a dayalı, deterministik) → editör prompt
    bloğu. 2026-08-07: review_service, run_orchestration'ı ÇAĞIRMADAN ÖNCE
    assess_manuscript'in Finding'lerinden bu deterministik değerlendirmeyi
    hesaplar ve editor'a geçer — editor'ın verdict alanı sonradan BU kararla
    override edileceği için, prose'unun (özellikle overall_assessment) bu
    kararla TUTARLI olması gerekir (guardian bulgusu: aksi halde rapor
    kendiyle çelişebilirdi)."""
    risks = "; ".join(verdict.top_fatal_risks) or "yok"
    return (
        "DETERMİNİSTİK RİSK DEĞERLENDİRMESİ (Finding severity-sayımına dayalı, "
        "LLM yargısı DEĞİL):\n"
        f"  Önerilen karar: {verdict.recommended_decision}\n"
        f"  Genel hazırlık skoru: {verdict.overall_readiness_score:.0f}/100\n"
        f"  En kritik riskler: {risks}\n"
        "NOT: Bu raporun RESMİ verdict alanı yukarıdaki deterministik kararla "
        "değiştirilecek — senin verdict alanın yalnızca iç gerekçeleme için "
        "kullanılır, kullanıcıya gitmeyecek. overall_assessment ve diğer prose "
        "alanların bu kararla TUTARLI olsun, çelişmesin.\n\n"
    )


def _lang_instruction(language: ReviewLang) -> str:
    return (
        "Raporu TÜRKÇE yaz." if language == "tr" else "Write the report in ENGLISH."
    )


# --- pipeline adımları ------------------------------------------------------

# 2026-08-14 (docs/plans/LLM_THINKING_TRUNCATION_RETRY_2026-08-14.md, guardian
# 2 tur onaylı): llm_service.py:120-122'nin fırlattığı sabit hata metninin
# öneki — pro-tier thinking-truncation'ını (structured JSON yarıda kesilmesi)
# network/diğer LLMServiceError türlerinden AYIRT ETMEK için kullanılır.
_STRUCTURED_OUTPUT_TRUNCATION_MARKER = "structured_output parse failed"


async def _call_with_truncation_retry(prompt: str, **call_kwargs: Any) -> tuple[Any, bool]:
    """Writer/editor'ın _DraftReport çağrısını yapar; Gemini 2.5 Pro'nun
    thinking modu tam kapatılamadığı için (llm_service.py:99, kapatma yalnız
    flash'ta) bazen max_tokens bütçesi thinking'e gidip JSON'ı yarıda kesiyor.
    Bu SPESİFİK hata sınıfında (başka bir LLMServiceError türünde DEĞİL) AYNI
    parametrelerle tam olarak 1 kez tekrar dener (döngü değil, düz 2. çağrı) —
    arızanın deterministik olmayan doğasına (çağrıdan çağrıya değişken
    thinking-tüketimi) uygun. 2. deneme de başarısız olursa yükseltilir.

    Döner: (LLMResponse, retried: bool) — retried=True ise çağıran dürüst bir
    not düşer (bkz. run_orchestration, all_failed ile aynı desen)."""
    try:
        return await call(prompt, **call_kwargs), False
    except LLMServiceError as exc:
        if _STRUCTURED_OUTPUT_TRUNCATION_MARKER not in str(exc):
            raise
        logger.warning(
            "LLM structured-output kesilmesi (mode=%s) — 1 kez tekrar deneniyor: %s",
            call_kwargs.get("mode"),
            exc,
        )
        return await call(prompt, **call_kwargs), True


async def _run_writer(
    manuscript: Manuscript,
    evidence_block: str,
    language: ReviewLang,
    mode: ReviewMode,
) -> tuple[_DraftReport, bool]:
    frame = f"{_EDITOR_WRITER_FRAME}\n\n" if mode == "editor" else ""
    prompt = (
        f"{_lang_instruction(language)}\n\n"
        f"{frame}"
        f"{_serialize_manuscript(manuscript)}\n\n"
        f"{evidence_block}\n\n"
        "Yukarıdaki makale ve KANIT PAKETİ'ne dayanarak hakem raporu taslağını "
        "üret. Olgusal iddialarda yalnız KANIT PAKETİ'ne dayan."
    )
    resp, retried = await _call_with_truncation_retry(
        prompt,
        tier="pro",
        mode="review_writer",
        structured_output_schema=_DraftReport,
        # 4000 yetersizdi: pro tier'da thinking kapatılamıyor (llm_service.py
        # yalnız flash'ta kapatıyor), thinking bütçesi + büyük _DraftReport JSON'ı
        # (10 boyut skoru + detaylı yorumlar) 4000'i aşıp yarıda kesiliyordu
        # (empirik: gerçek PDF testinde EOF-while-parsing-string hatası,
        # text_len=6050 kesilmiş çıktı). quantitative_engine emsaline uyarak 8000.
        # KALICI çözüm değil — hâlâ aralıklı kesilebiliyor, bu yüzden yukarıdaki
        # _call_with_truncation_retry ek bir güvenlik ağı sağlıyor.
        max_tokens=8000,
    )
    draft = resp.parsed_output
    if not isinstance(draft, _DraftReport):
        # Hata-yutma YOK: writer olmadan pipeline anlamsız → yükselt.
        raise LLMServiceError("writer taslağı çözümlenemedi (parsed_output yok)")
    logger.info(
        "review writer ok: verdict=%s dims=%d", draft.verdict, len(draft.dimension_scores)
    )
    return draft, retried


async def _run_one_critic(
    mode: str,
    critic_key: str,
    draft_block: str,
    manuscript: Manuscript,
    evidence_block: str,
    language: ReviewLang,
) -> Critique | None:
    """Tek eleştirmen geçişi. Hata → None (çağıran dürüst not düşer)."""
    prompt = (
        f"{_lang_instruction(language)}\n\n"
        f"{draft_block}\n\n"
        f"MAKALE BAŞLIĞI: {manuscript.meta.title or '(başlık yok)'}\n\n"
        f"{evidence_block}\n\n"
        "Yukarıdaki TASLAĞI denetle ve Critique JSON'u döndür."
    )
    try:
        resp = await call(
            prompt,
            tier="flash",
            mode=mode,
            structured_output_schema=Critique,
            max_tokens=2000,
        )
    except LLMServiceError as exc:
        logger.warning("critic '%s' failed: %s", critic_key, exc)
        return None
    parsed = resp.parsed_output
    if not isinstance(parsed, Critique):
        logger.warning("critic '%s' parsed_output not Critique", critic_key)
        return None
    return parsed


async def _run_critics(
    draft_block: str,
    manuscript: Manuscript,
    evidence_block: str,
    language: ReviewLang,
) -> tuple[list[Critique], list[str]]:
    """5 eleştirmen PARALEL. Döner: (başarılı critiques, düşen critic_key'ler)."""
    results = await asyncio.gather(
        *(
            _run_one_critic(
                mode, key, draft_block, manuscript, evidence_block, language
            )
            for mode, key in _CRITIC_MODES
        )
    )
    critiques: list[Critique] = []
    failed: list[str] = []
    for (_, key), res in zip(_CRITIC_MODES, results, strict=True):
        if res is None:
            failed.append(key)
        else:
            critiques.append(res)
    logger.info(
        "review critics: ok=%d failed=%d (%s)",
        len(critiques),
        len(failed),
        ", ".join(failed) or "-",
    )
    return critiques, failed


async def _run_editor(
    draft: _DraftReport,
    critiques: list[Critique],
    manuscript: Manuscript,
    evidence_block: str,
    language: ReviewLang,
    mode: ReviewMode,
    deterministic_summary_block: str = "",
) -> tuple[_DraftReport, str, bool]:
    frame = f"{_EDITOR_EDITOR_FRAME}\n\n" if mode == "editor" else ""
    prompt = (
        f"{_lang_instruction(language)}\n\n"
        f"{frame}"
        f"{_serialize_draft(draft)}\n\n"
        f"{_serialize_critiques(critiques)}\n\n"
        f"MAKALE BAŞLIĞI: {manuscript.meta.title or '(başlık yok)'}\n\n"
        f"{evidence_block}\n\n"
        f"{deterministic_summary_block}"
        "Taslağı, eleştirileri ve KANIT PAKETİ'ni sentezle. Çıpasız "
        "(grounded=false) iddiaları SİL, kaçan noktaları ekle, çelişkiyi kanıtla "
        "çöz, verdict'i kalibre et. Nihai raporu JSON döndür."
    )
    resp, retried = await _call_with_truncation_retry(
        prompt,
        tier="pro",
        mode="review_editor",
        structured_output_schema=_DraftReport,
        # Bkz. _run_writer'daki aynı yorum — pro tier'da thinking kapatılamıyor,
        # aynı _DraftReport şeması için aynı kesilme riski.
        max_tokens=8000,
    )
    final = resp.parsed_output
    if not isinstance(final, _DraftReport):
        raise LLMServiceError("editör nihai raporu çözümlenemedi (parsed_output yok)")
    logger.info("review editor ok: verdict=%s", final.verdict)
    return final, resp.model_used, retried


def _ungrounded_targets(critiques: list[Critique]) -> list[str]:
    """grounded=false işaretli hedeflerin deterministik listesi (denetim izi)."""
    out: list[str] = []
    for c in critiques:
        for issue in c.issues:
            if not issue.grounded:
                out.append(f"{c.critic}:{issue.target}")
    return out


def compute_final_score(scores: list[DimensionScore]) -> float | None:
    """dimension_scores ortalaması. Public: review_service, deterministik
    override (apply_deterministic_dimension_scores) sonrası final_score'u
    YENİDEN hesaplamak için de kullanır — aksi halde final_score, override
    ÖNCESİ (tamamen LLM) skorlara göre hesaplanmış kalır, override edilmiş
    dimension_scores ile TUTARSIZ olurdu (2026-08-07)."""
    if not scores:
        return None
    return round(sum(s.score for s in scores) / len(scores), 2)


# --- public API -------------------------------------------------------------


async def run_orchestration(
    manuscript: Manuscript,
    evidence_pack: EvidencePack,
    mode: ReviewMode,
    language: ReviewLang,
    *,
    max_rounds: int = 1,
    deterministic_summary_block: str = "",
) -> ReviewReport:
    """Çekişmeli hakemlik: writer → critics (paralel) → editor → ReviewReport.

    max_rounds parametrik (default 1 tur). >1 ise writer→critics→editor döngüsü
    tekrarlanır; her turun editör çıktısı sonraki turun taslağı olur.

    deterministic_summary_block (2026-08-07): risk_radar/executive_verdict'in
    (Finding severity-sayımına dayalı, kanıta-dayalı) özeti — editor'a geçilir
    ki nihai prose bu deterministik değerlendirmeyle TUTARLI olsun. review_service
    orchestration DÖNDÜKTEN SONRA report.verdict'i BU deterministik karara göre
    override eder (bkz. apply_deterministic_dimension_scores) — editor bunu
    bilmeden yazarsa rapor kendiyle çelişebilirdi (guardian bulgusu)."""
    if max_rounds < 1:
        raise ValueError("max_rounds >= 1 olmalı")

    evidence_block = serialize_evidence_pack(evidence_pack)

    draft, writer_retried = await _run_writer(manuscript, evidence_block, language, mode)

    all_failed: list[str] = []
    any_llm_retried = writer_retried
    last_critiques: list[Critique] = []
    for round_idx in range(max_rounds):
        critiques, failed = await _run_critics(
            _serialize_draft(draft), manuscript, evidence_block, language
        )
        all_failed.extend(failed)
        last_critiques = critiques
        draft, editor_model_used, editor_retried = await _run_editor(
            draft,
            critiques,
            manuscript,
            evidence_block,
            language,
            mode,
            deterministic_summary_block,
        )
        any_llm_retried = any_llm_retried or editor_retried
        logger.info("review round %d/%d done", round_idx + 1, max_rounds)

    # Eleştirmen düşmüşse rapora DÜRÜST not (sessiz geçme yok).
    overall = draft.overall_assessment
    if all_failed:
        note = (
            "Not: bazı eleştirmenler yanıt veremedi ("
            + ", ".join(sorted(set(all_failed)))
            + "); rapor kalan eleştirmenlere göre sentezlendi."
        )
        overall = f"{overall}\n\n{note}"
    # 2026-08-14 (docs/plans/LLM_THINKING_TRUNCATION_RETRY_2026-08-14.md):
    # writer/editor'dan biri thinking-truncation'a çarpıp otomatik 1x retry
    # ile kurtarıldıysa rapora DÜRÜST not (sessiz geçme yok, all_failed'la
    # aynı desen). ReviewReport'ta ayrı bir yapılandırılmış alan YOK (guardian
    # onaylı karar — kapsam büyütmeden var olan prose-notu mekanizması).
    if any_llm_retried:
        overall = (
            f"{overall}\n\nNot: yapay zeka modelinin yanıtı ilk denemede "
            "eksik/kesik geldiği için bir bölüm otomatik olarak tekrar üretildi; "
            "nihai rapor bu tekrar denemeye dayanır."
        )

    provenance = ReviewProvenance(
        # 2026-08-13: eskiden sabit "gemini-pro-tiebreak" — Router Claude
        # fallback'ine düşse bile rapor yanlışlıkla Gemini "kullanıldı" diyordu.
        # Artık editörün SON turdaki gerçek yanıtının model_used'ı (bkz.
        # llm_service.py::call — response.model varsa onu taşır).
        model_used=editor_model_used,
        persona_version=_persona_versions(),
        engine_version=ENGINE_VERSION,
        generated_at=datetime.now(UTC),
        deterministic_engine=True,
        judgment_reproducible=False,
    )

    # Editör digesti yalnız editör modunda taşınır; author modunda model bir
    # digest üretse bile rapora geçmez (mod ayrımı kati).
    editor_digest = draft.editor_digest if mode == "editor" else None

    report = ReviewReport(
        mode=mode,
        language=language,
        manuscript_meta=manuscript.meta,
        summary=draft.summary,
        strengths=draft.strengths,
        weaknesses=draft.weaknesses,
        detailed_comments=draft.detailed_comments,
        questions=draft.questions,
        overall_assessment=overall,
        verdict=draft.verdict,
        dimension_scores=draft.dimension_scores,
        final_score=compute_final_score(draft.dimension_scores),
        evidence_pack=evidence_pack,
        provenance=provenance,
        ethics_notice=_ethics_notice(mode),
        editor_digest=editor_digest,
    )

    # ARBITRA_RESEARCH_BRIEF.md Görev C — "hivemind" gözlemi: critic'ler gerçek
    # çeşitlilik mi gösteriyor yoksa aynı noktalara mı yığılıyor? Sadece LOG
    # (gözlemlenebilirlik) — rapor şemasına dokunmaz, bir Finding/yargı ÜRETMEZ.
    agreement = compute_critic_agreement(last_critiques)
    logger.info(
        "critic agreement: n_critics=%d issues=%d overlap_ratio=%s (%d/%d çapraz-çift)",
        agreement.n_critics_with_issues,
        agreement.total_issues,
        agreement.overlap_ratio,
        agreement.overlapping_pairs,
        agreement.total_cross_critic_pairs,
    )

    # FAZ C2: typed reviewer council — GERÇEK critic/editör çıktısından türetilir
    # (additive: v1 alanları DEĞİŞMEZ; reviewer_council önceden boş default'tu).
    # finding_ids burada BOŞ bırakılır (motor bulguları henüz yok); run_pipeline
    # anchor-doğrulanmış findings ile en-iyi-çaba dimension overlap'i bağlar.
    report.reviewer_council = build_council(
        last_critiques,
        editor_summary=draft.summary,
        editor_verdict=draft.verdict,
    )

    ungrounded = _ungrounded_targets(last_critiques)
    if ungrounded:
        logger.info(
            "review: %d çıpasız iddia editöre düşürmesi için işaretlendi (%s)",
            len(ungrounded),
            ", ".join(ungrounded),
        )

    return report


__all__ = [
    "ENGINE_VERSION",
    "compute_final_score",
    "run_orchestration",
    "serialize_executive_verdict",
]
