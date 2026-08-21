// F14 Hakemlik — FE tip + API katmanı.
// Tip sözleşmesi api/models/review.py (ReviewReport vd.) ile birebir aynalanır.
// Multipart upload apiFetch (JSON-only) ile yapılamaz → fetch doğrudan kullanılır
// ama Authorization header api.ts deseninden (getToken) alınır.

import { getToken } from "./auth";
import { ApiError, apiFetch } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// --- enums / literals (api/models/review.py ile aynı) ----------------------

export type ReviewMode = "author" | "editor";
export type ReviewLang = "tr" | "en";

export type JobStatus =
  | "queued"
  | "parsing"
  | "checking_citations"
  | "checking_context"
  | "coverage"
  | "orchestrating"
  | "assembling"
  | "done"
  | "failed";

export type CitationStatus =
  | "resolved"
  | "not_found_in_index"
  | "fabricated"
  | "retracted";

export type ContextSupport =
  | "supported"
  | "contradicted"
  | "unverifiable_from_abstract";

export type Verdict = "accept" | "minor_revision" | "major_revision" | "reject";

export type DimensionKey =
  | "originality"
  | "importance"
  | "claims_supported"
  | "soundness"
  | "clarity"
  | "community_value"
  | "contextualization"
  | "citation_integrity"
  | "coverage_completeness"
  | "statistical_consistency";

// --- model tipleri ---------------------------------------------------------

export type ParsedReference = {
  index: number;
  raw: string;
  title: string | null;
  authors: string[];
  year: number | null;
  doi: string | null;
  venue: string | null;
  parse_confidence: number;
  status: CitationStatus;
  openalex_id: string | null;
  is_retracted: boolean;
  evidence: string | null;
};

export type StatFinding = {
  test_type: string;
  reported_p: number | null;
  computed_p: number | null;
  status: "green" | "yellow" | "red";
  match_text: string;
};

export type ManuscriptMeta = {
  title: string | null;
  abstract: string | null;
  language: ReviewLang;
  section_titles: string[];
  word_count: number;
  reference_count: number;
  parse_confidence: number;
  parse_warnings: string[];
};

export type CitationContextFinding = {
  ref_index: number;
  claim: string;
  support: ContextSupport;
  // 6-değerli kanıt seviyesi (BE map_support_level üretir). EvidenceBadge tüketir.
  support_level: SupportLevel;
  evidence: string | null;
  cited_abstract_excerpt: string | null;
};

export type CoverageGap = {
  openalex_id: string;
  title: string;
  year: number | null;
  cited_by_count: number;
  reason: string;
};

export type CitationIntegritySummary = {
  total: number;
  resolved: number;
  not_found_in_index: number;
  fabricated: number;
  retracted: number;
};

export type EvidencePack = {
  citation_integrity: CitationIntegritySummary;
  references: ParsedReference[];
  context_findings: CitationContextFinding[];
  coverage_gaps: CoverageGap[];
  stat_findings: StatFinding[];
};

export type GroupedPoints = {
  category: string;
  points: string[];
};

export type DetailedComment = {
  area: string;
  comment: string;
  evidence_ref: string | null;
};

export type DimensionScore = {
  key: DimensionKey;
  score: number;
  rationale: string;
};

export type ReviewProvenance = {
  model_used: string;
  persona_version: string;
  engine_version: string;
  generated_at: string;
  deterministic_engine: boolean;
  judgment_reproducible: boolean;
};

// --- worldclass v2 tipleri (additive — backend api/models/review.py v2 aynası) ---

export type DocumentType =
  | "journal_article"
  | "conference_paper"
  | "thesis"
  | "grant_proposal"
  | "preprint"
  | "technical_report"
  | "book_chapter"
  | "unknown";

export type StudyDesign =
  | "qualitative"
  | "quantitative"
  | "mixed_methods"
  | "systematic_review"
  | "meta_analysis"
  | "scoping_review"
  | "theoretical"
  | "conceptual"
  | "design_science"
  | "computational_modeling"
  | "dataset_resource"
  | "software_tool"
  | "replication"
  | "registered_report"
  | "case_study"
  | "protocol"
  | "unknown";

