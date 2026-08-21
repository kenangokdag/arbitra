-- =====================================================================
-- PaperMind v4 — Migration 0044: review_job KVKK retention enforcement (additive)
-- =====================================================================
-- Bozuk söz kapatma: web/src/app/(app)/review/page.tsx UI'si "bu süre sonunda
-- yüklenen dosya silinir" vaat eder; retention_days api/routes/review.py'de
-- yakalanıp review_job.privacy JSONB'sine yazılır AMA hiçbir şey süresi geçen
-- işi SİLMEZ. Bu migration delete_after eşiğini açar; cron
-- scripts/cron/review_retention_delete_expired.py bu eşik ile DELETE çalıştırır
-- (project_completion delete_after deseninin birebir aynası — 0030/F13-S14).
--
-- TÜM değişiklikler ADDITIVE + idempotent (IF NOT EXISTS) → mevcut review_job
-- satırları ve 0041/0042 davranışı KIRILMAZ. manuscript + report satır içinde
-- (inline JSONB) tutulduğundan satırı silmek yüklenen içeriği de siler — ayrı
-- object storage yok (0041).
--
-- Eklenen:
--   delete_after  timestamptz — KVKK retention eşiği (created_at + retention_days).
--   idx_review_job_delete_after — cron toplu silme için (delete_after < now()).
--   Backfill: mevcut satırlara created_at + COALESCE(privacy.retention_days, 30) gün.
--
-- Tarih: 2026-06-26 · PG: 17.x
-- Bağımlılık: 0041 (review_job + privacy JSONB), 0042 (privacy kolonu additive).
--
-- ROLLBACK / MITIGATION (veri kaybı YOK — additive):
--   ALTER TABLE public.review_job DROP COLUMN IF EXISTS delete_after;
--   DROP INDEX IF EXISTS public.idx_review_job_delete_after;
--   (cron pasifleşir; retention enforcement durur, mevcut veri korunur.)
--
-- Apply (notebook DIŞINDA — K-029 dersi):
--   psql "$REVIEW_SUPABASE_DB_URL" -f db/migrations/0044_review_retention_delete_after.sql
--   (review IZOLE Supabase; REVIEW_* boşsa default SUPABASE_DB_URL.)
-- =====================================================================

BEGIN;

ALTER TABLE public.review_job
  ADD COLUMN IF NOT EXISTS delete_after timestamptz;

-- Backfill: mevcut işlere retention eşiği ver (privacy.retention_days yoksa 30 gün).
UPDATE public.review_job
  SET delete_after = created_at
    + (COALESCE((privacy->>'retention_days')::int, 30) || ' days')::interval
  WHERE delete_after IS NULL;

-- Cron-friendly: süresi geçmiş işleri toplu silmek için (delete_after < now()).
CREATE INDEX IF NOT EXISTS idx_review_job_delete_after
  ON public.review_job (delete_after);

COMMENT ON COLUMN public.review_job.delete_after IS
  'KVKK retention eşiği = created_at + privacy.retention_days (default 30g). '
  'review_retention_delete_expired cron bu eşikle DELETE çalıştırır (UI "dosya silinir" sözü). '
  'review_service._insert_job insert anında set eder; backfill mevcut satırlar için.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0044_review_retention_delete_after',
  'review_job KVKK retention (additive): delete_after kolonu + index + backfill. '
  'Cron review_retention_delete_expired süresi geçen işi siler (UI dosya-silme sözü). Veri kaybı yok.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
