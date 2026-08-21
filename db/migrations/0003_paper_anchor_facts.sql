-- =====================================================================
-- PaperMind v4 — Migration 0003: PaperCard + GhostCard (warehouse anchor)
-- =====================================================================
-- Karar: Warehouse ana gövde Faz 1 — paper-level FK anchor tablolar
-- Schema kaynağı: Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md §3 + §10.1
-- Aynalama prensibi: warehouse parquet kolon adları **aynen** Supabase'e taşınır
--   (B42-039 / L-013 manifest > planning hiyerarşisi)
-- NOT: public.papers (0001 init'te) app-side partial mirror; bu tablolar
--      warehouse full mirror — aynı paper_id alanı PK ama ayrı tablolar.
-- Tarih: 2026-04-30
-- Tier: Pro ($25/ay + metered storage)
-- Boyut: PaperCard 24.87M × 15 ~10 GB + GhostCard 31.85M × 16 ~15 GB
-- =====================================================================

BEGIN;

-- =====================================================================
-- 17. fact_paper_id_card — PaperCard (24,866,945 × 15, M31/N20e v1.2)
-- ENVANTER §10.1 + B42-045 v1.1 + N20e_patch_suspicious_flag (2026-04-28 15:52:30):
--   paper_id (String, bare W canonical)
--   pmid (String, 12 segment dot-separated D.F.S.T1.T2.T3.Y.Q.I.L.R.V)
--   topic_profile (Struct{theme_ids: List[String], theme_scores: List[Float32]}) → JSONB
--   language (String 2-char ISO)
--   year (Int32)
--   is_oa (Bool)
--   type_c/type_m/type_e/type_r/type_b (Float32, softmax 5-dim, sum=1)
--   dominant_type (String ∈ {C,M,E,R,B} — argmax)
--   type_confidence (Float32 = max − 2nd)
--   version_id (String 'v1.1_2026-04-29')
--   is_suspicious (Boolean = (q_weak<0.3 AND replication_signal_present) — v1.2 patch RISK_7
--                  20,677 paper flag'lendi; backend default filter, UI kırmızı uyarı rozet)
-- =====================================================================
CREATE TABLE public.fact_paper_id_card (
  paper_id          text PRIMARY KEY,                       -- bare W canonical
  pmid              text NOT NULL,                          -- 12 segment K6 sabit
  topic_profile     jsonb NOT NULL,                         -- {theme_ids: [...], theme_scores: [...]}
  language          text,                                   -- 2-char ISO
  year              int,
  is_oa             boolean,
  type_c            real,                                   -- concept softmax
  type_m            real,                                   -- method
  type_e            real,                                   -- empirical
  type_r            real,                                   -- review
  type_b            real,                                   -- bridge
  dominant_type     text,                                   -- {C,M,E,R,B}
  type_confidence   real,                                   -- max − 2nd
  version_id        text NOT NULL DEFAULT 'v1.1_2026-04-29',
  is_suspicious     boolean NOT NULL DEFAULT false,         -- v1.2 patch (RISK_7)
  CHECK (dominant_type IN ('C','M','E','R','B'))
);
CREATE INDEX idx_paper_card_pmid ON public.fact_paper_id_card(pmid);
CREATE INDEX idx_paper_card_dominant ON public.fact_paper_id_card(dominant_type);
CREATE INDEX idx_paper_card_lang ON public.fact_paper_id_card(language);
CREATE INDEX idx_paper_card_year ON public.fact_paper_id_card(year) WHERE year IS NOT NULL;
CREATE INDEX idx_paper_card_topic_gin ON public.fact_paper_id_card USING gin (topic_profile);
CREATE INDEX idx_paper_card_suspicious ON public.fact_paper_id_card(is_suspicious) WHERE is_suspicious = true;

ALTER TABLE public.fact_paper_id_card ENABLE ROW LEVEL SECURITY;
CREATE POLICY paper_card_read_all ON public.fact_paper_id_card
  FOR SELECT TO authenticated USING (true);
CREATE POLICY paper_card_write_service ON public.fact_paper_id_card
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 18. dim_ghost_paper — GhostCard (31,855,437 × 16, M51/N20f v1.2)
-- ENVANTER §10.1 + B42-045 v1.1 + N20f_patch_ghost_triage (2026-04-28 16:00:50):
--   paper_id (String, bare W canonical)
--   inferred_pmid (String, 12 segment — refs majority + pagerank Q + citer language L)
--   pmid_confidence_per_segment (Struct{D, F, L: Float}) → JSONB
--   citer_field_distribution (Struct{fields, counts, ratios}) → JSONB
--   citer_language_distribution (Struct) → JSONB
--   language_inferred (String, citer majority>0.5; ≤0.5 NULL)
--   year_upper_bound (Int32 = min(citer.year), iç hesap K7 — UI'da gösterilmez)
--   pagerank (Float64)
--   indegree (Int32)
--   outdegree (Int32) — citation graph outgoing edges (disk schema; ENVANTER §10.1'de yer almıyor — disk canon)
--   n_corpus_citers (UInt32 ≥3 K8 filtre)
--   is_canonical (Bool=True)
--   version_id (String 'v1.1_2026-04-29')
--   computed_at (String ISO)
--   enrichment_status (String 'pending')
--   triage_priority (Utf8 ∈ {high,medium,low,none}) — v1.2 patch RISK_4 mitigation
--                    high=75K (D_conf<0.5 AND citers≥50 — yanlış inferred majör paper, default suppressed)
--                    medium=144K (D_conf<0.5 AND citers≥20, UI warning badge)
--                    low=540K (D_conf<0.5 AND citers<20)
--                    none=31.10M (D_conf≥0.5, %97.6 — varsayılan güvenilir ghost)
--                    DOI enrichment Faz 3 öncelik listesi: high 75K manuel triage
--
-- NOT: 0001 init'te dim_ghost_paper boş schema vardı (placeholder).
--      Bu migration WAREHOUSE FULL MIRROR ile DROP + CREATE yapar.
-- =====================================================================
DROP TABLE IF EXISTS public.dim_ghost_paper CASCADE;

CREATE TABLE public.dim_ghost_paper (
  paper_id                       text PRIMARY KEY,
  inferred_pmid                  text NOT NULL,                       -- 12 segment K6
  pmid_confidence_per_segment    jsonb NOT NULL,                      -- {D, F, L: float}
  citer_field_distribution       jsonb NOT NULL,                      -- {fields, counts, ratios}
  citer_language_distribution    jsonb NOT NULL,
  language_inferred              text,                                -- citer majority>0.5 NULL
  year_upper_bound               int,                                 -- min(citer.year), K7 iç hesap
  pagerank                       double precision,
  indegree                       bigint,
  outdegree                      int,                                 -- citation graph outgoing edges (disk canon)
  n_corpus_citers                bigint NOT NULL,                     -- ≥3 K8
  is_canonical                   boolean NOT NULL DEFAULT true,
  version_id                     text NOT NULL DEFAULT 'v1.1_2026-04-29',
  computed_at                    text,                                -- ISO 8601 string (warehouse'tan aynen)
  enrichment_status              text NOT NULL DEFAULT 'pending',     -- pending|fetching|enriched|failed
  triage_priority                text NOT NULL DEFAULT 'none',        -- v1.2 patch (RISK_4)
  CHECK (n_corpus_citers >= 3),
  CHECK (enrichment_status IN ('pending','fetching','enriched','failed')),
  CHECK (triage_priority IN ('high','medium','low','none'))
);
CREATE INDEX idx_ghost_pmid ON public.dim_ghost_paper(inferred_pmid);
CREATE INDEX idx_ghost_pagerank ON public.dim_ghost_paper(pagerank DESC) WHERE pagerank IS NOT NULL;
CREATE INDEX idx_ghost_indegree ON public.dim_ghost_paper(indegree DESC);
CREATE INDEX idx_ghost_lang ON public.dim_ghost_paper(language_inferred);
CREATE INDEX idx_ghost_enrich_status ON public.dim_ghost_paper(enrichment_status)
  WHERE enrichment_status <> 'enriched';
CREATE INDEX idx_ghost_triage ON public.dim_ghost_paper(triage_priority)
  WHERE triage_priority IN ('high','medium');

ALTER TABLE public.dim_ghost_paper ENABLE ROW LEVEL SECURITY;
CREATE POLICY ghost_read_all ON public.dim_ghost_paper
  FOR SELECT TO authenticated USING (true);
CREATE POLICY ghost_write_service ON public.dim_ghost_paper
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0003_paper_anchor_facts',
  'fact_paper_id_card v1.2 (24.87M × 15 incl is_suspicious) + dim_ghost_paper v1.2 (31.85M × 16 disk canon: outdegree, no q_proxy, incl triage_priority, full mirror replace)'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
