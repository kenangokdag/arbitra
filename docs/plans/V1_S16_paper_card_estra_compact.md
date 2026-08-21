# V1-S16 — PaperCard ESTRA Render + Kompakt Varyant (B1+B2)

**Sub-sprint kodu:** V1-S16
**Önkoşullar:** V1-S14 mock-to-live KAPALI; aktif env'de `signals_13` backend dolu dönüyor (4 metrik canlı, 9 stub B5'e ait — bu plan **dışında**).
**Plan tarihi:** 2026-05-26
**Tek doğruluk kaynağı:** Bu manifest
**Onay:** BEKLİYOR (Omer "plan onaylandı" / "V1-S16 başla")
**Branch:** mevcut working branch üzerinde devam (push timing Omer kontrolünde, B-014 Hibrit)

---

## §0 — Amaç

Kullanıcının canlı şikâyeti (2026-05-26): "estra skorları görünmüyor" + "2. paper card olarak ben bunun küçük halini kurmuştum kafamda".

2 ayrık iş tek pakette:
- **B1** — `PaperCard.tsx` ESTRA render: `signals_13` payload'da dolu ama UI'da hiç gösterilmiyor; akademisyenin kararını besleyen sinyal kart yüzünde olmalı.
- **B2** — Liste görünümlerinde (`(app)/search`, `(app)/page.tsx`) büyük kart yerine kompakt varyant. Detay (paper detail / projeye dönüştür akışı) tam kartı görür.

**Plan dışı (ayrı iş):**
- B3 cache repro (kullanıcı tekrar üretecek)
- B4 bibliyometri seed paper akışı
- B5 backend signals_13 9 stub metriği (BC/TSP/RS/Ck/EDk/Ravg/SB/DI/sleeping_beauty) — ESTRA scorer F9 P096 kapsamı.

---

## §1 — Mevcut durum (envanter — kanıtla okundu)

### Backend payload — kanıt
```
GET /api/search "eğitim bilimleri"
signals_13: {'Q_weak': 1.92, 'MQ_Tier1': 1.73, 'CD5': 1.0,
             'sentence_role_RES': 1.72,
             'sleeping_beauty': 0, 'DI': 0, 'SB': 0, 'Ravg': 0,
             'RS': 0, 'Ck': 0, 'EDk': 0, 'BC': 0, 'TSP': 0}
```
4 metrik canlı (Q_weak / MQ_Tier1 / CD5 / sentence_role_RES) + 9 sıfır (backend stub).

### PaperCard.tsx envanteri (296 satır)
- `web/src/components/PaperCard.tsx:64-296` — büyük varyant
- Render: chip satırı (OA / dil / decision_band) → başlık → meta → 3-satır abstract → özet kutusu (koşullu) → **6 action** (Detay/Listeme/Özetle/Sohbet/Nota ekle/Danışmana sor)
- `signals_13` hiç tüketilmiyor (Grep: 0 match)
- `compact` prop YOK
- Type: `web/src/lib/types.ts:40-58` — `signals_13: Record<string, number>` mevcut, tüm dosyada yalnız `web/src/components/JourneyProgress.tsx`'ta kullanılır (farklı bağlam)

### PaperCardLite.tsx envanteri (227 satır)
- Farklı şema (`PaperCardLiteData`: id/title/authors/venue/volume/year/doi/is_open_access/source/scholar_url)
- `decision_band` / `signals_13` YOK
- `(app)` altında HİÇ kullanılmıyor — sadece marketing/demo
- **Karar (KD-V1-S16-02 aşağıda):** `compact` prop'u `PaperCard.tsx`'a ekle, `PaperCardLite.tsx`'a dokunma (silme önerisi şu an YOK — eski demo halen import edebilir).

### Kullanım yerleri (Grep kanıtı)
- `web/src/app/(app)/search/page.tsx:8,176` — `<PaperCard paper={paper} />` (büyük)
- `web/src/app/(app)/page.tsx:10,157` — `<PaperCard key={paper.paper_id} paper={paper} />` (büyük)
- `web/src/app/(marketing)/demo/page.tsx:129,463,678,740` — yerel `PaperCard` ayrı bileşen + `compact` prop pattern referansı (kopyalanmayacak, sadece görsel referans)

### EstraBars.tsx envanteri (referans için arandı)
- `web/src/components/EstraBars.tsx` mevcut (V1_S13 plan §1 referansı): D/W/S/T bar pattern.
- **Karar (KD-V1-S16-03):** ESTRA chip için EstraBars **reuse YOK** — farklı sinyal seti (D/W/S/T ≠ Q_weak/MQ_Tier1/CD5/RES). PaperCard'a yerel mini-chip strip yazılır.

---

## §2 — Hedef çıktı

### B1 — ESTRA chip strip (yeni)
`PaperCard.tsx` chip satırının altında / başlığın hemen üstünde **4 mini chip**:

