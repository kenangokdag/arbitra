"""P03-T04/T05 — akademik değerlendirme motorlarının PAYLAŞILAN LLM köprüsü.

Tek mekanizma: bir boyut grubunun değerlendirme KRİTERLERİNİ + makale bağlamını
LLM'e verir, structured JSON çıktı alır ve api.models.review.Finding SÖZLEŞMESİNE
DÜRÜST uyan Finding[] + ActionItem[] üretir.

KANUN (classifier.py ile AYNI desen — yeni istemci YOK):
  - LLM çağrısı: api.services.llm_service.call(..., structured_output_schema=...).
  - external AI engelliyse (allow_external_ai=False) → SIFIR LLM çağrısı; boş sonuç +
    GÖRÜNÜR degraded sinyali ("<label>:external_ai_blocked"). İçerik dışarı GİTMEZ.
  - LLM hatası → hata LOGLANIR (yutulmaz) + boş sonuç + degraded ("<label>:llm_unavailable").
  - Finding sözleşmesi (api/models/review.py:579-593) DÜRÜST uygulanır: severity
    critical/major iken model action_item VEYA anchor sağlamadıysa → UYDURMA YOK;
    severity 'moderate'a İNDİRİLİR + neden limitations'a yazılır + loglanır. Validator
    asla kullanıcıya çıkmaz (kontrollü downgrade, faked-anchor değil).
  - manuscript_anchor = LLM'in makaleden bulup alıntıladığı (section + verbatim quote).
    Stable global anchor id'leri FAZ C'nin işi; burada per-finding anchor_id yeterli.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from api.models.review import (
    ActionItem,
    ActionPriority,
    EffortGain,
    Finding,
    ManuscriptAnchor,
    SeverityV2,
)
from api.services.llm_service import LLMServiceError, call

logger = logging.getLogger(__name__)

# makale gövdesinden LLM'e verilen excerpt üst sınırı. Tüm metni göndermek hem
# maliyet hem token-kapağı riski; metodoloji/bulgular çoğunlukla bu sınır içinde.
_MANUSCRIPT_EXCERPT_CHARS = 30000

# Kırpma SINIRININ ÖTESİNDE kalabilen ama hakemlik için önemli "şeffaflık/beyan"
# bölümleri (veri/kod erişimi, etik, çıkar çatışması vb.) — genelde makale
# SONUNDA yer alırlar. İlk N karakterlik kırpma bunları atlarsa motor yanlışlıkla
# "eksik" der (empirik kanıt, 2026-08-04: gerçek bir makalede OSF veri/kod linki
# 30000. karakterden SONRA geldi; motor görmedi, "veri/kod erişilebilirliği
# eksik" diye MAJOR bulgu üretti — makalede gerçekte VARDI, gerçek bir hakem de
# veri paylaşımını övmüştü). Bu bölümleri kırpma sınırının ötesinde ayrıca arayıp
# kısa alıntılar olarak ekleriz — tüm metni göndermeden, token maliyeti sınırlı.
_DISCLOSURE_HEADING_KEYWORDS = (
    "data availability",
    "code availability",
    "data and code availability",
    "open practices",
    "availability of data",
    "openly available",
    "publicly available",
    "available on osf",
    "osf.io",
    "made available",
    "data are available",
    "dataset is available",
    "conflict of interest",
    "conflicts of interest",
    "ethics statement",
    "ethical approval",
    "author contributions",
    "veri erişilebilirliği",
    "kod erişilebilirliği",
    "açık erişimde",
    "çıkar çatışması",
    "etik beyan",
)
_DISCLOSURE_SNIPPET_CHARS = 600
_DISCLOSURE_MAX_TOTAL_CHARS = 2400

_SEVERITIES: frozenset[str] = frozenset(get_args(SeverityV2))
_PRIORITIES: frozenset[str] = frozenset(get_args(ActionPriority))
_EFFORT_GAINS: frozenset[str] = frozenset(get_args(EffortGain))

# Finding validator'ın (api/models/review.py:584) zorunlu kıldığı yüksek-önem set'i.
_HIGH_SEVERITY: frozenset[str] = frozenset({"critical", "major"})


# --- LLM structured çıktı şeması (extra=forbid; enum SONRADAN coerce edilir) ----


class _LLMAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str | None = None
    quote: str | None = None


class _LLMActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: str = "P1"
    instruction: str = ""
    target_section: str | None = None
    effort: str = "medium"
    expected_gain: str = "medium"
    acceptance_check: str | None = None


class _LLMFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = ""
    severity: str = "moderate"
    confidence: float = 0.5
    title: str = ""
    summary: str = ""
    reasoning_public: str | None = None
    manuscript_anchors: list[_LLMAnchor] = Field(default_factory=list)
    action_items: list[_LLMActionItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    global_issue: bool = False


class _LLMFindingList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[_LLMFinding] = Field(default_factory=list)


# --- motor çıktısı (dispatcher bunları toplar) ------------------------------


@dataclass
class EngineResult:
    """Bir motor/boyut değerlendirmesinin çıktısı.

    findings → Finding[] (sözleşme-geçerli) · action_items → bunların ActionItem[]'ı
    (Finding.action_item_ids bunlara işaret eder) · degraded → GÖRÜNÜR eksiklik
    sinyalleri (boş = sorun yok; consent-block / llm-fail / dropped burada görünür)."""

    findings: list[Finding] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    def extend(self, other: EngineResult) -> None:
        self.findings.extend(other.findings)
        self.action_items.extend(other.action_items)
        self.degraded.extend(other.degraded)


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _coerce(value: str, allowed: frozenset[str], fallback: str) -> str:
    return value if (value or "").strip() in allowed else fallback


def _find_disclosure_tail(body: str, excerpt_len: int) -> str:
    """Kırpma sınırının ÖTESİNDE kalan şeffaflık/beyan bölümlerini bul, kısa
    alıntılar olarak döndür (tam metin değil — token maliyeti sınırlı kalır).
    Bulunamazsa boş string (uydurma yok, dürüst boşluk)."""
    tail = body[excerpt_len:]
    if not tail:
        return ""
    lower_tail = tail.lower()
    snippets: list[str] = []
    seen_spans: list[tuple[int, int]] = []
    total = 0
    for kw in _DISCLOSURE_HEADING_KEYWORDS:
        idx = lower_tail.find(kw)
        if idx < 0:
            continue
        start = max(0, idx - 40)
        end = min(len(tail), idx + _DISCLOSURE_SNIPPET_CHARS)
        if any(not (end <= s or start >= e) for s, e in seen_spans):
            continue  # örtüşen aralık — tekrar ekleme
        snippet = tail[start:end].strip()
        if not snippet:
            continue
        if total + len(snippet) > _DISCLOSURE_MAX_TOTAL_CHARS:
            break
        snippets.append(snippet)
        seen_spans.append((start, end))
        total += len(snippet)
    return "\n---\n".join(snippets)


def _manuscript_block(manuscript) -> str:
    """Makale sinyallerini (künye + bölüm başlıkları + gövde excerpt) prompt bloğuna çevir."""
    meta = manuscript.meta
    lines = [
        "DEĞERLENDİRİLECEK MAKALE:",
        f"  Başlık: {meta.title or '(başlık yok)'}",
        f"  Dil: {meta.language}",
        f"  Kelime≈{meta.word_count}, referans={meta.reference_count}",
    ]
    if meta.abstract:
        lines.append(f"  Özet: {meta.abstract}")
    if meta.section_titles:
        lines.append(f"  Bölüm başlıkları: {', '.join(meta.section_titles)}")
    body = manuscript.full_text.strip()
    excerpt = body[:_MANUSCRIPT_EXCERPT_CHARS]
    if excerpt:
        truncated = " (KISALTILDI — tüm metin değil)" if len(body) > len(excerpt) else ""
        lines.append(f"  Gövde metni{truncated}:")
        lines.append(excerpt)
        disclosure_tail = _find_disclosure_tail(body, len(excerpt))
        if disclosure_tail:
            lines.append(
                "  EK — kırpma sınırının ÖTESİNDE bulunan şeffaflık/beyan "
                "bölümleri (veri/kod erişimi, etik, çıkar çatışması vb. — "
                "gövde metninde YOK diye YANLIŞ sonuca varmadan önce bunlara "
                "bak):"
            )
            lines.append(disclosure_tail)
    return "\n".join(lines)


def _build_prompt(
    *,
    manuscript,
    criteria_block: str,
    evidence_context: str | None,
) -> str:
    parts = [
        _manuscript_block(manuscript),
        "",
        "DEĞERLENDİRME KRİTERLERİ (yalnız bunları uygula, yeni kriter UYDURMA):",
        criteria_block,
    ]
    if evidence_context:
        parts += ["", "ÖNCEDEN HESAPLANMIŞ DETERMİNİSTİK KANIT (bağlam):", evidence_context]
    parts += [
        "",
        "Her kriter için makalede gerçek bir sorun/güçlü-yön gördüysen bir finding üret. "
        "Yüksek önem (critical/major) verdiğin her finding'de makaleden BİREBİR alıntı "
        "(manuscript_anchors.quote) VE en az bir action_item ZORUNLU. Alıntıyı UYDURMA; "
        "makalede yoksa global_issue=true işaretle veya önemi düşür. Çıktı SADECE JSON.",
    ]
    return "\n".join(parts)


def _to_findings(
    parsed: _LLMFindingList,
    *,
    id_prefix: str,
    force_dimension: str | None,
) -> EngineResult:
    """LLM çıktısını sözleşme-geçerli Finding[]+ActionItem[]'a çevir (DÜRÜST enforce)."""
    result = EngineResult()
    for i, raw in enumerate(parsed.findings):
        severity = _coerce(raw.severity, _SEVERITIES, "moderate")
        confidence = _clamp(raw.confidence)
        limitations = list(raw.limitations)

        fid = f"{id_prefix}.f{i}"

        # action item'ları kur (instruction'sız olanları DÜŞÜR — boş görev değersiz).
        action_ids: list[str] = []
        actions: list[ActionItem] = []
        for j, a in enumerate(raw.action_items):
            instruction = (a.instruction or "").strip()
            if not instruction:
                continue
            aid = f"{fid}.a{j}"
            actions.append(
                ActionItem(
                    action_id=aid,
                    priority=_coerce(a.priority, _PRIORITIES, "P1"),  # type: ignore[arg-type]
                    effort=_coerce(a.effort, _EFFORT_GAINS, "medium"),  # type: ignore[arg-type]
                    expected_gain=_coerce(a.expected_gain, _EFFORT_GAINS, "medium"),  # type: ignore[arg-type]
                    target_section=a.target_section,
                    instruction=instruction,
                    acceptance_check=a.acceptance_check,
                    linked_finding_ids=[fid],
                )
            )
            action_ids.append(aid)

        # anchor'ları kur (section VEYA quote olan — boş anchor değersiz). Quote UYDURULMAZ.
        anchors: list[ManuscriptAnchor] = []
        for k, an in enumerate(raw.manuscript_anchors):
            section = (an.section or "").strip() or None
            quote = (an.quote or "").strip() or None
            if section is None and quote is None:
                continue
            anchors.append(
                ManuscriptAnchor(anchor_id=f"{fid}.q{k}", section=section, quote=quote)
            )

        # DÜRÜST sözleşme uygulaması (api/models/review.py:584-592):
        # critical/major iken action VEYA anchor eksikse → UYDURMA YOK, 'moderate'a indir.
        if severity in _HIGH_SEVERITY:
            missing: list[str] = []
            if not action_ids:
                missing.append("action_item")
            if not anchors and not raw.global_issue:
                missing.append("manuscript_anchor/global_issue")
            if missing:
                note = (
                    f"Model '{severity}' önem verdi ama {', '.join(missing)} sağlamadı; "
                    "sözleşme gereği önem 'moderate'a indirildi (kanıt UYDURULMADI)."
                )
                logger.warning("finding %s downgraded: %s", fid, note)
                limitations.append(note)
                severity = "moderate"

        title = (raw.title or "").strip() or (raw.summary or "").strip()[:80] or (
            force_dimension or raw.dimension or "Bulgu"
        )
        dimension = force_dimension or (raw.dimension or "").strip() or "unspecified"

        try:
            finding = Finding(
                finding_id=fid,
                dimension=dimension,
                severity=severity,  # type: ignore[arg-type]
                confidence=confidence,
                title=title,
                summary=(raw.summary or "").strip(),
                manuscript_anchors=anchors,
                reasoning_public=(raw.reasoning_public or "").strip() or None,
                limitations=limitations,
                action_item_ids=action_ids,
                global_issue=bool(raw.global_issue),
            )
        except ValidationError as exc:
            # downgrade sonrası asla beklenmez ama sessiz çökme YASAK → logla + dürüst atla.
            logger.warning("finding %s validation failed, dropped: %s", fid, exc)
            result.degraded.append(f"{id_prefix}:finding_dropped")
            continue

        result.findings.append(finding)
        result.action_items.extend(actions)
    return result


