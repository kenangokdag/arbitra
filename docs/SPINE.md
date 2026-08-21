# SPINE.md — PaperMind MVP Mimari (2026-05-08 başladı)

> **Tek doğruluk kaynağı.** STATE/NEXT_ACTION/plan dosyaları ek; SPINE kanonik. Halüsinasyon yasak — her satırın arkasında repo veya kullanıcı kararı kanıtı var. Belirsiz alanlar "ERTELE" diye işaretli.

> **5 faz:** §0 Sayfa Envanteri → §1 Frontend Mimarisi → §2 Backend Mimarisi → §3 Veri Mimarisi → §4 İşçilik Sırası. Her faz onaydan sonra bir sonrakine geçer.

---

## §0 — Sayfa Envanteri

Her sayfa: **KONUM · MEVCUT · BOŞLUK · KARAR · NASIL**. Kanıt etiketleri: `[REPO]` repo dosyası, `[USER]` kullanıcı kararı bu thread'de, `[KARAR]` benim önerim onayda.

### §0.1 — Vitrin (3 sayfa, T0 anonim funnel; Q2 ELİMİNE — DM-054)

#### Q — Hızlı İnceleme

- **KONUM:** `web/src/app/(app)/q/page.tsx` (330 satır) `[REPO]`
- **MEVCUT:**
  - Tier badge "T0 · anonim · 3 sorgu / gün" (statik, sayaç yok)
  - Hero başlık "Konunu yaz, 3 makale gör"
  - Search input + 20/50/100 makale aralığı chip'leri (range state var, sonuçlara etkisi yok)
  - 3 hard-coded `MOCK_PAPERS` (Liu/Yıldız/Park) — her query için aynı 3 sonuç
  - Sonuç bandı: "3 makale · alaka sırasıyla · {range}'den önizleme"
  - Action bar: Q1 button active (`<a href="/q1">`), Q2/Q3 disabled "yakında", "Projeme Dönüştür" ink CTA (onClick yok)
  - URL state `?q=` (useSearchParams + router.replace)
- **BOŞLUK:**
  - Backend yok — search submit edilse de hep aynı 3 mock paper döner
  - Range chip'lerin (20/50/100) sonuçlara etkisi yok
  - "Projeme Dönüştür" button tıklanabilir ama hiçbir şey yapmaz
  - Tier rate limit (3 sorgu/gün) gerçek değil — sayaç ve gate yok
