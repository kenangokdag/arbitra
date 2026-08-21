# KONSEY SUNUMU — 2026-05-01 Oturum Kararları

> **Hazırlayan:** Claude (Omer talebiyle)
> **Statü:** ONAYLANDI (Council 35 + Omer hakem 2026-05-01)
> **Amaç:** Bu oturumdaki tüm kararların sistematik sunumu. Konsey her maddeyi inceler, onaylar veya revize eder. Nihai karar sonrası DECISIONS.md + STATE.md + plan manifest'ler güncellenir.

---

## OZET

Bu oturumda 12 stratejik karar alındı. 4 kategoride:

| Kategori | Karar Sayısı | Etki |
|----------|:---:|--------|
| A. Etkileşim Modeli Pivot | 3 | MVP scope + frontend + backend |
| B. Urun Yapısı + Fiyatlama | 3 | Is modeli + gelir + roadmap |
| C. Kalite Guvence Mimarisi (ESTRA + Validator) | 3 | Teknik mimari + veri pipeline |
| D. Girdi Esnekligi + Tez Genislemesi | 3 | Kullanıcı deneyimi + veri toplama |

---

## A. ETKİLESİM MODELİ PİVOT

### A1. Chat-First Hybrid Model (DM-017 adayı)

**Mevcut:** 3 keyword kutusu + VE/HARİC operatorleri
**Yeni:** Doğal dil chat input (default) + "Gelismis Arama" toggle (opsiyonel keyword modu)

**Gerekce:**
- 4/4 rakip (SciSpace, Consensus, Elicit, Undermind) chat veya doğal dil kullanıyor
- PaperMind keyword-based kalan tek platform
- Chat daha düşük giriş bariyeri (akademisyen keyword formulasyonu yapmak zorunda değil)

**Teknik etki:**
- P004 QwenListener'a `intent_classify` + `generate_refinement_question` eklenir
- Frontend `/search` sayfası keyword form → chat input + mesaj baloncukları
- Pipeline geri kalanı (P005 PmidAnchor + P006 PoolRouter) DEĞİŞMEZ
- Ek effort: ~3 gün

**Risk:**
- Chat yanıltıcı olabilir (kullanıcı "her şeyi bulur" beklentisi)
- Refinement loop 0-2 tur sınırı aşılırsa latency artar

**Kanıt:** 6 rakip ekran görüntüsü analizi (RAKIP_ANALIZ_VE_PIVOT.md §1)

---

### A2. Proje Bazlı Workspace (DM-018 adayı)

**Mevcut:** Flat yapı (tüm aramalar, okuma listeleri karışık)
**Yeni:** `projects` tablosu + tüm arama/okuma/chat geçmişi proje altında

```sql
CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

**FK eklenen tablolar:** search_history, reading_list, chat_history → `project_id`

**Gerekce:**
- Undermind proje bazlı ilerliyor (ekran kanıtı: "Research Projects" listesi)
- Akademisyen paralel projeler yürütür (tez danışmanlığı + kendi araştırması + ders)
- Proje izolasyonu = daha temiz UX + tier fiyatlama kolaylığı

**Ek effort:** ~3 gün (migration + sidebar proje listesi + routing)

---

### A3. Karar Hafızası (DM-019 adayı)

**Yeni:** `project_decisions` tablosu — kullanıcının her makale için aldığı kararları kaydeder

```sql
CREATE TABLE project_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  paper_id text REFERENCES fact_paper_id_card(paper_id),
  decision_type text NOT NULL CHECK (decision_type IN (
    'accept','reject','bookmark','note',
    'method_select','topic_narrow','topic_expand','direction_set'
  )),
  reason text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);
