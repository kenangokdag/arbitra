# PLAN — Dünya-Klası Review Cockpit + Omurga-Boşluk Kapatma

> **Durum:** ONAY BEKLİYOR (Omer). Bu plan %100 kilitlenmeden FE kokpit kodu YAZILMAZ (madde 12).
> **Kaynak gerçeklik:** 3 keşif ajanı + file:line kanıt (bu oturum). Motor zengin üretiyor; FE düz scroll gösteriyor.
> **Kanun sırası:** bilim çekirdeği → backend → frontend. Omurga boşlukları (FAZ 1) FE'den (FAZ 2) ÖNCE kapanır.
> **Builder ≠ auditor:** her FAZ: uygulayıcı ajan → yönetici bağımsız doğrula → AYRI auditor ajan → commit.

---

## 0. NEDEN — tek cümle
Motor, kullanıcının kendi metnine çıpalı + neden'i + fix'i olan zengin bir yargı üretiyor; ama FE bunu 18-bölümlük
düz scroll'a (toolbox) boşaltıyor. Bu plan: (a) motorun yarım kalan sözleşme uçlarını dürüstçe kapatır,
(b) çıktıyı **karar-önce, aşamalı-açığa-çıkaran** bir kokpite dönüştürür.

---

## 1. ANTİ-TOOLBOX KAPISI — DESIGN-LANGUAGE §0.5'in 5 sorusu (FE kodundan ÖNCE, zorunlu)
> Bu cevaplar `web/DESIGN-DECISIONS.md`'ye yazılır (FAZ 0 çıktısı). Onaylanmadan FE kodu yok.

**1. RUH (tek cümle):** "Sertçe ama dürüstçe hakemlendin — ve kabul için tam olarak ne yapacağını biliyorsun."
Duygu: adil-katı bir hakem masası; her yargı senin metnine ve bir kritere dayalı, hiçbiri keyfi değil.

**2. EKRANIN TEK İŞİ:** Verdict. "Paperim hazır mı, ve bu yargı güvenilir mi?" — en iri, en üstte
(verdict + tek-cümle teşhis + 3 ölümcül risk). Diğer her şey buradan drill ile açılır. İki eşit iş yok.

**3. İMZA ANI (kopyalanamaz):** **Kanıt çıpası.** Herhangi bir eleştiriye tıkla → senin makalendeki tam cümle
+ neden eleştirildi (`reasoning_public`) + fix (`action_item`) yan yana. Rakipler metnine dürüstçe çıpalamaz;
"model böyle dedi" yerine "şu cümlen, şu kriterde, şöyle düzelt." İmza burada; cesaret yalnız burada harcanır.

**4. REDDEDİLEN 3 JENERİK (açık):**
- ❌ 18-bölüm dikey scroll dökümü (mevcut) → ✅ verdict-önce kokpit + talep-üzerine drill.
- ❌ üstte büyük-sayı istatistik bandı (hazırlık 87! güven 92! 14 bulgu!) → ✅ skor, tek-cümle teşhisin ve
  kararın ALTINDA; sayı dekor değil, yargının kanıtı.
- ❌ eşit-ağırlıklı 6-kutu "boyut" kart-gridi → ✅ editöryal argüman: verdict (iddia) → risk (severity-sıralı)
  → kanıt (çıpalı) → fix. Gridlenmiş eşitlik değil, sıralı önem.

**5. GİZLENEN KARMAŞA (aşamalı açığa çıkarma):**
- **İlk açılış:** verdict + tek-cümle teşhis + 3 ölümcül risk + önerilen karar. ("Hazır mıyım?")
- **Talep-üzerine (drill/drawer):** her risk → bağlı bulgular → makalendeki çıpalı alıntı → fix + kabul ölçütü.
- **Uzman katmanı (en alt, sakin):** reviewer council detayı, atıf bütünlüğü tablosu, kapsam boşlukları,
  statcheck, provenance mührü, disclosure. Var ama bağırmıyor.

**Editöryal omurga:** başlık (verdict) → kanıt (çıpalı bulgular) → künye (provenance/disclosure). Gazete sayfası
gibi okunur, kontrol paneli gibi değil.

---

## 2. FAZ 1 — OMURGA BOŞLUK KAPATMA (BACKEND, FE'den ÖNCE)
> Her uç ya CANLI olur ya sözleşmeden ÇIKAR. Shipped sözleşmede kullanılmayan alan = ölü kod = yalan (madde 2).

