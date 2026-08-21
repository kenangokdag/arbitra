-- =====================================================================
-- PaperMind v4 — Supabase Migration 0034:
-- waitlist.status: pilot allowlist gate (V1-S18-P013)
-- =====================================================================
-- Plan referansı : docs/plans/MVP_TOMORROW_EXECUTION_PLAN.md §B3
-- Tarih          : 2026-05-14
-- Postgres       : 17.6
-- Bağımlılık     : 0017_waitlist_table.sql
-- Apply mode     : MANUEL (Omer Supabase Dashboard'da paste edecek)
-- =====================================================================
-- Amaç: MVP pilot fazda (Omer + 3 davetli = 4 kullanıcı) sadece
-- waitlist.status='invited' veya 'active' olan e-postaların auth
-- middleware'den geçmesi.
--
-- Durum makinesi:
--   pending  → kayıt oldu, davet bekliyor (default)
--   invited  → Omer e-postaya davet attı, signup hakkı var
--   active   → ilk başarılı login sonrası middleware atar
--   declined → kullanıcı katılmak istemiyor (manuel veya frontend opt-out)
-- =====================================================================

BEGIN;

ALTER TABLE public.waitlist
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'invited', 'active', 'declined'));

CREATE INDEX IF NOT EXISTS waitlist_status_idx
  ON public.waitlist (status);

COMMENT ON COLUMN public.waitlist.status IS
  'V1-S18-P013 pilot allowlist gate: pending | invited | active | declined. '
  'Auth middleware (api/middleware/auth.py) status ∈ {invited, active} aksi 403.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0034_waitlist_invite_status',
  'V1-S18-P013: waitlist.status ENUM pilot allowlist gate. '
  'Auth middleware status ∈ {invited, active} kontrolü ile pilot e-postaları sınırlar.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