```

**Gerekce:**
- Kullanıcının neyi kabul/reddettiğini bilmeden kişiselleştirme yapılamaz
- r-ESTRA geri bildirim döngüsü için veri kaynağı
- Rakiplerin hiçbirinde yok → fark yaratan özellik

**Kritik karar:** r-ESTRA profili **GLOBAL** kalır (project_id FK yok). Kullanıcının akademik kimliği projeden bağımsız. Kararlar proje bazlı, profil küresel. (DM-021 adayı)

---

## B. URUN YAPISI + FİYATLAMA

### B1. İki Urun Hattı (DM-020 adayı)

| Hat | Urun | Satış Modeli | Zamanlama |
|-----|------|-------------|-----------|
| **Hat 1: Core PaperMind** | Proje bazlı literatür tarama + ESTRA sıralama + chat + okuma listesi | Abonelik (tier) | MVP |
| **Hat 2a: Yayın Hazırlık** | Makale/tez analiz pipeline (ESTRA + Validator + LLM rapor) | Abonelik (tier) | Post-MVP |
| **Hat 2b: Simülasyon** | Savunma provası + hakemlik simülasyonu + danışman/hakem/editör eğitimi | Ayrı lisans | Post-MVP |

**Gerekce:**
- Simülasyon ve eğitim modülleri farklı kullanıcı kitlesi (danışman vs öğrenci)
- Ayrı satış = daha esnek fiyatlama
- Hat 1 sağlam olmadan Hat 2 anlamsız

### B2. İki Katmanlı Tier Fiyatlama

| | Free | Pro |
|---|---|---|
| **Katman 1: Proje** | 2 proje | Sınırsız |
| **Katman 2: İçerik** | Arama + Top 5 (günlük 10 arama) | + Sohbet + Özet + Rapor + Okuma Listesi + Sınırsız arama |

### B3. Hat 2 Modülleri (Post-MVP Roadmap)

| Modül | Ne | Sprint |
|-------|-----|--------|
| Tez Savunma Provası | Jüri soruları simülasyonu | Post-MVP S1 |
| Hakemlik Simülasyonu | Hakem raporu üretimi | Post-MVP S1 |
| Danışman Eğitimi | Geri bildirim örnekleri + yönlendirme senaryoları | Post-MVP S2 |
| Hakem Eğitimi | Hakem raporu yazma rehberi + örnek inceleme | Post-MVP S2 |
| Editör Eğitimi | Karar verme senaryoları + hakem atama mantığı | Post-MVP S3 |

**Tam metin kullanımı:** Hat 2 modülleri tam metin kullanır. Hat 1 sadece abstract + metadata. Tam metin = Hat 2'nin değer farkı.

### B4. Akıllı Yönlendirme Butonları

PaperCard üzerinde:
- AI ile Tartış → tartışma prompt'u oluştur (Claude/ChatGPT/Gemini uyumlu)
- Google Akademik → başlık + yazar ile arama linki
- Dergi Platformu → DOI link veya yayıncı sayfası
- Açık Erişim Ara → Unpaywall API ile OA versiyonu
- Atıf Kopyala → APA/Chicago/Harvard formatında clipboard'a
- Benzer Makaleler → ESTRA komşuluk araması

**Tüm linkler PaperCard metadata'sından otomatik üretilir.**

---

## C. KALİTE GUVENCE MİMARİSİ

### C1. ESTRA + Validator Çift Katman

**Problem:** ESTRA formülleri teorik tasarım aşamasında. Gerçek veriyle test edilmedi. Doğrulanmamış skor göstermek fiyasko riski.

**Çözüm:** Her ESTRA boyutunu bağımsız bir "Validator" metrikiyle çapraz kontrol et.

```
Makale girdi
  │
  ├── ESTRA Pipeline (bizim formüller)
  │     ├─ w-ESTRA → kelime kalitesi
  │     ├─ d-ESTRA → atıf kalitesi
  │     ├─ s-ESTRA → yapısal bütünlük
  │     └─ t-ESTRA → tema tutarlılığı
  │
  ├── Validator Pipeline (literatür metrikleri)
  │     ├─ RCR (Relative Citation Ratio, iCite NIH)
  │     ├─ FWCI (Field-Weighted Citation Impact)
  │     ├─ CD Index (Disruption Index, Funk & Owen-Smith 2017)
  │     ├─ Novelty Score (Uzzi et al. 2013, Science)
  │     ├─ SJR Quartile (SCImago)
  │     ├─ Flesch-Kincaid + AWL Coverage
  │     └─ statcheck (Nuijten et al. 2016)
  │
  └── Consistency Check
        ├─ ESTRA yüksek + Validator düşük → FLAG
        ├─ ESTRA düşük + Validator yüksek → ESTRA kalibre edilmeli
        └─ Tutarlı → GÜVENILIR
