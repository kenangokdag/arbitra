-- =====================================================================
-- PaperMind v4 — Supabase Migration 0023: gap matrix calibration + temporal
-- =====================================================================
-- Plan kaynağı: Page_Design/Sayfa_Plani_v2/4.1_bosluk_haritasi.rtf
--   "CANLI SUPABASE BULGUSU (2026-05-10)":
--     M1, M7, M8 ✓ hesaplı (504,436 satır)
--     M2-M6 ✗ hesaplanmamış (keyword ekseni dahil)
--     publishability = 0.5 sabit (kalibrasyon eksik)
--     matrix_confidence_calibrated = NULL (Aşama 3 LightGBM pending)
--   Karar (Omer onayı, 2026-05-10): HEPSİ V1'E ALINACAK
--
-- Bu migration NE YAPAR:
--   (a) fact_gap_matrix CHECK constraint genişletir: M1/M7/M8 → M1..M8
--       (M2 Konu×Kavram, M3 Metod×Kavram, M4 Alan×Kavram, M5 Alan×Konu,
--        M6 Alan×Metod) — RTF §Plan Detayı (1).
--   (b) fact_gap_matrix_temporal yeni tablo — yıl boyutu için ayrı tablo
--       (ana fact_gap_matrix overload olmasın, RTF satır 65).
--
-- Bu migration NE YAPMAZ:
--   - publishability backfill (offline kalibrasyon notebook; RTF Plan Detayı 3)
--   - matrix_confidence_calibrated backfill (LightGBM offline)
--   - M2-M6 satır insert (offline notebook; pattern M1 ile aynı)
--
-- Pattern: fact_gap_matrix kolon seti aynen korunur (axis_x/axis_y/depth/
--   neighbor/E/feasibility/gap_value/publishability/confidence_prior/calibrated).
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0002 (fact_gap_matrix tablosu)
--
-- Apply (notebook DIŞINDA — K-029):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0023_gap_matrix_calibration.sql
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. fact_gap_matrix CHECK constraint genişlet — M1/M7/M8 → M1..M8
-- ============================================================================
-- 0002 satır 95: CHECK (matrix_id IN ('M1','M7','M8')).
-- Constraint adı convention: <tablo>_<kolon>_check (Postgres default).
-- Ayrıca 4.1 RTF §Plan Detayı (1):
--   M2 = Konu × Kavram    (axis_x=theme_id, axis_y=keyword)
--   M3 = Metod × Kavram   (axis_x=metod_id, axis_y=keyword)
--   M4 = Alan × Kavram    (axis_x=primary_field, axis_y=keyword)
--   M5 = Alan × Konu      (axis_x=primary_field, axis_y=theme_id)
--   M6 = Alan × Metod     (axis_x=primary_field, axis_y=metod_id)

ALTER TABLE public.fact_gap_matrix
  DROP CONSTRAINT IF EXISTS fact_gap_matrix_matrix_id_check;

ALTER TABLE public.fact_gap_matrix
  ADD CONSTRAINT fact_gap_matrix_matrix_id_check
  CHECK (matrix_id IN ('M1','M2','M3','M4','M5','M6','M7','M8'));

COMMENT ON COLUMN public.fact_gap_matrix.matrix_id IS
  '4.1 bosluk haritası matrix tipi: M1 Tema×Metod, M2 Konu×Kavram, M3 Metod×Kavram, M4 Alan×Kavram, M5 Alan×Konu, M6 Alan×Metod, M7 Tema×Cümle-rolü, M8 Tema×Tema. M2-M6 veri offline notebook (0023 pending).';


-- ============================================================================
-- 2. fact_gap_matrix_temporal — yıl-bazlı gap_value alt-küme
-- ============================================================================
-- 4.1 sayfa kullanımı: üst slider "yıl filtresi" temporal matris üzerinde aktif.
--   "Yeni boşluk mu, terk edilmiş alan mı?" cevabı.
-- Kolon seti: ana fact_gap_matrix subset + year (kabarık değil; matrix_id +
--   ekseninde paper'lar yıl alt-kümesine bölündüğünde küçük gap_value alt-küme).
-- Tahmini boyut (RTF Plan Detayı (2)): son 10-15 yıl × 5 matris × ortalama
--   ~5K hücre/yıl ≈ 250-375K satır.

CREATE TABLE IF NOT EXISTS public.fact_gap_matrix_temporal (
  matrix_id          text NOT NULL,
  axis_x             text NOT NULL,
  axis_y             text NOT NULL,
  year               smallint NOT NULL CHECK (year BETWEEN 1900 AND 2100),
  depth              integer NOT NULL DEFAULT 0 CHECK (depth >= 0),
  gap_value          double precision NOT NULL,
  PRIMARY KEY (matrix_id, axis_x, axis_y, year),
  CHECK (matrix_id IN ('M1','M2','M3','M4','M5','M6','M7','M8'))
);

CREATE INDEX IF NOT EXISTS idx_gap_temporal_matrix
  ON public.fact_gap_matrix_temporal (matrix_id);
CREATE INDEX IF NOT EXISTS idx_gap_temporal_pair_year
  ON public.fact_gap_matrix_temporal (matrix_id, axis_x, axis_y, year);
CREATE INDEX IF NOT EXISTS idx_gap_temporal_year
  ON public.fact_gap_matrix_temporal (year);
CREATE INDEX IF NOT EXISTS idx_gap_temporal_value
  ON public.fact_gap_matrix_temporal (matrix_id, year, gap_value DESC);

ALTER TABLE public.fact_gap_matrix_temporal ENABLE ROW LEVEL SECURITY;

CREATE POLICY gap_temporal_read_all ON public.fact_gap_matrix_temporal
  FOR SELECT TO authenticated USING (true);
CREATE POLICY gap_temporal_write_service ON public.fact_gap_matrix_temporal
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.fact_gap_matrix_temporal IS
  '4.1 bosluk haritası yıl ekseni: matrix_id × axis × year → gap_value. UI yıl slider için. Tahmini ~250-375K satır (son 10-15 yıl × 5 matris). Veri offline notebook.';

COMMENT ON COLUMN public.fact_gap_matrix_temporal.gap_value IS
  'Yıl-bazlı gap_value (M1 formülü ile aynı: 0.25(1-depth_norm)+0.20·neighbor+0.20·E+0.15·feasibility+0.20·publishability — yıl alt-kümesinde hesaplı).';


-- ============================================================================
-- 3. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0023_gap_matrix_calibration',
  '4.1 bosluk haritası: fact_gap_matrix CHECK genişledi (M2-M6 eklendi) + fact_gap_matrix_temporal yeni tablo (yıl ekseni). Veri + kalibrasyon (publishability/confidence_calibrated) offline notebook.'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
