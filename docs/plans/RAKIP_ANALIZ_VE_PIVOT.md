# Rakip Analizi ve PaperMind Pivot Planı

> **Tarih:** 2026-05-01
> **Tetikleyici:** Omer — "hepsinde chatbox var, biz keyword soruyoruz. chat daha mantıklı. rakipler yol göstersin."
> **Statü:** ONAYLANDI (Council 35 + Omer hakem 2026-05-01)

---

## §1 Rakip Ekran Karşılaştırma Matrisi

### 1.1 Etkileşim Modeli

| Platform | Giriş Modeli | İlk Temas | Kullanıcıyı Anlama | Proje Yapısı |
|---|---|---|---|---|
| **SciSpace** | Chat-first | "Give me any task to work on..." | Sohbetle anlama | Chat geçmişi (flat) |
| **Consensus** | Search-first | "Ask the research..." + Corpus/Deep toggle | Sorgu analizi | Thread bazlı |
| **Elicit** | Agent-first | "Describe your research goal" + Research agent/General dropdown | Ajan soruları ile | Library (flat) |
| **Undermind** | Project + Chat | "What are your research goals?" + "I'll ask a few questions" | Proje bağlamı + soru-cevap | **Proje bazlı workspace** |
| **PaperMind (mevcut)** | Keyword-first | 3 keyword kutusu + VE/HARİÇ | Keyword eşleme | Yok (flat) |

**Sonuç:** 4/4 rakip chat veya doğal dil kullanıyor. PaperMind tek keyword-based kalan platform.

### 1.2 UI / Tasarım Karşılaştırma

