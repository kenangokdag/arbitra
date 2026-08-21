-- =====================================================================
-- PaperMind v4 — Supabase Migration 0026: silent_learning (5.3 Akademik Dil)
-- =====================================================================
-- Plan kaynağı: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S3)
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/5.3_akademik_dil_uslup.rtf §Plan-Detayı (1)
--
-- İki tablo:
--   1) user_silent_learning_log — paraphrase kararları akışı (accept/reject/edit)
--      RLS owner-only; 30-günlük TTL (kullanıcı stilini öğrenmek için yeterli pencere)
--   2) user_style_profile — kullanıcı × dil bazlı agregat stil tercihleri
--      Composite PK (user_id, lang); JSONB profile alanı; sample_size = güven göstergesi
--
-- decision ENUM yerine CHECK (ALTER esnek, 0025 pattern).
-- section_context: intro/methods/findings/discussion/null — IMRaD bölüm context'i.
-- lang: CHAR(2) tr/en/id — RTF §Felsefe (3 dil yerli destek).
--
-- Tarih: 2026-05-10 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations), 0012 (auth.users), 0015 (projects)
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. user_silent_learning_log — paraphrase karar akışı
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_silent_learning_log (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id          uuid NOT NULL,
  sentence_original   text NOT NULL,
  sentence_proposed   text NOT NULL,
  decision            text NOT NULL
                      CHECK (decision IN ('accept','reject','edit')),
  edited_text         text,
  decision_at         timestamptz NOT NULL DEFAULT now(),
  lang                char(2) NOT NULL
                      CHECK (lang IN ('tr','en','id')),
  section_context     text
                      CHECK (section_context IN ('intro','methods','findings','discussion') OR section_context IS NULL),
  meta                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_silent_learning_user_lang_time
  ON public.user_silent_learning_log (user_id, lang, decision_at DESC);

CREATE INDEX IF NOT EXISTS idx_silent_learning_session
  ON public.user_silent_learning_log (session_id);

-- ============================================================================
-- 2. user_style_profile — agregat stil tercihi (kullanıcı × dil)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_style_profile (
  user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lang          char(2) NOT NULL
                CHECK (lang IN ('tr','en','id')),
  profile       jsonb NOT NULL DEFAULT '{}'::jsonb,
  sample_size   integer NOT NULL DEFAULT 0
                CHECK (sample_size >= 0),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, lang)
);

CREATE OR REPLACE FUNCTION public.user_style_profile_touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_style_profile_updated_at
  BEFORE UPDATE ON public.user_style_profile
  FOR EACH ROW EXECUTE FUNCTION public.user_style_profile_touch_updated_at();

-- ============================================================================
-- 3. RLS — owner-only
-- ============================================================================
ALTER TABLE public.user_silent_learning_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY silent_learning_owner_select ON public.user_silent_learning_log
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY silent_learning_owner_insert ON public.user_silent_learning_log
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY silent_learning_owner_delete ON public.user_silent_learning_log
  FOR DELETE USING (user_id = auth.uid());

ALTER TABLE public.user_style_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY style_profile_owner_select ON public.user_style_profile
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY style_profile_owner_insert ON public.user_style_profile
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY style_profile_owner_update ON public.user_style_profile
  FOR UPDATE USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY style_profile_owner_delete ON public.user_style_profile
  FOR DELETE USING (user_id = auth.uid());

-- ============================================================================
-- 4. TTL (30 gün) — manuel cron temizleme (F13-S14 cron job)
-- ============================================================================
-- Cron işi (F13-S14): DELETE FROM user_silent_learning_log WHERE decision_at < now() - interval '30 days';

-- ============================================================================
-- 5. Comments
-- ============================================================================
COMMENT ON TABLE public.user_silent_learning_log IS
  '5.3 Akademik Dil: kullanıcının paraphrase kararları (accept/reject/edit). 30-gün TTL — F13-S14 cron temizler. Pattern aggregation user_style_profile''e yazılır.';

COMMENT ON TABLE public.user_style_profile IS
  '5.3 Akademik Dil: kullanıcı × dil bazlı agregat stil tercihleri (passive_voice_pref, hedge_term_freq, avg_sentence_length, accepted/rejected_patterns). sample_size = güven göstergesi.';

COMMENT ON COLUMN public.user_silent_learning_log.section_context IS
  'IMRaD bölüm context (5.2''den): intro/methods/findings/discussion. NULL = bölüm bağımsız.';

COMMENT ON COLUMN public.user_style_profile.profile IS
  'JSONB: {avg_sentence_length, passive_voice_pref [0,1], hedge_term_freq (low|medium|high), accepted_patterns[], rejected_patterns[]}.';

-- ============================================================================
-- 6. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0026_silent_learning',
  'F13-S3 5.3 Akademik Dil: user_silent_learning_log (paraphrase kararı akışı, 30-gün TTL) + user_style_profile (kullanıcı × dil agregat). RLS owner-only.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
