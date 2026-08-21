-- =====================================================================
-- PaperMind v4 — Supabase Migration 0019: project_seed_papers + Q seed columns
-- =====================================================================
-- Plan: docs/plans/F11_tek_kanal_mimarisi.md §4 (Phase A — Q→Project köprüsü)
-- Tetik: Q (vitrin/OpenAlex) sayfasından "Projeye Dönüştür" CTA → bizim havuza
--        ait yeni proje yarat + Q'dan miras snapshot (sorgu + seçilen paper'lar).
-- Tarih: 2026-05-10 · PG: 17.6
-- Bağımlılık: 0015 (projects tablosu)
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. projects: Q'dan miras snapshot kolonları
-- ============================================================================
-- seed_query     : Q'da yapılan sorgu metni (kullanıcı dilinde)
-- seed_lang      : Q sorgusunun dili (Q sayfasında 'tr'/'en'/'id'/'other')
-- seed_source    : Projenin nereden açıldığı — 'q' | 'onboarding' | 'manual'
ALTER TABLE public.projects
  ADD COLUMN IF NOT EXISTS seed_query  text,
  ADD COLUMN IF NOT EXISTS seed_lang   text,
  ADD COLUMN IF NOT EXISTS seed_source text NOT NULL DEFAULT 'manual'
    CHECK (seed_source IN ('q','onboarding','manual'));

COMMENT ON COLUMN public.projects.seed_query IS
  'F11 Phase A: Q (vitrin) sorgusu — proje açılışında miras alınır, sonradan değişmez.';
COMMENT ON COLUMN public.projects.seed_lang IS
  'F11 Phase A: Q sorgusunun dili (q-api QLang ile aynı domain).';
COMMENT ON COLUMN public.projects.seed_source IS
  'F11 Phase A: proje hangi kanaldan açıldı. ''q''=Q vitrin, ''onboarding''=onboarding miras, ''manual''=boş başla.';

-- ============================================================================
-- 2. project_seed_papers — Q'dan seçilen paper'ların proje köprüsü
-- ============================================================================
-- Q'da kullanıcı 1-25 paper seçer + "Projeye Dönüştür" tıklar. Bu satırlar
-- kullanıcının ilk niyet sinyali; cluster_expander (Phase B) anchor'a kadar
-- bu seçimi referans alır.
CREATE TABLE IF NOT EXISTS public.project_seed_papers (
  project_id    uuid    NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id      text    NOT NULL,                         -- OpenAlex ID (W-prefix)
  source_query  text    NOT NULL,
  source_lang   text    NOT NULL,
  selected_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, paper_id)
);

CREATE INDEX IF NOT EXISTS idx_seed_papers_project
  ON public.project_seed_papers (project_id);

ALTER TABLE public.project_seed_papers ENABLE ROW LEVEL SECURITY;

CREATE POLICY seed_papers_owner ON public.project_seed_papers FOR ALL
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

COMMENT ON TABLE public.project_seed_papers IS
  'F11 Phase A: Q (vitrin) sayfasından proje açarken seçilen paper''lar (1-25). paper_id OpenAlex W-id metni; bizim warehouse papers.id ile FK YOK (Q evreni ayrı).';

-- ============================================================================
-- 3. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0019_project_seed_papers',
  'projects.seed_query/lang/source + project_seed_papers (F11 Phase A — Q→Project köprüsü)'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
