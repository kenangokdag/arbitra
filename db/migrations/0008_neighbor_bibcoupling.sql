-- =====================================================================
-- PaperMind v4 — Migration 0008: neighbor graph bibcoupling top-50 (Faz 3)
-- =====================================================================
-- Karar: Pool Router "Komşu" havuz cosine_direct_top50 — paper-pair tablosu
-- Önkoşul: Migration 0007 PASS
-- Schema kaynağı: ENVANTER.md §6 N09b (B42-022 + B42-030)
--   method=cosine_direct_top50_no_bidir (top-50 her yön bağımsız)
-- Tarih: 2026-05-01
-- Boyut tahmini: parquet 4.81 GB → Postgres ~5-6 GB tablo + 1 INDEX (paper_b)
--   ~3 GB ek = toplam ~8-9 GB (en büyük tek tablo)
--
-- ⚠ FK YASAK KARARI:
--   643M satır × 2 FK = ~30 GB ek index. Loader katmanında VALID_PAPER_IDS
--   anti-join filter ile veri bütünlüğü garanti edilir (B-009 pattern).
--   Postgres FK constraint'i atlanarak disk tasarrufu.
-- =====================================================================

-- =====================================================================
-- 35. fact_paper_bibcoupling_top50 — 643,445,780 × 5 (N09b B42-030)
-- SCHEMA AUDIT 2026-05-01 (parquet head): paper_id, neighbor_id, raw_count,
--   cosine_score, rank (ENVANTER §180 schema iddiası `paper_a/paper_b/intersect/score/raw_count`
--   YANLIŞ — gerçek parquet farklı; manifest > ENVANTER B42-039)
-- NO_BIDIR asimetrik: her yön bağımsız top-50; rank 1..50
-- Coverage: 15.87M paper (%63.8 master 24.87M üzerinden — degree filter sonrası)
-- =====================================================================
CREATE TABLE public.fact_paper_bibcoupling_top50 (
  paper_id        text NOT NULL,    -- NO FK (loader anti-join, disk tasarrufu)
  neighbor_id     text NOT NULL,    -- NO FK (loader anti-join)
  raw_count       integer NOT NULL DEFAULT 0,
  cosine_score    real,
  rank            smallint NOT NULL,
  PRIMARY KEY (paper_id, neighbor_id),
  CHECK (cosine_score IS NULL OR (cosine_score >= 0 AND cosine_score <= 1)),
  CHECK (rank >= 1 AND rank <= 50)
);
CREATE INDEX idx_bibcoup_neighbor_score ON public.fact_paper_bibcoupling_top50(neighbor_id, cosine_score DESC);
CREATE INDEX idx_bibcoup_paper_rank     ON public.fact_paper_bibcoupling_top50(paper_id, rank);

ALTER TABLE public.fact_paper_bibcoupling_top50 ENABLE ROW LEVEL SECURITY;
CREATE POLICY bibcoup_read_all ON public.fact_paper_bibcoupling_top50
  FOR SELECT TO authenticated USING (true);
CREATE POLICY bibcoup_write_service ON public.fact_paper_bibcoupling_top50
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0008_neighbor_bibcoupling',
  'fact_paper_bibcoupling_top50 (643M N09b cosine_direct_top50_no_bidir, schema: paper_id/neighbor_id/raw_count/cosine_score/rank, NO FK)'
)
ON CONFLICT (version) DO NOTHING;
