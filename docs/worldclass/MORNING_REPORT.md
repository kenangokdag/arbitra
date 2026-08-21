# Sabah Raporu — Otonom Gece Koşumu (2026-06-25)

> Omer, gece otonom kod işini bitirdim. Bu rapor: **ne yaptım** (kanıtlı), **ne parka aldım**
> (neden), **sabah ne yapacağız** (canlı denemeye giden yol). Sahte başarı yok — her iddia
> commit + test sayısı ile bağlı.

## 1. Tek cümle karar
**Omurga (test-edilebilir backend) sağlamlaştı: 688 → 735 test geçiyor (+47), 8 dalga commit'lendi,
bağımsız adversarial audit GO (koşullu) verdi.**
Kalan iş bilinçli olarak SENİN alanın: bilimsel motor (ENG), tasarım (FE), deploy kararları.

## 2. Gece biten dalgalar (hepsi `uv run pytest -q` ile doğrulandı)

| Dalga | Ne yaptım | Kanıt | Test |
|---|---|---|---|
| **SPINE-1** | Veri sözleşmesi v2 (additive — 688 test korundu) | `api/models/review.py` v2 blok + `0042` migration | 698 |
| **SEC-1** | Prod boot fail-fast + quota Redis-down→503 | `config_validation.py`, `tier_gate.py` | 706 |
| **SEC-2** | External-AI consent gate (gizli dosya rızasız LLM'e GİTMEZ) | `consent_gate.py` + run_pipeline gate | 714 |
| **BE-2** | Sağlayıcı arızası SESSİZ değil GÖRÜNÜR | `find_coverage_gaps` re-raise + `degraded_features` | 716 |
| **SEC-3** | magic-byte dosya doğrulama + BOLA sahiplik testleri | `_validate_magic`, `test_sec3_upload_and_bola.py` | 728 |
| **BE-1** | Idempotency dedup + stale-job sweep | `create_and_dispatch` + `mark_stale_jobs_failed` | 733 |
| **QA-1** | CI test-gate (733 test + eval smoke) | `.github/workflows/test_gate.yml` | 733 |

Commit'ler `worldclass/build` dalında, **local** (push'u senin onayına bıraktım — YASA 3 geri-dönülmez kapı).
Son 7 commit: `git log --oneline -7`.

## 3. En kritik güvenlik kazanımları (canlı-öncesi şart)
- **Gizlilik vaadi artık backend'de zorunlu:** gizli hakemlik dosyası + açık rıza yoksa external
  LLM **çağrılmıyor** (test bunu spy ile kanıtlıyor: `run_orchestration` çağrı sayısı = 0).
- **Prod yanlış-config ile AÇILMIYOR:** WAITLIST_BYPASS=true veya auth-provider yok veya
  FRONTEND_ORIGINS boşken `APP_ENV=production` → boot reddediliyor (fail-fast).
- **Quota backend düşerse prod'da 503** (eskiden fail-open = bedava sınırsız kullanım riski).
- **Disguise dosya reddi:** uzantısı .pdf ama içi ELF/HTML olan dosya gate'te 400.

## 4. Parka aldıklarım — NEDEN (bunlar gece YAPILMADI, bilinçli)

### 4a. Senin alanın (YASA 4 — bilimsel/alan doğruluğu yalnız sende)
- **ENG-1/2/3** (classifier + rubric + qualitative/quantitative motor + claim-anchor + council v2):
  Bunlar bilimsel yargı. Sahte sayı/rubrik üretmektense **seninle sabah** yapmak doğru.
  Veri sözleşmesi (SPINE-1) HAZIR — motorları ona bağlayacağız.

### 4b. Mimari/deploy kararı (YASA 3 — kilitli plan dışı, tek başıma karar vermem)
- **Provider abstraction (ScholarlyProvider):** yeni soyutlama deseni = mimari karar.
- **Gerçek durable resume + ayrı worker:** upload baytlarını object storage'a yazmayı gerektirir
  (S3 / Railway volume) = deploy + maliyet kararı. Şimdilik **stale-sweep** orphan işi dürüstçe
  `failed("interrupted")` yapıyor (sonsuz dönen çark yok), ama gerçek "kaldığı yerden devam" senin
  storage kararından sonra.
