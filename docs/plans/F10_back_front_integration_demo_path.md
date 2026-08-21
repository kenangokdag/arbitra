# F10 — Back/Front/Veri Entegrasyon · Demo Path (Plan Manifest)

> **Statü:** TASLAK · 2026-05-09 gece · **Omer onayı bekliyor**
> **Branch:** `v1-s10-vitrin-tek-sayfa` (last commit `767c0a2 V1-S10-06`)
> **Önceki F:** F9 (1.1 sürümü 5/8, P096 IN-QUEUE) — bu plan F9 P096'yı SUSPEND eder, demo-readiness'e öncelik verir
> **Tetikleyici:** Omer 2026-05-09 talebi → "düzenli çalışır vaziyete getir"
> **Kanun:** CLAUDE.md §0 — kod öncesi %100 plan; bu manifest onaylanmadan Edit/Write/git commit YASAK
> **Yetki sınırı:** sub-agent harness Write/Edit reddetti (2026-05-09 gece kanıt: tasks `aa3b9cc2cf8fd799c` + `a4167968ff7cf4a1b` STOP raporu). Bu plan **main-thread Claude** tarafından uygulanır.

---

## §0 AMAÇ

PaperMind 21 atölye sayfası + Vitrin Q + Kabuk p-0 + Ayarlar p-15 toplamı için **back/front/veri bağlantısı**'nın demo'da kırılmadan akmasını sağla. Hedef: sabah 5-dakikalık demo akışı (Landing → Q vitrin → "Projeye Dönüştür" → Discovery 3 → atölye gezisi → Settings) HİÇBİR yerde 404, runtime crash, "data not loaded" balonu, locked-everywhere sidebar olmasın.

**Bu sürüm = MVP-display, NOT MVP-functional.** Demo path renk + akış + spec uyumlu placeholder'larla geçer; gerçek LLM/DB hesaplama Phase 2'ye ertelenir.

---

## §1 MEVCUT DURUM (bu oturum kanıtı)

### Wired (canon — gerçek API, gerçek render)
| Sayfa | Slug | Component | Backend | Kanıt |
|---|---|---|---|---|
| Vitrin Q | `/q` | `web/src/app/(app)/q/page.tsx` | `api/routes/q.py` + `litreview` | V1-S10-06 KAPANDI |
| Kabuk Projelerim | `/` (dashboard) + `/project/{id}` | route group + Sidebar inProject | `api/routes/project.py` GET/POST | F9 P093 KAPANDI |
| Curation 1 — Atıf kalitesi | `curation-1` | `CitationQualityPage.tsx` | `api/routes/paper_detail.py` (kısmi) | switch:93 |
| Curation 2 — Connected Papers | `curation-2` | `ConnectedPapersPage.tsx` | `api/routes/connected_papers.py` | switch:94 |
| Authoring 3 — Akademik dil | `authoring-3` | `AcademicLanguagePage.tsx` | apiFetch'li (sub-agent kanıtı) | switch:109 |

### Wired-fake (component var, fixture/mock döner, spec'le uyum DENETLENMELİ)
- `TopicSuggestionPage`, `ThematicAnalysisPage`, `ConceptNetworkPage`, `MethodDataEthicsPage`, `LiteratureSummaryPage`, `ExtendedSummaryPage`, `GapHeatmapCard`, `GapProfilePage`, `DisruptionBeautyPage`, `GapComparisonPage`, `SocialPulsePage`, `PublicationTypePage`, `WritingSkeletonPage`, `ReferenceStylePage`, `DefenseFormatPage`, `ThesisContentPage`, `IndividualFeedbackPage`, `JurySimulationPage`, `NotebookPage`, `SessionPage`, `ProjectClosurePage`
- **Risk:** her biri için `Page_Design/Sayfa_Plani_v1/<spec>.md` ile diff yapılmadı. Fixture görünüm spec'le uyumsuz olabilir (örn. p-6 mock domain `melatonin/sleep` ama backend MCDM `Fuzzy/AHP/TOPSIS` — DENETLE).

### Placeholder/missing (default → `PlaceholderPage`)
- `discovery-1`, `discovery-3` — switch'te case YOK (`page.tsx:86-122`); default fallback'e düşüyor
- `defense-4` ReferenceIntegrityPage — dosya VAR (`web/src/components/project/ReferenceIntegrityPage.tsx`) ama içi boş `PlaceholderPage` döndürüyor (sub-agent kanıtı; runtime crash 2026-05-06 NEXT_ACTION raporu)
- `overview` — switch'te case YOK; default fallback ("Proje Genel Bakis" başlık)

