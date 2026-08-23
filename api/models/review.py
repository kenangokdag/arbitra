"""F14 Hakemlik — peer-review domain models (Stanford-grade review).

Tek doğruluk SÖZLEŞMESİ: ingestion · OpenAlex atıf motoru · atıf-bağlam ·
kapsama · orkestrasyon (yazar/eleştirmen/editör) · rapor — hepsi bu modelleri
kullanır. HK-1: tüm modeller extra="forbid".

Yasa (F14_hakemlik_master §0):
  - Olgu katmanı deterministik+künyeli (CitationCheck/ContextFinding/CoverageGap/StatFinding).
  - Yargı katmanı serbest persona ama KANIT PAKETİ'ne çıpalı (ReviewReport.evidence_pack).
  - "yok ≠ uydurma" (HK-3): CitationStatus 3+1 değerli, fabricated yalnız pozitif çelişki.
  - atıf-bağlam belirsizlik birinci sınıf (HK-4): ContextSupport unverifiable_from_abstract dahil.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.providers.base import ProviderSnapshot

# --- enums / literals -------------------------------------------------------

ReviewMode = Literal["author", "editor"]
"""author = yazar göndermeden önce (Faz 1 pilot) · editor = dergi-tarafı (Faz 2)."""

ReviewLang = Literal["tr", "en"]

JobStatus = Literal[
    "queued",
    "parsing",
    "checking_citations",
    "checking_context",
    "coverage",
    "orchestrating",
    "assembling",
    "done",
    "failed",
]
"""Async iş durumları — FE ilerleme çarkı bu adımları gösterir (R-2)."""

CitationStatus = Literal[
    "resolved",
    "not_found_in_index",
    "fabricated",
    "retracted",
]
"""HK-3 — 'yok ≠ uydurma'. fabricated YALNIZ pozitif çelişki kanıtıyla
(DOI başka esere ait, vb). not_found_in_index = OpenAlex/S2'de çözülemedi,
ASLA suçlama değil."""

ContextSupport = Literal[
    "supported",
    "contradicted",
    "unverifiable_from_abstract",
]
"""HK-4 — belirsizlik birinci sınıf. Kesin suçlama yalnız 'contradicted'+kanıt;
özetten teyit edilemezse 'unverifiable_from_abstract' (suçlama değil)."""

SupportLevel = Literal[
    "full_text_verified",
    "abstract_only",
    "metadata_only",
    "unresolved",
    "contradictory",
    "not_applicable",
]
"""Pack 5+1 değer (P04-T03). Atıf-çözüm sinyallerinin deterministik fonksiyonu —
review_citation_service.map_support_level üretir. Mevcut ContextSupport (3-değer)
ile BİRLİKTE taşınır (support = ham bağlam yargısı; support_level = çözüm-derinliği
+ çelişki birleşik kanıt seviyesi). Tam metin doğrulama gelene kadar varsayılan üst
sınır abstract_only (asla full_text gibi sunma). CitationContextFinding bu tipe
referans verdiği için ContextSupport'tan SONRA, finding'den ÖNCE tanımlı olmalı."""

Verdict = Literal["accept", "minor_revision", "major_revision", "reject"]

DimensionKey = Literal[
    # Stanford 7
    "originality",
    "importance",
    "claims_supported",
    "soundness",
    "clarity",
    "community_value",
    "contextualization",
    # bizim 3 deterministik boyut (moat)
    "citation_integrity",
    "coverage_completeness",
    "statistical_consistency",
]

CriticKey = Literal[
    "skeptik",
    "yontemci",
    "sempatik",
    "citation_critic",
    "novelty_critic",
]

Severity = Literal["minor", "major", "blocker"]


# --- ingestion (S1) ---------------------------------------------------------


class ParsedReference(BaseModel):
    """Kaynakçadan çıkarılan tek referans + OpenAlex çözüm durumu (S1 doldurur,
    S2 status/evidence/openalex alanlarını günceller)."""

    model_config = ConfigDict(extra="forbid")

    index: int
    raw: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    parse_confidence: float = Field(0.0, ge=0.0, le=1.0)
    # S2 doldurur:
    status: CitationStatus = "not_found_in_index"
    openalex_id: str | None = None
    is_retracted: bool = False
    evidence: str | None = None  # neden bu status — künye/dürüstlük
    resolution_degraded: bool = False
    """§41 (2026-08-12): True SADECE OpenAlex/S2 servis HATASI (ağ/429/vb.)
    status'ü not_found_in_index'e düşürdüyse — yani "aslında çözülemedi, çünkü
    sağlayıcı yanıt veremedi" (gerçek eşleşme-yokluğu DEĞİL). Genuine not_found
    (DOI 404, zayıf başlık eşleşmesi, DOI+başlık yok) için False kalır. resolve_all
    bunu CitationIntegritySummary.provider_errors'a toplar; review_service.py
    EvidencePack.degraded_features'a görünür yazar (önceden SESSİZDİ — guardian
    bulgusu, PDF_PIPELINE_CALISMA_GUNLUGU.md §40)."""


class InTextCitation(BaseModel):
    """Metin-içi atıf işareti + çevresindeki iddia cümlesi."""

    model_config = ConfigDict(extra="forbid")

    marker: str
    sentence: str
    section: str | None = None
    ref_index: int | None = None  # ParsedReference.index eşleşmesi


class StatFinding(BaseModel):
    """statcheck (Nuijten) — mevcut motor yeniden kullanılır, buraya köprülenir."""

    model_config = ConfigDict(extra="forbid")

    test_type: str
    reported_p: float | None = None
    computed_p: float | None = None
    status: Literal["green", "yellow", "red"]
    match_text: str


class ManuscriptMeta(BaseModel):
    """Parse sonrası yapılandırılmış makale künyesi (gövde metni ayrı taşınır)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    abstract: str | None = None
    language: ReviewLang = "en"
    section_titles: list[str] = Field(default_factory=list)
    word_count: int = 0
    reference_count: int = 0
    parse_confidence: float = Field(0.0, ge=0.0, le=1.0)
    parse_warnings: list[str] = Field(default_factory=list)  # "okuyamadım" dürüst durumu