- **KARAR `[KARAR]` (DM-047, DM-052):**
  1. Havuz: dil-aware paralel fetch — TR sorgu = S2 30 + TRDizin 20, EN = S2 50. Toplam 50 paper havuz.
  2. **Display chip: 3 / 20 / 50** (mock'taki 20/50/100 değişir). Sıralama 50-paper havuz üzerinden 1-50 sabit; chip kesim noktasını değiştirir.
  3. **Tier:** Anon = 3 aktif, 20/50 → paywall modal "Literatür Özeti İçin Deneme Sürecini Başlat"; Pro = 3/20/50 hepsi aktif.
  4. Kart üstü rank göstergesi `[01]..[50]`; 50-kart UI virtualized list (`react-window`).
  5. Bottom CTA: **"Literatür Özeti Oluştur"** → `/q1?qid={query_id}` (chip seçiminden bağımsız; Q1'de K rakip-pattern, DM-050).
  6. IP-based günlük 3 sorgu limit + rate aşınca paywall modal.
  7. "Projeme Dönüştür" → e-posta capture form (auth gereksiz, Supabase tek-tablo insert).
- **NASIL `[KARAR]`:**
  - Yeni endpoint: `POST /api/q/search` `{query, range}` → `{papers: [3], pool_size: 50, query_id, sources}` `[DM-047]`
  - Havuz: langdetect → TR ise S2 30 + TRDizin 20 = 50; EN ise S2 50. S2 `relevance_search` + SPECTER2; TRDizin `https://search.trdizin.gov.tr/api/defaultSearch/publication/?q={q}&order=relevance-DESC&limit=20`
  - Redis L1 cache: `q:search:{sha256(query)}` 1h TTL (range pool'u etkilemez, hep 50)
  - Rate limit: Redis sliding window `q:ratelimit:{ip_hash}` günlük 3
  - Capture form: `POST /api/waitlist` `{email, research_area, query_id}` → Supabase `waitlist` tablo

#### Q1 — Literatür Özeti

- **KONUM:** ROUTE YOK — `web/src/app/(app)/q1/` dizini bulunmuyor `[REPO]`
- **MEVCUT:**
  - Q sayfasında `<a href="/q1">` link mevcut, ama hedef sayfa 404 dönüyor `[REPO]`
  - Sayfa içerik tasarımı: SOL PANEL (3 makale meta) + SAĞ GÖVDE (özet) `[USER]`
- **BOŞLUK:** Tüm sayfa.
- **KARAR `[KARAR]`:** Pilot funnel'in tier-aware ana değer ekranı. Sayfa herkese açık; içerik tier'a göre değişir.
  - **Sol panel (320 px sticky, hep görünür):** Q'dan gelen top-3 makale kartı (numara [01]/[02]/[03], title, authors+venue+year, citation count, kısa TR özet). Her karta hover'da inline highlight = sağ gövdedeki `[1][2][3]` alıntı (sadece Pro mode'da aktif).
  - **Sağ gövde:**
    - **Anon (T0):** Breadcrumb + query metni + paywall placeholder kartı: *"Geniş kapsamlı literatür özeti için Pro'ya geç. NotebookLM gibi çok yüksek ilişkili makaleleri tarayıp tek özet üretir."* + "Literatür Özeti İçin Deneme Sürecini Başlat" CTA + "Projeme Dönüştür" capture form (Q ile aynı).
    - **Pro:** Breadcrumb + query metni + ~400 kelime TR literatür özeti (NotebookLM-style, source-grounded); cümle sonlarında inline `[1]`, `[2]`, ..., `[K]` alıntı (clickable → sol panel highlight). Üst K çok yüksek ilişkili makaleden üretilir.
  - Bottom action bar: "Q ile yeni sorgu" (←) + "Q2/Q3 yakında" (disabled) + tier'a göre CTA ("Literatür Özeti İçin Deneme Sürecini Başlat" / "Projeme Dönüştür").
- **NASIL `[KARAR]`:**
  - Route: `web/src/app/(app)/q1/page.tsx` yeni
  - URL state: `/q1?qid={query_id}` (Q'dan gelen `query_id` ile aynı 50-paper pool'u geri çağır)
  - Yeni endpoint: `POST /api/q/literature` `{query_id}` → tier check (server-side session/header):
    - **Anon:** `{papers: [3 kart metadata], paywall: true, summary: null}`
    - **Pro:** `{papers: [K kart metadata], paywall: false, summary_tr, citations: [{sentence_idx, paper_ids: [...]}]}`
  - **Rerank — 2 aşamalı hybrid `[DM-049]`:**
    - **Aşama 1 (deterministic, hızlı):** S2 + TRDizin native relevance skoru → 50 havuzdan top-25
    - **Aşama 2 (LLM, kalite):** Gemini Flash 2.0 → 25 paper'ı sorguya göre yeniden sırala, Pydantic structured output (`paper_ids: list[str]` zorunlu) → top-K
  - LLM: Gemini Flash 2.0 (F8 LLMService — Faz 2'de doğrulanacak). Prompt: K abstract + query → 400 kelime TR özet + cümle-paper map. Citation grounding: Pydantic structured output, `paper_id` array zorunlu (halüsinasyon kapısı).
  - **K sayısı ERTELE `[DM-050]`:** Faz 2 (Backend mimarisi) başında Consensus + SciSpace + Elicit özet patternleri araştırılır → K rakip ortalamasına göre belirlenir. Pilot placeholder: K = 10-15 aralığı.
  - Cache: `q:literature:{query_id}:anon` (paywall response) + `q:literature:{query_id}:pro` (tam summary) 24h TTL
  - Tier gate: Anon Q1 sayaç artırmaz (Q'da harcandı). Pro session pilot key veya Supabase auth (Faz 2'de netleşir).

#### ~~Q2 — Giriş Bölümü~~ (ELİMİNE — DM-054, 2026-05-08)

Sayfa silindi. Üç gerekçe: (a) academic research-positioned 3 büyük rakip (Consensus/Elicit/Scite) intro üretmiyor → kategori sinyali bozulur; (b) Nature/Science/Cell AI authorship politikaları gri alan → senior researcher kullanmaz; (c) Q→Q1→Q3 funnel zaten temiz (keşif → sentez → eylem önerisi), Q2 asimetri yaratır. Detay: DECISIONS.md DM-054.

#### Q3 — Metod Önerisi

- **KONUM:** ROUTE YOK `[REPO]` — `web/src/app/(app)/q3/page.tsx` Faz 1+ açılır
- **MEVCUT:** Q sayfasında disabled button "yakında" `[REPO]` → DM-054 sonrası **aktif** edildi (paywall-aware), Q1 ile aynı tier davranışı
- **KARAR `[KARAR]` (DM-055):** Q1 + Q3 **iki bağımsız endpoint** — Q havuzu (50 paper Redis cache, DM-047) ortak kaynak; LLM çağrıları ayrı; cache key ayrı. **Q3 scope (3 komponent):** (a) havuzdaki metod dağılımı (% bazında: RCT, sistematik derleme, nitel, mixed, simulation, vs.); (b) sorguya uygun 2-3 metod önerisi + gerekçe + literatürden örnek paper; (c) sample size aralığı + bilinen dataset/araç hint (ML→benchmark, Bio→cohort, Soc→survey scale). Tier: Anon = sol panel 3 kart + sağ paywall placeholder; Pro = full method analysis (sorgu dilinde TR/EN/ID).
- **NASIL `[KARAR]`:** Endpoint `POST /api/q/method`; service `api/services/q_method_service.py`; cache `q:method:{query_id}:{tier}` 24h TTL. Pydantic structured output `used_paper_ids ⊆ Q havuzu paper_id'leri` (halüsinasyon kapısı, DM-049 doktrini). Detay sayfa planı `Page_Design/Sayfa_Plani_v1/C_vitrin/q3.md` (sıradaki yazılacak).
- **Pilot kod scope:** AÇIK — F1 başında karar; mimari plan kanon, kod yazımı F1+ veya pilot retrospektif.

---

**§0.1 Vitrin batch DURUM:** 3 sayfa envanteri yazıldı. **3 aktif (Q + Q1 + Q3); Q2 ELİMİNE — DM-054.** Pilot kod scope: **Q ⇄ Q1 funnel + capture form**; Q3 mimari plan kanon, pilot kod scope F1 kararı.

**Tier modeli (pilot):**
- **Anon (T0):** Q'da 3 sorgu/gün IP-rate, Q1 ve Q3'te sadece sol panel (3 kart) + paywall placeholder. Çıktı YOK.
- **Pro:** Q1 sağ gövdede literatür özeti (sorgu dilinde TR/EN/ID, K çok yüksek ilişkili makale, citation-grounded); Q3 sağ gövdede metod önerisi (havuz metod dağılımı + 2-3 metod öneri + sample/dataset hint).
- **Free tier (registered, ödenmemiş): YOK.** İcat çıkarmadık — 2-tier basit funnel.
- **Pro+ tier:** ELİMİNE EDİLDİ (2026-05-08 [USER] kararı).

**Çözülmüş kararlar (DECISIONS.md'de kanon):**
- **DM-046:** Tier modeli Anon + Pro (Free + Pro+ ELİMİNE)
- **DM-047:** Havuz S2 30 + TRDizin 20 = 50 (TR sorgu için TRDizin paralel; EN/ID sadece S2 50)
- **DM-048:** Q1 sol panel + sağ gövde tier-aware tasarım
- **DM-049:** Rerank 2 aşamalı hybrid (S2/TRDizin native → 25, LLM → K)
- **DM-051:** ~~Q2/Q3 ERTELE~~ İPTAL — DM-053 ile değişti
- **DM-052:** Q chip 3/20/50 + tier paywall + ranking görünür + "Literatür Özeti / Metod Önerisi" CTA
- **DM-053:** Page_Design tüm sayfalar (Q3 dahil; Q2 hariç) plan yazılacak — pilot kod scope DEĞİŞMEDİ
- **DM-054:** Q2 (Giriş Bölümü) ELİMİNE — kategori sinyali + etik gri alan + funnel asimetri
- **DM-055:** Q1 + Q3 bağımsız endpoint mimarisi (Q havuzu paylaşımlı, LLM çağrıları ayrı, Pydantic pool grounding)

**Açık ERTELE'ler (§0.1):**
- **DM-050 — K sayısı** (Pro Q1 özetinde kaç makale): F2'de Consensus/SciSpace/Elicit pattern araştırılıp belirlenir. Pilot placeholder: 12.
- **Trial mekanizması** (Anon → Pro deneme akışı): F2'de netleşir (Stripe / pilot key / X gün ücretsiz vb.).
- **Q3 pilot kod scope:** F1 başında karar (mimari plan kanon).

**Sıradaki:** §0.2 Atölye Discovery 5 sayfa (kullanıcı onayı bekliyor).
