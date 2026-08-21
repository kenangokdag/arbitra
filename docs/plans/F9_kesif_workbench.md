# F9 — Keşif Tezgahı 1.1 Araştırma Alanı (Plan Manifest)

> **Statü:** TASLAK — Omer onayı bekliyor (2026-05-05)
> **Şablon:** `reference/ARCHITECT_PROMPT_TEMPLATE` §0..§18 (mevcut F8 plan canon ile aynı yapı)
> **Owner:** Omer (plan onayı + .env + deploy) · Claude (kod, K-027 askıya alma protokolü solo yetki)
> **Branch:** `feat/F9-kesif-tezgah` (off `f363b76` main)
> **LOC tahmini:** ~1860 (8 atomik commit P091..P098) + ~36 test
> **Süre tahmini:** 4-5 gün kod + browser empirik test
> **Kanun:** CLAUDE.md "%100 plan kod öncesi" + DM_RULES R1/R2 + R13.13 build PASS empirik kanıt

---

## §0 — Plan kimliği

| Alan | Değer |
|---|---|
| Faz adı | **F9 Keşif Tezgahı** |
| Scope | **Sadece 1.1 Araştırma Alanı** (D9 §5.1 içindeki tek sayfa; 1.2/1.3/1.4/1.5 ayrı plan'lara ertelenir — §17) |
| Onay sahibi | Omer |
| Yazım tarihi | 2026-05-05 |
| Bağlı kararlar | DM-LLM-1..10 (F8 unified Gemini 2.5), B-021/B-022 (proje bazlı pivot + ESTRA validator), DM-017..024 + DM-002r (5-6 hafta MVP), K-023 (user_vectors pgvector — Brain memory; bu plan'da kullanılmaz, F10/F11'e ertelenir), B-024 (background canon: AppShell `bg-stone-50` mirası — `data-zone` wrapper YASAK), DM-LLM-3/4 (LiteLLM tek abstraction + ProjectContext otomatik enjekte) |
| Bağlı dosyalar | `docs/plans/F8_llm_provider_unification.md`, `docs/plans/F4_S4_advisor_chatbox.md` (ChatThread/ChatboxPanel), `docs/plans/F3a_search.md` (SUPERSEDED, 5-katman pipeline mimari referans), `~/Downloads/D9-Sidebar.html` (sayfa hiyerarşisi canon), `~/Downloads/D5-D6-Cards.html` (kart görsel canon) |

---

## §1 — Niyet (1 paragraf)

Hocam dashboard'da **"Yeni proje"** butonuna basıp proje adı girdiğinde, sistem onboarding alan/alt-alan/odak verisini bu projeye miras geçirir; `/project/{id}/discovery-1` sayfasında kütüphaneci ile en fazla 2 turda araştırma alanını netleştirir; ardından sistem 3 çapa adayı gösterir; hoca birini **ÇAPA SEÇ** ile kilitler; arka planda 500 komşu makale + ESTRA skor + curator çıktısı 4-6 sn içinde hazırlanır; otomatik olarak `/project/{id}/discovery-2` (1.2 Konu Belirleme) sayfasına geçer. Bu plan **sadece** 1.1 Araştırma Alanı'nın 3 stage'ini (A=sohbet, B=çapa adayları, C=alan hazırlanıyor) kapsar; sonraki tezgah sayfaları (1.2-1.5, İnceleme/Literatür Boşluğu/Yazım/Savunma) ayrı plan'lara ertelenir.

---

## §2 — Kapsam (IN / OUT / DEFERRED)

### IN (F9)

| # | Slice | Konum |
|---|---|---|
| 1 | `projects` + `project_chat_messages` + `project_anchor` tabloları + RLS (migration 0015) | `db/migrations/0015_projects_skeleton.sql` |
| 2 | `project_cluster` materialize tablosu (BÖLÜM 3 RRF çıktısı + ESTRA skor) | `db/migrations/0016_project_cluster.sql` |
| 3 | 1.1 Stage A — Kütüphaneci 2-tur (Gemini Flash, ProjectContext + uyumsuzluk hafızası) | `api/services/librarian.py`, `api/routes/research_area.py`, `prompts/librarian_v1.md` |
| 4 | 1.1 Stage B — 3 çapa adayı (BÖLÜM 2: Listener → PoolRouter [Pinecone vec + Supabase tsvector] → Reranker → top-3) | `api/services/anchor_finder.py` |
| 5 | 1.1 Stage C — Background job (BÖLÜM 3 vec+bib+theme RRF k=60 → BÖLÜM 4 Supabase enrich → BÖLÜM 5 ESTRA + curator) | `api/services/cluster_expander.py`, `api/services/estra_scorer.py` |
| 6 | 4 yeni FE bileşen: `StageIndicator`, `AnchorCandidateCard` (D5 stili 5-aksiyon), `ProfileHint`, `PreparingArea` | `web/src/components/project/*.tsx` |
| 7 | 4 yeni BE endpoint: `/api/project` CRUD + `research-area/messages` + `anchor-candidates` + `anchor/lock` + `lock-status` + `reset` | `api/routes/project.py`, `api/routes/research_area.py` |
| 8 | Özetle / Çevir / Danışmana sor entegrasyonu (anchor candidate kart üstü + ChatboxPanel paper context) | `api/routes/paper_actions.py`, `AnchorCandidateCard` accordion |
| 9 | Sohbet uyumsuzluk hafızası (`rejected_anchors` + `reject_reasons` JSON kolonları) | `project_anchor` tablosu + `librarian.py` system prompt append |

### OUT (bu plan değil)

- 1.2 Konu Belirleme sayfası UI (BÖLÜM 5 backend hesaplaması yapılır ama ekran ayrı plan'da)
- 1.3/1.4/1.5 sayfaları (Bibliyometri, Tematik, Kavram Ağı)
- Diğer 4 tezgah (2 İnceleme, 3 Literatür Boşluğu, 4 Yazım, 5 Savunma)
- Mevcut `TopicSuggestionPage`, `ThematicAnalysisPage`, `ConceptNetworkPage` refactor (1.2+ planlarında ele alınır — **bu plan'da DOKUNULMAZ**)
- `<AdvisorButton>` kalan 12 ROLE_MODULE enjeksiyonu (F8 plan §2 OUT, F9-S2'ye ertelendi)
- Reviewer pipeline / JuryMind tiebreaker (F8 §2 OUT)

### DEFERRED (engelleyici, §16'da liste)

- Pinecone B-012 metadata HARD filter patch — 1.1'de `filter=None` tolere edilir; 1.2'de zorunlu (Omer Colab paralel akış)
- `user_vectors` pgvector tablosu (K-023) — bu plan'da yok; F10 (1.2 Konu Belirleme) öncesi ya 0017 migration ya Brain ratifikasyon
- Background job — F9'da FastAPI `BackgroundTasks` (Celery F7 P065'e ertelendi, KD-?)
- `dim_theme_embedding` BÖLÜM 3 K3 kanalı — eğer corpus mismatch varsa 2-kanal RRF (vec+bib) fallback (§11 doğrulama: ✅ tablo var, fallback gerek yok)

---

## §3 — Atomik commit boundary (8 commit, R7 + R13.3 zorunlu)

| # | ID | Commit subject | Dosyalar | LOC | Test |
|---|---|---|---|---|---|
| 1 | **P091** | `feat(db): 0015 projects + project_chat_messages + project_anchor + RLS` | `db/migrations/0015_projects_skeleton.sql` | ~120 | smoke INSERT/SELECT (Supabase Dashboard SQL) |
| 2 | **P092** | `feat(db): 0016 project_cluster materialize tablosu + RLS + index` | `db/migrations/0016_project_cluster.sql` | ~100 | smoke INSERT/SELECT |
| 3 | **P093** | `feat(api): /api/project CRUD + onboarding miras` | `api/routes/project.py` (yeni), `api/models/project.py` (yeni) | ~180 | 5 unit + 3 integration |
| 4 | **P094** | `feat(api): /research-area/messages — Kütüphaneci 2-tur Gemini Flash` | `api/routes/research_area.py` (yeni), `api/services/role_modules/librarian.py` (yeni — F8 ROLE_MODULE pattern uyumu, brief revize 2026-05-05), `api/models/research_area.py` (yeni), `prompts/librarian_v1.md` (yeni) | ~220 | 6 unit + 2 integration |
| 5 | **P095** | `feat(api): anchor-candidates — BÖLÜM 2 paralel arama (Pinecone+tsvector RRF+reranker)` | `api/services/anchor_finder.py` (yeni), `api/services/pool_router.py` (`lexical_tsvector_pool` helper), `api/models/research_area.py` (`AnchorCandidate` + `HydePacket` append), `prompts/hyde_packet_v1.md` (yeni), `api/routes/research_area.py` (POST `/anchor-candidates` endpoint append) — `papers.title_tsv` GENERATED + GIN index P091'de zaten indi (K-029, drift fix) | ~260 | 5 unit + 1 integration |
| 6 | **P096** | `feat(api): anchor/lock — BÖLÜM 3+4+5 background job + ESTRA skor` | `api/services/cluster_expander.py` (yeni), `api/services/estra_scorer.py` (yeni), `api/workers/anchor_lock_worker.py` (yeni FastAPI BackgroundTasks adaptör) | ~280 | 4 unit + 1 e2e |
| 7 | **P097** | `feat(web): 1.1 sayfası Stage A/B/C + 4 yeni bileşen` | `web/src/app/(app)/project/[id]/[[...slug]]/page.tsx` (discovery-1 case), `web/src/components/project/{StageIndicator,AnchorCandidateCard,ProfileHint,PreparingArea}.tsx` | ~520 | 8 vitest |
| 8 | **P098** | `feat(web): Özetle/Çevir/Danışmana sor entegrasyon (kart üstü + ChatboxPanel paper context)` | `api/routes/paper_actions.py` (translate yeni endpoint), `AnchorCandidateCard` accordion patch, `ChatboxPanel` paper context wire | ~180 | 4 vitest |

**Boundary kuralları (R7 + R13.3):**
- `git commit --no-verify` YASAK
- Plan dışı dosya edit denemesi → **STOP** + plan revize commit'i ayrı
- Her commit'te empirik kanıt: `pytest` EXIT 0 + `next build` EXIT 0 + son 3 satır log (R13.13)
- Mevcut sayfalar (`TopicSuggestionPage`, `ThematicAnalysisPage`, `ConceptNetworkPage`) **DOKUNULMAZ**

---

## §4 — Kullanıcı senaryosu (gold path)

1. Hoca onboarding'i daha önce doldurmuş (alan/alt-alan/odak Supabase'de) — F5 PR #8 KAPANDI.
2. Dashboard'da **"Yeni proje"** butonuna basar → name input → `POST /api/project {name}` → `projects` row yaratılır + onboarding miras alınır (`inherited_field_ids`, `inherited_subfield_ids`, `inherited_research_focus`).
3. Tarayıcı `/project/{id}/discovery-1` adresine yönlenir.
4. Sayfa açılır → AppShell `bg-stone-50` zemin (B-024) → `<ProfileHint>` üstte (`{fields, subfields, focus}` chip) → Stage A başlar → `<AdvisorBanner>` Lora italik karşılama + `<ChatThread>` aktif.
5. Hoca yazar: *"yükseköğretimde kalite akreditasyonu için ÇKKV"*.
6. `POST /api/project/{id}/research-area/messages` → `librarian.py` Gemini Flash çağırır → Tur 1 anlama JSON: `{focuses: [3 madde], field, subfield, interdisc: bool, confidence: high|med|low, adviser_text, finished: false}` → kullanıcıya 3 odak + onay sorusu döner.
7. **Evet** → `finished: true` → Stage A→B fade 200ms; sohbet kaybolur; sağ üst pill **"Sohbete dön"** Stage B süresince görünür.
   **Hayır/düzelt** → Tur 2 başlar (`attempt_no` aynı, `turn_no=2`) → "evet" → Stage B; "hâlâ değil" → `POST /research-area/reset {reject_reason}` → `attempt_no++`, `rejected_anchors` push, sistem prompt'a uyumsuzluk hafızası eklenir.
8. Stage B: `POST /research-area/anchor-candidates` → BÖLÜM 2 paralel arama (Pinecone vec + Supabase tsvector havuzları → RRF k=60 → BGE reranker → top-3) → 3 `<AnchorCandidateCard>` render: orijinal dilde başlık + abstract preview + chip'ler (alan, dil, yıl, decision_band) + `q_weak` ESTRA bar + 5 aksiyon (Detay / Kütüphaneye ekle / **Özetle** / **Çevir** / **Danışmana sor**) + altta amber CTA **"ÇAPA SEÇ"**.
9. Hoca **"ÇAPA SEÇ"** → confirm dialog → `POST /research-area/anchor/lock {paper_id}` (202 Accepted, `job_id`) → Stage C başlar.
10. Stage C: `<PreparingArea>` 4-6 sn ilerleme animasyonu (Pinecone komşu / bibcoupling / tema / kalite / ESTRA) — `GET /research-area/lock-status` polling 800ms → `status: ready` → otomatik `router.push('/project/{id}/discovery-2')`.

---

## §5 — Tasarım canon (D5/D6 referans, B-024 background canon zorunlu)

### Palet (D5'ten 1:1, P056 cool-academic)

| Token | Değer | Kullanım |
|---|---|---|
| `bg-page` | `bg-stone-50` (AppShell mirası) | Sayfa zemini — **page-level override YASAK (B-024)** |
| `bg-card` | `var(--color-bg-card)` `#ffffff` | Kart yüzeyi |
| accent | `#b45309` amber-700 | F4-S1.5 cool-academic kanon (D9'un `#E8A157` orange'ı **DEĞİL**) |
| accent-pale | `#fef3c7` | Hint banner, pale chip |
| ink/ink-soft/ink-mute/ink-faint | `#0f172a / #334155 / #475569 / #64748b` | Hierarchy AAA→AA |
| decision band 3px border-left | canon `#047857` / strong `#1d4ed8` / frontier `#b45309` / risk `#b91c1c` | AnchorCandidateCard sol kenar |

### Tipografi

- Title kart: **Lora italic 16.5px / 500**
- Title sayfa (`<PageHeader>`): Lora italic 28px / tracking -0.015em
- Body: Inter 13-14px
- Mono: JetBrains Mono (ESTRA bar score, year)

### Kart anatomisi (8-checklist)

- radius: 12px
- padding: 18×20
- border: 1px rule-soft + 3px decision band
- shadow: 2-katman (P046 stack — D5 referans)
- paper-grain: radial 8×8 noktalı texture (kart yüzeyi içinde, `bg-page` üzerinde değil)

### Buton

- standard `.btn`: h:30 / radius:7 / Inter 12 / 500
- `.btn primary`: slate-900 bg, beyaz fg (Detay)
- `.btn adviser`: amber-pale bg, Lora italik, radius:100px (Danışmana sor)
- ana CTA **"ÇAPA SEÇ"**: amber-700 → amber-600 gradient, h:42, ayrı satır kart altında

### Stage geçişi

- A→B: fade 200ms (cubic-bezier(0.16,1,0.3,1) ease-out-expo, P046 transition tokens)
- "Sohbete dön" pill: sağ üst, Stage B süresince visible; tıklandığında Stage A geri açılır (sohbet hafızası korunur, anchor candidates state cache)
- B→C: PreparingArea full-card progress bar 800ms tick (`requestAnimationFrame` deterministik, prefers-reduced-motion guard)

---

## §6 — Veri katmanı (migration 0015 + 0016)

### `db/migrations/0015_projects_skeleton.sql`

```sql
-- =====================================================================
-- PaperMind v4 — Migration 0015: projects + chat + anchor (F9 1.1)
-- =====================================================================
-- Karar referansı: docs/plans/F9_kesif_workbench.md §6
-- Tarih: 2026-05-05  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Bağımlı kararlar: B-021 proje bazlı workspace (DM-018), DM-019 karar hafızası
-- =====================================================================

CREATE TABLE public.projects (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                   uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name                      text NOT NULL,
  status                    text NOT NULL DEFAULT 'active',     -- active|archived
  current_stage             text NOT NULL DEFAULT '1.1',
  inherited_field_ids       text[] NOT NULL DEFAULT '{}',       -- onboarding miras
  inherited_subfield_ids    text[] NOT NULL DEFAULT '{}',
  inherited_research_focus  text,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_projects_user_status ON public.projects (user_id, status);
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY projects_owner ON public.projects
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- ---------------------------------------------------------------------
CREATE TABLE public.project_chat_messages (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  attempt_no            smallint NOT NULL DEFAULT 1,
  turn_no               smallint NOT NULL,
  role                  text NOT NULL CHECK (role IN ('user','adviser')),
  content               text NOT NULL,
  parsed_understanding  jsonb,                                  -- {focuses:[3], field, subfield, interdisc, confidence}
  created_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_chatmsg_project_attempt_turn
  ON public.project_chat_messages (project_id, attempt_no, turn_no);

ALTER TABLE public.project_chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY chatmsg_owner ON public.project_chat_messages
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

-- ---------------------------------------------------------------------
CREATE TABLE public.project_anchor (
  project_id        uuid PRIMARY KEY REFERENCES public.projects(id) ON DELETE CASCADE,
  anchor_paper_id   text,                                       -- BÖLÜM 2 sonu seçim
  candidates_meta   jsonb,                                      -- 3 aday + skor + rationale
  rejected_anchors  jsonb NOT NULL DEFAULT '[]'::jsonb,         -- uyumsuzluk hafızası
  reject_reasons    jsonb NOT NULL DEFAULT '[]'::jsonb,         -- kullanıcı sebepleri
  locked_at         timestamptz,
  cluster_status    text NOT NULL DEFAULT 'pending'             -- pending|expanding|ready|failed
                    CHECK (cluster_status IN ('pending','expanding','ready','failed'))
);

ALTER TABLE public.project_anchor ENABLE ROW LEVEL SECURITY;
CREATE POLICY anchor_owner ON public.project_anchor
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

-- ---------------------------------------------------------------------
-- BÖLÜM 2 lexical havuz: papers.title tsvector materyalize (KD-23 kapanır)
-- Lazy: GENERATED ALWAYS AS (to_tsvector(...)) STORED
-- ---------------------------------------------------------------------
ALTER TABLE public.papers
  ADD COLUMN IF NOT EXISTS title_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,''))) STORED;
CREATE INDEX IF NOT EXISTS idx_papers_title_tsv ON public.papers USING gin (title_tsv);

-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0015_projects_skeleton',
  'projects + project_chat_messages + project_anchor (F9 1.1) + papers.title_tsv (KD-23 lexical)'
)
ON CONFLICT (version) DO NOTHING;
```

### `db/migrations/0016_project_cluster.sql`

```sql
-- =====================================================================
-- PaperMind v4 — Migration 0016: project_cluster materialize (F9 1.1)
-- =====================================================================
CREATE TABLE public.project_cluster (
  project_id    uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id      text NOT NULL,
  source        text NOT NULL CHECK (source IN ('vec','bib','theme')),
  rrf_score     numeric NOT NULL,
  q_weak        numeric,
  estra_score   numeric,
  rank_final    int,
  frozen_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, paper_id)
);
CREATE INDEX idx_cluster_project_rank
  ON public.project_cluster (project_id, rank_final);

ALTER TABLE public.project_cluster ENABLE ROW LEVEL SECURITY;
CREATE POLICY cluster_owner ON public.project_cluster
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

-- =====================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0016_project_cluster',
  'project_cluster (F9 1.1 BÖLÜM 3 RRF çıktısı + ESTRA skor materialize)'
)
ON CONFLICT (version) DO NOTHING;
```

---

## §7 — Backend endpoint sözleşmesi (Pydantic `extra="forbid"`)

| Method | Path | Body / Query | Response | Hata |
|---|---|---|---|---|
| POST | `/api/project` | `{name: str}` | `201 {id, name, current_stage, inherited_*}` | 422 / 401 |
| GET | `/api/project` | — | `200 [{id, name, status, current_stage, updated_at}]` | 401 |
| GET | `/api/project/{id}` | — | `200 {id, name, status, current_stage, inherited_*, anchor?}` | 401 / 403 / 404 |
| POST | `/api/project/{id}/research-area/messages` | `{content: str, attempt_no?: int}` | `200 {turn_no, parsed_understanding, adviser_text, finished: bool}` | 422 / 401 / 403 / 503 (Gemini fail) |
| POST | `/api/project/{id}/research-area/anchor-candidates` | (Tur sonu onay sonrası, body yok) | `200 {candidates: [3 × AnchorCandidate], packet_p, packet_s}` | 401 / 403 / 503 (Pinecone/Supabase) / 504 (timeout) |
| POST | `/api/project/{id}/research-area/anchor/lock` | `{paper_id: str}` | `202 {job_id, status: "expanding"}` (BackgroundTasks) | 422 / 401 / 403 |
| GET | `/api/project/{id}/research-area/lock-status` | — | `200 {status, progress_pct, eta_sec}` | 401 / 403 / 404 |
| POST | `/api/project/{id}/research-area/reset` | `{reject_reason: str}` | `200 {attempt_no, rejected_count}` | 422 / 401 / 403 |
| POST | `/api/paper/{paper_id}/summarize` | `{target_lang: 'tr'\|'en'}` | `200 {summary, faithfulness_meta}` | 422 / 503 |
| POST | `/api/paper/{paper_id}/translate` | `{target_lang: 'tr'\|'en'}` | `200 {translated_title, translated_abstract, faithfulness_meta}` | 422 / 503 |
| POST | `/api/paper/{paper_id}/library/add` | `{project_id?: uuid}` | `201 {reading_list_id}` | 422 / 401 |

### Pydantic model'leri

- `api/models/project.py`: `ProjectCreate`, `ProjectRead`, `ProjectListItem`
- `api/models/research_area.py`: `MessageRequest`, `MessageResponse`, `ParsedUnderstanding`, `AnchorCandidate`, `LockRequest`, `LockStatus`, `ResetRequest`
- `api/models/paper_actions.py`: `SummarizeRequest`, `TranslateRequest` (yeni)

Tüm modeller `model_config = ConfigDict(extra="forbid")` (HK-1).

---

## §8 — LLM kullanımı (F8 LiteLLM router üzerinden)

### Stage A — Kütüphaneci sohbet (max 2 tur, sıkı budget)

- **Model:** `gemini-2.5-flash` (DM-LLM-2 default Flash)
- **Provider:** LiteLLM (`litellm.acompletion`, DM-LLM-3 zero-import gate korunur)
- **Service:** `LLMService.call(tier="flash", project_id=..., role="librarian", page="discovery-1")` (DM-LLM-4 ProjectContext otomatik enjekte)
- **Prompt:** `prompts/librarian_v1.md` (yeni dosya — F8 §8 ROLE_MODULE pattern paralel)
- **Sistem mesajı (özet):** "Sen akademik kütüphanecisin. En fazla 2 turda araştırma odağını netleştir. JSON döndür: `{focuses: [3], field, subfield, interdisc, confidence: 'high'|'med'|'low', adviser_text, finished: bool}`. Onay sorusu adviser_text içinde olmalı."
- **Uyumsuzluk hafızası:** Önceki `parsed_understanding` + `reject_reasons` system prompt'a append edilir (DM-LLM-9 stateless ile uyumlu — her çağrı bağımsız ama kullanıcının ret sebepleri Supabase'den çekilip prompt'a serialize edilir, conversation memory **DEĞİL**)
- **Structured output:** Outlines / Pydantic JSON şema ile validate (HK-1)

### Stage B — HyDE + keyword paket (BÖLÜM 2)

- **Model:** Gemini Flash, JSON şema (Outlines)
- **Çıktı:** `packet_p` (HyDE pseudo-paragraph 80-120 token), `packet_s` (5-8 keyword TR/EN/ID)
- `extra="forbid"`

### Özetle / Çevir (P098)

- Gemini Flash + `faithfulness_gate.check(level=SUMMARY)` (LVR ≥ 0.85, F2 P008 mevcut)
- Translate: source lang detect → target lang Gemini çevir → faithfulness gate aynı LVR threshold
- DM-012 kuralı: corpus için mevcut abstract varsa LLM özet **on-demand** (default direkt göster)

### BÖLÜM 3-4-5 (background)

- **LLM YOK.** Saf SQL + Pinecone + cached kolonlar.
- Cluster expander = vec (Pinecone top-K) + bib (`fact_paper_bibcoupling_top50`) + theme (`dim_theme_embedding` HNSW) → RRF k=60.
- ESTRA skor = `q_weak` (`fact_paper_quality_v3`) + `cd_5` (`fact_paper_disruption`) + `b` (`fact_paper_beauty`) + `pagerank` (`fact_paper_centrality`) deterministik formül (Plan 1 proxy ağırlıklar; Plan 2 LightGBM kalibre F7+).

---

## §9 — 5-katman pipeline eşleme (F3a SUPERSEDED ama mimari referans)

| BÖLÜM | Mevcut hat | F9'da yeni iş |
|---|---|---|
| **1 (sohbet)** | — | `services/librarian.py` (yeni) |
| **2 (çapa)** | Listener (P004 Gemini ✅, F8'de unify edildi) + PoolRouter (P006 mock kısmı concrete) + Reranker (P007 BGE-v2-m3 ✅) | `services/anchor_finder.py` orkestrasyon (yeni); PoolRouter `lexical=tsvector` concrete patch (KD-23 kapanır) |
| **3 (500 aday)** | — | `services/cluster_expander.py` (yeni; vec [Pinecone] + bib [`fact_paper_bibcoupling_top50`] + theme [`dim_theme_embedding`] RRF k=60) |
| **4 (Supabase batch)** | Mevcut Supabase client (P002 + P012 timeout) | `cluster_expander.py` enrich query — `papers` + `fact_paper_id_card` + temporal/disruption/beauty/centrality JOIN batch |
| **5 (skor + curator)** | Curator (P008 iskelet ✅, faithfulness_gate.py ✅) | `services/estra_scorer.py` (yeni); curator concrete `signals_13` çıktısı `project_cluster` tablosuna persist |

### KD-23 lexical havuz kararı (bu plan'da KAPANIR)

- F2 Day 3-4'te lexical havuz **Postgres title FTS** olarak kararlaştırılmıştı (Council 25, B-018) ama concrete migration yapılmamıştı.
- **F9 P095**'te `papers.title_tsv` GENERATED tsvector + GIN index 0015 migration'a inline eklenir.
- BÖLÜM 2 lexical havuz aktif: `SELECT paper_id FROM papers WHERE title_tsv @@ plainto_tsquery('simple', :q) ORDER BY ts_rank(title_tsv, query) DESC LIMIT :k`
- Pinecone sparse Plan 2'ye ertelenmiş (B-018 Council 25) — değişmez.

---

## §10 — Frontend bileşen sözleşmesi (8-anatomi + WCAG kontrast)

### `StageIndicator.tsx` (~30 LOC)

```ts
type Props = { stages: string[]; current: number };
// Render: 3 dot horizontal, current = amber-700 fill, others = slate-300 outline
```

### `AnchorCandidateCard.tsx` (~180 LOC)

```ts
type AnchorCandidate = {
  paper_id: string;
  title: string;
  abstract: string;
  authors: { name: string; orcid?: string }[];
  year: number;
  venue?: string;
  doi?: string;
  lang: string;
  q_weak: number;                              // ESTRA bar 0..1
  decision_band: 'canon'|'strong'|'frontier'|'risk';
  rationale: string;                           // BÖLÜM 2 reranker output
};
type Props = {
  paper: AnchorCandidate;
  rank: 1|2|3;
  onSelect: () => void;                        // ÇAPA SEÇ → confirm → /anchor/lock
  onSummarize: () => Promise<string>;          // POST /paper/{id}/summarize
  onTranslate: () => Promise<string>;          // POST /paper/{id}/translate
  onAskAdviser: () => void;                    // ChatboxPanel açar (paper context)
  onAddToLibrary: () => void;                  // POST /paper/{id}/library/add {project_id}
  onDetail: () => void;                        // /paper/[id] inline-modal veya yeni sekme
};
// Anatomi: D5 kart anatomi (12px radius + 18×20 padding + 1px rule-soft + 3px decision band border-left + 2-katman shadow + paper-grain + Lora italic 16.5px title + Inter 13px body + JetBrains Mono ESTRA bar + 5 .btn standard + 1 amber-700 gradient CTA)
```

### `ProfileHint.tsx` (~25 LOC)

```ts
type Props = { fields: string[]; subfields: string[]; focus: string };
// Render: tek satır, üst sayfa, küçük chip × 3 + focus tek satır italik
// Kontrast: ink-mute slate-600 8:1 AAA
```

### `PreparingArea.tsx` (~60 LOC)

```ts
type Props = { projectId: string; onReady: () => void };
// Render: full-card, Lora 22px başlık "Alanın hazırlanıyor",
//   amber progress bar 800ms tick (5 step etiket: "Pinecone komşu / bibcoupling / tema / kalite / ESTRA"),
//   eta_sec geri sayım, prefers-reduced-motion guard
// Polling: GET /lock-status 800ms → status='ready' → onReady()
```

**WCAG kontrast verify (her bileşen):**
- ink slate-900 16:1 AAA · ink-soft 10:1 AAA · ink-mute 8:1 AAA · ink-faint 5.2:1 AA · accent amber-700 4.5:1 AA · decision band 4 renk hepsi AA-AAA

**B-024 background canon zorunlu:** `data-zone="*"` wrapper YASAK · `body::before` halo YASAK · `--color-bg` override YASAK · sayfa zemini AppShell `bg-stone-50` mirası kalır.

---

## §11 — Halüsinasyon ve doğrulama (kritik — kanıt seviyesi A)

### Grep doğrulama tablosu (CLAUDE: §0'da grep yaptım, kanıtlar dosya:satır)

| # | Kontrol | Sonuç | Kanıt (dosya:satır) | Not |
|---|---|---|---|---|
| 1 | `fact_paper_quality_v3` tablosu var mı? | ✅ VAR | `db/migrations/0005_paper_estra_temporal.sql:20-32` | Kolonlar: `paper_id, q_weak, q_weak_low, q_weak_high, n_lfs_active, q_weak_v2`; CHECK q_weak ∈ [0,1]; idx_quality_v3_q DESC partial; RLS aktif. ✅ Plan §6/§9 SQL kabul. |
| 2 | `fact_paper_centrality` tablosu var mı? | ✅ VAR | `db/migrations/0007_method_centrality.sql:70-79` | Kolonlar: `paper_id, pagerank, indegree, outdegree`; 3 index (pagerank/indegree/outdegree DESC); RLS aktif. ✅ Plan §9 BÖLÜM 5 ESTRA skor kullanılabilir. |
| 3 | `dim_theme_embedding` tablosu var mı? | ✅ VAR | `db/migrations/0002_static_facts.sql:18-32` | 4516 × 256-d TF-IDF L2-normed (N17b/W-32); HNSW index pgvector; RLS read_all. ✅ Plan §9 BÖLÜM 3 K3 theme kanalı **aktif**, 2-kanal fallback gerek yok. |
| 4 | `is_suspicious` kolonu nerede? | ✅ VAR | `db/migrations/0003_paper_anchor_facts.sql:46` (`fact_paper_id_card`) | Boolean default false; RISK_7 patch v1.2; partial index `WHERE is_suspicious=true`. ✅ Plan §9 anchor_finder filter (`is_suspicious=false` HARD filter zorunlu). |
| 5 | `cd_5` hangi tabloda? | ✅ VAR | `db/migrations/0005_paper_estra_temporal.sql:117` (`fact_paper_disruption`) | `cd_5` double precision ∈ [-1, 1]; idx_disruption_cd5 DESC partial WHERE cd_undefined=false. ✅ |
| 6 | `beauty` (Sleeping Beauty B) hangi tabloda? | ✅ VAR | `db/migrations/0005_paper_estra_temporal.sql:140-155` (`fact_paper_beauty`) | Ke et al. PNAS 2015; `b` + `t_a` + `b_undefined`; 3 index. ✅ |
| 7 | `rao_stirling` hangi tabloda? | ✅ VAR | `db/migrations/0006_paper_metadata.sql:49` (`fact_paper_interdisc`) | rao_stirling double precision ∈ [0,1] (Plan 1 distinct-theme variant); idx_interdisc_rao DESC partial. ✅ |
| 8 | `pagerank` hangi tabloda? | ✅ VAR | `db/migrations/0007_method_centrality.sql:73,77` (`fact_paper_centrality`) | double precision; idx_centrality_pr DESC partial. ✅ |
| 9 | `neighbor_bibcoupling` (0008) tablosu? | ⚠ İSİM DÜZELTME | `db/migrations/0008_neighbor_bibcoupling.sql:26-37` | **Gerçek tablo adı: `fact_paper_bibcoupling_top50`** (brief'teki "neighbor_bibcoupling" sadece migration dosya adı). Kolonlar: `paper_id, neighbor_id, raw_count, cosine_score, rank` (1..50); 2 index (neighbor_score DESC + paper_rank); 643M satır; **NO FK** (loader anti-join, B-009 pattern). ✅ Plan §9 cluster_expander bib kanalı `fact_paper_bibcoupling_top50` tablosuna SQL atar. |
| 10 | `user_vectors` (K-023 pgvector) tablosu? | ❌ YOK | `db/migrations/` içinde grep sonucu 0 hit | Bu plan'da **kullanılmaz** (1.1 r-ESTRA profil GLOBAL DM-021 — F10/F11'e ertelendi). §16 DEFERRED listesinde. |
| 11 | `papers.title_tsv` tsvector materyalize? | ❌ YOK (P095'te eklenecek) | `db/migrations/0001_init_schema_v1.sql:38-58` `papers` tablosunda sadece `idx_papers_title_trgm` var (pg_trgm) | F9 P091 0015 migration'da `papers ADD COLUMN title_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,''))) STORED` + GIN index eklenir → KD-23 lexical havuz kapanır. |

### Kanıt seviyesi

- **Hepsi A (gerçek dosya:satır)** — grep tool ile fiziksel kanıt; halüsinasyon sıfır (R4 + DM_RULES K2).
- §6 SQL bloğu Supabase Dashboard'a paste edilebilir formatta (`schema_migrations` row, RLS, FK, index, CHECK hepsi yazıldı).
- §9 cluster_expander BÖLÜM 3 K1 (vec) + K2 (bib) + K3 (theme) **3-kanal RRF aktif**, fallback gerek yok.

---

## §12 — Test stratejisi

### Unit (vitest, frontend)

| Bileşen | Test sayısı | Kapsam |
|---|---|---|
| `StageIndicator` | 1 | render 3 dot + current highlight |
| `AnchorCandidateCard` | 4 | render + 5 aksiyon click handler + ESTRA bar render + decision band border |
| `ProfileHint` | 1 | chip render + tek satır |
| `PreparingArea` | 2 | progress tick + onReady polling |

### Unit (pytest, backend)

| Servis | Test sayısı | Kapsam |
|---|---|---|
| `librarian.py` | 6 | Tur 1 happy / Tur 2 düzeltme / reset hafıza / Gemini fail 503 / parsed_understanding şema / `extra=forbid` |
| `anchor_finder.py` | 5 | 3 aday top-3 / Pinecone fail graceful / tsvector empty / reranker uniform fallback (P007 K11) / RRF k=60 |
| `cluster_expander.py` | 4 | RRF 3-kanal / theme kanal isabet / bib JOIN / project_cluster persist |
| `estra_scorer.py` | 3 | q_weak + cd_5 + beauty + pagerank skor / NULL handle / Plan 1 proxy ağırlık |

### Integration (httpx + TestClient)

- `POST /api/project` happy path + onboarding miras
- `research-area/messages` 2 tur dialog + reset
- `anchor/lock` + `lock-status` polling + `project_cluster` row count

### E2E (Playwright, F7'ye ertelendi)

- Stage A → B → C tam akış (browser hard refresh)

### Empirik kanıt kapısı (R13.13 zorunlu)

Her commit'te:
1. `cd /Users/omer/papermind-app && uv run pytest` EXIT 0 + son 3 satır log yapıştırılır
2. `cd web && npx next build` EXIT 0 + 9+ route generated kanıtı
3. `npx vitest run` EXIT 0 + 36+ PASS

---

## §13 — 7-kontrol (DM_RULES R2 zorunlu)

| # | Kontrol | Cevap |
|---|---|---|
| **1. Literatür** | Anchor + cluster expansion = bibliyometrik standart: cocitation Small (1973) + bibliographic coupling Kessler (1963); RRF Cormack et al. (2009 SIGIR); Sleeping Beauty Ke et al. (PNAS 2015); CD₅ disruption Funk & Owen-Smith (2017); Rao-Stirling (Stirling 2007). Daha kaliteli alternatif: **CLM (Citation Linkage Model)** + RRF F7+ kalibre Plan 2'de; MVP Plan 1 proxy yeterli. ✅ A kanıt |
| **2. Halüsinasyon** | §11 grep doğrulama 11 satır × A kanıt seviyesi (dosya:satır). `user_vectors` yok → §16 DEFERRED açıkça. `neighbor_bibcoupling` tablo adı düzeltildi → `fact_paper_bibcoupling_top50`. `papers.title_tsv` mevcut değil → P091 migration'a inline eklenir. ✅ |
| **3. Fayda-maliyet** | 1860 LOC + ~36 test + 8 atomik commit + ~4-5 gün; çıktı = projenin omurgası (proje bazlı pivot DM-018 + 1.1 ekran D9 §5.1 + ESTRA+validator çift katman B-022). Maliyet: Gemini Flash ~$0.001/2-tur sohbet × pilot 5 user × 5 proje = ~$0.025/proje hayat boyu (DM-LLM-1 budget projeksiyon §11 F8 ile uyumlu). **Net pozitif.** ✅ |
| **4. Daha kolayı** | Tek-sayfa monolith vs 8-commit boundary: monolith hata izolasyonsuz + R7 ihlali + hash recovery imkansız (B-014 lessons learned); 8-commit boundary recovery ucuzu + atomic empirik kanıt + plan revize granular. **Boundary tercih.** ✅ |
| **5. Son kullanıcı** | Hoca 3 paper'dan birini seçerek 500-makalelik alanı şeffaf+kontrollü açar. SciSpace generic Q&A; Consensus query→evidence-only; Elicit literatür özet; **niş**: PaperMind = proje bazlı sıralı tezgah + r-ESTRA sessiz öğrenme + ESTRA validator çift katman. Hoca'nın zamanı (3-5 dk araştırma alanı netleşir, alternatif: 30 dk Google Scholar gezme) + güveni (deterministik 3 aday, kara kutu yok) + kararı (rejected_anchors hafızası) iyileşir. ✅ |
| **6. Rakip** | SciSpace = generic Q&A (proje yok); Consensus = sadece arama (state yok); Elicit = literatür özet (chat yok); Scite = atıf bağlam (öneri yok). PaperMind 1.1 = proje bazlı + sıralı tezgah + 2-tur kütüphaneci + ESTRA çapa + 500 komşu deterministik. **Rakip yok bu kombinasyonda.** ✅ |
| **7. Lokal/global** | D9 5-tezgah modelinin 1.1'i; aynı Stage A/B/C pattern + 4 bileşen + endpoint sözleşmesi 1.2-5.6 sayfalarına extrapolate edilebilir. **Global çözüm.** Lokal hack: (a) FastAPI BackgroundTasks (Celery F7 P065'e ertelendi — geçici etiket §16'da); (b) Pinecone B-012 metadata patch yokken `filter=None` (1.1 tolere, 1.2 zorunlu — geçici etiket §16'da). ✅ |

---

## §14 — Sycophant kontrol (R3)

**"Mükemmel" / "Harika" yasak.** Bu plan'ın somut riskleri:

1. **Pinecone+tsvector paralel arama:** Pinecone B-012 metadata HARD filter patch tamamlanmadan da çalışır (`filter=None` fallback) — performans riski (geniş aday havuz ~500K vector tarama, p95 +1-2sn). 1.1'de tolere edilir; 1.2'de **zorunlu** (Omer Colab paralel akış).
2. **Background job ilk versiyon Celery DEĞİL:** FastAPI `BackgroundTasks` kullanılır (KD-?: Celery F7 P065'e ertelendi, B-018 Council 39 KD-36 Circuit Breaker pattern paralel). Job 30sn'i aşarsa kullanıcı kaybeder — `lock-status` polling 800ms × max 60 tick (48sn) timeout + `failed` status fallback. Pilot 5 user'da ölçeklenir; 100+ user'da Celery refactor zorunlu.
3. **LLM 2-tur sınırı düşük:** Kullanıcı 3. turda zorlanırsa fallback "3 makale göster" yumuşak; sohbet hâlâ erişilebilir ama anchor candidates state cache'lenir.
4. **`AnchorCandidate` kart 5-aksiyon yoğunluk:** Detay/Listeme/Özetle/Çevir/Danışmana sor + ÇAPA SEÇ = 6 buton → görsel kalabalık riski; D5 anatomi `flex-wrap` + amber CTA ayrı satır ile mitig (P052 PaperCard 6-action precedent).
5. **`papers.title_tsv` GENERATED STORED kolon:** 24.87M satır × ~200 byte tsvector = ~5 GB ek disk + 10-15 dk migration süresi (Supabase 2XL compute zorunlu, Pro tier $25/ay sınırı içinde). **Bir kez** yazılır; sonraki INSERT'ler trigger'sız otomatik.
6. **B-024 background canon ihlali riski:** AnchorCandidateCard'ın `bg-page` yerine kart-içi `paper-grain` texture kullanması zorunlu; halüsinasyon yaparsam B-024 RED olur. §10'da explicit yazıldı.

---

## §15 — Onay kapıları

1. **Plan manifest yazıldı** → Omer **"manifest onaylı"** der → P091 yeni session'da başlar.
2. Her commit empirik kanıt PASS (pytest + next build + vitest, R13.13) → sonraki commit.
3. P098 sonu **browser empirik test** (Stage A→B→C tam akış localhost:3000 hard refresh + screenshot) → 1.1 KAPANIR.
4. **1.1 KAPANMADAN 1.2 plan'ı YAZILMAZ / kod YAZILMAZ** (DM_RULES R1 mutlak).

---

## §16 — Engelleyici / DEFERRED

| # | Engel | Etki | Çözüm | Sahip |
|---|---|---|---|---|
| 1 | Pinecone B-012 metadata HARD filter patch tam değil | 1.2'de field/subfield/year HARD filter yok → geniş aday havuz; 1.1'de `filter=None` tolere edilir (performans hit p95 +1-2sn) | Omer Colab paralel akış — `mdv1` namespace'inde 8-meta upload tamamlanmış (B-012 ✅ KAPANDI 2026-05-01); patch'ın F9'da gerek olduğu yer yok, sadece 1.2'de | Omer |
| 2 | `user_vectors` pgvector tablosu yok (K-023 Brain memory) | 1.1'de **kullanılmaz**; 1.2 r-ESTRA profil eşleşme için zorunlu | F10 plan §0 önkoşulu olarak 0017 migration veya Brain ratifikasyon | Omer + Claude (F10 plan'da) |
| 3 | Background job library Celery değil | 100+ concurrent user'da `BackgroundTasks` event loop block riski | F7 P065'te Celery + Redis broker refactor (KD-36 paralel pattern) | Sercan / Claude F7'de |
| 4 | Render plan timeout limiti | BackgroundTasks job 30sn'i aşarsa free tier worker kill | Render plan teyit (Starter $7 vs Standard $25); 60sn target Starter sınırı içinde — Omer kontrol eder | Omer |
| 5 | F4-S3 OpenAlex+arXiv canlı arama (Hat 2) entegrasyonu | F4-S3 ayrı sprint plan'ında; F9 BÖLÜM 2 sadece corpus (Pinecone) + tsvector — canlı API havuzu YOK | F9 OUT scope; F4-S3 plan kapanışı sonrası ek slice F9.1 | Claude (F4-S3 closure sonrası) |
| 6 | `papers` tablosunda `title_tsv` kolonu yok | BÖLÜM 2 lexical havuz çalışmaz | P091 0015 migration'a inline `ADD COLUMN title_tsv tsvector GENERATED ALWAYS AS ... STORED` + GIN index (5 GB disk + 15 dk migration, 2XL compute) | Claude P091'de |
| 7 | Mevcut `TopicSuggestionPage` / `ThematicAnalysisPage` / `ConceptNetworkPage` | F4-S5 P083+ olarak Omer önceden draft yazmış olabilir | F9'da **DOKUNULMAZ**; 1.2/1.4/1.5 plan'larında refactor ele alınır | F10/F12/F13 plan'larında |

---

## §17 — Sonraki plan'lara pointer

| Plan | Faz | Scope | Ön koşul |
|---|---|---|---|
| `F10_konu_belirleme.md` | 1.2 Konu Belirleme | BÖLÜM 5 curator çıktısı + UI; r-ESTRA profil eşleşme (`user_vectors` 0017); `TopicSuggestionPage` refactor | F9 1.1 KAPANMASI + `user_vectors` migration |
| `F11_bibliyometri.md` | 1.3 Bibliyometri | Co-citation network + author/journal aggregates + vis-network/D3 | F10 KAPANMASI |
| `F12_tematik.md` | 1.4 Tematik Analiz | LDA/BERTopic + theme drift + `dim_theme_embedding` UMAP; `ThematicAnalysisPage` refactor | F11 KAPANMASI |
| `F13_kavram_agi.md` | 1.5 Kavram Ağı | NER + concept extraction + force-directed graph; `ConceptNetworkPage` refactor | F12 KAPANMASI |
| Tezgah 2-5 plan'ları | İnceleme / Literatür Boşluğu / Yazım / Savunma | D9 §5.2-5.6 sayfaları | Tezgah 1 (1.1-1.5) tüm KAPANMASI |

---

## §18 — Brain ratifikasyon (papermind-brain repo, ayrı commit + ayrı PR)

Plan kabul edilince Brain'e aşağıdaki K-NNN entry'si eklenecek (ayrı pencere, App PR'dan bağımsız):

```
- **K-029** (2026-05-05): F9 Keşif tezgahı 1.1 Araştırma Alanı kanonu —
  Stage A (kütüphaneci 2-tur Gemini 2.5 Flash via LiteLLM, ProjectContext otomatik enjekte, uyumsuzluk hafızası rejected_anchors+reject_reasons) +
  Stage B (3 çapa adayı, BÖLÜM 2 paralel arama: Pinecone vec havuzu + Supabase tsvector lexical havuzu → RRF k=60 → BGE-v2-m3 reranker → top-3) +
  Stage C (BÖLÜM 3-4-5 background, 500-aday vec+bib+theme RRF → Supabase enrich JOIN → ESTRA q_weak/cd_5/beauty/pagerank skor → curator signals_13 → project_cluster persist).
  4 yeni FE bileşen (StageIndicator/AnchorCandidateCard/ProfileHint/PreparingArea) + 4 yeni BE endpoint (project CRUD + research-area messages + anchor-candidates + anchor lock+status+reset) +
  0015/0016 migration (projects/project_chat_messages/project_anchor + papers.title_tsv + project_cluster).
  Lexical havuz kararı: Supabase tsvector (KD-23 KAPANIR, B-018 Council 25 ile uyumlu).
  Background job: FastAPI BackgroundTasks (Celery F7 P065'e ertelendi, KD-36 paralel).
  1.2-1.5 ayrı plan'lara ertelendi (F10-F13).
  Empirik kanıt: §11 grep doğrulama 11 satır × A kanıt seviyesi.
  Halüsinasyon düzeltme: `neighbor_bibcoupling` tablo adı = `fact_paper_bibcoupling_top50` (NO FK, 643M satır).
```

**Brain push protokolü:**
- P090 (bu plan) PR sonrası Omer "manifest onaylı" → ayrı pencere açılır → `papermind-brain` repo'da `K-029` entry → ayrı commit + ayrı PR.
- App PR (`feat/F9-kesif-tezgah` plan manifest) ve Brain PR bağımsız reviewer döngülerinden geçer; çelişki varsa R5 hiyerarşi (manifest > Brain).

---

## Kabul kriterleri (manifest tamamlanma)

- [x] §0..§18 eksiksiz, tüm başlıklar `reference/ARCHITECT_PROMPT_TEMPLATE` yapısı ile birebir
- [x] §11 grep doğrulama tablosu 11 satır × A kanıt seviyesi (gerçek dosya:satır)
- [x] §3 commit zinciri 8 satır (P091..P098), her satır subject + dosyalar + LOC + test
- [x] §6 SQL bloğu Supabase Dashboard'a paste edilebilir (RLS + index + CHECK + schema_migrations row)
- [x] §7 endpoint listesi 11 satır method + path + body + response + hata
- [x] §10 4 bileşenin TypeScript prop signature
- [x] §13 7-kontrol her satır cevaplı
- [x] §16 engelleyici tablosu 7 satır, her satır çözüm + sahip

---

**SON.** Bu manifest onayı sonrası P091 yeni session'da başlar. Onaya kadar sadece bu döküman + PR var. **Kod YASAK.**