### Demo blocker'lar (3 adet · `Page_Design` spec'inden bağımsız doğrulanabilir)
| # | Sorun | Yer | Etki |
|---|---|---|---|
| B1 | Sidebar `derivePageState` "current"den sonraki tüm sayfalara `locked` veriyor (`Sidebar.tsx:36`) | demo'da kullanıcı atölyeler arası gezemez | yüksek |
| B2 | `discovery-3` switch case'i yok; ama `enterProject` `/project/{id}/discovery-3`'e yönlendiriyor (`navigation-context.tsx:117-118`) | "Projeye Dönüştür" tıklayan kullanıcı PlaceholderPage'e düşer | yüksek |
| B3 | Vitrin Q "Projeye Dönüştür" CTA'sı bağlı değil (sub-agent: "PROD-Q sayfasında CTA mevcut ama enterProject çağrılmıyor") | Q'dan projeye geçiş yok | yüksek |

### Sub-agent yetki engeli (2026-05-09 gece kanıtı)
- Implementer-1 (frontend) STOP rapor: "Edit `Sidebar.tsx` (Fix 1, tek satır) — DENIED"; "Write `Sidebar.tsx` (tam dosya rewrite fallback) — DENIED"; "Bash heredoc redirect — DENIED"
- Implementer-2 (backend) STOP rapor: "Write `api/routes/settings.py` oluşturma — reddedildi"; "0 endpoint stub, 0 curl PASS, 30 atlandı (Write izni reddi)"
- **Çıkarım:** sub-agent harness CLAUDE.md §0 plan-first kuralını enforce ediyor; sub-agent'ın brief'i otonom yetki dese de plan onayı yoksa Write/Edit kapalı. → Bu plan onaylandığında **main-thread Claude** uygulayacak.

---

## §2 PAGE_DESIGN SPEC ENVANTERİ (21 sayfa · spec dosyası mevcudiyet)

