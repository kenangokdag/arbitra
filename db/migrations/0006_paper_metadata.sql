-- =====================================================================
-- PaperMind v4 — Migration 0006: paper metadata facts (Faz 3)
-- =====================================================================
-- Karar: paper-level metadata + bridge tabloları (theme + method)
-- Önkoşul: Migration 0005 PASS
-- Schema kaynağı: ENVANTER.md §3 + §4 + §5
--   W-30 fact_paper_field, W-18 fact_paper_interdisc,
--   bridge fact_paper_topic (rank≤3 loader filter), fact_paper_metod,
--   dim_paper_replication (Int8 NOT Bool L-022)
-- Tarih: 2026-05-01
-- Boyut tahmini: ~3 GB Postgres (field 0.3 + interdisc 0.5 + topic 1.6 +
--   metod 1.0 + replication 0.1) + indeks overhead
-- =====================================================================

-- =====================================================================
-- 27. fact_paper_field — 24,866,945 × 4 (W-30 / N04D)
-- ENVANTER §5: paper_id, primary_field, primary_subfield, primary_domain
-- 26 unique field, 4 domain (Physical/Health/Social/Life), coverage=100%
-- 24,866,945 < 24,867,210 (265 zero-themes paper N04D primary_topic filter dışında)
-- =====================================================================
CREATE TABLE public.fact_paper_field (
  paper_id            text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  primary_field       text NOT NULL,
  primary_subfield    text,
  primary_domain      text NOT NULL
);
CREATE INDEX idx_field_field   ON public.fact_paper_field(primary_field);
CREATE INDEX idx_field_domain  ON public.fact_paper_field(primary_domain);

ALTER TABLE public.fact_paper_field ENABLE ROW LEVEL SECURITY;
CREATE POLICY field_read_all ON public.fact_paper_field
  FOR SELECT TO authenticated USING (true);
CREATE POLICY field_write_service ON public.fact_paper_field
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 28. fact_paper_interdisc — 24,866,945 × 5 (W-18 / N09c HÜCRE 4)
-- ENVANTER §5: Porter & Rafols 2009 Rao-Stirling
--   rao_stirling = 1 − Σ p_i² ∈ [0, 1] (Plan 1 distinct-theme variant)
-- 23.16M paper ≥2 themes (%93.1) rao>0; remainder rao=0 (tek-tema)
-- =====================================================================
CREATE TABLE public.fact_paper_interdisc (
  paper_id              text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  n_distinct_domains    integer NOT NULL DEFAULT 0,
  n_distinct_fields     integer NOT NULL DEFAULT 0,
  n_themes              integer NOT NULL DEFAULT 0,
  rao_stirling          double precision,
  CHECK (rao_stirling IS NULL OR (rao_stirling >= 0 AND rao_stirling <= 1))
);
CREATE INDEX idx_interdisc_rao    ON public.fact_paper_interdisc(rao_stirling DESC) WHERE rao_stirling IS NOT NULL;
CREATE INDEX idx_interdisc_themes ON public.fact_paper_interdisc(n_themes DESC);

ALTER TABLE public.fact_paper_interdisc ENABLE ROW LEVEL SECURITY;
CREATE POLICY interdisc_read_all ON public.fact_paper_interdisc
  FOR SELECT TO authenticated USING (true);
CREATE POLICY interdisc_write_service ON public.fact_paper_interdisc
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 29. fact_paper_topic — bridge n:m (rank≤3 loader filter)
-- ENVANTER §4: parquet schema (id, theme_id, score, rank, is_primary)
--   parquet 69,751,445 satır (TÜM ranks dahil); loader rank≤3 filter
--   ile ~75M tahmini Postgres'e yüklenir (24.87M paper × ortalama ~3.0)
-- "id" parquet kolonu paper_id'ye mapping (semantik açıklık)
-- =====================================================================
CREATE TABLE public.fact_paper_topic (
  paper_id      text NOT NULL
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  theme_id      text NOT NULL,
  score         real,
  rank          smallint NOT NULL,
  is_primary    boolean NOT NULL DEFAULT false,
  PRIMARY KEY (paper_id, theme_id),
  CHECK (rank >= 1 AND rank <= 3)
);
CREATE INDEX idx_topic_paper_primary ON public.fact_paper_topic(paper_id, is_primary) WHERE is_primary = true;
CREATE INDEX idx_topic_theme_score   ON public.fact_paper_topic(theme_id, score DESC);
CREATE INDEX idx_topic_rank          ON public.fact_paper_topic(rank);

ALTER TABLE public.fact_paper_topic ENABLE ROW LEVEL SECURITY;
CREATE POLICY topic_read_all ON public.fact_paper_topic
  FOR SELECT TO authenticated USING (true);
CREATE POLICY topic_write_service ON public.fact_paper_topic
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 30. fact_paper_metod — bridge n:m (51,785,496 × 6 / N04B)
-- ENVANTER §4: paper_id, metod_id, score, is_primary, confidence_flag, source
-- Ortalama ~2.1 metod/paper; F1_macro=0.748 N04B kalibre regex
-- =====================================================================
CREATE TABLE public.fact_paper_metod (
  paper_id          text NOT NULL
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  metod_id          text NOT NULL,
  score             real,
  is_primary        boolean NOT NULL DEFAULT false,
  confidence_flag   text,
  source            text,
  PRIMARY KEY (paper_id, metod_id)
);
CREATE INDEX idx_metod_paper_primary ON public.fact_paper_metod(paper_id, is_primary) WHERE is_primary = true;
CREATE INDEX idx_metod_metod_score   ON public.fact_paper_metod(metod_id, score DESC);

ALTER TABLE public.fact_paper_metod ENABLE ROW LEVEL SECURITY;
CREATE POLICY metod_read_all ON public.fact_paper_metod
  FOR SELECT TO authenticated USING (true);
CREATE POLICY metod_write_service ON public.fact_paper_metod
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 31. dim_paper_replication — 24,867,210 × 3 (B42-019 N10 CANDIDATE_ONLY)
-- ENVANTER §3: paper_id, replication_signal_present (Int8 NOT Bool, L-022),
--   regex_evidence (Utf8 nullable)
-- 66,368 signal_present (%0.27) broad regex; pre=0.10/rec=0.96/κ=0.10
-- K2 KARARI: smallint (Int8 sadık mirror, parquet ile parite)
-- =====================================================================
CREATE TABLE public.dim_paper_replication (
  paper_id                      text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  replication_signal_present    smallint NOT NULL DEFAULT 0,
  regex_evidence                text,
  CHECK (replication_signal_present IN (0, 1))
);
CREATE INDEX idx_replication_signal ON public.dim_paper_replication(replication_signal_present)
  WHERE replication_signal_present = 1;

ALTER TABLE public.dim_paper_replication ENABLE ROW LEVEL SECURITY;
CREATE POLICY replication_read_all ON public.dim_paper_replication
  FOR SELECT TO authenticated USING (true);
CREATE POLICY replication_write_service ON public.dim_paper_replication
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0006_paper_metadata',
  'fact_paper_field (24.87M W-30) + fact_paper_interdisc (24.87M W-18) + fact_paper_topic (~75M rank≤3) + fact_paper_metod (51.79M N04B) + dim_paper_replication (24.87M B42-019)'
)
ON CONFLICT (version) DO NOTHING;