export type DocumentClassification = {
  document_type: DocumentType;
  document_type_confidence: number;
  study_design: StudyDesign;
  study_design_confidence: number;
  rationale: string | null;
  user_document_type_override: DocumentType | null;
  user_study_design_override: StudyDesign | null;
};

export type ConfidentialityMode = "author_owned" | "reviewer_confidential";
export type ExternalAIConsent = "allowed" | "blocked" | "requires_private_mode";

export type PrivacyConfig = {
  version: "privacy_config.v1";
  is_author: boolean;
  confidentiality_mode: ConfidentialityMode;
  external_ai_consent: ExternalAIConsent;
  retention_days: number;
};

export type ReviewStage =
  | "file_security_scan"
  | "parse_document"
  | "classify"
  | "extract_references"
  | "resolve_references"
  | "retrieve_evidence"
  | "select_guidelines"
  | "run_academic_engines"
  | "run_reviewer_council"
  | "editor_synthesis"
  | "build_report"
  | "prepare_exports";

export type StageStatus =
  | "queued"
  | "running"
  | "completed"
  | "degraded"
  | "failed"
  | "skipped";

export type ReviewStageState = {
  stage: ReviewStage;
  status: StageStatus;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  degraded_reason: string | null;
  summary: string | null;
};

export type SupportLevel =
  | "full_text_verified"
  | "abstract_only"
  | "metadata_only"
  | "unresolved"
  | "contradictory"
  | "not_applicable";

export type SeverityV2 = "critical" | "major" | "moderate" | "minor" | "info";
export type ActionPriority = "P0" | "P1" | "P2";
export type EffortGain = "low" | "medium" | "high";

export type ManuscriptAnchor = {
  anchor_id: string;
  section: string | null;
  quote: string | null;
};

export type ActionItem = {
  action_id: string;
  priority: ActionPriority;
  effort: EffortGain;
  expected_gain: EffortGain;
  target_section: string | null;
  instruction: string;
  acceptance_check: string | null;
  linked_finding_ids: string[];
};

export type Finding = {
  finding_id: string;
  dimension: string;
  severity: SeverityV2;
  confidence: number;
  title: string;
  summary: string;
  manuscript_anchors: ManuscriptAnchor[];
  reasoning_public: string | null;
  limitations: string[];
  action_item_ids: string[];
  global_issue: boolean;
};

export type RiskRadarItem = {
  dimension: string;
  // null = bu boyut bu doküman türü için hiç değerlendirilmedi ("sorun yok"
  // ile karıştırılmasın — 2026-08-07 backend fix'i, bkz. report_synthesis.py).
  score: number | null;
  severity: SeverityV2;
  confidence: number;
  why_it_matters: string;
};

export type CouncilRole =
  | "methodologist"
  | "field_expert"
  | "skeptical_reviewer"
  | "constructive_reviewer"
  | "citation_auditor"
  | "ethics_reviewer"
  | "statistics_reviewer"
  | "editor_synthesizer";

export type ReviewerCouncilItem = {
  role: CouncilRole;
  stance: string;
  summary: string;
  key_objection: string | null;
  confidence: number;
  finding_ids: string[];
};

export type ExecutiveVerdict = {
  overall_readiness_score: number;
  recommended_decision: Verdict;
  confidence: number;
  top_fatal_risks: string[];
  one_sentence_diagnosis: string;
};

export type SectionReview = {
  section: string;
  status: "ok" | "weak" | "broken" | "missing";
  what_works: string | null;
  what_breaks: string | null;
  anchor_ids: string[];
  action_item_ids: string[];
};

export type AIUsageDisclosure = {
  external_ai_used: boolean;
  providers: string[];
  confidentiality_mode: ConfidentialityMode;
  degraded_due_to_consent: boolean;
  note: string | null;
};

