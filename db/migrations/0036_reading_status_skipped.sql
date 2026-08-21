-- =====================================================================
-- PaperMind v4 — Supabase Migration 0036:
-- reading_status: 'skipped' enum değeri ekle
-- =====================================================================
-- Plan referansı : 2026-05-26 Madde 1 — reading_list Supabase persist
-- Tarih          : 2026-05-26
-- Postgres       : 17.6
-- Bağımlılık     : 0001_init_schema_v1.sql (public.reading_status enum)
-- Apply mode     : MANUEL (Omer Supabase Dashboard → SQL Editor)
-- =====================================================================
-- Amaç:
--   API ReadingStatus (want_to_read|reading|finished|skipped) DB enum
--   (to_read|reading|done) arasındaki uyumsuzluğu kapat. 'skipped' web'de
--   aktif tab (reading-list/page.tsx:22) — DB'de yok, eklenmeli.
--
-- API ↔ DB eşleme (api/routes/reading_list.py):
--   want_to_read → to_read
--   reading      → reading
--   finished     → done
--   skipped      → skipped (BU MIGRATION sonrası)
-- =====================================================================

ALTER TYPE public.reading_status ADD VALUE IF NOT EXISTS 'skipped';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0036_reading_status_skipped',
  '2026-05-26 Madde 1: reading_status enum''una skipped eklendi. '
  'API ReadingStatus (want_to_read|reading|finished|skipped) ↔ DB uyumu.'
)
ON CONFLICT (version) DO NOTHING;