| # | Boşluk (kanıt) | Karar | DoD |
|---|---|---|---|
| **G1** | `evidence_anchors` hiçbir yerde set edilmiyor (grep boş; `review.py:588`) | **Bağla:** finding'i `evidence_pack` id'lerine (citation/coverage/stat) deterministik linkle — motor zaten bu olguları üretiyor. Bağlanamıyorsa sözleşmeden çıkar. | birim test: en az 1 finding'in evidence_anchors'ı gerçek evidence id'sine işaret eder; boşsa alan kaldırıldı |
| **G2** | `acceptance_check` bağlı ama LLM dolduruyor mu test yok (`_engine_base.py:204`, 3 rol prompt) | **Doğrula + garanti:** gerçek motor çıktısında acceptance_check dolu mu test; boş geliyorsa prompt/şema sıkılaştır | test: critical/major action_item'ların acceptance_check'i dolu (None değil) |
| **G3** | `SectionReview.status="missing"` asla üretilmiyor (rubric beklenen-bölüm tanımlamıyor) | **Üret:** RubricRegistry'ye doc-type başına beklenen bölümler ekle → eksikse "missing". Yapılamıyorsa enum'dan çıkar | test: beklenen bölüm yoksa status="missing" üretilir; aksi halde enum daraltıldı |
| **G4** | per-stage emit yok (`review_service.py` grep boş) → StageTimeline boş çark | **Emit et:** runner her aşamada `ReviewStageState` yazsın (queued→parsing→…→done, degraded_reason dahil). Durable-resume/worker = go-live (kapsam DIŞI) | test: pipeline N stage yazar; FE polling stage listesi alır |
| **G5** | `references[]` üretilir, FE render etmez + sözleşmede sergilenmiyor (`review-api.ts:116`) | **Sözleşmede tut, FE'de uzman-katmanı tablo** (FAZ 2'de). Burada sadece: alan FE tipinde sergilenir | tip: ReviewReport.evidence_pack.references FE tipinde mevcut + erişilebilir |
| **G6** | risk↔action veride bağlı (`action_item_ids↔linked_finding_ids`) ama FE görsel bağlamıyor | Veri katmanı SAĞLAM (doğrulandı). Bu tamamen FE işi → FAZ 2'ye taşı | — (FAZ 2 DoD'unda) |

**FAZ 1 DoD:** her boşluk için yeni/güncellenmiş birim test yeşil · `uv run pytest` tam-suite yeşil · hiçbir
ölü alan kalmadı (ya canlı ya silinmiş) · AYRI auditor mutation testi geçti.

---

## 3. FAZ 2 — REVIEW COCKPIT (FRONTEND, FAZ 1 kilitlendikten SONRA)
> DESIGN-DECISIONS (FAZ 0) onaylı + FAZ 1 yeşil olmadan başlamaz. API sözleşmesi tek doğruluk (madde 4).

### 2A — Verdict Cockpit (`ReviewReportView.tsx` yeniden mimari)
Mevcut 18-bölüm düz scroll → 3 katmanlı aşamalı kokpit:
- **Katman 1 (ilk açılış):** ExecutiveVerdict — önerilen karar (iri) + tek-cümle teşhis + hazırlık 0-100
  (teşhisin altında, dekor değil) + top_fatal_risks. Verdict-önce.
- **Katman 2 (drill):** risk_radar → her risk tıklanır → bağlı findings → **çıpa tıkla → AnchorDrawer**
  (makaleden alıntı) + reasoning_public + bağlı action_item (fix) + acceptance_check. İMZA ANI burada.
- **Katman 3 (uzman, en alt, collapse):** reviewer_council, citation_integrity tablosu, references tablosu (G5),
  coverage_gaps, stat_findings, provenance mührü, disclosure.

### 2B — Kritik→Öneri görsel köprüsü (G6)
Her finding kartında bağlı action_item görünür ("Düzeltme →"); her action_item hangi bulgudan doğduğunu
gösterir. Risk → bulgu → fix tek görsel iplik. "Eleştirdik ama ne yapsın?" boşluğu kapanır.