class Manuscript(BaseModel):
    """S1 çıktısı — orkestrasyon + motor girdisi."""

    model_config = ConfigDict(extra="forbid")

    meta: ManuscriptMeta
    full_text: str
    references: list[ParsedReference] = Field(default_factory=list)
    in_text_citations: list[InTextCitation] = Field(default_factory=list)


# --- deterministik motor çıktıları (S2/S3) — KANIT PAKETİ -------------------


class CitationContextFinding(BaseModel):
    """S3 — 'iddia [n] kaynağı destekliyor mu' (özet/TLDR-seviyesi, HK-4)."""

    model_config = ConfigDict(extra="forbid")

    ref_index: int
    claim: str
    support: ContextSupport
    support_level: SupportLevel = "unresolved"
    """6-değerli kanıt seviyesi (map_support_level üretir). check_context HER
    finding'i atıf-çözüm sinyalleriyle doldurur. Default 'unresolved' = sinyal
    olmadan bunu kuran (eski/test) çağıranlar için güvenli, suçlama-olmayan üst
    sınır (kaynak çözüldüğü teyit edilmeden 'doğrulandı' demez). ADDITIVE:
    extra='forbid' altında default'lu alan eklemek geriye-uyumludur."""
    evidence: str | None = None
    cited_abstract_excerpt: str | None = None


class CoverageGap(BaseModel):
    """S3 — alanda atlanmış seminal/zorunlu iş (OpenAlex grafı)."""

    model_config = ConfigDict(extra="forbid")

    openalex_id: str
    title: str
    year: int | None = None
    cited_by_count: int = 0
    reason: str


