-- =====================================================================
-- PaperMind v4 — Migration 0002: pgvector + 3 statik fact tablo
-- =====================================================================
-- Karar: F1_master_plan §5 ek (B-002 takiben warehouse statik upload)
-- Schema kaynağı: Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md §3 + §10.1
-- Aynalama prensibi: warehouse parquet kolon adları **aynen** Supabase'e taşınır
--   (B42-039 / L-013 manifest > planning hiyerarşisi; isim drift yasak)
-- Tarih: 2026-04-29
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================
-- 14. dim_theme_embedding — 4516 × 4 (TF-IDF 256-d L2-normed, N17b/W-32)
-- ENVANTER §10.1: theme_id (String), embedding (List[Float32], 256-d),
--                 text_source (String), n_terms_used (Int32)
-- =====================================================================
CREATE TABLE public.dim_theme_embedding (
  theme_id       text PRIMARY KEY REFERENCES public.dim_theme(theme_id) ON DELETE CASCADE,
  embedding      vector(256) NOT NULL,
  text_source    text,                                  -- 'tfidf-256-l2norm' veya kaynak metin türü
  n_terms_used   int,                                   -- TF-IDF term count
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_theme_emb_hnsw ON public.dim_theme_embedding
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

ALTER TABLE public.dim_theme_embedding ENABLE ROW LEVEL SECURITY;
CREATE POLICY theme_emb_read_all ON public.dim_theme_embedding
  FOR SELECT TO authenticated USING (true);
CREATE POLICY theme_emb_write_service ON public.dim_theme_embedding
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 15. fact_theme_year_aggregates — 53,943 × 15 (t-ESTRA partial 7/8, N14b/W-26b+c)
-- ENVANTER §10.1: theme_id, year, paper_count, R_mean/R_std, E_mean/E_std,
--                 ED_k_simpson, ES_k_top10, TS_penalty,
--                 blocked_metrics (List[String]), n_blocked,
--                 C_k, CD_k, MQ_k (Plan 1 NULL — patch ile dolacak)
-- =====================================================================
CREATE TABLE public.fact_theme_year_aggregates (
  theme_id          text NOT NULL REFERENCES public.dim_theme(theme_id) ON DELETE CASCADE,
  year              int NOT NULL,
  paper_count       int NOT NULL DEFAULT 0,
  r_mean            real,                               -- relevance mean
  r_std             real,
  e_mean            real,                               -- epistemic confidence mean
  e_std             real,
  ed_k_simpson      real,                               -- field diversity Simpson 1-Σp²
  es_k_top10        real,                               -- semantic similarity top-10 cosine
  ts_penalty        real,                               -- time-series logistic penalty
  c_k               real,                               -- continuity (Plan 1 NULL)
  cd_k              real,                               -- CD-disruption W-20 (Plan 1 NULL)
  mq_k              real,                               -- mass×quality (Plan 1 NULL → patch v2)
  blocked_metrics   text[] DEFAULT '{}',                -- ['C_k','CD_k','MQ_k'] hangi NULL
  n_blocked         smallint DEFAULT 0,
  PRIMARY KEY (theme_id, year)
);
CREATE INDEX idx_theme_year_year ON public.fact_theme_year_aggregates(year);
CREATE INDEX idx_theme_year_mq ON public.fact_theme_year_aggregates(mq_k DESC) WHERE mq_k IS NOT NULL;
CREATE INDEX idx_theme_year_e ON public.fact_theme_year_aggregates(e_mean DESC) WHERE e_mean IS NOT NULL;

ALTER TABLE public.fact_theme_year_aggregates ENABLE ROW LEVEL SECURITY;
CREATE POLICY theme_year_read_all ON public.fact_theme_year_aggregates
  FOR SELECT TO authenticated USING (true);
CREATE POLICY theme_year_write_service ON public.fact_theme_year_aggregates
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 16. fact_gap_matrix — 504,436 × 12 (M1/M7/M8 birleşik, N16/W-27)
-- ENVANTER §10.1: matrix_id (M1=theme×method, M7=theme×outcome, M8=theme×theme),
--                 axis_x (heterojen — theme_id veya metod_id veya outcome_role),
--                 axis_y, depth (≥5), depth_norm, neighbor, E,
--                 feasibility, gap_value, publishability,
--                 matrix_confidence_prior, matrix_confidence_calibrated
-- NOT: M8 dışında (axis_x<axis_y) constraint geçerli değil — heterojen tipler.
--      M8 ordered-pair dedup uygulamada filter ile garanti.
-- =====================================================================
CREATE TABLE public.fact_gap_matrix (
  id                            bigserial PRIMARY KEY,
  matrix_id                     text NOT NULL,                       -- 'M1' | 'M7' | 'M8'
  axis_x                        text NOT NULL,
  axis_y                        text NOT NULL,
  depth                         int NOT NULL,                        -- ≥5
  depth_norm                    real,                                -- log1p-normalized [0,1]
  neighbor                      real,                                -- 3×3 conv smoothed [0,1]
  e_value                       double precision,                    -- mean d-ESTRA E or sentence-role conf
  feasibility                   real DEFAULT 0.5,                    -- Plan 1 placeholder
  publishability                real,
  gap_value                     double precision NOT NULL,           -- 0.25(1-depth_norm) + 0.20·neighbor + 0.20·E + 0.15·feasibility + 0.20·publishability
  matrix_confidence_prior       real DEFAULT 0.5,
  matrix_confidence_calibrated  real,                                -- Aşama 3 LightGBM sonrası
  CHECK (matrix_id IN ('M1','M7','M8')),
  CHECK (depth >= 5)
);
CREATE INDEX idx_gap_matrix ON public.fact_gap_matrix(matrix_id);
CREATE INDEX idx_gap_pair ON public.fact_gap_matrix(matrix_id, axis_x, axis_y);
CREATE INDEX idx_gap_value ON public.fact_gap_matrix(gap_value DESC);
CREATE INDEX idx_gap_axis_x ON public.fact_gap_matrix(axis_x);
CREATE INDEX idx_gap_axis_y ON public.fact_gap_matrix(axis_y);

ALTER TABLE public.fact_gap_matrix ENABLE ROW LEVEL SECURITY;
CREATE POLICY gap_read_all ON public.fact_gap_matrix
  FOR SELECT TO authenticated USING (true);
CREATE POLICY gap_write_service ON public.fact_gap_matrix
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES ('0002_static_facts', 'pgvector + dim_theme_embedding (4516) + fact_theme_year_aggregates (53.9K) + fact_gap_matrix (504K)')
ON CONFLICT (version) DO NOTHING;
