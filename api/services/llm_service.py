"""F8 LLMService — provider-agnostic LLM çağrı katmanı (DM-LLM-3 + DM-LLM-4).

Mimari:
  call(prompt, tier, mode, project_ctx, page_state, structured_output_schema)
    ↓ build system prompt: BASE_PERSONA + ROLE_MODULES[mode] + ProjectContext + PageState
    ↓ litellm.acompletion(model_for_tier, messages, ...)
    ↓ structured_output parse (Pydantic) varsa
    ↓ LLMResponse

Tier routing:
  flash → router_settings.CHAT_ADVISOR_MODEL (Gemini Flash)
  pro   → router_settings.TIEBREAK_MODEL    (Gemini Pro)

HK-1 Pydantic forbid; HK-2 model_id config'den; HK-7 temperature seed.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from api.config import Settings, get_settings
from api.models.llm import LLMResponse, ProjectContext
from api.models.review import ReviewReport
from api.services.litellm_router import acompletion

logger = logging.getLogger(__name__)

BASE_PERSONA = """Sen ALI — Adaptive Literature Intelligence danışmanısın.
Akademik araştırmacılara tez sürecinde rehberlik edersin.
Tarz: net, kanıt-odaklı, jargon yok, kullanıcının diline uyumlu.
Yasak: kanıtsız iddia, hatırlamadığın detayı uydurma, generic SaaS cevap.
Doğrulama kuralı: bir iddiayı destekleyecek paper/abstract/veri parçası sana
verilmediyse uydurma — açıkça "doğrulayamıyorum" yaz ve hangi kanıtın
eksik olduğunu belirt. (Audit M-11 / finding-F-PERSONA-1.)
"""


def _get_role_modules() -> dict[str, str]:
    from api.services.role_modules import ROLE_MODULES
    return ROLE_MODULES


# 2026-08-20 (kullanıcı bulgusu): review pipeline'ın 7 aşaması da (writer +
# 5 critic + editor) örnekleme yapıyordu (temperature>0, seed hiç yok) — aynı
# makale art arda analiz edilince farklı bulgu sayısı/verdict/skor çıkıyordu
# ("3 major konu eksik" → "1"). Kaynak: review_orchestration.py'nin
# review_writer/review_editor (L276/L387) + _CRITIC_MODES (L110-116) mode
# adları — döngüsel import'tan kaçınmak için burada AYNEN kopyalanıyor,
# review_orchestration.py'de mode adı değişirse burası da güncellenmeli.
# Chat/Danışman modları (default, review_advisor, ...) bu kümenin DIŞINDA —
# konuşma için hâlâ tier-bazlı temperature kullanılıyor.
#
# DÜRÜST SONUÇ (2026-08-20, kullanıcı talebiyle 3 canlı run karşılaştırıldı,
# eval/review/temperature_zero_consistency_check.py + sonuçlar
# eval/review/results/temperature_zero_consistency_log.jsonl'de): temperature=0
# varyansı AZALTTI ama ORTADAN KALDIRMADI. Aynı deneme.pdf 3 kez analiz
# edildi — citation_integrity ve originality 3/3 tam aynı çıktı, ama VERDICT
# BİLE değişti (2× major_revision, 1× accept). Kök neden muhtemelen: (a)
# Gemini'de temp=0'ın bile bit-birebir determinism garantisi vermemesi
# (doğrulanamadı, ama tutarlı bulgu), (b) 7 aşamalı zincirde (writer→5
# critic→editor) küçük bir fark bir sonraki aşamaya taşınıp büyüyor. "Rapor
# üretimi artık deterministik" DENEMEZ — sadece run-to-run varyans azaldı.
#
# 2026-08-20 devamı — seed EKLENDİ, canlı doğrulandı, DÜRÜST SONUÇ AŞAĞIDA:
# Vertex/Gemini seed'i litellm üzerinden gerçekten destekliyor (A-kanıt, kod
# okunarak doğrulandı):
# .venv/Lib/site-packages/litellm/llms/vertex_ai/gemini/vertex_and_google_ai_studio_gemini.py
# L209/L222/L313/L1155-1156 (`VertexGeminiConfig.seed`) → transformation.py
# L715-736/765-766 → gerçekten Gemini'ye giden JSON body'nin
# `generationConfig.seed` alanına yazılıyor (guardian ikinci turda bu zinciri
# de doğruladı). Kullanıcının kabul kriteri: "verdict + major-count birebir
# aynı, olmazsa self-consistency'ye geç." Canlı 3-run sonucu
# (eval/review/results/temperature_zero_seed_consistency_log.jsonl, run 1/4/5
# — run 2/3 fix'le ilgisiz bir GCP billing/dunning 403'ünden düştü):
# verdict 3/3 AYNI (accept/accept/accept — temp=0-only testinde 2/3 idi, bir
# iyileşme AMA n=3 çok küçük, kesin sonuç çıkarılamaz). major-count TAM
# AYNI DEĞİL (2, 1, 2). Toplam bulgu sayısı ve birçok boyut skoru (özellikle
# coverage_completeness: 5.14/10.0/4.06, community_value: 1.0/4.0/1.5) HÂLÂ
# ciddi varyans gösteriyor — kabul kriteri seed EKLENSE BİLE TAM
# KARŞILANMADI. Kenan kararı (2026-08-20): olduğu gibi kabul + kod yorumu
# yeterli, self-consistency/N-run oylaması (daha pahalı) ayrı bir plan
# gerektirir, bu commit'in kapsamı dışında bırakıldı.
#
# YAN BULGU/DÜZELTME: seed eklenince Vertex 403 (billing) sonrası Claude
# fallback'i de kırılıyordu (Anthropic `seed` desteklemiyor,
# UnsupportedParamsError) — önceden (seed yokken) fallback ÇALIŞIRDI. Bunu
# da bu oturumda `drop_params=True` ile düzelttim (aşağı bkz, call()
# içinde).
#
# `judgment_reproducible=False` alanı (api/models/review.py) bu artık daha
# iyi belgelenmiş ama HÂLÂ tam çözülmemiş gerçeği doğru işaretliyor —
# flip EDİLMEDİ, dürüstlük korundu.
_REVIEW_PIPELINE_SEED = 42
"""2026-08-21: sadece review_orchestration'ın 7 aşaması değil, aşağıdaki
_DETERMINISTIC_SCORING_MODES kümesindeki (review + academic-assessment,
11 mode) HER çağrı için kullanılan sabit seed — hangi makale/prompt olursa
olsun AYNI sabit değer kullanılır (seed RNG state'i sabitler, farklı prompt
yine farklı çıktı üretir — makaleler arası çeşitlilik BOZULMAZ, sadece AYNI
prompt AYNI çıktıyı vermeli). İsim tarihsel (ilk fix'te sadece review
pipeline'ı kapsıyordu), rename edilmedi (gereksiz diff gürültüsü)."""

_REVIEW_PIPELINE_MODES = frozenset(
    {
        "review_writer",
        "review_editor",
        "critic_skeptik",
        "critic_yontemci",
        "critic_sempatik",
        "citation_critic",
        "novelty_critic",
    }
)

# 2026-08-21 devamı — DAHA DERİN kök neden bulundu (kullanıcı: "review
# pipeline'ının '3 deterministik moat boyutu' iddiası... çöz"). review_writer/
# editor'ın serbest skorları review_service.py:639'da
# report_synthesis.apply_deterministic_dimension_scores() ile ZATEN override
# ediliyor — mekanizma DOĞRU bağlı (guardian'ın "rubric_registry hiç
# geçmiyor" bulgusu review_orchestration.py'ye bakınca doğruydu ama EKSİKTİ,
# review_service.py'nin post-processing'ini kaçırmıştı). Ama override'ın
# GİRDİSİ olan `findings`, assess_manuscript()'in (rubric_registry/
# dimension_engine motoru) kendi İÇİNDEKİ 4 LLM çağrısından geçiyor — bunların
# HİÇBİRİ _REVIEW_PIPELINE_MODES'ta değildi, hâlâ temperature=0.2/seed-yok
# örnekleme yapıyordu. Kaynak (A-kanıt, kod okunarak, 4 dosya):
#   engine/academic/classifier.py:159        mode="manuscript_classifier"
#   engine/academic/dimension_engine.py:120  mode="academic_dimension"
#   engine/academic/qualitative_engine.py:86 mode="qualitative_rigor"
#   engine/academic/quantitative_engine.py:101 mode="quantitative_validity"
# Hepsi tier="flash" (_engine_base.py:352 default, classifier.py L158 açıkça).
# quantitative_validity, statistical_consistency/coverage risk boyutunu
# DOĞRUDAN besliyor (report_synthesis.py:510-518 yorumu bunu doğruluyor) —
# canlı testte bu boyutun en gürültülü çıkmasının kök nedeni muhtemelen bu.
# citation_integrity'nin göreceli stabil kalması (6/6 run'da 6.22) gerçek
# OpenAlex verisine büyük ölçüde dayanmasıyla tutarlı.
#
# SONUÇ (2026-08-21, canlı 3-run doğrulama, deneme.pdf, backend temiz restart
# sonrası — eval/review/results/temperature_zero_academic_modes_log.jsonl):
# verdict, overall_readiness_score, final_score, toplam bulgu sayısı, severity
# dağılımı VE 10 boyutun TAMAMI 3 run'da BİT-BİREBİR AYNI çıktı (önceki
# turlarda coverage_completeness/statistical_consistency en gürültülü
# olanlardı — o run'da ikisi de 3/3 sabitti). n=1 makale, n=3 run.
#
# DÜZELTME (2026-08-22, 61-goldset canlı yeniden-koşum —
# eval/review/results/goldset61_classifier_determinism_2026-08-22.json):
# yukarıdaki "TAM BAŞARI" tek makaleye özgüydü, GENEL bir garanti DEĞİL.
# 61-goldset'in 6 makalelik alt-kümesi 2. kez canlı koşulunca (4 geçerli
# kıyaslama, 2'si zaten rate-limit'ten düşmüştü): document_type/study_design
# 4/4 (%100) aynı kaldı, AMA verdict sadece 3/4 (%75) aynı kaldı — 1 makalede
# (peerj:20153) major_revision→accept DEĞİŞTİ. Doğru çerçeveleme: bu
# düzeltme run-to-run varyansı BÜYÜK ÖLÇÜDE azalttı (33/33/31 findings → tek
# makalede 3/3 tam eşleşme; 61-goldset'te classifier'ın document_type/
# study_design çıktısı 4/4 sabit), ama MUTLAK/HER-ZAMAN determinism GARANTİSİ
# vermiyor — verdict gibi zincirleme sonuçlar hâlâ ARADA SIRADA değişebilir.
#
# Kalibrasyon (61-goldset, n=43/61 — 18'i rate-limit'ten analiz edilemedi):
# tam isabet %67→%72.1, tolerans %74→%79.1, sınıf-dengeli doğruluk
# %49.2→%65.9 — genel olarak OLUMLU ama n küçüldüğü için (61→43) kesinlik
# iddia edilemez; reject-sınıfı doğruluğu hâlâ zayıf (%12.5) ve soundness
# korelasyonu hâlâ negatif/gürültülü (r=-0.31) — ÇÖZÜLMEDİ, bu turun kapsamı
# dışında. Detay: PDF_PIPELINE_CALISMA_GUNLUGU.md §71.
_ACADEMIC_ASSESSMENT_MODES = frozenset(
    {
        "manuscript_classifier",
        "academic_dimension",
        "qualitative_rigor",
        "quantitative_validity",
    }
)

_DETERMINISTIC_SCORING_MODES = _REVIEW_PIPELINE_MODES | _ACADEMIC_ASSESSMENT_MODES


class LLMServiceError(Exception):
    """LLM çağrı hatası."""


async def call(
    prompt: str,
    *,
    tier: Literal["flash", "pro"] = "flash",
    mode: str = "default",
    project_ctx: ProjectContext | None = None,
    page_state: dict[str, Any] | None = None,
    paper_context: list[dict[str, Any]] | None = None,
    report_context: ReviewReport | None = None,
    structured_output_schema: type[BaseModel] | None = None,
    max_tokens: int | None = None,
    settings: Settings | None = None,
) -> LLMResponse:
    """LLM çağrısı + ProjectContext + PageContext otomatik prompt injection."""
    settings = settings or get_settings()
    role_modules = _get_role_modules()

    system_parts = [BASE_PERSONA]

    role_brief = role_modules.get(mode)
    if role_brief is not None:
        system_parts.append(role_brief)

    if project_ctx is not None:
        system_parts.append(_serialize_project_ctx(project_ctx))

    if page_state is not None:
        system_parts.append(f"Sayfada şu an görünen veri: {page_state}")

    if paper_context:
        system_parts.append(_serialize_paper_context(paper_context))

    if report_context is not None:
        system_parts.append(_serialize_report_context(report_context))

    system_prompt = "\n\n".join(system_parts)

    model = _model_for_tier(tier)
    effective_max_tokens = max_tokens if max_tokens is not None else (
        600 if tier == "flash" else 800
    )

    t0 = time.perf_counter()
    try:
        response = await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0 if mode in _DETERMINISTIC_SCORING_MODES else (0.2 if tier == "flash" else 0.1),
            max_tokens=effective_max_tokens,
            # drop_params=True: 2026-08-20 canlı testte bulunan GERÇEK regresyon —
            # Vertex/Gemini 403 (billing) verince Router Claude'a fallback
            # deniyordu, ama Anthropic `seed`'i desteklemiyor →
            # litellm.UnsupportedParamsError, fallback da patlıyordu (önceden,
            # seed yokken fallback çalışırdı). drop_params=True litellm'e
            # desteklenmeyen param'ı SESSİZCE düşürmesini söylüyor (litellm/main.py:1581,
            # per-call kwarg) — Gemini'ye giderken seed hâlâ gönderiliyor,
            # sadece fallback Claude'a düşerse seed'siz devam ediyor.
            # GUARDIAN UYARISI (2026-08-20, ikinci tur): drop_params=True SADECE
            # seed'e özel değil — bu çağrıdaki HERHANGİ bir provider-desteklemeyen
            # parametreyi sessizce düşürür, hiç loglamaz (litellm/utils.py:2953-3031,
            # doğrulandı). İleride bu çağrıya eklenecek başka bir param da fallback'te
            # fark edilmeden düşebilir — bilinçli kabul edilen risk, izlenmeli.
            # DOĞRULAMA (2026-08-20): 3 geçerli seed-run'ın (run1/4/5) 3'ünde de
            # `provenance.model_used == "gemini-2.5-pro"` — Claude'a sessiz düşüş
            # OLMADI (report tablosundan admin client ile doğrudan okunarak
            # doğrulandı). Ama bu alan pipeline-seviyesi TEK string (hangi
            # aşamanın yazdığı belli değil, muhtemelen editor) — 7 aşamanın HER
            # BİRİNİN Gemini'de kaldığını KANITLAMAZ, sadece pipeline'ın genel
            # sonucunu gösterir.
            **({"seed": _REVIEW_PIPELINE_SEED, "drop_params": True} if mode in _DETERMINISTIC_SCORING_MODES else {}),
            **({"thinking": {"type": "disabled", "budget_tokens": 0}} if tier == "flash" else {}),
        )
    except Exception as e:
        logger.exception("LLM call failed")
        raise LLMServiceError(f"LLM çağrısı başarısız: {e}") from e

    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = response.choices[0].message.content
    parsed = None
    if structured_output_schema is not None:
        try:
            parsed = structured_output_schema.model_validate_json(_strip_code_fence(text))
        except ValidationError as exc:
            # Gemini truncate / malformed JSON → LLMServiceError; caller fallback path'i devreye girer.
            logger.warning(
                "LLM structured parse failed (model=%s, schema=%s, text_len=%d): %s",
                model,
                structured_output_schema.__name__,
                len(text or ""),
                exc,
            )
            raise LLMServiceError(
                f"structured_output parse failed ({structured_output_schema.__name__})"
            ) from exc

    # `model` burada İSTENEN alias (örn. "gemini-pro-tiebreak") — Router bir
    # Claude fallback'ine düşerse GERÇEKTE çağrılan model FARKLI olur.
    # `response.model` litellm'in gerçekten yanıt veren deployment'ı yazdığı
    # alan (ModelResponse.model, Optional) — varsa onu kullan, testte/edge-case'te
    # boşsa istenen alias'a düş (2026-08-13, eski hardcoded provenance bug'ının
    # kök nedeni: fallback olduğunda rapor hâlâ istenen alias'ı "kullanıldı"
    # diye yazıyordu — dürüst olmayan provenance).
    actual_model = getattr(response, "model", None) or model

    return LLMResponse(
        text=text,
        parsed_output=parsed,
        model_used=actual_model,
        tokens_in=response.usage.prompt_tokens,
        tokens_out=response.usage.completion_tokens,
        latency_ms=latency_ms,
    )


