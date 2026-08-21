# V1-S14 — Mock-to-Live Wiring (Frontend → Supabase + Pinecone)

**Sub-sprint kodu:** V1-S14
**Önkoşullar:** V1-S13 ✅ (DataProvenance pattern · 8 atomik commit · `feat/V1-S13-demo-path-polish` merged)
**Plan tarihi:** 2026-05-10
**Onay:** Omer 2026-05-10 — "onaylıyorum. b olsun" (.env restore) + "sıralı git, P003 (b), P005 (c)" (P003 empty state, P005 paper_ids body)
**Branch:** `feat/V1-S14-mock-to-live` (off main HEAD `454ec2e` — V1-S13 + literature_review/tts hotfix merged)

---

## §0 — Amaç

Frontend mock fixture'larını gerçek backend'e bağla; mock = ürün → mock = canlı veri. 9 mock konum tespit edildi (önceki context envanter), 6'sı bu sprint'te bağlanır:

| Konum | Mock | Backend | Sprint |
|---|---|---|---|
| `app/(app)/search/page.tsx:11,14` | `search.json` + FIXTURE_PAPERS | `POST /api/search` ✓ | **P001** |
| `app/(app)/chat/page.tsx:8,27` + `ChatboxPanel.tsx:10,88` | `fixtureReply` + `lib/chat-fixture.ts` | `POST /api/chat` ✓ | **P002** |
| `lib/navigation-context.tsx:5,89` | `MOCK_PROJECTS` | `GET /api/project` ✓ | **P003** |
| `components/project/ResearchAreaConfirmPage.tsx:37,62,124` | PARSED + ANCHORS | `POST /api/q` ✓ | **P004** |
| (yok) | (yok) | `POST /api/project/{id}/bibliometrics` (yeni) | **P005** |
| `components/project/BibliometricSummaryPage.tsx:36,43,62,69,77,90` | 6 const | yeni endpoint | **P006** |

**Scope dışı:**
- `useTierMock.ts` (V1-S5 tier-canon scope)
- `lib/mock-data.ts` (demo seed, kalır)
- `lib/api.ts:64` `apiFetchOrFixture` helper (P001-P004 sonunda silinir, P006 sonunda commit'lenir)
- PostgREST schema cache (404 tablolar) — B-016 olarak ayrı iş, V1-S14 içinde değil

---

## §1 — Veri envanteri (kanıt seviyesi A — bu turda Supabase + Pinecone canlı sorgulandı)

### Pinecone
- Index: `papers-bgem3` · Namespace: `mdv1` · **24,866,945 vektör** · 1024-dim · cosine

### Supabase dolu warehouse fact tabloları (paper_id ortak join key)

| Tablo | Satır | Kritik kolonlar |
|---|---|---|
| `fact_paper_id_card` | 24,862,232 | `paper_id, year, language, type_*, dominant_type, title, abstract_short, keywords, doi, venue, topic_profile` |
| `fact_paper_quality_v3` | 24,862,232 | `paper_id, q_weak, q_weak_v2, n_lfs_active` |
| `fact_paper_beauty` | 24,862,232 | `paper_id, pub_year, total_cites, b, c_max, t_m, t_a` |
| `fact_paper_sentence_role` | 24,862,232 | `paper_id, n_method, n_result, n_conclusion, dominant_role` |
| `fact_paper_temporal` | 18,374,327 | `paper_id, total_citations, cite_age_p25/median/p75, cite_half_life` |
| `fact_gap_matrix` | 504,436 | `axis_x, axis_y, gap_value, feasibility, publishability` |
| `fact_theme_year_aggregates` | 53,943 | `theme_id, year, paper_count, r_mean, e_mean, c_k, mq_k` |
| `dim_theme_embedding` | 4,516 | `theme_id, embedding[1024], text_source` |
| `dim_subfield` | 252 | `subfield_id, field_id, name_en, slug, paper_count_total` |
| `dim_field` | 26 | `field_id, name_en, slug, paper_count_total` |

### Boş tablolar (seed yok, normal — backend yazar)
`papers, user_profiles, projects, project_chat_messages, project_anchor, project_cluster`

### Erişilemeyen (PostgREST 404/500 — scope dışı)
`dim_ghost_paper, project_seed_papers, waitlist, paper_authors, dim_author, mart_*, fact_paper_velocity, fact_paper_method, fact_paper_topic`

---

## §2 — Yol kararları

### KD-V1-S14-01 — Sıralı 6 commit (paralel değil)
Omer onayı 2026-05-10. Sebep: P001-P002 düşük risk warm-up; P004 zincirleme bağımlı (q endpoint yanıt şekli ResearchArea kabul kriterini belirler); P005 yeni servis writer + P006 consumer test.

### KD-V1-S14-02 — P003 empty state (Omer 2026-05-10 (b))
`projects` tablosu boş. Seed migration **yazılmaz**. Frontend `MOCK_PROJECTS` silindiğinde "henüz proje yok · onboarding'den başla" CTA gösterir. Avantaj: gerçek kullanıcı yolu test edilir; mock seed yanılsama yaratmaz.

### KD-V1-S14-03 — P005 paper_ids body (Omer 2026-05-10 (c))
Bibliometric endpoint `project_seed_papers` PostgREST 404 sorununa girmez. Body'de `paper_ids: list[str]` array al. Frontend zaten projenin paper listesini bildiği için (kendi state'inde), bunu request'te gönderir. Backend SQL: `WHERE paper_id = ANY($1)`.

