-- =====================================================================
-- PaperMind v4 — Supabase Migration 0022: extended affinity tables
-- =====================================================================
-- Plan kaynağı: Page_Design/Sayfa_Plani_v2/3.3_yontem_matrisi.rtf
--   "Lift overlay AYIRT EDİCİ DOKUNUŞ" — 3.3 sayfasında 6 dropdown
--   kombinasyonun (Metod/Tema/Alan/Kavram × transpose) hepsinde lift
--   overlay aktif olabilsin diye 3 yeni türetilmiş affinity tablosu.
--
-- Önceki affinity tablolar (Migration 0007):
--   fact_method_topic_affinity   65,061 satır   (metod × theme)
--   fact_method_field_affinity      390 satır   (metod × field)
--
-- Bu migration eklenir (3.3 felsefe notu, kanıt seviyesi A):
--   fact_theme_field_affinity     ~19 × 4516 → eskiden başına Faz3 hesap
--   fact_theme_keyword_affinity  4516 × 1000 ≈ 4.5M satır (top-1000 keyword)
--   fact_field_keyword_affinity    19 × 1000 ≈ 19K satır
--
-- Pattern: 0007 ile birebir aynı (joint count + marginal + lift formülü).
-- Offline notebook: N18-benzeri (henüz yazılmadı — F13-S12-data faz).
--
-- İndeks paterni: PK + tek lookup index (sol kolon) + lift DESC partial.
-- (0007 pattern: idx_<ad>_<sol_kolon>, idx_<ad>_<sağ_kolon>, idx_<ad>_lift.)
--
-- RLS: read-all authenticated; service_role write.
--
-- Tarih: 2026-05-11 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations), 0002 (theme/field domain), 0007 (paterni miras)
--
-- Apply (notebook DIŞINDA — K-029 dersi: Dashboard SQL Editor silent fail):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0022_extended_affinity.sql
--
-- DB_URL: Session Pooler :5432 (transaction :6543 ISP blok).
--
-- Risk R4 (F13 plan §6): EXPLAIN ANALYZE benchmark — 4.5M satır
--   fact_theme_keyword_affinity insert kalitesi notebook'ta ölçülür;
--   >10s ise V2'ye ertelenir. Schema DDL bu commit'te; veri offline.
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. fact_theme_field_affinity — theme_id × primary_field
-- ============================================================================
-- 3.3 sayfa kullanımı: Tema×Alan heatmap'te lift overlay rakam.
--   Felsefe (RTF satır 23): "alanın geneline göre dengeli/sapkın" iddiası
--   savunmada rakamla destekli; klasik araç bunu vermez.
-- Pattern: fact_method_topic_affinity (0007) ile birebir aynı kolon seti.
CREATE TABLE IF NOT EXISTS public.fact_theme_field_affinity (
  theme_id           text NOT NULL,
  primary_field      text NOT NULL,
  n_papers           integer NOT NULL DEFAULT 0,
  mean_centrality    double precision,
  mean_q_weak        double precision,
  lift               double precision,
  PRIMARY KEY (theme_id, primary_field)
);

CREATE INDEX IF NOT EXISTS idx_tfa_theme  ON public.fact_theme_field_affinity(theme_id);
CREATE INDEX IF NOT EXISTS idx_tfa_field  ON public.fact_theme_field_affinity(primary_field);
CREATE INDEX IF NOT EXISTS idx_tfa_lift   ON public.fact_theme_field_affinity(lift DESC) WHERE lift IS NOT NULL;

ALTER TABLE public.fact_theme_field_affinity ENABLE ROW LEVEL SECURITY;

CREATE POLICY tfa_read_all ON public.fact_theme_field_affinity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY tfa_write_service ON public.fact_theme_field_affinity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.fact_theme_field_affinity IS
  '3.3 yöntem matrisi: theme × field lift overlay. ~19 × 4516 ≈ 86K satır. Offline hesap pattern fact_method_topic_affinity (0007) ile aynı (joint/marginal/lift).';

