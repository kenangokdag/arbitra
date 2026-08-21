# F13 — Sayfa Planı v2 Implementation (Plan Manifest)

**Faz kodu:** F13
**Önkoşullar:** PR #26 merge-pending (`design/sayfa-plani-v2` → main, 26 sayfa RTF + EK_HESAPLAR_TUM_SAYFA_PLAN.rtf canonical) · V1-S14 ✅ (merged `fad5be8`) · V1-S15 P001 in-progress
**Plan tarihi:** 2026-05-10
**Onay durumu:** ⏳ ONAYSIZ — Omer explicit "F13 onaylandı" gerekli (CLAUDE.md §0)
**Branch (plan):** `feat/F13-sayfa-plani-v2-impl` off main HEAD (PR #26 merge sonrası)
**Author:** Omer (kararlar) + Claude (yazım)

---

## §0 — AMAÇ

Sayfa Planı v2'nin (26 sayfa RTF + S1 + S2) backend/frontend/veri katmanını sıfırdan inşa et. PR #26 design canon → çalışan sistem. Mevcut V1 hattı (Q + research-area + bibliometric + onboarding + chat + reading-list + notes + paper + search + summarize + top5) **bozulmaz**; F13 üstüne yeni `/api/workshop/*` + `/api/defense/*` + `/api/diary/*` + `/api/completion/*` katmanı ekler.

**Hedef metrikler (closure):**
- 39 yeni endpoint canlı (`uvicorn` import + `/openapi.json` listede)
- 8 migration `psql` apply PASS (0022, 0023, 0025-0030)
- 11 yeni FE komponent + 3 SCOPE-fix mevcut komponent
- ~30 engine/ dosyası (style/checklist/citation/dictionary/personas/journals/statcheck/jury/completion)
- 6 cron job kayıtlı + smoke
- LLM bütçe ≤ $10/ay@100proje (Gemini Flash/Pro + ElevenLabs + Cohere rerank-3)

---

## §1 — MEVCUT DURUM (kanıt seviyesi A — bu oturumda Read/Grep ile doğrulandı)

### Backend (`api/routes/`)
**MEVCUT (22 endpoint):** `q.py:99,198,283` · `research_area.py:55,84` · `project.py:187,223,290,319` · `project_bibliometrics.py:63` · `connected_papers.py:77` · `gap_heatmap.py:181` · `gap_profile.py:90` · `tts.py:42` · `onboarding.py:53` · `chat.py:37` · `enrich.py:56` · `notes.py:30,40,56,74` · `paper_detail.py:56,109` · `reading_list.py:32,39,55,78` · `search.py:114` · `summarize.py:88,117` · `top5.py:46` · `waitlist.py:67` · `dim.py:49,74`
**YOK (39 endpoint):** /api/workshop/* (24) + /api/defense/* (8 — `defense.py` dosyası kodda yok) + /api/diary/* (4) + /api/completion/* (1) + /api/feedback/project-completion (1) + /api/project/{id}/research-area/reset (1)

### Servisler (`api/services/`)
**MEVCUT:** `llm_service.py` (Gemini wrapper, fence strip, max_tokens override) · `litellm_router.py` (3-dil routing) · `elevenlabs_tts.py` · `bibliometric_service.py` · `openalex_polite.py` · `faithfulness_gate.py` · `anchor_finder.py` · `pool_router.py` · `reranker.py` (BGE-v2-m3) · `curator.py` · `presenter.py` · `translator.py` · `role_modules/` (librarian)

### Frontend (`web/src/components/project/`)
**MEVCUT (38 komponent):** 26 sayfa komponenti + 9 yardımcı kart/banner (AdvisorBanner, JourneyProgressCard, GapHeatmapCard, NetworkMapCard, DataVizCard, DataProvenance, ExtendedSummaryPage, BibliometricSummaryPageSkeleton, ColorTokensPage) + 3 hook (useQ, useLitReview, useSpeechInput, useTierMock)
**YOK:** `DiarySidebar` (S1)
**SCOPE REVIEW gerekli:** 3.2 MethodDataEthicsPage · 3.3 (eşleşme net değil) · 6.4 ReferenceIntegrityPage

### Veri (`db/migrations/`)
**Son migration:** `0021_concept_term_arm.sql` (2.5 kavram ağı)
**YOK:** 0022 (extended_affinity), 0023 (gap_matrix_calibration), 0025 (project_progress), 0026 (silent_learning), 0027 (manuscript_section), 0028 (defense_session), 0029 (project_event), 0030 (completion). 0024 plan-time reddedildi (JSONB tercih edildi → user_profiles.metadata.gap_targets)

### `engine/` klasörü
**Klasör mevcut DEĞİL.** F13'de oluşturulacak: `engine/{style,checklist,citation,dictionary,personas/{journal,jury},journals,statcheck,jury,completion}/`

### `.env`
**VAR:** GEMINI_API_KEY · PINECONE_API_KEY (`.env.example:19,30`)
**YOK / DOĞRULAN:** COHERE_API_KEY (rerank-3), ELEVENLABS_API_KEY (`elevenlabs_tts.py` zaten var → key tanımı ayrı doğrulama gerek)

### Branch / git state
- Aktif branch: `design/sayfa-plani-v2` (PR #26 design dokümanları)
- Working tree: 2 RTF modified + 3 untracked (0021 SQL + 2 colab notebook)
- Son commit: `b74c33a` (PR #26 base)

---

## §2 — SCOPE & SIRA (14 alt-sprint, sıralı)

> **Sıra ilkesi:** En az bağımlı + warm-up değerinden en yüksek bağımlılığa. Her alt-sprint = bağımsız atomik commit dizisi; bir önceki PASS olmadan sonraki başlamaz.

| # | Alt-sprint | Migration | Endpoint | FE | engine/ | LOC ~ |
|---|---|---|---|---|---|---|
| **F13-S1** | S1 Araştırma Defteri | 0029 (project_event) | 4 (/api/diary/*) | DiarySidebar (NotebookPage refactor) | — | ~600 |
| **F13-S2** | 5.1 Yayın Formatı | 0025 (project_progress) | 2 (/api/workshop/maturity, advisor-summary) | PublicationTypePage bağla | — | ~450 |
| **F13-S3** | 5.3 Akademik Dil | 0026 (silent_learning) | 2 (/api/workshop/paraphrase, paraphrase-decision) | AcademicLanguagePage bağla | style/{tr,en,id}.json | ~550 |
| **F13-S4** | 5.4 Atıf Stil | — | 4 (/api/workshop/citation-*) | CitationQualityPage bağla | citation/{apa,vancouver,ieee,chicago,mla}.py + dictionary/{tr,en,id}.json | ~700 |
| **F13-S5** | 5.2 Yayın Taslağı | — | 2 (/api/workshop/topic-proposals, draft-skeleton) | WritingSkeletonPage bağla | — | ~400 |
| **F13-S6** | 6.1 Yayın İçeriği | 0027 (manuscript_section) | 4 (/api/workshop/manuscript*) | ThesisContentPage bağla | — | ~650 |
| **F13-S7** | 6.2 Savunma Formatı | 0028 (defense_session) | 2 (/api/workshop/defense/generate-questions, suggest-jury) | DefenseFormatPage bağla | — | ~500 |
| **F13-S8** | 6.3 Bireysel Kontrol | — (JSONB extend) | 3 (/api/workshop/journal-suggest, manuscript/coherence-check, personal-feedback) | IndividualFeedbackPage bağla | checklist/{makale,tez}_{tr,en}.json | ~600 |
| **F13-S9** | 6.4 Dergi Simülasyonu | — (JSONB extend) | 3 (/api/defense/reviewer-3persona, statcheck, journal-calibration) | ReferenceIntegrityPage scope-fix | personas/journal/* + statcheck/multilingual.json + journals/review_distribution.json | ~750 |
| **F13-S10** | 6.5 Jüri Simülasyonu | — (JSONB extend) | 5 (/api/defense/jury-question, hyde-fanout-rerank, answer-score, consistency-check, jury-decision-band) | JurySimulationPage bağla | personas/jury/* + jury/reaction_thresholds.json | ~900 |
| **F13-S11** | 3.4 + 4.2-4.5 atölye | — | 5 (/api/workshop/synthesize, gap, originality, compare, impact-curve) | sayfaları bağla | — | ~700 |
| **F13-S12** | 3.3 + 4.1 + 2.1 reset | 0022 (extended_affinity), 0023 (gap_matrix_calibration) | 1 (/api/project/{id}/research-area/reset) | (data-driven; sayfa zaten var) | — | ~400 |
| **F13-S13** | S2 Proje Tamamlama | 0030 (completion) | 2 (/api/completion/snapshot, /api/feedback/project-completion) | ProjectClosurePage bağla | completion/* (badge_thresholds, oneri_kuralı, calculator, prompts) | ~700 |
| **F13-S14** | Cron altyapısı | — | — | — | (cron config) | ~300 |

**Toplam:** ~7200 LOC · 8 migration · 39 endpoint · 11 FE binding/refactor · ~30 engine/ dosyası · 6 cron job
**Süre tahmini:** 30 iş günü (3 sprint × 2 hafta) — Sercan paralel hat varsa 18 gün

**Not — V1-S15 ile çakışma:** V1-S15 P001+ frontend `/q` UX işi devam ediyor; F13 bağımsız hatta. Branch off main HEAD'de açılır → V1-S15 main'e merge olduğunda rebase tek seferde.

---

## §3 — ATOMİK COMMIT HARİTASI

> **Her alt-sprint için pattern:** (i) Migration → psql apply smoke → commit · (ii) Endpoint Pydantic model + service stub → commit · (iii) Endpoint logic + LLM call → commit · (iv) Test (unit + integration + live smoke fixture) → commit · (v) FE wiring → commit · (vi) FE test (vitest + RTL) → commit. Toplam = ~6 atomik commit/alt-sprint × 14 alt-sprint = ~80 commit.

### F13-S1 örnek (S1 Araştırma Defteri, ~6 commit)

| Commit | İş | Test | LOC |
|---|---|---|---|
| `[F13-S1-P001]` | `db/migrations/0029_project_event.sql` (id, project_id FK, user_id FK auth.users, page_slug, paper_id, event_type ENUM, payload jsonb, created_at, resolved_at) + 2 indeks + RLS read-own + write-own policy | `psql` apply + `\d+ project_event` smoke | ~80 |
| `[F13-S1-P002]` | `api/models/diary.py` Pydantic (DiaryEvent + Create/Patch/Timeline) `extra="forbid"` + `api/services/diary_service.py` Supabase CRUD | mypy strict + 6 unit | ~150 |
| `[F13-S1-P003]` | `api/routes/diary.py` POST /api/diary/event + GET /api/diary/timeline (cursor-based) + PATCH /api/diary/event/:id + main.py router include | 5 integration + live smoke `tests/fixtures/diary_event_v1.json` | ~180 |
| `[F13-S1-P004]` | `api/routes/diary.py` POST /api/diary/pre-advisor-summary (Gemini Flash 2K input) + prompt `prompts/diary_pre_advisor_v1.md` lru_cache | 2 unit + 1 live smoke (Gemini canlı) | ~80 |
| `[F13-S1-P005]` | `web/src/components/project/DiarySidebar.tsx` (NotebookPage'den refactor — sayfa-bazlı notebook → defter sidebar global tab) + `web/src/lib/diary-api.ts` apiFetch wrapper + `web/src/hooks/useDiary.ts` React Query | tsc + 4 RTL test | ~250 |
| `[F13-S1-P006]` | Sidebar entegrasyon (Ayarlar/Projelerim'in altına "Araştırma Defteri" tab) + 3 sayfa-içi buton ("Ajandama Kaydet" / "Danışmana Sor" / "Kütüphaneme Ekle") shared `DiaryActions` komponent | tsc + next build PASS + RTL 3 test | ~150 |

**Closure kanıtı (F13-S1 DoD):** R13.13 `npx next build` exit 0 + `pytest -k diary` PASS + `mypy --strict api/routes/diary.py` clean + `ruff` clean + 1 canlı Gemini Flash smoke + 1 Supabase canlı insert/read/patch döngüsü.

### Diğer alt-sprintler (F13-S2..S14)
Her biri benzer §6-commit pattern. Detayları her alt-sprint başlangıcında ilgili "executor brief" olarak `/tmp/F13-S<N>_executor_brief.md` üretilir (B-014 hibrit workflow); plan §3'te tablo yeterli.

---

## §4 — HALÜSİNASYON-KOD-SEVİYESİ (HK-1..HK-7)

> R13.10 zorunlu. Her atomik commit öncesi doğrulanır.

| HK | Uygulama (F13 spesifik) |
|---|---|
| **HK-1** Pydantic gate | Tüm endpoint'lerde `response_model=` + `model_config = ConfigDict(extra="forbid")`. Diary event_type ENUM + paraphrase decision ENUM + jury reaction_score [0,1] sınırı. |
| **HK-2** Sayı/skor kaynak yorumu | Eşikler engine/ JSON dosyalarında, kod yorumunda referans (`# kaynak: engine/jury/reaction_thresholds.json`). Magic number yasak. |
| **HK-3** Dış servis empirik kanıt | Gemini Flash/Pro her endpoint'te canlı smoke fixture; ElevenLabs F13-S1 öncesi smoke; Cohere rerank-3 F13-S10 öncesi smoke (key + endpoint hâlâ var mı doğrula). |
| **HK-4** Runtime assertion | `assert event.event_type in ("kayit","danismana_sor","kutuphane_ekle","not")` · `assert 0 <= jury.reaction_score <= 1`. |
| **HK-5** Manifest verify | Migration apply öncesi `db/migrations/` schema_migrations tablo kontrolü; çakışma → STOP. |
| **HK-6** Type-strict | `mypy --strict` her yeni dosya; `Any` leak yasak. |
| **HK-7** Reproducibility | Test seed `random.seed(42)`; flaky → halüsinasyon riski. |

---

## §5 — BU PLAN'IN UYGULAMA YETKİSİ

- **Yetki:** F13 onayı sadece **F13-S1**'i serbest bırakır. Her alt-sprint bittiğinde Omer'in açık "F13-S<N+1> başla" cümlesi gerekli (mikro-istisna: Omer "tüm F13'ye otonom yetki" derse hat boyunca koşturulur, R13.9 §0 askı).
- **Plan dışı edit yasak:** Sayfa Planı v2 RTF dışı kapsam genişlemesi (yeni sayfa, yeni endpoint) plan revize gerektirir.
- **Migration counter rezervasyonu:** 0022, 0023, 0025-0030 F13'ye ait. 0024 reddedildi (JSONB tercih). V1-S15 ya da paralel iş yeni migration **eklemez**; eklerse F13 plan'a §11 revize entry düşer.
- **R13 Council çağrısı:** Her alt-sprint başlangıcında § 8 Council tablosu güncellenir (HK Avcısı + Sercan BAĞLAYICI + 4 değerlendirici + Frontend Lead post-hoc).

---

## §6 — RİSK KAYDI

| # | Risk | Etki | Mitigasyon |
|---|---|---|---|
| R1 | Cohere rerank-3 key yok / billing yok | F13-S10 (jüri HyDE fanout) bloke | F13-S10 öncesi Omer doğrula; yoksa bge-reranker fallback (zaten var) |
| R2 | ElevenLabs key F13-S1 dışında kullanılmıyor; voice library 4. tier ücretli | Sadece S1 pre-advisor değil, S2'de mezun mail TTS planlanırsa etki | F13-S13 öncesi karar — TTS sadece vitrin'de kalsın mı |
| R3 | Pinecone index `papers-bgem3` dolu (24.8M) ama F13-S10 hyde-fanout-rerank yeni namespace ister mi? | Cost (vector storage $) + index karmaşa | F13-S10 plan'da namespace karar — V1 reuse mu yeni `jury-claims-v1` mi |
| R4 | Migration 0022 extended_affinity warehouse query maliyeti | 3 türetilmiş tablo lift+transpose, ~30M satır | 0022 commit öncesi `EXPLAIN ANALYZE` benchmark; >10s ise V2'ye ertele |
| R5 | engine/personas/jury 5 persona prompt kalibrasyonu (Cohen κ ≥0.7) pilot olmadan tanımlanamaz | F13-S10 closure ertelenir | Pilot N=20 (B-014) F13-S10 sonrası, threshold post-hoc commit |
| R6 | LLM maliyet patlaması (Pro 2.5 paraphrase her cümle = $$$) | $10/ay hedefi aşılır | F13-S3'te Pro yerine Flash 2.5 + cache ilk; Pro sadece "iyileştir" butonu opsiyonel |
| R7 | Frontend Lead boş → R13.9 post-hoc Sercan onayı + Frontend kararları post-hoc | UI tutarlılık riski | 8-anatomi token'lar canon, F13 sadece veri-bağlama; design system değişmez |
| R8 | NotebookPage refactor → DiarySidebar mevcut kullanıcı state'i kırar | V1-S14/S15'te Notebook kullanan yer var mı? | F13-S1-P001 öncesi `grep -r NotebookPage web/`; bağlantı yoksa refactor güvenli |
| R9 | V1-S15 main merge olduğunda F13 branch çakışma | Rebase merge conflict | Her hafta `git fetch origin main && git rebase origin/main` (B-014) |
| R10 | Persona drift — Claude tek "evet" ile 14 sub-sprint'i otonom koşar (memory: feedback_persona_drift_correction) | Plan dışı kod, R12 recovery | Her alt-sprint sonu explicit Omer onay "F13-S<N+1> başla" |

---

## §7 — AÇIK SORULAR (Omer cevap verecek)

| # | Soru | Engellediği |
|---|---|---|
| **Q1** | Cohere rerank-3 API key + billing aktif mi? Yoksa F13-S10 bge-reranker fallback'e mi bağlanacak? | F13-S10 |
| **Q2** | ElevenLabs key `.env`'de var mı (TTS vitrin'de çalışıyor → büyük ihtimal var, doğrulama lazım)? | F13-S1 (pre-advisor TTS opsiyonel) |
| **Q3** | Cron altyapısı: Render scheduled jobs mu, Supabase cron mu, ayrı GitHub Actions mu? Mevcut bir cron var mı? | F13-S14 |
| **Q4** | Mail sağlayıcı (S1 aylık digest + S2 kapanış mail) — Resend, SES, SendGrid? Hangisi `.env`'de? | F13-S1, F13-S13 |
| **Q5** | NotebookPage `web/`'de aktif kullanılıyor mu yoksa V1-S15'ten önce yeniden adlandırma güvenli mi? | F13-S1-P005 |
| **Q6** | Pinecone namespace stratejisi: F13-S10 jüri claim'leri için yeni namespace mi (`jury-claims-v1`) yoksa mevcut `mdv1` reuse mi? | F13-S10 |
| **Q7** | 8 migration sıralı tek PR mi (mega merge) yoksa her alt-sprint kendi migration PR'ı mı? | merge stratejisi |
| **Q8** | engine/ dosyaları Python paketinin içinde mi (`api/engine/`) yoksa repo root'ta `engine/` mi? | F13-S3 ilk commit |
| **Q9** | Sercan post-hoc review batch ne sıklıkta — her alt-sprint sonu mu, her 3 alt-sprint mi? | R13.9 |
| **Q10** | F13-S5 (5.2 yayın taslağı) IMRaD draft-skeleton — mevcut V1-S14/S15'in `WritingSkeletonPage` mock'u canlı bağlanmaya hazır mı yoksa sayfa yeniden mi tasarlanır? | F13-S5 |
| **Q11** | Persona JSON dosyaları için sürüm kontrolü: `engine/personas/jury/canli.json` v1 sabitlenir, prompt değişikliği yeni dosya `canli_v2.json` mu, in-place edit mi? | F13-S10 |
| **Q12** | Pilot N=20 ne zaman? F13-S10 closure pilot bekler mi (Cohen κ kalibre) yoksa post-MVP'ye ertelenir mi? | F13-S10 closure |

---

## §8 — R13 COUNCIL (post-approval — burada placeholder)

### §Council F13-init (yazılacak — Omer onayından SONRA)

**Alan:** Backend (39 endpoint) + Frontend (FE binding) + Veri (8 migration + JSONB)
**Alan sahibi (BAĞLAYICI):** Sercan (backend) · Frontend Lead boş (post-hoc) · Omer (proje sahibi)

| # | Üye | Oy | Gerekçe | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | ⏳ | Plan §1 file:line kanıtı verildi; Q1-Q12 açık. Cohere/ElevenLabs/cron/mail kanıt seviyesi C. | Q1, Q2, Q3, Q4 cevaplanmadan F13-S10/S14 GREEN olamaz |
| 2 | Akademik İsabet | ⏳ | 26 sayfa RTF design canon (PR #26); workshop/defense ayrımı net. | — |
| 3 | Fayda-Maliyet | ⏳ | ~7200 LOC + ~30 iş günü; LLM bütçe $10/ay@100proje (kanıt B EK_HESAPLAR). Pro 2.5 paraphrase R6 risk. | F13-S3 Pro→Flash fallback öncelik |
| 4 | Daha İyisi Var Mı? | ⏳ | 14 alt-sprint sıralı; mega-PR yerine alt-sprint = atomik faz doğru pattern. | Q7 cevabına bağlı |
| 5 | Global Çözüm | ⏳ | 3-dil engine/ (tr/en/id) baştan; persona JSON pilot kalibre eksik. | R5 mitigasyon zorunlu |
| 6 | Son Kullanıcı Avukatı | ⏳ | 4-persona (danışman/öğrenci/jüri/hakem) RTF'de canon. | NotebookPage R8 dikkatli |
| **A** | **Sercan (BAĞLAYICI backend)** | ⏳ | API contract + 8 migration + cron şeması — onay bekliyor | Q3, Q4, Q7, Q8 |
| **A** | **Frontend Lead (boş)** | — | Sandalye boş; post-hoc onay açık iş listesinde | — |

**Sonuç:** ⏳ ONAYSIZ — Omer Q1-Q12 cevap + "F13 onaylandı" sonrası Council yeniden toplanır.

---

## §9 — DoD CHECKLIST (her alt-sprint kapanışı)

- [ ] Migration `psql` apply exit 0 + `\d+ <table>` smoke (kanıt: son 3 satır log)
- [ ] `pytest -k <slug>` PASS (unit + integration)
- [ ] `mypy --strict` yeni dosyalar clean
- [ ] `ruff` clean
- [ ] En az 1 canlı dış-servis smoke fixture (Gemini/Cohere/ElevenLabs)
- [ ] `npx next build` exit 0 (R13.13 — frontend etkilenirse)
- [ ] `vitest run` PASS (frontend etkilenirse)
- [ ] Atomik commit hash zinciri NEXT_ACTION'a yazıldı (R13.12)
- [ ] R13 Council §-toplantı tablosu plan'a append (post-toplantı)
- [ ] Sercan post-hoc review issue açıldı (R13.9)
- [ ] Frontend etkilenirse browser smoke (golden path + 1 edge) — yapamadıysam "test edemedim" itiraf

---

## §10 — CLOSURE KRİTERLERİ (F13 tamamlandı = bu)

- [ ] 14 alt-sprint kapatılmış (her biri DoD geçmiş)
- [ ] 39 yeni endpoint `/openapi.json`'da listede + integration test PASS
- [ ] 8 migration apply'lı + `schema_migrations` tablosunda kayıt
- [ ] 11 FE komponent canlı veri tüketiyor; 3 SCOPE-fix sayfa scope-aligned
- [ ] ~30 engine/ dosyası repoda + en az 1 birim test her dosya tipi
- [ ] 6 cron job kayıtlı + 1 manuel trigger smoke
- [ ] LLM bütçe ölçümü: 10 simülasyon proje × 18 LLM call = $0.10/proje doğrulandı
- [ ] DECISIONS.md F13 entry (B-NNN — alt-sprint hash zinciri)
- [ ] STATE.md güncel (F13 KAPANDI ✅)
- [ ] PR (veya 14 ayrı PR — Q7) main'e merge
- [ ] Omer demo path smoke: 1 proje yolculuğu Q → 2.x → 3.x → 4.x → 5.x → 6.x → S2 closure (uçtan uca)

---

## §11 — REVIZYON LOG

| Tarih | Değişiklik | Sebep |
|---|---|---|
| 2026-05-10 | Plan §0..§11 ilk yazım | F13 init |

---

## §12 — REFERANS DOSYALAR

- Design canon: `Page_Design/Sayfa_Plani_v2/` (26 RTF + EK_HESAPLAR)
- Mimari xlsx: `~/Desktop/PaperMind_Mimari.xlsx` (31 sekme, v2 doğrulanmış)
- Build script: `/tmp/build_mimari.py`
- Önceki canon: `docs/plans/F10_back_front_integration_demo_path.md` · `docs/plans/V1_S14_mock_to_live.md` (örüntü referansı)
- Kural: `CLAUDE.md` §0 + `docs/DM_RULES.md` R1, R7, R13
- Memory canon: `feedback_persona_drift_correction.md` · `feedback_halüsinasyon_yasakları.md` · `feedback_kalite_modu.md`

---

**ONAYSIZ — Omer "F13 onaylandı" + Q1-Q12 cevap → Council §8 toplanır → F13-S1-P001 koda başla.**
