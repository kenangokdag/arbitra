# World-Class Transformation State — GERÇEKLİK SENKRONU

> **2026-06-25 gece — otonom inşa koşumu (Omer uyuyor).** Bu dosya pack'in `not_started`
> varsayımını DEĞİL, kodun GERÇEK durumunu yansıtır. Reality scan 5 paralel ajan + file:line
> kanıt + toolchain baseline (688 backend test pass) ile doğrulandı.

## Temel gerçek

Repo **greenfield DEĞİL** — olgun PaperMind/Arbitra monorepo'su. Pack'in "P00 not_started /
her şey generic" varsayımı **worldclass dönüşümü** içindir; gerçek kod (F14 hakemlik) çok ileride:
S1–S6 + eval bitmiş, **688 backend test PASS** (doğrulandı, iddia değil), FE tsc EXIT 0,
Deploy hedefi: Render (deploy/render.yaml — api + managed redis + 6 cron; canlı durum doğrulanmadı).

## Baseline (2026-06-25 gece, bu makinede koşuldu — kanıt)

- Backend: `uv run pytest -q` → **688 passed, 2 skipped** (223s)
- FE: `npx tsc --noEmit` → EXIT 0 temiz; `vitest` → 187 pass / 1 fail (`tts-api.test.ts`, review-dışı pre-existing)
- Ruff: 51 hata (pre-existing, 21 auto-fix, çoğu import sıralama)
- Toolchain: uv 0.11.24 + Python 3.12 + node deps kuruldu (bu makinede yoktu, kuruldu)

## Pack boyutları — GERÇEK durum (reality scan, file:line kanıtlı)

> ⚠️ **SÜPERSEDED satırlar (2026-06-26 doğrulama):** Aşağıdaki tablo 25-Haz GECE reality-scan'idir
> — motor dalgaları (FAZ A-E2 / task ENG-1/2/3) BU SCAN'DEN SONRA indi. P03/P04/P06 "MISSING/PARTIAL"
> satırları artık ESKİ; motor kodda VAR (doğrulandı 2026-06-26): `engine/academic/classifier.py`,
> `qualitative_engine.py`, `quantitative_engine.py`, `council.py`, `report_synthesis.py` +
> `SupportLevel`/`risk_radar`/`action_plan` (`api/models/review.py`). Güncel durum için "Current phase"
> + dalga logu esastır; tablo tarihsel referanstır.

| Pack boyut | Durum | Kanıt / not |
|---|---|---|
| P00 marka/kimlik | **DONE** | `web/src/lib/brand.ts:5` BRAND="ARBITRA", ArbitraWordmark var |
| P01-T01 auth forge | **PARTIAL** | forge-path kapalı (`auth.py:103-121`) AMA APP_ENV default `development` (config.py:17) → unset prod'da fail-OPEN; FE sadece mock auth (`web/src/lib/auth.ts:16-39`) |
| P01-T02 BOLA | **DONE (gece)** | owner check VAR + negative-access testleri eklendi (`test_sec3_upload_and_bola.py`: B kullanıcı A'nın job'unu okuyamaz → 404) |
| P01-T03 consent | **DONE (SEC-2)** | `consent_gate.py` + gate `review_service.py` run_pipeline; gizli+rıza-yok → LLM ÇAĞRILMAZ (test: run_orchestration spy n==0) |
| P01-T04 quota fail-closed | **DONE (SEC-1)** | prod boot fail-fast (`config_validation.py`); Redis-down prod→503 (`tier_gate.py _quota_backend_unavailable`) |
| P01-T05 dosya güvenliği | **PARTIAL (gece)** | zip solid + magic-byte/MIME doğrulama eklendi (`routes/review.py _validate_magic`); **retention/delete DONE (cbc7126)**: delete_after + cron silme (UI "dosya silinir" sözü tutuluyor); PARK→Omer kalan: parser hard-timeout (subprocess izolasyonu = mimari karar), audit-events alt-sistemi |
| P02-T01 stage schema | **PARTIAL** | flat status+progress; v2 stage modelleri SPINE-1'de (`review.py` ReviewStageState) ama runner henüz per-stage yazmıyor |
| P02-T02 durable workflow | **PARTIAL (gece)** | idempotency dedup (`create_and_dispatch`+idx 0042) + stale-sweep (`mark_stale_jobs_failed`+/admin/sweep-stale); PARK→Omer: gerçek resume = object storage + ayrı worker (deploy) |
| P02-T03/04 provider abstraction | **PARK→Omer** | ScholarlyProvider yeni soyutlama deseni = mimari karar (YASA 3); gece yapılmadı |
| P02-T05 degraded/provenance | **DONE (BE-2)** | `find_coverage_gaps` artık SESSİZ empty-list DEĞİL → re-raise; `EvidencePack.degraded_features` GÖRÜNÜR (test: coverage:openalex_unavailable) |
| P03 classifier+rubric | **MISSING** | DocumentType/StudyDesign classifier YOK; DimensionKey fixed 10-list herkese aynı; checklist iskeletleri wire edilmemiş |
| P03-T04 qualitative engine | **MISSING** | hiç yok; mevcut persona quant-bias |
| P03-T05 quantitative engine | **PARTIAL** | statcheck (p-value) VAR; ~9 boyut (causal/power/missing-data) yok |
| P04 claim/anchor/support | **PARTIAL** | reference resolution GÜÇLÜ+honest (koru); manuscript-anchor/claim modeli + 5-değer SupportLevel YOK |
| P06 report v2 + council | **PARTIAL** | gerçek adversarial loop VAR (writer+5critic+editor, `review_orchestration.py:101`); ama free-form, typed v2 (verdict/risk_radar/council[]/action_plan) YOK |
| P07 eval | **PARTIAL (gece)** | harness honest; CI smoke gate eklendi (`test_gate.yml`); `run_eval --live`=NotImplementedError; goldset thin (5, Omer N≥10 dolduracak) |
| P09 CI/audit/ops | **PARTIAL (gece)** | CI test-gate eklendi (`test_gate.yml`: 733 test + eval smoke); env boot-validation VAR (SEC-1); Sentry solid; audit events PARK→Omer |
| FE cockpit | **PARTIAL** | review FE %100 real-API (mock YOK!); v1 typed render var; wizard/consent/cockpit-v2/drawers SPINE-1'e bağlı |