| Etiket UI | signals_13 anahtarı | Renk eşiği |
|---|---|---|
| Kalite (Q) | `Q_weak` | ≥1.5 emerald · 1.0–1.5 amber · <1.0 stone |
| Yöntem (M) | `MQ_Tier1` | ≥1.5 emerald · 1.0–1.5 amber · <1.0 stone |
| Atıf Δ5y | `CD5` | ≥1.0 emerald · 0.5–1.0 amber · <0.5 stone |
| Bulgu (R) | `sentence_role_RES` | ≥1.5 emerald · 1.0–1.5 amber · <1.0 stone |

- Format: `<harf chip>` 2 karakter ikon + 1 ondalık sayı (`Q 1.9`, `M 1.7`, `Δ5 1.0`, `R 1.7`)
- Hover: native `title=` ile tam açıklama (örn. "Q_weak = 1.92 — kalite zayıf sinyal skoru"). Popover YOK (V1-S13 KD-02 pattern: bar üstü hover = native title).
- 9 sıfır metrik PaperCard'da **gösterilmez** (B5 backend stub iken görsel kirlilik yapar).
- Sıfır olan canlı metrik (örn. CD5=0) chip stone tonunda görünür — eksik değil, "düşük" sinyali.

### B2 — `compact` prop
`PaperCard.tsx` imzaya `compact?: boolean = false` eklenir. `true` iken fark:

| Bölüm | full | compact |
|---|---|---|
| chip satırı (OA/dil/band) | ✅ | ✅ |
| ESTRA chip strip (B1) | ✅ | ✅ |
| başlık (Lora 17px) | ✅ | ✅ (15px) |
| meta satırı | ✅ | ✅ (tek satır truncate) |
| abstract excerpt 3-line | ✅ | **YOK** |
| özet kutusu (summarize sonucu) | ✅ | **YOK** (compact iken summarize aksiyonu da yok) |
| 6 action butonu | ✅ | sadece **3:** Detay · Listeme · Sohbet |
| padding | `p-5` | `p-3.5` |

Demo zaten compact pattern uyguluyor (`demo/page.tsx:463`) — görsel parite referans.

### Kullanım swap
- `(app)/search/page.tsx:176` → `<PaperCard paper={paper} compact />`
- `(app)/page.tsx:157` → `<PaperCard paper={paper} compact />`
- Diğer (paper detail / projeye dönüştür sonrası) varsa **dokunulmaz** — full kalır.

---

## §3 — Yol kararları (KD-V1-S16-NN)

### KD-V1-S16-01 — ESTRA chip = renderer-only, scorer DEĞİL
B1 sadece backend'in döndürdüğü `signals_13`'ü render eder. Threshold mantığı sabit/lokal (yukarıdaki tablo). Backend'de threshold değişimi → bu tabloyu güncelleriz, scorer logic frontend'de YOK.

### KD-V1-S16-02 — `compact` prop, ayrı bileşen DEĞİL
İki kart yerine tek `PaperCard.tsx` + `compact` boolean. Sebep: state/mutation/imza tek yerde kalır; demo'da kanıtlı pattern.

`PaperCardLite.tsx` **silinmez** — eski demo bağımlılığı + farklı şema (PaperCardLiteData). Ayrı KD: V1-S17+ değerlendirme.

### KD-V1-S16-03 — `EstraBars.tsx` reuse YOK
Farklı sinyal seti. Bağımsız yeni mini bileşen `<EstraChips signals={signals_13} />` PaperCard içinde inline yazılır (yeni dosya yaratma, ~30 LOC inline).

