-- =====================================================================
-- PaperMind v4 — Supabase Migration 0030: project_completion (F13-S13)
-- =====================================================================
-- Plan kaynağı: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S13
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/S2_proje_tamamlama.rtf
--
--   Felsefe (S2 RTF Felsefe/Amaç): Kullanıcı "tamamla" der; sistem
--   project_event + manuscript_section + defense_session + revision verilerini
--   toplar; her adım için "başarılı/geliştirilmeli" rozeti + LLM tek paragraf
--   yorum üretir. Mezun çıktısı: özet rapor + sonraki adım önerileri.
--   Değerlendirme formu: 5-soru. Hafıza: KVKK uyumlu 3 ay sonra otomatik silme.
--
-- snapshot JSONB schema:
--   {
--     "step_reviews": [{"step_id": str, "status": "basarili"|"gelistirilmeli",
--                       "score": float, "comment": str}],
--     "badges": {"basarili": int, "gelistirilmeli": int},
--     "graduate_advice": [str, ...],  -- mezun için ileri-adım önerileri
--     "summary_paragraph": str         -- LLM tek paragraf genel yorum
--   }
--
-- feedback JSONB schema (RTF: 5-soru):
--   {
--     "topic_suggestion_rating": int 1-5,    -- konu önerisi tatmin
--     "process_rating": int 1-5,             -- süreç tatmin
--     "missing_features": str,               -- eksiklikler
--     "overall_satisfaction": int 1-5,       -- genel tatmin
--     "nps": int 0-10                        -- net promoter score
--   }
--
-- delete_after: completed_at + 3 ay (RTF: KVKK uyumlu otomatik silme).
--   Cron F13-S14'te bağlanır; bu migration sadece veri sütununu açar.
--
-- UNIQUE (project_id): bir proje sadece bir kez tamamlanabilir (re-open ileri iş).
--
-- RLS: owner-only — projects.user_id JOIN (0027/0028/0029 pattern).
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations, auth.users), 0015 (public.projects)
--
-- Apply (notebook DIŞINDA — K-029 dersi):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0030_project_completion.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. project_completion — proje kapanış snapshot + feedback
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_completion (
  id              uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  completed_at    timestamptz NOT NULL DEFAULT now(),
  snapshot        jsonb NOT NULL DEFAULT '{}'::jsonb,
  feedback        jsonb NOT NULL DEFAULT '{}'::jsonb,
  pdf_url         text,
  delete_after    timestamptz NOT NULL DEFAULT (now() + INTERVAL '3 months'),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id)
);

CREATE INDEX idx_project_completion_user
  ON public.project_completion (user_id, completed_at DESC);

-- Cron-friendly: 3 ay geçmiş satırları toplu silmek için
CREATE INDEX idx_project_completion_delete_after
  ON public.project_completion (delete_after);

-- ============================================================================
-- 2. RLS — owner-only (0029 pattern: doğrudan user_id eşitlik)
-- ============================================================================
ALTER TABLE public.project_completion ENABLE ROW LEVEL SECURITY;

CREATE POLICY project_completion_owner_select ON public.project_completion FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY project_completion_owner_insert ON public.project_completion FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY project_completion_owner_update ON public.project_completion FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY project_completion_owner_delete ON public.project_completion FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================================
-- 3. Comments
-- ============================================================================
COMMENT ON TABLE public.project_completion IS
  'S2 Proje Tamamlama: kapanış snapshot + 5-soru feedback + KVKK 3 ay delete. UNIQUE per project.';

COMMENT ON COLUMN public.project_completion.snapshot IS
  'JSONB: step_reviews [{step_id,status,score,comment}], badges, graduate_advice, summary_paragraph.';

COMMENT ON COLUMN public.project_completion.feedback IS
  'JSONB: 5-soru — topic_suggestion_rating, process_rating, missing_features, overall_satisfaction, nps.';

COMMENT ON COLUMN public.project_completion.delete_after IS
  'completed_at + 3 ay. F13-S14 cron job bu eşik ile DELETE çalıştırır (KVKK uyumlu).';

COMMENT ON COLUMN public.project_completion.pdf_url IS
  'Mezun raporu PDF Storage URL''i (V2). V1''de NULL kalır; FE render eder.';

-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0030_project_completion',
  'F13-S13 S2 Proje Tamamlama: project_completion (snapshot + feedback + delete_after 3 ay). UNIQUE per project, RLS owner-only.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