_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*\n?", re.IGNORECASE)
_FENCE_CLOSE_RE = re.compile(r"\n?```\s*$")


def _strip_code_fence(text: str) -> str:
    """Gemini Flash bazen ```json…``` ile sarmalıyor; Pydantic JSON parse öncesi soy.

    Why: Gemini response_format respect'i tutarsız; ayrıca max_tokens kapağı
    yanıtı kapanış fence'i olmadan kesebilir — açılış fence'ini her durumda soy,
    kapanış varsa ek olarak temizle.
    """
    stripped = text.strip()
    stripped = _FENCE_OPEN_RE.sub("", stripped, count=1)
    stripped = _FENCE_CLOSE_RE.sub("", stripped, count=1)
    return stripped.strip()


def _model_for_tier(tier: str) -> str:
    """Tier → yaml alias (Router config/litellm_models.yaml resolve eder)."""
    if tier == "flash":
        return "gemini-flash-tr"
    if tier == "pro":
        return "gemini-pro-tiebreak"
    raise ValueError(f"Unknown tier: {tier}")


def _serialize_paper_context(papers: list[dict[str, Any]]) -> str:
    """paper_context_ids OpenAlex meta'sını system prompt bloğuna çevir.

    Her paper: title (year, venue) · authors · abstract. Eksik alanlar atlanır.
    Caller projeksiyon yapar (title/year/venue/authors/abstract anahtarları).
    """
    lines = [
        "Aşağıdaki paper(lar) bu konuşmanın bağlamıdır. "
        "Yorumlarını yalnızca bu kaynaklara dayandır; uydurma yok:"
    ]
    for i, p in enumerate(papers, 1):
        title = (p.get("title") or "").strip() or "(başlık yok)"
        year = p.get("year")
        venue = (p.get("venue") or "").strip()
        header = f"[{i}] {title}"
        meta_bits: list[str] = []
        if year:
            meta_bits.append(str(year))
        if venue:
            meta_bits.append(venue)
        if meta_bits:
            header += f" ({', '.join(meta_bits)})"
        lines.append(header)
        authors = p.get("authors")
        if authors:
            authors_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
            lines.append(f"  Yazar: {authors_str}")
        abstract = (p.get("abstract") or "").strip()
        if abstract:
            lines.append(f"  Özet: {abstract}")
    return "\n".join(lines)