export type ReviewReport = {
  mode: ReviewMode;
  language: ReviewLang;
  manuscript_meta: ManuscriptMeta;
  summary: string;
  strengths: GroupedPoints[];
  weaknesses: GroupedPoints[];
  detailed_comments: DetailedComment[];
  questions: string[];
  overall_assessment: string;
  verdict: Verdict;
  dimension_scores: DimensionScore[];
  final_score: number | null;
  evidence_pack: EvidencePack;
  provenance: ReviewProvenance;
  ethics_notice: string | null;
  editor_digest: string | null;
  // --- worldclass v2 (additive, opsiyonel — v1 render bozulmaz) ---
  schema_version?: string;
  document_classification?: DocumentClassification | null;
  executive_verdict?: ExecutiveVerdict | null;
  risk_radar?: RiskRadarItem[];
  reviewer_council?: ReviewerCouncilItem[];
  findings?: Finding[];
  action_plan?: ActionItem[];
  section_reviews?: SectionReview[];
  disclosure?: AIUsageDisclosure | null;
};

// --- API response tipleri --------------------------------------------------

export type ReviewUploadResponse = {
  job_id: string;
  status: JobStatus;
};

export type ReviewStatusResponse = {
  job_id: string;
  status: JobStatus;
  progress: number;
  step_label: string;
  error: string | null;
  // G4 — CANLI: backend ReviewStatusResponse.stages'i her aşamada doldurur
  // (api/models/review.py:397, default_factory=list). StageTimeline bununla
  // çıplak çark yerine gerçek aşama listesi gösterir. Boş liste de olabilir
  // (henüz aşama yazılmadıysa) → opsiyonel; v1 davranışı bozulmaz.
  stages?: ReviewStageState[];
};

export type ReviewReportResponse = {
  job_id: string;
  report: ReviewReport;
};

// --- admin response tipleri ------------------------------------------------

export type AdminJob = {
  job_id: string;
  user_id: string;
  mode: ReviewMode;
  language: ReviewLang;
  status: JobStatus;
  progress: number;
  step_label: string;
  created_at: string;
  updated_at: string;
  error: string | null;
  filename?: string | null;
};

export type AdminJobsResponse = {
  jobs: AdminJob[];
};

export type AdminStats = {
  total: number;
  done: number;
  failed: number;
  in_progress: number;
};

// --- kullanıcı-kapsamlı job listesi + versiyon karşılaştırma ---------------
// VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 — api/models/review.py aynası.

export type UserJob = {
  job_id: string;
  mode: ReviewMode;
  language: ReviewLang;
  status: JobStatus;
  source_name: string | null;
  source_kind: string | null;
  created_at: string;
  updated_at: string;
};

export type UserJobsResponse = {
  jobs: UserJob[];
};

export type DimensionScoreDelta = {
  key: DimensionKey;
  previous_score: number | null;
  current_score: number | null;
  delta: number | null;
};

export type VersionComparison = {
  parent_job_id: string;
  previous_verdict: Verdict;
  current_verdict: Verdict;
  verdict_changed: boolean;
  previous_readiness_score: number | null;
  current_readiness_score: number | null;
  readiness_delta: number | null;
  dimension_deltas: DimensionScoreDelta[];
};

export type VersionComparisonResponse = {
  job_id: string;
  comparison: VersionComparison | null;
};

// --- global app teması (FAZ 4A/4B — api/models/theme.py aynası) ------------
// Font anahtarları backend allowlist'iyle BİREBİR (api/models/theme.py:24-27).
export type FontSansKey = "inter" | "source-sans";
export type FontSerifKey = "lora" | "newsreader" | "source-serif";

/** GET /api/app/theme response. updated_by/updated_at yalnız response künyesi. */
export type ThemeSettings = {
  accent_color: string; // #RRGGBB
  bg_color: string; // #RRGGBB
  ink_color: string; // #RRGGBB
  font_sans: FontSansKey;
  font_serif: FontSerifKey;
  updated_by?: string | null;
  updated_at?: string | null;
};

