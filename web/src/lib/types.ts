/**
 * Backend Pydantic mirror — api/models/* ile birebir eş.
 * Backend kaynak, frontend uyar. DM-025.
 */

export type Language = "tr" | "en" | "id";

export type DecisionBand = "canon" | "strong_evidence" | "frontier" | "risk";

/* ── Gate ── */

export type GateId = "G1" | "G2" | "G3" | "G4" | "G5" | "G6" | "G7";
export type GateSeverity = "info" | "warn" | "block";

export type GateWarning = {
  gate_id: GateId;
  severity: GateSeverity;
  message: string;
};

/* ── Faithfulness ── */

export type FaithfulnessMeta = {
  jsonschema_pct: number;
  minicheck_nli: number;
  alce_recall: number;
};

/* ── Citation ── */

export type Citation = {
  sentence: string;
  paper_id: string;
  span: [number, number];
  lvr_distance: number;
};

/* ── Paper ── */

export type PaperCard = {
  paper_id: string;
  pmid: string;
  title: string;
  authors: string[];
  year: number | null;
  year_verified: boolean;
  doi: string | null;
  abstract_excerpt: string | null;
  journal: string | null;
  n_cited: number;
  signals_13: Record<string, number>;
  citations_lvr: Citation[];
  decision_band: DecisionBand;
  gate_warnings: GateWarning[];
  is_ghost: boolean;
  language?: Language | null;
  is_open_access?: boolean;
};

/* ── Search ── */

export type SearchRequest = {
  query: string;
  k?: number;
  language_hint?: Language;
  include_ghost?: boolean;
};

export type SearchResponse = {
  papers: PaperCard[];
  faithfulness_meta: FaithfulnessMeta;
  decision_band: DecisionBand;
  gate_warnings: GateWarning[];
  latency_ms: number;
  pmid_match_score: number;
};

/* ── Top5 ── */

export type Top5Request = {
  query: string;
  session_id: string;
  margin?: number;
  k?: number;
};

export type Top5Response = {
  papers: PaperCard[];
  needs_clarify: boolean;
  margin_used: number;
};

/* ── Chat ── */

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type ChatRequest = {
  session_id: string;
  messages: ChatMessage[];
  language: Language;
  paper_context_ids: string[];
};

export type ChatChunk = {
  delta: string;
  finished: boolean;
  citation_paper_ids: string[];
};

/* ── Project ── */

export type ProjectStatus = "active" | "archived";

export type ProjectListItem = {
  id: string;
  name: string;
  status: ProjectStatus;
  current_stage: string;
  updated_at: string;
};

/* ── Summarize ── */

export type SummaryMode = "abstract" | "tldr" | "deep";

export type SummarizeRequest = {
  paper_id: string;
  mode?: SummaryMode;
  language?: Language;
};

export type SummarizeAccepted = {
  task_id: string;
  status: "pending" | "running" | "complete" | "failed";
};

export type SummaryDoc = {
  paper_id: string;
  mode: SummaryMode;
  language: Language;
  text: string;
  citations: string[];
  faithfulness_meta: Record<string, number>;
};

/* ── Reading List ── */

export type ReadingStatus = "want_to_read" | "reading" | "finished" | "skipped";

export type ReadingListItem = {
  id: string;
  paper_id: string;
  status: ReadingStatus;
  notes: string;
  added_at: string;
  updated_at: string;
};

export type ReadingListAddRequest = {
  paper_id: string;
  status?: ReadingStatus;
  notes?: string;
};

export type ReadingListUpdateRequest = {
  status?: ReadingStatus;
  notes?: string;
};

export type ReadingListResponse = {
  items: ReadingListItem[];
  count: number;
};

/* ── Onboarding ──
 * api/models/onboarding.py mirror — F5-S1A/B + S2 (K-008/K-013/K-017/K-019).
 * K-017: primary_language KALDIRILDI — UI dili browser/locale, DB'de tutulmaz.
 * Language tipi yalnız UI locale (search_request.language_hint) için kullanılır.
 */

export type UserTier = "ogrenci" | "arastirmaci" | "profesyonel";

export type SubfieldRef = {
  subfield_id: string;
  field_id: string;
};

export type OnboardingRequest = {
  full_name: string;
  tier: UserTier;
  field_ids: string[];
  subfields: SubfieldRef[];
  research_focus: string;
  affiliation?: string;
  orcid_raw?: string;
};

export type OnboardingResponse = {
  user_id: string;
  tier: UserTier;
  field_ids: string[];
  subfields: SubfieldRef[];
  profile_complete: boolean;
};

/* ── Dim taxonomy (K-011 DB EN-only; UI TR via web/src/lib/i18n/fields_tr.ts dictionary) ── */

export type DimField = {
  field_id: string;
  name_en: string;
  slug?: string;
  paper_count_total?: number;
  name_tr?: string;
};

export type DimSubfield = {
  subfield_id: string;
  field_id: string;
  name_en: string;
  slug?: string;
  paper_count_total?: number;
  name_tr?: string;
};

export type DimFieldListResponse = {
  fields: DimField[];
};

export type DimSubfieldListResponse = {
  subfields: DimSubfield[];
};

/* ── Paper Detail ── */

export type PaperDetail = {
  paper_id: string;
  pmid: string;
  title: string;
  authors: string[];
  year: number | null;
  year_verified: boolean;
  doi: string | null;
  abstract: string | null;
  abstract_excerpt: string | null;
  journal: string | null;
  n_cited: number;
  signals_13: Record<string, number>;
  citations_lvr: Citation[];
  decision_band: DecisionBand;
  gate_warnings: GateWarning[];
  is_ghost: boolean;
  language?: string | null;
  is_open_access?: boolean;
  keywords: string[];
  references_count: number;
  cited_by_count: number;
  url: string | null;
};

/* ── Notes ── */

export type NoteItem = {
  id: string;
  paper_id: string | null;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type NotesResponse = {
  items: NoteItem[];
  count: number;
};

/* ── Enrich ── */

export type EnrichSource = "openalex" | "semantic_scholar" | "crossref";

export type EnrichRequest = {
  paper_id: string;
  sources?: EnrichSource[];
};

export type EnrichResponse = {
  paper_id: string;
  sources_hit: EnrichSource[];
  cache_hit: boolean;
  enriched_fields: Record<string, string>;
};