class CitationIntegritySummary(BaseModel):
    """S2 özet sayaçları (FE rozet)."""

    model_config = ConfigDict(extra="forbid")

    total: int = 0
    resolved: int = 0
    not_found_in_index: int = 0
    fabricated: int = 0
    retracted: int = 0
    provider_errors: int = 0
    """§41: not_found_in_index içinde SAKLI kalan, aslında sağlayıcı-hatası
    kaynaklı alt-küme (ParsedReference.resolution_degraded=True sayısı). 0 ==
    "hiç servis hatası olmadı" DEMEK DEĞİL — yalnız Bu KOŞUMDA görülenleri sayar."""
    semantic_scholar_recovered: int = 0
    """2026-08-23: OpenAlex not_found_in_index dedikten SONRA Semantic Scholar
    fallback'inin resolved'a YÜKSELTTİĞİ referans sayısı (engine/providers/
    semantic_scholar.py). `resolved` sayacına ZATEN dahildir — bu sadece
    KAYNAĞIN ne kadarının S2'den geldiğini gösteren ayrı, additive bir sayaç
    (gözlemlenebilirlik — fabricated/retracted'a hiç dokunmaz, sadece bu)."""


class EvidencePack(BaseModel):
    """Deterministik OLGULAR — orkestrasyonun çıpası. LLM bunu UYDURAMAZ."""

    model_config = ConfigDict(extra="forbid")

    citation_integrity: CitationIntegritySummary = Field(
        default_factory=CitationIntegritySummary
    )
    references: list[ParsedReference] = Field(default_factory=list)
    context_findings: list[CitationContextFinding] = Field(default_factory=list)
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
    stat_findings: list[StatFinding] = Field(default_factory=list)
    degraded_features: list[str] = Field(default_factory=list)
    """BE-2 / P02-T05: bir stage provider arızası nedeniyle KISMİ/atlandıysa burada
    GÖRÜNÜR işaretlenir (sessiz boş-liste YASAK). Örn 'coverage:openalex_unavailable'.
    Boş liste 'sorun yok' demektir; degraded varsa rapor bunu kullanıcıya gösterir."""
    provider_snapshots: list[ProviderSnapshot] = Field(default_factory=list)
    """FAZ D (BE-2 / P02-T03/T04): her OpenAlex kullanan stage'in ProviderSnapshot'ı
    (provider + status + query_hash + result_count + limitations). Her evidence
    sonucu provider+status taşır (evidence_provider_spec.md §Başarı kapısı); arıza
    degraded_features'ın YANINDA burada da yapılandırılmış görünür (çoğaltma değil,
    zenginleştirme). ADDITIVE: default-boş → v1/v2 tüketici ve testler kırılmaz.
    DB: review_job.evidence_pack jsonb (0041) → migration GEREKMEZ."""


# --- orkestrasyon (S4) ------------------------------------------------------


class CritiqueIssue(BaseModel):
    """Eleştirmenin taslakta bulduğu sorun."""

    model_config = ConfigDict(extra="forbid")

    target: str  # rapor bölümü / iddia
    problem: str
    severity: Severity = "minor"
    grounded: bool = True  # kanıt paketine dayanıyor mu (çıpasız iddia avı)


