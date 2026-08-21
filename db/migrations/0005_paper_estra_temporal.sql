-- =====================================================================
-- PaperMind v4 — Migration 0005: paper ESTRA + temporal facts (Faz 3)
-- =====================================================================
-- Karar: B-013 PASS sonrası warehouse Faz 3 mirror — ESTRA çekirdek +
--   temporal sinyal tabloları (CD₅ disruption + Sleeping Beauty)
-- Önkoşul: Migration 0004 + Faz 2 satellite upload tamam (B-013 PASS)
-- Schema kaynağı: ENVANTER.md §5 W-31 + W-33 + W-29 + W-20 + W-21
-- Aynalama prensibi: warehouse parquet kolon adları lowercase Postgres'e
-- Tarih: 2026-05-01
-- Boyut tahmini: ~3.5 GB Postgres (quality 0.3 + w_estra 1.5 + velocity 0.4
--   + disruption 1 + beauty 0.3) + indeks overhead
-- =====================================================================

-- =====================================================================
-- 22. fact_paper_quality_v3 — 24,867,210 × 6 (W-31 / N08v3)
-- ENVANTER §5: paper_id, q_weak (Float32 [0,1] Snorkel posterior),
--   q_weak_low/high (Float32 z90 CI), n_lfs_active (Int8 0-8),
--   q_weak_v2 (Float32 backup)
-- =====================================================================
CREATE TABLE public.fact_paper_quality_v3 (
  paper_id        text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  q_weak          real,
  q_weak_low      real,
  q_weak_high     real,
  n_lfs_active    smallint NOT NULL DEFAULT 0,
  q_weak_v2       real,
  CHECK (q_weak IS NULL OR (q_weak >= 0 AND q_weak <= 1)),
  CHECK (n_lfs_active >= 0 AND n_lfs_active <= 11)
);
CREATE INDEX idx_quality_v3_q     ON public.fact_paper_quality_v3(q_weak DESC) WHERE q_weak IS NOT NULL;
CREATE INDEX idx_quality_v3_n_lfs ON public.fact_paper_quality_v3(n_lfs_active DESC);

ALTER TABLE public.fact_paper_quality_v3 ENABLE ROW LEVEL SECURITY;
CREATE POLICY quality_v3_read_all ON public.fact_paper_quality_v3
  FOR SELECT TO authenticated USING (true);