### KD-V1-S16-04 — 9 sıfır metrik gizli
B5 (backend scorer) tamamlanana kadar 9 stub metrik PaperCard'da gösterilmez. B5 KAPALI'da bu plan revize olur (`§2 B1` tablosu 13'e çıkar).

### KD-V1-S16-05 — Compact'ta `is_ghost` ve özet kutusu kuralı
`isGhost` chip (Klasik kaynak rozeti) compact'ta da görünür (akademisyen sinyali, küçük). Özet kutusu (summarize sonucu) compact'ta render YOK çünkü summarize butonu compact'ta hiç gözükmüyor.

### KD-V1-S16-06 — Push timing Hibrit
Lokal commit zinciri yazılır. Push timing Omer kontrolünde (B-014).

---

## §4 — Atomik commit boundary (R13.13 build PASS empirik kanıt)

| # | Commit | Kapsam | Yeni LOC (~) |
|---|---|---|---|
| P001 | `feat(web): EstraChips strip inline + 4 active signals` | `PaperCard.tsx` içinde inline `EstraChips` fonksiyon bileşeni + 4 chip + threshold renk + native title hover | 60 |
| P002 | `feat(web): PaperCard compact variant` | `compact?: boolean` prop + conditional render (abstract gizle / aksiyon 3 / padding küçült / başlık 15px) | 70 |
| P003 | `chore(web): switch list views to compact PaperCard` | `(app)/search/page.tsx:176` + `(app)/page.tsx:157` swap; smoke browser kanıt | 10 |
| P004 | `test(web): PaperCard EstraChips + compact snapshot` | Vitest 6 test: chip render / threshold renk / compact 3 aksiyon / abstract gizli / full default / ghost compact | 100 |

**Toplam:** ~240 LOC, 4 atomik commit, ~3-4h.

**Her commit öncesi (R13.13):**
```
cd web && npm run build 2>&1 | tail -3
cd web && npx tsc --noEmit 2>&1 | tail -3
cd web && npx vitest run 2>&1 | tail -5
```
PASS log commit body'sinde inline.

---

## §5 — Test / kanıt

### Vitest (P004)
- `web/src/components/PaperCard.test.tsx` (yeni dosya — Glob ile yokluğu doğrulandı)
- T1: full default render → abstract DOM'da
- T2: `compact` true → abstract YOK · aksiyon sayısı 3 (Detay/Listeme/Sohbet)
- T3: EstraChips strip render → 4 chip (Q/M/Δ5/R)
- T4: Threshold rengi: Q_weak=1.92 → emerald class · Q_weak=0.5 → stone class
- T5: signals_13 boş objesi → strip render etmez (graceful)
- T6: `isGhost` + `compact` → "Klasik kaynak" rozeti hâlâ DOM'da

### Browser smoke (Omer, sprint sonu)
1. `cd web && npm run dev` → `http://localhost:3000`
2. `/` ana sayfa: 5 önerilen kart → her biri kompakt + ESTRA chip strip görünür
3. `/search` "eğitim bilimleri" → liste kompakt + ESTRA chip
4. Bir karta tıkla → `/paper/W…` (detail sayfası) → full PaperCard (varsa) abstract + 6 aksiyon
5. Hover bir chip'in üstüne → native tooltip "Q_weak = …" görünür
6. `signals_13` tüm sıfır olsa (mock test) → 4 chip görünür, hepsi stone (graceful)

### Empirik kanıt R13.13
- `next build` exit 0 + son 3 satır commit body'sinde
- `tsc --noEmit` exit 0
- vitest tüm test PASS sayısı commit body'sinde

---

## §6 — Risk

1. **Liste yoğunluğunda chip kalabalığı** — Compact varyantta chip satırı 3 + ESTRA chip 4 = 7 chip. Tek satırda taşmazsa OK; taşarsa `flex-wrap` ile alt satıra düşer. Browser smoke #2'de doğrula. Eğer kalabalık → ESTRA stripi rounded badge yerine ince bar'a indir (P005 revize commit).
2. **`signals_13` partial null** — Bazı paper'larda backend `Q_weak` döndürmezse undefined → NaN render. **Fix:** `signals.Q_weak ?? 0` defansif. T5 testle örtülü.
3. **Mevcut paper detay sayfası kırılır mı?** — Detail sayfası `PaperCard` kullanıyorsa ve `compact` default false ise dokunulmamış olur. Grep ile doğrula:
   `Grep "PaperCard" web/src/app/(app)/paper/` → eğer kullanmıyorsa zaten etkilenmiyor.
4. **Demo (marketing) etkilenmez** — Marketing demo'daki `PaperCard` yerel bileşen, bu repo'nun `web/src/components/PaperCard.tsx`'ı değil; risk yok.
5. **Bundle size delta** — Yeni LOC ~240, framework dependency YOK. Bundle delta ihmal edilebilir.

---

## §7 — Closure kriterleri

1. ✅ P001 + P002 + P003 + P004 commit hash'leri NEXT_ACTION.md'ye işlendi
2. ✅ Her commit body'sinde build PASS son 3 satır (R13.13)
3. ✅ Vitest yeni 6 test PASS (mevcut testler regress YOK)
4. ✅ Omer browser smoke 6 adım PASS (§5)
5. ✅ Bu manifest'in §6 risklerinden hiçbiri açık değil (taşma çözüldü, partial null defansif eklendi)

Closure sonrası bu dosya `## §8 — Sonuç` bloğuyla mühürlenir, NEXT_ACTION'da B5 (backend scorer) sıraya alınır.

---

## §8 — Uyum sinyali (executor için)

Bu plan'ı uygulayan oturum başlamadan önce **uyum sinyali checklist**:

- [ ] Plan başlık `V1-S16 — PaperCard ESTRA Render + Kompakt Varyant (B1+B2)` mı?
- [ ] §2 B1 tablosu **4 metrik** mi (Q_weak/MQ_Tier1/CD5/sentence_role_RES)? 13 değil.
- [ ] §3 KD-V1-S16-02: `compact` prop **aynı bileşende**, ayrı bileşen DEĞİL.
- [ ] §4 4 atomik commit (P001..P004), 5+ değil.

Bu 4 maddenin biri farklıysa executor STOP, plan revize edilmiş demektir, yeniden onay alınmalı.