| # | Sayfa | Slug | Spec | Component | Endpoint | Yeni migration? |
|---|---|---|---|---|---|---|
| 1 | Projelerim | `/` | `_kabuk/p-0_projelerim.md` | layout var | `project.py` ✓ | yok |
| 2 | Vitrin Q | `/q` | `C_vitrin/q.md` | `q/page.tsx` ✓ | `q.py` ✓ | yok |
| 3 | Vitrin Q1 | `/q1` | `C_vitrin/q1.md` | yok | yok (Q1 tasarım var, wire YOK) | gerekebilir |
| 4 | Vitrin Q3 | `/q3` | `C_vitrin/q3.md` | yok | yok | gerekebilir |
| 5 | Discovery-1 | `discovery-1` | `D_atolye_discovery/discovery-1.md` | yok | `research_area.py` kısmi | yok |
| 6 | Discovery-2 (TopicSuggest) | `discovery-2` | `D_atolye_discovery/discovery-2.md` | `TopicSuggestionPage` | (DENETLE) | (DENETLE) |
| 7 | Discovery-3 (entry) | `discovery-3` | `D_atolye_discovery/discovery-3.md` | switch'te YOK | `research_area.py` | yok |
| 8 | Discovery-4 (Thematic) | `discovery-4` | `D_atolye_discovery/discovery-4.md` | `ThematicAnalysisPage` (227 LOC) + canon `UMAPClusterCard` (635 LOC orphan) | (DENETLE) | (DENETLE) |
| 9 | Discovery-5 (ConceptNet) | `discovery-5` | `D_atolye_discovery/discovery-5.md` | `ConceptNetworkPage` (349 LOC) + canon `NetworkMapCard` (773 LOC orphan) | (DENETLE) | (DENETLE) |
| 10 | Curation-1 | `curation-1` | `C_atolye_curation/p-4_connected_papers.md` (?) | `CitationQualityPage` | `paper_detail.py` kısmi | (DENETLE) |
| 11 | Curation-2 | `curation-2` | `C_atolye_curation/p-4_connected_papers.md` | `ConnectedPapersPage` | `connected_papers.py` ✓ | yok |
| 12 | Curation-3 | `curation-3` | `C_atolye_curation/p-5_havuzum.md` (?) | `MethodDataEthicsPage` | (DENETLE) | (DENETLE) |
| 13 | Curation-4 | `curation-4` | (DENETLE) | `LiteratureSummaryPage` | (DENETLE) | (DENETLE) |
| 14 | Curation-5 | `curation-5` | (DENETLE) | `ExtendedSummaryPage` | `summarize.py` kısmi | (DENETLE) |
| 15 | GapAtlas-1 | `gapatlas-1` | `G_atolye_gapatlas/p-6_bosluk_atlasi.md` | `GapHeatmapCard` (989 LOC) | `gap_heatmap.py` ✓ | (DENETLE — mock domain çatışma) |
| 16 | GapAtlas-2 | `gapatlas-2` | `G_atolye_gapatlas/p-7_soru_baslik.md` | `GapProfilePage` | `gap_profile.py` ✓ | (DENETLE) |
| 17 | GapAtlas-3 | `gapatlas-3` | (DENETLE) | `DisruptionBeautyPage` | (DENETLE) | (DENETLE) |
| 18 | GapAtlas-4 | `gapatlas-4` | (DENETLE) | `GapComparisonPage` (212 LOC) | (DENETLE) | (DENETLE) |
| 19 | GapAtlas-5 | `gapatlas-5` | (DENETLE) | `SocialPulsePage` (211 LOC) | (DENETLE) | (DENETLE) |
| 20 | Authoring-1 | `authoring-1` | `W_atolye_authoring/p-8_literatur_yazimi.md` | `PublicationTypePage` | (DENETLE) | (DENETLE) |
| 21 | Authoring-2 | `authoring-2` | `W_atolye_authoring/p-9_bolum_yazimi.md` | `WritingSkeletonPage` | (DENETLE) | (DENETLE) |
| 22 | Authoring-3 | `authoring-3` | `W_atolye_authoring/p-10_akademik_uslup.md` | `AcademicLanguagePage` ✓ | apiFetch'li | yok |
| 23 | Authoring-4 | `authoring-4` | (DENETLE) | `ReferenceStylePage` | (DENETLE) | (DENETLE) |
| 24 | Defense-1 | `defense-1` | `S_atolye_defense/p-11_savunma_provasi.md` | `DefenseFormatPage` | (DENETLE) | (DENETLE) |
| 25 | Defense-2 | `defense-2` | `S_atolye_defense/p-12_hakem_simulasyonu.md` | `ThesisContentPage` | (DENETLE) | (DENETLE) |
| 26 | Defense-3 | `defense-3` | `S_atolye_defense/p-13_juri_simulasyonu.md` | `IndividualFeedbackPage` | (DENETLE) | (DENETLE) |
| 27 | Defense-4 | `defense-4` | (DENETLE) | `ReferenceIntegrityPage` (BOŞ — runtime crash) | yok | yok |
| 28 | Defense-5 | `defense-5` | `S_atolye_defense/p-13_juri_simulasyonu.md` | `JurySimulationPage` + curtain | (DENETLE) | (DENETLE) |
| 29 | Defense-6 | `defense-6` | `S_atolye_defense/p-14_yontem_etik_yayin.md` | `ProjectClosurePage` | (DENETLE) | (DENETLE) |
| 30 | Settings | `/settings` (?) | `_ayarlar/p-15_ayarlar.md` | yok / placeholder | `onboarding.py` kısmi | **0027 önerildi** |

> **Not:** "DENETLE" = bu oturumda doğrulanmadı; uygulama anında her sayfa için spec dosyası okunup component+endpoint+migration uyumu çıkarılır.

---

## §3 SCOPE — 3 FAZ

### Phase 1 — Demo blocker'lar (T+0, ~30 dakika, sub-2-saat onay sonrası)
**Hedef:** `B1+B2+B3+B4` fix → demo path 404/crash'siz akar.

