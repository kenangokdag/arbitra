# Açık İşler — Arbitra Worldclass (gerekçeli)

> Kaynak: gece otonom koşum (2026-06-25/26). Bu dosya `OPEN_WORK.log`'un (gitignore'da, local)
> izlenebilir/GitHub'a giden karşılığıdır. Her madde NEDEN açık olduğunu söyler.
> Durum: 688 → 735 test geçiyor; bağımsız adversarial audit GO (koşullu).

## A. Senin alanın — bilimsel motor (YASA 4: alan doğruluğu yalnız Omer)
> Sözleşme (SPINE-1, `api/models/review.py` v2 blok + migration 0042) HAZIR; motorları ona bağlayacağız.

- [ ] **ENG-1 (P03-T01/02/03):** Belge + çalışma türü classifier (DocumentType/StudyDesign) + RubricRegistry.
      Şu an DimensionKey sabit 10-liste herkese aynı. Bilimsel rubrik kuralları Omer'den.
- [ ] **ENG-2 (P03-T04/05):** Qualitative rigor motoru (hiç yok) + Quantitative validity
      (statcheck p-value VAR; causal/power/missing-data ~9 boyut yok). Alan kuralları Omer'den.
- [ ] **ENG-3 (P04-T01/03 + P06-T01/02):** Claim/manuscript-anchor + 5-değer SupportLevel +
      Report v2 (verdict/risk_radar/council[]/action_plan) + typed council. Model var, montaj Omer ile.
- [ ] **Eval --live + goldset N≥10:** şu an goldset 5 girdi, `run_eval --live`=NotImplementedError.
      Gerçek kalite kanıtı için Omer goldset doldurur + LLM key + PDF→Manuscript parser hattı bağlanır.

## B. Mimari / deploy / storage kararı (YASA 3: kilitli plan dışı, tek başına yapılmadı)
- [ ] **Provider abstraction (P02-T03/04):** ScholarlyProvider yeni soyutlama deseni = mimari karar.
      Şu an raw OpenAlex polite-pool çağrısı business logic'te.
- [ ] **Gerçek durable resume + ayrı worker (P02-T02):** upload baytlarını object storage'a
      (S3 / Railway volume) yazmayı gerektirir = deploy + maliyet kararı. Şu an: idempotency dedup +
      stale-sweep VAR (orphan iş dürüstçe failed("interrupted")); tam "kaldığı yerden devam" storage sonrası.
- [ ] **Audit-events (10 olay, P01-T05/P09):** yeni alt-sistem + muhtemel yeni tablo + RLS = tasarım kararı.
- [x] **Retention OTO-SİLME — DONE (cbc7126):** UI'nin "dosya silinir" sözü artık tutuluyor. migration 0044
      review_job.delete_after + _insert_job set + cron review_retention_delete_expired (delete_after<cutoff). Audit GO.
- [x] **Manuel silme + KVKK hesap silme — DONE (b098cce):** DELETE /api/review/jobs/{id} (BOLA-safe→404) +
      DELETE /api/account (anında hard-delete, Omer seçimi). account_deletion_service: 14 direct + projects
      cascade + review_job + enrichment nötrle + waitlist email-purge + auth.admin.delete_user; GLOBAL korunur.
      FE /settings tehlikeli-bölge + ConfirmDialog. Security audit GO (BOLA+global-koruma KANITLI). Sahiplik
      haritası: 60 tablo file:line doğrulandı. Rate-limit (MINOR, self-scoped) bilerek eklenmedi.
