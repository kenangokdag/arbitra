-- =====================================================================
-- PaperMind v4 — Supabase Migration 0013: dim_subfield (level-2 taksonomi)
-- =====================================================================
-- Plan: docs/plans/F5_S1B_dim_subfield_bridge.md §7.1 (composite PK, DM-7)
-- Brain: K-007 (taxonomy), K-010/K-011 (EN-only), K-019 ext (level-2 ~252)
-- DM_RULES: R4 (zero-hallucination) · R7 (atomic) · R10 (RLS)
-- Tarih: 2026-05-03 · PG: 17.6 · Region: eu-central-1
-- Bağımlılık: 0011_create_dim_field (parent FK)
-- Collision kanıtı: 252 distinct, 8 subfield_id 2 parent altında (composite PK zorunlu)
-- =====================================================================

CREATE TABLE public.dim_subfield (
  subfield_id         text NOT NULL,
  field_id            text NOT NULL REFERENCES public.dim_field(field_id) ON DELETE CASCADE,
  name_en             text NOT NULL,
  slug                text NOT NULL,
  paper_count_total   integer NOT NULL DEFAULT 0,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (subfield_id, field_id),
  UNIQUE (field_id, slug),
  UNIQUE (field_id, name_en)
);

CREATE INDEX dim_subfield_field_idx ON public.dim_subfield(field_id);
-- (field_id, slug) UNIQUE zaten slug index gibi davranır; composite PK leading subfield_id kapsar

CREATE TRIGGER trg_dim_subfield_updated_at BEFORE UPDATE ON public.dim_subfield
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.dim_subfield ENABLE ROW LEVEL SECURITY;

CREATE POLICY dim_subfield_read_authenticated ON public.dim_subfield
  FOR SELECT TO authenticated USING (true);

CREATE POLICY dim_subfield_write_service ON public.dim_subfield
  FOR ALL TO service_role USING (true) WITH CHECK (true);

INSERT INTO public.schema_migrations (version, description)
VALUES ('0013_create_dim_subfield',
        'K-007/K-019 ext — dim_subfield level-2 taxonomy 252 satır, composite PK (DM-7), EN-only')
ON CONFLICT (version) DO NOTHING;
