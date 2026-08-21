-- =====================================================================
-- PaperMind v4 — Migration 0043: Global app teması (admin düzenler)
-- =====================================================================
-- Plan: docs/worldclass/PLAN_REVIEW_COCKPIT.md FAZ 4A — "Global app teması".
--
-- Eklenen tablo:
--   app_theme_settings — TEK-SATIR global tema (CHECK id=1 ile tek satır zorlanır).
--                        Admin PATCH /api/app/theme ile günceller; herkes
--                        GET /api/app/theme ile okur (FE açılışta). Tema
--                        ayarlanana kadar GÖRSEL DEĞİŞMEZ → varsayılan satır
--                        web/src/styles/globals.css değerleriyle seed edilir.
--
-- Tarih: 2026-06-26 · PG: 17.x
-- Bağımlılık: 0001 (schema_migrations).
--
-- ROLLBACK / MITIGATION:
--   DROP TABLE IF EXISTS public.app_theme_settings;
--   (uygulama theme_service kod-varsayılanına düşer → görsel yine değişmez.)
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.app_theme_settings (
  -- Tek-satır zorlaması: id daima 1; ikinci satır INSERT'i CHECK reddeder.
  id           integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  accent_color text NOT NULL,
  bg_color     text NOT NULL,
  ink_color    text NOT NULL,
  font_sans    text NOT NULL,
  font_serif   text NOT NULL,
  updated_by   text,                       -- admin user_id/sub (künye)
  updated_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.app_theme_settings IS
  'Global app teması (tek satır, id=1). Admin PATCH /api/app/theme günceller; GET public. Seed = globals.css değerleri → ayarlanana kadar görsel değişmez.';

-- Varsayılan satır: mevcut globals.css değerleri (accent indigo-600, bg slate-50,
-- ink slate-900, font_sans inter, font_serif lora). Doğrulandı:
--   web/src/styles/globals.css:13 (#f8fafc), :21 (#0f172a), :31 (#4F46E5),
--   :47 (--font-inter), :48 (--font-lora).
INSERT INTO public.app_theme_settings
  (id, accent_color, bg_color, ink_color, font_sans, font_serif, updated_by)
VALUES
  (1, '#4F46E5', '#f8fafc', '#0f172a', 'inter', 'lora', NULL)
ON CONFLICT (id) DO NOTHING;

-- RLS: tema PUBLIC okunur (anon key dahil); yazma yalnız service-role (backend
-- admin endpoint). Hiçbir write policy yok → anon/authed RLS yazamaz.
ALTER TABLE public.app_theme_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_theme_public_select ON public.app_theme_settings;
CREATE POLICY app_theme_public_select ON public.app_theme_settings
  FOR SELECT USING (true);

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0043_app_theme_settings',
  'Global app teması (admin düzenler): app_theme_settings tek-satır tablo (CHECK id=1) + globals.css seed + public-read RLS. FAZ 4A.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