## Güçlü varlıklar (KORU, dokunma)

- Citation resolution motoru (`review_citation_service.py:150-299`) — DOI+fuzzy, **uydurmuyor**, R-1 honest
- Adversarial orkestrasyon (writer + 5 critic + editor synthesis) — gerçek, evidence-grounded
- Provenance (judgment layer) — model/persona/engine version, honest `judgment_reproducible=False`
- Zip güvenliği — bomb/traversal/size limitleri
- Sentry KVKK PII scrub

## İnşa sırası (omurga → kabuk, madde 12)

SPINE-1 (veri sözleşmesi v2) = yük taşıyan karar; HEM akademik motor HEM FE cockpit ona bağlı.
Sıra: SPINE-1 → [SEC-1/2/3 ∥ BE-1/2 ∥ ENG-1→2→3] → QA-1 → FE-COCKPIT. FE-SAFE paralel.

Todolist: harness TaskList (#1..#14). PARK (#14) = Omer-kararı, gece yapılmaz.

## Current phase
- Phase: **OTONOM YÜRÜTME — marka + landing + KVKK hesap-silme TAMAM** (b098cce). Omer "otonom yürüt" dedi;
  güvenli-tamamlanabilir işler kapatılıyor, Omer-kararı/deploy PARK. Her dalga: builder→bağımsız doğrula→
  AYRI auditor (mutation/security)→commit+push.
- Test baseline: **880 backend passed, 2 skipped** (863→880: +7 retention, +17 account-deletion); FE **249/249
  vitest** (+3 ConfirmDialog), tsc 0, lint temiz. **CI test-gate YEŞİL**.
- DALGA marka (e54fe27): chrome'dan PaperMind silindi (31 dosya) → Arbitra canonu (BRAND/ArbitraWordmark);
  PaperMindLogo emekli. DALGA landing (44b5507): yanlış-ürün (gap-analiz) → saf hakemlik landing; hero=bağımsız
  hakem paneli (Omer onayı); kanıt-çıpası minyatürü; KVKK/gizlilik bölümü; tüm demo "Örnek değerlendirme";
  FE-excellence audit GO + 3 craft fix (WaitlistModal token+dialog a11y, koyu kontrast AA, dead-button).
- DALGA KVKK (b098cce): hesap silme ANINDA hard-delete (Omer seçimi) — account_deletion_service (14 direct +
  projects cascade 7 + review_job + enrichment nötrle + waitlist email-purge + auth.admin.delete_user SON;
  GLOBAL tablolara ASLA dokunmaz). DELETE /api/account (confirm_phrase) + DELETE /api/review/jobs/{id} (BOLA→404).
  FE: /settings tehlikeli-bölge + ConfirmDialog (typed-gate, a11y) + review-delete. Security audit GO (BOLA+
  global-koruma+sıra KANITLI; mutation-gap'ler hardcoded-set ile kapatıldı). Sahiplik haritası: 60 tablo file:line.
- DALGA retention+tts (cbc7126): **KIRIK SÖZ** kapatma — UI (review/page.tsx:647) "dosya silinir" vaat ediyordu ama
  hiçbir şey süresi geçen review_job'u silmiyordu (retention_days yalnız yakalanıyordu). project_completion deseninin
  aynası: migration 0044 review_job.delete_after (additive+idempotent+backfill+index) · _insert_job insert anında
  delete_after=now+retention_days · cron review_retention_delete_expired (cutoff Python-ISO, PG 'now()' parser'ına
  bağlı değil) · render.yaml 04:30 UTC cron (review izole Supabase). tts: jsdom Blob.arrayBuffer yoktu → vitest.setup
  FileReader polyfill (gerçek, stub değil). Adversarial audit: **GO** — no-op şüphesi gerçek PG16'da çürütüldü
  ('now()'::timestamptz=now() → t; süresi geçen silinir, NULL güvenle atlanır) + 2 hardening fix uygulandı
  (ISO cutoff + non-vacuous cron testi: fake .lt() artık argümanı kaydedip predicate uyguluyor, lt→gt/kolon mutasyonu yakalanır).
- CANLIYA-ÇIKIŞ TESTİ (yazılım GO): backend 856 + prod fail-fast kapısı (eksik env→boot reddedilir, doğru→geçer) +
  FE `next build` temiz (14 route, 0 uyarı) + canlı uvicorn smoke (/healthz + GET /api/app/theme default döndü,
  Redis yoksa degrade). BULUNAN+DÜZELTİLEN: boş REDIS_URL boot çökmesi (from_url ValueError→redis.ConnectionError;
  artık degrade, uvicorn ile uçtan uca doğrulandı). Deploy = kod değil: secrets + migration apply + gerçek-tarayıcı göz.
- CI FIX (e1927a2): kök neden = OPENALEX_EMAIL boş-olmayan default → get_reranker gerçek BgeReranker → HF model
  yükleme CI'da offline fail (c087281'den beri kırmızıydı). conftest get_reranker→MockReranker override (test niyeti;
  BgeReranker test_reranker_bge.py'de scorer-injection ile ayrıca kapsanır). Boş-cache+offline 852 ile kanıtlı.
- FAZ 4 (3b6f921 BE + f649bab FE): admin tema — migration 0043 app_theme_settings (APPLY=go-live) + ThemeSettings
  (hex/font validation) + theme_service (fallback, sahte-başarı yok) + GET public/PATCH admin-only router · FE
  ThemeProvider (app ASLA kırılmaz, çift savunma) + /admin/theme form (canlı önizleme + WCAG kontrast readout + 5
  durum) + 5 font next/font yüklü. İkincil: orphan-action yok (çift-yönlü köprü) · çift findings-testid ayrıldı.
  BE-auditor 4/4 mutation GO · FE-auditor 6/6 mutation GO.
- Test baseline (önceki): **841 backend / FE 225/226** @ b369fd8.
- FAZ 1 (caee216): G1 evidence_anchors ÇIKARILDI (ölü konteyner, anti-fabrikasyon) · G2 acceptance_check boru-hattı
  testli · G3 SectionReview "missing" üretiliyor (IMRaD beklenen-bölüm, named-constant+Omer-flag) · G4 per-stage
  emit (StageTimeline canlı). Auditor: 4/4 GERÇEK, sahte-yeşil yok, anti-tahrifat temiz.
- FAZ 2 (b369fd8): ReviewReportView 3-katman kokpit (Katman1 verdict-hero · Katman2 risk→bulgu→çıpa→fix drill =
  İMZA ANI · Katman3 uzman collapse) · 2B finding↔action köprü · 2C upload 3-adım · 2D canlı progress · 2E 5-durum ·
  AnchorDrawer focus-trap+odak-iadesi (a11y blocker fix). DESIGN-DECISIONS.md soul-gate. FE-auditor: A/B/D GERÇEK.
- AÇIK (ikincil, OPEN_WORK): yetim-action_item backend doğrulaması · çift `findings` testid · action-item>=2 kapsam.
- ESKİ baseline notu (tarihsel): önceki faz **822 backend / FE tsc temiz**.
- FAZ dalgaları (her biri uygulayıcı→bağımsız doğrulama→AYRI auditor→commit): A (ENG-1 classifier+rubric) · B (ENG-2 qual/quant/general engines) · C1 (deterministik sentez+anchor doğrulama+support-level) · C2 (uçtan uca pipeline + typed council) · D (provider abstraction) · E1 (FE v2 render) · gap-closure (support_level CANLI) · E2 (consent wizard). 8 commit push'landı (origin/worldclass/build = 80d3dfd).
- GO-LIVE / KILIF (Omer/deploy — backbone değil): **DEPLOY ŞABLONU HAZIR** → `.env.production.example` +
  `deploy/DEPLOY_CHECKLIST.md` + render.yaml düzeltildi (eksik FRONTEND_ORIGINS prod-FATAL'di → eklendi +
  ADMIN_USER_IDS/REVIEW_SUPABASE_*/BGE_WARMUP). Kalan operatör adımları: secrets gir (FRONTEND_ORIGINS!,
  auth, GEMINI/PINECONE/SENTRY/ADMIN), migration 0042+0043 apply (DATABASE_URL=... apply_migrations.sh), canlı smoke +
  gerçek-tarayıcı göz testi. Ek backbone: durable resume+worker, eval --live goldset N≥10.
- DEPLOY YOLU: **Railway seçildi** (Omer). Config repo'da HAZIR + doğrulandı: API `railway.json`+root `Dockerfile`
  (uvicorn /healthz smoke ✓); FE `web/railway.json`+`web/Dockerfile` (npm ci+build+start → / ve /review 200 ✓).
  Docker imaj build'i lokalde doğrulanamadı (docker yok; adımlar tek tek geçti). Render (`deploy/render.yaml`) =
  alternatif, repo'da duruyor. AÇIK: Railway cron servisleri (Render'daki 6 cron Railway'de henüz config'siz).
  DÜZELTME: önceki "FE config YOK = gap" notu YANLIŞTI — config 25 Haz'dan beri vardı (eksik kontrol, madde 7).
- LATENT CI RİSKİ — DÜZELTİLDİ/ÇÜRÜTÜLDÜ (2026-06-26 doğrulama): önceki not "entegrasyon testleri CANLI OpenAlex'e gidiyor" diyordu — YANLIŞ. Kanıt: `test_skeleton_endpoints.py:133` `_fetch_openalex` patch'liyor; `test_q_routes.py:117/124` `search_papers`/`fetch_papers_by_ids` mock; `test_review_citation.py:9` "gerçek OpenAlex çağrısı YOK"; `test_openalex_polite` `_CountingTransport`. Tüm testler ağı MOCK'luyor → CI zaten hermetik + offline-enforced (HF_HUB_OFFLINE=1) + yeşil. Hardening gerekmez (fantom gap).
- TİCARİ GATING (Omer marka kararı, PARK): review şu an tam-açık, paywall yok. "Verdict ücretsiz / fix-derinliği ücretli" çizgisi kokpit Katman-3 ayrımına doğal map olur.
- FLAG→Omer kararı (yeni alt-sistem/politika): audit-events (10), retention/delete (KVKK), parser hard-timeout (subprocess), interactive revision-board (BE revision-state).
- Bilimsel-audit→Omer: rubrik ağırlıkları + verdict eşikleri + classifier isabet + engine kriter sadakati (hepsi versiyonlu named-constant, OPEN_WORK.md'de listeli).
- CANLI DURUM (2026-06-27): **pazarlama canlıda.** Web servisi düzeltildi (rootDirectory=web → Next.js; önceki
  bug: kök railway.json web'e API imajı build ediyordu). `/landing`+`/ornek-rapor` 200, API sağlam. Lansman kapısı
  (`web/src/middleware.ts` + `LAUNCH_MODE=marketing`, commit 7084c4f) app rotalarını `/landing`'e 307 yönlendiriyor.
  BLOKE (Omer dashboard): API'ye SUPABASE_URL/SECRET_KEY + JWKS/JWT + WAITLIST_BYPASS=false TOPLU girilmeli — yoksa
  redeploy fatal'la API'yi brick'ler (config_validation). Waitlist şu an KALICI DEĞİL (double-POST 2×200 kanıtı).
  Detay + kök-neden: OPEN_WORK.md "FAZ F" + D bölümü 🔴. FE gerçek auth (auth.ts mock) hâlâ PARK.
- Owner: yönetici=main `worldclass/build`. Last updated: 2026-06-27.
