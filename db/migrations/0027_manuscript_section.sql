-- =====================================================================
-- PaperMind v4 — Supabase Migration 0027: manuscript_section (F13-S6 6.1 Yayın İçeriği)
-- =====================================================================
-- Plan kaynağı: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S6-P001)
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/6.1_yayin_icerigi_doldurma.rtf §Plan-Detayı (1)
--   Felsefe: 5 bölümlü Emerald-benzeri akademik makale doluluk; 3/5 doluluk +
--   her bölümde min. 50 kelime + ai_quality_flag != 'sahte' → simülasyon kapısı.
--
-- section_type domain'i (RTF §Plan-Detayı (1)):
--   'intro' | 'methods' | 'findings' | 'discussion' | 'conclusion'
--   ENUM yerine CHECK: 0025/0026 pattern; ALTER pahalı, CHECK esnek.
--
-- ai_quality_flag domain'i:
--   NULL = henüz değerlendirilmedi
--   'ok' = akademik içerik
--   'sahte' = lorem ipsum / test metni (Gemini Flash kararı)
--
-- UNIQUE (project_id, section_type): bir proje × bir bölüm = tek satır.
--
-- RLS: owner-only — projects.user_id JOIN (0025 pattern).
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations), 0015 (public.projects)
--
-- Apply:
--   psql "$SUPABASE_DB_URL" -f db/migrations/0027_manuscript_section.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. manuscript_section — 5 bölümlü içerik tablosu
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.manuscript_section (
  id              uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  section_type    text NOT NULL
                  CHECK (section_type IN ('intro','methods','findings','discussion','conclusion')),
  content         text NOT NULL DEFAULT '',
  word_count      int  NOT NULL DEFAULT 0 CHECK (word_count >= 0),
  ai_quality_flag text
                  CHECK (ai_quality_flag IN ('ok','sahte')),
  ai_quality_reason text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, section_type)
);

CREATE INDEX idx_manuscript_section_project ON public.manuscript_section(project_id);

-- updated_at trigger: content / quality_flag güncellenince otomatik bump
CREATE OR REPLACE FUNCTION public.manuscript_section_touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_manuscript_section_updated_at
  BEFORE UPDATE ON public.manuscript_section
  FOR EACH ROW EXECUTE FUNCTION public.manuscript_section_touch_updated_at();

-- ============================================================================
-- 2. RLS — owner-only via projects.user_id JOIN
-- ============================================================================
ALTER TABLE public.manuscript_section ENABLE ROW LEVEL SECURITY;

CREATE POLICY manuscript_section_owner_select ON public.manuscript_section FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = manuscript_section.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY manuscript_section_owner_insert ON public.manuscript_section FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = manuscript_section.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY manuscript_section_owner_update ON public.manuscript_section FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = manuscript_section.project_id AND p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = manuscript_section.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY manuscript_section_owner_delete ON public.manuscript_section FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = manuscript_section.project_id AND p.user_id = auth.uid()
    )
  );

-- ============================================================================
-- 3. Comments
-- ============================================================================
COMMENT ON TABLE public.manuscript_section IS
  '6.1 Yayın İçeriği: 5 bölümlü akademik makale taslağı (intro/methods/findings/discussion/conclusion). Bölüm başına tek kayıt; gate: 3+ doluluk × min. 50 kelime × quality != sahte. Owner-only RLS.';

COMMENT ON COLUMN public.manuscript_section.section_type IS
  'intro | methods | findings | discussion | conclusion. UNIQUE(project_id, section_type) tek satır garanti.';

COMMENT ON COLUMN public.manuscript_section.word_count IS
  'PUT zamanında hesaplanan kelime sayısı (whitespace split). 50+ → gate koşulu.';

COMMENT ON COLUMN public.manuscript_section.ai_quality_flag IS
  'NULL = değerlendirilmedi. ok = akademik içerik. sahte = lorem ipsum/test metni. Gemini Flash kararı; içerik değiştiğinde NULL''a reset.';

-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0027_manuscript_section',
  'F13-S6 6.1 Yayın İçeriği: manuscript_section 5-bölümlü akademik makale taslağı. section_type CHECK 5-değer, word_count cache, ai_quality_flag (ok/sahte/null), RLS owner-only via projects JOIN.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
