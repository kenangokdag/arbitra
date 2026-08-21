-- =====================================================================
-- PaperMind v4 — Migration 0042: F14 Hakemlik worldclass v2 (additive)
-- =====================================================================
-- Plan: docs/worldclass/SPECS/data_model_migration_spec.md (additive-önce kuralı).
-- SPINE-1 veri sözleşmesi v2'nin DB karşılığı. TÜM kolonlar ADDITIVE + nullable/
-- default → mevcut review_job satırları ve 0041 davranışı KIRILMAZ.
--
-- Eklenen kolonlar (review_job):
--   lifecycle        — üst-seviye yaşam döngüsü (flat status'ün yanında).
--   stages           — per-stage durum listesi (ReviewStageState[], FE timeline).
--   privacy          — PrivacyConfig (confidentiality + external_ai_consent + retention).
--   idempotency_key  — duplicate enqueue koruması (aynı user+doc+config → aynı job).
--   classification   — DocumentClassification (belge+çalışma türü, confidence, override).
--   schema_version   — review_report.v1 / v2 ayrımı (report jsonb içinde de var; sorgu kolaylığı).
--
-- Tarih: 2026-06-25 · PG: 17.x
-- Bağımlılık: 0041 (review_job).
--
-- ROLLBACK / MITIGATION (veri kaybı YOK — additive):
--   ALTER TABLE public.review_job
--     DROP COLUMN IF EXISTS lifecycle, DROP COLUMN IF EXISTS stages,
--     DROP COLUMN IF EXISTS privacy, DROP COLUMN IF EXISTS idempotency_key,
--     DROP COLUMN IF EXISTS classification, DROP COLUMN IF EXISTS schema_version;
--   DROP INDEX IF EXISTS public.idx_review_job_idempotency;
--   (uygulama eski kolonlarla çalışmaya devam eder; v2 alanları opsiyonel.)
-- =====================================================================

BEGIN;

ALTER TABLE public.review_job
  ADD COLUMN IF NOT EXISTS lifecycle       text
    CHECK (lifecycle IS NULL OR lifecycle IN
      ('queued', 'running', 'stage_failed', 'completed', 'cancelled')),
  ADD COLUMN IF NOT EXISTS stages          jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS privacy         jsonb,
  ADD COLUMN IF NOT EXISTS idempotency_key text,
  ADD COLUMN IF NOT EXISTS classification  jsonb,
  ADD COLUMN IF NOT EXISTS schema_version  text NOT NULL DEFAULT 'review_report.v1';

COMMENT ON COLUMN public.review_job.stages IS
  'ReviewStageState[] — durable worker per-stage checkpoint (P02). FE StageTimeline bunu okur.';
COMMENT ON COLUMN public.review_job.privacy IS
  'PrivacyConfig v1 — confidentiality_mode + external_ai_consent + retention_days (P01-T03 consent gate kaynağı).';
COMMENT ON COLUMN public.review_job.classification IS
  'DocumentClassification — belge/çalışma türü + confidence + user override (P03 rubric routing kaynağı).';

-- Idempotency: aynı kullanıcı için aynı key tek job (kısmi unique; NULL serbest).
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_job_idempotency
  ON public.review_job (user_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- Durable resume için: orphan (mid-run) işleri worker bulsun.
CREATE INDEX IF NOT EXISTS idx_review_job_resume
  ON public.review_job (updated_at)
  WHERE status NOT IN ('done', 'failed');

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0042_review_worldclass_v2',
  'F14 worldclass v2 (additive): review_job + lifecycle/stages/privacy/idempotency_key/classification/schema_version. Consent gate + durable stage + rubric routing + idempotency için. Veri kaybı yok.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