COMMENT ON COLUMN public.fact_theme_field_affinity.lift IS
  '3.3: P(theme,field) / (P(theme)·P(field)). Heatmap hücresine "+%Y" rakam.';


-- ============================================================================
-- 2. fact_theme_keyword_affinity — theme_id × keyword (top-1000)
-- ============================================================================
-- 3.3 sayfa kullanımı: Tema×Kavram heatmap (keyword corpus genelinde top-1000
--   ile sınırlı — kabarıklık yönetimi, RTF satır 72).
--   Felsefe: kavram ekseni klasik araçta yok; ayırt edici imza.
-- Veri kaynağı: fact_paper_topic ⨝ fact_paper_id_card.keywords (jsonb expand).
CREATE TABLE IF NOT EXISTS public.fact_theme_keyword_affinity (
  theme_id           text NOT NULL,
  keyword            text NOT NULL,
  n_papers           integer NOT NULL DEFAULT 0,
  mean_q_weak        double precision,
  lift               double precision,
  PRIMARY KEY (theme_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_tka_theme    ON public.fact_theme_keyword_affinity(theme_id);
CREATE INDEX IF NOT EXISTS idx_tka_keyword  ON public.fact_theme_keyword_affinity(keyword);
CREATE INDEX IF NOT EXISTS idx_tka_lift     ON public.fact_theme_keyword_affinity(lift DESC) WHERE lift IS NOT NULL;

ALTER TABLE public.fact_theme_keyword_affinity ENABLE ROW LEVEL SECURITY;

CREATE POLICY tka_read_all ON public.fact_theme_keyword_affinity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY tka_write_service ON public.fact_theme_keyword_affinity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.fact_theme_keyword_affinity IS
  '3.3 yöntem matrisi: theme × keyword (top-1000) lift overlay. ~4516 × 1000 ≈ 4.5M satır. EXPLAIN ANALYZE bench notebook''ta (F13 R4).';


-- ============================================================================
-- 3. fact_field_keyword_affinity — primary_field × keyword (top-1000)
-- ============================================================================
-- 3.3 sayfa kullanımı: Alan×Kavram heatmap lift overlay.
-- Veri kaynağı: fact_paper_field ⨝ fact_paper_id_card.keywords (jsonb expand).
CREATE TABLE IF NOT EXISTS public.fact_field_keyword_affinity (
  primary_field      text NOT NULL,
  keyword            text NOT NULL,
  n_papers           integer NOT NULL DEFAULT 0,
  mean_q_weak        double precision,
  lift               double precision,
  PRIMARY KEY (primary_field, keyword)
);

CREATE INDEX IF NOT EXISTS idx_fka_field    ON public.fact_field_keyword_affinity(primary_field);
CREATE INDEX IF NOT EXISTS idx_fka_keyword  ON public.fact_field_keyword_affinity(keyword);
CREATE INDEX IF NOT EXISTS idx_fka_lift     ON public.fact_field_keyword_affinity(lift DESC) WHERE lift IS NOT NULL;

ALTER TABLE public.fact_field_keyword_affinity ENABLE ROW LEVEL SECURITY;

CREATE POLICY fka_read_all ON public.fact_field_keyword_affinity
  FOR SELECT TO authenticated USING (true);
CREATE POLICY fka_write_service ON public.fact_field_keyword_affinity
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMENT ON TABLE public.fact_field_keyword_affinity IS
  '3.3 yöntem matrisi: field × keyword (top-1000) lift overlay. ~19 × 1000 ≈ 19K satır.';


-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0022_extended_affinity',
  '3.3 yöntem matrisi lift overlay: 3 yeni affinity tablo (theme×field, theme×keyword, field×keyword). 0007 pattern. Veri offline notebook (F13-S12-data faz).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
