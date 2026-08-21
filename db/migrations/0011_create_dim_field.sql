-- =====================================================================
-- PaperMind v4 — Supabase Migration 0011: dim_field (taksonomi)
-- =====================================================================
-- Plan referansı : docs/plans/F5_S0_dim_field_taxonomy.md §B
-- Brain referansı: K-007 (dim_field kurulumu), K-010 (sistem iç dili EN),
--                  K-011 (DB tek dil EN, ileri yönlü — yeni tablo, name_en yalnız),
--                  K-019 (granularity = OpenAlex level-1, ~26 satır)
-- DM_RULES       : R4 (zero-hallucination) · R7 (atomic commit) · R10 (RLS)
-- Tarih          : 2026-05-03  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Postgres       : 17.6        ·  RLS: zorunlu (DM_RULES R10)
-- =====================================================================

-- =====================================================================
-- 1. dim_field — onboarding alan dropdown'u için kanonik taksonomi
--    Kaynak: warehouse fact_paper_field.parquet (N04D, OpenAlex level-1)
--    Seed   : api/scripts/seed_dim_field.py (idempotent upsert, on field_id)
-- =====================================================================
CREATE TABLE public.dim_field (
  field_id            text PRIMARY KEY,                       -- türev id, underscore (örn: "computer_science")
  name_en             text NOT NULL UNIQUE,                   -- K-010/K-011: kanonik EN ad (örn: "Computer Science")
  slug                text NOT NULL UNIQUE,                   -- URL-safe, dash (örn: "computer-science"); UI dropdown value
  paper_count_total   integer NOT NULL DEFAULT 0,             -- warehouse'tan upsert sırasında güncellenir
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX dim_field_slug_idx
  ON public.dim_field(slug);
CREATE INDEX dim_field_paper_count_idx
  ON public.dim_field(paper_count_total DESC);

CREATE TRIGGER trg_dim_field_updated_at BEFORE UPDATE ON public.dim_field
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =====================================================================
-- 2. RLS — read herkese açık (auth gerektirir), write yalnız service_role
-- =====================================================================
ALTER TABLE public.dim_field ENABLE ROW LEVEL SECURITY;

CREATE POLICY dim_field_read_authenticated ON public.dim_field
  FOR SELECT TO authenticated USING (true);

CREATE POLICY dim_field_write_service ON public.dim_field
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş — versiyon tablo
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0011_create_dim_field',
  'K-007/K-010/K-011/K-019 — dim_field taksonomi (OpenAlex level-1, EN-only, ~26 satır)'
)
ON CONFLICT (version) DO NOTHING;
