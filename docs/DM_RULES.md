# DM_RULES.md — Çalışma Kuralları (PaperMind App)

> **Bu dosya çalışma kanunudur.** Her oturumda Claude bu dosyayı okur ve uygular.
> **İhlal yasak.** Kullanıcı "yapalım" dese bile kurallar geçerli; tek istisna: kullanıcı açıkça "kuralı atla, riski biliyorum" der + kayıt altına alınır.

---

## R1 — KOD ÖNCESİ %100 PLAN (mutlak)

> Omer 2026-04-29 yazılı: *"her adımda %100 plan yapmadan sakın kod önerme ve yazma. önce plan."*

**Sırası:**
1. Faz başında **Plan Manifest** yazılır → `docs/plans/F<N>_<başlık>.md`
2. Plan Manifest §0..§18 yapısı (`reference/ARCHITECT_PROMPT_TEMPLATE.md`)
3. Omer **explicit onay** verir
4. Onay sonrası kod yazılır
5. Plan dışı edit YASAK — gerekirse plan revize

**Hard-stop:** Plan onayı yoksa Claude `Edit/Write` kullanmaz, sadece `Read/Grep/Glob`.

---

## R2 — 7 KONTROL (Omer'in karar çerçevesi — her öneride zorunlu)

> Omer 2026-04-29 yazılı: backend/frontend ne yaparsa yapsın 7 soru sorar. Claude öneri sunmadan ÖNCE 7'yi iç olarak cevaplar; herhangi biri "kırmızı" ise cevapta açıkça söyler. Atlama = R2 ihlali.

### K1 — Literatür
Sağlam akademik / endüstri kaynak ne diyor? Daha yeni veya daha kaliteli yaklaşım çıkmış mı? ("Yaygın" değil, "sağlam".)

### K2 — Halüsinasyon
Hayal mi görüyorum? Sayı / yol / eşik / fonksiyon / dosya gerçek mi (kanıt A/B/C)? Doğrulanmamışı "doğrulayamıyorum" diye açıkça yazıyor muyum? (R4 ile bağlı.)

### K3 — Fayda-maliyet
Küçük hesaplar mı yapıyorum? Somut metrik (süre, $, LOC, doğruluk, bakım) marj net pozitif mi? Marjinal kazanç için zaman yakıyor muyum?

### K4 — Daha kolayı
Bunu daha basit, daha az bağımlılıkla, daha az kodla yapmanın yolu var mı? Aşırı mühendislik mi yapıyorum?

### K5 — Son kullanıcı avantajı
Son kullanıcı (öğrenci / akademisyen) için gerçekten kazanç var mı, yoksa hayalimde mi koşuyorum? Onun zamanını / güvenini / kararını iyileştiriyor mu?

### K6 — Rakip karşılaştırma
SciSpace / Consensus / Elicit / Scite bunu nasıl yapıyor? Onlardan somut olarak nerede daha iyiyiz? "Aynı"sa yapma sebebimiz ne?

### K7 — Lokal mi global mi
Çözüm bu kullanıcı / bu sorgu / bu paper'a mı çalışıyor, yoksa tüm corpus + tüm dil + tüm alanlarda mı? **Omer her zaman global çözüm ister.** Lokal hack önerirken zorunlu uyarı + "geçici" etiketi + global maliyet.

### Çıktı kuralı
- Her K iç olarak cevaplanır; cevapta hepsini madde madde göstermek **zorunlu değil** ama herhangi biri kırmızıysa **mutlaka söylenir**.
- "Sycophant yasak" (R3) ile birleşir — "yapalım" dense bile 7-kontrol geçerli.
- Tek istisna: kullanıcı açıkça "7-kontrolü atla, riski biliyorum" der + kayıt.

---

## R3 — SYCOPHANT YASAK

- "Harika fikir!" / "Mükemmel" / "Çok güzel" yasak. Gerçekçi ve dürüst olacaksın
- Önerinin yan etkisini açıkça söyle. Gerçekten işe yarar mı bilmeli
- Daha iyisini öner ("X yerine X' nasıl? Şu maliyetle şu fayda") fayda maliyet analizi her zaman
- "Yapalım" dense bile R2 (3-kontrol) hâlâ uygulanır

