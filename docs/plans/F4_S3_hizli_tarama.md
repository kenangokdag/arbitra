# F4-S3 — Hizli Tarama (OpenAlex + arXiv Canli Arama + Yan Panel Okuma)

> **Durum:** TASLAK — Council 37 onayi bekliyor
> **Son guncelleme:** 2026-05-01
> **Onkosul:** F4-S2 KAPANDI (Chat-First + Karar Hafizasi + 10 atom shadcn)
> **Branch:** `feat/F4-frontend-shell` ustune devam
> **Sprint LOC tahmini:** ~850-1000
> **Sprint sure tahmini:** 3-4 gun

---

## S0 — Nedir / Ne Degildir

**Nedir:**
- ESTRA'dan BAGIMSIZ, canli API arama motoru
- Kullanici keyword + filtre secer, OpenAlex / arXiv API'sine canli sorgu gider
- 50 veya 100 makale listelenir (PaperCard formatinda)
- Publish or Perish benzeri hizli tarama araci
- Proje icinde bir sayfa/tab olarak oturur
- Acik erisim makaleleri yan panelde (Sheet) okunabilir — PDF reader entegre

**Ne degildir:**
- ESTRA skorlama, r-ESTRA profil, decision_band, signals_13 — HICBIRI UYGULANMAZ
- Bizim 24.87M corpus'tan arama degil — canli dis kaynak
- Oneri motoru degil — saf arama motoru
- Hat 2 (simulasyon) ile ilgisi yok

---

## S1 — Hedef

Kullanici proje icinde "Hizli Tarama" sayfasina girer. Keyword yazar, filtreleri secer (dil, yil, tur, siralama, acik erisim), kaynak secer (OpenAlex / arXiv). 50 veya 100 makale listelenir. Acik erisim makalelerde [Oku] butonuna tiklar, sag tarafta Sheet paneli acilir, PDF dogrudan panelde goruntulenir. Kullanici begendiklerini Okuma Listesi'ne ekler veya DOI/Scholar linkine gider.

**Kullanici akisi:**
```
Proje icinde sidebar: "Hizli Tarama" (Globe icon)
    |
    v
Keyword input + Filtre paneli:
    - Kaynak:      [OpenAlex] [arXiv] [Ikisi]
    - Dil:         [Tumumu] [Turkce] [Ingilizce] [Almanca] [Fransizca] ...
    - Yil:         [Tum yillar] [Son 5 yil] [Son 10 yil] [Ozel aralik]
    - Tur:         [Makale] [Review] [Konferans] [Preprint] [Hepsi]
    - Siralama:    [Atif sayisi] [Yeni -> Eski] [Ilgililik]
    - Acik erisim: [Hepsi] [Sadece OA]
    - Sonuc sayisi: [50] [100]
    |
    v
[Ara] butonu
    |
    v
Sonuc listesi (PaperCard-lite):
    - Baslik, Yazarlar, Dergi, Yil, Atif
    - [Dil badge] [OA badge] [Tur badge]
    - [Oku] [Listeme Ekle] [DOI Link] [Google Akademik] [Atif Kopyala]
    |
    v  (kullanici [Oku] tiklar)
    |
    v
Sag yan panel (Sheet) acilir:
    +------------------------------------------+---------------------------+
    |  Sonuc listesi (daraltilmis)             |  PDF Reader Panel         |
    |  [PaperCard-lite] x N                    |                           |
    |                                          |  Baslik + Yazar + Yil     |
    |                                          |  ─────────────────────    |
    |                                          |  [PDF sayfasi render]     |
    |                                          |  Sayfa: < 3 / 18 >       |
    |                                          |                           |
    |                                          |  [Tam ekran] [Indir]      |
    |                                          |  [Listeme Ekle]           |
    +------------------------------------------+---------------------------+
```

**arXiv siniri:** OpenAlex ana kaynak. arXiv'ten max 2 makale (en guncel preprint — "taze sinyal").

---

## S2 — Teknik Mimari

### 2.1 Backend Endpoint — Arama

**`POST /api/explore`** — canli dis kaynak arama proxy