```

### C2. ESTRA ↔ Validator Eşleşme Tablosu

| ESTRA | Kontrol Eden Validator | Neden |
|-------|----------------------|-------|
| d-ESTRA (atıf) | RCR + FWCI + CD Index | Üçü de atıf bazlı, farklı normalize yöntemleri |
| w-ESTRA (kelime) | Flesch-Kincaid + AWL Coverage | Okunabilirlik + akademik yoğunluk |
| s-ESTRA (yapı) | SJR Quartile + statcheck | Q1 dergiler yapısal standart zorlar |
| t-ESTRA (tema) | Novelty Score (Uzzi) | İkisi de referans ağı bazlı |
| r-ESTRA (profil) | h-index + Research Diversification | Profil doğrulama |

### C3. Doğrulama Protokolü (V0-V4)

| Aşama | Ne | Çıktı |
|-------|-----|-------|
| **V0** | Ne ölçtüğümüzü netleştir, ground truth kaynakları belirle | Metrik tanım dokümanı |
| **V1** | 30K tam metinden tabakalı 500 makale seç, ground truth hazırla | Gold standard dataset |
| **V2** | Her ESTRA boyutunu ayrı test et (korelasyon, ANOVA, Cohen's kappa) | Test sonuç raporu |
| **V3** | Formül ağırlıkları + alan bazlı norm tabloları çıkar | Kalibrasyon tabloları |
| **V4** | 5-fold çapraz doğrulama, overfitting kontrolü | Güvenilirlik raporu |

**Başarı kriterleri:**
- d-ESTRA vs RCR: Spearman rho > 0.5
- s-ESTRA vs dergi quartile: ANOVA p < 0.05
- w-ESTRA vs Flesch: rho < -0.3
- t-ESTRA vs alan kümesi: Silhouette > 0.4
- s-ESTRA vs uzman puanı (Omer 50 makale): Cohen's kappa > 0.6

**ESTRA doğrulanmadan Hat 1'de skor gösterilemez. Doğrulanmadan ürüne koymak yasak.**

---

## D. GİRDİ ESNEKLİĞİ + TEZ GENİŞLEMESİ

### D1. 3 Seviyeli Girdi Pipeline

Tam metin yüklemek istemeyen kullanıcılar için:

| Seviye | Girdi | Çalışan Modüller | Güven |
|--------|-------|-------------------|:-----:|
| **3: Tam Metin** | PDF/DOCX | Tüm ESTRA + Tüm Validator + LLM | %85-95 |
| **2: Özet** | Abstract + kaynakça | d-ESTRA + t-ESTRA + w-ESTRA (kısmi) + RCR/SJR | %50-65 |
| **1: Metadata** | Başlık + DOI + yazar | d-ESTRA (atıf) + RCR/FWCI/SJR | %25-35 |

**Güven kartı kullanıcıya gösterilir:**
- Ne çalıştı, ne eksik → şeffaflık
- "Tam metin yüklerseniz güven %90'a çıkar" → organik upsell

### D2. Makale vs Tez Ayrımı

Tez makaleden farklı: RCR/FWCI yok, yapı farklı (80-300 sayfa), jüri değerlendirmesi var.

| ESTRA | Makale Validator | Tez Validator |
|-------|-----------------|---------------|
| d-ESTRA | Kaynakçanın RCR/FWCI'ı | Literatür Kapsam Oranı (LCR) |
| s-ESTRA | SJR Quartile | YÖK/üniversite şablon uyumu |
| w-ESTRA | Flesch + AWL | Flesch + AWL + 300 sayfa ton tutarlılığı |
| t-ESTRA | Novelty (Uzzi) | Bölümler arası tema akışı (CC) |

**Tez-spesifik yeni metrikler:**
- **LCR (Lit Coverage Ratio):** Alandaki temel çalışmaların kaçı kaynakçada
- **MRA (Method-Result Alignment):** Metodda söylenen araçlar bulgularda kullanılmış mı
- **CC (Chapter Coherence):** Bölümler arası tema tutarlılığı (embedding cosine)
- **DR (Depth Ratio):** Derinlik vs genişlik dengesi
- **DRS (Defense Readiness Score):** Zayıf noktalar + olası jüri soruları (LLM)

### D3. Tez Verisi Toplama

| Kaynak | İçerik | Erişim |
|--------|--------|--------|
| YÖK Tez Merkezi | TR tezleri, abstract + metadata | Açık, scrape |
| DART-Europe | Avrupa tezleri, tam metin | Açık erişim |
| EThOS (British Library) | UK tezleri, tam metin | Açık erişim |
| ProQuest | Uluslararası tezler | Kurumsal erişim |

**Hedef:** 5K tez (2.5K YL + 2.5K DR), alan çeşitliliği sağlanmış.

---

## RAKIP TEKNOLOJİ ANALİZİ — REFERANS

Bu oturumda analiz edilen kör hakemlik araçları:

| Araç | Yaklaşım | Katman |
|------|----------|--------|
| **SciScore** | Kural tabanlı, ARRIVE/MDAR/CONSORT | Metodolojik kontrol |
| **StatReviewer** | Deterministik, p-değeri/istatistik tutarlılığı | İstatistik denetimi |
| **Proofig** | CNN tabanlı görsel anomali | Görsel (kapsam dışı) |
| **iThenticate** | N-gram fingerprint | Benzerlik (kapsam dışı) |
| **Penelope** | Kural tabanlı dergi şablon uyumu | Yapısal uyumluluk |
| **Paperpal** | 3 kategori x 35+ kontrol (hibrit: kural + LLM + CV) | Çok katmanlı |
| **Thesify** | 7 rubrik (1 hesaplama Flesch + 6 LLM) | LLM ağırlıklı |

**PaperMind farkı:** ESTRA (7 boyutlu hesaplama) + Validator (literatür metrikleri) + LLM (semantik) + alan norm kalibrasyonu → rakiplerin hiçbirinde olmayan hibrit derinlik.

---

## MVP SCOPE ETKİSİ

| Karar | MVP Etkisi | Ek Effort |
|-------|-----------|-----------|
| Chat-first hybrid | F4-S2 scope değişir | ~3 gün |
| Proje yapısı | Yeni migration + routing | ~3 gün |
| Karar hafızası | project_decisions tablosu | ~1 gün |
| Akıllı yönlendirme butonları | PaperCard genişler | ~1 gün |
| ESTRA Validator pipeline | Yeni doğrulama fazı | ~8-11 gün (V0-V4) |
| 3 seviyeli girdi | Pipeline modülerleştirme | ~2 gün |
| **Toplam ek effort** | | **~18-21 gün** |

**Not:** ESTRA doğrulama (V0-V4) MVP'ye paralel çalışabilir — kod geliştirme durdurmaz. 30K tam metin üzerinde batch hesaplama Colab'da arka planda koşar.

---

## KONSEY DEĞERLENDİRME SORULARI

Her konsey üyesi aşağıdaki soruları değerlendirsin:

| # | Soru | Seçenekler |
|---|------|-----------|
| 1 | Chat-first hybrid onaylanır mı? | GREEN / YELLOW (revize) / RED (reddet) |
| 2 | Proje yapısı MVP'ye mi girer? | MVP / Post-MVP |
| 3 | Karar hafızası (project_decisions) onaylanır mı? | GREEN / YELLOW / RED |
| 4 | r-ESTRA GLOBAL kalır mı? | GLOBAL / Proje bazlı |
| 5 | İki ürün hattı (Core + Simülasyon) onaylanır mı? | GREEN / YELLOW / RED |
| 6 | İki katmanlı tier doğru mu? | GREEN / YELLOW / RED |
| 7 | ESTRA + Validator çift katman mimarisi onaylanır mı? | GREEN / YELLOW / RED |
| 8 | Doğrulama protokolü (V0-V4) yeterli mi? | GREEN / YELLOW / RED |
| 9 | 3 seviyeli girdi (tam metin / özet / metadata) onaylanır mı? | GREEN / YELLOW / RED |
| 10 | Makale vs tez ayrımı doğru mu? | GREEN / YELLOW / RED |
| 11 | Tez verisi toplama planı (5K, YÖK önce) onaylanır mı? | GREEN / YELLOW / RED |
| 12 | Akıllı yönlendirme butonları MVP'de mi? | MVP / Post-MVP |
| 13 | Toplam ek effort (~18-21 gün) kabul edilebilir mi? | EVET / HAYIR (kapsam daralt) |
| 14 | Hat 2 modül sıralaması doğru mu? | GREEN / YELLOW / RED |

---

## ÖNCELİK SIRASI (öneri)

```
1. Core PaperMind (Hat 1) MVP
   ├── Supabase altyapı tamamla (Faz 2 + Faz 3)
   ├── Chat-first hybrid
   ├── Proje yapısı + karar hafızası
   ├── ESTRA doğrulama (V0-V4, paralel)
   └── Akıllı yönlendirme butonları