---

## R4 — HALÜSİNASYON SIFIR (ESTRA Politikası §0 P4)

- Ölçemediğimizi yazmayız
- Plan 1'de ölçülemeyen sinyal Plan 2'ye ertelenir veya çıkarılır
- LVR validator zorunlu (her cümle paper_id+span ile doğrulanır)
- LVR_min_distance > τ → öneri OTOMATIK REJECT
- K1 ihlali (yıl tahmini gösterimi) → runtime fail

---

## R5 — KAYNAK HİYERARŞİSİ (B42-039 / L-013)

```
manifest_*.json  >  Pipeline_Akis.docx  >  ENVANTER.md  >  STATE.md  >  diğer md  >  memory
```

Çelişkide manifest galip. Docx alıntısı manifest doğrulaması olmadan B-evidence (kanıt sayılmaz).

---

## R6 — DOSYA YAZIM PROTOKOLÜ

### R6.1 — Yeni .md yazma
- ❌ Yeni `*.md` yazma; varolan dosyayı güncelle
- **İstisna 1:** Plan Manifest (`docs/plans/F<N>_<başlık>.md`) — her faz için yeni dosya
- **İstisna 2:** Runbook (`docs/runbook/<endpoint>_down.md`) — her runbook için yeni
- **İstisna 3:** Sprint plan (`docs/SPRINT_HISTORY.md`'ye append)

### R6.2 — STATE.md / DECISIONS.md güncelleme
- Önce ENVANTER (varsa) → sonra STATE → sonra DECISIONS → en son NEXT_ACTION
- Yeni karar yazılı Omer onayı olmadan EKLENMEZ

### R6.3 — `reference/` klasörü
- READ-ONLY. Edit/Write yasak.
- Değişiklik için Papermind_V2'ye gidilir, oradan kopyalanır.

---

## R7 — ATOMIC COMMIT BOUNDARY

- Her commit = bir slice = §8 ilgili test PASS
- Commit boundary plan manifest §6'da yazılı
- Plan dışı dosya edit denemesi → **STOP**, plan revize
- `git commit --no-verify` YASAK (pre-commit hook bypass)

---

## R8 — SABIT KURALLAR (B42-045 §12 K1-K15)

| K | Kural |
|---|---|
| K1 | Doğrulanmamış yıl gösterilmez |
| K2 | Tahmini segment `?` placeholder |
| K3 | Boş veriyle tam referans yok |
| K4 | LLM rank alanı yok (deterministik formül) |
| K5 | Cümle-düzey atıf zorunlu |
| K6 | PMID 12-segment sabit format `D.F.S.T1.T2.T3.Y.Q.I.L.R.V` |
| K7 | year_upper_bound arka plan, year_verified UI |
| K8 | Ghost n_corpus_citers ≥ 3 |
| K9 | confidence < 0.5 → segment `?` |
| K10 | BGE-M3 ana, BGE-reranker-v2-m3 reranker |
| K11 | TR FAIL fallback hazır |
| K12 | Ağırlıklar bootstrap, LightGBM Aşama 3 kalibre |
| K13 | Eval 330 stratified zorunlu |
| K14 | Pilot N=20 yeter, Faz 2 N≥150 |
| K15 | Tek doğruluk kaynağı DECISIONS B42-045, manifest hiyerarşisi |

---

## R9 — KALITE KAPILARI (üretim ship öncesi)

| Kapı | Eşik |
|---|---|
| JSON şema validation | %100 |
| MiniCheck NLI | ≥ 0.7 |
| ALCE citation-recall | ≥ 0.8 |
| End-to-end p50 | < 4s |
| End-to-end p95 | < 7s |
| Cache hit ratio | %70+ |
| Warm endpoint ratio | %95+ |

---

## R10 — ESTRA POLİTİKASI 5 PRENSİP (kullanıcı UX)

| # | Prensip |
|---|---|
| **P1** | Skorlar internal — kullanıcı sadece **karar bandı** görür (canon / frontier / kuvvetli kanıt / risk); "neden?" tıklarsa engineer-mode açılır |
| **P2** | Compensatory yerine gated + ağırlıklı (G1-G7 önce çalışır) |
| **P3** | Kalibrasyon veriden — uniform/bootstrap → LightGBM (Aşama 3) |
| **P4** | Halüsinasyon-sıfır — ölçemediğimizi yazmayız |
| **P5** | Plan 1 PASS olmadan Plan 2 yok |

---

## R11 — L-NNN DERSLERİ (CLAUDE_LESSONS aktif)

| Lesson | Kural |
|---|---|
| **L-013** | Manifest > docx hiyerarşi |
| **L-016** | stdout verdict ≠ disk write (3-yönlü hizalama: manifest mtime + log + state.json) |
| **L-017** | Stale-empty preflight + hard-fail-on-empty |
| **L-021** | `_norm_w` defansif normalize her `scan_parquet` sonrası (paper_id format mismatch silent corruption) |
| **L-022** | ENVANTER plan-time ≠ gerçek schema; `collect_schema()` zorunlu |
| **L-023** | Eşik kalibrasyon mutlak değil oran |
| **L-024** | Patch sonrası semantic gate zorunlu |

---

## R12 — RECOVERY PROTOKOLÜ

Kullanıcı "kafan karışıyor" / "savruluyorsun" / "dur" derse:
1. Dur — daha tool çağırma
2. Şu an ne yaptığımı + hangi karara dayandığını madde madde özetle
3. Her madde için STATE/DECISIONS/Plan Manifest'te hangi satıra dayandığını göster
4. Dayanağı olmayan maddeyi sil
5. Baştan başla

---

## R13 — COUNCIL PROTOKOLÜ (2026-04-30, B-004)

> **R13 = R2 (7-kontrol)'ün konsey halindeki sürümü.** R13 toplandığında R2 ayrıca yapılmaz; 6 üye R2 K1-K7'yi tamamen kapsar (eşleme R13.7). R13 atlanırsa R2'ye düşülür (geri dönüş güvenliği).

### R13.1 — Üyeler (6 sabit rol)

| # | Rol | Tek soru | Veto |
|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | Bu sayı / yol / formül / eşik / dosya / API gerçek mi? Kanıt A/B/C? | **Tek veto** |
| 2 | **Akademik İsabet** | Doğru alan + doğru konu + doğru yayın + doğru atıf mı? | yok |
| 3 | **Fayda-Maliyet Hakemi** | Para + zaman + LOC + bakım maliyetine değer mi? Net pozitif somut metrik var mı? | yok |
| 4 | **Daha İyisi Var Mı?** | 2026'da daha güçlü teknoloji / algoritma / UI pattern / kütüphane çıktı mı? | yok |
| 5 | **Global Çözüm Mühendisi** | Tüm corpus + tüm dil + tüm alan + tüm ekran boyutu + tüm erişilebilirlik mi? | yok |
| 6 | **Son Kullanıcı Avukatı** | Akademisyen için: hızlı + güvenilir + doğru + amaca hizmet mi? Önerinin kalitesi yeterli mi? | yok |

### R13.2 — Backend / Frontend / Görsel adaptasyon

| Rol | Backend'de bakar | Frontend + Görsel'de bakar |
|---|---|---|
| Halüsinasyon Avcısı | Veri / skor / eşik gerçek mi? | Ekrandaki rakam doğru mu? K1 (yıl tahmini) ihlali var mı? |
| Akademik İsabet | Doğru paper geri geliyor mu? Atıf doğru mu? | Karar bandı + chip rozeti akademisyene anlamlı mı? |
| Fayda-Maliyet | Bu model / kütüphane maliyetine değer mi? | Bu animasyon / komponent iş yüküne değer mi? |
| Daha İyisi Var Mı? | 2026 reranker / vector DB / LLM çıktı mı? | Daha iyi UI pattern (virtualization, view transitions) çıktı mı? |
| Global Çözüm | 25M corpus + TR/EN/karışık? | Tüm ekran + a11y + i18n? |
| Son Kullanıcı Avukatı | Çıktı doğru / hızlı / güvenilir / amaca hizmet mi? | Akademisyen brief'siz kullanabilir mi? |

### R13.3 — Çağrılma anları (zorunlu)

- Her **plan manifest** yazılırken (R1 plan-first ile birlikte)
- Her **OPEN-NNN cevabı** kararlaşmadan önce
- Her **atomic commit** öncesi (R7 ile birlikte)
- Faz geçişlerinde (F0 → F1 → F2 …)
- **Frontend görsel kararları** (palet, tipografi, komponent seçimi) dahil

**Çağrılmaz:** Operasyonel mikro-ayarlar (cache TTL +1h, env var rename, type-fix, formatting, lint).

### R13.4 — Çıktı formatı (her üye 3 satır)

```
[Üye adı] ✅ GREEN | ⚠️ YELLOW | ❌ RED
Gerekçe: <tek cümle>
RED / YELLOW ise ne istiyor: <tek cümle, somut>
```

### R13.5 — Karar kuralı

| Durum | Sonuç |
|---|---|
| Halüsinasyon Avcısı RED | **STOP** — öneri durur, plan revize, council yeniden toplanır |
| 1+ diğer üye RED | Plan revize, council yeniden toplanır |
| 3+ üye YELLOW | **Omer hakem** — "yine de yap" derse YELLOW gerekçeleri DECISIONS.md'ye **bypass entry** olarak yazılır (B-NNN, R6.2 protokolü) |
| Hepsi GREEN veya 1-2 YELLOW + 4-5 GREEN | İlerle |

### R13.6 — Kayıt protokolü

Her council toplantısı ilgili plan manifest sonuna **§Council** tablosu olarak yazılır. Bypass varsa DECISIONS.md'de B-NNN entry zorunlu.

### R13.7 — R2 (7-kontrol) ile birebir eşleşme

| R2 sorusu | R13 üyesi |
|---|---|
| K1 Literatür | Akademik İsabet |
| K2 Halüsinasyon | Halüsinasyon Avcısı |
| K3 Fayda-maliyet | Fayda-Maliyet Hakemi |
| K4 Daha kolayı | Daha İyisi Var Mı? |
| K5 Son kullanıcı | Son Kullanıcı Avukatı |
| K6 Rakip | Daha İyisi Var Mı? + Son Kullanıcı Avukatı (ortak) |
| K7 Lokal/global | Global Çözüm Mühendisi |

### R13.8 — Yürürlük

- **F2'den itibaren** tüm yeni plan manifestler R13 ile gelir.
- F1' Master Plan (B-001) **dondurulmuş**, retroactive council yapılmaz.
- R13 değişikliği yazılı Omer onayı olmadan yapılmaz (R6.2).

### R13.9 — Alan Sahipleri (insan üyeler, BAĞLAYICI oy) (2026-04-30, B-015)

R13.1'deki 6 değerlendirici rol Claude'un takındığı şapkalardır. Bunlara ek olarak **3 alan sahibi sandalyesi** (insan) eklendi; alan sahibinin oyu kendi alanı için **bağlayıcı**.

| Sandalye | Kişi | Alan | Bağlayıcı oy alanı | İnce-ayar son sözü |
|---|---|---|---|---|
| Proje Sahibi | Omer | Akademik vizyon + ürün vizyonu + her şeyin son onayı | Tüm RED + 3+ YELLOW hakem | — |
| Backend Lead | **Sercan** (senior backend, meraklı + öğrenmeye açık + uygulama fırsatı arıyor — yetenekleri yüksek) | API + DB + concurrency + Pinecone/Supabase/Redis + middleware + güvenlik + KVKK | API contract + DB schema + auth + perf | **EVET** — Omer kod yazar, Sercan prod'a getirir |
| Frontend Lead | _aday aranıyor (B42-050 design direction + akademik UX deneyimi)_ | Next.js + design system + Tiptap + animasyon + i18n + a11y | UI/UX kararları + design system tutarlılığı + Lighthouse | **EVET** — boş kalırsa post-hoc onay açık iş listesine düşer |

**Alan sahipliği kuralı:**
- Her toplantıda **işin alanı kimi etkiliyorsa onun yorumu öne çıkar** (Council tablosunda **A** satırı, vurgulu).
- **Alan sahibi RED** = otomatik plan revize (Halüsinasyon Avcısı RED ile aynı seviye).
- **Alan sahibi YELLOW** = 6 rol GREEN olsa bile **Omer hakem zorunlu**.
- **Alan sahibi yoksa (frontend boş)**: kararı 6 rol + Omer alır, **post-hoc Sercan onayı** açık iş listesine düşer.
- Alan dışında işlere alan sahibinin oy hakkı **yorum/öneri** seviyesinde; sadece kendi alanında bağlayıcı.

**Tablo şablonu (her toplantıda zorunlu — R13.4'ün genişlemesi):**

```markdown
### §Council N — <konu> (YYYY-MM-DD)

**Alan:** Backend / Frontend / Mimari / Dış servis / Veri
**Alan sahibi (BAĞLAYICI):** Sercan / Frontend Lead / Omer

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği (RED/YELLOW ise) |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟢/🟡/🔴 | … | … |
| 2 | Akademik İsabet | 🟢/🟡/🔴 | … | … |
| 3 | Fayda-Maliyet | 🟢/🟡/🔴 | … | … |
| 4 | Daha İyisi Var Mı? | 🟢/🟡/🔴 | … | … |
| 5 | Global Çözüm | 🟢/🟡/🔴 | … | … |
| 6 | Son Kullanıcı Avukatı | 🟢/🟡/🔴 | … | … |
| **A** | **<Alan sahibi> (BAĞLAYICI)** | 🟢/🟡/🔴 | **alan-spesifik teknik gerekçe** | **somut değişiklik talebi** |

**Sonuç:** GREEN ilerle / YELLOW Omer hakem / RED revize
**Empirik test gerekli mi?** EVET → <ne test, hangi metrik> / HAYIR
```

### R13.10 — Halüsinasyon Kod-Seviyesi (HK-1..HK-7) (2026-04-30, B-015)

> Halüsinasyon prosa-seviyesinde değil, **kodun kendisinde** engellenir. Plan manifest'te §Halüsinasyon-Kod-Seviyesi başlığı altında her atomic commit öncesi doğrulanır.

| # | Kural | Nasıl uygulanır |
|---|---|---|
| HK-1 | Pydantic schema gate, response her zaman validate | `response_model=` zorunlu; `model_config = ConfigDict(extra="forbid")` her dış-yüz model için |
| HK-2 | Sayı/skor/eşik kaynağı kod yorumunda | `# kaynak: fact_paper_quality_v3.q_weak (W-31)` — uydurulmuş eşik yasak, manifest referansı zorunlu |
| HK-3 | Dış servis empirik kanıt | HF / Pinecone / OpenAlex / Crossref → mock değil **canlı smoke test** + response snapshot fixture |
| HK-4 | Runtime assertion kritik invariantlar için | `assert paper.year is None or paper.year <= now().year, "K1 ihlali"` — plan-time inanma, runtime kanıtla |
| HK-5 | Manifest verify pre-import | Pinecone/DB upsert öncesi parquet manifest size + row count + schema (L-025); FAIL → STOP |
| HK-6 | Type-strict + no `Any` leak | `mypy --strict`; `Any` kullanılmışsa nedeni docstring'de + KD-N entry'si |
| HK-7 | Reproducibility seed | Test fixture'lar deterministic seed (`random.seed(42)`); flaky test = halüsinasyon riski |

### R13.11 — Dış Servis Empirik Kanıt Zorunluluğu (2026-04-30, B-015)

> "HF gibi dış servisleri **deneyerek** bileceğiz" — Omer 2026-04-30 talebi. Varsayım yasak.

- Her dış servis (HF Endpoint / Pinecone / Supabase / Redis / OpenAlex / Crossref / Cosmos / Komodo) için **canlı smoke test fixture** zorunlu: `tests/fixtures/<service>_<scenario>.json`.
- İlk çağrı yapılmadan önce **response schema bilinmiyorsa** önce smoke test → JSON snapshot al → ondan sonra Pydantic model yaz (reverse-engineering yasak değil, halüsinasyon yasak).
- Servis değiştiğinde (model swap, API version bump) snapshot diff CI'da otomatik tespit eder; breaking change = STOP + plan revize.
- Mock-only test kabul edilir ama **en az 1 canlı smoke** her servis için commit öncesi geçmeli.

### R13.12 — Commit hash kanıt zorunluluğu (2026-05-01, B-020 düzeltmesi)

> "P045-P056 12-commit zinciri lokal" iddiası B-020'de **yazıldı, gerçekte 0 commit vardı** — Halüsinasyon Avcısı RED, R12 recovery, R4 halüsinasyon-sıfır. Bir daha olmasın.

**Kural:** Tüm B-NNN entry'lerinde "commit zinciri / atomic commit / lokal-only commit" iddiası yazıldığında **commit hash kanıt zorunlu**. `git log --oneline` doğrulanmadan iddia entry'ye giremez.

**Format örneği:**
- ✅ DOĞRU: "4 wrap commit lokal `feat/F4-frontend-shell`: `7a92de0` tooling, `94931f0` design tokens, `bf87659` components, `<hash>` docs"
- ❌ YANLIŞ: "12-commit zinciri lokal `feat/F4-frontend-shell` üzerinde" (hash yok = kanıt yok = halüsinasyon riski)

**Uygulama:**
- Council §-toplantısı kapanışında Halüsinasyon Avcısı **`git log --oneline` doğrulamasını GREEN şartı yapar**.
- B-NNN entry yazımı sırasında commit henüz atılmamışsa entry'de "(commit pending — wrap-X sonrası hash güncellenir)" placeholder; commit atılınca aynı session'da hash injekte edilir.
- F4-S1.5 wrap commit yaklaşımı bu kuralın **ilk uygulanması** — atomic commit anayasası R7+R13.3 bu sprint için gevşetildi (Council 22 hibrit workflow "logical wrap" pattern), B-020 entry'sinde **şeffaf yazılı**: "atomik 12-commit retroaktif imkansız (globals.css 4 kez üst üste yazıldı), 4 wrap commit ile düzeltildi".

### R13.13 — Build PASS Empirik Kanıt Zorunluluğu (2026-05-01, Konsey post-F4-S4)

> Konsey 2026-05-01 frontend audit'inde STATE.md'deki "build/lint PASS" iddiası kanıtsız çıktı: `next build` aslında **TS hatası ile exit 1** veriyordu (orphan `web/src/lib/url-state.ts` initial commit'ten beri kırık). Kimse production build koşmadığı için fark edilmemiş; `next dev --turbopack` typecheck gate'lemiyor.

**Kural:** Sprint closure / B-NNN entry / STATE.md'de "**build PASS**" iddiası yazılmadan önce **`npx next build` exit 0 + son 3 satır log** kanıt olarak alınmalı. `next dev` PASS ≠ `next build` PASS.

**Format örneği:**
- ✅ DOĞRU: "Build PASS — `npx next build` exit 0, `✓ Compiled successfully in 2.1s` + `✓ Generating static pages (9/9)` + `Build complete`"
- ❌ YANLIŞ: "Build/lint/dev PASS" (dev sayılmaz, exit code yok = kanıt yok)

**Uygulama:**
- Sprint DoD checklist'ine `next build` zorunlu satır: `- [ ] npx next build → exit 0 (kanıt: son 3 log satırı)`.
- Konsey kapanışında Halüsinasyon Avcısı **`echo $?` doğrulamasını GREEN şartı yapar**.
- `next dev`, `vitest run`, `tsc --noEmit` ayrı kapılar — her biri ayrı koşulup ayrı kanıtlanmalı; biri PASS diğeri implicit PASS sayılmaz.
- Backend paraleli: `mypy --strict` + `pytest` + `ruff` üçlüsü zaten R13.10/HK-6 kapsamında; bu kural frontend `next build` boşluğunu doldurur.
