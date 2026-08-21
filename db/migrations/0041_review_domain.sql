-- =====================================================================
-- PaperMind v4 — Migration 0041: F14 Hakemlik (peer-review) domaini
-- =====================================================================
-- Plan: docs/plans/F14_hakemlik_master.md §1 (AYRI ALAN: /api/review),
--       §6 R-6 (hakemlik ≠ jüri → defense_session'a cıvatalama YOK).
--
-- Eklenen tablolar:
--   review_job       — async hakemlik işi (R-2): upload → parse → check →
--                      orchestrate → done; durum + ilerleme + nihai rapor.
--   (manuscript + rapor JSONB olarak review_job içinde taşınır; ayrı tablo
--    gereksiz şişme yaratmaz — tek iş = tek satır, tüm sinyaller burada.)
--
-- Tarih: 2026-06-21 · PG: 17.x
-- Bağımlılık: 0001 (schema_migrations), auth (user_id text — Supabase sub).
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.review_job (
  job_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       text NOT NULL,
  mode          text NOT NULL DEFAULT 'author'
                  CHECK (mode IN ('author', 'editor')),
  language      text NOT NULL DEFAULT 'en'
                  CHECK (language IN ('tr', 'en')),
  status        text NOT NULL DEFAULT 'queued'
                  CHECK (status IN (
                    'queued', 'parsing', 'checking_citations',
                    'checking_context', 'coverage', 'orchestrating',
                    'assembling', 'done', 'failed'
                  )),
  progress      real NOT NULL DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 1),
  step_label    text NOT NULL DEFAULT '',
  source_name   text,                       -- yüklenen dosya adı (insan-dili künye)
  source_kind   text CHECK (source_kind IN ('pdf', 'docx', 'latex', 'zip')),
  manuscript    jsonb,                      -- Manuscript (S1 çıktısı)
  evidence_pack jsonb,                      -- EvidencePack (S2/S3 deterministik olgular)
  report        jsonb,                      -- ReviewReport (S5 nihai)
  error         text,                       -- observability: hata yutulmaz, saklanır
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.review_job IS
  'F14 hakemlik async işi (R-2). mode=author(Faz1)/editor(Faz2). manuscript/evidence_pack/report JSONB. defense_session''dan AYRI (R-6: hakemlik≠jüri).';

CREATE INDEX IF NOT EXISTS idx_review_job_user
  ON public.review_job (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_job_status
  ON public.review_job (status) WHERE status NOT IN ('done', 'failed');

-- RLS: kullanıcı yalnız kendi işini görür (admin secret-key bypass eder).
ALTER TABLE public.review_job ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS review_job_owner_select ON public.review_job;
CREATE POLICY review_job_owner_select ON public.review_job
  FOR SELECT USING (user_id = (auth.jwt() ->> 'sub'));

DROP POLICY IF EXISTS review_job_owner_insert ON public.review_job;
CREATE POLICY review_job_owner_insert ON public.review_job
  FOR INSERT WITH CHECK (user_id = (auth.jwt() ->> 'sub'));

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0041_review_domain',
  'F14 Hakemlik: review_job tablosu (async peer-review işi, mode author/editor, JSONB manuscript/evidence_pack/report, RLS owner). defense_session''dan ayrı.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
