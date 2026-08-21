-- =====================================================================
-- PaperMind v4 — Supabase Migration 0032: defense_session.scan_results (6.4)
-- =====================================================================
-- Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S9
-- RTF:  Page_Design/Sayfa_Plani_v2/6.4_dergi_simulasyonu.rtf §Plan-Detayı (1)
--
-- Eklenen:
--   scan_results jsonb DEFAULT '{}' — dergi simülasyonu birleşik çıktısı:
--     {
--       reviewer_3persona: { skeptik, sempatik, yontemci },
--       statcheck:        { results[], summary },
--       journal_calibration: { distribution, prediction, confidence },
--       revisions: [{ persona, question_index, decision, decided_at }]
--     }
--
-- RTF kararı: "YENİ DB MIGRATION YOK — tüm yapılandırma dosya-bazlı". Bu
-- migration sadece tek kolon ekler (mevcut tablo extend); persona/statcheck
-- prompt+regex setleri engine/ dosyalarında saklanır.
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0028_defense_session, 0031_defense_session_individual_check
-- =====================================================================

BEGIN;

ALTER TABLE public.defense_session
  ADD COLUMN IF NOT EXISTS scan_results jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.defense_session.scan_results IS
  'F13-S9 6.4: 3-persona hakem + statcheck + dergi kalibrasyon + revisions birleşik JSONB. RTF kararı yeni tablo yok; tüm sinyaller burada toplanır.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0032_defense_session_scan_results',
  'F13-S9 6.4 Dergi Simülasyonu: defense_session.scan_results JSONB (3-persona + statcheck + journal_calibration + revisions).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
