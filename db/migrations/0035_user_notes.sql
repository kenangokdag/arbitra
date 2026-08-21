-- =====================================================================
-- PaperMind v4 — Supabase Migration 0035:
-- user_notes: paper-başına çoklu not (reading_list.note tekil alanın yerine)
-- =====================================================================
-- Plan referansı : 2026-05-26 Madde 1 — reading_list + notes Supabase persist
-- Tarih          : 2026-05-26
-- Postgres       : 17.6
-- Bağımlılık     : 0001_init_schema_v1.sql (auth.users, public.paper_kind, set_updated_at)
-- Apply mode     : MANUEL (Omer Supabase Dashboard → SQL Editor)
-- =====================================================================
-- Amaç:
--   user_reading_list.note (TEKIL) yerine, 1 paper'a N not yazılabilen
--   ayrı tablo. Notes endpoint'i (api/routes/notes.py) bu tabloya bağlanır.
--
-- Tasarım:
--   - paper_kind enum (corpus|ghost) — 0001'den miras
--   - papers existence trigger YOK (lazy mirror; endpoint OpenAlex'ten upsert)
--   - RLS: auth.uid() = user_id (self-all)
--   - updated_at trigger: set_updated_at() (0001'de mevcut)
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_notes (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  paper_id              text,                              -- NULL: serbest not (paper'a bağlı değil)
  paper_kind            public.paper_kind,                  -- paper_id NULL ise NULL
  content               text NOT NULL CHECK (length(content) > 0 AND length(content) <= 8000),
  tags                  text[] NOT NULL DEFAULT '{}',
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_notes_user_updated
  ON public.user_notes(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_notes_user_paper
  ON public.user_notes(user_id, paper_id);

DROP TRIGGER IF EXISTS trg_user_notes_updated_at ON public.user_notes;
CREATE TRIGGER trg_user_notes_updated_at
  BEFORE UPDATE ON public.user_notes
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.user_notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_notes_self_all ON public.user_notes;
CREATE POLICY user_notes_self_all ON public.user_notes
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE public.user_notes IS
  '2026-05-26 Madde 1: paper-başına çoklu not. user_reading_list.note (tekil) '
  'yerini alır. Notes endpoint (api/routes/notes.py) bu tabloya yazar/okur.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0035_user_notes',
  '2026-05-26 Madde 1: paper-başına çoklu not tablosu (RLS self-all). '
  'reading_list.note tekil alandan ayrılır; notes endpoint persist edilir.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