- [ ] **Parser hard-timeout:** CPU-bound sync parse'ı gerçekten kesmek subprocess izolasyonu ister
      (Python'da thread öldürülemez); dürüst hard-timeout = tasarım kararı. grobid I/O zaten timeout=30.
- [ ] **Read-path RLS:** şu an BOLA app-layer ownership check tek savunma (yeterli ama ölçekte RLS) — audit INFO notu.

## C. Tasarım (FE — madde 12 anti-toolbox: görsel kimlik Omer onayı)
> FE iskelet + tip katmanı hazır (review FE %100 real-API, mock YOK). Görsel kimlik pass'i Omer ile.
- [ ] **FE-SAFE:** landing görsel kimliği (Arbitra), sample-report sayfası, security sayfası.
- [ ] **FE-COCKPIT:** wizard + consent UI, cockpit v2, drawers, revision board (SPINE-1 v2 tüketimine bağlı).

## D. Canlı-öncesi zorunlu adımlar (PARK #14 — Omer/deploy)
- [ ] **Migration 0042 APPLY (Supabase):** idempotency'nin SERT garantisi `idx_review_job_idempotency`
      bu index. Uygulanmadan dedup yalnız best-effort ön-kontrol. **Canlı smoke'tan ÖNCE şart.**
- [ ] **🔴 API secrets — BİRLİKTE girilmeli (yoksa redeploy API'yi brick'ler):** `config_validation.py`
      fatal'da `ProductionConfigError` raise eder → boot reddedilir (`main.py:92`). Şu an prod API env'inde
      İKİ fatal koşul aktif: `WAITLIST_BYPASS=true` + auth provider yok (`SUPABASE_JWKS_URL`/`SUPABASE_JWT_SECRET`
      ikisi de yok). Çalışan API yalnız eski boot anının env'iyle ayakta; **herhangi bir env değişikliği redeploy
      tetikler → fatal → API çöker.** O yüzden tek başına `WAITLIST_BYPASS=false` YAPILMADI (canlı API'yi öldürürdü).
      Omer dashboard'dan API servisine TOPLU girmeli (ana Supabase projesi): `SUPABASE_URL` · `SUPABASE_SECRET_KEY`
      (service-role) · `SUPABASE_JWKS_URL` **veya** `SUPABASE_JWT_SECRET` · `WAITLIST_BYPASS=false`.
- [ ] **🔴 Waitlist KALICI DEĞİL (kanıtlanmış, 2026-06-27):** canlı API'ye aynı e-posta 2× POST → ikisi de
      `200 ok:true` (kalıcı olsa 2.→409 already_queued). Kök neden: `SUPABASE_URL`/`SUPABASE_SECRET_KEY` yok →
      `waitlist.py:_supabase()` None → insert ATLANIR, sahte-200 dev-fallback. Yukarıdaki secrets girilince
      double-POST testi + landing formundan E2E tekrar koşulacak (2.→409 = kalıcılık kanıtı).
- [ ] **FE gerçek auth (Supabase Auth swap):** `web/src/lib/auth.ts` hâlâ MOCK forge-token. Lansman kapısı
      (`LAUNCH_MODE=marketing`) app yüzeyini kapattı; auth gelince kapı kalkar. App'in canlı kullanımı buna bağlı.
- [ ] **CI ilk push teyidi:** `test_gate.yml` Actions'ta yeşil mi (lokalde offline 735 geçiyor; runner'ı
      lokalde çalıştıramadım — Omer Actions sekmesinde görmeli).
- [ ] **İlk canlı uçtan-uca smoke:** gerçek makale → consent → pipeline → rapor render (FE auth + secrets sonrası).

## Gece BİTEN (referans, kapatıldı)
- [x] SPINE-1 sözleşme v2 (additive) · SEC-1 boot fail-fast + quota fail-closed · SEC-2 consent gate
- [x] BE-2 degraded görünür · SEC-3 magic-byte + BOLA testleri · BE-1 idempotency + stale-sweep
- [x] QA-1 CI test-gate · Audit-fix (CI offline + idempotency yarış-güvenli)

## FAZ A (ENG-1) — BİTTİ + audit GO (2026-06-26). Omer bilimsel-audit'te bakacak:
- Rubrik AĞIRLIKLARI v1 varsayılan (engine/academic/rubric_registry.py `_RUBRICS`), normalize=1.0 ama bilimsel kalibrasyon DEĞİL → Omer ayarlar.
- "Soft" boyut→engine eşlemesi (contribution/theory/venue_fit → ClaimEvidence/Citation/Ethics/Structure/Guideline) v1 konvansiyon, spec'te birebir yok → Omer onayı.
- mixed_methods metodoloji v1'de quant-arm'a düşüyor → Omer onayı.
- review_mode v1'de boyutları değiştirmiyor (ton orchestration'da) → Omer onayı.
### FAZ A audit minör notları (yazılım):
- [LOW/fail-closed] external_ai_allowed(None)=True (SEC-2 geri-uyum, tested) + run_pipeline privacy default None → teorik açık-varsayılan. Bugün route hep PrivacyConfig üretiyor (exploit YOK). Semantiği değiştirmek SEC kontrat kararı → Omer/ileride, sessiz değiştirme YOK.
- [FAZ-B'ye taşındı] classifier per-stage izolasyon sarmalı yok; classify_document asla raise etmiyor diye güvenli. ENG-2 motorları raise edebilir → FAZ B'de her motor çağrısı degraded-izolasyonla sarılacak (coverage stage gibi).

## FAZ B (ENG-2) — BİTTİ + audit GO (2026-06-26). 761 test. Omer bilimsel-audit:
- Genel engine "intent" cümleleri (dimension_engine.py _DIMENSION_INTENT) spec etiketlerinden TÜRETİLDİ (kriter uydurulmadı, ama ifade benim) → Omer onayı.
- Metodoloji rubrik dim'leri domain-engine'in kendi 12/10 alt-boyutuyla TOPLU kapsanıyor (dim-bazlı değil) → Omer onayı.
- mixed_methods metodolojisi v1'de yalnız quant engine'i tetikliyor → Omer onayı.
- theoretical/conceptual/design_science/dataset/software/protocol tasarımları metodolojide GENEL prompt alıyor (tailored değil) → ileride özelleştirme.
### FAZ C ZORUNLU carry-forward (audit'in iki kez vurguladığı):
- [SEV-MED] Yüksek-severity KANIT DOĞRULANMAMIŞ: anchor quote'ları manuscript.full_text'e karşı DOĞRULANMALI (uydurma quote yakalanmalı); `global_issue=true` tek başına anchor-gate'i geçiyor → FAZ C bunu güvenmemeli, global_issue-only finding'leri ağırlık/confidence-düşürmeli veya işaretlemeli.

## FAZ C1 — BİTTİ + audit GO (2026-06-26). 800 test. Omer bilimsel-audit + FE notu:
- Verdict v1 varsayılan eşikleri (report_synthesis.py named constants): RADAR_SEVERITY_PENALTY {critical45/major25/moderate12/minor5}, reject@critical≥1, major_revision@major≥1, minor_revision@moderate≥1, WEAK_EVIDENCE_WEIGHT=0.4, TOP_FATAL_RISKS_MAX=5 → Omer kalibre eder.
- _DIMENSION_KEYWORD_MAP (serbest finding.dimension → 10 spec radar boyutu) v1 anahtar-kelime eşlemesi → Omer onayı.
- [FE notu] executive_verdict.recommended_decision (severity-sayım) ile overall_readiness_score (10-boyut ortalama) farklı şeyler ölçer → "reject @ 89/100" çelişki gibi GÖRÜNMESİN; FE ikisini birlikte+açıklamalı sunmalı (FAZ E).
- full_text_verified pratikte üretilmez (sistem abstract çekiyor) → tam-metin provider gelene dek abstract_only tavan (spec'e sadık).

## FAZ C2 — BİTTİ + audit GO (2026-06-26). 806 test. ENGINE OMURGASI (A+B+C) TAMAM.
- run_pipeline artık uçtan uca v2: classify→rubric→assess→verify_anchors→synthesis→council; disclosure normal yolda; degraded görünür.
- Council role mapping v1 (novelty_critic→field_expert; _ROLE_DIMENSIONS) → Omer bilimsel-audit.
- ethics_reviewer/statistics_reviewer enum'da var ama v1'de critic eşlenmiyor (engine findings/risk_radar kapsıyor) → Omer onayı.
- Provenance rubric_id/SYNTHESIS_VERSION engine_version string'ine ekleniyor (ReviewProvenance extra=forbid) → isteğe bağlı first-class alan.
- Degraded yolda v2 sentez alanları BOŞ (dürüst: inceleme yok→uydurma yok).

## FAZ D — BİTTİ + audit GO (2026-06-26). 820 test. Provider abstraction (additive).
- ScholarlyProvider Protocol + ProviderSnapshot + OpenAlexProvider adapter; snapshot'lar evidence.provider_snapshots'a görünür. Taç mücevher (citation service) HİÇ değişmedi.
- Gate "business logic raw-URL bilmez" KISMİ: adapter hazır, tam Protocol-routing provider #2 (Crossref/S2/PubMed) ile yapılacak (taç mücevher korunması için ertelendi).
- OPENALEX_PROVIDER_VERSION="2026-06" varsayılan (openalex_polite'te versiyon yok) → şema değişince elle bump.
- [LOW backlog] Transient-servis-hatası not-found ile gerçek not-found yapısal olarak ayrılmıyor (fark evidence free-text'te). Başlıksız+abstract'sız manuscript coverage-tripwire'ı atlar. Exploit yok, fabrication yok. → ileride structured resolution_error flag.
- get_citations NotImplementedError (dürüst, silent-empty değil) — live path'te çağrılmıyor; citation-graph işine ertelendi.

## FAZ E1 — BİTTİ + audit GO koşullu (2026-06-26). FE v2 render. tsc temiz, 5/5 test.
- 10 spec render bölümü mevcut shell+token ile (görsel kimlik DEĞİL — kılıf go-live). Drawer+degraded+empty dişli.
- Fixture 0-1→0-100/1-10 ölçek düzeltmesi LEGİTİM (kontrat ge/le ile uyumsuzdu).
- [DEBT] v1-backward-compat testi isV2 guard'ını pinlemiyor (mutasyon geçti) → gap-closure'da sertleştirilecek.
### DEAD-CODE / UNWIRED envanteri (audit JOB B — C1/C2/D kaçırdı):
- [TRUE DEAD → gap-closure'da KAPAT] map_support_level + 6-değer SupportLevel (kontrat taşıyıcısı yok) + EvidenceBadge (FE bağlanmamış). Spec gate "citation support level gösterir" KARŞILANMAMIŞ → CitationContextFinding'e support_level (additive) + populate + EvidenceBadge render.
- [UNWIRED → dormant-by-design dokümante et] OpenAlexProvider.get_references/_with_snapshot: ScholarlyProvider Protocol tamlığı, citation-graph feature'ı (live review'da tüketici yok) → get_citations gibi açık deferral yorumu ekle.
- [DORMANT-BY-DESIGN, kabul] get_citations (NotImplementedError dokümante); StageTimeline + ReviewJob.stages/ReviewStageState (BE-1 status'e stages ekleyince canlanır, FE gated+yorumlu).

## GAP-CLOSURE — BİTTİ + audit GO (2026-06-26). 822 BE test. Dead code KAPANDI.
- support_level uçtan uca CANLI: check_context map_support_level'i çağırıyor (review_citation_service.py:513) → CitationContextFinding.support_level (6-değer) → FE EvidenceBadge render. Spec gate "citation support level gösterir" KARŞILANDI.
- abstract-only → full_text_verified yapısal olarak İMKANSIZ (full_text_verified=False hardwired, mutasyon-kanıtlı).
- v1-backward-compat testi dişlendi ("Yönetici özeti" v1'de absent — isV2 mutasyonu artık yakalanıyor).
- get_references/_with_snapshot: dürüst deferral notu (Protocol tamlığı, citation-graph future) — dormant-by-design.

## FAZ E2 — BİTTİ + audit GO (2026-06-26). Consent wizard upload'da.
- uploadReview 4 privacy alanını backend Form adlarıyla BİREBİR gönderiyor; SEC-2 consent artık FE'den erişilebilir.
- Consent copy consent_gate davranışına DÜRÜST (confidential+rıza-yok→deterministik-only; mutasyonla pinlendi). Fail-safe cascade.
- [FLAG, kapsam dışı] İnteraktif revision board (action'ları işaretle/takip) yeni BE revision-state ister (rapor read-only) → feature, backbone-consume değil.
- [DORMANT] StageTimeline canlı değil: status response per-stage state yaymıyor (BE-1 durable worker'a bağlı) → BE-1 tamamlanınca canlanır.

## FAZ F — Deploy / canlıya çıkış (2026-06-27). Pazarlama canlıda; app secrets'a bağlı bekliyor.
> Omer kararı: "şimdilik sadece pazarlamayı canlıya al" + app secrets'ı kendi dashboard'undan girer.
> Railway proje "Arbitra": web + api + grobid + Redis (servisler git-bağlı DEĞİL, `railway up` ile deploy).

### BİTEN (kanıtlı, canlı doğrulandı)
- [x] **Marka/landing/KVKK/örnek-rapor** dalgaları main'e merge + push (FF, CI yeşil).
- [x] **🔧 Web servisi kök-neden düzeltmesi:** kökteki `railway.json` (dockerfilePath=API) `railway up`'ta web'e
      API imajını build ediyordu (web domain API JSON sunuyordu). Düzeltme: web serviceInstance `rootDirectory="web"`
      (GraphQL `serviceInstanceUpdate`) → her build `web/railway.json`+`web/Dockerfile` (Next.js) kurar. Footgun temelli kapandı.
- [x] **Web canlı (Next.js):** `/landing` 200 (Arbitra hakemlik), `/ornek-rapor` 200, `/healthz` 404 (API değil). API servisi sağlam (env=production 200, dokunulmadı).
- [x] **Lansman kapısı (commit `7084c4f`):** `web/src/middleware.ts` — `LAUNCH_MODE=marketing` env'i set; app/kokpit/admin
      rotaları → `/landing` 307 (12 rota canlı test, sızıntı yok). Flag kalkınca tam app açılır (geri-alınabilir,
      koda dokunmadan). Not: Next 16 `middleware`→`proxy` deprecate uyarısı (çalışıyor; ileride `proxy.ts`'e taşınabilir).

### BLOKE (Omer'in dashboard'una bağlı — bkz D bölümü 🔴 maddeleri)
- [ ] API secrets TOPLU girişi (redeploy brick riski) → waitlist kalıcılığı + auth-provider fatal'ı + `WAITLIST_BYPASS=false`.
- [ ] Secrets sonrası: double-POST 409 testi + landing formundan E2E + (FE auth gelince) tam app smoke.

### Railway kaynak kimlikleri (referans)
- project `6ea1c04b-0101-459d-bfb8-b8f88d7fa00a` · env(production) `6f002ac5-bee9-491f-bb95-594c3dabd5b4`
- web `147e7166-...` (rootDirectory=web, LAUNCH_MODE=marketing) → web-production-64ccd.up.railway.app
- api `4ee11816-...` → api-production-88ca.up.railway.app · grobid `879e6914-...` · Redis `9e28a82d-...`
