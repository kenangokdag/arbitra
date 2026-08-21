"""P03-T01/T02 — belge + çalışma türü sınıflandırıcı (academic_engine_spec §Pipeline).

Manuscript → DocumentClassification (api.models.review SÖZLEŞMESİ — yeniden tanımlanmaz).

KANUN:
  - external AI engelliyse (gizli dosya + rıza yok) → LLM ÇAĞRILMAZ; dürüst
    unknown + 0.0 confidence + gerekçe döner (sahte sınıflandırma yok). SEC-2 gate
    review_service'te uygulanır; bu fonksiyon allow_external_ai bayrağına saygı duyar.
  - LLM çağrısı, review_orchestration ile AYNI mekanizmayı kullanır:
    api.services.llm_service.call(..., structured_output_schema=...). YENİ istemci YOK.
  - LLM çıktısı enuma karşı doğrulanır: enum-dışı değer → "unknown" + 0.0 confidence.
  - LLM hatası → dürüst unknown + gerekçe (CANON/observability: hata loglanır, yutulmaz).
  - user override modelin effective_* property'leri üzerinden kazanır; burada override
    alanları DocumentClassification'a aynen taşınır (model reconcile'i yapar).
"""

from __future__ import annotations

import logging
from typing import get_args

from pydantic import BaseModel, ConfigDict

from api.models.review import (
    DocumentClassification,
    DocumentType,
    Manuscript,
    StudyDesign,
)
from api.services.llm_service import LLMServiceError, call

logger = logging.getLogger(__name__)

ENGINE_VERSION = "academic_classifier.v1"

# Geçerli enum değerleri — Literal'lardan TÜRETİLİR (hardcode liste drift'i yok).
_DOC_TYPES: frozenset[str] = frozenset(get_args(DocumentType))
_STUDY_DESIGNS: frozenset[str] = frozenset(get_args(StudyDesign))

# Sınıflandırma için LLM'e verilen full_text excerpt üst sınırı (tez/proje ipuçları
# çoğu zaman ilk sayfalardadır; tüm metni göndermek hem maliyet hem gürültü).
_FULLTEXT_EXCERPT_CHARS = 1500


class _ClassifierLLMOutput(BaseModel):
    """LLM structured çıktısı (extra=forbid). Enum doğrulaması SONRADAN yapılır;
    bu yüzden type alanları `str` — enum-dışı değer parse'ı KIRMAZ, coerce edilir."""

    model_config = ConfigDict(extra="forbid")

    document_type: str = "unknown"
    document_type_confidence: float = 0.0
    study_design: str = "unknown"
    study_design_confidence: float = 0.0
    rationale: str = ""


