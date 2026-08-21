-- =====================================================================
-- PaperMind v4 — Supabase Migration 0025: project_progress (S2 5.1 Yayın Formatı)
-- =====================================================================
-- Plan kaynağı: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S2-P001)
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/5.1_yayin_formati.rtf §Plan-Detayı (1)
--   Felsefe: "Danışmana Gitmeden Evvel" kapısı — kullanıcı her sayfa adımının
--   tamamlanma durumunu izler; yayın türüne göre zorunlu/opsiyonel maske ile
--   olgunluk yüzdesi hesaplanır; %100 → akademik özet üretimi aktif.
--
-- step_id konvansiyonu (Omer 2026-05-10 kararı):
--   FE route slug — `discovery-1`..`discovery-5`, `curation-1`..`curation-5`,
--   `gapatlas-1`..`gapatlas-5`, `authoring-1`..`authoring-4`, `defense-1`..`defense-6`
--   kaynak: web/src/lib/nav-config.ts:61-117
--
-- Şema sözleşmesi (RTF §Plan-Detayı (1) satır 53-66):
--   project_id (FK projects), step_id, status, completed_at?, meta jsonb
--   PRIMARY KEY (project_id, step_id) — bir adım bir kez kayıtlı
--
-- status domain'i:
--   'not_started' / 'in_progress' / 'completed'
--   ENUM yerine CHECK: 0029 pattern; ENUM ALTER pahalı, CHECK esnek.
--
-- İndeks: (project_id) zaten composite PK'de prefix; ekstra index gereksiz.
--
-- RLS: owner-only — kullanıcı yalnızca kendi project'lerinin progress'ini görür.
--   project tablosu üzerinden user_id JOIN policy.
--
-- Tarih: 2026-05-10 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations), 0015 (public.projects)
--
-- Apply (notebook DIŞINDA — K-029 dersi):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0025_project_progress.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. project_progress — adım-bazlı yayın olgunluk state machine
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_progress (
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  step_id       text NOT NULL CHECK (char_length(step_id) BETWEEN 1 AND 60),
  status        text NOT NULL DEFAULT 'not_started'
                CHECK (status IN ('not_started','in_progress','completed')),
  completed_at  timestamptz,
  meta          jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, step_id)
);

-- updated_at trigger: status / meta güncellenince otomatik bump
CREATE OR REPLACE FUNCTION public.project_progress_touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_progress_updated_at
  BEFORE UPDATE ON public.project_progress
  FOR EACH ROW EXECUTE FUNCTION public.project_progress_touch_updated_at();

-- ============================================================================
-- 2. RLS — owner-only via projects.user_id JOIN
-- ============================================================================
ALTER TABLE public.project_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY project_progress_owner_select ON public.project_progress FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = project_progress.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY project_progress_owner_insert ON public.project_progress FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = project_progress.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY project_progress_owner_update ON public.project_progress FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = project_progress.project_id AND p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = project_progress.project_id AND p.user_id = auth.uid()
    )
  );

CREATE POLICY project_progress_owner_delete ON public.project_progress FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.projects p
      WHERE p.id = project_progress.project_id AND p.user_id = auth.uid()
    )
  );

-- ============================================================================
-- 3. Comments
-- ============================================================================
COMMENT ON TABLE public.project_progress IS
  '5.1 Yayın Formatı: adım-bazlı state machine. step_id = FE route slug (discovery-1, gapatlas-4, ...). publication_type maskesi runtime''da uygulanır. Owner-only RLS.';

COMMENT ON COLUMN public.project_progress.step_id IS
  'FE route slug (web/src/lib/nav-config.ts:61-117): discovery-1..5, curation-1..5, gapatlas-1..5, authoring-1..4, defense-1..6.';

COMMENT ON COLUMN public.project_progress.status IS
  'not_started | in_progress | completed. CHECK ile sınırlanır; ENUM tercih edilmedi (ALTER pahalı).';

COMMENT ON COLUMN public.project_progress.meta IS
  'Adıma özel çıktı referansları: çapa adı, gap matrix_id, sentez_id vb. JSONB → şema değişimine geri-uyumlu.';

-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0025_project_progress',
  'F13-S2 5.1 Yayın Formatı: project_progress (adım-bazlı state machine). status CHECK 3-değer, meta JSONB, RLS owner-only via projects JOIN.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