def _serialize_report_context(report: ReviewReport) -> str:
    """İncelenen makalenin hakem raporunu system prompt bloğuna çevir (ÖZET, TAM DEĞİL).

    Plan: docs/plans/DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16.md §4.3.
    Token bütçesi (flash tier max_tokens=600) TAM raporu (özellikle evidence_pack.
    references, onlarca kayıt olabilir) taşımaya izin vermez — sadece karar-ilgili
    özet: verdict, executive_verdict, dimension_scores, risk_radar (zaten kompakt),
    critical/major findings (title+summary, tam liste değil), citation_integrity
    SAYAÇLARI (referans listesi değil).
    """
    lines = [
        "Aşağıdaki, kullanıcının şu an görüntülediği makalenin hakem raporunun "
        "ÖZETİDİR. Cevaplarını YALNIZCA buna dayandır; uydurma yok:",
        f"Verdict: {report.verdict}",
    ]

    ev = report.executive_verdict
    if ev is not None:
        lines.append(f"Genel teşhis: {ev.one_sentence_diagnosis}")
        if ev.top_fatal_risks:
            lines.append(f"En kritik riskler: {'; '.join(ev.top_fatal_risks)}")

    if report.dimension_scores:
        dim_bits = [f"{d.key}={d.score:.1f}" for d in report.dimension_scores]
        lines.append(f"Boyut skorları: {', '.join(dim_bits)}")

    if report.risk_radar:
        lines.append("Risk radarı:")
        for item in report.risk_radar:
            score_str = f"{item.score:.0f}" if item.score is not None else "değerlendirilmedi"
            lines.append(
                f"  - {item.dimension} (skor={score_str}, önem={item.severity}): "
                f"{item.why_it_matters}"
            )

    critical_findings = [
        f for f in (report.findings or []) if f.severity in ("critical", "major")
    ]
    if critical_findings:
        lines.append("Kritik/majör bulgular:")
        for f in critical_findings:
            lines.append(f"  - [{f.finding_id}] ({f.dimension}, {f.severity}) {f.title}: {f.summary}")

    ci = report.evidence_pack.citation_integrity
    lines.append(
        f"Atıf bütünlüğü sayaçları: toplam={ci.total}, çözüldü={ci.resolved}, "
        f"uydurma={ci.fabricated}, geri-çekilmiş={ci.retracted}, "
        f"indekste-bulunamadı={ci.not_found_in_index}"
    )

    return "\n".join(lines)


def _serialize_project_ctx(ctx: ProjectContext) -> str:
    parts = [f"Proje bağlamı (project_id={ctx.project_id}):"]
    if ctx.topic:
        parts.append(f"  - Konu: {ctx.topic}")
    if ctx.hypothesis:
        parts.append(f"  - Hipotez: {ctx.hypothesis}")
    if ctx.selected_method:
        parts.append(f"  - Seçilen metod: {ctx.selected_method}")
    if ctx.corpus_filter:
        parts.append(f"  - Korpus filtresi: {ctx.corpus_filter}")
    if ctx.last_decisions:
        parts.append(f"  - Son 5 karar: {', '.join(ctx.last_decisions)}")
    parts.append("Önerilerin bu bağlamla çelişmesin.")
    return "\n".join(parts)