CREATE POLICY quality_v3_write_service ON public.fact_paper_quality_v3
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 23. fact_paper_w_estra — 24,867,210 × 15 (W-33 / N20)
-- ENVANTER §5: w_ESTRA = 0.40·wIR + 0.30·wTS + 0.30·wD (placeholder ağırlıklar);
--   her metric için low/high CI band (delta method z=1.6449);
--   n_themes (Int8), gate_w_triggered (Bool, Plan 1'de hep false)
-- =====================================================================
CREATE TABLE public.fact_paper_w_estra (
  paper_id           text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  w_estra            real,
  w_estra_low        real,
  w_estra_high       real,
  wir                real,
  wir_low            real,
  wir_high           real,
  wts                real,
  wts_low            real,
  wts_high           real,
  wd                 real,
  wd_low             real,
  wd_high            real,
  n_themes           smallint NOT NULL DEFAULT 0,
  gate_w_triggered   boolean  NOT NULL DEFAULT false,
  CHECK (w_estra IS NULL OR (w_estra >= 0 AND w_estra <= 1))
);
CREATE INDEX idx_w_estra_w        ON public.fact_paper_w_estra(w_estra DESC) WHERE w_estra IS NOT NULL;
CREATE INDEX idx_w_estra_wir      ON public.fact_paper_w_estra(wir DESC)     WHERE wir     IS NOT NULL;
CREATE INDEX idx_w_estra_wts      ON public.fact_paper_w_estra(wts DESC)     WHERE wts     IS NOT NULL;
CREATE INDEX idx_w_estra_gate     ON public.fact_paper_w_estra(gate_w_triggered) WHERE gate_w_triggered = true;

ALTER TABLE public.fact_paper_w_estra ENABLE ROW LEVEL SECURITY;
CREATE POLICY w_estra_read_all ON public.fact_paper_w_estra
  FOR SELECT TO authenticated USING (true);
CREATE POLICY w_estra_write_service ON public.fact_paper_w_estra
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 24. fact_paper_velocity — 24,867,210 × 5 (W-29 / N04E)
-- ENVANTER §5: velocity (cited/age), velocity_pct_in_field_year [0,1] strata
--   percentile, age_adjusted_impact (Float32 NULL when fwci null),
--   is_too_new (Bool)
-- =====================================================================
CREATE TABLE public.fact_paper_velocity (
  paper_id                       text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  velocity                       real,
  velocity_pct_in_field_year     real,
  age_adjusted_impact            real,
  is_too_new                     boolean NOT NULL DEFAULT false,
  CHECK (velocity_pct_in_field_year IS NULL OR
         (velocity_pct_in_field_year >= 0 AND velocity_pct_in_field_year <= 1))
);
CREATE INDEX idx_velocity_pct    ON public.fact_paper_velocity(velocity_pct_in_field_year DESC) WHERE velocity_pct_in_field_year IS NOT NULL;
CREATE INDEX idx_velocity_age    ON public.fact_paper_velocity(age_adjusted_impact DESC)        WHERE age_adjusted_impact        IS NOT NULL;
CREATE INDEX idx_velocity_new    ON public.fact_paper_velocity(is_too_new) WHERE is_too_new = true;

ALTER TABLE public.fact_paper_velocity ENABLE ROW LEVEL SECURITY;
CREATE POLICY velocity_read_all ON public.fact_paper_velocity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY velocity_write_service ON public.fact_paper_velocity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 25. fact_paper_disruption — 24,867,210 × 8 (W-20 / N09e v7.2 cd_5.parquet)
-- ENVANTER §5: Funk & Owen-Smith 2017 PNAS CD₅
--   cd_5 = (n_a − n_i) / (n_a + n_i + n_j) ∈ [−1, 1]
--   cd_undefined = pub_year > 2020 OR total_window_papers = 0 OR pub_year IS NULL
-- Defined: 10.05M (%40.40); Undefined: 14.82M (%59.60)
-- =====================================================================
CREATE TABLE public.fact_paper_disruption (
  paper_id                text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  pub_year                integer,
  n_a                     bigint NOT NULL DEFAULT 0,
  n_i                     bigint NOT NULL DEFAULT 0,
  n_j                     bigint NOT NULL DEFAULT 0,
  total_window_papers     bigint NOT NULL DEFAULT 0,
  cd_5                    double precision,
  cd_undefined            boolean NOT NULL DEFAULT false,
  CHECK (cd_5 IS NULL OR (cd_5 >= -1 AND cd_5 <= 1))
);
CREATE INDEX idx_disruption_cd5     ON public.fact_paper_disruption(cd_5 DESC) WHERE cd_undefined = false;
CREATE INDEX idx_disruption_year    ON public.fact_paper_disruption(pub_year)  WHERE pub_year     IS NOT NULL;
CREATE INDEX idx_disruption_defined ON public.fact_paper_disruption(cd_undefined);

ALTER TABLE public.fact_paper_disruption ENABLE ROW LEVEL SECURITY;
CREATE POLICY disruption_read_all ON public.fact_paper_disruption
  FOR SELECT TO authenticated USING (true);
CREATE POLICY disruption_write_service ON public.fact_paper_disruption
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 26. fact_paper_beauty — 24,867,210 × 10 (W-21 / N09d sleeping beauty)
-- ENVANTER §5: Ke et al. PNAS 2015 sleeping beauty coefficient
--   B = Σ ((c_max−c_0)·t/t_m + c_0 − c_t) / max(1, c_t)
--   t_a = argmax(line_t − c_t) over [0, t_m]
--   year_obs_max = -1 sentinel (atıfsız paperlar için)
--   b_undefined = (year_obs_max < 5)
-- B mean=0.864 median=0 std=224.95 (heavy-tail Ke 2015 uyumlu)
-- =====================================================================
CREATE TABLE public.fact_paper_beauty (
  paper_id           text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  pub_year           integer,
  c_max              bigint NOT NULL DEFAULT 0,
  t_m                integer,
  t_a                integer,
  c_0                bigint NOT NULL DEFAULT 0,
  total_cites        bigint NOT NULL DEFAULT 0,
  year_obs_max       integer,
  b                  double precision,
  b_undefined        boolean NOT NULL DEFAULT false
);
CREATE INDEX idx_beauty_b      ON public.fact_paper_beauty(b DESC) WHERE b_undefined = false;
CREATE INDEX idx_beauty_t_a    ON public.fact_paper_beauty(t_a)    WHERE t_a IS NOT NULL;
CREATE INDEX idx_beauty_undef  ON public.fact_paper_beauty(b_undefined);

ALTER TABLE public.fact_paper_beauty ENABLE ROW LEVEL SECURITY;
CREATE POLICY beauty_read_all ON public.fact_paper_beauty
  FOR SELECT TO authenticated USING (true);
CREATE POLICY beauty_write_service ON public.fact_paper_beauty
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0005_paper_estra_temporal',
  'fact_paper_quality_v3 (24.87M W-31) + fact_paper_w_estra (24.87M W-33) + fact_paper_velocity (24.87M W-29) + fact_paper_disruption (24.87M W-20) + fact_paper_beauty (24.87M W-21)'
)
ON CONFLICT (version) DO NOTHING;