async def assess(
    *,
    label: str,
    mode: str,
    criteria_block: str,
    manuscript,
    allow_external_ai: bool,
    id_prefix: str,
    evidence_context: str | None = None,
    force_dimension: str | None = None,
    tier: str = "flash",
    max_tokens: int = 8000,
) -> EngineResult:
    """Bir kriter bloğunu LLM ile değerlendir → sözleşme-geçerli EngineResult.

    Args:
        label: degraded sinyali / log etiketi (örn 'qualitative_engine').
        mode: ROLE_MODULES kaydı (örn 'qualitative_rigor').
        criteria_block: spec'ten BİREBİR kriter metni (prompt'a gömülür).
        allow_external_ai: False → SIFIR LLM çağrısı, boş sonuç + degraded.
        id_prefix: finding/action/anchor id'leri için benzersiz önek (dispatcher
            çakışmayı önlemek için boyut/motor başına ayrı verir).
        force_dimension: doluysa tüm finding.dimension buna ayarlanır (general motor
            rubrik boyutuna çıpalar); None ise LLM'in dimension'ı kullanılır (qual/quant
            alt-boyut başlıkları).
    """
    if not allow_external_ai:
        logger.info("%s: external AI blocked → no LLM call, honest empty", label)
        return EngineResult(degraded=[f"{label}:external_ai_blocked"])

    prompt = _build_prompt(
        manuscript=manuscript,
        criteria_block=criteria_block,
        evidence_context=evidence_context,
    )
    try:
        resp = await call(
            prompt,
            tier=tier,  # type: ignore[arg-type]
            mode=mode,
            structured_output_schema=_LLMFindingList,
            max_tokens=max_tokens,
        )
    except LLMServiceError as exc:
        logger.warning("%s LLM failed → honest empty (no findings): %s", label, exc)
        return EngineResult(degraded=[f"{label}:llm_unavailable"])

    parsed = resp.parsed_output
    if not isinstance(parsed, _LLMFindingList):
        logger.warning("%s parsed_output not _LLMFindingList → empty", label)
        return EngineResult(degraded=[f"{label}:bad_output"])

    return _to_findings(parsed, id_prefix=id_prefix, force_dimension=force_dimension)


__all__ = ["EngineResult", "assess"]