/** PATCH body — yalnız 5 düzenlenebilir alan (backend extra="forbid"; künye yollanmaz). */
export type ThemeUpdate = {
  accent_color: string;
  bg_color: string;
  ink_color: string;
  font_sans: FontSansKey;
  font_serif: FontSerifKey;
};

// --- API çağrıları ---------------------------------------------------------

/** Multipart upload — apiFetch JSON-only olduğu için doğrudan fetch.
 *  Content-Type elle SET EDİLMEZ (browser FormData boundary'yi kendi koyar).
 *
 *  Gizlilik alanları (SEC-2) backend api/routes/review.py:155-158 Form imzasıyla
 *  BİREBİR eşleşir: is_author / confidentiality_mode / external_ai_consent /
 *  retention_days. Sadece kullanıcının ayarladığı değer gönderilir; verilmezse
 *  backend default'una (Form(...) varsayılanları) bırakılır. */
export async function uploadReview(args: {
  file: File;
  mode: ReviewMode;
  language: ReviewLang;
  // --- gizlilik / rıza (SEC-2 — opsiyonel; verilirse backend Form'una gider) ---
  isAuthor?: boolean;
  confidentialityMode?: ConfidentialityMode;
  externalAiConsent?: ExternalAIConsent;
  retentionDays?: number;
  // VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.1 — kullanıcının BİLİNÇLİ seçtiği
  // önceki versiyon (otomatik/sessiz eşleştirme YOK).
  parentJobId?: string;
  signal?: AbortSignal;
}): Promise<ReviewUploadResponse> {
  const form = new FormData();
  form.append("file", args.file);
  form.append("mode", args.mode);
  form.append("language", args.language);

  // Backend Form alan adları (api/routes/review.py:155-158) — birebir.
  if (args.isAuthor !== undefined) {
    // FastAPI bool Form'u "true"/"false" string'ini çözer.
    form.append("is_author", args.isAuthor ? "true" : "false");
  }
  if (args.confidentialityMode !== undefined) {
    form.append("confidentiality_mode", args.confidentialityMode);
  }
  if (args.externalAiConsent !== undefined) {
    form.append("external_ai_consent", args.externalAiConsent);
  }
  if (args.retentionDays !== undefined) {
    form.append("retention_days", String(args.retentionDays));
  }
  if (args.parentJobId !== undefined) {
    form.append("parent_job_id", args.parentJobId);
  }

  const res = await fetch(`${API_URL}/api/review/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
    signal: args.signal,
  });

  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : undefined;
  } catch {
    parsed = text;
  }

  if (!res.ok) {
    const message =
      parsed && typeof parsed === "object" && "detail" in parsed
        ? `API ${res.status}: ${JSON.stringify((parsed as { detail: unknown }).detail)}`
        : `API ${res.status}`;
    throw new ApiError(res.status, parsed, message);
  }

  return parsed as ReviewUploadResponse;
}

export function fetchReviewStatus(
  jobId: string,
  signal?: AbortSignal,
): Promise<ReviewStatusResponse> {
  return apiFetch<ReviewStatusResponse>(`/api/review/${jobId}/status`, {
    signal,
  });
}

export function fetchReviewReport(
  jobId: string,
  signal?: AbortSignal,
): Promise<ReviewReportResponse> {
  return apiFetch<ReviewReportResponse>(`/api/review/${jobId}/report`, {
    signal,
  });
}

/** GET /api/review/{job_id}/export.docx — hakem raporunu .docx olarak indir.
 *  RAPOR_DOCX_EXPORT_2026-08-16 §3.1. apiFetch JSON-only olduğu için
 *  tts-api.ts'deki desenle AYNI: native fetch + Authorization + .blob(). */
export async function fetchReviewReportDocx(
  jobId: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/review/${jobId}/export.docx`, {
    headers: {
      Authorization: `Bearer ${getToken()}`,
    },
    signal,
  });

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      detail = await res.json();
    } catch {
      // ignore — gövde docx değildi, hata da JSON değil
    }
    throw new ApiError(res.status, detail, `export.docx API ${res.status}`);
  }

  return res.blob();
}

