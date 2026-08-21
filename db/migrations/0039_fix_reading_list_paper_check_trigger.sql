-- =====================================================================
-- PaperMind v4 — Supabase Migration 0039:
-- check_reading_list_paper_exists trigger function fix (dormant BLOCKER)
-- =====================================================================
-- Audit referansı : AUDIT_REPORT.md §2.6 finding-B1 / B-8
-- Plan referansı  : Wave F1 migration tamir
-- Tarih           : 2026-05-27  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Postgres        : 17.6
-- Bağımlılık      : 0001 (trigger function + trigger) · 0003 (DROP CASCADE dim_ghost_paper, PK rename ghost_id → paper_id)
-- =====================================================================
-- SORUN:
--   0001'de trigger fonksiyonu `WHERE ghost_id = NEW.paper_id` yazıyordu.
--   0003 dim_ghost_paper'ı DROP+CREATE etti; yeni PK adı `paper_id` (eski `ghost_id` yok).
--   Trigger fonksiyonu güncellenmedi → ghost paper INSERT'i `column "ghost_id" does not exist`
--   ile patlar. Şu an dormant: reading_list_service.py hardcoded `paper_kind='corpus'`.
-- DÜZELTME:
--   CREATE OR REPLACE FUNCTION ile fonksiyon gövdesini günceller; ghost dalı
--   `dim_ghost_paper.paper_id` kolonunu sorgular. Trigger zaten doğru fonksiyonu
--   çağırıyor (CREATE OR REPLACE etkisi anlık).
-- =====================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.check_reading_list_paper_exists()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.paper_kind = 'corpus' THEN
    IF NOT EXISTS (SELECT 1 FROM public.papers WHERE paper_id = NEW.paper_id) THEN
      RAISE EXCEPTION 'paper_not_found: corpus paper_id=% does not exist', NEW.paper_id
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  ELSIF NEW.paper_kind = 'ghost' THEN
    IF NOT EXISTS (SELECT 1 FROM public.dim_ghost_paper WHERE paper_id = NEW.paper_id) THEN
      RAISE EXCEPTION 'paper_not_found: ghost paper_id=% does not exist', NEW.paper_id
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0039_fix_reading_list_paper_check_trigger',
  'finding-B1 / B-8 — ghost dalı dim_ghost_paper.paper_id (0003 rename sonrası), dormant BLOCKER kapatıldı.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