def _clamp(value: float) -> float:
    """confidence'i sözleşme aralığına [0,1] sıkıştır (LLM 1.2 verse de kırılmasın)."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _build_prompt(manuscript: Manuscript) -> str:
    """Spec'in saydığı sinyalleri (başlık, özet, bölüm başlıkları, künye) odaklı topla.

    Tüm metni DEĞİL, yalnız sınıflandırmaya yarayan sinyalleri verir (focused prompt)."""
    meta = manuscript.meta
    lines = [
        "Sınıflandırılacak belge sinyalleri:",
        f"  Başlık: {meta.title or '(başlık yok)'}",
        f"  Dil: {meta.language}",
        f"  Kelime≈{meta.word_count}, referans={meta.reference_count}",
    ]
    if meta.abstract:
        lines.append(f"  Özet: {meta.abstract}")
    if meta.section_titles:
        lines.append(f"  Bölüm başlıkları: {', '.join(meta.section_titles)}")
    if meta.parse_warnings:
        lines.append(f"  Parse uyarıları: {'; '.join(meta.parse_warnings)}")

    excerpt = manuscript.full_text.strip()[:_FULLTEXT_EXCERPT_CHARS]
    if excerpt:
        lines.append("  Metin başı (kısaltılmış):")
        lines.append(excerpt)

    lines.append(
        "\nYukarıdaki sinyallere dayanarak document_type ve study_design'ı "
        "sınıflandır. Emin değilsen 'unknown' + düşük confidence kullan."
    )
    return "\n".join(lines)


def _coerce_enum(value: str, allowed: frozenset[str]) -> tuple[str, bool]:
    """Enum-dışı değeri 'unknown'a indir. Döner: (değer, geçerli_miydi)."""
    normalized = (value or "").strip()
    if normalized in allowed:
        return normalized, True
    return "unknown", False


def _unknown(
    rationale: str,
    user_document_type_override: DocumentType | None,
    user_study_design_override: StudyDesign | None,
) -> DocumentClassification:
    """Dürüst 'bilinmiyor' sonucu (override alanları korunur — kullanıcı seçimi kazanır)."""
    return DocumentClassification(
        document_type="unknown",
        document_type_confidence=0.0,
        study_design="unknown",
        study_design_confidence=0.0,
        rationale=rationale,
        user_document_type_override=user_document_type_override,
        user_study_design_override=user_study_design_override,
    )


async def classify_document(
    manuscript: Manuscript,
    *,
    allow_external_ai: bool,
    user_document_type_override: DocumentType | None = None,
    user_study_design_override: StudyDesign | None = None,
) -> DocumentClassification:
    """Belge + çalışma türünü sınıflandır → DocumentClassification.

    Args:
        manuscript: parse edilmiş makale (sinyaller meta + full_text'ten alınır).
        allow_external_ai: consent_gate.external_ai_allowed(privacy) sonucu. False ise
            içerik dış modele GÖNDERİLMEZ → dürüst unknown.
        user_document_type_override / user_study_design_override: kullanıcı seçimi;
            modelin effective_* property'leri üzerinden inferred değerin yerine geçer.

    Returns:
        DocumentClassification — her zaman bir sonuç (asla None, asla exception sızması;
        LLM hatası dürüst unknown'a düşer).
    """
    # external AI engelli → içerik dışarı gitmez, sahte sınıflandırma üretilmez.
    if not allow_external_ai:
        logger.info(
            "classifier: external AI blocked → honest unknown (no content sent out)"
        )
        return _unknown(
            "Gizli dosya: external AI engellendi (rıza yok); belge türü "
            "sınıflandırması için içerik dış modele gönderilmedi.",
            user_document_type_override,
            user_study_design_override,
        )

    prompt = _build_prompt(manuscript)
    try:
        resp = await call(
            prompt,
            tier="flash",
            mode="manuscript_classifier",
            structured_output_schema=_ClassifierLLMOutput,
            max_tokens=4000,
        )
    except LLMServiceError as exc:
        # CANON/observability: hata yutulmaz — loglanır + dürüst unknown'a düşülür.
        logger.warning("classifier LLM failed → honest unknown: %s", exc)
        return _unknown(
            f"Sınıflandırma modeli yanıt veremedi ({exc}); güvenli 'unknown'a düşüldü.",
            user_document_type_override,
            user_study_design_override,
        )

    out = resp.parsed_output
    if not isinstance(out, _ClassifierLLMOutput):
        logger.warning("classifier parsed_output not _ClassifierLLMOutput → unknown")
        return _unknown(
            "Sınıflandırma çıktısı çözümlenemedi; güvenli 'unknown'a düşüldü.",
            user_document_type_override,
            user_study_design_override,
        )

    doc_type, doc_ok = _coerce_enum(out.document_type, _DOC_TYPES)
    study, study_ok = _coerce_enum(out.study_design, _STUDY_DESIGNS)

    # enum-dışı değer 'unknown'a indiyse confidence güvenilmez → 0.0 damgala.
    doc_conf = _clamp(out.document_type_confidence) if doc_ok else 0.0
    study_conf = _clamp(out.study_design_confidence) if study_ok else 0.0

    rationale = out.rationale.strip() or None
    if not doc_ok or not study_ok:
        off = []
        if not doc_ok:
            off.append(f"document_type={out.document_type!r}")
        if not study_ok:
            off.append(f"study_design={out.study_design!r}")
        note = f"(enum-dışı değer 'unknown'a indirildi: {', '.join(off)})"
        rationale = f"{rationale} {note}" if rationale else note

    logger.info(
        "classifier ok: document_type=%s (%.2f) study_design=%s (%.2f)",
        doc_type, doc_conf, study, study_conf,
    )

    return DocumentClassification(
        document_type=doc_type,  # type: ignore[arg-type]  # _coerce_enum enum garanti eder
        document_type_confidence=doc_conf,
        study_design=study,  # type: ignore[arg-type]
        study_design_confidence=study_conf,
        rationale=rationale,
        user_document_type_override=user_document_type_override,
        user_study_design_override=user_study_design_override,
    )


__all__ = ["ENGINE_VERSION", "classify_document"]