class Critique(BaseModel):
    """Tek eleştirmen geçişi."""

    model_config = ConfigDict(extra="forbid")

    critic: CriticKey
    issues: list[CritiqueIssue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    """Eleştirmenin gördüğü GERÇEK güçlü yanlar (metne dayalı, çıpasız övgü
    YASAK). 2026-08-05 guardian bulgusu: bu alan yokken sempatik critic'in
    'önce 1-2 güçlü yan say' talimatının koyacağı yer yoktu — övgü ya
    kayboluyordu ya da issues[].problem alanına zorla negatif çerçevede
    sıkışıyordu, editöre giden girdi yapısal olarak hep negatif ağırlıklıydı."""


# --- rapor (S5) -------------------------------------------------------------


class GroupedPoints(BaseModel):
    """Strengths/Weaknesses alt-boyutlu grup (Stanford yapısı)."""

    model_config = ConfigDict(extra="forbid")

    category: str
    points: list[str] = Field(default_factory=list)


class DetailedComment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str  # technical_soundness | experimental | related_work | impact
    comment: str
    evidence_ref: str | None = None  # kanıt paketine referans (HK-5)


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: DimensionKey
    score: float = Field(..., ge=1.0, le=10.0)
    rationale: str


class ReviewProvenance(BaseModel):
    """Künye + determinizm dürüstlüğü (HK-6)."""

    model_config = ConfigDict(extra="forbid")

    model_used: str
    persona_version: str
    engine_version: str
    generated_at: datetime
    deterministic_engine: bool = True  # atıf/stat/kapsama bit-kararlı
    judgment_reproducible: bool = False  # LLM yargısı bit-kararlı DEĞİL — dürüst işaret


class ReviewReport(BaseModel):
    """S5 — nihai Stanford-yapı rapor."""

    model_config = ConfigDict(extra="forbid")

    mode: ReviewMode
    language: ReviewLang
    manuscript_meta: ManuscriptMeta
    summary: str
    strengths: list[GroupedPoints] = Field(default_factory=list)
    weaknesses: list[GroupedPoints] = Field(default_factory=list)
    detailed_comments: list[DetailedComment] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    overall_assessment: str
    verdict: Verdict
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    final_score: float | None = Field(None, ge=1.0, le=10.0)
    evidence_pack: EvidencePack = Field(default_factory=EvidencePack)
    provenance: ReviewProvenance
    ethics_notice: str | None = None  # editör modu guardrail (R-4)
    editor_digest: str | None = None
    """Editör modu KARAR-DESTEĞİ üst-özeti (yayın kararı + güven + 'neden').

    Yalnız mode='editor' iken dolar (author modunda None). Mevcut summary/
    overall_assessment uzun yazar-geri-bildirimidir; editörün hızlı okuması için
    AYRI, kısa, karar-odaklı bir alan gerekir — bu yüzden opsiyonel yeni alan
    (extra=forbid uyumlu, default None, author davranışı bozulmaz)."""

    # --- worldclass v2 (additive, default-boş → v1 tüketici/test korunur) ---
    schema_version: str = "review_report.v1"
    """v1 üreticiler 'review_report.v1' bırakır; ENG-3 v2 üretince 'review_report.v2'."""
    document_classification: DocumentClassification | None = None
    executive_verdict: ExecutiveVerdict | None = None
    risk_radar: list[RiskRadarItem] = Field(default_factory=list)
    reviewer_council: list[ReviewerCouncilItem] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    action_plan: list[ActionItem] = Field(default_factory=list)
    section_reviews: list[SectionReview] = Field(default_factory=list)
    disclosure: AIUsageDisclosure | None = None


# --- async iş + API sözleşmesi ---------------------------------------------


class ReviewJob(BaseModel):
    """Async iş kaydı (review_job tablosu)."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    user_id: str
    mode: ReviewMode
    language: ReviewLang
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=1.0)
    step_label: str = ""
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    report: ReviewReport | None = None

    # --- worldclass v2 (additive) ---
    lifecycle: JobLifecycle | None = None  # flat status'ün yanında üst-seviye
    stages: list[ReviewStageState] = Field(default_factory=list)
    privacy: PrivacyConfig | None = None
    idempotency_key: str | None = None


class ReviewUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: JobStatus


class ReviewStatusResponse(BaseModel):
    """FE ilerleme çarkı bunu poll eder (R-2)."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=1.0)
    step_label: str = ""
    error: str | None = None
    stages: list[ReviewStageState] = Field(default_factory=list)
    """G4 — per-stage durum listesi (FE StageTimeline çıplak çark yerine bunu
    okur). run_pipeline her aşamada review_job.stages'a yazar; get_status döndürür.
    Default-boş → v1 tüketici/test kırılmaz (additive)."""


class ReviewReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    report: ReviewReport


# --- versiyon karşılaştırma (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17) --------
# Faz 1: SADECE deterministik üst-seviye diff (verdict/hazırlık puanı/boyut
# skoru). Bulgu-eşleştirme ("hangi Finding kapandı") BİLİNÇLİ olarak YOK —
# Finding.finding_id iki motor koşumu arasında stabil değil (_engine_base.py
# sıra-bazlı üretiyor), bulanık eşleştirme ayrı, guardian gerektiren bir
# Faz 2 kararı (plan §5).


class DimensionScoreDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: DimensionKey
    previous_score: float | None
    current_score: float | None
    delta: float | None
    """current - previous. İki taraftan biri (veya ikisi) yoksa None — dürüst
    eksik-veri işareti, tahmin/interpolasyon YOK."""


class VersionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_job_id: UUID
    previous_verdict: Verdict
    current_verdict: Verdict
    verdict_changed: bool
    previous_readiness_score: float | None
    current_readiness_score: float | None
    readiness_delta: float | None
    dimension_deltas: list[DimensionScoreDelta] = Field(default_factory=list)


class VersionComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    comparison: VersionComparison | None
    """None = parent_job_id set edilmemiş (ilk yükleme) — hata DEĞİL, normal
    durum. 404 fırlatılmaz."""


# ===========================================================================
# WORLD-CLASS v2 SÖZLEŞME (additive — v1 alanları DOKUNULMAZ, 688 test korunur)
# ---------------------------------------------------------------------------
# Bu blok pack'in "report_report.v2" hedefini karşılar. TÜM yeni alanlar
# default-boş/None → mevcut v1 tüketiciler ve testler kırılmaz. Motor (ENG-3)
# bu alanları doldurur; FE cockpit (FE-COCKPIT) okur. Backward-compat:
# ReviewReport.schema_version + ReviewReport'a eklenen opsiyonel v2 alanları.
# ===========================================================================

# --- sınıflandırma (P03-T01/T02) -------------------------------------------

DocumentType = Literal[
    "journal_article",
    "conference_paper",
    "thesis",
    "grant_proposal",
    "preprint",
    "technical_report",
    "book_chapter",
    "unknown",
]

StudyDesign = Literal[
    "qualitative",
    "quantitative",
    "mixed_methods",
    "systematic_review",
    "meta_analysis",
    "scoping_review",
    "theoretical",
    "conceptual",
    "design_science",
    "computational_modeling",
    "dataset_resource",
    "software_tool",
    "replication",
    "registered_report",
    "case_study",
    "protocol",
    "unknown",
]


class DocumentClassification(BaseModel):
    """Belge + çalışma türü sınıflandırması (confidence + rationale + override).

    'unknown' + düşük confidence → generic değil GÜVENLİ-minimal review (P03 stop_if).
    user_*_override doluysa model tahmininin yerine geçer (reconcile)."""

    model_config = ConfigDict(extra="forbid")

    document_type: DocumentType = "unknown"
    document_type_confidence: float = Field(0.0, ge=0.0, le=1.0)
    study_design: StudyDesign = "unknown"
    study_design_confidence: float = Field(0.0, ge=0.0, le=1.0)
    rationale: str | None = None
    user_document_type_override: DocumentType | None = None
    user_study_design_override: StudyDesign | None = None

    @property
    def effective_document_type(self) -> str:
        return self.user_document_type_override or self.document_type

    @property
    def effective_study_design(self) -> str:
        return self.user_study_design_override or self.study_design


# --- gizlilik / external-AI consent (P01-T03) ------------------------------

ConfidentialityMode = Literal["author_owned", "reviewer_confidential"]
ExternalAIConsent = Literal["allowed", "blocked", "requires_private_mode"]


class PrivacyConfig(BaseModel):
    """Create-review akışında ZORUNLU. reviewer_confidential → external_ai_consent
    default 'blocked' (P01-T03). Gate review_service'te consent'i denetler;
    FE-only enforcement YETMEZ (backend zorunlu)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["privacy_config.v1"] = "privacy_config.v1"
    is_author: bool = True
    confidentiality_mode: ConfidentialityMode = "author_owned"
    external_ai_consent: ExternalAIConsent = "allowed"
    retention_days: int = Field(30, ge=1, le=365)


# --- durable stage modeli (P02-T01) ----------------------------------------

ReviewStage = Literal[
    "file_security_scan",
    "parse_document",
    "classify",
    "extract_references",
    "resolve_references",
    "retrieve_evidence",
    "select_guidelines",
    "run_academic_engines",
    "run_reviewer_council",
    "editor_synthesis",
    "build_report",
    "prepare_exports",
]

StageStatus = Literal[
    "queued", "running", "completed", "degraded", "failed", "skipped"
]

JobLifecycle = Literal[
    "queued", "running", "stage_failed", "completed", "cancelled"
]
"""Üst-seviye yaşam döngüsü (flat JobStatus'ün YANINDA, additive). FE bunu
veya stage[] listesini okuyabilir; v1 status alanı korunur."""


class ReviewStageState(BaseModel):
    """Tek stage durumu — DB checkpoint + FE timeline (spinner DEĞİL)."""

    model_config = ConfigDict(extra="forbid")

    stage: ReviewStage
    status: StageStatus = "queued"
    progress: float = Field(0.0, ge=0.0, le=1.0)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    degraded_reason: str | None = None
    summary: str | None = None


# --- v2 bulgu / aksiyon / çıpa (P04-T01, P06-T01) --------------------------


class ManuscriptAnchor(BaseModel):
    """Bulgunun makaledeki kesin yeri — FE tek tıkla quote drawer açar."""

    model_config = ConfigDict(extra="forbid")

    anchor_id: str  # ingestion'dan stable id (örn 'methods.p4')
    section: str | None = None
    quote: str | None = None


ActionPriority = Literal["P0", "P1", "P2"]
EffortGain = Literal["low", "medium", "high"]


class ActionItem(BaseModel):
    """Revizyon görevi — rapor→uygulanabilir iş (P06-T03)."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    priority: ActionPriority
    effort: EffortGain = "medium"
    expected_gain: EffortGain = "medium"
    target_section: str | None = None
    instruction: str
    acceptance_check: str | None = None
    linked_finding_ids: list[str] = Field(default_factory=list)


SeverityV2 = Literal["critical", "major", "moderate", "minor", "info"]


class Finding(BaseModel):
    """v2 bulgu — anchor/severity/confidence/action zorunluluğu (P06-T01 mandatory).

    KURAL (assemble sonrası doğrulanır, motorda enforce edilir):
      severity in (critical, major) → en az 1 action_item ZORUNLU
                                     → en az 1 manuscript_anchor VEYA global_issue=True gerekçesi."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    dimension: str
    severity: SeverityV2 = "moderate"
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    title: str
    summary: str = ""
    manuscript_anchors: list[ManuscriptAnchor] = Field(default_factory=list)
    # G1 (NOT): 'evidence_anchors' KALDIRILDI. Bulgular akademik motorlarda LLM ile
    # evidence_pack'TEN BAĞIMSIZ üretilir (engine/academic/_engine_base._to_findings);
    # motor çıktısı hangi evidence id'sini kullandığını döndürmez ve kanıt nesneleri
    # (CitationContextFinding/StatFinding) stable id taşımaz. Finding→evidence linki
    # ancak fuzzy metin eşleştirmeyle KURULABİLİRDİ = uydurma ilişki. Anti-fabrikasyon
    # gereği ölü konteyneri taşımak yerine SÖZLEŞMEDEN ÇIKARILDI (boş alan = yalan).
    reasoning_public: str | None = None
    limitations: list[str] = Field(default_factory=list)
    action_item_ids: list[str] = Field(default_factory=list)
    global_issue: bool = False  # anchor yoksa "global belge sorunu" gerekçesi

    @model_validator(mode="after")
    def _enforce_high_severity_contract(self) -> Finding:
        """P06-T01 mandatory: critical/major bulgu → en az 1 action ZORUNLU
        + (en az 1 manuscript_anchor VEYA global_issue gerekçesi). Bu kapı motorun
        çıpasız/aksiyonsuz yüksek-önem bulgusu üretmesini sözleşme düzeyinde engeller."""
        if self.severity in ("critical", "major"):
            if not self.action_item_ids:
                raise ValueError(
                    f"Finding {self.finding_id}: severity={self.severity} en az 1 action_item gerektirir"
                )
            if not self.manuscript_anchors and not self.global_issue:
                raise ValueError(
                    f"Finding {self.finding_id}: severity={self.severity} manuscript_anchor VEYA global_issue gerektirir"
                )
        return self


class RiskRadarItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    score: float | None = Field(None, ge=0.0, le=100.0)
    """None = bu boyut bu doküman türünün rubric'inde hiç DEĞERLENDİRİLMEDİ —
    'sorun bulunamadı' (yüksek skor) ile karıştırılmasın (2026-08-07 guardian
    bulgusu: eskiden ikisi de aynı 100 skorunu alıyordu, 'değerlendirilmedi'
    durumu sessizce 'mükemmel' gibi görünüyordu — kendi başına bir şişirme
    kaynağıydı, LLM önyargısından bağımsız)."""
    severity: SeverityV2 = "moderate"
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    why_it_matters: str = ""


CouncilRole = Literal[
    "methodologist",
    "field_expert",
    "skeptical_reviewer",
    "constructive_reviewer",
    "citation_auditor",
    "ethics_reviewer",
    "statistics_reviewer",
    "editor_synthesizer",
]


class ReviewerCouncilItem(BaseModel):
    """Typed council çıktısı — serbest metin DEĞİL (P06-T02)."""

    model_config = ConfigDict(extra="forbid")

    role: CouncilRole
    stance: str = ""
    summary: str = ""
    key_objection: str | None = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    finding_ids: list[str] = Field(default_factory=list)


class ExecutiveVerdict(BaseModel):
    """Raporun ilk ekranı — 'ne kadar kötü/iyi ve önce ne yapmalıyım' (P06-T01)."""

    model_config = ConfigDict(extra="forbid")

    overall_readiness_score: float = Field(..., ge=0.0, le=100.0)
    recommended_decision: Verdict
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    top_fatal_risks: list[str] = Field(default_factory=list)
    one_sentence_diagnosis: str = ""


class SectionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    status: Literal["ok", "weak", "broken", "missing"] = "ok"
    what_works: str | None = None
    what_breaks: str | None = None
    anchor_ids: list[str] = Field(default_factory=list)
    action_item_ids: list[str] = Field(default_factory=list)


class AIUsageDisclosure(BaseModel):
    """Rapor metadata'sında AI kullanım açıklaması (P01-T03)."""

    model_config = ConfigDict(extra="forbid")

    external_ai_used: bool = False
    providers: list[str] = Field(default_factory=list)
    confidentiality_mode: ConfidentialityMode = "author_owned"
    degraded_due_to_consent: bool = False
    note: str | None = None


# --- forward-ref çözümü (v1 modeller v2 tiplerine string-annotation ile bağlı) ---
# from __future__ import annotations nedeniyle tüm annotation'lar lazy; v2 tipleri
# modül sonunda tanımlı olduğundan rebuild burada güvenle resolve eder.
ReviewReport.model_rebuild()
ReviewJob.model_rebuild()
ReviewReportResponse.model_rebuild()
ReviewStatusResponse.model_rebuild()  # G4: stages → ReviewStageState (modül sonunda tanımlı)
