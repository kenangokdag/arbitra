# NEXT_ACTION.md — Lean-Back Pointer

> **Tek satır kuralı:** "Devam et" prompt'una verilecek tek cevap. Belirsizse Claude ASK'e geçer.

> **2026-05-10 — V1-S13 demo path polish KAPANDI ✅** (`feat/V1-S13-demo-path-polish` branch off `v1-s12-sesli-arama-ve-dinlet`, 8 atomik commit lokal, push YOK). Hedef: Phase 2 backend bağlanmadan BibliometricSummaryPage'in görsel ve epistemik kalitesini Y(B perceived quality) + Y(C epistemic showcase) seviyesine çek. **8 commit zinciri**: `62ac250` plan manifest → `5cefc58` P001 motion lib + smoke test → `4fe03e8` P002 mount stagger reveal (containerVariants 80ms staggerChildren / itemVariants opacity+4px slide-up / useReducedMotion fallback) → `34ae2d3` P003 bar+list hover polish (year+lotka bars whileHover scaleY 1.04 / list items hover bg-soft) → `6554de7` P004 BibliometricSummaryPageSkeleton (motion shimmer + 4 metric + 3 chart + 2 top-10 iskelet placeholder, aria-busy) → `77c301c` P005 DataProvenance pill + Base UI Popover (5 ChartCard sağ-üst, openOnHover, kaynak/N/hesaplama/güncellik/kanıt A-B-C renkli badge) → `e8bbfd4` P006 MetricCard provenance (4 top metric kart aynı pattern, pilot scope) → `335604c` P007 DemoHint "Neden mock?" Popover (Phase 1 frontend-only iskelet rationale + Phase 2 cluster_expander+bibliometric_service ref). **Empirik kanıt R13.13 (kümülatif son commit)**: tsc clean + vitest 21 test files / 105 PASS + Next 16 build 10/10 routes (8 statik + 1 dinamik project + 1 _not-found). **Plan manifest**: `docs/plans/V1_S13_demo_path_polish.md` §9 closure kriterleri sağlandı. **DataProvenance reusable** — `web/src/components/project/DataProvenance.tsx` herhangi bir veri yüzeyi sağ-üst köşesinde kullanılabilir; gelecek ChartCard/DataVizCard'lara propla taşınır. **Sıradaki**: Omer browser smoke `/project/p1/discovery-3` (a) mount stagger görsel onayı, (b) bar/list hover hissedilebilir mi, (c) DataProvenance pill hover'da popover içerik okunaklı mı, (d) MetricCard pill çakışmıyor mu, (e) DemoHint "Neden mock?" Phase 2 referansı net mi, (f) prefers-reduced-motion ile flat fallback. Push timing Omer kararı (Hibrit workflow B-014). **Y(A) chart library swap (Recharts/Visx) ertelendi** — saf CSS bar/donut MVP için yeterli, KD-V1-S13-01 Phase 3 polish'e bırakıldı.

> **2026-05-09 SABAH (otonom gece koşumu) — F10 PHASE 1 KAPANDI ✅** Omer'in açık otonom yetkisi ("F10 Phase 1 + demo path 5 sayfa için autonom uygulamaya yetki. CLAUDE.md §0 askı sadece bu scope'ta. Diğer sayfalar placeholder kalsın.") doğrultusunda 4 atomik commit (`v1-s10-vitrin-tek-sayfa` branch, push YOK — Omer kararı): **`246f30a` F1** Sidebar lock policy → pending (demo path serbest gezinme); **`9665c51` F4** ReferenceIntegrityPage iskelet (defense-4 placeholder yerine 4 mock kart: Atıf doğrulama / DOI+URL kontrolü / Kayıp referans / Tutarlılık); **`e001a41` F2** BibliometricSummaryPage iskelet + `discovery-3` switch case (5 görsel blok: top metrik · yıl bar chart · dil donut · Lotka · top yazar/dergi — fixture data, Recharts dependency YOK saf CSS); **`c50d0c9` F3** Q vitrin "Projeye Dönüştür" CTA → `enterProject('p1')` → `/project/p1/discovery-3` (Bibliometric'e bağlanır, demo bridge kapandı). **F5 (overview switch case) silindi** — default fallback `pageId === "overview" ? "Proje Genel Bakis"` zaten temiz çalışıyor. **Empirik kanıt R13.13:** `npm run build` (Next 16.2.4 Turbopack) — `✓ Compiled successfully in 2.6s` + `✓ Generating static pages using 9 workers (10/10)`; tüm 10 route üretildi (`/`, `/_not-found`, `/chat`, `/demo`, `/landing`, `/onboarding`, `/project/[id]/[[...slug]]` dinamik, `/q`, `/reading-list`, `/search`); tsc PASS her commit'ten önce (4× temiz çıktı). **Browser smoke YAPILMADI** (otonom gece, kullanıcı uyuyordu) — sabah Omer manuel doğrulama: (a) `/q` ara → Literatür Özeti üret → "Projeye Dönüştür" görünüyor mu, (b) tıklayınca `/project/p1/discovery-3` açılıyor mu, (c) BibliometricSummary 5 blok render ediyor mu, (d) Sidebar'dan defense-4 "Kaynak Bütünlüğü" tıklayınca yeni iskelet açılıyor mu, (e) Sidebar lock-icon kalmadı mı (tüm sayfalar pending hover-able). **Plan manifest:** `docs/plans/F10_back_front_integration_demo_path.md`. **Phase 2/3 SUSPEND** — sabah Omer demo sonrası karar: gerçek backend (bibliometric_service + warehouse aggregate + atıf entegrite tarayıcı) Phase 2'de bağlanır.

> **2026-05-09 GECE — Sabah ilk iş** ⚡ Omer talebi: "back-front-data wiring per Page_Design specs · düzenli çalışır vaziyet · sabah sayfa sayfa bakacağız". Sub-agent harness Write/Edit reddetti (kanıt: `aa3b9cc2cf8fd799c` + `a4167968ff7cf4a1b` STOP raporları); 0 kod değişikliği. **F10 plan manifest yazıldı:** `docs/plans/F10_back_front_integration_demo_path.md`. **Sen okuyup onayla → ben Phase 1 (5 demo blocker fix, ~30dk) uygulayım.** Phase 1 fix listesi: (F1) Sidebar `Sidebar.tsx:36` lock→pending; (F2) `discovery-3` switch case; (F3) Vitrin Q "Projeye Dönüştür" CTA wire; (F4) `ReferenceIntegrityPage` iskelet (defense-4 runtime crash fix); (F5) `overview` switch case. Açık sorular F10 §7'de — en önemlisi "branch yeni mi, eski mi?" + "discovery-3 component spec'te ne diyor?". F9 P096 bu plan'la SUSPEND ediliyor; sonra döneriz.

