-- =====================================================================
-- 0033_fix_term_arm_temporal_pk — fact_term_arm_temporal schema fix
-- =====================================================================
-- 0021 plan-time'da fact_term_arm_temporal için year boyutu varsaydı
-- (PK = term_a, term_b, year). Gerçek parquet "term×term + recent vs prev
-- window" granülasyonunda (N17 sliding-window output: cnt_recent/cnt_prev,
-- support_recent/support_prev, lift_recent/lift_prev, delta_lift).
-- year kolonu üretilmiyor; NOT NULL constraint COPY FROM STDIN'i bloklar.
--
-- Bağımlılık taraması (2026-05-13, kanıt-A grep): fact_term_arm_temporal +
-- delta_lift kelimeleri kodbase'de FE/BE 0 sorgu — sadece notebook +
-- migration + plan RTF (4 dosya). Schema breaking change güvenli.
--
-- Patch:
--   1. PK'yı drop et (year içeriyor)
--   2. year kolonunu drop et
--   3. PK'yı yeniden kur: (term_a, term_b)
--
-- Tarih: 2026-05-13 · PG: 17.6
-- Bağımlılık: 0021_concept_term_arm
-- Apply: psql "$SUPABASE_DB_URL" -f db/migrations/0033_fix_term_arm_temporal_pk.sql
-- =====================================================================

BEGIN;

ALTER TABLE public.fact_term_arm_temporal
  DROP CONSTRAINT fact_term_arm_temporal_pkey;

ALTER TABLE public.fact_term_arm_temporal
  DROP COLUMN year;

ALTER TABLE public.fact_term_arm_temporal
  ADD PRIMARY KEY (term_a, term_b);

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0033_fix_term_arm_temporal_pk',
  '0021 plan-time year boyutu yanlıştı (parquet recent vs prev window). year DROP + PK (term_a,term_b).'
) ON CONFLICT (version) DO NOTHING;

COMMIT;
