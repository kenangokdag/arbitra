# SPRINT_HISTORY.md — PaperMind App Sprint Log'u

> **Format:** P-NNN her atomic commit grubu (her faz birden fazla P olabilir)
> **Numara başlangıcı:** P001 (decisionmind-v2 P107'siyle ayrı)
> **Eklenme:** Her atomic commit + ROL 1 §8 PASS sonrası

---

## P000 — F0 Hazırlık (BU SPRINT)

**Tarih:** 2026-04-29
**Tip:** STANDART (klasör + skeleton + dokümantasyon)
**Süre:** ~30 dk

**Yapıldı:**
- [x] `~/Desktop/papermind-app/` klasör ağacı oluşturuldu (35 alt-klasör)
- [x] Skeleton dosyalar yazıldı:
  - `README.md` (public-facing intro)
  - `CLAUDE.md` (oturum protokolü)
  - `.gitignore` + `.env.example`
  - `docs/DM_RULES.md` (R1-R12 kurallar)
  - `docs/STATE.md` (F0 + faz tahminleri)
  - `docs/DECISIONS.md` (DM-001..DM-012)
  - `docs/NEXT_ACTION.md` (lean-back pointer)
  - `docs/ARCHITECTURE.md` (v0.1 mimari skeleton)
  - `docs/SPRINT_HISTORY.md` (bu dosya)
  - `reference/README.md` (read-only işaret)

**Bağlama:**
- DM-001 klasör adı `papermind-app/`
- DM-008 plan-first kuralı (R1)

**Sonraki:** F1' Master Plan + 5 mini-plan (B-001)

---

## B-001 — F1' End-to-End Master Plan + 5 mini-plan teslimi

**Tarih:** 2026-04-29
**Tip:** STANDART (plan manifest yazımı, kod yok)
**Süre:** ~1 gün
**Karar referansı:** DECISIONS.md B-001 (ŞARTLI KABUL — backend-first pivot)

**Yapıldı:**
- [x] `docs/plans/F1_master_plan.md` (~600 satır §0..§18, master tek doğruluk)
- [x] `docs/plans/F3a_search.md` (P001-P009: /api/search 5-katman slice)
- [x] `docs/plans/F3b_chat.md` (P010-P016: /api/chat SSE + IntentPMID + topic-lock)
- [x] `docs/plans/F3c_summarize.md` (P017-P023: /api/summarize Celery + Qwen+Claude 2-stage)
- [x] `docs/plans/F3d_enrichment.md` (P024-P030: /api/enrichment OpenAlex polite pool)
- [x] `docs/plans/F3e_reading_list.md` (P031-P036: /api/reading-list CRUD + RLS)
- [x] `docs/DECISIONS.md` B-001 entry + B42-046/047/048/049/050 miras
- [x] `docs/STATE.md` backend-first pivot uyarlaması
- [x] `docs/NEXT_ACTION.md` 6-adım açılış + 4 kritik engelleyici listesi

**Bağlama:**
- DM-008 plan-first mutlak kuralı
- DM-013 Next.js 16 (master §1 ile uyumlu)
- DM-014 Render backend
- B42-046/047/048/049/050 dondurulmuş referans

**Şartlı kabul önkoşulları (Omer aksiyonu):**
- OPEN-001 LLM model adı (Qwen2.5-7B-Instruct AWQ?)
- OPEN-003 12 chip listesi
- OPEN-004 Pipeline_Akis canonical
- B42-046 Papermind_V2/DECISIONS.md entry yazılması
- Pinecone upload (24.87M × 1024-d)
- Supabase project init + schema_v1 (11 tablo MVP)

**Sonraki:** F2 P001 — `feat/F2-search-skeleton` branch + `api/main.py + 3 middleware` (yukarıdaki 6 önkoşul tamam olunca)

---

## B-002 — Supabase project + schema_v1 migration

**Tarih:** 2026-04-29 (20:29 UTC)
**Tip:** STANDART (infra provision + DDL migration)
**Süre:** ~10 dk
**Karar referansı:** DECISIONS.md B-002

**Yapıldı:**
- [x] Supabase project provisioned: `ewggwvadfqwkxgddywma` (eu-central-1 Frankfurt, KVKK uyumlu, Free tier)
- [x] `.env` lokal yazıldı (URL + sb_publishable_ anon + DB Session Pooler URL) — gitignored
- [x] `.env.example` Pinecone index adı `papermind-corpus` → `papers-bgem3` master ile hizalandı
- [x] `db/migrations/0001_init_schema_v1.sql` yazıldı (~330 satır)
- [x] psql Session Pooler üzerinden migration uygulandı, 0 hata
- [x] Audit: 12 tablo + 19 RLS policy + 9 trigger + 6 enum + 2 extension (pgcrypto, pg_trgm) doğrulandı

**12 tablo (master §5 + dim_ghost_paper eklendi F3d için):**
papers · dim_ghost_paper · dim_theme · user_profiles · user_quota · chat_sessions · chat_messages · topic_locks · user_reading_list · summary_cache · enrichment_log · schema_migrations (meta)

**Bağlama:**
- B-001 §14 Supabase init önkoşulunu kapatır
- F3a P002 supabase_client wrapper artık bağlanabilir
- DM-014 Postgres backend (Render değil — Supabase managed Postgres MVP için)

**Beklenen ek (Omer aksiyonu):**
- `service_role` key paylaşımı (admin operations + RLS bypass için backend tarafı)
- `JWT_SECRET` paylaşımı (auth middleware verify için)
- Bu 2 değer `.env` placeholder'da bekliyor (Settings → API → Reveal)

**Sonraki:** F2 önkoşul kalan 5 madde — Pinecone upload (in-flight) + OPEN-001/003/004 + B42-046

---

## B-003 — Supabase static fact stack upload (4 tablo, 562,931 satır)

**Tarih:** 2026-04-30
**Tip:** STANDART (DDL migration + bulk data load)
**Süre:** ~30 dk (notebook yazımı + 4 cell upload + teşhis döngüsü 1)
**Karar referansı:** DECISIONS.md B-003

**Yapıldı:**
- [x] `db/migrations/0002_static_facts.sql` (~110 satır, warehouse parquet ile birebir aynalı schema)
- [x] `scripts/colab_load_static_facts.ipynb` (8 cell: setup → audit → DDL → 4 upload → verify; 17 cell toplam)
- [x] Migration 0002 Colab Cell 3'ten uygulandı (idempotent IF NOT EXISTS + DROP/CREATE policy)
- [x] Drive parquet → Session Pooler bulk upload (CHUNK 50K + page_size 5000-2500)
- [x] **dim_theme** 4,516 satır (parent FK)
- [x] **dim_theme_embedding** 4,516 × 256-d (pgvector text-cast format, HNSW cosine indexed)
- [x] **fact_theme_year_aggregates** 53,943 × 15 (theme_id format `T`-prefix normalize patch ile)
- [x] **fact_gap_matrix** 504,436 × 12 (M8=427,063 + M1=56,192 + M7=21,181)
- [x] Cell 8 verify: 4/4 row count ✓ + pgvector cosine smoke (T11791 top-5 sim 0.64-0.82) ✓ + gap_value top-5 ✓

**Bulgu (öğrenme):**
- `fact_theme_year_aggregates` parquet'inde `theme_id` T-prefix YOK (örn. `10001`); diğer 3 tabloda VAR (örn. `T10001`); FK violation 53,943/53,943 → patch ile çözüldü.
- ENVANTER §3 + §10.1 schema A-evidence kullanıldı; planlama hiyerarşisi (B42-039/L-013) doğrulandı.

**Bağlama:**
- B-002 Supabase init üzerine atomic ekleme
- DM_RULES R6 (atomic commit + audit trail)
- F2 P002 supabase_client wrapper artık static fact lookup yapabilir
- F3b chat IntentPMID için pgvector theme similarity kullanılabilir (256-d cosine)

**Sonraki:** F2 önkoşul kalan 4 madde (Pinecone upload Omer in-flight + OPEN-001/003/004 + B42-046 onay)

---

## B-008 — Faz 1 PaperCard + GhostCard upload (Migration 0003)

**Tarih:** 2026-04-30
**Tip:** STANDART (DDL migration + bulk data load, 1 gün erken)
**Süre:** ~1h45m (PaperCard 54m39s + GhostCard ~50m)
**Karar referansı:** DECISIONS.md B-008

**Yapıldı:**
- [x] `db/migrations/0003_paper_anchor_facts.sql` (~140 satır, PaperCard + GhostCard schema warehouse-mirror)
- [x] `scripts/colab_load_paper_anchor.ipynb` (6 cell: setup → audit → migration 0003 → PaperCard upload → GhostCard upload → verify)
- [x] Migration 0003 Cell 6 üzerinden uygulandı (CHECK dominant_type ∈ {C,M,E,R,B} + ON DELETE CASCADE FK için 0004)
- [x] **PaperCard** 24,862,232 satır (envanter 24,866,945 / Δ=-4,713 dominant_type filter, beklenen)
- [x] **GhostCard** 31,855,437 satır (Δ=+0, tam parity)
- [x] Cell 6 verify: row counts ✓ + dominant_type histogram (C 52.75% / E 26.76% / B 8.14% / M 8.09% / R 4.26%) + PMID K6 ✓ + JSONB topic_profile avg 2.80 ✓ + is_suspicious 20,675 (envanter 20,677, Δ=2) + triage_priority 4 grup tam parity (75,159 / 143,877 / 540,123 / 31,096,278) + disk 28 GB

**Süreç içi vakalar:**
- (1) **ReadOnlySqlTransaction** — KeyboardInterrupt sonrası conn read-only kaldı; kök neden tam tespit edilmedi (Supabase pooler retry / `set_session(readonly=True)` şüphesi). Temiz conn ile sarılarak bypass edildi. **Known Debts kaydı.**
- (2) **4,713 skipped_dom_invalid** — Cell 8 `_norm_dom` filter + 0003 `CHECK (dominant_type IN ...)` zinciri; veri kaybı yok, schema gereği zorunlu filtre. DQ kaydı gereksiz; ENVANTER §10.1 W-36 effective row count notu yeterli.

**Bağlama:**
- B-002 + B-003 üstüne Faz 1 ana corpus anchor
- F2 backend `B-02 /api/papers/{id}` (PaperCard) + `B-03 reading-list` 3-katlı DOI fallback (GhostCard) için kritik veri katmanı
- xlsx Sheet 6 M-4c "🟡 KISMEN ✅" — Faz 2 sıradaki

**Sonraki:** B-009 (notebook FK guard) → Faz 2 (S3a satellite tabloları) → Faz 3 (graf gövdesi, ipynb yazılacak)

---

## B-009 — paper_satellites notebook FK guard patch

**Tarih:** 2026-04-30
**Tip:** HIZLI DÜZELTME (notebook patch, kod 7 satır)
**Süre:** ~5 dk
**Karar referansı:** DECISIONS.md B-009

**Yapıldı:**
- [x] `scripts/colab_load_paper_satellites.ipynb.bak.20260430` yedek alındı
- [x] **Cell 2 (Setup)** sonuna ~5 satır eklendi: PaperCard'dan tüm `paper_id`'leri belleğe yükle → `VALID_PAPER_IDS` global set (~24.86M, ~2 GB RAM, 2XL'de OK)
- [x] **Cell 8 (stream_upload helper)** içine 3 satır eklendi: `if row[0] not in VALID_PAPER_IDS: skipped += 1; continue` (FK guard, tek noktada — 3 upload otomatik kapsanır)
- [x] **Cell 13 (markdown)** yanlış FK açıklaması düzeltildi: "ON CONFLICT DO NOTHING ile FK violation olmaz" → "Cell 2 VALID_PAPER_IDS anti-join ile elenir; ON CONFLICT PK için" (ON CONFLICT FK violation'ı yakalamaz)
- [x] Edit verify: 3 hücre değişikliği `python3` ile re-read ✓

**Bağlama:**
- B-008'in sonucu (4,713 PaperCard miss) → Faz 2 satellite tablolar `ON DELETE CASCADE` FK ile bağlı → batch FK violation riski
- Yarın Faz 2 koşulduğunda her upload sonu `skipped ≈ 4,713-4,714` envanter NONE notu ile eşleşmeli (canlı doğrulama)

**Sonraki:** Faz 2 (S3a) — `fact_paper_sentence_role` (24.87M) + `fact_paper_d_estra` (24.87M) + `fact_paper_ref_age` (16.70M) upload, ~1.5-2h @ 2XL

---

## B-011 — Pinecone import KAPANDI (2026-04-30 11:07 UTC)

**Tarih:** 2026-04-30
**Tip:** STANDART (Pinecone bulk import + smoke verify)
**Süre:** ~3h (polling pct 0% → 100%, IMPORT_ID=3)
**Karar referansı:** DECISIONS.md B-011

**Yapıldı:**
- [x] N12d notebook bulk import job tamamlandı (Yol B re-upload başarılı)
- [x] `papers-bgem3` index canlı: **24,867,210 vector** / expected 24,867,210 / Δ=+0
- [x] Smoke `describe_index_stats`: dimension=1024 cosine, vector_type=dense, namespace=`__default__` (DM-016 dense-only MVP), index_fullness=0.0 serverless, request latency 176ms eu-west-1
- [x] Yol B re-upload pattern: 4-parquet metadata join (field+quality+id_card+metod) + GCS embeddings_v3/papers/ + start_import → 2026-04-29 fail (No namespace + Type:Dense uyumsuzluğu) sorunu DM-016 ile çözüldü, bu run temiz

**Bağlama:**
- F3a Pool Router semantic pool önkoşulu (P006) kapandı; F2 P006 mock client yerine gerçek Pinecone client'la başlanabilir
- M-3 (xlsx Sheet 6) ✅ TAMAM
- B0 + B1 (xlsx Sheet 3) ✅ TAMAM
- W-39 (xlsx Sheet 1) ✅ HAZIR
- F2 başlangıç engelleyici sayısı 3 → 2 (kalan: HF Endpoint Sercan + METHOD §1 onay)

**Sonraki:** B-012 (Pinecone metadata patch) + B-013 (Faz 2 satellite verify)

---

## B-012 — Pinecone metadata patch — notebook hazır (2026-04-30)

**Tarih:** 2026-04-30
**Tip:** STANDART (Council 20 onay + plan-first manifest + notebook iskelet)
**Süre:** plan + notebook ~30 dk; koşum yarın ~4-5h
**Karar referansı:** DECISIONS.md B-012 + Council 20 (6/6 GREEN, 0 YELLOW, 0 RED, R13.5 otomatik onay)

**Yapıldı:**
- [x] Council 20 değerlendirme — `v_conf` kaynak seçimi (a) `type_confidence` vs (b) `topic_profile.theme_scores[0]`; (b) 6/6 GREEN
- [x] DECISIONS.md B-012 entry yazıldı (8 metadata field şeması + Council gerekçeleri + DoD)
- [x] `scripts/colab_pinecone_metadata_join.ipynb` (17 cell: 9 md + 8 code)
  - Cell 1 Setup (Drive + pip + env + Pinecone client + GCS)
  - Cell 2 Schema audit (4 parquet)
  - Cell 3 Polars stream join → unified metadata parquet (~24.86M × 9 col, ~1 GB)
  - Cell 4 Embedding shard A/B + metadata inner join → `id, values, metadata` Pinecone-ready parquet (~50 GB)
  - Cell 5 GCS upload (`gs://embeddings_v3/papers_with_metadata_v1/`)
  - Cell 6 Pinecone `start_import` (upsert mode, mevcut vector korunur)
  - Cell 7 Status poll (60s × 8h)
  - Cell 8 Smoke verify (fetch metadata audit + query latency + DoD verdict)

**Bağlama:**
- B-011 Pinecone import close sonrası smoke testi metadata `[]` boş çıktı; xlsx Sheet 3 B1 hedef şeması yapışmamış
- F2 P006 Pool Router engeli kapanır (B-38 + B-61 + B-62 endpoint'leri çalışır hale gelir)
- DM-016 dense-only MVP (sparse drop edilir)
- Yedek: mevcut Pinecone vector korunur (upsert overwrite ID match)

**Yarın koşum talimatı:**
1. Colab Pro+ runtime, GCS auth + Pinecone API key Secrets'ta hazır
2. 8 cell sırayla manuel koş (Run all yasak)
3. Cell 4 sonrası `skipped_no_meta` ≈ 4,978 (sentence_role NONE benzeri PaperCard miss artığı) civarı
4. Cell 7 polling status `Completed` görünce Cell 8 smoke
5. DoD üç ✓ (vector parity, metadata 8-field, latency<500ms) → B-012 kapanışı

**Sonraki:** B-013 (Faz 2 satellite verify) — paper_satellites Cell 8 verify çıktısı

---

## B-019 + F4-S1 — Mockup v3 design lock + Frontend Shell (P037-P044)

**Tarih:** 2026-04-30 gece geç
**Tip:** STANDART (mockup iterasyon + plan revize + 7 atomic commit frontend skeleton)
**Süre:** ~3h aktif (mockup v1→v2→v3 iterasyon + F4 plan revize + Node install + P037-P044 + smoke)
**Karar referansı:** DECISIONS.md B-019
**Branch:** `feat/F4-frontend-shell` (off `bf5db7e` B-018 last) — lokal-only

**Yapıldı (3 paket):**

### Paket 1 — Mockup v3 design canon (Omer onayı)
- [x] Mockup v1 (üst yatay nav, B42-050 krem-parşömen #F5EBDD + Crimson Pro) → Omer feedback "üstteki sayfa seçeneklerini solda hayal etmiştim. sci-space gibi. renkleri de krem tonlu düşünmüştüm. içerik güzel ama kafa karıştırıcı"
- [x] Mockup v2 (sol sidebar 248px + krem heavy #EFE6D6 + jargon "Keşif/Düzenleme/tezgâh") → Omer feedback "çok beğenmedim. her taraf anlamsız terimler ile dolu. akademisyen için çok kullanışlı değil. öğrenciler de anlamaz. ayrıca arka fon beyaza yakın olsun"
- [x] **Mockup v3** (sol sidebar 240px SciSpace + #FAF8F3 beyaza yakın + Inter+Lora sade + plain Turkish nav: Ana Sayfa/Makale Ara/Bana Önerilenler/Makaleyle Sohbet/Okuma Listem/Açık Makale/Profilim/Hoş Geldin + Yakında 3 locked) → **Omer onayı: "bu daha iyi"** 2026-04-30
- [x] Mockup canonical: `~/Desktop/papermind-mockup/index.html` (~1100 satır CSS + 8 ekran)

### Paket 2 — F4 plan manifest revize (`add846b`)
- [x] `docs/plans/F4_frontend_skeleton_arama.md` revize: scope F4-S1'e daraltıldı (~1400 LOC, 4 gün); F4-S2..S5 future sprint
- [x] Eski B42-050 §5 kütüphane fişi (Crimson Pro display + ESTRA bar + PMID Geist Mono renklendirme + termo-strip + paper-grain texture) **post-MVP polish'e ertelendi** (R5 hiyerarşi gereği mockup v3 üstün)
- [x] Mockup v3 design tokens locked: `--bg #FAF8F3` + `--bg-card #FFFFFF` + `--accent #B26B2C` + Inter UI + Lora display
- [x] Routing: kısa İngilizce slug (`/`, `/search`, `/top5`, `/chat`, `/reading-list`, `/paper/[id]`, `/profile`, `/onboarding`) — eski `/kutuphane/arama/[query_id]` iptal
- [x] §Council R13 6-rol: 5 GREEN + 1 YELLOW (Global Çözüm — mobile drawer S1 vs S5) → Omer hakem (A): F4-S1 placeholder, tam pass S5

### Paket 3 — F4-S1 implementation (P037-P044, 6 commit)
- [x] **Tooling kurulum** — Node v24.15.0 LTS Krypton (2026-04-15 release) `~/.local/share/node24` extracted + `node`/`npm`/`npx`/`corepack` `~/.local/bin` symlink (uv pattern paralel); npm 11.12.1; 500 packages 47s install
- [x] **`a073b8f` [P037]** — `web/package.json` (Next 16.2.4 + React 19 + Turbopack default + Tailwind 4 + TanStack Query 5 + Zustand 5 + RHF 7 + Zod 3.23 + Lucide + next-intl 4.11 (3.x→4.11 bump Next 16 peer compat) + Vitest 2 + RTL 16) + `next.config.ts` (typedRoutes + 3 security header) + `tsconfig.json` (strict + noUncheckedIndexedAccess + noImplicitOverride + path alias `@/*`) + `postcss.config.mjs` (@tailwindcss/postcss) + `eslint.config.mjs` (Next 16 native flat — FlatCompat circular structure error workaround) + `.prettierrc.json` + `.gitignore` + `.npmrc`
- [x] **`22b86f4` [P038]** — `src/app/layout.tsx` (`<html lang="tr">` + Inter (UI 400/500/600/700) + Lora (display 400/500/600 + italic) `next/font/google` + AppShell wrap + QueryProvider + metadata template `%s · PaperMind`) + `src/styles/globals.css` (mockup v3 `@theme` tokens: 14 color var + 2 font var + 3 radius + 2 shadow + WCAG AA `:focus-visible` amber halka + `prefers-reduced-motion` respect) + `src/lib/cn.ts` (clsx + twMerge) + `src/lib/query-client.tsx` (staleTime 1h Redis L1 hizalı + gcTime 24h + retry 1)
- [x] **`71b2877` [P039+P040]** — `src/lib/nav-config.ts` (3 grup × plain Turkish label + `isActiveHref` pathname matcher + `labelForPathname` breadcrumb) + `src/components/Sidebar.tsx` (use client, brand mark + 3 grup + locked yakında badge + active aria-current="page" + Lucide ikonlar) + `Topbar.tsx` (use client, dynamic breadcrumb + cmd+K global search + Bell/HelpCircle + user chip avatar) + `AppShell.tsx` (RSC, grid 240px sidebar + 56px topbar + main `role="main"` overflow-y-auto max-w 1200px)
- [x] **`a86c61b` [P041]** — 8 route stub: `/` (Ana Sayfa stat 4-grid + 3 card row) / `/search` (placeholder F4-S2) / `/top5` (Hint banner + placeholder F4-S2) / `/chat` (placeholder F4-S3) / `/reading-list` (placeholder F4-S3) / `/paper/[id]` (async params Next 16 placeholder F4-S4) / `/profile` (placeholder F4-S5) / `/onboarding` (placeholder F4-S4); `PageHeader` (Lora h1 26px + lede max-w 720px) + `Card`/`CardRow` + `Hint` (amber-tinted info banner)
- [x] **`40b16c1` [P042+P043]** — `api.ts` (fetch wrapper + `Authorization: Bearer ${token}` + ApiError class + 204 handling + `apiFetchOrFixture` 501 fallback for B-018 6 endpoint skeleton uyumlu) + `auth.ts` (dev JWT mock HS256 sub=user-dev-omer exp 24h + localStorage persist + SSR-safe `typeof window` guard) + `types.ts` (backend Pydantic mirror: Language tr/en/id + DecisionBand StrEnum 4 + GateWarningCode G1-G7 + FaithfulnessMeta + PaperCard year_verified K1 + signals_13 + Search/Top5/Chat/ReadingList/Onboarding shapes) + `fixtures/search.json` (2 paper Krishnan 2024 canon + Moor 2023 strong_evidence)
- [x] **`772977b` [P044]** — `src/app/loading.tsx` (3 placeholder card shimmer + `aria-busy` + `aria-live="polite"` + sr-only "Yükleniyor…") + `error.tsx` (use client + `reset()` retry button + Card içinde `error.message` + `console.error` capture F7 P065 Sentry swap notu) + `not-found.tsx` (sade 404 + Ana Sayfa link)

**Smoke (S1-S3 PASS):**
- `npm run build` → 0 type error, 9 route generated (8 statik + `/paper/[id]` ƒ dinamik)
- `npm run lint` → 0 hata
- `npm run dev` (background, server up 2s) → `/`, `/search`, `/paper/W2024001` → 200; `/unknown` → 404
- Security headers `X-Content-Type-Options: nosniff` + `X-Frame-Options: DENY` + `Referrer-Policy: strict-origin-when-cross-origin` aktif

**Bağlama:**
- B-017 Senaryo B (Frontend Lead boş, Claude kod %100, Sercan post-hoc) korundu → KD-21 yeni Bilinen Borç (Frontend post-hoc PR review batch)
- B-018 backend skeleton 6 endpoint 501 NotImplemented + TODO marker (P020/P022/P031/P035/P046/P050) frontend `apiFetchOrFixture` ile uyumlu — F2 PASS sonrası gerçek wiring
- DM-013 Next.js 16 stack onayı + B-005 dil seçimi onboarding + Mockup v3 lock
- R5 hiyerarşi: mockup v3 (Omer 2026-04-30 onaylı) > B42-050 §5 (Papermind_V2 plan-time) — kütüphane fişi spec post-MVP polish

**Bilinen Borçlar:**
- KD-21 yeni: Frontend post-hoc Sercan PR review batch (F4-S1..S5 sprint sonu PR'ları biriktirilip Sercan'a tek seferde verilir)
- Mobile drawer S1'de placeholder (Omer hakem A); tam mobile responsive pass S5'e ertelendi
- ESLint 9 flat config: `@typescript-eslint/consistent-type-imports` typed-linting required (parserOptions.project konfigsiz; F4-S1 scope dışı, future enhancement)
- next-intl 3.x→4.11 bump (Next 16 peer compat); locale slot açık ama provider F5 onboarding sonrası migrate

**Sıradaki:** F4-S2 (Omer visual review PASS sonrası) — Makale Ara wiring + filter chip + URL state sync + apiFetchOrFixture + PaperCard component + 501→demo banner; ~600-800 LOC, 3 gün; yeni `docs/plans/F4_S2_arama_top5.md` mini-plan yazılacak

---

## SİRADAKİ SPRINTLER (B-001 master §9 ile uyumlu)

| P | Faz | Plan manifest | Hedef |
|---|---|---|---|
| **P001** | F2 | F3a §3 | api/main.py + 3 middleware (auth/rate_limit/sentry) |
| **P002** | F2 | F3a §3 | 3 db client (supabase + pinecone + redis) |
| **P003** | F2 | F3a §3 | Listener (Qwen multi-query 4-6 rewrite) + unit |
| **P004** | F2 | F3a §3 | Anchor (PMID 12-segment match) + unit |
| **P005** | F2 | F3a §3 | Pool Router (3-havuz RRF k=60) + unit |
| **P006** | F2 | F3a §3 | Reranker (BGE-reranker-v2-m3) + unit |
| **P007** | F2 | F3a §3 | Curator (Outlines + LVR validator) + unit |
| **P008** | F2 | F3a §3 | POST /api/search route + Pydantic schemas + integration |
| **P009** | F2 | F3a §3 | E2E test + p50<4s/p95<7s bench + cache + outage senaryolar |
| **P010-P016** | F3 | F3b | /api/chat SSE (sessions migration → Listener multi-turn → IntentPMID → topic-lock → SSE route → margin clarify → persist) |
| **P017-P023** | F3 | F3c | /api/summarize (Celery → cache → route → Qwen+Claude 2-stage → curator → faithfulness gate → poll) |
| **P024-P030** | F3 | F3d | /api/enrichment (OpenAlex polite pool → S2 fallback → fetcher depth 1/2 → ghost curator K1+K8 → route → Celery task → audit log) |
| **P031-P036** | F3 | F3e | /api/reading-list (migration+RLS → schemas → LIST/CREATE → UPDATE/DELETE → paper join → bulk) |
| **P037+** | F4 | (yazılacak) | Frontend skeleton: Next.js 16 + Tailwind v4 + 4-zone palet + PaperCard + E4 Arama |
| **P0??+** | F5 | (yazılacak) | E1 Onboarding + E2 Chat SSE + E3 Top-5 onay |
| **P0??+** | F6 | (yazılacak) | E5 Detay + Summarize UI + Ghost enrichment UI |
| **P0??+** | F7 | (yazılacak) | Quality (3-katlı faithfulness + Sentry) + Docker + HF + 5 pilot |

---

## SPRINT TEMPLATE

Her P için bu şablon tekrarlanır (atomic commit sonrası):

```markdown
## PNNN — F<N> <başlık>

**Tarih:** YYYY-MM-DD
**Tip:** STANDART | HIZLI DÜZELTME
**Süre:** Xh
**Plan Manifest:** docs/plans/F<N>_<başlık>.md
**Commit hash:** abc1234
**§8 verification:** Y PASS / 0 FAIL
**ROL 2 audit:** GREEN | YELLOW + Omer kabul | RED → revize

**Yapıldı:**
- [x] Madde 1
- [x] Madde 2

**Bağlama:**
- DM-NNN
- Plan manifest §X

**Sonraki:** P<N+1>
```
