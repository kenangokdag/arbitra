-- =====================================================================
-- PaperMind v4 — Supabase Migration 0040:
-- enrichment_log.ghost_id → paper_id rename + FK restore (dormant MAJOR)
-- =====================================================================
-- Audit referansı : AUDIT_REPORT.md §2.6 finding-B2 / M-16
-- Plan referansı  : Wave F1 migration tamir
-- Tarih           : 2026-05-27  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Postgres        : 17.6
-- Bağımlılık      : 0001 (enrichment_log + ghost_id FK to dim_ghost_paper(ghost_id))
--                   0003 (DROP CASCADE dim_ghost_paper → FK düştü; PK rename ghost_id → paper_id)
-- =====================================================================
-- SORUN:
--   0001 enrichment_log.ghost_id text NOT NULL REFERENCES dim_ghost_paper(ghost_id).
--   0003 DROP TABLE dim_ghost_paper CASCADE → FK constraint dropped.
--   0003 yeni dim_ghost_paper.PK adı `paper_id`; FK rebuild edilmedi.
--   Kolon `enrichment_log.ghost_id text` hâlâ var ama hem referential integrity yok
--   hem de hedef PK adı ile uyumsuz (ghost_id ≠ paper_id).
-- DÜZELTME:
--   1) Kolon rename: ghost_id → paper_id (kavramsal uyum)
--   2) Yeni FK: paper_id REFERENCES dim_ghost_paper(paper_id) ON DELETE CASCADE
-- DORMANT NOT:
--   Tablo şu an 0 kod referansı (api/ grep boş). Feature aktive olmadan kapatıldı.
-- =====================================================================

BEGIN;

-- 1) Mevcut FK varsa düşür (0003 CASCADE zaten silmiş olabilir; defensive guard).
ALTER TABLE public.enrichment_log
  DROP CONSTRAINT IF EXISTS enrichment_log_ghost_id_fkey;

-- 2) Kolon adı uyumu — IF EXISTS koru (re-run safe; ikinci çalıştırmada NOP).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'enrichment_log'
      AND column_name = 'ghost_id'
  ) THEN
    ALTER TABLE public.enrichment_log RENAME COLUMN ghost_id TO paper_id;
  END IF;
END $$;

-- 3) Yeni FK — dim_ghost_paper(paper_id) yeni PK adı.
ALTER TABLE public.enrichment_log
  ADD CONSTRAINT enrichment_log_paper_fk
  FOREIGN KEY (paper_id) REFERENCES public.dim_ghost_paper(paper_id) ON DELETE CASCADE;

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0040_fix_enrichment_log_ghost_fk',
  'finding-B2 / M-16 — enrichment_log.ghost_id → paper_id rename + FK restore; dormant MAJOR kapatıldı.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