> **2026-05-08 akşam pointer — SPINE.md §0.1 Vitrin batch KAPANDI ✅.** 7 yeni karar yazıldı: **DM-046** tier 2-katman (Anon + Pro, Free/Pro+ ELİMİNE), **DM-047** havuz S2 30 + TRDizin 20 = 50, **DM-048** Q1 sol panel + sağ gövde tier-aware tasarım, **DM-049** rerank 2 aşamalı hybrid (native → 25 → Gemini Flash → K), **DM-050** K=ERTELE F2 closure (rakip pattern), **DM-051** Q2/Q3 dondurulmuş Faz 5+, **DM-052** Q sayfası 3/20/50 chip + ranking + "Literatür Özeti Oluştur" CTA. Pilot scope kanon: **Q ⇄ Q1 funnel + capture form**. **Sıradaki:** §0.2 Atölye Discovery 5 sayfa envanteri (discovery-1..5) — KONUM · MEVCUT · BOŞLUK · KARAR · NASIL formatında. Akşam çalışmasıyla devam.
>
> **2026-05-08 TEMİZLİK:** Desktop'taki PaperMind dokümanları RENCBER'a arşivlendi. Tek doğruluk kaynağı GitHub repo + V2 warehouse. Aşağıdaki 7-adım listesinde 2 kaynak değişti — yeni path'ler kullanılacak.
> - **Yerinde kalanlar:** `~/Desktop/Papermind_V2/` (warehouse, referans), `~/Code/papermind-app/` + `~/Code/decisionmind2/` (GitHub).
> - **RENCBER arşivi:** `/Volumes/RENCBER/papermind_archive_2026-05-08/{papermind_brain,papermind_docs,papermind_reklam,papermind_downloads}.zip`.
> - **RENCBER secrets:** `/Volumes/RENCBER/secrets/papermind-493118-cf60c8a51035.json` (GCP service account).
> - **Silinen referanslar:** `~/Desktop/papermind-brain/` (artık `papermind_brain.zip`), `~/Desktop/PaperMind_Rapor_2026-05-06.pdf` (artık `papermind_docs.zip`), `~/Desktop/papermind-mockup/` (zaten yoktu — eski plan dosyalarındaki path'ler tarihsel referans).
> - **Halüsinasyon kuralı:** Bu temizlik sonrası "Desktop'ta X dosyası var" iddiası YASAK; kaynak yoksa RENCBER zip'inden çıkar.

> **2026-05-06 (mola öncesi devir) — F9 P095 KAPANDI ✅ + Pre-existing 10 fail KAPANDI ✅. F9 1.1 sürümü 5/8.** Bugün main'e inen 3 PR squash: (1) **PR #15** `aaf3780` — `fix(listener): max_tokens=1500 override` (Gemini Flash default 600 token sonu fence'i kestiği için P094 sırasında raporlanmış; 8 listener fail kapandı); (2) **PR #16** `e053d84` — `fix(test): onboarding schema drift` (`field_id` int → uuid + `slug` NOT NULL + `theme_id` "T" prefix tutarsızlığı; 2 onboarding fail kapandı); (3) **PR #17** `9af5be0` — **F9 P095 anchor-candidates BÖLÜM 2 paralel arama** (HyDE → Pinecone vec(80) + Supabase tsvector(80) → RRF k=60 → top-50 → enrich (`is_suspicious=false` HARD filter + q_weak band) → BGE-v2-m3 rerank → top-3; 11 dosya +1564/-13; 9/9 yeni test PASS — 6 unit `test_anchor_finder.py` + 3 integration `test_anchor_candidates.py`; ruff + mypy --strict PASS; suite 231 PASS / 2 FAIL pre-existing onboarding stale → PR #16 ile kapandı; live smoke `tests/fixtures/anchor_candidates_v1.json` Gemini HyDE valid + Pinecone vec=80 + Supabase enrich functional, cold-start 21s, warm ~4-5s). **K-031 zırh kanıtı** P095'te de iki kat (route `_user_id(request)` 401 + service `.eq("user_id", uid)` + `ProjectNotFoundError → 404`). **Plan §74 drift** (executor brief 2-commit istiyordu — drift fix + impl ayrı; tek commit `1f34cc3` ile birleştirdi, küçük drift kabul; future briefs: drift fix mutlaka ayrı commit). **DEFERRED işaretler P096+ için**: (a) Supabase `papers` tablosu **0 satır** → tsvector havuzu fonksiyonel ama gerçek aday üretmiyor (warehouse upload pending Omer); (b) Pinecone B-012 metadata `filter=None` (1.1 tolere, 1.2 zorunlu); (c) BGE-reranker cold-start ~700MB RAM (production singleton bir kez yüklenir, `paths.parents[1]` lru_cache). **Lokal repo state (mola öncesi):** `papermind-app` main = `9af5be0` = `origin/main` (clean, sadece `.env.bak.20260506` untracked yedek dosya, izlenmiyor). `papermind-brain` main = `5896eca` (K-033 ratify), **1 commit ahead `origin/main` — push edilecek**. Worktree'ler temizlendi (P095 + onboarding-fix iki branch silindi merge sonrası). **PaperMind proje raporu** PDF'i Desktop'a yazıldı: `~/Desktop/PaperMind_Rapor_2026-05-06.pdf` (~877 KB; 8 ana rota + 24 workbench alt sayfası için sayfa-sayfa amaç + gösterim + tamam/eksik tablosu, kaynak: `/tmp/papermind_rapor.md`). **Tek satır cevap** (yeni oturum açılışı): "P096 brief'i panoya: `/tmp/F9_P096_executor_brief.md`". **P096 = `anchor/lock` background job + ESTRA scorer + cluster_expander** (~280 LOC, brief plan §75 + §9 BÖLÜM 3-4-5 + §11/§12 referansları ile yazılacak; bağımlılık F9 P095 ✅ anchor_finder + 0016 project_cluster ✅). 1.1 sürümü progress: 5/8 ✅ (P091..P095), kalan 3/8 — P096 background, P097 frontend en büyük blok (~520 LOC, `discovery-1` araştırma alanı bağlama), P098 özetle/çevir/danışmana action zinciri. **defense-4 ReferenceIntegrityPage runtime crash bug** raporda yakalandı (`web/src/components/project/ReferenceIntegrityPage.tsx` dosyası yok ama lazy import yazıyor) — F9 dışı hızlı PR ile düzeltilmeli. **2026-05-05 gece (geç) — F9 P094 KAPANDI ✅, P095 IN-QUEUE.** P094 librarian Stage A 2-tur Gemini Flash sohbeti production'a indi (PR #14 squash `7ebaa31` → main, 2026-05-05 18:48 UTC, 2 atomic commit `ff694ee` LLMService global fence strip + `max_tokens` override + `27b054f` librarian implementasyonu; F8 ROLE_MODULES pattern `api/services/role_modules/librarian.py` + `prompts/librarian_v1.md` lru_cache + `ParsedUnderstanding` 3-focus schema + `MessageRequest`/`MessageResponse` Pydantic forbid + K-031 RLS zırh manuel `.eq("user_id")` + Gemini Flash markdown ` ```json…``` ` defansif strip global fix; **empirik kanıt R13.13**: 17 test PASS (7 unit librarian + 2 integration research_area + 8 llm_service) + mypy --strict 5 dosya + ruff 7 dosya temiz + live Gemini smoke fixture `tests/fixtures/gemini_librarian_v1.json` tokens_out=797 latency 10.5s; 12 dosya +1146/-3). **Halting signal**: paralel session brief okurken Gemini fence wrapping bug raporladı; kök neden `llm_service.py:96` civarında — global fix `_strip_code_fence()` ayrık open/close regex (max_tokens kapağı kapanış fence'i kesebilir) librarian + tüm structured_output çağrıları için aktif. **Tek satır cevap**: "P095 brief'i panoya: `/tmp/F9_P095_executor_brief.md`". P095 = anchor-candidates BÖLÜM 2 paralel arama (Pinecone+tsvector RRF+reranker, ~260 LOC, `anchor_finder.py` yeni + `pool_router.py` lexical=tsvector concrete patch + 5 unit + 1 integration; bağımlılık F8 LLMService ✅ + P094 librarian ✅ + 0015 `papers.title_tsv` ✅). **2026-05-05 gece — F9 P093 KAPANDI ✅, P094 IN-QUEUE.** P093 `/api/project` CRUD + onboarding miras production'a indi (PR #13 squash `67f1b9f` → main, 18:17 +0300, K-031 ratified — POST/GET/GET{id} + Pydantic forbid + onboarding miras user_profile_fields/subfields bridge + research_focus_en metadata; **defansif RLS zırhı** brief dışı eklendi `eq("user_id", uid)` çünkü service-role RLS bypass eder; 6 dosya +631 satır; ruff + mypy strict + 10/10 yeni test + live smoke production PASS). **Pre-existing 14 fail** (test_search_endpoint::*, test_skeleton_endpoints::test_onboarding_*/test_top5_*) main HEAD'de zaten vardı — ayrı KD (F3a/F5 refactor).