/** DELETE /api/review/jobs/{job_id} — sahip-yalnız kalıcı silme.
 *  Backend 204 (gövdesiz) döner → apiFetch undefined verir, void döneriz.
 *  404 → ApiError(status=404) (çağıranın işi değil ya da zaten silinmiş). */
export async function deleteReviewJob(jobId: string): Promise<void> {
  await apiFetch<void>(`/api/review/jobs/${jobId}`, { method: "DELETE" });
}

export function fetchAdminJobs(signal?: AbortSignal): Promise<AdminJobsResponse> {
  return apiFetch<AdminJobsResponse>("/api/review/admin/jobs", { signal });
}

/** GET /api/review/jobs — kullanıcının KENDİ job'ları (admin/jobs'tan AYRI).
 *  Upload sayfasındaki "önceki versiyon" seçici için. */
export function fetchMyReviewJobs(
  limit?: number,
  signal?: AbortSignal,
): Promise<UserJobsResponse> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch<UserJobsResponse>(`/api/review/jobs${qs}`, { signal });
}

/** GET /api/review/{job_id}/comparison — parent_job_id yoksa comparison=null
 *  döner (hata DEĞİL, normal durum). */
export function fetchVersionComparison(
  jobId: string,
  signal?: AbortSignal,
): Promise<VersionComparisonResponse> {
  return apiFetch<VersionComparisonResponse>(`/api/review/${jobId}/comparison`, {
    signal,
  });
}

export function fetchAdminStats(signal?: AbortSignal): Promise<AdminStats> {
  return apiFetch<AdminStats>("/api/review/admin/stats", { signal });
}

/** GET /api/app/theme — PUBLIC (auth zorunlu değil; apiFetch yine de dev-token header'ı
 *  ekler ama backend GET'i public sayar). Yoksa backend kod-varsayılanını döndürür. */
export function fetchTheme(signal?: AbortSignal): Promise<ThemeSettings> {
  return apiFetch<ThemeSettings>("/api/app/theme", { signal });
}

/** PATCH /api/app/theme — admin-only. 403 → ApiError(status=403) (form yetkisiz mesajı). */
export function updateTheme(
  body: ThemeUpdate,
  signal?: AbortSignal,
): Promise<ThemeSettings> {
  return apiFetch<ThemeSettings>("/api/app/theme", {
    method: "PATCH",
    body,
    signal,
  });
}

// --- son-kullanıcı dili: status → insan cümlesi ----------------------------

/** Ham status kodunu değil, insan cümlesini göster (son-kullanıcı dili). */
export const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Sıraya alındı",
  parsing: "Belge okunuyor",
  checking_citations: "Atıflar doğrulanıyor",
  checking_context: "Atıf bağlamı inceleniyor",
  coverage: "Literatür kapsamı taranıyor",
  orchestrating: "Hakem değerlendirmesi yürütülüyor",
  assembling: "Rapor hazırlanıyor",
  done: "Tamamlandı",
  failed: "Başarısız oldu",
};

export const VERDICT_LABELS: Record<Verdict, string> = {
  accept: "Kabul",
  minor_revision: "Küçük revizyon",
  major_revision: "Büyük revizyon",
  reject: "Ret",
};

export const DIMENSION_LABELS: Record<DimensionKey, string> = {
  originality: "Özgünlük",
  importance: "Önem",
  claims_supported: "İddia desteği",
  soundness: "Yöntem sağlamlığı",
  clarity: "Anlaşılırlık",
  community_value: "Alana katkı",
  contextualization: "Bağlamlandırma",
  citation_integrity: "Atıf bütünlüğü",
  coverage_completeness: "Kapsam tamlığı",
  statistical_consistency: "İstatistik tutarlılığı",
};