- **Audit-events (10 olay):** yeni alt-sistem + muhtemel yeni tablo + RLS = tasarım kararı.
- **Retention/delete endpoint:** KVKK silme politikası kararı.
- **Parser hard-timeout:** CPU-bound sync parse'ı gerçekten kesmek subprocess izolasyonu ister
  (Python'da thread öldürülemez) — dürüst hard-timeout = tasarım kararı.

### 4c. Tasarım (FE — madde 12 anti-toolbox, görsel kimlik senin onayın)
- Landing görsel kimliği, sample-report sayfası, security sayfası, cockpit v2, wizard/consent UI.
  FE iskelet/tip katmanı hazır; görsel kimlik pass'i seninle.

## 5. Doğrulama sınırları (dürüst itiraf)
- **CI workflow'u lokalde GitHub-runner olarak çalıştıramadım** (act yok). İçindeki komutlar
  lokalde geçiyor (pytest 733, eval exit 0). İlk push'ta Actions sekmesinde yeşili **sen görmelisin**.
- **`run_eval --live` gerçek kalite kanıtı vermiyor** — goldset 5 girdi (N≥10 lazım) + LLM key +
  PDF→Manuscript parser hattı ister. Dry-run İLLÜSTRATİF (banner+_warning ile işaretli).
- **Migration 0042 lokal DB'ye apply edilmedi** (Supabase bağlı değil); SQL additive + rollback'li,
  apply'ı canlı-öncesi adımda yapacağız.

## 5b. Bağımsız adversarial audit (YASA 4 — builder ≠ auditor)
Ayrı bir audit ajanı gece işini **kırmaya çalıştı** (sadece yazılım/güvenlik/dayanıklılık).
Sonuç: **dolandırıcılık YOK, testlerin dişi var** (3/3 mutasyon testi yakalandı — üretim
satırını bozunca ilgili test fail etti), consent/BOLA/magic-byte/degraded gerçekten üretim
kodunu çalıştırıyor. Karar: **GO (koşullu)**. İki bulgusu vardı, **ikisini de düzelttim**:
- **[MEDIUM] CI ağ bağımlılığı:** test paketi collection'da canlı HuggingFace indiriyordu →
  CI flaky olabilirdi. `test_gate.yml`'e `HF_HUB_OFFLINE=1 + TRANSFORMERS_OFFLINE=1` eklendi.
  Kanıt: offline tam paket **735 pass** (68s, ağsız). CI artık deterministik.
- **[LOW] Idempotency yarış 500'ü:** eşzamanlı ikili submit'te insert unique-index'e çarpınca
  kullanıcıya 500 dönebilirdi. `create_and_dispatch` artık yarışı çözüyor (insert hatası →
  yeniden lookup → kazanan işi döndür; gerçek hata → yine fırlat). +2 test.
- Auditor'ın kalan notları (benim düzeltmediğim, çünkü senin/deploy alanın): **migration 0042
  canlı-öncesi APPLY edilmeli** (idempotency'nin sert garantisi o index), read-path için **RLS**
  ileride (şu an app-layer ownership check tek savunma) — INFO seviyesi.

## 6. Sabah planı (canlı denemeye giden yol)
1. **Migration 0042 apply** (Supabase) — sözleşme v2 kolonları canlıya.
2. **ENG-1 birlikte:** belge/çalışma türü classifier + rubric registry — bilimsel kurallar senden.
3. **Railway secrets + WAITLIST_BYPASS=false** + FE auth provider seçimi (PARK #14).
4. **İlk canlı smoke:** bir gerçek makale yükle → uçtan uca (consent → pipeline → rapor).
5. CI ilk push → Actions yeşil teyidi.

## 7. Açık iş kaydı
Tüm parklar gerekçeli `OPEN_WORK.log`'da. TaskList #8/#9/#10 (ENG) + #12/#13 (FE) + #14 (PARK) açık.
