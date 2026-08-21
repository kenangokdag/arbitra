-- =====================================================================
-- ARBITRA (F14 hakemlik) — İZOLE Supabase projesi için TEK-PARÇA kurulum
-- =====================================================================
-- 2026-08-14: db/clarus_review_job.sql'in GÜNCEL hali. O dosya sadece
-- migration 0041'i yansıtıyordu (review_job'ın ilk hali) — kod bugün
-- 0042 (idempotency_key, stages, lifecycle, privacy, classification,
-- schema_version) ve 0044'ün (delete_after, KVKK retention) eklediği
-- kolonlara da ihtiyaç duyuyor. Bu dosya 0041+0042+0044'ün TOPLAM/nihai
-- şemasını TEK sorguda kurar — 44 numaralı migration'ın tamamını
-- çalıştırmaya GEREK YOK (onlar papermind'in diğer, review-dışı
-- alanları için; review_job'a sadece bu 3 migration dokunuyor).
--
-- NASIL ÇALIŞTIRILIR:
--   Yeni Supabase projesi → Dashboard → SQL Editor → New query →
--   bu dosyanın TAMAMINI yapıştır → Run.
--
-- SONRA .env'e ekle (proje Ayarlar → API'den):
--   SUPABASE_URL=https://<project-ref>.supabase.co
--   SUPABASE_SECRET_KEY=<service_role secret key>
--   (REVIEW_SUPABASE_* boş bırakılabilir — kod SUPABASE_*'e düşer,
--    bkz. api/db/supabase_client.py::get_review_supabase_admin)
--
-- RLS notu: policy YOK, deny-all — sadece service-role (backend) erişir.
-- review_service.py TÜM sorguları get_review_supabase_admin() (service-role)
-- ile yapıyor, RLS'i zaten bypass ediyor — owner-policy (auth.jwt() sub
-- eşleşmesi) burada anlamsız olurdu (Clarus'un aynı gerekçesi, bkz.
-- db/clarus_review_job.sql yorumu) çünkü dev-modda JWT imzası doğrulanmıyor,
-- gerçek bir Supabase Auth oturumu yok.
-- =====================================================================

BEGIN;

-- --- 0041: temel tablo -------------------------------------------------
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
  source_name   text,
  source_kind   text CHECK (source_kind IN ('pdf', 'docx', 'latex', 'zip')),
  manuscript    jsonb,
  evidence_pack jsonb,
  report        jsonb,
  error         text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.review_job IS
  'ARBITRA (F14 hakemlik) izole işi. Backend-only (service-role). db/review_job_standalone_setup.sql ile kuruldu (0041+0042+0044 birleşik).';

CREATE INDEX IF NOT EXISTS idx_review_job_user
  ON public.review_job (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_job_status
  ON public.review_job (status) WHERE status NOT IN ('done', 'failed');

-- --- 0042: worldclass v2 (additive) ------------------------------------
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
  'ReviewStageState[] — durable worker per-stage checkpoint. FE StageTimeline bunu okur.';
COMMENT ON COLUMN public.review_job.privacy IS
  'PrivacyConfig v1 — confidentiality_mode + external_ai_consent + retention_days.';
COMMENT ON COLUMN public.review_job.classification IS
  'DocumentClassification — belge/çalışma türü + confidence + user override (rubric routing kaynağı).';

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_job_idempotency
  ON public.review_job (user_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_review_job_resume
  ON public.review_job (updated_at)
  WHERE status NOT IN ('done', 'failed');

-- --- 0044: KVKK retention (additive) ------------------------------------
ALTER TABLE public.review_job
  ADD COLUMN IF NOT EXISTS delete_after timestamptz;

CREATE INDEX IF NOT EXISTS idx_review_job_delete_after
  ON public.review_job (delete_after);

COMMENT ON COLUMN public.review_job.delete_after IS
  'KVKK retention eşiği = created_at + privacy.retention_days (default 30g). review_retention_delete_expired cron bu eşikle DELETE çalıştırır.';

-- --- RLS: deny-all (yalnız service-role erişir) -------------------------
ALTER TABLE public.review_job ENABLE ROW LEVEL SECURITY;
-- Bilinçli olarak HİÇBİR policy eklenmiyor — service-role RLS'i zaten
-- bypass eder (backend tüm sorguları get_review_supabase_admin() ile
-- yapıyor); policy eklemek dev-modda kullanılmayan bir auth.jwt() eşleşmesi
-- varsayardı (Clarus dosyasının aynı gerekçesi).

COMMIT;

-- Doğrulama (opsiyonel, ayrı çalıştır):
--   SELECT count(*) FROM public.review_job;                         -- 0 dönmeli
--   SELECT column_name FROM information_schema.columns
--     WHERE table_name = 'review_job' ORDER BY ordinal_position;    -- 22 kolon olmalı
