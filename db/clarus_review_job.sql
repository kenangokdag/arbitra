-- =====================================================================
-- ARBITRA (F14 hakemlik) — Clarus Supabase'e İZOLE review_job tablosu
-- =====================================================================
-- Hedef proje: Clarus (project_ref qoojmhaagwbvxjlthjaa)
-- Karar: B-F14-09 / B-F14-12 — review_job izole, backend-only (service-role).
--
-- NASIL ÇALIŞTIRILIR (MCP'siz, en güvenli):
--   Clarus Supabase Dashboard → SQL Editor → New query → bu dosyayı YAPIŞTIR → Run.
--   (Hiçbir secret paylaşman gerekmez.)
--
-- NEDEN papermind'in 0041'inden farklı:
--   - schema_migrations INSERT'i YOK (o papermind'e özgü; Clarus onu izlemez).
--   - RLS = deny-all (policy yok): tabloya yalnız service-role erişir; uygulama
--     sahipliği review_service'te user_id ile doğrular (auth.jwt() Clarus'a göre
--     papermind kullanıcısıyla eşleşmez, o yüzden owner-policy yerine backend-only).
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
  'ARBITRA (papermind F14 hakemlik) izole işi. Backend-only (service-role). Clarus projesinde misafir tablo.';

CREATE INDEX IF NOT EXISTS idx_review_job_user
  ON public.review_job (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_job_status
  ON public.review_job (status) WHERE status NOT IN ('done', 'failed');

-- RLS açık + policy YOK → service-role dışında her erişim reddedilir (izolasyon).
ALTER TABLE public.review_job ENABLE ROW LEVEL SECURITY;

COMMIT;

-- Doğrulama (opsiyonel, ayrı çalıştır):
--   SELECT count(*) FROM public.review_job;            -- 0 dönmeli
--   SELECT relrowsecurity FROM pg_class WHERE relname='review_job';  -- t (true)