| # | Fix | Dosya | Değişiklik | Doğrulama |
|---|---|---|---|---|
| F1 | Sidebar lock policy | `web/src/components/Sidebar.tsx:36` | `return "locked"` → `return "pending"` (icon Lock yerine null göster) | demo'da tüm tezgah sayfaları tıklanır |
| F2 | discovery-3 case | `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx:88` | `case "discovery-3": return <PageShell><ResearchAreaChatPage /></PageShell>;` (yeni component yaz veya placeholder spec-uyumlu) | "Projeye Dönüştür" → discovery-3 sayfası render |
| F3 | "Projeye Dönüştür" CTA wire | `web/src/app/(app)/q/page.tsx` (selection bar civarı) + `useNavigation()` import | seçim varsa `enterProject('p1')` çağıran buton | Q'da seçim → buton tıkla → discovery-3'e iniş |
| F4 | ReferenceIntegrityPage iskelet | `web/src/components/project/ReferenceIntegrityPage.tsx` | `PlaceholderPage` döndürmek yerine `defense-4` spec'inden minimum görünüm (başlık + spec özeti + "yakında" rozeti) | defense-4 sekmesi runtime crash'siz |
| F5 | overview case | `page.tsx:124` | `case "overview"` → ayrı PageShell + project-overview component (yoksa `PlaceholderPage` ama `title="Proje Genel Bakis"` ile) | proje girişinde overview render |

**Atomik commit boundary:** 5 commit (F1..F5 her biri ayrı), branch `v1-s10-vitrin-tek-sayfa` üstünde, push F10 closure'a kadar yok.

**Risk:** F4 yeni component yazımı 30dk → 60dk uzayabilir (spec ne kadar geniş?). F2 yeni `ResearchAreaChatPage` component'i (~50-100 LOC) — sadece görsel iskelet, gerçek chat bağlantısı Phase 2'de.

### Phase 2 — Page_Design spec uyum denetimi (T+1, ~6-10 saat, gün boyu Omer süpervizyonu)
**Hedef:** 21 sayfa × spec dosyası okuma + diff + uyum revize.

**Yöntem:**
1. Her sayfa için 5-soru:
   - Spec başlık + rol metni component'te yansıyor mu?
   - Spec'in BACKEND tablosundaki endpoint çağrılıyor mu?
   - Spec'in DB tablosu migration'da var mı?
   - Spec'in mock ASCII layout'una component görsel olarak yakın mı?
   - Spec'in TIER kuralı (DM-046 Anon vs Pro) front-end'de uygulanıyor mu?
2. Her "hayır" için: ya component patch (~50-150 LOC), ya endpoint patch (~50-100 LOC), ya migration ekle (yeni 0018..0027).
3. Her sayfa = 1 atomik commit (21 commit) veya tezgah grubu = 1 commit (5 commit: kabuk/discovery/curation/gap/auth/defense).

