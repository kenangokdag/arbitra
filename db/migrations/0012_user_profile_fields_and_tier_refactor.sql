-- =====================================================================
-- PaperMind v4 — Supabase Migration 0012:
-- user_profile_fields bridge + tier enum 4→3 + drop language_pref/field_primary
-- =====================================================================
-- Plan referansı : docs/plans/F5_S1_user_profile_bridge_tier_enum.md §7
-- Brain referansı: K-008 (bridge), K-013 (tier 3), K-015 (zorunlu form),
--                  K-017 (language_pref drop), K-019 (field 1-3),
--                  K-011 (DB tek dil EN, ileri yönlü), K-010 (sistem iç dili EN)
-- DM_RULES       : R7 (atomic) · R10 (RLS) · R4 (zero-hallucination)
-- Tarih          : 2026-05-03  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Postgres       : 17.6        ·  RLS: zorunlu (DM_RULES R10)
-- Bağımlılık     : 0011_create_dim_field (FK target: dim_field.field_id)
-- =====================================================================

BEGIN;

-- =====================================================================
-- 1. Bridge tablo: user_profile_fields
--    Kullanıcı 1-3 alan seçer (K-008/K-019); composite PK = (user_id, field_id)
--    aynı alanı iki kez seçilmesini engeller. position = UI tıklama sırası.
-- =====================================================================
CREATE TABLE public.user_profile_fields (
  user_id     uuid     NOT NULL REFERENCES auth.users(id)             ON DELETE CASCADE,
  field_id    text     NOT NULL REFERENCES public.dim_field(field_id) ON DELETE RESTRICT,
  position    smallint NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, field_id),
  CHECK (position BETWEEN 1 AND 3)
);

CREATE INDEX user_profile_fields_user_idx
  ON public.user_profile_fields(user_id);
CREATE INDEX user_profile_fields_field_idx
  ON public.user_profile_fields(field_id);

-- Defense-in-depth: max 3 alan/kullanıcı (frontend Zod atlanırsa DB korur)
CREATE OR REPLACE FUNCTION public.check_user_field_count() RETURNS trigger AS $$
BEGIN
  IF (SELECT count(*) FROM public.user_profile_fields WHERE user_id = NEW.user_id) > 3 THEN
    RAISE EXCEPTION 'user_profile_fields: maksimum 3 alan/kullanıcı (K-019/K-008)';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER user_profile_fields_max_3
  AFTER INSERT OR UPDATE ON public.user_profile_fields
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.check_user_field_count();

-- =====================================================================
-- 2. RLS politikaları (DM_RULES R10)
--    Self read/insert/delete; UPDATE policy YOK (kullanıcı DELETE+INSERT ile sıralar).
-- =====================================================================
ALTER TABLE public.user_profile_fields ENABLE ROW LEVEL SECURITY;

CREATE POLICY upf_self_read   ON public.user_profile_fields
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY upf_self_insert ON public.user_profile_fields
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY upf_self_delete ON public.user_profile_fields
  FOR DELETE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY upf_service_all ON public.user_profile_fields
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 3. Tier enum 4 → 3 (K-013)
--    Pre-launch (0 user); 'takim' UPDATE adımı YOK; sanity guard ile koru.
--    Postgres value-drop transactional olmadığı için 4-adım swap idiomu.
-- =====================================================================

-- 3.1 Yeni enum (3-değer; TR korunur — K-011 ileri yönlü, S16'da EN'e taşınacak)
CREATE TYPE public.user_tier_v2 AS ENUM ('ogrenci', 'arastirmaci', 'profesyonel');

-- 3.2 Sanity (pre-launch garanti) — beklenen 0; varsayım kırılırsa migration patlar
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.user_profiles WHERE tier::text = 'takim') THEN
    RAISE EXCEPTION 'F5-S1A FAIL: tier=takim satır var; "0 user" varsayımı geçersiz, plan revize gerek';
  END IF;
END $$;

-- 3.3 Kolon tipini değiştir
ALTER TABLE public.user_profiles
  ALTER COLUMN tier DROP DEFAULT,
  ALTER COLUMN tier TYPE public.user_tier_v2 USING tier::text::public.user_tier_v2,
  ALTER COLUMN tier SET DEFAULT 'ogrenci';

-- 3.4 Eski enum drop + yeni'yi rename
DROP TYPE public.user_tier;
ALTER TYPE public.user_tier_v2 RENAME TO user_tier;

-- =====================================================================
-- 4. user_profiles: language_pref + field_primary DROP
--    K-017: UI dili browser/locale; DB'de tutulmaz.
--    K-008: field_primary bridge'e taşındı; pre-launch 0 user (backfill yok).
-- =====================================================================
ALTER TABLE public.user_profiles
  DROP COLUMN language_pref,
  DROP COLUMN field_primary;

-- =====================================================================
-- 5. Versiyon kaydı
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0012_user_profile_fields_and_tier_refactor',
  'K-008/K-013/K-015/K-017 — user_profile_fields bridge + tier 3 + lang/field_primary drop'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