```python
# Request
{
  "query": "MCDM education higher education",
  "source": "openalex" | "arxiv" | "both",
  "language": "tr" | "en" | "de" | "fr" | null,  # null = tum diller
  "year_from": 2020,           # null = tum yillar
  "year_to": 2026,             # null = tum yillar
  "type": "article" | "review" | "proceedings" | "preprint" | null,
  "sort": "cited_by_count" | "publication_date" | "relevance_score",
  "open_access": false,        # true = sadece OA
  "per_page": 50               # 50 veya 100
}

# Response
{
  "results": [
    {
      "id": "W1234567890",
      "source": "openalex",
      "title": "Multi-Criteria Decision...",
      "authors": ["A. Yilmaz", "B. Demir"],
      "journal": "European Journal of...",
      "year": 2024,
      "cited_by_count": 45,
      "language": "en",
      "type": "article",
      "doi": "10.1016/j.ejor.2024.01.001",
      "url": "https://doi.org/10.1016/...",
      "is_oa": true,
      "oa_url": "https://...",
      "abstract_snippet": "This study..."
    }
  ],
  "total_count": 1523,
  "query_time_ms": 1200,
  "sources_queried": ["openalex"]
}
```

### 2.2 Backend Endpoint — PDF Proxy

**`GET /api/explore/pdf-proxy?url=<encoded_url>`** — CORS-free PDF stream

```python
# Guvenlik: sadece whitelist domain'lerden PDF cekilir
ALLOWED_DOMAINS = [
    "arxiv.org",
    "europepmc.org",
    "ncbi.nlm.nih.gov",       # PubMed Central
    "repository.*.edu",        # universite repo'lari (wildcard)
    "hal.science",             # Fransiz acik arsiv
    "jstage.jst.go.jp",       # Japon acik erisim
    "scielo.org",              # Latin Amerika acik erisim
    "doaj.org",                # Directory of Open Access Journals
]

# Akis:
# 1. URL domain whitelist kontrolu — reject edilirse 403
# 2. httpx.AsyncClient GET (stream=True, timeout=30s)
# 3. Content-Type kontrolu: application/pdf olmalidir
# 4. Max boyut: 50 MB (akademik makale genelde 1-10 MB)
# 5. Response: streaming binary (frontend'e chunk chunk)

# Ornek:
# GET /api/explore/pdf-proxy?url=https%3A%2F%2Farxiv.org%2Fpdf%2F2401.12345
# Response: application/pdf binary stream
```

