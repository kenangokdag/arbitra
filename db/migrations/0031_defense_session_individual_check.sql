-- =====================================================================
-- PaperMind v4 — Supabase Migration 0031: defense_session ALTER (6.3)
-- =====================================================================
-- Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S8
-- RTF:  Page_Design/Sayfa_Plani_v2/6.3_bireysel_kontrol.rtf §Plan-Detayı (2)
--
-- Eklenenler:
--   individual_check  jsonb DEFAULT '[]' — checklist cevap kayıtları
--     [{ checklist_id: str, item_id: str, response: 'evet'|'hayir'|'yapamadim',
--        noted_at: timestamptz }]
--   target_journal_id text NULL — makale yolu "bu dergiyi hedef yap" seçimi
--     (dim_journal henüz canlı değil; basit ISSN veya UUID stringi)
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0028_defense_session
-- =====================================================================

BEGIN;

ALTER TABLE public.defense_session
  ADD COLUMN IF NOT EXISTS individual_check  jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS target_journal_id text;

COMMENT ON COLUMN public.defense_session.individual_check IS
  'F13-S8 6.3: kullanıcının checklist cevap geçmişi [{ checklist_id, item_id, response, noted_at }]. evet|hayir|yapamadim CHECK string seviyesinde değil — service-side enforce.';

COMMENT ON COLUMN public.defense_session.target_journal_id IS
  'F13-S8 6.3: "Bu dergiyi hedef yap" sonrası seçilen dergi anahtarı (dim_journal henüz canlı değil; v1 basit string). 6.4 dergi simülasyonu bu hedefe yönlenir.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0031_defense_session_individual_check',
  'F13-S8 6.3 Bireysel Kontrol: defense_session.individual_check (JSONB) + target_journal_id (text).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