| Platform | Ana Renk | Accent | Arka Plan | Font | Buton Stili | Sidebar |
|---|---|---|---|---|---|---|
| **SciSpace** | Beyaz/açık gri | Kırmızı-turuncu gradient | #FFFFFF | Sans-serif (Inter benzeri) | Rounded pill, hafif shadow | 240px, 12+ link, ikon+text |
| **Consensus** | Beyaz | Mavi-teal gradient | #FFFFFF | Sans-serif temiz | Pill button, gradient fill | 220px, minimal 4 link |
| **Elicit** | Beyaz, bol boşluk | Teal/yeşil (#0F766E civarı) | #FFFFFF | Sans-serif, ince | Rounded subtle, outline | 240px, 2 bölüm (Workflows/Tools) |
| **Undermind** | Beyaz/açık lavanta | Mor/purple (#6D28D9 civarı) | #F8F7FF lavanta tint | Sans-serif | Pill, gradient mor | 100px ultra-minimal |
| **PaperMind (mevcut)** | Slate cool-academic | Amber-700 | Slate-50 (#F8FAFC) | Inter + Lora | Radius-sm, flat | 240px, 3 grup |

**Gözlemler:**
- Rakipler: hepsi **saf beyaz** veya çok hafif tinted background
- Rakipler: accent renkler **canlı** (gradient, saturated blue/teal/purple)
- Rakipler: butonlar **pill shaped** (rounded-full veya rounded-xl)
- PaperMind: slate palette + amber accent → **rakiplerden belirgin şekilde farklı** (soğuk, akademik, az kontrast)
- PaperMind: Lora serif italic → **hiçbir rakipte serif yok** (diferansiyel avantaj mı yoksa uyumsuzluk mu?)

### 1.3 Fonksiyon Karşılaştırma

| Özellik | SciSpace | Consensus | Elicit | Undermind | PaperMind (plan) |
|---|---|---|---|---|---|
| Doğal dil arama | ✅ | ✅ | ✅ | ✅ | ❌ (keyword) |
| Chat ile derinleşme | ✅ | ✅ | ✅ | ✅ | ✅ (F3b plan) |
| Proje/workspace | ❌ | ❌ | ❌ | ✅ | ❌ (Omer önerisi) |
| Rapor yazma | ✅ | ✅ Draft | ✅ Report | ✅ Report Writer | ❌ (post-MVP) |
| Kişiselleştirme/profil | ❌ | ❌ | ❌ | ❌ | ✅ r-ESTRA |
| Karar transparanlığı | ❌ | ❌ | ❌ | ❌ | ✅ decision_band + 13 sinyal |
| Sessiz öğrenme | ❌ | ❌ | ❌ | ❌ | ✅ r-ESTRA |
| Makale kalite skoru | ❌ | ❌ | ❌ | ❌ | ✅ w-ESTRA + q_weak |
| Systematic review | ❌ | ❌ | ✅ (kilitli) | ❌ | ❌ |
| Data extraction | ✅ | ❌ | ✅ (kilitli) | ❌ | ❌ |
| Citation graph | ❌ | ✅ | ❌ | ❌ | ❌ (post-MVP) |

---

## §2 Pivot Önerisi — Chat-First + Proje Bazlı

### 2.1 Etkileşim Modeli Değişikliği

```
ESKİ (keyword-first):
  Kullanıcı → [keyword1] [VE] [keyword2] [HARİÇ] [keyword3] → Ara butonu
  ↓
  Makale listesi (ESTRA sıralı)

YENİ (chat-first):
  Kullanıcı → "MCDM yöntemlerinin eğitimde kullanımını araştırıyorum"
  ↓
  Sistem → "Hangi eğitim kademesini hedefliyorsunuz? (K-12 / Yükseköğretim / Mesleki)"
  ↓
  Kullanıcı → "Yükseköğretim, özellikle mühendislik fakülteleri"
  ↓
  Sistem → [Chat'ten keyword çıkarır: MCDM + education + higher education + engineering]
         → [ESTRA + r-ESTRA skorlama]
         → [Top-K makale listesi + decision_band + chip'ler]
  ↓
  Makale listesi (aynı zenginlikte, ama daha iyi anlaşılmış sorgu)
```

### 2.2 Teknik Mimari

```
Chat Input (doğal dil)
  ↓
P004 QwenListener.listen(query, lang="tr")
  ↓ (mevcut: keyword extraction)
  ↓ (yeni: intent classification + entity extraction + refinement question generation)
  ↓
Refinement Loop (0-2 tur, kullanıcı "Ara" derse hemen geçer)
  ↓
P005 PmidAnchor + P006 PoolRouter (mevcut pipeline, değişmez)
  ↓
Sonuç listesi (mevcut PaperCard + decision_band + chip)
```

**Backend etkisi:** P004 QwenListener'a `intent_classify` + `generate_refinement_question` eklenir. Pipeline geri kalanı DEĞİŞMEZ.

**Frontend etkisi:** `/search` sayfası keyword form yerine chat input + mesaj baloncukları. Sonuç listesi aynı kalır.

### 2.3 Proje Yapısı

```
DB: projects tablosu
  - id, user_id, name, created_at, updated_at
  - status (active/archived)

Her mevcut tablo'ya project_id FK eklenir:
  - search_history → project_id
  - reading_list → project_id
  - chat_history → project_id

r-ESTRA profil → project_id YOK (global)
```

### 2.4 İki Katmanlı Tier

| | Free | Pro | Açıklama |
|---|---|---|---|
| **Katman 1: Proje** | 2 proje | Sınırsız | Workspace sayısı |
| **Katman 2: İçerik** | Arama + Top 5 (günlük 10 arama) | + Sohbet + Özet + Rapor + Okuma Listesi + Sınırsız arama | Proje içi özellik derinliği |

---

## §3 Tasarım Pivot Önerileri

### 3.1 Renk Paleti Yeniden Değerlendirme

**Mevcut (cool-academic):**
- BG: slate-50 (#F8FAFC)
- Ink: slate-900
- Accent: amber-700
- Status: emerald/blue/orange/red pale chip

**Rakip ortalaması:**
- BG: saf beyaz (#FFFFFF)
- Accent: canlı saturated (teal/blue/purple)
- Buton: gradient veya solid saturated

**Seçenekler:**

| Seçenek | Palet | Risk |
|---|---|---|
| A: Mevcut koru | slate + amber (akademik, farklılaşır) | Rakiplerden çok farklı → "eski" algısı? |
| B: Beyaz + teal | #FFFFFF + teal-600 accent | Elicit'e benzer → farksız |
| C: Beyaz + indigo | #FFFFFF + indigo-600 + amber accent korunur | Modern ama amber ile kimlik korunur |
| D: Krem-warm + indigo | #FAFAF8 + indigo-600 | Akademik sıcaklık + modern accent |

### 3.2 Buton Stili

| Mevcut | Rakip Trendi | Öneri |
|---|---|---|
| radius-sm (6px), flat, manuscript underline | Pill (rounded-full), gradient/solid | radius-lg (14px) veya pill, solid accent fill, hover scale |

### 3.3 Font

| Mevcut | Rakip Trendi | Öneri |
|---|---|---|
| Inter (UI) + Lora (display, italic) | Hepsi sans-serif only | Lora italic KORU → akademik diferansiyel. Ama body'de Lora azalt, sadece başlıklarda |

---

## §4 MVP Scope Etkisi

| Değişiklik | MVP'ye Etkisi | Effort |
|---|---|---|
| Chat-first input (/search) | F4-S2 scope değişir (keyword form → chat input) | ~2 gün ek |
| Refinement question loop | P004 Listener'a ek fonksiyon | ~1 gün ek |
| Proje yapısı (DB + routing) | Yeni migration + sidebar proje listesi + routing | ~3 gün ek |
| Renk paleti revize | globals.css token swap + component audit | ~1 gün |
| Buton stili revize | Button.tsx + tüm buton kullanımları | ~0.5 gün |
| İki katmanlı tier | Pricing page + middleware tier check | Post-MVP |

**Toplam ek effort:** ~7.5 gün (MVP süresine eklenir)

---

## §5 Council Sunumu İçin Sorular

1. Chat-first mi yoksa hybrid mi? (Chat default + gelişmiş keyword modu opsiyonel)
2. Proje yapısı MVP'ye mi Faz 2'ye mi girer?
3. Renk paleti hangi seçenek? (A/B/C/D)
4. Buton stili pill'e mi geçer?
5. Lora serif korunur mu?
6. İki katmanlı tier tasarımı MVP'de mi planlanır?
7. Rapor yazma (Report Writer) MVP scope'una girer mi?

---

## §6 Hat 2 Genişleme — Simülasyon + Eğitim + Akıllı Yönlendirme

### 6.1 Hat 2 Kapsamı (Post-MVP, sıralı)

| Modül | Ne | Girdi | Çıktı | Zamanlama |
|---|---|---|---|---|
| **Tez Savunma Provası** | Jüri soruları simülasyonu | PDF/abstract + tez türü (YL/DR) | Jüri soruları + zayıf nokta + hazırlık | Post-MVP Sprint 1 |
| **Hakemlik Simülasyonu** | Hakem raporu üretimi | Makale draft + hedef dergi | R1/R2 rapor + revizyon + ret riski | Post-MVP Sprint 1 |
| **Danışman Eğitimi** | Danışmanlık becerisi geliştirme | Tam metin + öğrenci profili | Geri bildirim örnekleri + yönlendirme senaryoları | Post-MVP Sprint 2 |
| **Hakem Eğitimi** | Hakemlik becerisi geliştirme | Tam metin + dergi profili | Hakem raporu yazma rehberi + örnek inceleme | Post-MVP Sprint 2 |
| **Editör Eğitimi** | Editörlük becerisi geliştirme | Makale seti + dergi politikası | Karar verme senaryoları + hakem atama mantığı | Post-MVP Sprint 3 |

**Tam metin kullanımı:** Hat 2 modülleri `works_clean_v2` (73 GB tam abstract/metin) kullanarak eğitim yapar. Hat 1 (Core PaperMind) sadece abstract ve metadata kullanır — tam metin Hat 2'nin değer farkı.

### 6.2 Akıllı Yönlendirme Sistemi ("Danışmana Sor" ve Ötesi)

PaperCard ve arama sonuçlarında **akıllı aksiyon önerileri:**

```
Makale kartı üzerinde:
  ├── [Detay]        → PaperMind iç sayfa
  ├── [Listeme Ekle] → Okuma listesi (proje bazlı)
  ├── [Özetle]       → LLM özet
  ├── [Sohbet Et]    → Makale ile chat
  ├── [Nota Ekle]    → Karar hafızası
  └── [Daha Fazla ▼]
        ├── 🤖 AI ile Tartış      → tartışma prompt'u oluştur (Claude/ChatGPT/Gemini uyumlu)
        ├── 🔗 Google Akademik    → Google Scholar arama linki (başlık + yazar)
        ├── 🔗 Dergi Platformu    → DOI link veya yayıncı sayfası (Elsevier/Springer/Wiley...)
        ├── 🔗 Sci-Hub Alternatif → Open Access versiyonu ara (Unpaywall API)
        ├── 📋 Atıf Kopyala       → APA/Chicago/Harvard formatında clipboard'a
        └── 📊 Benzer Makaleler   → ESTRA komşuluk araması (bibcoupling_top50)
```

**AI ile Tartış prompt şablonu:**
```
"Bu makaleyi okudum: [başlık]. Yazarlar [özet].
Benim araştırma konum: [proje adı + konu daraltma kararları].
Bu makalenin güçlü ve zayıf yönlerini tartışalım.
Özellikle metodoloji seçimi ve bulgularının genellenebilirliğini değerlendir."
```
→ Kullanıcı bunu Claude/ChatGPT/Gemini'ye yapıştırır. PaperMind kendi LLM'i ile de yapabilir (Pro tier).

**Dış platform arama linkleri:**
- Google Scholar: `https://scholar.google.com/scholar?q="başlık"+yazar`
- Semantic Scholar: `https://api.semanticscholar.org/...`
- PubMed: `https://pubmed.ncbi.nlm.nih.gov/?term=...`
- DOI doğrudan: `https://doi.org/10.xxxx/...`

Bu linkler **PaperCard metadata'sından otomatik üretilir** — kullanıcı kopyala-yapıştır yapmaz.

### 6.3 Öncelik Sırası (Omer onayı)

```
1. Core PaperMind (Hat 1) → MVP sağlam hale getir
   ├── Supabase altyapı (Faz 2 + Faz 3)
   ├── Chat-first hybrid
   ├── Proje yapısı + karar hafızası
   ├── Akıllı yönlendirme butonları (Google Scholar/DOI/atıf)
   └── AI ile Tartış prompt üretici

2. Simülasyon (Hat 2) → Post-MVP
   ├── Savunma provası + hakemlik simülasyonu
   └── Danışman/hakem/editör eğitim modülleri (tam metin bazlı)
```

---

## §7 Rakip Görseller (kanıt)

| Dosya | Platform | Sayfa |
|---|---|---|
| `Ekran Resmi 2026-05-01 09.55.23.png` | SciSpace | Ana sayfa (chat + tool grid) |
| `Ekran Resmi 2026-05-01 09.55.38.png` | Consensus | Ana sayfa (search + Corpus/Deep) |
| `Ekran Resmi 2026-05-01 09.56.14.png` | Elicit | Ana sayfa (agent + suggested prompts) |
| `Ekran Resmi 2026-05-01 09.56.31.png` | Undermind | Landing page |
| `Ekran Resmi 2026-05-01 10.00.30.png` | Undermind | Research Projects listesi |
| `Ekran Resmi 2026-05-01 10.00.41.png` | Undermind | Proje içi (Search Architect + Report Writer) |

---

## §8 ESTRA + Validator Çift Katman Mimarisi

### 8.1 Problem

ESTRA formülleri teorik tasarım aşamasında. Gerçek veriyle test edilmedi. Doğrulanmamış skor göstermek fiyasko riski.

### 8.2 Çözüm: Çift Katman

Her ESTRA boyutunu bağımsız literatür metrikleriyle çapraz kontrol:

| ESTRA | Validator | Kaynak |
|-------|----------|--------|
| d-ESTRA (atıf) | RCR + Dimensions FCR + CD Index | iCite (ücretsiz) + S2 hesaplama |
| w-ESTRA (kelime) | Flesch-Kincaid + AWL Coverage | Direkt hesaplama |
| s-ESTRA (yapı) | SJR Quartile + statcheck | SCImago CSV (ücretsiz) + R paketi |
| t-ESTRA (tema) | Novelty Score (Uzzi et al. 2013) | Cocitation verisinden hesaplama |
| r-ESTRA (profil) | h-index + Research Diversification | S2 / ORCID |

Consistency Check: ESTRA yüksek + Validator düşük → FLAG. Güven kartı kullanıcıya gösterilir.

### 8.3 Doğrulama Protokolü (V0-V4)

- **V0:** Metrik tanımları netleştir
- **V1:** 30K'dan tabakalı 500 makale + Omer 50 manuel puanlama (rubrik tanımlanacak)
- **V2:** Korelasyon testleri (Spearman > 0.5, Cohen's kappa > 0.6)
- **V3:** Alan norm tabloları + formül ağırlık kalibrasyonu
- **V4:** 5-fold çapraz doğrulama

### 8.4 3 Seviyeli Girdi

| Seviye | Girdi | Güven (tahmini) |
|--------|-------|:---:|
| 3 | Tam metin (PDF/DOCX) | %85-95 |
| 2 | Özet + kaynakça | %50-65 |
| 1 | Metadata (başlık + DOI) | %25-35 |

### 8.5 Makale vs Tez Ayrımı

Tez için farklı validator seti: LCR (lit kapsam), MRA (metod-sonuç uyumu), CC (bölüm coherence), DR (derinlik oranı), DRS (savunma hazırlık).

Tez verisi: YÖK Tez Merkezi + DART-Europe + EThOS. Hedef 5K (2.5K YL + 2.5K DR).

### 8.6 Council 35 Sonucu

13/14 GREEN, 1 ŞARTLI (DM-002 revize: 1 ay → 5-6 hafta, Omer onayladı). B-022 DECISIONS.md'ye yazıldı.
