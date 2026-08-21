-- =====================================================================
-- PaperMind v4 — Migration 0016: project_cluster materialize (F9 1.1)
-- Bağımlılık: 0015 (public.projects parent FK target)
-- BÖLÜM 3 RRF (vec+bib+theme) çıktısı + BÖLÜM 4-5 ESTRA q_weak/estra_score persist
-- =====================================================================

BEGIN;

CREATE TABLE public.project_cluster (
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id      text NOT NULL,
  source        text NOT NULL CHECK (source IN ('vec','bib','theme')),
  rrf_score     numeric NOT NULL,
  q_weak        numeric,
  estra_score   numeric,
  rank_final    int,
  frozen_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, paper_id)
);

CREATE INDEX idx_cluster_project_rank
  ON public.project_cluster (project_id, rank_final);

ALTER TABLE public.project_cluster ENABLE ROW LEVEL SECURITY;

CREATE POLICY cluster_owner ON public.project_cluster
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

COMMENT ON TABLE public.project_cluster IS
  'F9 1.1 BÖLÜM 3 RRF çıktısı (vec+bib+theme 3-kanal füzyon) + BÖLÜM 4-5 ESTRA skor materialize. Composite PK (project_id, paper_id), CASCADE DELETE projects parent.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0016_project_cluster',
  'project_cluster (F9 1.1 BÖLÜM 3 RRF çıktısı + ESTRA skor materialize)'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