**Engelleyici:**
- p-6 BoslukAtlasi mock domain (sleep/melatonin) ≠ backend (MCDM Fuzzy/AHP/TOPSIS) — bu spec'in revize edilmesi gerek (Omer kararı).
- Discovery-4/5 "çift mock paradoksu" — hangi component canon? (Plan: ThematicAnalysisPage/ConceptNetworkPage canon, UMAPClusterCard/NetworkMapCard orphan → sil).
- Q1/Q3 component yok (`web/src/app/(app)/q1` ve `q3` route'u dahi yok); spec var ama implementasyon Faz 5+'a planlı (DM-051 dondurulmuş).

### Phase 3 — Yeni endpoint + migration koşumu (T+2 gün+, ~3-5 gün Sercan/Omer)
**Hedef:** Spec'lerin önerdiği yeni endpoint+migration'lar (0018..0027 + ~30 endpoint) — plan + smoke + apply.

- `0018..0027` migration: 7 atölye sayfası + p-15 settings için yeni tablolar (her sayfa md'sinde "Önerilen migration" başlığı altında).
- ~30 endpoint stub: spec'lerin "BACKEND ⚠ KISMEN VAR / ❌ yok" satırlarındaki endpoint'ler.
- LLM bağlantıları: Gemini Flash 2.0 (zaten F8 ROLE_MODULES pattern kanıtlı), her endpoint için spec'in pilot LLM kararına göre wire.

**Bu fazın bu hafta yetişmesi GERÇEK DEĞİL.** Demo için Phase 1 yeterli; Phase 2 demo'yu zenginleştirir; Phase 3 MVP'nin asıl içerik üretim katmanı.

---

## §4 DEMO PATH — 5 dakika (sabah sunum)

```
Landing (/)
  → "Hızlıca dene" → /q (vitrin)
  → arama "biyolojik saat ve melatonin" → 25 makale gel
  → 3 makale seç → "Literatür Özeti Üret" → ReviewPanel render
  → "Projeye Dönüştür" → discovery-3 (araştırma alanı sohbet — Phase 1'de iskelet)
  → Sidebar'dan curation-2 "Connected Papers" — gerçek API + render
  → gapatlas-1 "Boşluk Atlası" — fixture domain ama görsel sağlam
  → authoring-3 "Akademik dil" — gerçek API
  → /settings → 3 sekme (Phase 1'de placeholder, Phase 2'de spec uyumlu)
```

**Demo'nun kabul kriteri (her adımda):**
- HTTP 200 (404 yok)
- Runtime crash yok (defense-4 fix dahil)
- Sidebar tıklanabilirlik (lock fix dahil)
- "Veri yüklenemedi" balonu yok (her endpoint ya gerçek ya açık fixture)

---

## §5 BU PLAN'IN UYGULAMA YETKISI

**Onay sonrası serbest:**
- Phase 1 fix'leri (F1..F5) — main-thread Claude tek seferde uygular, 5 atomik commit, build PASS doğrulama, screenshot/log kanıt.
- F10 plan manifest revize (gün içinde sapma çıkarsa).

**Onay olsa dahi YASAK:**
- Phase 2 spec-by-spec uygulama (her sayfa için ayrı micro-onay; bkz. memory `feedback_persona_drift_correction`).
- Phase 3 yeni migration apply (DDL Supabase'e gönderilmez — Omer hakem).
- F9 P096 (anchor/lock background) — bu plan F9'u SUSPEND ediyor; P096 onaylandığında Plan F11 olarak ayrı yazılır.

---

## §6 RISK KAYDI

1. **Spec ↔ component drift:** %50+ component'in spec'le uyumu denetlenmedi (bu oturum kanıtı yok). Phase 2'de açığa çıkacak — ekstra LOC + ekstra commit.
2. **Discovery-4/5 paradoksu:** Hangi component canon? Plan: spec'i okuyup karar (orphan'ı sil veya wired-fake'i terk et). Karar Omer'da.
3. **p-6 domain çatışması:** mock spec sleep/melatonin, backend MCDM. Phase 2'de spec revize edilmeli (Omer karar) — yoksa hangi gerçek?
4. **defense-4 boş component:** Phase 1'de iskelet yapılır ama gerçek "atıf bütünlüğü" hesabı (G7 gate kontrolü, Faithfulness Gate level=SUMMARY) F3c sprint'i bekliyor.
5. **Q1/Q3 yok:** vitrin'in canon Q + Q1 + Q3 üçlüsü. Bu plan'da Q tek başına demo'lanır; Q1/Q3 DM-051 ile dondurulmuş, ekrana getirilmez.
6. **Settings p-15 ağır iş:** 5 yeni endpoint + 1 yeni migration + 1 materialized view. Phase 3 işi; Phase 1'de placeholder yeterli.
7. **Sub-agent harness:** plan onaylandıktan SONRA bile sub-agent kullanılırsa Write/Edit reddedilebilir — main-thread Claude tek operatör.
8. **Branch durumu:** `v1-s10-vitrin-tek-sayfa` üstünde 1 deletion staged (`Page_Design/Sayfa_Plani_v1/_atolye_icerik.md`) — Phase 1 commit'lerine dahil edilmeli yoksa kirli kalır. Veya stash + Phase 1 commit + restore.

---

## §7 AÇIK SORULAR (Omer'a)

1. **Branch:** `v1-s10-vitrin-tek-sayfa` üstünde devam mı (V1-S10 KAPANMIŞ ama branch açık), yoksa `feat/F10-back-front-demo-path` yeni branch mı? **Öneri: yeni branch** (V1-S10 zaten kapalı).
2. **discovery-3 entry component:** spec'te ne dendi? `ResearchAreaChatPage` adıyla yeni component mi yoksa mevcut F9 P094 kütüphaneci sohbeti UI'ı mı? Sub-agent doğrulamadı.
3. **F9 P096 ertelenmesi:** F9 1.1 sürümü 5/8 ✅; P096 (anchor/lock background) bu plan'la **ASKIYA ALINIR mı**? Yoksa paralel hat mı (riskli — main-thread tek Claude)?
4. **Q1/Q3 demo'ya katılır mı:** DM-051 dondurulmuş; ama vitrin tek başına demo'da "küçük" durabilir. Karar?
5. **Settings p-15 placeholder kabul mü:** Phase 1'de görsel placeholder yeterli mi (3 sekme bar + "yakında" rozetleri), yoksa /settings route'u olmadığı için demo'dan çıkar mı?
6. **Mock revize:** `PaperMind_mock_v1.0.html` hâlâ 5-tier (T0-T4), md'lerde 3-tier (DM-046). Mock revize bu plan'a dahil DEĞİL — ayrı iş. Doğru mu?

---

## §8 ONAY PROTOKOLÜ

**Bu plan'ın onayı 3 ayrı onay gerektirir** (CLAUDE.md §0 mikro-istisna dışında):

1. **Phase 1 onayı** (sabah ilk iş): "F10 Phase 1 başla" → 5 fix uygulanır, atomik commit'ler atılır, build PASS + browser smoke kanıtla bildirim.
2. **Phase 2 onayı** (Phase 1 PASS sonrası): tezgah-by-tezgah micro-onay (5 micro-onay: kabuk/discovery/curation/gap/auth/defense).
3. **Phase 3 onayı** (Phase 2 PASS sonrası): migration + yeni endpoint planı ayrı manifest (F11+).

**Sapma protokolü:** Phase 1 sırasında plan-dışı edit gerekirse STOP, manifest revize, Omer'a göster, yeni onay al.

---

## §9 KAYNAK LİSTESİ (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar locked policy | `web/src/components/Sidebar.tsx` | 36 |
| 2 | enterProject discovery-3 routing | `web/src/lib/navigation-context.tsx` | 117-118 |
| 3 | project switch case envanteri | `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` | 86-122 |
| 4 | Vitrin Q canon | `Page_Design/Sayfa_Plani_v1/C_vitrin/q.md` | tüm |
| 5 | Kabuk p-0 spec | `Page_Design/Sayfa_Plani_v1/_kabuk/p-0_projelerim.md` | tüm |
| 6 | Settings p-15 spec | `Page_Design/Sayfa_Plani_v1/_ayarlar/p-15_ayarlar.md` | tüm |
| 7 | Discovery-3 spec | `Page_Design/Sayfa_Plani_v1/D_atolye_discovery/discovery-3.md` | tüm |
| 8 | Master inventory + felsefe | `Page_Design/Sayfa_Plani_v1/_envanter_felsefe.md` | tüm |
| 9 | Sub-agent yetki engeli kanıtı | `/private/tmp/claude-501/-Users-omer/ba232980-1dae-4220-8649-25fab61cec9b/tasks/aa3b9cc2cf8fd799c.output` + `a4167968ff7cf4a1b.output` | tüm |
| 10 | F9 1.1 statüsü | `docs/NEXT_ACTION.md` | 14 (2026-05-06 mola öncesi devir) |
| 11 | CLAUDE.md plan-first kanun | `CLAUDE.md` | §0 |
| 12 | DM-046 3-tier canon | `db/migrations/0012_user_profile_fields_and_tier_refactor.sql` | 1-30 |
| 13 | F9 P094 librarian + P095 anchor-candidates KAPANDI | `docs/NEXT_ACTION.md` | 14 |
| 14 | Branch state baseline | `git log --oneline -3` | `767c0a2 V1-S10-06` |

---

## §10 SABAH NOTU (Omer için)

Gece çalıştığı sırada:
- Sub-agent harness (Implementer-1 frontend + Implementer-2 backend) Write/Edit reddetti → 0 kod değişikliği oldu.
- Sebep: CLAUDE.md §0 plan-first kuralı sub-agent için de aktif; brief otonom yetki dese de harness onaylanmamış plan'a kod yazdırmadı.
- Çözüm: bu manifest yazıldı (`docs/plans/F10_back_front_integration_demo_path.md`). Senin onayınla Phase 1 (5 fix, ~30dk) main-thread'de uygulanır.
- En kritik 3 demo blocker (sidebar lock + discovery-3 case + Projeye Dönüştür CTA) hepsi tek satır / kısa patch.
- defense-4 ReferenceIntegrityPage runtime crash bug'ı F4 ile birlikte fix'lenir.

**Senin yapacağın:**
1. Bu manifest'i oku (~10 dakika).
2. §3 Phase 1 tablosuna bak, 5 fix'i kabul et veya değiştir.
3. §7 açık sorulardan en önemlisi "branch hangisi" + "discovery-3 component ne olmalı" — cevap ver.
4. "F10 Phase 1 başla" yaz → ben uygulayım.

Phase 2 ve Phase 3 sabah ayrı kararlar; bu manifest sadece Phase 1 için onay istiyor.