### KD-V1-S14-04 — apiFetchOrFixture helper'ı P006'da sil
Helper'ı her commit'te kısmen kullansak da silmek P006'da olur (BibliometricSummaryPage son tüketici). P001-P005 boyunca yardımcı kalır, son commit'te `lib/api.ts:64-78` + `lib/chat-fixture.ts` kaldırılır.

### KD-V1-S14-05 — Auth header
Frontend `apiFetchOrFixture`'a `Authorization: Bearer <jwt>` ekleme zorunlu değil bu sprint — mevcut endpoint'lerin çoğu `dev_user` fallback kabul ediyor (kanıt seviyesi B — F10 closure'da yazılı, P001'de Read ile doğrulanacak). Eğer 401 dönerse: ya devleştir, ya P001'den önce auth kontekst migration'u (B-017 olarak yeni iş).

---

## §3 — Atomik commit haritası

### P001 — Search live wire
**Dosyalar:**
- Edit: `web/src/app/(app)/search/page.tsx` — `search.json` import sil, `FIXTURE_PAPERS` sil, `apiFetchOrFixture` → `apiFetch` (gerçek)
- Read-only: `api/routes/search.py:114` — request/response schema doğrula

**Kabul:**
- "Bibliometrics" araması canlı 5+ sonuç döner (Pinecone hit)
- vitest mevcut search testleri PASS (eğer fixture mocking varsa, MSW handler güncellenir)
- tsc PASS, build PASS
- Browser smoke: search bar boş ekrandan sonuç ekranına geçiş <2s

**Risk:** auth header (KD-V1-S14-05). Eğer 401 → P001 stop, B-017 aç.

---

### P002 — Chat live wire
**Dosyalar:**
- Edit: `web/src/app/(app)/chat/page.tsx`, `web/src/components/chat/ChatboxPanel.tsx` — `fixtureReply` + `chat-fixture` import sil; `apiFetch` ile streaming endpoint
- Delete: `web/src/lib/chat-fixture.ts`

**Kabul:**
- "Lithium-ion catalysts" gibi soru gerçek Gemini Flash yanıtı verir
- Streaming chunks UI'da görünür
- vitest + tsc + build PASS
- Browser smoke: 3 turn konuşma + 1 paper-anchor reference

**Risk:** Streaming response shape — `POST /api/chat` chunk format frontend bekleyenle eşleşir mi (`response_model=ChatChunk`).

---

### P003 — Projects list live wire (empty state)
**Dosyalar:**
- Edit: `web/src/lib/navigation-context.tsx` — `MOCK_PROJECTS` const sil, `useEffect` ile `GET /api/project` çek; loading + empty + error state
- Edit: navigation sidebar empty state UI ("henüz proje yok · onboarding")

**Kabul:**
- Sidebar boş listede "henüz proje yok" CTA gösterir (KD-V1-S14-02)
- vitest + tsc + build PASS
- Browser smoke: yeni hesapta sidebar boş; onboarding'den proje yaratma → sidebar'a düşer

**Risk:** Onboarding flow projeyi nereye insert ediyor — backend yazıyor mu yoksa client'mı bekleniyor? `api/routes/onboarding.py` Read ile doğrulanır.

---

### P004 — ResearchArea live wire
**Dosyalar:**
- Edit: `web/src/components/project/ResearchAreaConfirmPage.tsx:37,62,124` — `PARSED` + `ANCHORS` sabitleri sil; `POST /api/q` (literature-review variant uygunsa) çağır

**Kabul:**
- Kullanıcı serbest metin alanı + onay butonu canlı listener+anchor sonucu döner (5-katman: Listener Gemini + Anchor OpenAlex/Mock + PoolRouter Pinecone+tsvector RRF)
- vitest + tsc + build PASS
- Browser smoke: "iyon piller" → 3 anchor + 1 cluster önerisi

**Risk:** `POST /api/q` response shape ResearchAreaConfirmPage'in beklediğiyle eşleşmiyor olabilir. Endpoint Read ile şema kontrolü P004 başında zorunlu.

---

### P005 — Bibliometric service backend (yeni) — **REVİZE 2026-05-10**

**Plan §1 column hatası:** `fact_paper_id_card`'da `venue/title/abstract_short/doi/keywords` **yok** (migration `0003_paper_anchor_facts.sql:31-48` ve servisler `api/services/curator.py:120` doğrulandı). `papers` tablosu boş. Yazar tabloları (`paper_authors/dim_author`) PostgREST 404. → TOP_VENUES, TOP_AUTHORS, LOTKA_BINS canlı türetilemez. **Karar (Omer 2026-05-10): B opsiyonu — frontend metric setini warehouse'a hizala.**

