-- =====================================================================
-- PaperMind v4 — Migration 0007: method affinity + centrality (Faz 3)
-- =====================================================================
-- Karar: method × theme + method × field affinity tabloları + paper centrality
-- Önkoşul: Migration 0006 PASS
-- Schema kaynağı: ENVANTER.md §5
--   W-19 fact_method_topic_affinity, A2 fact_method_field_affinity (B42-046 §7),
--   fact_paper_centrality (corpus subset, 100M parquet → ~24.87M loader filter)
-- Tarih: 2026-05-01
-- Boyut tahmini: ~1 GB Postgres (affinity'ler ~10 MB + centrality ~1 GB)
-- =====================================================================

-- =====================================================================
-- 32. fact_method_topic_affinity — 65,061 × 6 (W-19 / N09c HÜCRE 5)
-- ENVANTER §5: metod_id × theme_id × n_papers + mean_centrality (PageRank)
--   + mean_q_weak + lift = obs/expected
-- 4-way join: paper_metod ⨝ paper_topic ⨝ centrality ⨝ quality_v3
-- =====================================================================
CREATE TABLE public.fact_method_topic_affinity (
  metod_id           text NOT NULL,
  theme_id           text NOT NULL,
  n_papers           integer NOT NULL DEFAULT 0,
  mean_centrality    double precision,
  mean_q_weak        double precision,
  lift               double precision,
  PRIMARY KEY (metod_id, theme_id)
);
CREATE INDEX idx_mta_theme  ON public.fact_method_topic_affinity(theme_id);
CREATE INDEX idx_mta_metod  ON public.fact_method_topic_affinity(metod_id);
CREATE INDEX idx_mta_lift   ON public.fact_method_topic_affinity(lift DESC) WHERE lift IS NOT NULL;

ALTER TABLE public.fact_method_topic_affinity ENABLE ROW LEVEL SECURITY;
CREATE POLICY mta_read_all ON public.fact_method_topic_affinity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY mta_write_service ON public.fact_method_topic_affinity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 33. fact_method_field_affinity — 390 × 6 (A2 / B42-046 §7 pending)
-- ENVANTER §5: metod_id × primary_field × n_papers + mean_centrality
--   + mean_q_weak + lift; M3/M4 gap matrix dimension + UI typicality rozeti
-- DEPTH_MIN=5 filter; lift outlier küçük cell'lerde (max 455K) — backend
-- log-transform önerilir (ENVANTER notu)
-- =====================================================================
CREATE TABLE public.fact_method_field_affinity (
  metod_id           text NOT NULL,
  primary_field      text NOT NULL,
  n_papers           integer NOT NULL DEFAULT 0,
  mean_centrality    double precision,
  mean_q_weak        double precision,
  lift               double precision,
  PRIMARY KEY (metod_id, primary_field)
);
CREATE INDEX idx_mfa_field  ON public.fact_method_field_affinity(primary_field);
CREATE INDEX idx_mfa_metod  ON public.fact_method_field_affinity(metod_id);
CREATE INDEX idx_mfa_lift   ON public.fact_method_field_affinity(lift DESC) WHERE lift IS NOT NULL;

ALTER TABLE public.fact_method_field_affinity ENABLE ROW LEVEL SECURITY;
CREATE POLICY mfa_read_all ON public.fact_method_field_affinity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY mfa_write_service ON public.fact_method_field_affinity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 34. fact_paper_centrality — corpus subset (~24.87M / N09)
-- ENVANTER §5: parquet 100,982,867 satır (corpus DIŞI nodes dahil — referenced_works)
--   loader VALID_PAPER_IDS anti-join → ~24.87M corpus subset Postgres'e
-- Schema: paper_id, pagerank (Float64 sum=1±ε), indegree (Int64), outdegree (Int64)
-- =====================================================================
CREATE TABLE public.fact_paper_centrality (
  paper_id      text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  pagerank      double precision,
  indegree      bigint NOT NULL DEFAULT 0,
  outdegree     bigint NOT NULL DEFAULT 0
);
CREATE INDEX idx_centrality_pr        ON public.fact_paper_centrality(pagerank DESC) WHERE pagerank IS NOT NULL;
CREATE INDEX idx_centrality_indegree  ON public.fact_paper_centrality(indegree DESC);
CREATE INDEX idx_centrality_outdegree ON public.fact_paper_centrality(outdegree DESC);

ALTER TABLE public.fact_paper_centrality ENABLE ROW LEVEL SECURITY;
CREATE POLICY centrality_read_all ON public.fact_paper_centrality
  FOR SELECT TO authenticated USING (true);
CREATE POLICY centrality_write_service ON public.fact_paper_centrality
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0007_method_centrality',
  'fact_method_topic_affinity (65K W-19) + fact_method_field_affinity (390 A2) + fact_paper_centrality (~24.87M corpus subset N09)'
)
ON CONFLICT (version) DO NOTHING;
