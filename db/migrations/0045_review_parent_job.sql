-- =====================================================================
-- PaperMind v4 — Migration 0045: review_job.parent_job_id (versiyon zinciri)
-- =====================================================================
-- Plan: docs/plans/VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17.md §2.1
-- Additive-önce kuralı (0042'nin deseniyle BİREBİR aynı): nullable, default
-- yok → mevcut review_job satırları ve davranışı KIRILMAZ.
--
-- Amaç: kullanıcı revize bir makaleyi tekrar yüklerken (kendi seçtiği,
-- otomatik/sessiz DEĞİL) önceki job'a bağlanabilsin — versiyon karşılaştırma
-- özetinin (verdict/hazırlık puanı/boyut skoru deltası) veri temeli.
--
-- Tarih: 2026-08-17 · PG: 17.x
-- Bağımlılık: 0041 (review_job tablosu).
--
-- ROLLBACK / MITIGATION (veri kaybı YOK — additive):
--   DROP INDEX IF EXISTS public.idx_review_job_parent;
--   ALTER TABLE public.review_job DROP COLUMN IF EXISTS parent_job_id;
--   (uygulama eski davranışla çalışmaya devam eder; parent_job_id opsiyonel.)
-- =====================================================================

BEGIN;

ALTER TABLE public.review_job
  ADD COLUMN IF NOT EXISTS parent_job_id uuid REFERENCES public.review_job(job_id);

COMMENT ON COLUMN public.review_job.parent_job_id IS
  'Kullanıcının BİLİNÇLİ seçtiği önceki versiyon (otomatik/sessiz eşleştirme YOK, F14 versiyon karşılaştırma Faz 1). NULL = ilk yükleme / bağlanmamış.';

CREATE INDEX IF NOT EXISTS idx_review_job_parent
  ON public.review_job (parent_job_id) WHERE parent_job_id IS NOT NULL;

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0045_review_parent_job',
  'review_job.parent_job_id (additive, nullable) — kullanıcı-seçimli versiyon zinciri, VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