### 2C — Upload akışı sürtünme düşürme (`review/page.tsx`)
8 düz adım → mantıksal gruplar; consent en alta gömülü değil görünür güven-anı (sürtünme #1). Çift-submit kilidi
+ alan-bazlı doğrulama korunur.

### 2D — Gerçek progress (`review/[jobId]/page.tsx`)
G4'ten gelen stage verisiyle StageTimeline canlı: "N atıf doğrulandı, council görüşüyor" — bekleyiş değere döner
(sürtünme #2). İptal + tahmini süre.

### 2E — 5 durum (her ekran, madde 13)
loading · boş · hata · kısmi-veri (v1 uyumlu) · yetkisiz — beşi de gerçek. degraded_features görünür uyarı
(sessiz boş değil). Ölü buton / sonsuz spinner / beyaz ekran yok.

**FAZ 2 DoD:** `npx tsc --noEmit` EXIT 0 · lint temiz · vitest yeşil · her bölüm gerçek API alanına bağlı
(render GÖRÜLDÜ, "bağladım" demek = gördüm) · 5 durum test · frontend-excellence-audit (AYRI ajan) FAZ 0.5+craft geçti.

---

## 4. FAZ 3 — AUDIT (AYRI adversarial ajan, builder ≠ auditor)
- Backend: `backend-audit` — FAZ 1 uçları (mutation: alan gerçekten canlı mı, ölü-kod yok mu).
- Frontend: `frontend-excellence-audit` — FAZ 0.5 anti-toolbox + ux-craft + 5-durum + a11y (WCAG 2.2 AA).
- Bulgular kapanmadan FAZ "bitti" denmez (fail-closed).

---

## 5. KAPSAM DIŞI (bu plana DAHİL DEĞİL — park/Omer)
- **Ticari gating / paywall** (review ücretsiz mi / "verdict ücretsiz, fix-derinliği ücretli" mi): **marka+iş kararı
  → Omer.** Bu planda review TAM-AÇIK kalır; kokpit katman-3 ayrımı ileride paywall çizgisine doğal map olur.
- **Admin tema paneli** (renk + tipografi runtime-konfigüre): Omer istedi ("admin'den değişsin, uğraşmayalım").
  Token'lar zaten CSS-var; bu = settings endpoint + admin UI. **Light, kapsam-dışı, ayrı küçük iş** — kokpiti
  bloklamaz. Onay verirsen FAZ 4 olarak eklenir.
- **Durable resume + ayrı worker + object storage** (BE-1 kalıcılık): go-live işi.
- **Renk paleti nihai seçimi:** admin-konfigüre olacağı için tasarım-kilidi değil; kokpit YAPISI renkten bağımsız.

---

## 6. SIRA & COMMIT SINIRLARI
1. FAZ 0: `web/DESIGN-DECISIONS.md` (5 soru) → **Omer onayı** (soul-gate).
2. FAZ 1: G1→G4 (G5 tip ucu dahil) — her boşluk ayrı commit, test+auditor.
3. FAZ 2: 2A→2E — mantıklı commit sınırları (cockpit / bridge / upload / progress / states).
4. FAZ 3: audit dalgası, bulgu kapatma.
Her commit: `worldclass/build` dalı, push (restore), kısa özet + DECISIONS kaydı.

---

## 5b. FAZ 4 — ADMIN TEMA YETKİSİ (Omer onayladı: "admin panele tema yetkisi ekle")
> Global app teması, admin düzenler, FE uygular. Per-user DEĞİL. "Çok uğraşmayalım" → bounded.
> Madde 3 kararları (mevcut mimarinin zorladığı, ikinci-yol değil; keşif ajanı file:line ile doğruladı):
> - **Persistence:** ayar tablosu YOK → tek-satır `app_theme_settings` (yeni migration, sıradaki no). Supabase
>   admin-client deseni (supabase_call_async) — review-job'larla aynı. Migration APPLY = go-live (0042 gibi).
> - **Yetki:** mevcut `_require_admin()` (ADMIN_USER_IDS, prod fail-closed) reuse.
> - **Token kümesi (bounded):** accent · bg · ink · font_sans · font_serif. (DESIGN-DECISIONS: palet+tipografi
>   admin-konfigüre; aksan = tek etkileşim rengi.) Hex format doğrulama + admin formunda canlı WCAG kontrast readout.
> - **Runtime uygulama:** ThemeProvider (client) root layout'ta GET /api/app/theme → `documentElement.style
>   .setProperty`. Hata/yoklukta globals.css varsayılanları (app ASLA kırılmaz — 5 durum).
> - **Font:** serbest değil — ALLOWLIST (next/font ile önceden yüklü: Inter/Lora + alternatif). Uydurma "her font" yok.

**FAZ 4A (BE):** migration `app_theme_settings` + `ThemeSettings` pydantic (hex/font validation) + `theme_service`
(supabase upsert single-row + get) + router `api/routes/theme.py` (GET /api/app/theme public · PATCH admin-only).
Birim test (mocked supabase): get-default, admin-patch-upsert, non-admin-403, hex-validation-reject.
+ İKİNCİL: yetim-action_item backend doğrulaması (orphan action üretiliyor mu? test).

**FAZ 4B (FE):** `useTheme` hook (GET) + `ThemeProvider` runtime CSS-var injection (fallback=defaults) + root layout
wire + `/admin/theme` form (accent colorpicker + bg/ink + font dropdown + canlı önizleme + WCAG readout + 5-durum,
WaitlistModal deseni) + AdminShell nav link. Test: provider fallback, form submit, token uygulanışı.
+ İKİNCİL: çift `findings` testid temizliği + action-item kapsam.

**FAZ 4 DoD:** BE birim test yeşil · FE tsc/lint/vitest yeşil · 5 durum · admin-only enforce test · app fallback'le
asla kırılmaz · AYRI auditor (BE mutation + FE a11y/anti-toolbox) GO.

## 7. ONAY SORUSU (Omer)
- [ ] FAZ 0'daki 5-soru cevabı (RUH/İŞ/İMZA/RED/GİZLEME) onaylanıyor mu? (soul-gate)
- [ ] G1 (evidence_anchors) ve G3 (section "missing"): **bağla** mı, yoksa yapılamıyorsa **sözleşmeden çıkar** mı? (önerim: önce bağlamayı dene, maliyet yüksekse çıkar — her ikisi de dürüst)
- [ ] Admin tema paneli FAZ 4 olarak eklensin mi, yoksa go-live'a mı park?