**Dosyalar:**
- Yeni: `api/services/bibliometric_service.py` — Supabase client wrapper, 6 aggregate fonksiyonu:
  - `compute_median_year(paper_ids)` → `fact_paper_id_card.year` Python median
  - `compute_mean_citations(paper_ids)` → `fact_paper_beauty.total_cites` AVG
  - `compute_publications_by_year(paper_ids)` → `fact_paper_id_card.year` GROUP BY (Python aggregation)
  - `compute_language_dist(paper_ids)` → `fact_paper_id_card.language` GROUP BY (Python aggregation)
  - `compute_top_areas(paper_ids, k=10)` → `fact_paper_field.primary_field` GROUP BY + `dim_field.name_en` JOIN
  - `compute_top_methods(paper_ids, k=10)` → `fact_paper_sentence_role.dominant_role` GROUP BY
  - `most_cited_paper(paper_ids)` → `fact_paper_beauty` ORDER BY total_cites DESC LIMIT 1 + `fact_paper_id_card.pmid` (title yok, frontend pmid placeholder)
- Yeni: `api/routes/project_bibliometrics.py` — `POST /api/project/{project_id}/bibliometrics`, body `{paper_ids: list[str]}`, response `BibliometricSummary` Pydantic
- Yeni: `api/models/bibliometric.py` — Pydantic models (api/models pattern, `api/schemas/` dizini yok)
- Edit: `api/main.py` — router register

**Kabul:**
- pytest 6 unit test (her aggregate için 1) PASS
- 1 integration test: 50-paper mock seed → endpoint 200 OK + tüm alanlar dolu
- mypy + ruff PASS

**Risk:**
- Supabase IN filter max 100 — `paper_ids > 100` ise batch'le (curator.py pattern: `for i in range(0, len(ids), 100)`)
- `fact_paper_field` 24.86M satır, `paper_id` PRIMARY KEY (idx `0006:21`); `dim_field` ile JOIN PostgREST tek-query yerine 2-step (paper_field + dim_field map merge) yap
- `fact_paper_beauty` `total_cites` PRIMARY KEY indeksinden okunur; aggregate Python-side

---

### P006 — Bibliometric live wire + helper cleanup — **REVİZE 2026-05-10**
**Dosyalar:**
- Edit: `web/src/components/project/BibliometricSummaryPage.tsx` — 6 const sil; `useQuery` ile `POST /api/project/{id}/bibliometrics` çek; **metric set warehouse'a hizalı:**
  - TOP_VENUES → **TOP_AREAS** (alan dağılımı, `fact_paper_field.primary_field` 24.86M dolu)
  - TOP_AUTHORS + LOTKA_BINS → **TOP_METHODS** (yöntem dağılımı, `fact_paper_sentence_role.dominant_role`)
  - mostCited.title → frontend "PMID-{pmid}" placeholder (papers tablosu boş, lazy-fill V2)
- DataProvenance pill `confidence="A"` (warehouse aggregate)
- Delete: `web/src/lib/api.ts:64-78` — `apiFetchOrFixture` helper

**Kabul:**
- Sayfa açıldığında skeleton → ~2s sonra canlı 6 metrik
- DataProvenance pill `N=<gerçek>` (mock 240 değil)
- vitest + tsc + build PASS
- Browser smoke: gerçek proje üzerinde 6 metrik gözle doğrulanır

---

## §4 — Test piramidi (her commit'te)

R13.13 protokol:
1. `cd web && npx vitest run` — unit + component (PASS = ✅ X/X files / Y/Y tests)
2. `cd web && npx tsc --noEmit` — type check
3. `cd web && npm run build` — production build PASS
4. (P001-P004, P006) Browser smoke — golden path + 1 edge case
5. (P005) `cd api && pytest tests/ -k bibliometric` — backend unit + integration

Commit body'sinde her 5 satır R13.13 evidence zorunlu.

---

## §5 — Risk ve geri dönüş

**Yüksek risk:** P005 (yeni servis, 24M tablo aggregate). Geri dönüş: P006'ya geçmeden P005 stop. Bibliometric endpoint hazır olmadan P006 başlamaz.

**Orta risk:** P004 (5-katman live), P003 (auth + onboarding zinciri).

**Düşük risk:** P001, P002 (mevcut endpoint).

**Tamir senaryosu:** Herhangi commit fail ederse → `git revert HEAD`, plan manifest revize, yeni onay.

---

## §6 — Plan revizyon log
- 2026-05-10 — İlk versiyon, Omer onayı sonrası yazıldı.
- 2026-05-10 (B-029) — P005/P006 schema hizalama. Plan §1 column listesi (`fact_paper_id_card.venue/title/abstract_short/doi/keywords`) migration evidence'a (`0003_paper_anchor_facts.sql:31-48`) ve servis kullanımına (`api/services/curator.py:120`) göre yanlıştı. `papers` tablosu boş + author tabloları PostgREST 404. Frontend metric seti warehouse'a hizalandı: TOP_VENUES→TOP_AREAS, TOP_AUTHORS+LOTKA_BINS→TOP_METHODS, mostCited.title→pmid placeholder. Omer onayı: "b" 2026-05-10.
