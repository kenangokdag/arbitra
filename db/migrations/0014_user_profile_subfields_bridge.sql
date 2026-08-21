-- =====================================================================
-- PaperMind v4 — Supabase Migration 0014: user_profile_subfields bridge
-- =====================================================================
-- Plan: docs/plans/F5_S1B_dim_subfield_bridge.md §7.2/§7.3 (composite, DM-8)
-- Brain: K-008/K-019 ext · DM_RULES R7/R10
-- Tarih: 2026-05-03 · PG: 17.6
-- Bağımlılık: 0012 (user_profile_fields), 0013 (dim_subfield composite PK)
-- =====================================================================

-- 1. Bridge tablo — composite PK (user_id, subfield_id, field_id), composite FK
CREATE TABLE public.user_profile_subfields (
  user_id      uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subfield_id  text NOT NULL,
  field_id     text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, subfield_id, field_id),
  FOREIGN KEY (subfield_id, field_id)
    REFERENCES public.dim_subfield(subfield_id, field_id) ON DELETE RESTRICT
);

CREATE INDEX user_profile_subfields_user_idx           ON public.user_profile_subfields(user_id);
CREATE INDEX user_profile_subfields_subfield_field_idx ON public.user_profile_subfields(subfield_id, field_id);

-- 2. Cascade trigger — NEW.field_id ∈ user_profile_fields
--    (composite PK sayesinde bridge satırında field_id zaten var; dim_subfield lookup gereksiz)
CREATE OR REPLACE FUNCTION public.check_subfield_parent_field() RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.user_profile_fields f
    WHERE f.user_id = NEW.user_id AND f.field_id = NEW.field_id
  ) THEN
    RAISE EXCEPTION
      'user_profile_subfields: field_id=% kullanıcının seçili alanları arasında değil (subfield=%, K-019 ext)',
      NEW.field_id, NEW.subfield_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_profile_subfields_cascade_check
  AFTER INSERT OR UPDATE ON public.user_profile_subfields
  FOR EACH ROW EXECUTE FUNCTION public.check_subfield_parent_field();

-- 3. RLS — 4 policy (S1A ile aynı pattern)
ALTER TABLE public.user_profile_subfields ENABLE ROW LEVEL SECURITY;

CREATE POLICY ups_self_read   ON public.user_profile_subfields
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY ups_self_insert ON public.user_profile_subfields
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY ups_self_delete ON public.user_profile_subfields
  FOR DELETE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY ups_service_all ON public.user_profile_subfields
  FOR ALL TO service_role USING (true) WITH CHECK (true);

INSERT INTO public.schema_migrations (version, description)
VALUES ('0014_user_profile_subfields_bridge',
        'K-008/K-019 ext — user_profile_subfields composite PK + composite FK + cascade trigger (DM-8)')
ON CONFLICT (version) DO NOTHING;
