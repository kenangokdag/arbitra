# F3e — Mini-Plan: /api/reading-list (CRUD)

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16)
> **Üst plan**: `docs/plans/F1_master_plan.md`
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + WhatsApp checklist
> **Owner**: Sercan (backend code) · Claude (RLS audit) · Omer (UX onayı tag taksonomisi)

---

## §0 Bağlam (3 cümle)

E5 detay sayfasındaki "Okuma Listesine Ekle" + ana navigasyondaki `/kutuphane/okuma-listesi` ekranının arkası — kullanıcının kayıt ettiği paper'lar (corpus + ghost), notlar, etiketler ve durumu (`to_read` / `reading` / `done`) için tipik CRUD endpoint. Niş ayrım: jenerik bookmark değil — Supabase RLS ile çapraz kullanıcı erişimi imkânsız (KVKK uyumlu), `paper_id` foreign key validation, paper deduplikasyonu (aynı paper 2× eklenmez), tier kuotası (Öğrenci 50 paper limit). MVP'nin tek senkron CRUD endpoint'i — Pinecone/LLM yok, p95 < 500ms hedefi.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| Supabase RLS (`auth.uid() = user_id`) her satırda | master §6.5 + DM-003 | migration policy |
| Tier kuotası: Öğrenci 50 paper, Araştırmacı/Profesyonel/Takım MVP-sonrası | B42-049 §1 + master §6.2 | INSERT guard |
| Deduplikasyon: `UNIQUE(user_id, paper_id)` constraint | M52 (B42-045) | DB constraint |
| Status enum: `to_read` / `reading` / `done` (MVP'de 3 state) | UX simplicity | column |
| `note` TEXT max 2000 char (form Zod ayniyle) | master §6.4 | Pydantic max_length |
| `tags` TEXT[] (Postgres array, max 10 tag, her tag 50 char) | M52 | DB array |
| Sıralama: `pinned` (manual order) DEFAULT, fallback `added_at DESC` | UX | response order |
| Optimistic concurrency: `updated_at` OCC field, `If-Match` header opsiyonel | MVP-sonrası | header |
| Response cache YOK (her zaman fresh — list küçük < 50 satır) | master §3 | no Redis |
| `paper_id` FK: `papers` (corpus) VEYA `dim_ghost_paper` (ghost) — 2 tablo birden referans | M52 | trigger validate |
| LLM kullanılmaz, faithfulness gate yok | scope | — |

---

## §2 Endpoint sözleşmesi (tam OpenAPI)

```yaml
# 1. LIST
GET /api/reading-list
authorization: Bearer <jwt>
query:
  status?: to_read | reading | done
  tag?: string                     # tek tag filter
  limit: int default 50
  offset: int default 0
response 200:
  type: object
  properties:
    items: { type: array, items: ReadingItem }
    total: int
    quota: { used: int, limit: int }   # ör. {used: 23, limit: 50}

# 2. CREATE
POST /api/reading-list
body:
  paper_id: string             # corpus W123 veya GHOST_OA_W123
  note?: string (≤ 2000)
  tags?: string[] (≤ 10, her ≤ 50)
  status?: to_read | reading | done (default to_read)
response 201: ReadingItem
errors:
  404 paper_not_found
  409 already_in_list             # UNIQUE(user_id, paper_id) violation
  422 schema_invalid | quota_exceeded   # 50 paper aşımı

# 3. UPDATE
PATCH /api/reading-list/{id}
body: { note?, tags?, status?, pinned? }
response 200: ReadingItem
errors:
  404 not_found_or_not_yours      # RLS reject
  422 schema_invalid

# 4. DELETE
DELETE /api/reading-list/{id}
response 204
errors: 404 not_found_or_not_yours

# 5. (opt) BULK STATUS UPDATE
PATCH /api/reading-list/bulk
body: { ids: uuid[], status: to_read|reading|done }
response 200: { updated: int }

ReadingItem:
  type: object
  properties:
    id:           uuid
    user_id:      uuid (gizli — response'ta yok, RLS zaten enforce)
    paper_id:     string
    paper_kind:   { type: string, enum: [corpus, ghost] }
    paper_card:   PaperCard | GhostCard       # join projection
    note:         string|null
    tags:         string[]
    status:       to_read|reading|done
    pinned:       boolean
    pinned_order: int|null                    # pinned=true ise manuel sıra
    added_at:     date-time
    updated_at:   date-time
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P031** | `user_reading_list` tablo + RLS + UNIQUE constraint + index migration | `db/migrations/0005_reading_list.sql` | ~80 | RLS audit: anon → empty list; cross-user → reject |
| **P032** | Pydantic schemas (Request + ReadingItem + PaperCard projection) | `api/models/reading_list.py` | ~120 | unit: validation max_length + enum + array bounds |
| **P033** | LIST + CREATE route + dedup guard + tier kuota guard | `api/routes/reading_list.py` | ~120 | integration: 200 + 201 + 409 + 422 quota |
| **P034** | UPDATE + DELETE + bulk PATCH | `api/routes/reading_list.py` (extension) | ~80 | integration: 200 + 204 + 404 RLS |
| **P035** | Paper join projection (corpus VEYA ghost — 2 tablo birden) | `api/services/reading_list_service.py` | ~80 | unit: paper_kind=corpus + paper_kind=ghost |
| **P036** | Optimistic UI hook backend hazırlığı (no-op MVP, PATCH idempotent) | (test only) | — | integration: aynı PATCH 2× → 200 + 200 (idempotent) |

---

## §4 Verification (komut + beklenen output, 6 manuel smoke senaryosu)

```bash
# S1: Unit + RLS migration
pytest tests/unit/ -v -k "reading_list"
psql $SUPABASE_URL -c "\d user_reading_list"
# Beklenen: ≥10 PASS; tablo + UNIQUE(user_id, paper_id) + RLS POLICY 4 (SELECT, INSERT, UPDATE, DELETE)

# S2: CREATE happy path
curl -X POST http://localhost:8000/api/reading-list \
  -H "Authorization: Bearer $JWT" \
  -d '{"paper_id":"W123","note":"derin öğrenme + depresyon","tags":["dl","mh"]}'
# Beklenen: 201 + ReadingItem.id + paper_kind=corpus + paper_card.title var + quota.used += 1

# S3: Dedup (409)
curl ... -d '{"paper_id":"W123"}'   # aynı paper 2.×
# Beklenen: 409 + body {error: "already_in_list", existing_id: "..."}

# S4: LIST + filter
curl "http://localhost:8000/api/reading-list?status=to_read&tag=dl&limit=10"
# Beklenen: 200 + items[].status==to_read + items[].tags includes "dl" + total + quota

# S5: UPDATE status
ITEM_ID=$(... .items[0].id)
curl -X PATCH /api/reading-list/$ITEM_ID -d '{"status":"reading","pinned":true,"pinned_order":1}'
# Beklenen: 200 + status=reading + pinned=true + updated_at güncel

# S6: DELETE
curl -X DELETE /api/reading-list/$ITEM_ID
# Beklenen: 204 + ardışık GET /api/reading-list quota.used -= 1

# S7: RLS reject (cross-user)
JWT_BOB=...
curl -X DELETE /api/reading-list/$ITEM_ID_OF_ALICE -H "Authorization: Bearer $JWT_BOB"
# Beklenen: 404 (RLS Bob'a göstermez, UPDATE/DELETE etkilemez)

# S8: Quota exceeded (Öğrenci 50 limit)
for i in {1..51}; do curl ... -d "{\"paper_id\":\"W$i\"}" -o /dev/null -w "%{http_code}\n"; done
# Beklenen: ilk 50 → 201; 51. → 422 + body {error: "quota_exceeded", limit: 50}

# S9: Ghost paper kabul
curl ... -d '{"paper_id":"GHOST_OA_W4567","note":"klasik"}'
# Beklenen: 201 + paper_kind=ghost + paper_card.year_verified flag

# S10: Latency
time curl /api/reading-list   # 30 satır
# Beklenen: < 500ms (master §3 hedefi)
```

---

## §5 Critical files

### Backend touch
- `api/routes/reading_list.py` (LIST + CREATE + UPDATE + DELETE + bulk)
- `api/models/reading_list.py` (Pydantic)
- `api/services/reading_list_service.py` (paper_kind join)
- `db/migrations/0005_reading_list.sql` (tablo + RLS + index + UNIQUE + trigger)

### Tests touch
- `tests/unit/test_reading_list.py` (validation)
- `tests/integration/test_reading_list_endpoint.py` (S2-S10)
- `tests/integration/test_reading_list_rls.py` (S7 cross-user)

### Read-only
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-045-MIMARI-V1.md` (M52 reading list)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/DM_RULES.md`

---

## §6 TODO(sercan)

### 6.1 Infrastructure
- [ ] Supabase migration 0005_reading_list:
  - tablo: id (uuid pk), user_id (uuid fk), paper_id (text), paper_kind (text check), note (text), tags (text[]), status (text check), pinned (bool), pinned_order (int), added_at (timestamptz default now), updated_at (timestamptz)
  - UNIQUE(user_id, paper_id)
  - INDEX (user_id, status), INDEX (user_id, pinned, pinned_order)
  - RLS: 4 policy (SELECT/INSERT/UPDATE/DELETE auth.uid() = user_id)
  - Trigger: paper_id existence check (papers OR dim_ghost_paper)
  - Trigger: updated_at auto-set

### 6.2 Code
- [ ] P031-P036 sırasıyla atomik commit
- [ ] Pydantic max_length 2000 (note), array bounds (tags ≤10, each ≤50 char), status enum
- [ ] Tier quota guard: INSERT öncesi `user_reading_list` count + tier limit kıyas
- [ ] Paper join: corpus için `papers`, ghost için `dim_ghost_paper` (2 LEFT JOIN, paper_kind belirler)
- [ ] Bulk PATCH: max 100 id (request body cap)
- [ ] Idempotency: aynı PATCH body 2× → aynı response (UPDATE no-op)

### 6.3 Tests + Quality
- [ ] Unit ≥10 PASS
- [ ] Integration S2-S10 PASS
- [ ] RLS audit: cross-user 100% reject (S7)
- [ ] Latency < 500ms 30 satır LIST (S10)
- [ ] Quota guard 51. INSERT → 422 (S8)

### 6.4 Auth + Observability
- [ ] JWT verify
- [ ] Rate limit: tier-bazlı (Öğrenci 120 req/min)
- [ ] Sentry: standart trace_id

---

## §7 Commit disiplini

- **Branch**: `feat/F3-reading-list-crud`
- **Atomic commit**: P031..P036 ayrı commit + ayrı PR
- **Pre-flight Read**: §5 listesi
- **Test gate**: §4 S1-S10 PASS olmadan merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] api/reading-list: <kısa>` (örn. `[P031] api/reading-list: schema + RLS migration`)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| `papers` + `dim_ghost_paper` Supabase upload | ✅ B-008 (PaperCard 24.86M + GhostCard 31.85M; FK: paper_id existence check trigger için ikisi de hazır) |
| `user_quota` tablo (B-002 schema_v1 §5) | ✅ B-002 |
| RLS policy template (auth.uid() = user_id) | ✅ B-002 (11 uygulama tablosunda enable) |

### ⏳ F3a bağımlı
| Önkoşul | Statü |
|---|---|
| F3a P001 (auth middleware Supabase JWT verify) merge | ⏳ F3a PR |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| Supabase migration `0008_reading_list.sql` (user_reading_list + RLS + UNIQUE + 2-tablo FK trigger) | ⏳ | F3e P031 |

**Not:** F3e MVP'nin **en hafif endpoint**'i — LLM yok, Pinecone yok, sadece RLS CRUD. F3a P001 sonrası hemen başlanabilir.

---

**Final commitment**: F3a sonrası bu en hafif endpoint — 1-2 günde curl S2-S10 PASS. MVP'nin son backend slice'ı.