**Neden proxy gerekli:**
- Yayinci siteleri CORS header gondermez — frontend iframe/fetch ile PDF alamaz
- Backend server-side istek yapar, CORS sorunu olmaz
- Whitelist ile guvenlik saglenir (arbitrary URL fetch engellenir)
- Stream ile bellek verimli (tum PDF RAM'e yuklenmez)

### 2.3 OpenAlex API Entegrasyonu

```python
filters = []
if language:
    filters.append(f"language:{language}")
if year_from:
    filters.append(f"from_publication_date:{year_from}-01-01")
if year_to:
    filters.append(f"to_publication_date:{year_to}-12-31")
if type:
    filters.append(f"type:{type}")
if open_access:
    filters.append("is_oa:true")

params = {
    "search": query,
    "filter": ",".join(filters),
    "sort": sort,
    "per_page": per_page,
    "mailto": "ofrencber@gantep.edu.tr"  # polite pool
}

# GET https://api.openalex.org/works?{params}
```

**OpenAlex dil kodlari:** ISO 639-1 (`tr`, `en`, `de`, `fr`, `es`, `ar`, `zh`, `ja`, `ko`, `pt`, `ru`, `id`)
**OpenAlex type degerleri:** `article`, `review`, `book-chapter`, `proceedings-article`, `preprint`, `dataset`
**OpenAlex sort degerleri:** `cited_by_count:desc`, `publication_date:desc`, `relevance_score:desc`

### 2.4 arXiv API Entegrasyonu

```python
# arXiv API (Atom feed)
# GET http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=2&sortBy=submittedDate&sortOrder=descending

# arXiv sinirliliklari:
# - Dil filtresi YOK (arXiv cogunlukla Ingilizce)
# - Atif sayisi YOK (arXiv metadata'sinda yok)
# - Type: her zaman preprint
# - Rate limit: 1 istek / 3 saniye (politeness)
# - Max 2 sonuc (taze sinyal, ana kaynak degil)

# arXiv PDF URL: https://arxiv.org/pdf/{arxiv_id} — dogrudan erisim, CORS yok
```

**arXiv + OpenAlex birlesim (source="both"):**
1. Iki API'ye paralel istek (`asyncio.gather`)
2. arXiv max 2 sonuc
3. Sonuclari birlestir (duplicate DOI/baslik kontrolu)
4. Ortak formata normalize et
5. arXiv sonuclari listenin basina eklenir (preprint etiketi ile)

### 2.5 Frontend Route + PDF Reader Panel

- **Route:** `/explore` (sidebar'da "Hizli Tarama" adi)
- **Sidebar ikonu:** `Globe` (Lucide) — dis kaynak aramasi oldugunu ima eder

**Sayfa yapisi (normal):**
```
PageHeader: "Hizli Tarama" (Lora italic)
Hint banner: "OpenAlex ve arXiv'ten canli arama yapin, acik erisim makaleleri dogrudan okuyun."

[Keyword input] ................ [Ara butonu]

Filtre paneli (collapsible, varsayilan acik):
  Kaynak | Dil | Yil | Tur | Siralama | OA | Sonuc sayisi

Sonuc listesi:
  Toplam: 1,523 sonuc (0.8 saniye) — [OpenAlex'ten]

  [PaperCard-lite] x 50/100
```

**Sayfa yapisi (PDF paneli acik — Sheet side="right" width="55%"):**
```
+--- Sol %45 ----------------------------+--- Sag %55 (Sheet) ------------------+
|                                        |                                      |
| Sonuc listesi (scroll korunur)         | [X Kapat]                            |
|                                        |                                      |
| [PaperCard-lite aktif vurgulu]         | Baslik (Lora 17px)                   |
| [PaperCard-lite]                       | Yazarlar | Dergi | Yil              |
| [PaperCard-lite]                       | ──────────────────────────────────── |
| [PaperCard-lite]                       |                                      |
| ...                                    | [PDF render — react-pdf]             |
|                                        | Sayfa gorunumu tam genislik          |
|                                        |                                      |
|                                        |                                      |
|                                        | ──────────────────────────────────── |
|                                        | Sayfa: [<] 3 / 18 [>]               |
|                                        | [Tam Ekran] [Indir] [Listeme Ekle]  |
+----------------------------------------+--------------------------------------+
```

### 2.6 PDF Reader Bileseni

**Teknoloji:** `react-pdf` (pdfjs-dist tabanli)
- Lazy load: Sheet acilinca dynamic import (`next/dynamic` + `ssr: false`)
- Bundle etkisi: ~300KB (lazy, ana sayfa etkilenmez)

**Ozellikler:**
- Sayfa sayfa gorunum (tek sayfa gorunur, < > ile gecis)
- Sayfa numarasi gosterge: "Sayfa 3 / 18"
- Zoom: %100 varsayilan, pinch-to-zoom mobilde
- Tam ekran: Sheet'ten cikar, tam ekran modal (`Dialog` reuse)
- Indir: `<a download>` ile PDF indirme (proxy URL'den)
- Yukleniyor: Skeleton + progress bar (PDF boyutuna gore)

**3 katmanli fallback:**
1. `oa_url` varsa → PDF proxy uzerinden react-pdf render
2. `oa_url` yoksa ama `abstract_snippet` varsa → abstract tam metin goster + "Bu makaleye acik erisim yok" uyarisi
3. Hicbiri yoksa → "Bu makale acik erisimde degil" + [DOI Link] butonu (yayinci sayfasina yonlendirme)

**OA olmayan makalelerde [Oku] butonu durumu:**
- `is_oa: true` → [Oku] butonu aktif (yesil vurgu)
- `is_oa: false` → [Oku] butonu disabled + tooltip "Acik erisim degil — DOI ile yayinciya gidin"

### 2.7 PaperCard-Lite Bileseni

Mevcut PaperCard'in sadelesilmis versiyonu (ESTRA yok):

| PaperCard (tam) | PaperCard-Lite (Hizli Tarama) |
|---|---|
| decision_band stripe | YOK |
| 13 sinyal chip | YOK |
| ESTRA skor | YOK |
| 6 action (Detay/Listeme/Ozetle/Sohbet/Nota/Danismana) | 5 action (Oku/Listeme/DOI/Scholar/Atif) |
| Karar butonu (accept/reject/bookmark/note) | YOK (sadece Listeme Ekle) |
| 3-line abstract | abstract_snippet (2 satir) |
| Hover lift + shadow | Ayni |
| Chip semantic renkler | Dil + OA + Tur badge'leri |

**Reuse:** PaperCard'in `variant="lite"` prop'u ile calisir — ayri component DEGIL. Kod tekrari yasak.

**[Oku] butonu:**
- OA makalelerde: `BookOpen` ikonu (Lucide) + yesil accent
- OA olmayan makalelerde: disabled, gri, tooltip aciklama
- Tiklaninca: Sheet acilir, PDF proxy'den yuklenir

---

## S3 — Atomic Commit Boundary

| # | P-no | Slice | LOC | Dosya |
|---|---|---|---|---|
| 1 | P073 | Backend `/api/explore` endpoint + OpenAlex proxy + Pydantic models | ~150 | `api/routes/explore.py` + `api/models/explore.py` + `api/services/openalex_client.py` |
| 2 | P074 | Backend arXiv proxy (max 2 sonuc) + birlesim + duplicate dedup | ~80 | `api/services/arxiv_client.py` + `api/services/explore_service.py` |
| 3 | P075 | Backend PDF proxy endpoint + domain whitelist + stream | ~80 | `api/routes/explore.py` (edit) + `api/services/pdf_proxy.py` |
| 4 | P076 | Frontend `/explore` route + PageHeader + Hint banner + keyword input | ~80 | `web/src/app/explore/page.tsx` |
| 5 | P077 | ExploreFilters component (kaynak/dil/yil/tur/siralama/OA/sonuc) | ~120 | `web/src/components/ExploreFilters.tsx` |
| 6 | P078 | PaperCard `variant="lite"` prop + [Oku] butonu + badge'ler (dil/OA/tur) | ~70 | `web/src/components/PaperCard.tsx` (edit) |
| 7 | P079 | PdfReaderPanel (react-pdf + Sheet + sayfa gecis + fallback 3 katman) | ~150 | `web/src/components/PdfReaderPanel.tsx` |
| 8 | P080 | Explore page wiring (Zustand store + apiFetchOrFixture + 501 fallback + SearchPending reuse + Sheet state) | ~110 | `web/src/stores/explore.ts` + `web/src/app/explore/page.tsx` (edit) |
| 9 | P081 | Sidebar nav ekleme + fixture + integration test | ~50 | `web/src/config/nav.ts` (edit) + `web/src/fixtures/explore_demo.json` + test |
| 10 | docs | F4-S3 closure + B-024 entry | ~ | docs/* |

**Toplam: ~890 LOC + docs**

---

## S4 — Halusinasyon Kod-Seviyesi (HK)

- **HK-1:** OpenAlex API field ID'leri NUMERIK olmali (URL degil). `primary_topic.field.id:33` = dogru, `https://openalex.org/fields/33` = YANLIS (0 sonuc doner). Empirik kanit: 2026-05-01 Colab notebook hata ve duzeltme.
- **HK-2:** arXiv rate limit 1 req/3s — backend'de `asyncio.sleep(3)` arXiv istekleri arasinda.
- **HK-3:** OpenAlex `language` field'i **yayin dili**. Kullanici kendi dilinde makale okumak icin bu filtre kullanir. UI'da acikca: "Yayin dili secin — sectiginiz dilde yayimlanmis makaleler listelenir."
- **HK-4:** Turkce yayin sayisi dusuk olabilir — sonuc 0 ise "Bu dilde sonuc bulunamadi. Ingilizce'de X sonuc var." fallback mesaji.
- **HK-5:** OpenAlex polite pool = mailto parametresi — 3 .edu.tr adresten birini kullan.
- **HK-6:** PDF proxy guvenlik — whitelist disindaki domain'ler 403 doner. Arbitrary URL fetch YASAK (SSRF onleme).
- **HK-7:** react-pdf lazy load — ana sayfa bundle'i etkilenmez. `next/dynamic` + `ssr: false` zorunlu (pdfjs-dist server-side calismaz).
- **HK-8:** Buyuk PDF'ler (50+ MB) timeout olabilir — proxy'de 30s timeout + 50 MB max limit. Akademik makaleler genelde 1-10 MB, 20 sayfa altinda.

---

## S5 — Council 37 (R13)

**Alan:** Frontend + Backend (hibrit sprint)
**Alan sahibi (BAGLAYICI):** Defne Yildiz (Frontend) + Sercan (Backend)

| # | Uye | Oy | Gerekce |
|---|---|---|---|
| 1 | Halusinasyon Avcisi | | OpenAlex numeric field ID empirik kanitli; PDF proxy whitelist SSRF onleme; HK-1..HK-8 tanimli |
| 2 | Akademik Isabet | | Publish or Perish benzeri arac akademisyen icin bilinen UX; dil filtresi = kendi dilinde okuma; yan panel okuma SciSpace pattern |
| 3 | Fayda-Maliyet | | ~890 LOC 3-4 gun; react-pdf ~300KB lazy load; PaperCard reuse; OpenAlex + arXiv API ucretsiz; PDF proxy ~80 LOC |
| 4 | Daha Iyisi Var Mi? | | react-pdf (pdfjs-dist) en yaygin PDF renderer; alternatif pdf.js embed (daha dusuk seviye, daha fazla is); Semantic Scholar post-MVP |
| 5 | Global Cozum | | PaperCard-Lite variant reuse; PdfReaderPanel Hat 2'de yeniden kullanilir (hakemlik + juri simulasyonu tam metin okuma); citation-format.ts reuse |
| 6 | Son Kullanici Avukati | | Dil filtresi = kendi dilinde okuma; yan panel = sayfa degistirmeden PDF okuma; 3 katman fallback = OA olmayanlara da aciklama |
| **A** | **Defne (Frontend, BAGLAYICI)** | | Sheet %55 genislik + PaperCard aktif vurgu + PDF sayfa gecis; 8-anatomi uyumlu; BookOpen ikonu OA vurgu |
| **S** | **Sercan (Backend)** | | PDF proxy basit (httpx stream + whitelist); arXiv max 2 sonuc mantikli; Redis cache explore sonuclari 1h |

**Sonuc:** Council 37 onayi bekleniyor.

---

## S6 — Done-of-Definition (DOD)

**P073-P075 Backend:**
- [ ] `POST /api/explore` 200 donuyor (OpenAlex query)
- [ ] arXiv query max 2 sonuc + birlesim (source="both") calisir
- [ ] Dil filtresi OpenAlex'te dogru sonuc dondurur (empirik: `language:tr` → Turkce makaleler)
- [ ] Rate limit arXiv 1 req/3s korunuyor
- [ ] Duplicate DOI dedup calisiyor (OpenAlex + arXiv birlesimde)
- [ ] `GET /api/explore/pdf-proxy` whitelist domain'den PDF stream doner
- [ ] Whitelist disi domain 403 doner (SSRF testi)
- [ ] 50 MB ustu PDF reject edilir
- [ ] Unit test: OpenAlex mock + arXiv mock + birlesim + dedup + PDF proxy whitelist

**P076-P081 Frontend:**
- [ ] `/explore` route sidebar'da gorunur ("Hizli Tarama" + Globe ikonu)
- [ ] Keyword input + 7 filtre calisiyor
- [ ] Kaynak secimi (OpenAlex / arXiv / ikisi) toggle
- [ ] Dil secimi dropdown (12+ dil)
- [ ] 501 fallback fixture + Hint banner "demo verisi"
- [ ] PaperCard variant="lite" render (ESTRA yok, 5 action: Oku/Listeme/DOI/Scholar/Atif)
- [ ] [Oku] butonu: OA → aktif (yesil BookOpen), degil → disabled + tooltip
- [ ] Sonuc 0 ise dil fallback mesaji ("Ingilizce'de X sonuc var")
- [ ] SearchPending reuse (pending state)
- [ ] Listeme Ekle → okuma listesine ekleme (toast onay)
- [ ] Sheet yan panel acilir (%55 genislik, sag tarafta)
- [ ] PdfReaderPanel: react-pdf ile PDF render (sayfa sayfa)
- [ ] Sayfa gecis: < > butonlari + "Sayfa 3 / 18" gosterge
- [ ] Tam ekran butonu (Dialog reuse)
- [ ] Indir butonu (`<a download>`)
- [ ] Fallback 2: OA degil + abstract varsa → abstract goster
- [ ] Fallback 3: OA degil + abstract yok → "Acik erisimde degil" + DOI link
- [ ] Lazy load: react-pdf `next/dynamic` + `ssr: false` (ana sayfa bundle etkilenmez)

---

## S7 — Yan Etki: Hat 2 Tam Metin Okuma Altyapisi

**PdfReaderPanel bileseni Hat 2 modullerinde dogrudan yeniden kullanilir:**

| Hat 2 Modulu | PdfReaderPanel Kullanimi |
|---|---|
| **Hakemlik Simulasyonu** | Kullanici makale draft'ini yukler → yan panelde goruntuler → hakem raporu yan panelde olusturulur (split view: sol PDF, sag rapor) |
| **Juri Simulasyonu (Tez Savunma Provasi)** | Kullanici tez PDF'ini yukler → yan panelde goruntuler → juri sorulari alt panelde listelenir |
| **Danismanlik Egitimi** | Ogrenci draft'i yan panelde → danismanlik senaryolari sol panelde |

**Bu sprint'te kurulan altyapi:**
1. `PdfReaderPanel.tsx` — genel amacli PDF goruntuleyici (sayfa gecis, zoom, tam ekran, indir)
2. `pdf_proxy.py` — backend PDF stream proxy (whitelist guvenlikli)
3. Sheet + PDF reader entegrasyon pattern'i — Hat 2'de ayni pattern tekrarlanir

**Hat 2'de ek olarak gerekecekler (F4-S3 scope'unda DEGIL):**
- PDF yukle (kullanici kendi dosyasini surukle-birak) → Supabase Storage
- PDF annotation (highlight + not birakma) → post-MVP
- Split view (sol PDF + sag rapor/soru) → Hat 2 sprint'inde

**Karar:** PdfReaderPanel'i simdiden iyi tasarla, Hat 2'de sadece ek prop'lar eklenir (ornek: `onPageChange` callback, `annotations` overlay, `splitMode` layout). Temel PDF render + sayfa gecis + fallback + proxy altyapisi **bir kez yazilir, her yerde kullanilir**.

---

## S8 — Baglantilar

- **F4-S2 plan:** Chat-first hybrid arama (ESTRA tabanli, bizim corpus) — FARKLI
- **RAKIP_ANALIZ_VE_PIVOT.md §6.1:** Hat 2 modulleri — tam metin okuma altyapisi buraya baglaniyor
- **RAKIP_ANALIZ_VE_PIVOT.md §6.2:** Akilli yonlendirme butonlari (DOI/Scholar/Atif) — REUSE
- **Colab notebook:** `scripts/colab_fulltext_fetch.ipynb` — OpenAlex API deneyimi (numeric field ID hatasi ve duzeltmesi)
- **OpenAlex API docs:** https://docs.openalex.org/api-entities/works
- **arXiv API docs:** https://info.arxiv.org/help/api/index.html
- **Master plan §1:** E4 Makale Ara = ESTRA tabanli; Hizli Tarama = dis kaynak tabanli — iki ayri ozellik
- **Memory:** project_pivot_decisions.md — Hat 2 moduller (hakemlik + juri + danismanlik)
