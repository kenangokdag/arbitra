# MVP Canlı Test İş Planı (Master)

> **Tarih:** 2026-05-13 gece audit · canlı test hedefi **2026-05-16 (3 gün)**
> **Repo:** `/Users/omer/papermind-app` · **Branch:** `design/sayfa-plani-v2` (48 commit ahead origin/main)
> **Kanun:** CLAUDE.md §0 plan-first. Her madde için ayrı plan manifest + Omer "plan onaylandı" onayı sonrası kod.

---

## §0 — Audit özeti (Explore agent, 2026-05-13 gece)

Uçtan uca codebase taraması (`api/routes/`, `web/src/components/project/`, `db/migrations/`, `deploy/`, `.github/workflows/`) sonucu:

| Katman | Durum | Kanıt |
|---|---|---|
| **Backend** | 23 route dosyası, **stub yok** — hepsi Supabase + LLM bağlı | api/routes/*.py · servis çağrıları + LLMServiceError handling |
| **Frontend** | 27 sayfa, **3 sayfa hâlâ mock/fixture** | aşağıda §1 detay |
| **DB** | 33 migration uygulanmış (Supabase live) | db/migrations/00*.sql |
| **Deploy** | `deploy/render.yaml` hazır (web + 5 cron job) | render.yaml:1-194 |
| **CI/CD** | `.github/workflows/polish_gate.yml` sadece TODO marker check | build/test pipeline YOK |
| **Auth** | Supabase JWT verify + dev fallback | api/middleware/auth.py:68-80 |
| **Sentry** | init kodu hazır, DSN manuel girilecek | api/middleware/sentry.py:49-61 |
| **Pilot/invite** | **YOK** — sadece `waitlist` tablosu var (0017) | grep "invite|allowlist" → 0 hit |

**Sonuç:** Backend/DB tamam. 3 sayfa wiring + 1 endpoint + manuel ops adımları MVP'yi açar.

---

## §1 — Kritik açık iş listesi (P0/P1/P2)

### 🔴 P0 — Canlı test'i engelliyor

| # | İş | LOC | Plan | Bağımlılık |
|---|---|---|---|---|
| **A1** | `POST /research-area/anchor/lock` endpoint | ~110 | `docs/plans/V1_S15_pre_anchor_lock.md` ✅ | §3.1 açık sorulara cevap |
| **A2** | ResearchAreaConfirmPage `PARSED` fixture → gerçek `/research-area/messages` parsed_understanding | ~80 | yazılacak (V1-S16) | A1 öncesi de yazılabilir; bağımsız |
| **A3** | ResearchAreaConfirmPage "ÇAPA SEÇ" CTA → A1 endpoint çağrısı | ~50 | yazılacak (V1-S16) | A1 |
| **A4** | Render deploy + env vars + smoke `/healthz` | manuel | — | tüm kod canlı olduktan sonra |

**Kanıt-A:**
- A1: bugün doğrulandı, `grep anchor_paper_id api/` boş.
- A2: `ResearchAreaConfirmPage.tsx:58` `const PARSED = {...}` (kanıt: yorum satırı 13 "PARSED + ANCHORS hala fixture").
- A3: aynı dosyada "ÇAPA SEÇ" → POST `/anchor/lock` çağrısı yok.
- A4: render.yaml hazır ama production env hiç çalıştırılmamış.

### 🟡 P1 — Canlı test'i kalitesizleştiriyor ama açmıyor

| # | İş | LOC | Plan |
|---|---|---|---|
| **B1** | ConceptNetworkPage NODES/EDGES → `/api/workshop/concept-network` endpoint + FE bağlama | ~280 | `docs/plans/V1_S15_concept_network_wiring.md` ✅ |
| **B2** | ReferenceStylePage 10-kaynak fixture → `project_papers` + `/api/workshop/citation-format` (P074-077 backend hazır) | ~120 | yazılacak (V1-S17) |
| **B3** | Pilot/invite sistemi — basit: Supabase allowlist tablosu + auth middleware kontrol | ~150 | yazılacak (V1-S18) |
| **B4** | TopicSuggestionPage sabit "MCDM..." sorgusu → anchor context'inden gelen query | ~60 | yazılacak (V1-S19) — F9 §75 P096 partial |

**Kanıt-A:**
- B1: `ConceptNetworkPage.tsx:29-83` hardcoded array; bugünkü V1-S15 plan'ı zaten hazır.
- B2: backend endpoint P074-077 var (F13 sprint commit), FE bağlanmamış.
- B3: agent audit'i pilot/invite kodu bulamadı; waitlist tablosu var ama gating yok.
- B4: `TopicSuggestionPage.tsx:25-30` default query SABIT "MCDM cok kriterli karar verme" (kanıt: 2.2_konu_belirleme.rtf:124-127).

### 🟢 P2 — MVP sonrası

| # | İş | Not |
|---|---|---|
| **C1** | GitHub Actions full CI (lint+test+build) | Şu an polish_gate.yml sadece marker check |
| **C2** | Load test (50 concurrent, OpenAlex quota) | Render Starter cold-start riski test edilmeli |
| **C3** | Stage C `cluster_expander.py` (500-paper havuz, ESTRA scorer) | F9 P096, ~280 LOC; B1'i daha zengin yapar |
| **C4** | LightGBM ESTRA kalibrasyonu | F7+, proxy ağırlıklar şu an deterministik |

---

## §2 — Sıralı zaman planı (3 gün, 2026-05-14..16)

### Gün 1 (yarın, 2026-05-14)

**Sabah blok:**
1. V1-S15.pre §8 5 açık soruyu cevapla (15 dk).
2. **A1 anchor/lock** uygula — V1_S15_pre_anchor_lock.md §6 sıra: P001 Pydantic → P002 servis → P003 route + testler (3 commit).
3. Smoke: yerel `uv run pytest api/tests/services/test_anchor_lock.py` PASS.

**Öğle:**
4. **A2 + A3** plan manifest yaz: `docs/plans/V1_S16_research_area_confirm_wiring.md` (parsed_understanding FE wiring + ÇAPA SEÇ button).
5. Onay → uygula (2-3 commit).
6. Smoke: yerel `npm run dev` → `/project/{id}/discovery-1` golden path manuel test (Stage A sohbet → 3 odak onay → 3 anchor candidate → ÇAPA SEÇ → 2.2'ye geçiş).

### Gün 2 (2026-05-15)

**Sabah:**
7. **B1 ConceptNetwork** — V1_S15_concept_network_wiring.md (zaten yazılı) anchor lock'a göre revize → onay → uygula.
8. **B2 ReferenceStyle** plan + uygula.

**Öğleden sonra:**
9. **B3 pilot/invite** — basit allowlist tablosu + middleware. Mini-plan + 1-2 commit.
10. Yerel full smoke: onboarding → proje aç → 2.1 → 2.2 → 2.5 Kavram Ağı → atölye 3.x → 6.x defense → kapanış. 10 sayfa manuel tur.

### Gün 3 (2026-05-16) — Canlı test

11. `git push origin design/sayfa-plani-v2` → PR aç (review yok, tek geliştirici).
12. Merge → main.
13. **A4 Render deploy** (manuel ops):
    - Render Dashboard → Connect repo → render.yaml otomatik.
    - Env vars manuel: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_SECRET`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, `SENTRY_DSN`, `REDIS_URL`.
    - Deploy → `/healthz` 200 doğrula.
14. **Vercel deploy** (FE):
    - Vercel Dashboard → import repo → `web/` root.
    - Env vars: `NEXT_PUBLIC_API_URL` (Render endpoint).
15. **Smoke canlı**: 1 pilot user (Omer kendisi) — onboarding → 1 proje uçtan-uca.
16. **Pilot invite** 2-3 kullanıcıya gönder.

---

## §3 — Yarın karar verilecek açık sorular

### 3.1 V1-S15.pre anchor lock 5 sorusu
(Plan §8'den; bugün önerilerim verildi.)
1. İki kere lock → 409 (önerim) / sessiz idempotent.
2. Aday listede olmayan paper_id → 409 (önerim) / 422.
3. Lock sırasında `projects.current_stage = 'topic_selection'` aynı transaction (önerim) / ayrı endpoint.
4. Response'da `cluster_status: 'pending'` (önerim) / yok.
5. 202+job_id (F9 spec) yerine 200 senkron (önerim, Stage C yok) → kabul mü?

### 3.2 ConceptNetwork V1-S15 plan revize durumu — KAPALI (2026-05-13)
- `docs/plans/V1_S15_concept_network_wiring.md` **2026-05-13'te canlı Supabase kanıtıyla revize edildi**:
  - İki kimlik uzayı: `fact_term_arm_static.term_a/b` (integer-as-text "2213") vs `dim_term_community.term` (T-prefix "T10050") — match `dim_term_community.extra->>'term_id'` üzerinden.
  - Çift-yön sorgu zorunlu (tek yön ~%50 edge kaybı).
  - 11 community → 4 Tableau renk modulo.
  - Default anchor = T10050 (MCDM).
- Karar: ek revize gerekmiyor. B1 implementasyonu mevcut plan'a göre yürür.

### 3.3 Pilot kullanıcı listesi
- Kaç kişi (3 / 5 / 10)?
- Davet kanalı (e-mail / manuel allowlist / waitlist UNLOCK)?
- Kapsam: sadece Omer + 1-2 yakın akademisyen mi, yoksa waitlist'ten cherry-pick mi?

### 3.4 Branch politikası
- `design/sayfa-plani-v2` 48 commit ahead; PR mı tek-shot merge mi?
- Hibrit workflow B-014 default: lokal-first, Omer "şimdi push" deyince push.

### 3.5 Mock sayfa kapsam kararı
- Audit'e göre ConceptNetwork + ReferenceStyle + ResearchAreaConfirm-parsed kaldı.
- TopicSuggestionPage SABIT "MCDM..." sorgusu (kanıt: 2.2 RTF §124-127) — MVP'ye dahil mi yoksa P2'ye mi?
- Önerim: **dahil** (B4 olarak) çünkü 2.1→2.2 geçişinde anchor context taşımıyor, kullanıcı garip görür.

---

## §4 — Manuel ops checklist (Gün 3)

Omer'in Render/Vercel/Supabase dashboard'larında yapacağı işler:

### Render (papermind-api)
- [ ] GitHub repo connect (`ofrencber/PaperMind` veya muadili)
- [ ] `render.yaml` otomatik algılansın
- [ ] Env vars (7 adet, secrets):
  - `SUPABASE_URL`
  - `SUPABASE_SECRET_KEY` (service_role)
  - `SUPABASE_JWT_SECRET`
  - `GEMINI_API_KEY`
  - `PINECONE_API_KEY`
  - `SENTRY_DSN`
  - `REDIS_URL` (Render Redis service'i otomatik kurar render.yaml ile)
- [ ] Deploy → `https://papermind-api.onrender.com/healthz` 200 doğrula
- [ ] Cron job 5 adet aktif mi (`completion_delete_expired`, `diary_unresolved_weekly`, `diary_monthly_digest`, `method_centrality`, `neighbor_bibcoupling`)?

### Vercel (papermind-web)
- [ ] GitHub repo connect, root `web/`
- [ ] Framework: Next.js (otomatik)
- [ ] Env var: `NEXT_PUBLIC_API_URL = https://papermind-api.onrender.com`
- [ ] Deploy → preview URL'i Omer aç, ilk sayfayı gör

### Supabase (production)
- [ ] Supabase project zaten var (session pooler :5432 ile yüklendi)
- [ ] RLS policies aktif (her tabloda owner-only)
- [ ] Auth: e-mail magic link enable, custom SMTP opsiyonel

### Sentry
- [ ] Project oluştur, DSN Render env'e yapıştır
- [ ] PII scrub middleware'de aktif (api/middleware/sentry.py)

---

## §5 — Risk + plan B

| Risk | Olasılık | Mitigasyon |
|---|---|---|
| Render cold-start ilk request 30-60s | Yüksek | Keep-warm cron job (her 14 dk `/healthz` ping) — `render.yaml`'a ek |
| OpenAlex rate-limit pilot trafikten patlayabilir | Orta | `polite_pool` header zaten var (F3d); 5 user düşük risk |
| Gemini API quota daily limit | Düşük | Project ID Google Cloud Console'dan quota artır |
| Anchor lock A1 yarın bitmezse | Düşük | Sadece A1 alır 1h; testler dahil 2-3h |
| ConceptNetwork B1 revize gerekirse | Orta | Plan'ı yarın sabah revize et + onayla; alternatif: B1'i Gün 3'e kaydır, B3 pilot'u önce |

---

## §6 — Uyum sinyali (executor için)

Yarın çalışan asistan **doğrulamadan başlamasın**:

- [ ] CLAUDE.md §0 okundu (plan-first canon)
- [ ] Bu master plan'ın tarihi 2026-05-13/14
- [ ] V1-S15.pre §8 5 sorunun cevabı Omer'den alındı
- [ ] `git status` clean (sadece 0033 migration + colab notebook untracked beklenir)
- [ ] Her P0/P1 işi için ayrı mini-plan manifest yazılır, sonra kod

Aksi halde **STOP**, plan revize.

---

## §7 — Closure kriterleri (MVP canlı test PASS)

Bu liste yeşilse MVP canlı test başlamış sayılır:

- [ ] A1 anchor/lock endpoint canlıda, 200 dönüyor
- [ ] A2 + A3 ResearchAreaConfirmPage anchor seçimi → 2.2'ye geçiş
- [ ] B1 ConceptNetwork canlı veriyle render (Supabase concept tabloları okunuyor)
- [ ] B2 ReferenceStyle gerçek `project_papers` listesi gösteriyor
- [ ] B3 sadece allowlist'teki user'lar giriş yapabiliyor
- [ ] A4 Render `/healthz` 200, Vercel FE açılıyor
- [ ] 1 pilot user (Omer) onboarding'den proje kapanışına kadar uçtan-uca gitti
- [ ] Sentry hata yakalıyor (test exception ile doğrulanmış)

---

**Sonraki adım (yarın sabah):** §3 5 başlığa cevap → V1-S15.pre "plan onaylandı" → A1 kod.
