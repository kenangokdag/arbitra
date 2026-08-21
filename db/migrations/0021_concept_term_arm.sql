-- =====================================================================
-- PaperMind v4 — Supabase Migration 0021: concept term ARM tables
-- =====================================================================
-- Plan kaynağı: Page_Design/Sayfa_Plani_v2/2.5_kavram_agi.rtf
--   "KRİTİK ALTYAPI BULGUSU (2026-05-10, kanıt A)" — 3 parquet Drive'da
--   hesaplı, Supabase'de YOK; sayfa canlıya bağlanamaz, taşıma şart.
--   Karar (Omer onayı, 2026-05-10): A yolu — taşıma yapılacak.
--
-- Veri kaynağı (ENVANTER.md kanıt A):
--   ~/Dataleak/facts/fact_term_arm_static.parquet     297,855 satır × 20 col
--   ~/Dataleak/facts/fact_term_arm_temporal.parquet   547,824 satır × 17 col
--   ~/Dataleak/facts/dim_term_community.parquet         4,516 satır × 10 col
--
-- Ad seçimi (A): tablo isimleri parquet adıyla hizalı; 2.5 sayfasındaki
-- "concept_edge / concept_node" terminolojisi ürün-katmanı (UI),
-- table-katmanı warehouse hizalı (parquet adı). Çift bakım yükü yok.
--
-- İndeks paterni: SADECE PK + tek lookup index (community_id) bu migration'da.
-- 5 secondary index POST-LOAD'da scripts/colab_load_concept_terms.ipynb
-- Cell 6'da bilinçli (COPY hızı için — bulk-load sırasında index maintenance
-- yükü ~2-3× düşer; Compute Small'da bile 5-10× hız kazancı).
--
-- Kolon sözleşmesi: ENVANTER kanıtladığı 4-6 "core" kolon explicit;
-- parquet'in geri kalan ~14 kolonu "extra JSONB" alanına serialize.
-- Halüsinasyon yasağı (R4/HK): plan-time kolon adı uydurmuyoruz.
--
-- Tarih: 2026-05-10 · PG: 17.6
-- Bağımlılık: 0001 (schema_migrations tablosu)
--
-- Apply (notebook DIŞINDA — K-029 dersi: Dashboard SQL Editor silent fail):
--   psql "$SUPABASE_DB_URL" -f db/migrations/0021_concept_term_arm.sql
--
-- DB_URL formatı: Session Pooler :5432 (transaction :6543 ISP blok).
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. fact_term_arm_static — term × term Association Rule Mining (statik)
-- ============================================================================
-- 2.5 sayfa kullanımı: anchor-merkezli 1-hop / 2-hop alt-graf.
--   Sorgu: WHERE term_a = $anchor OR term_b = $anchor ORDER BY npmi DESC.
-- Kanıtlı core: term_a, term_b, lift, npmi, support, conviction
-- (ENVANTER.md satır 196: "term_a, term_b, lift, npmi, support, conviction, ...").
CREATE TABLE IF NOT EXISTS public.fact_term_arm_static (
  term_a       text   NOT NULL,
  term_b       text   NOT NULL,
  lift         float8,
  npmi         float8,
  support      float8,
  conviction   float8,
  extra        jsonb,                    -- parquet'in geri kalan ~14 kolonu
  PRIMARY KEY (term_a, term_b)
);

ALTER TABLE public.fact_term_arm_static ENABLE ROW LEVEL SECURITY;

CREATE POLICY fact_term_arm_static_read_all
  ON public.fact_term_arm_static
  FOR SELECT
  TO authenticated
  USING (true);

COMMENT ON TABLE public.fact_term_arm_static IS
  '2.5 kavram ağı: term × term ARM (NPMI/lift/support/conviction). Drive: ~/Dataleak/facts/fact_term_arm_static.parquet (~297K satır). Read-all authenticated; write = service_role (RLS bypass).';

COMMENT ON COLUMN public.fact_term_arm_static.npmi IS
  '2.5: kavram-kavram eş-anma normalize PMI. Anchor 1-hop top-K ranking için ana skor.';
COMMENT ON COLUMN public.fact_term_arm_static.lift IS
  '2.5: ARM lift skoru. Community boundary köprü tespiti (alt + community farklı + lift yüksek).';
COMMENT ON COLUMN public.fact_term_arm_static.extra IS
  'Parquet"in core olmayan kolonları (window_size, antecedent_count, vb.). Şema değişimi geri-uyumlu.';


-- ============================================================================
-- 2. fact_term_arm_temporal — term × term × year delta_lift (trend sinyali)
-- ============================================================================
-- 2.5 sayfa kullanımı: trending/declining ok. delta_lift > 0 yeşil yukarı,
-- < 0 kırmızı aşağı; jüri/hakem personası "yeni yükselen kavramı kovaladım"
-- iddiasını rakamla destekler.
-- Kanıtlı core: term_a, term_b, year, delta_lift
-- (ENVANTER.md satır 197: "term_a, term_b, year, delta_lift, ...").
CREATE TABLE IF NOT EXISTS public.fact_term_arm_temporal (
  term_a       text   NOT NULL,
  term_b       text   NOT NULL,
  year         int4   NOT NULL,
  delta_lift   float8,
  extra        jsonb,                    -- parquet'in geri kalan ~12 kolonu
  PRIMARY KEY (term_a, term_b, year)
);

ALTER TABLE public.fact_term_arm_temporal ENABLE ROW LEVEL SECURITY;

CREATE POLICY fact_term_arm_temporal_read_all
  ON public.fact_term_arm_temporal
  FOR SELECT
  TO authenticated
  USING (true);

COMMENT ON TABLE public.fact_term_arm_temporal IS
  '2.5 kavram ağı: yıl-bazlı ARM (RECENT_CUTOFF=2020 N17 üretimi). delta_lift trending/declining sinyali. Drive: fact_term_arm_temporal.parquet (~547K satır).';


-- ============================================================================
-- 3. dim_term_community — Leiden community map (term → community_id)
-- ============================================================================
-- 2.5 sayfa kullanımı: aynı topluluğun kelimeleri aynı renk; "alanın doğal
-- kümeleri" görsel mesaj. Köprü kavram tespitinde community_a ≠ community_b
-- ama lift > eşik filtresi.
-- Kanıtlı core: term, community_id
-- (ENVANTER.md satır 124: "term, community_id, ...").
CREATE TABLE IF NOT EXISTS public.dim_term_community (
  term          text  PRIMARY KEY,
  community_id  int4  NOT NULL,
  extra         jsonb                    -- parquet'in geri kalan ~8 kolonu
);

ALTER TABLE public.dim_term_community ENABLE ROW LEVEL SECURITY;

CREATE POLICY dim_term_community_read_all
  ON public.dim_term_community
  FOR SELECT
  TO authenticated
  USING (true);

COMMENT ON TABLE public.dim_term_community IS
  '2.5 kavram ağı: term → community_id (Leiden detection). Aynı community = aynı renk. Drive: dim_term_community.parquet (~4.5K satır).';


-- ============================================================================
-- 4. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0021_concept_term_arm',
  '2.5 kavram ağı altyapısı: 3 tablo (fact_term_arm_static + temporal + dim_term_community). Drive parquet → Supabase taşıma; secondary index post-load notebook''ta (COPY hızı için).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
