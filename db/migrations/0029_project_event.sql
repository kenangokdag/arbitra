-- =====================================================================
-- PaperMind v4 — Supabase Migration 0029: project_event (S1 Araştırma Defteri)
-- =====================================================================
-- Plan kaynağı: docs/plans/F12_sayfa_plani_v2_implementation.md §3 (F13-S1-P001)
-- Sayfa kaynağı: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf
--   Felsefe: PaperMind iteratif; her sayfada "Ajandama Kaydet / Danışmana Sor /
--   Kütüphaneme Ekle" event üretir; bu tablo zaman çizgisi olarak rendır edilir.
--
-- Şema sözleşmesi (S1 §Plan-Detayı, satır 53-66):
--   id, project_id, user_id, page_slug, paper_id?, event_type, payload, created_at, resolved_at
--
-- event_type domain'i (S1 §Backend, satır 75-77):
--   'kayit'           → "Ajandama Kaydet"
--   'danismana_sor'   → "Danışmana Sor"  (danışman akışı tetiklenir)
--   'kutuphane_ekle'  → "Kütüphaneme Ekle" (dim_user_library upsert)
--   'not'             → serbest not
--   ENUM yerine CHECK: 0015:23-24 pattern; ENUM ALTER pahalı, CHECK esnek.
--
-- İndeks (S1 satır 64-65):
--   (user_id, project_id, created_at desc) — timeline list ana yol
--   (user_id, resolved_at) WHERE resolved_at IS NULL — "hâlâ açık" digest
--
-- RLS: owner-only (0015:47-58 pattern). LLM yok — saf SQL. Maliyet ≈ 0.
--
-- Tarih: 2026-05-10 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations, auth.users), 0015 (public.projects)
--
-- Apply (notebook DIŞINDA — K-029 dersi: Dashboard SQL Editor silent fail):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0029_project_event.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. project_event — sayfa-bazlı kullanıcı eylem zaman çizgisi
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.project_event (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  user_id      uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  page_slug    text NOT NULL CHECK (char_length(page_slug) BETWEEN 1 AND 100),
  paper_id     text,
  event_type   text NOT NULL
               CHECK (event_type IN ('kayit','danismana_sor','kutuphane_ekle','not')),
  payload      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now(),
  resolved_at  timestamptz
);

-- Timeline listeleme indeksi: GET /api/diary/timeline ana yol
CREATE INDEX idx_project_event_user_project_created
  ON public.project_event (user_id, project_id, created_at DESC);

-- "Hâlâ açık" digest indeksi: haftalık notification + aylık mail cron'u kullanır
CREATE INDEX idx_project_event_user_unresolved
  ON public.project_event (user_id, created_at)
  WHERE resolved_at IS NULL;

-- ============================================================================
-- 2. RLS — owner-only (0015 pattern)
-- ============================================================================
ALTER TABLE public.project_event ENABLE ROW LEVEL SECURITY;

CREATE POLICY project_event_owner_select ON public.project_event FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY project_event_owner_insert ON public.project_event FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY project_event_owner_update ON public.project_event FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY project_event_owner_delete ON public.project_event FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================================
-- 3. Comments
-- ============================================================================
COMMENT ON TABLE public.project_event IS
  'S1 Araştırma Defteri: sayfa-bazlı kullanıcı eylem zaman çizgisi. Her sayfadan "Ajandama Kaydet / Danışmana Sor / Kütüphaneme Ekle" event üretir. Owner-only RLS.';

COMMENT ON COLUMN public.project_event.page_slug IS
  'Olayın çıktığı sayfa slug''ı: "5.1_yayin_formati", "4.2_bosluk_profili", "S1_arastirma_defteri", ...';

COMMENT ON COLUMN public.project_event.paper_id IS
  'OpenAlex / havuz paper kimliği. Olay paper-bağlamlı değilse NULL.';

COMMENT ON COLUMN public.project_event.event_type IS
  'kayit | danismana_sor | kutuphane_ekle | not. CHECK ile sınırlanır; ENUM tercih edilmedi (ALTER pahalı).';

COMMENT ON COLUMN public.project_event.payload IS
  'Not metni, etiketler, persona, sayfa snapshot anahtarları. Şema değişimine geri-uyumlu.';

COMMENT ON COLUMN public.project_event.resolved_at IS
  '"Hâlâ açık" digest için; NULL = açık. 21+ gün açık olaylar haftalık notification cron tarafından tespit edilir.';

-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0029_project_event',
  'F13-S1 Araştırma Defteri: project_event (sayfa-bazlı eylem zaman çizgisi). 4 event_type CHECK, 2 indeks (timeline + unresolved), RLS owner-only.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