> **2026-05-05 akşam — F9 P092 KAPANDI ✅, P093 IN-QUEUE.** Zincir: P090 manifest (PR #10 `63d93e9`) → P091 0015 projects skeleton + papers.title_tsv (PR #11 `4c0dbd3`, K-029) → P092 0016 project_cluster materialize (PR #12 `568753b`, K-030, 14:56 UTC merge). Smoke kanıtları (R13.13): P091 A-F PASS, P092 A-F PASS (CASCADE 3 rows → parent DELETE → 0 rows verified). **Tek satır cevap**: "P093 brief'i panoya: `/tmp/F9_P093_executor_brief.md`". P093 = `/api/project` CRUD + onboarding miras (~180 LOC + 5 unit + 3 integration; bağımlılık 0015 ✅ + 0011-0014 onboarding chain ✅). Pattern referansı: `api/routes/onboarding.py` (Supabase dev fallback + KVKK SHA-256). **DRIFT UYARISI**: "Son güncelleme" bloku 2026-05-01'den; arada F4-S5/F5/F6/F7/F8/F9 P090 yansımamış. Brain repo BRAIN.md K-027..K-030 kanonik kayıt — tam reconstruct ayrı KD. **K-029 dersleri P091+P092'de doğrulandı**: asyncpg direkt apply (Dashboard silent fail bypass) + port 5432 session pooler (ISP :6543 blok) + atomik BEGIN/COMMIT + R13.13 empirik kanıt commit body inline.
> **AKŞAM ÇALIŞMASI (2026-05-01):** Faz 3 scope audit REVİZE — ilk audit 8 tablo iddia etti, 5'i halüsinasyondu (0001-0004'te zaten kayıtlı). **Gerçek eksik: 2 micro tablo** → `0010_paper_flags_temporal.sql` (abstract_flags_v5 24.87M × 7 + temporal 18.38M × 7, ~1-1.5 GB Postgres ek). 7-kontrol uygulandı: has_hypothesis/has_novelty rozeti = akademisyen UI sinyali (Scite/Consensus pattern); cite_half_life ≠ beauty.B (Price 1965 ≠ Ke 2015); total_citations ≠ centrality.indegree. Önceki "Plan 2'ye ertelenebilir" cevabı closure-bias düzeltildi. **Akşam yapılacak:** (a) 0010 SQL Claude'a yazdır, (b) Supabase Dashboard'a paste, (c) `colab_load_phase3.ipynb`'a 2 upload cell ekle, (d) 4XL window halen açıkken yükle. Detay: `docs/plans/F2_phase3_warehouse_mirror.md §11.1-§11.4` (revize edildi).
> **Son güncelleme:** 2026-05-01 (öğleden sonra — **Konsey 40 post-F4-S4 audit + 4 fix commit ✅** main branch ardışık atomik). Omer talebi "renk değil köke odaklan, global çözüm" → konsey 2 production blocker + 1 race + 1 scope leak yakaladı. **4 fix**: (1) `26d016d` `next build` EXIT 1 kökü → `web/src/lib/url-state.ts` orphan kaldır (initial commit `93f75e7` F4-S2 P059 scaffold artığı, `@/stores/search` import edip kayıp dosyaya bağımlıydı; STATE'deki "build PASS" kanıtsız çıktı, initial commit'ten beri kırıktı); (2) `9461d2e` SimulationCurtain race fix → shared `cancelledRef` boolean replay/skip race'inde önceki run'ın await'ten dönen mutation'larını engellemiyordu; per-run generation token (`runGenRef.current++` + her await sonrası `gen !== runGenRef.current` drop); (3) `d74586c` ChatboxPanel scope fix → `document.querySelector('[data-chatbox-panel="true"] textarea')` global selector birden fazla portal mount durumunda yanlış panel focus verebilirdi; `panelRef.current?.querySelector` scoped (R7 lokal→global); (4) `667f5a2` DM_RULES R13.13 yeni kural "Build PASS Empirik Kanıt Zorunluluğu" — sprint closure / B-NNN entry / STATE.md "build PASS" iddiası yazılmadan önce `npx next build` exit 0 + son 3 satır log kanıt; `next dev` PASS ≠ `next build` PASS (Konsey 40'ın kök nedeni codify edildi). **Empirik kanıt kümülatif**: tsc EXIT 0 + next build EXIT 0 9/9 static + dynamic `/paper/[id]` + vitest 32/32 (29 F4-S4 + 3 SimulationCurtain) + ESLint 26→23. **Halüsinasyon avı**: STATE.md F4-S1 "build PASS" iddiası A→C kanıt seviyesi düştü (initial commit'ten beri B grade hayalet PASS); R13.13 ile artık empirik. **Bugün ana hatlar (2026-05-01, 35 commit)**: **Backend (3 commit)** — F2 day 3-4 resilience hardening P011-P015 KAPANDI ✅ (`93f75e7` initial 228 dosya + `0d2438f` closure + `9a085ec` test fixture; utils/resilience.py + Pinecone/Supabase async wrapper + 503/504 mapping + 4 runbook; 145 unit + 11 integration = 156/156 PASS; DM-030..034 + KD-36..40; Council 39; GitHub push main). **Frontend (32 commit, 6 blok)**: Blok 1 F4-Foundation 12 commit (brand canon journey amber→indigo→amber-700→orange #F97316; ui/button 4-variant; sidebar D9 + logo+Wordmark + state machine + accent stripe; landing C3 polish; nav-config refactor); Blok 2 F4-S3 Hızlı Tarama 7 commit (D5/D6/D8/D14/D15/D21/D29 bileşenler); Blok 3 F4-S4 Danışman ChatboxPanel 8 commit B-023; Blok 4 P080 SimulationCurtain ad-hoc; Blok 5 Konsey 40 audit + 4 fix; Blok 6 bu docs commit. Empirik kanıt (frontend): tsc EXIT 0 + next build EXIT 0 9/9 + vitest 32/32 + ESLint 26→23. **Sıradaki**: Omer kararı — F4-S2 P059 Zustand+URL state / F4-S5 Profil+Home+Polish / Faz 3 warehouse mirror upload paralel hattan biri. **Önceki güncelleme:** 2026-05-01 (akşam — **F4-S4 Danışman ChatboxPanel KAPANDI ✅ (B-023)** main branch üstünde 7 atomic commit + 1 docs commit. Plan: `docs/plans/F4_S4_advisor_chatbox.md`. D16-Chatbox.html canonical floating yan-panel surface — 370×620 fixed bottom-right + slideIn 280ms cubic-bezier(.16,1,.3,1) + warm-neutral editorial palet (`#F7F7F5/#FFFFFF/#E4E4E0/#EFEFED` + ink header, status emerald-400, amber YOK), mobile <640px bottom-drawer full-width, ESC kapanma + portal mount + `prefers-reduced-motion` opacity-fade, Cmd+J Topbar shortcut, PaperCard "Danismana sor" → `openChatbox({kind:"paper",...})`, /chat full-page 128→60 LOC `<ChatThread variant="page">` reuse, `/api/chat` 501 fallback `lib/chat-fixture.ts` 4-reply round-robin (HK-7 deterministic + 600ms artificial delay + `// TODO(P020)` swap marker). 7 commit hash: `78dd164` P073 (idempotent — chat token grubu zaten brand commit'inde) / `74bab55` P074 PenIcon / `2b59ad4` P075 useUiStore Zustand atomic ref selectors HK-4 invariant / `6a4f7ab` P076 `<ChatThread>` shared (Lora italic adviser + Inter user + typing 3-dot + jsdom scrollTo guard) / `81699d2` P077 `<ChatboxPanel>` floating shell + portal + autoFocus 280ms / `9da69fe` P078 Topbar Pen + Cmd+J + AppShell mount (lib/keybindings.ts dropped — tek shortcut için ayrı dosya overkill) / `4935950` P079 PaperCard rewiring + /chat refactor + chat-fixture. **Empirik kanıt:** Vitest **29/29 PASS** (`web/`'den `npx vitest run`): ui.test.ts 5 + pen.test.tsx 2 + ChatThread.test.tsx 6 + SearchPending.test.tsx 8 + ChatboxPanel.test.tsx 8. TypeScript `tsc --noEmit` temiz (sadece pre-existing F4-S2 `@/stores/search` dead-code error, F4-S2 P059 bekliyor). **Sapma kayıt:** (1) main branch'te ilerlendi (B-019 `feat/F4-frontend-shell` tek-branch kararı F4-S2/S3 plan onaylarına ertelendi, Omer triple-yes onayıyla); (2) Cmd+K coexistence dropped — sadece Cmd+J; (3) F4-S2 P060 dependency dropped — `<ChatBubble>`/`<ChatInput>` ChatThread içinde inline; (4) Zustand composite selector → infinite re-renders bug yakalandı, atomic ref selectors fix; (5) jsdom scrollTo guard. KD-29..KD-32 (zone-spesifik 5×3 starter / multi-thread persisted / focus-trap react-aria / markdown render bubble + Shiki) Bilinen Borçlar listesine eklendi. **Önceki (gece):** F2 day 3-4 backend resilience hardening **KAPANDI ✅** + GitHub repo **PUSHED ✅**. **F2 day 3-4 P011/P012/P013/P015**: `api/utils/resilience.py` (with_timeout/with_retry/call_resilient PEP 695 generics) + Pinecone async wrapper (`asyncio.to_thread + with_timeout`, `@lru_cache get_pinecone_index()` singleton, `PineconeQueryError`) + Supabase async helper (`SyncClientOptions(postgrest_client_timeout=10)`, `supabase_call_async`, `SupabaseQueryError`) + search route 503/504 mapping (`ResilienceTimeoutError → 504`, `(PineconeQueryError, SupabaseQueryError) → 503`) + 4 runbook iskelet (`docs/runbook/{pinecone_down,supabase_down,hf_endpoint_down,search_p95_breach}.md`). **Test**: 145/145 unit + 11/11 integration PASS, ruff + mypy strict temiz. **DECISIONS**: DM-030/031/032/033/034 eklendi (DM-034 = P014 Circuit Breaker F7 P065'e ertelendi, KD-36). **GitHub push (2026-05-01 gece)**: lokal `.git` corrupt'tu (object 1e5c9d02 unreadable, secret leak fix sonrası GC artığı) → `rm -rf .git && git init -b main` clean reinit + 228 dosya stage (.env protected, node_modules/.venv ignored) + commit `93f75e7` `initial: PaperMind v4 backend skeleton + F2 day 3-4 P011-P015 resilience hardening` + remote https://github.com/ofrencber/PaperMind.git + `git push -u origin main` ✅. **Konsey 39 (alt-§ 39a/b/c/d) + Sercan post-hoc backend review yazıldı (DM-030..033 kanıt sütunu)**. **Sıradaki backend (F2 day 5+)**: **P006 HybridPoolRouter concrete** — semantic + theme + lexical 3-havuz RRF fusion + B-012 metadata HARD filter (q_weak/method/lang/year), Pinecone B-012 patch koşumu Omer Colab'da bittiğinde başlanır (engelleyici: KD-23 lexical karar açık FTS audit Council 25 düzeltme A). LOC tahmini ~180. **Frontend paralel akış (F4-S2)**: P059 Zustand search store + URL state sync (~80 LOC) — bağımsız, sabah açılışta seçim Omer'in. **Önceki güncelleme:** 2026-05-01 gece (oturum devri — Omer sabah yeni oturumda başlayacak). **F4-S2 BAŞLADI ✅** — P058 SearchPending 3D rotating carousel + P058.1 Tailwind v4 polish fix tamamlandı, Browser empirik kanıt onaylandı. **Sıradaki: P059 Zustand search store + URL state sync (~80 LOC)** — F4-S2 plan manifest §3 tablosu, mevcut `web/src/lib/api.ts` + `auth.ts` üstüne yeni `web/src/stores/search.ts` (Zustand 5) + `web/src/lib/url-state.ts` (useSearchParams + Zustand sync). Sabah açılışta atomic commit P059 ile başla. **Bu oturumda atılan 7 atomic commit lokal `feat/F4-frontend-shell`** (push timing Omer kontrolünde): `7a92de0` feat(tooling) wrap-1 + `94931f0` feat(design) wrap-2 + `bf87659` feat(components) wrap-3 + `106545e` docs wrap-4 + `ea7b2a0` hash injection fix + `e0b25ae` P058 SearchPending + `5081a08` P058.1 polish fix. **Önceki güncelleme:** 2026-05-01 — **F4-S1.5 design system polish KAPANDI ✅** (B-020). 4 wrap commit lokal `feat/F4-frontend-shell` (`7a92de0` tooling + `94931f0` design tokens + `bf87659` components + wrap-4 docs; atomik 12-commit retroaktif imkansız — R12 recovery + R13.12 yeni kural; push timing Omer kontrolünde): shadcn `init --defaults` + 8-anatomi token altyapısı (shadow stack 2-katman + transition cubic-bezier(0.16,1,0.3,1) + type scale + radius 6/10/14) + Defne Yıldız Frontend Lead persona resmi atama (R13.9 BAĞLAYICI sandalye doldu, post-hoc Sercan onay yükü kapandı) + Default shadcn yasak 8-anatomi memory + Hazır tasarım entegrasyon politikası memory (Tier-1 shadcn registries birinci sınıf + Tier-2 uiverse manuel JSX rewrite + 5-soru filter) + Button mockup v3 override (radius-sm + flat shadow + manuscript underline + 11 unit test PASS Vitest 2 + RTL 16 + jest-dom + jsdom + `@/` alias) + COMPONENT_RULES.md + REFERENCES.md (Anthropic/Stripe/Linear/ResearchRabbit kıyas) + Topbar duplicate search→ikon-only Cmd+K (P049) + contrast tweak +6-8% (P050) + PageHeader Lora italic 28px + Card 2-katman shadow + 18×20 padding (P051) + PaperCard prototip (Lora 17px title + Inter meta + 3-line abstract + 6 action: Detay/Listeme/Özetle/Sohbet/Nota ekle/Danışmana sor + semantic chip yeşil-açık erişim/gri-dil/amber-mavi decision_band, P052) + cool-paper-blue palet revize Nature/JAMA (P053, B-019 mockup v3 krem warm imza accent amber-700'e çekildi) + stat card semantic border-left amber/info/warn/ok (P054) + PaperCard chip semantic renkler (P055) + **profesyonel cool-academic palet swap WCAG AAA verified (P056, Radix 12-step + Tailwind v4 OKLCH — slate-50/100/200/300 bg + slate-900 ink 16:1 AAA + slate-700 10:1 AAA + slate-600 8:1 AAA + slate-500 5.2:1 AA + amber-700 accent 4.5:1 AA + emerald/blue/orange/red status pale chip bg)** + sidebar reorg (Hesap grup `mt-auto` en alta, Ayarlar > Profilim sırası). KD-22 (dark mode + chart-* tokens post-MVP) + KD-23 (tier-1 community 9 atom 2. konsey turu) Bilinen Borçlar listesine eklendi. **Sıradaki F4-S2** (Omer push + visual review sonrası): Makale Ara wiring + 9 atom community shadcn import 2. konsey turu KD-23 (sidebar/card/tabs/separator/badge/sheet/skeleton/dialog/sonner). **Önceki güncelleme:** 2026-04-30 gece geç (oturum devri — **F4-S1 KAPANDI ✅**) — `feat/F4-frontend-shell` branch'inde 7 atomic commit lokal (push yok). Mockup v3 dondurma + F4 plan revize + P037-P044 zinciri: Next.js 16.2.4 + React 19 + Tailwind 4 (@theme tokens #FAF8F3 + Inter+Lora) + sol sidebar 240px (SciSpace pattern) + 8 ekran route stub + API client (501 fixture fallback) + dev JWT mock + types (Pydantic mirror) + search fixture + Loading/Error/NotFound Suspense. Build/Lint/Dev all PASS (9 route, 0 type error, security headers aktif). Node v24.15.0 LTS Krypton kuruldu (`~/.local/share/node24` + `~/.local/bin` symlinks, npm 11.12.1, 500 packages). **Sıradaki F4-S2** (Omer onayı bekliyor): Makale Ara wiring — gerçek arama formu + filter chip (yıl/dil/alan) + fixture'dan PaperCard listesi + 501→"demo verisi" banner + URL state sync; ~3 gün, ~600-800 LOC. **Önce visual review** (Omer browser'da `npm run dev` → localhost:3000) sonra F4-S2 onay. Eski B42-050 §5 kütüphane fişi (Crimson Pro + ESTRA bar + PMID Geist Mono renklendirme + krem-parşömen #F5EBDD) post-MVP polish'e ertelendi (mockup v3 sade hat onaylı; R5 hiyerarşi gereği mockup v3 üstün). KD-21 Frontend post-hoc Sercan PR review batch yeni Bilinen Borç. **Önceki güncelleme:** 2026-04-30 gece (**B-018 Backend Senaryo B + pseudocode-first hibrit — Pinecone-bağımsız parçalar concrete + F3+F5 6 endpoint skeleton bugün tamamlandı**: Council 30 4 RED + 2 YELLOW + 1 GREEN alt-öneri → Omer arbiter onayı; bugün ~8h aktif **121/121 PASS** + ruff + mypy strict 32 src; (a) `uv` 0.11.8 omer2 user'a kuruldu + .venv onarıldı; (b) smoke koşuldu (HF 503 cold-start retry doğrulandı + Pinecone hâlâ koşuyor + Supabase ✅ + Redis lokal kapalı graceful degrade); (c) **P004 QwenListener** concrete async (HF httpx pool + cold-start retry 502/503/504/524 + 3-dil routing + Pydantic forbid + K11 fallback) — 11 unit; (d) **P007 BgeReranker** concrete async (transformers+torch lazy CPU/MPS + scorer DI + degraded uniform 0.5 TODO P006-after) — 6 unit; (e) **P009 DilSpesifikPresenter** YENİ ABC + concrete (LiteLLM router 3-dil + completion_async DI + K11 fallback) + `config/litellm_models.yaml` — 11 unit; (f) **P008 OutlinesCurator iskelet** + **`api/services/faithfulness_gate.py` YENİ ortak servis** (B-010): level=SEARCH 2-kat aktif (jsonschema=100% Pydantic forbid + LVR placeholder 0.85), level=SUMMARY NotImplementedError; `config/faithfulness_thresholds.yaml`; signals_13 sözleşmesi + decision_band + G3 warnings + multi-lang claim + gate FAIL → HTTP 500 — 16 unit; (g) **F3+F5 skeleton 6 endpoint** YENİ: chat (P020 SSE Cosmos KD-18) + summarize POST+GET (P022 level=SUMMARY) + enrich (P031) + reading-list 4 metod (P035 asyncpg) + onboarding (P046) + top5 (P050 OPEN-005) — Pydantic forbid + 501 + detail.error+todo+blocker; main.py 6 router include; 11 integration; (h) DECISIONS B-018 entry + sprint plan KD-13 pointer + STATE update; (i) bu NEXT_ACTION update; **henüz commit yok**, atomic 7-commit zinciri Hibrit workflow B-014 (Council 22) lokal-first, push timing Omer kontrolünde. **Pinecone gelince ince işçilik**: P006 HybridPoolRouter + P008 LVR validate gerçek + F3 6 TODO concrete (Cosmos+MiniCheck+ALCE+OpenAlex Sercan handoff geldikçe) + grep TODO(P sayım=0 polish gate. **Önceki güncelleme akşam**: Council insan üye katmanı + 3-günlük sıkıştırılmış sprint paketi + Senaryo B Frontend Lead post-MVP ertelemesi — B-015 + B-016 + B-017; (a) DM_RULES R13.9-R13.11 + DECISIONS B-015 + memory 2 dosya; (b) `docs/plans/F2_day2_4_compressed_sprint.md` Council 25-28 + 6 atomic commit revize plan; (c) `scripts/smoke_external_services.py` HF + Pinecone + Supabase + Redis fixture üreteci; (d) **B-017 Senaryo B**: Claude kod + Omer iterasyon + freelance illustrator + Sercan post-hoc; Frontend Lead arama post-MVP'ye ertelendi (recruitment_brief.md arşiv); aktif `docs/frontend/illustrator_brief.md` (7 asset paketi $500-1500, 7 gün). **F2 Day 2 yarın Omer başlar**: Adım 1 `uv sync` (.venv kırık) → Adım 2 smoke koşumu → Adım 3 B-012 verify → Adım 4 migration 0005 → Adım 5 P004→P006→P007→P008→P009 6 atomic commit → Day 4 wrap. **Sercan post-hoc onay paralel**. **Freelance illustrator paralel akış**: aday arama Day 1, brief gönder Day 2, asset teslim Day 9 (F4 frontend skeleton başlamadan ✒ + adviser hazır). Bilinen Borçlar §7'de KD-1..KD-19 + KD-20 freelance illustrator aday arama görevi.)

---

## 🚀 YENİ OTURUMDA İLK 7 ADIM (2026-05-06 mola sonrası güncel)

```
1. Read: CLAUDE.md                                       (oturum protokolü, K-001..K-005 + plan-first kural)
2. ARŞİV: BRAIN.md artık /Volumes/RENCBER/papermind_archive_2026-05-08/papermind_brain.zip içinde — gerekirse oradan çıkar (K-001..K-033 historical canon)
3. Read: docs/NEXT_ACTION.md                             (bu dosya — F9 P096 IN-QUEUE)
4. Read: docs/DM_RULES.md                                (R1-R13 + R13.9-R13.13 commit hash kanıt + HK gates + Build PASS Empirik Kanıt)
5. Read: docs/DECISIONS.md                               (B-018..B-020 + F9 1.1 ratification miras)
6. Read: docs/HEDEF.md                                   (MVP §4 C1-C11 kabul kriterleri + 30 günlük zincir)
7. ARŞİV: PaperMind_Rapor_2026-05-06.pdf artık /Volumes/RENCBER/papermind_archive_2026-05-08/papermind_docs.zip içinde
```

**Hazırlık raporu** (Claude → Omer ilk mesaj):
> "7 dosyayı okudum. Şu an: **F9 1.1 sürümü 5/8 ✅** — bugün PR #15 (listener max_tokens fix) + PR #16 (onboarding schema drift fix) + PR #17 (P095 anchor-candidates) main'e indi; pre-existing 10 fail tamamen kapandı. K-033 BRAIN.md'ye işlendi (`5896eca` brain repo lokal, push'lanacak). PaperMind proje raporu PDF Desktop'a (~877 KB) — sayfa-sayfa amaç+gösterim+durum tablosu + frontend'de mevcut ama bağlanmamış 22 kritik özellik tespit edildi. **defense-4 ReferenceIntegrityPage dosyası yok** (runtime crash bug, F9 dışı hızlı PR ile düzeltilmeli). Sıradaki: **P096** `anchor/lock` background job + ESTRA scorer + cluster_expander (~280 LOC); brief panoda. Lokal state: `papermind-app` clean main=origin (9af5be0), `papermind-brain` 1 commit ahead push'lanacak. Hazırım."

---

## 🟦 F4-S1 ÖZETİ (oturum devri için)

**Branch**: `feat/F4-frontend-shell` (off `bf5db7e` B-018 last) — lokal-only
**Commit zinciri (7)**: `add846b` plan revize → `a073b8f` P037 tooling → `22b86f4` P038 layout+tokens → `71b2877` P039+P040 sidebar+topbar+appshell → `a86c61b` P041 8 route stub → `40b16c1` P042+P043 api+types+fixtures → `772977b` P044 Suspense
**Smoke**: build PASS (0 type error, 9 route — 8 statik + 1 dinamik) · lint PASS · dev PASS (200 OK + 404 not-found)
**Tooling install**: Node v24.15.0 LTS Krypton `~/.local/share/node24` (uv pattern paralel); npm 11.12.1; 500 packages 47s
**Mockup canonical**: `~/Desktop/papermind-mockup/index.html` v3 (Omer onaylı "bu daha iyi" 2026-04-30) — design tokens kaynağı
**Plan revize**: `docs/plans/F4_frontend_skeleton_arama.md` — eski B42-050 §5 kütüphane fişi MVP'den çıkartıldı (post-MVP polish), scope F4-S1 (shell+8 stub) + S2..S5 future sprint'ler

---

## 🟧 SIRADAKİ — F4-S2 Makale Ara wiring + 9 atom community shadcn import (Omer push + onay bekliyor)

### F4-S2 başlangıç önkoşulu — KD-23 10 atom 2. konsey turu
F4-S1.5'te sadece `@shadcn/button` `--defaults` ile init edildi + mockup v3 8-anatomi override yapıldı. F4-S2 başında **community/resmi tier-1 registries** üzerinden 10 atom import edilecek (her import sonrası 8-anatomi checklist + 5-soru filter + token uyum + WCAG):

```
 1. @shadcn/sidebar       (block — mockup v3 sol panel + locked badge ile composite)
 2. @shadcn/card          (zaten Card.tsx var — primitif swap mı yoksa korunsun mu konsey kararı)
 3. @shadcn/tabs          (Top-5 "neden seçildi" stripe + paper detay sekmeleri)
 4. @shadcn/separator     (sidebar grup ayraçları + meta satır ayraçları)
 5. @shadcn/badge         (chip semantic renkler — PaperCard'da zaten var, primitif refactor)
 6. @shadcn/sheet         (mobile drawer — F4-S5 yerine S2'de drawer hazır, KD korumalı)
 7. @shadcn/skeleton      (loading.tsx 3 placeholder swap + paper detay skeleton)
 8. @shadcn/dialog        (Top-5 modal + onboarding adım adım)
 9. @shadcn/sonner        (toast — 501 banner + Nota ekle / Listeme onay feedback)
10. @shadcn/dropdown-menu (KD-26: B reading list more menu F6 + C profil avatar dropdown F5; dark overlay variant)
```

**Konsey 2. turu zorunlu** (her atom için): Defne BAĞLAYICI A satırı + Sercan alan-dışı yorum + 8-anatomi checklist verify (typography/palet/radius/shadow/spacing/transition/mikro-imza/component override) + WCAG kontrast verify + bundle size delta gözlem. Default kabul YASAK — vendor look reddi (memory: feedback_default_shadcn_yasak_8_anatomi.md).

### Visual review checklist (önce Omer)
- [ ] `cd ~/Desktop/papermind-app/web && npm run dev` → http://localhost:3000
- [ ] Sidebar Hesap grubu en altta + Ayarlar > Profilim sırası doğru mu?
- [ ] Cool-academic palet WCAG AAA hierarchy okunaklı mı? (slate-900 ink / amber-700 accent / status emerald/blue/orange/red)
- [ ] Topbar Cmd+K ikon-only button (form yok) sayfa form ile çakışmıyor mu?
- [ ] PageHeader Lora italic 28px tracking -0.015em görsel olarak akademik dergi izlenimi veriyor mu?
- [ ] PaperCard 6 action (Detay/Listeme/Özetle/Sohbet/Nota ekle/Danışmana sor) layout taşmıyor mu?
- [ ] Card 2-katman shadow + hover shadow-md tactile feel doğru mu?
- [ ] Mockup v3 ile palet+font parite tatmin edici mi (cool-paper-blue Nature/JAMA pivot kabul)?
- [ ] 8-anatomi 8 katman gözle doğrulanır mı? (font + token bg/ink + radius scale + shadow stack + spacing scale + transition + mikro-imza + component override)
- [ ] Mobile responsive 375px (Chrome DevTools) — sidebar collapse placeholder kabul mü? (S5'e ertelendi)

### Visual review + push PASS sonrası → F4-S2 plan
- Yeni mini-plan: `docs/plans/F4_S2_arama_top5.md` (yazılacak; §0..§6 + §Council 32 6-rol + Defne A satırı + Sercan alan-dışı)
- Scope: 9 atom community import (yukarıdaki sıra) + gerçek search input + filter chip (yıl/dil/alan) + URL state sync (useSearchParams + Zustand store) + apiFetchOrFixture wiring + 501→"demo verisi" Hint banner + PaperCard primitif refactor (Card+Badge swap) + Top-5 modal Dialog+Tabs "neden seçildi" stripe + **KD-24 SearchPending 3D rotating carousel** (TanStack Query isPending state'inde, 6 kart × 60° × 12s + decision_band semantic strips + ARIA role=status + prefers-reduced-motion statik fallback, ~120 LOC, atomic commit P058)
- LOC tahmini: ~800-1100 (9 atom import + override polish + arama wiring + SearchPending)
- Süre: 3-4 gün
- Council R13: 6-rol + **Defne BAĞLAYICI** (R13.9 ilk uygulamadan sonra ikinci tur) + Sercan alan-dışı yorum

### Visual review FAIL sonrası → F4-S1.6 düzeltme
- Sorun listele → Council R13 plan revize → P057-P0?? düzeltme commit'leri (palet ince ayar / nav re-order / spacing tweak / 8-anatomi checklist re-pass)

---

## ✅ BUGÜN NE YAPTIK (2026-04-30)

### 1. md dosyaları senkron + Bilinen Borçlar yansıtıldı
- `STATE.md` başlık paragrafı F2 Day 1 wrap + §7 Bilinen Borçlar bölümü 11 madde (KD-1..KD-11)
- `DECISIONS.md` B-014 entry (8 commit detayı + Council 21-24 + secret leak fix + JWT ES256)
- `NEXT_ACTION.md` (bu dosya) tam yeniden

### 2. F2 Day 1 backend kod (8 atomic commit lokal, ~3000 LOC)

| Commit | İş | Test |
|---|---|---|
| `c8c3b47` [scaffold] | initial: docs + skeleton + db/migrations 0001-0004 + .env.example | — |
| `f373e9c` [P000] | uv 0.11.8 + pyproject (PEP 621+735) + Makefile + Python 3.12.13 + ruff/mypy/pytest config + Council 21 plan boşluğu yakalama | smoke ✓ |
| `33487a6` [P001] | FastAPI 0.136 app factory + lifespan + /healthz + 3 middleware (Auth Bearer JWT verify dev mode + RateLimit sliding window 60 req/dk + Sentry init + KVKK PII scrub 5 regex) | 14 unit |
| `f632bf5` [P002] | Supabase admin/anon + Pinecone wrapper (3-retry envelope) + Redis sync/async + cache namespaces (q:1h, sum:24h, enrich:7d) + graceful degrade | 9 unit |
| `008fab8` [P003] | 5-katman ABC iskelet (Listener / Anchor / PoolRouter / Reranker / Curator) abstract method imzaları | 10 unit |
| `6e3c8f1` [P005] | PmidAnchor concrete: PartialPMID dataclass + parse_pmid + score_match (wildcard/placeholder K9 don't-care) + threshold 0.6 | 25 unit |
| `2d79ad4` [P010] | /api/search POST endpoint + Pydantic models + 5-katman mock orchestration + Redis cache (SHA-256 key) + main.py router + **live smoke 200 mock backend** | 7 integration |
| `895b05d` [P010-fix] | Council 24 düzeltmeleri: (A) Sentry breadcrumb cache fail KVKK-aware (B) signals_13 5 kanıt + 8 placeholder = 13 anahtar (C) PoolRouter.fan_out filter param ABC | 1 yeni filter test |

**Quality gate kümülatif**: ruff All checks passed + mypy strict 18 files no issues + pytest **66/66 passed** in 0.64s (58 unit + 8 integration) + live smoke `/api/search` 200.

### 3. Council 4 tur (R13)

- **Council 21**: P000 plan boşluğu yakalandı (pyproject yok), F3a §3'e P000 entry eklendi
- **Council 22**: Hibrit workflow (lokal commit-per-slice + GitHub push timing Omer kontrolünde) GREEN, mega-upload commit RED
- **Council 23**: P000-P005 retrospektif 5 GREEN + 1 YELLOW (Sentry init runtime test → KD-2)
- **Council 24**: F2 backend kod akışı 4 GREEN + 4 YELLOW → 6 GREEN düzeltme (A+B+C P010-fix; D+E Known Debt KD-2 + KD-6)

### 4. Secret leak fix (kritik güvenlik)
- B-008 sırasında `.gitignore` satır 33'e yapışmış eski HS256 service_role JWT initial commit `71cfd0a`'da yakalandı
- Lokal-only commit avantajı: `git update-ref -d HEAD` + .gitignore temizlik + reflog purged + GC ile kalıcı silindi
- Omer Supabase Dashboard işlemleri: JWT Keys → ES256 P-256 yeni signing key + API Keys → "Disable legacy API keys" + JWT Keys → Previous HS256 → Revoke
- `.env` modern keys (sb_publishable_... + sb_secret_...) ile güncel; `.env.example` ES256 JWKS endpoint pattern revize

### 5. Bilinen Borçlar (Known Debt) — 11 madde
STATE.md §7'de KD-1..KD-11 (numara çakışması, Sentry runtime, Anchor→Supabase, JWKS prod, fields trick, asyncio paralel, signals_13 tam liste, hypothesis fuzz, tier-aware rate, Pinecone broad except, Sentry lifespan smoke).

---

## ⏭️ SIRADAKİ — F2 Day 2 devam (2026-05-01, oturum 2)

### Engelleyici durumu (2026-04-30 18:00 güncelleme)

| Engel | Statü | Detay |
|---|---|---|
| **HF Inference Endpoint (Qwen anlama)** | ✅ TAMAM | `papermind-qwen` — Qwen2.5-7B-Instruct-AWQ, vLLM v0.18.1, T4 GPU eu-west-1 Ireland, $0.50/h, Scale-to-zero 15min. TR test PASS. URL: `https://rjr0wcowg9daoy2m.eu-west-1.aws.endpoints.huggingface.cloud`. `.env`'e yazıldı (HF_ENDPOINT_URL + HF_MODEL_ID + HF_TOKEN). |
| **Cosmos TR sunum endpoint** | ⏳ ERTELENDİ | Qwen TR kalitesi pilotta değerlendirilecek; yeterliyse tek endpoint ($0.50/h tasarruf). Yetersizse Cosmos ayrı endpoint kurulur. |
| **B-012 metadata patch koşum** | ⏳ DEVAM EDİYOR | Shard 2 yükleniyordu oturum kapanışında. Omer Colab. |
| **METHOD §1** | ⏳ Omer bilgisi var, paylaşılmadı | F4 önkoşulu, F2'yi engellemiyor. |

### FTS Audit sonucu (Council 25 düzeltme A)

- 0001 migration'da `pg_trgm` extension + `papers.title` trigram GIN index VAR
- `to_tsvector()` FTS index YOK — hiçbir migration'da tsvector yok
- **Kritik bulgu**: `papers` tablosu boş (lazy mirror), `fact_paper_id_card` 24.86M dolu ama title/abstract YOK. Pinecone B-012 metadata'da da title/abstract yok (sadece D/F/S/year/q_weak/method/lang/v_conf).
- **Karar gerekli**: Lexical havuzu nasıl çözülecek? 3 seçenek: (1) papers tablosuna lazy-fill + FTS, (2) Pinecone sparse Plan 2'ye ertele, (3) MVP'de semantic + theme 2-havuz RRF (lexical mock). Omer ile tartışılacak.
- 0005 migration şu an BEKLEMEDE (hedef tablo kararı sonrası).

### Yeni oturumda yapılacaklar (sırasıyla)

1. **METHOD §1 bilgisini al** (Omer paylaşacak)
2. **B-012 metadata patch sonucu kontrol** (Pinecone fetch sample 8 metadata field dolu mu?)
3. **Lexical havuz kararı** (FTS audit sonucuna göre — Omer ile tartış)
4. **P004** Listener Qwen multi-query + LiteLLM router (~250 LOC) — HF Endpoint ✅ HAZIR
5. **P006** Pool Router (semantic + theme + lexical/mock) + B-012 metadata HARD filter (~180 LOC) — B-012 sonucuna bağlı
6. **P007** Reranker BGE-reranker-v2-m3 (~100 LOC)
7. **P008** Curator + faithfulness_gate (~220 LOC)
8. **P009** Presenter dil-spesifik (~120 LOC)

**Toplam kalan F2**: 5 atomic commit ~870 LOC + integration tests + Council her commit öncesi.

### F2 Day 2 sonrası

- F2 PR + push GitHub (Hibrit workflow Omer "şimdi push" dediğinde)
- F3 sprint başlar (chat + summarize + enrichment + reading-list — F3b/c/d/e mini-planlar mevcut)

---

## 🛑 KOD ÖNCESİ %100 PLAN — MUTLAK KURAL (R1 / DM-008)

> Master plan + F3a-F3e + F4-F7 + 2 ortak servis spec **11 plan dosyası onaylandı**. F2 Day 1 8 commit (~3000 LOC) plan'a sadık. F2 Day 2 P004-P009 dış engelleyici sonrası R13 council her atomic commit öncesi yeniden.
> 7-kontrol her öneride zorunlu (DM_RULES R2). R13.3 council her atomic commit öncesi (Council 21-24 örnek). Sycophant yasak.

---

## CEVAP BEKLEYEN — Omer'den

| # | Soru | Engellediği | ETA |
|---|---|---|---|
| **B-012 koşum** (yarın Colab + Pinecone bulk import) | Omer | F2 P006 + P008 | yarın |
| **METHOD §1** Akademik Mekanlar mekan modeli onayı | Omer | F4 frontend skeleton (F2'yi engellemiyor) | TBD |
| **OPEN-005** Top 5 onay margin eşiği (default 0.7) | Omer | F5 P050 chat clarify branch | F5 öncesi |
| **OPEN-006** Ghost cache TTL (7d master vs 90d DM-006 L1) | Omer | F3d enrichment + F6 P060 | F3d öncesi |
| **OPEN-007** Pilot 5 user listesi | Omer | F7 P072 invite | F7 öncesi |
| **OPEN-DD4** Dark mode MVP'de mi? | Omer | F4 + Faz 2 (B42-050 §1.2) | pilot sonrası |
| **NPS hedefi C11** (≥+30 vs ≥+50 vs ≥0) | Omer | F7 P074 | F7 öncesi |
| **Pilot süresi** (14 gün vs 21 gün) | Omer | F7 | F7 öncesi |
| Lokal 8 commit GitHub'a push timing | Omer | F2 PR + Sercan brief | "şimdi push" dediğinde |

## CEVAP BEKLEYEN — Sercan'dan

| # | Soru | Engellediği |
|---|---|---|
| **HF Inference Endpoint kurulumu** (Qwen2.5 anlama + Cosmos TR sunum 2 endpoint + keep-alive 240s) | F2 P004 + P007 + P009 + F7 P069 |
| MiniCheck NLI fine-tune indir + ALCE recall implementation (faithfulness_gate ortak servis) | F2 P008 + F3c P022 |
| Sentry organization + project + alert rules | F7 P065 |
| Render service + Vercel project + custom domain DNS | F7 P068 + P070 |
| Magic-link e-mail provider (Supabase Auth default veya custom SMTP) | F5 P046 |

---

## DEVAM EDEN (paralel arka plan)

| İş | Statü | Kim |
|---|---|---|
| N11 v2 sentence_persist | ✅ KAPANDI 2026-04-29 (193,653,620 satır) | — |
| Redis paper+theme curation | ⏳ Omer manuel | Omer |
| Krippendorff α validation 30 paper | ⏳ ~2 gün manuel | Omer + 3 etiketleyici |
| GhostCard spot check 50 paper | ⏳ ~1 gün manuel | Omer |
| **B-012 Pinecone metadata patch koşum** (yarın 4-5h Colab) | ⏳ in-flight | Omer |
| **HF Endpoint setup** | ⏳ Sercan | Sercan |

---

## SIRADAKİ FAZLAR (B-001 master §9 ile uyumlu)

| Faz | Ne | Süre | Mini-plan | Statü |
|---|---|---|---|---|
| F1' | Master Plan + F3a-F3e + F4-F7 + 2 ortak servis spec | 1+1 gün | F1 + F3a-e + F4-7 + spec | ✅ 2026-04-29..30 |
| **F2 Day 1** | Backend skeleton + /api/search slice (P000-P010 + P010-fix) | 1 gün | F3a §3 | ✅ 2026-04-30 (B-014) |
| **F2 Day 2** | Listener + PoolRouter + Reranker + Curator + Presenter (P004 + P006-P009) | 1-2 gün | F3a §3 | ⏳ B-012 + HF |
| F3 | Backend kalan 4 endpoint (P010-P036) + Faithfulness gate ortak refactor + Celery setup | 4-5 gün | F3b/c/d/e + 2 spec | ⏳ F2 PASS |
| F4 | Frontend skeleton + E4 Arama Next 16 (P037-P043) | 3-4 gün | F4_*.md | ⏳ F2 + METHOD §1 |
| F5 | E1 Onboarding + E2 Chat SSE + E3 Top-5 + i18n migration (P044-P052) | 4-5 gün | F5_*.md | ⏳ F4 + F3b |
| F6 | E5 Detay + Summarize + Ghost (P053-P061) | 4-5 gün | F6_*.md | ⏳ F4+F5+F3c+F3d+F3e |
| F7 | Quality + Sentry + Docker + HF + Vercel + 5 pilot 14 gün (P062-P074) | 3-4 gün kod + 14 gün pilot | F7_*.md | ⏳ F2-F6 |

---

## HALÜSİNASYON RİSKLERİ (Claude'a uyarı)

1. **F3a P010 vs F3b P010 numara çakışması** (KD-1, B-010'dan miras): F3 sprint'inde Sercan `[P010a]` + `[P010b]` ayrıştırmalı
2. **B42-050 §10 i18n** B-005 ile geçersiz; F4 §1'de açıkça yazılı
3. **Master §3 vs §7 onboarding endpoint çelişkisi**: §3 üstün, F5 §1 Supabase RLS upsert
4. **OPEN-005/006 frontend transparent**: backend kararı, frontend sadece event/poll render eder
5. **HF Endpoint cold start** doğrulanmadı — pilot ile ölçülecek (C7 ≥%95 warm)
6. **5 user NPS directional** (C11 ≥+30): gerçek NPS Faz 2 N=20 sonrası; F7'de yanında CSAT 5-point + open-ended
7. **OpenAlex polite pool 100K req/gün**: 2026'da değişmiş olabilir, F3d öncesi Sercan doğrulama
8. **Playwright E2E F4-F6'dan F7 P071'e ertelendi** (Council 14-16 Fayda-Maliyet düzeltmeleri)
9. **MockX implementations** (P010): P004-P009 swap edildiğinde `api/services/_mocks.py` silinecek/extended
10. **8 commit henüz GitHub'da yok**: lokal-only; push timing Omer kontrolünde (Hibrit workflow)
