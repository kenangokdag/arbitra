-- =====================================================================
-- PaperMind v4 — Migration 0004: paper satellite facts (Faz 2)
-- =====================================================================
-- Karar: Warehouse ana gövde Faz 2 — paper-level satellite tablolar
--   (FK fact_paper_id_card.paper_id, ON DELETE CASCADE)
-- Önkoşul: Migration 0003 + Faz 1 upload tamam (24.87M PaperCard yüklü)
-- Schema kaynağı: ENVANTER.md §10.1 W-23 + W-26a + W-17
-- Aynalama prensibi: warehouse parquet kolon adları **aynen** Supabase'e
-- Tarih: 2026-04-30
-- Boyut: ~7 GB Postgres total (sentence_role ~2.5 + d_estra ~3.5 + ref_age ~1)
-- =====================================================================

-- =====================================================================
-- 19. fact_paper_sentence_role — 24,867,210 × 13 (W-23 / N11_W23)
-- ENVANTER §10.1: paper_id, n_sentences_total (Int16),
--   n_BACKGROUND/n_OBJECTIVE/n_METHOD/n_RESULT/n_CONCLUSION (Int16),
--   mean_conf_* (Float32 × 5),
--   dominant_role ∈ {BACKGROUND, OBJECTIVE, METHOD, RESULT, CONCLUSION, NONE}
-- Coverage: %99.981 (4,714 zero-sent → NONE)
-- =====================================================================
CREATE TABLE public.fact_paper_sentence_role (
  paper_id              text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  n_sentences_total     smallint NOT NULL DEFAULT 0,
  n_background          smallint NOT NULL DEFAULT 0,
  n_objective           smallint NOT NULL DEFAULT 0,
  n_method              smallint NOT NULL DEFAULT 0,
  n_result              smallint NOT NULL DEFAULT 0,
  n_conclusion          smallint NOT NULL DEFAULT 0,
  mean_conf_background  real,
  mean_conf_objective   real,
  mean_conf_method      real,
  mean_conf_result      real,
  mean_conf_conclusion  real,
  dominant_role         text NOT NULL,
  CHECK (dominant_role IN ('BACKGROUND','OBJECTIVE','METHOD','RESULT','CONCLUSION','NONE'))
);
CREATE INDEX idx_sent_role_dom ON public.fact_paper_sentence_role(dominant_role);
CREATE INDEX idx_sent_role_meth ON public.fact_paper_sentence_role(n_method DESC) WHERE n_method > 0;

ALTER TABLE public.fact_paper_sentence_role ENABLE ROW LEVEL SECURITY;
CREATE POLICY sent_role_read_all ON public.fact_paper_sentence_role
  FOR SELECT TO authenticated USING (true);
CREATE POLICY sent_role_write_service ON public.fact_paper_sentence_role
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 20. fact_paper_d_estra — 24,867,210 × 13 (W-26a / N14a)
-- ENVANTER §10.1: paper_id, TS_p ∈ [0,1], rising_signal ∈ [0,1],
--   R/R_low/R_high, E/E_low/E_high, d_scalar/d_scalar_low/d_scalar_high (∈ [0,1]),
--   gate_d_triggered (Bool)
-- d-ESTRA Plan 1 simplified: R = 0.30·wIR + 0.70·TS_p,
--                            E = 0.60·rising + 0.40·wD,
--                            d_scalar = 0.60·R + 0.40·E
-- =====================================================================
CREATE TABLE public.fact_paper_d_estra (
  paper_id            text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  ts_p                real,
  rising_signal       real,
  r                   real,
  r_low               real,
  r_high              real,
  e                   real,
  e_low               real,
  e_high              real,
  d_scalar            real,
  d_scalar_low        real,
  d_scalar_high       real,
  gate_d_triggered    boolean NOT NULL DEFAULT false
);
CREATE INDEX idx_d_estra_d ON public.fact_paper_d_estra(d_scalar DESC) WHERE d_scalar IS NOT NULL;
CREATE INDEX idx_d_estra_r ON public.fact_paper_d_estra(r DESC) WHERE r IS NOT NULL;
CREATE INDEX idx_d_estra_e ON public.fact_paper_d_estra(e DESC) WHERE e IS NOT NULL;
CREATE INDEX idx_d_estra_gate ON public.fact_paper_d_estra(gate_d_triggered) WHERE gate_d_triggered = true;

ALTER TABLE public.fact_paper_d_estra ENABLE ROW LEVEL SECURITY;
CREATE POLICY d_estra_read_all ON public.fact_paper_d_estra
  FOR SELECT TO authenticated USING (true);
CREATE POLICY d_estra_write_service ON public.fact_paper_d_estra
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 21. fact_paper_ref_age — 16,698,232 × 6 (W-17 / N09c HÜCRE 3)
-- ENVANTER §10.1: paper_id, mean_ref_age (Float64, year), std_ref_age,
--   median_ref_age, p_recent_5y ∈ [0,1], n_refs_inside (UInt32)
-- Coverage: %67.1 (24.87M corpus'tan; remainder atıfsız ya da ref'leri yıl bilgisi yok)
-- =====================================================================
CREATE TABLE public.fact_paper_ref_age (
  paper_id            text PRIMARY KEY
    REFERENCES public.fact_paper_id_card(paper_id) ON DELETE CASCADE,
  mean_ref_age        double precision,
  std_ref_age         double precision,
  median_ref_age      double precision,
  p_recent_5y         double precision,
  n_refs_inside       integer NOT NULL DEFAULT 0,
  CHECK (p_recent_5y IS NULL OR (p_recent_5y >= 0 AND p_recent_5y <= 1))
);
CREATE INDEX idx_ref_age_mean ON public.fact_paper_ref_age(mean_ref_age) WHERE mean_ref_age IS NOT NULL;
CREATE INDEX idx_ref_age_recent ON public.fact_paper_ref_age(p_recent_5y DESC) WHERE p_recent_5y IS NOT NULL;
CREATE INDEX idx_ref_age_n ON public.fact_paper_ref_age(n_refs_inside DESC);

ALTER TABLE public.fact_paper_ref_age ENABLE ROW LEVEL SECURITY;
CREATE POLICY ref_age_read_all ON public.fact_paper_ref_age
  FOR SELECT TO authenticated USING (true);
CREATE POLICY ref_age_write_service ON public.fact_paper_ref_age
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş
-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0004_paper_satellite_facts',
  'fact_paper_sentence_role (24.87M W-23) + fact_paper_d_estra (24.87M W-26a) + fact_paper_ref_age (16.70M W-17)'
)
ON CONFLICT (version) DO NOTHING;
