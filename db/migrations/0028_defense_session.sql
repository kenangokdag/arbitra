-- =====================================================================
-- PaperMind v4 — Supabase Migration 0028: defense_session (F13-S7 6.2 Savunma)
-- =====================================================================
-- Plan kaynağı: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S7-P001)
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/6.2_savunma_formati.rtf §Plan-Detayı (1)
--
--   Felsefe: Savunma simülasyonu kişiselleşsin diye gerçek jüri üyelerini ve
--   onların alanlarını gir; her üye için OpenAlex Author + havuz paperlardan
--   kişi-spesifik soru havuzu üret. Stanford-style 2-derinlik zincir.
--
-- session_type domain'i (RTF §Plan-Detayı (1)):
--   'makale' | 'tez' | 'yeterlilik' | 'bildiri'
--   CHECK constraint (0027 pattern; ALTER esnek).
--
-- jury_members JSONB schema:
--   [{name, affiliation?, field, orcid?, openalex_author_id?,
--     found_papers: [{paper_id, title, year, cited_by}], generic_fallback: bool}]
--
-- question_pool JSONB schema:
--   [{jury_member_index, category, question, depth, source_paper_id?,
--     follow_up_questions: [str]}]
--   category: 'method' | 'contribution' | 'limitation' | 'ethics' | 'field_specific'
--   depth: 1..2 (Stanford-style 2-derinlik zincir)
--
-- UNIQUE YOK — bir proje birden fazla deneme oturumu çalıştırabilir (örn.
-- önce makale provası, sonra tez savunması). Aktif oturum frontend tarafında
-- son created_at ile seçilir; istenirse session_id ile spesifik geri getirilir.
--
-- RLS: owner-only — projects.user_id JOIN (0025/0027 pattern).
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations), 0015 (public.projects)
--
-- Apply:
--   psql "$SUPABASE_DB_URL" -f db/migrations/0028_defense_session.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. defense_session — kişiselleştirilmiş savunma oturumu
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.defense_session (
  id              uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  session_type    text NOT NULL
                  CHECK (session_type IN ('makale','tez','yeterlilik','bildiri')),
  scheduled_date  date,
  jury_size       int  NOT NULL CHECK (jury_size BETWEEN 1 AND 7),
  title           text NOT NULL,
  field           text NOT NULL,
  preferred_lang  char(2) NOT NULL DEFAULT 'tr'
                  CHECK (preferred_lang IN ('tr','en')),
  jury_members    jsonb NOT NULL DEFAULT '[]'::jsonb,
  question_pool   jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_defense_session_project ON public.defense_session(project_id);
CREATE INDEX idx_defense_session_project_created
  ON public.defense_session(project_id, created_at DESC);

-- updated_at trigger: jury_members / question_pool / temel alanlar güncellenince
-- otomatik bump.
CREATE OR REPLACE FUNCTION public.defense_session_touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_defense_session_updated_at
  BEFORE UPDATE ON public.defense_session
  FOR EACH ROW EXECUTE FUNCTION public.defense_session_touch_updated_at();

-- ============================================================================
-- 2. RLS — owner-only via projects.user_id JOIN
-- ============================================================================
ALTER TABLE public.defense_session ENABLE ROW LEVEL SECURITY;

CREATE POLICY defense_session_owner_select ON public.defense_session FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = defense_session.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY defense_session_owner_insert ON public.defense_session FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = defense_session.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY defense_session_owner_update ON public.defense_session FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = defense_session.project_id AND p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = defense_session.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY defense_session_owner_delete ON public.defense_session FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = defense_session.project_id AND p.user_id = auth.uid()
    )
  );

-- ============================================================================
-- 3. Comments
-- ============================================================================
COMMENT ON TABLE public.defense_session IS
  '6.2 Savunma Formatı: kişiselleştirilmiş savunma oturumu (makale/tez/yeterlilik/bildiri). jury_members + question_pool JSONB; aynı proje için çok satır (geçmiş oturumlar). Owner-only RLS.';

COMMENT ON COLUMN public.defense_session.session_type IS
  'makale | tez | yeterlilik | bildiri. CHECK 4-değer; ENUM yerine.';

COMMENT ON COLUMN public.defense_session.jury_members IS
  'JSONB: [{name, affiliation?, field, orcid?, openalex_author_id?, found_papers:[{paper_id,title,year,cited_by}], generic_fallback}]. Generic mode = OpenAlex match yok.';

COMMENT ON COLUMN public.defense_session.question_pool IS
  'JSONB: [{jury_member_index, category, question, depth, source_paper_id?, follow_up_questions[]}]. category: method|contribution|limitation|ethics|field_specific. depth 1..2.';

COMMENT ON COLUMN public.defense_session.preferred_lang IS
  'tr | en — kullanıcının savunmayı yapacağı dil; soru havuzu bu dilde üretilir.';

-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0028_defense_session',
  'F13-S7 6.2 Savunma Formatı: defense_session kişiselleştirilmiş savunma oturumu (4 tür). jury_members + question_pool JSONB; Stanford-style 2-derinlik zincir; RLS owner-only via projects JOIN.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