2. Kalibrasyon
   ├── 500 makale gold standard
   ├── Validator API entegrasyonu (iCite, SCImago)
   ├── Consistency check kuralları
   └── Alan norm tabloları

3. Tez Genişlemesi
   ├── YÖK Tez Merkezi veri toplama
   ├── Tez-spesifik ESTRA + Validator
   └── YL vs DR norm tabloları

4. Hat 2 (Post-MVP)
   ├── Yayın hazırlık pipeline (makale + tez)
   ├── Savunma + hakemlik simülasyonu
   └── Danışman/hakem/editör eğitimi
```

---

## GÜNCELLENECEK DOSYALAR (konsey onayı sonrası)

| Dosya | Güncelleme |
|-------|-----------|
| `docs/DECISIONS.md` | B-021 + DM-017..DM-021 + yeni OPEN kararları |
| `docs/STATE.md` | Pivot kararları + ek effort yansıması |
| `docs/plans/RAKIP_ANALIZ_VE_PIVOT.md` | §8 ESTRA+Validator eklenir |
| `docs/plans/F4_frontend_skeleton_arama.md` | Chat-first hybrid revizesi |
| `docs/PaperMind_Is_Plani.xlsx` | Yeni satırlar (V0-V4 + tez + validator) |
| `docs/ARCHITECTURE.md` | Çift katman mimari güncelleme |
| Memory dosyaları | Pivot kararları kalıcı kayıt |

---

> **Bu doküman konsey değerlendirmesi içindir. Nihai karar Omer'in hakemliğinde alınır.**
