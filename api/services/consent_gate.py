"""SEC-2 / P01-T03 — external-AI consent gate + gizlilik çözümü.

Merkezi gizlilik vaadi: GİZLİ hakemlik dosyası (reviewer_confidential) external
LLM'e AÇIK RIZA olmadan GİTMEZ. Editör/hakem modunda consent default 'blocked'.

Gate run_pipeline'da, LLM orkestrasyonundan (review_orchestration) ÖNCE uygulanır:
  - external_ai_allowed=False → run_orchestration ATLANIR; deterministik kanıt
    paketi (atıf bütünlüğü + statcheck + kapsama — LLM gerektirmez) ile DÜRÜST,
    AÇIKÇA degraded bir rapor üretilir + AIUsageDisclosure(degraded_due_to_consent).
  - external_ai_allowed=True → normal orkestrasyon + disclosure(external_ai_used).

FE-only enforcement YETMEZ — bu modül backend'de zorunlu kapıdır.
"""

from __future__ import annotations

from datetime import UTC, datetime

from api.models.review import (
    AIUsageDisclosure,
    EvidencePack,
    ExternalAIConsent,
    Manuscript,
    PrivacyConfig,
    ReviewLang,
    ReviewMode,
    ReviewProvenance,
    ReviewReport,
    Verdict,
)

ENGINE_VERSION = "consent_gate.v1"


def resolve_privacy(
    *,
    mode: ReviewMode,
    is_author: bool = True,
    confidentiality_mode: str | None = None,
    external_ai_consent: str | None = None,
    retention_days: int = 30,
) -> PrivacyConfig:
    """Kullanıcı girdisinden PrivacyConfig türetir + güvenli default uygular.

    Kural (P01-T03): editor modu VEYA reviewer_confidential → external_ai_consent
    AÇIKÇA 'allowed' verilmediyse 'blocked'a düşer (fail-safe, sessiz external-AI yok).
    """
    conf = confidentiality_mode or (
        "reviewer_confidential" if mode == "editor" else "author_owned"
    )
    is_confidential = conf == "reviewer_confidential"

    if is_confidential:
        # GİZLİ: yalnız AÇIKÇA 'allowed' verilirse izinli; aksi (None/blocked/
        # requires_private_mode) → 'blocked' (güvenli default, sessiz external-AI yok).
        consent: ExternalAIConsent = (
            "allowed" if external_ai_consent == "allowed" else "blocked"
        )
    elif external_ai_consent in ("allowed", "blocked", "requires_private_mode"):
        consent = external_ai_consent  # type: ignore[assignment]
    else:
        consent = "allowed"  # author-owned default

    return PrivacyConfig(
        is_author=is_author,
        confidentiality_mode="reviewer_confidential" if is_confidential else "author_owned",
        external_ai_consent=consent,
        retention_days=retention_days,
    )


def external_ai_allowed(privacy: PrivacyConfig | None) -> bool:
    """privacy yoksa (eski akış) izinli kabul (geri uyum). Aksi: yalnız 'allowed'."""
    if privacy is None:
        return True
    return privacy.external_ai_consent == "allowed"


def build_disclosure(
    privacy: PrivacyConfig | None, *, external_ai_used: bool, providers: list[str]
) -> AIUsageDisclosure:
    mode = privacy.confidentiality_mode if privacy else "author_owned"
    degraded = (not external_ai_used) and privacy is not None and not external_ai_allowed(privacy)
    note = None
    if degraded:
        note = (
            "External AI kullanımı bu gizli dosya için engellendi (rıza yok). "
            "Aşağıdaki rapor yalnız deterministik bütünlük analizidir; hakem-paneli "
            "yargısı (LLM) çalıştırılmadı."
        )
    return AIUsageDisclosure(
        external_ai_used=external_ai_used,
        providers=providers if external_ai_used else [],
        confidentiality_mode=mode,
        degraded_due_to_consent=degraded,
        note=note,
    )


def _deterministic_verdict(evidence: EvidencePack) -> tuple[Verdict, str]:
    """Şeffaf, deterministik bütünlük-ekranı kararı (LLM yargısı DEĞİL).

    Kural açıkça raporda belirtilir — gizli kapalı-kutu skor değil."""
    ci = evidence.citation_integrity
    if ci.fabricated > 0 or ci.retracted > 0:
        return "major_revision", (
            f"Atıf bütünlüğü: {ci.fabricated} uydurma/çelişkili + {ci.retracted} geri-çekilmiş "
            "kaynak tespit edildi."
        )
    if ci.total and ci.not_found_in_index > ci.resolved:
        return "major_revision", (
            f"Kaynakların çoğu indekste çözülemedi ({ci.not_found_in_index}/{ci.total}); "
            "kaynakça doğrulanmalı (bu bir suçlama değil, doğrulanamama)."
        )
    return "minor_revision", "Deterministik bütünlük ekranında ölümcül atıf sorunu görülmedi."


def degraded_report(
    manuscript: Manuscript,
    evidence: EvidencePack,
    mode: ReviewMode,
    language: ReviewLang,
    privacy: PrivacyConfig | None,
) -> ReviewReport:
    """External AI engellendiğinde üretilen DÜRÜST deterministik-only rapor.

    Gerçek değer taşır (atıf bütünlüğü + statcheck + kapsama) ama LLM hakem-paneli
    yargısı içermez ve bunu AÇIKÇA söyler (disclosure + overall_assessment)."""
    verdict, verdict_reason = _deterministic_verdict(evidence)
    disclosure = build_disclosure(privacy, external_ai_used=False, providers=[])

    ci = evidence.citation_integrity
    summary = (
        "GİZLİ MOD — External AI engellendi. Bu rapor yalnız deterministik bütünlük "
        f"analizidir: {ci.total} kaynak ({ci.resolved} çözüldü, {ci.not_found_in_index} "
        f"çözülemedi, {ci.fabricated} uydurma, {ci.retracted} geri-çekilmiş), "
        f"{len(evidence.stat_findings)} istatistik kontrolü, "
        f"{len(evidence.coverage_gaps)} kapsama notu. Hakem-paneli (LLM) yargısı "
        "çalıştırılmadı; tam inceleme için external AI iznine veya yerel-model moduna ihtiyaç var."
    )
    overall = (
        f"Deterministik bütünlük kararı: {verdict}. Gerekçe: {verdict_reason} "
        "Bu, kapalı-kutu bir LLM skoru değil; şeffaf kurala dayanır ve TAM hakem "
        "incelemesinin yerini TUTMAZ."
    )
    return ReviewReport(
        mode=mode,
        language=language,
        manuscript_meta=manuscript.meta,
        summary=summary,
        strengths=[],
        weaknesses=[],
        detailed_comments=[],
        questions=[],
        overall_assessment=overall,
        verdict=verdict,
        dimension_scores=[],
        final_score=None,
        evidence_pack=evidence,
        provenance=ReviewProvenance(
            model_used="none (external AI blocked)",
            persona_version="degraded",
            engine_version=ENGINE_VERSION,
            generated_at=datetime.now(UTC),
            deterministic_engine=True,
            judgment_reproducible=True,  # LLM yok → bu rapor deterministik/yeniden-üretilebilir
        ),
        disclosure=disclosure,
        schema_version="review_report.v1",
    )
