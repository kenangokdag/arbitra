# V1-S15.pre — Anchor Lock Endpoint (Plan Manifest)

> **Tarih:** 2026-05-13 · **Bağlı plan:** V1-S15 ConceptNetwork (engelli)
> **Kanun:** CLAUDE.md §0 plan-first. Omer "plan onaylandı" demeden kod yazılmaz.

---

## §0 — Plan kimliği

- **Sprint:** V1-S15.pre (Kavram Ağı'nın bağlı olduğu anchor lock back'i)
- **Repo:** `/Users/omer/papermind-app` · **Branch:** `design/sayfa-plani-v2`
- **Bağlı planlar:**
  - F9 §7 tablo satır 278-279 (endpoint sözleşmesi — kanonik kaynak)
  - F9 §4 senaryo madde 8-10 (Stage B→C akış)
  - `Page_Design/Sayfa_Plani_v2/2.2_konu_belirleme.rtf:94-99` ("HENÜZ YAZILMAMIŞ" notu)
- **Engelliyor:** V1-S15 ConceptNetwork (anchor_paper_id okunmadan FE bağlanamaz)

---

## §1 — Niyet (1 paragraf)

Stage B'nin 3 aday içinden seçilen çapayı `project_anchor` satırına yaz, sonraki sayfalar (2.2 Konu Belirleme, 2.5 Kavram Ağı, atölye) bu çapayı okusun. Şu an `project_anchor.anchor_paper_id` koduyla yazılmıyor (kanıt-A: `grep -r anchor_paper_id api/` boş). FE `ResearchAreaConfirmPage` (web/src/components/project/ResearchAreaConfirmPage.tsx) anchor-candidates döndürüyor ama seçim sonrası `/anchor/lock` POST'u yok — kullanıcı çapa seçemiyor.

---

## §2 — Kapsam (IN / OUT / DEFERRED)

### IN (bu sprint)
- `POST /api/project/{id}/research-area/anchor/lock` body `{paper_id: str}` → **200** `{anchor_paper_id, locked_at}` (senkron, BackgroundTasks **YOK**)
- `project_anchor` satır upsert: `anchor_paper_id`, `locked_at = now()`, `cluster_status = 'pending'` (Stage C başlamadığı için pending kalır)
- `candidates_meta` jsonb upsert: Stage B'nin döndürdüğü 3 aday + seçilen paper_id metadata (kaybolmasın diye)
- Pydantic `LockRequest`, `LockResponse` (HK-1 forbid)
- Ownership zırhı (K-031 manuel `.eq("user_id", uid)`)
- Hata yolları: 404 project_not_found · 409 already_locked (idempotent değil, 2. lock reddedilir) · 409 paper_id_not_in_candidates (Stage B aday listesinde olmayan ID reddedilir — güvenlik)

### OUT (bu sprint dışı)
- Stage C cluster_expander.py (~280 LOC, BÖLÜM 3-4-5 RRF + ESTRA) — F9 §75 P096
- BackgroundTasks + worker + job_id semantiği — Stage C başlayınca gerekecek
- `GET /research-area/lock-status` — Stage C polling endpoint'i, Stage C olmadan dönecek hiçbir şey yok
- FE `ResearchAreaConfirmPage` "ÇAPA SEÇ" CTA wiring — V1-S15 P002'de yapılacak (bu plan değil)

### DEFERRED (engelleyici değil ama bilinmesi gerek)
- F9 §98 spec'inde `202 + job_id` var; biz **200 senkron** dönüyoruz. Sebep: Stage C yok → arkada job tetiklenmiyor → 202 yalan olur. Stage C gelince upgrade'lenir, FE polling eklenir.

---

## §3 — Kanıt-A (mevcut durum, 2026-05-13)

| İddia | Kanıt | Sonuç |
|---|---|---|
| `project_anchor` tablosu var | `db/migrations/0015_projects_skeleton.sql:95-104` | A — kullanılabilir |
| `anchor_paper_id text` nullable | aynı dosya `:97` | A — UPDATE/UPSERT yeterli |
| `cluster_status` CHECK ENUM | aynı `:102-103` | A — `pending` default geçerli |
| `candidates_meta jsonb` nullable | aynı `:98` | A — Stage B aday listesi buraya |
| RLS owner-only policy | aynı `:108-110` | A — admin client + manuel .eq zırh canon (K-031) |
| `anchor_paper_id` yazan kod yok | `grep -nr anchor_paper_id api/` → 0 hit | A — endpoint gerçekten yok |
| `research_area_reset.py` sadece `rejected_anchors`/`reject_reasons` yazıyor | `api/services/research_area_reset.py:103-140` | A — lock akışı bağımsız |
| FE confirm sayfasında `/anchor/lock` çağrısı yok | `ResearchAreaConfirmPage.tsx` grep `lock` → 0 | A — FE bekliyor |
| Endpoint sözleşmesi F9 §7'de yazılı | `docs/plans/F9_kesif_workbench.md:278` | A — kanonik kontrat |

---

## §4 — Endpoint sözleşmesi

```
POST /api/project/{project_id}/research-area/anchor/lock
Auth: AuthMiddleware request.state.user_id (401 if missing)
Body: { "paper_id": "W2118646272" }   # min_length=1, max_length=64
Response 200: {
  "anchor_paper_id": "W2118646272",
  "locked_at": "2026-05-13T09:30:00Z"
}
Hatalar:
  422 — Pydantic validation (paper_id boş/uzun)
  401 — missing_user_id (AuthMiddleware)
  404 — project_not_found (ownership zırhı)
  409 — already_locked  (project_anchor.anchor_paper_id zaten dolu, locked_at not null)
  409 — paper_id_not_in_candidates (Stage B candidates_meta listesinde değil)
  503 — supabase_unavailable
```

**Neden 202 değil 200:** Stage C arka iş yok; senkron tek UPDATE. 202 dönmek "iş başladı" yalan olur → kullanıcı `/lock-status` polling'inde sonsuza kadar `pending` görürdü.

**Neden 409 already_locked:** Çapa kilitlendikten sonra sayfa 2.2 Konu Belirleme açılmalı; kullanıcı tekrar 2.1'e gelirse "tekrar reset" UX'ı `/reset` endpoint'inden geçer, lock endpoint'inden değil. Bu güvenlik kapısı, accidental double-click korumasıdır.

---

## §5 — Service akış (`api/services/anchor_lock.py`)

```
async def run(*, db, project_id, user_id, paper_id) -> LockResponse:
    1. _verify_ownership(db, project_id, user_id)
         → SELECT id FROM projects WHERE id=$1 AND user_id=$2 LIMIT 1
         → boşsa ProjectNotFoundError → 404

    2. _load_anchor_state(db, project_id)
         → SELECT anchor_paper_id, candidates_meta, locked_at FROM project_anchor WHERE project_id=$1
         → row yoksa AnchorRowMissingError (Stage B çağrılmadı demek)
         → anchor_paper_id not null OR locked_at not null → AlreadyLockedError → 409

    3. _verify_paper_in_candidates(candidates_meta, paper_id)
         → candidates_meta["candidates"] içinde paper_id eşleşmiyorsa PaperIdNotInCandidatesError → 409

    4. _lock_anchor(db, project_id, paper_id)
         → UPDATE project_anchor SET
               anchor_paper_id = $2,
               locked_at = now(),
               cluster_status = 'pending'  -- Stage C başlamadı, default kalır
            WHERE project_id = $1
         → return (paper_id, locked_at_iso)

    5. return LockResponse(anchor_paper_id=paper_id, locked_at=locked_at_iso)
```

**Why service ayrı dosya:** `research_area_reset.py` pattern'i (F13-S12-P003) bire bir takip ediliyor. Endpoint route ince, business logic service'te.

**candidates_meta şekli (Stage B'den):** `anchor_finder.py`'nin upsert ettiği jsonb — şu an `candidates: [{paper_id, ...}, ...]` listesi içeriyor (kanıt: `anchor_finder.run`'a bakılacak — açık soru §8.1).

---

## §6 — Atomik commit haritası (3 commit)

| # | Commit | Dosyalar | Test |
|---|---|---|---|
| P001 | `feat(api): V1-S15.pre-P001 — LockRequest/LockResponse Pydantic` | `api/models/research_area.py` (+ ~25 LOC) | unit: extra forbid, paper_id min/max |
| P002 | `feat(api): V1-S15.pre-P002 — anchor_lock servisi` | `api/services/anchor_lock.py` (yeni) | unit: 4 hata yolu (ownership, missing, already_locked, not_in_candidates) + golden path |
| P003 | `feat(api): V1-S15.pre-P003 — POST anchor/lock route` | `api/routes/research_area.py` (+ ~30 LOC) | integration: TestClient 200 / 401 / 404 / 409 × 2 / 503 |

**Boundary kuralı:** Her commit tek atomik unit, test yeşil. P001 tip-only, P002 servis + unit, P003 route + integration.

---

## §7 — Test stratejisi

### Unit (pytest, backend)
1. `test_lock_request_validation` — paper_id boş 422, 65 char 422
2. `test_anchor_lock_ownership_missing` — başka user'ın project_id → ProjectNotFoundError
3. `test_anchor_lock_row_missing` — Stage B çağrılmamış → AnchorRowMissingError
4. `test_anchor_lock_already_locked` — anchor_paper_id dolu → AlreadyLockedError
5. `test_anchor_lock_not_in_candidates` — candidates_meta'da olmayan paper_id → PaperIdNotInCandidatesError
6. `test_anchor_lock_golden_path` — Stage B candidates_meta var, paper_id eşleşiyor → UPDATE + LockResponse

### Integration (httpx TestClient)
7. `test_route_200_locks_anchor` — golden path + DB satır UPDATE doğrula
8. `test_route_401_missing_user` — header yok → 401 missing_user_id
9. `test_route_404_not_owner` — başka user → 404 project_not_found
10. `test_route_409_already_locked` — 2. çağrı → 409
11. `test_route_503_supabase_unavailable` — SUPABASE_URL boş → 503

**Mock pattern:** `research_area_reset` testleri (api/tests/services/test_research_area_reset.py varsa) referans alınır; supabase client mocklanır, `supabase_call_async` lambda fixture.

---

## §8 — Açık sorular (Omer onayı gerek)

1. **candidates_meta şekli** — `anchor_finder.py` `project_anchor.candidates_meta`'ya yazıyor mu, yazıyorsa hangi key (`candidates` mi, `top3` mi)? Plan §5 adım 3 buna bağlı. → Plan onayı öncesi `Read api/services/anchor_finder.py` ile doğrulanacak. **Risk:** yazmıyorsa P002'den önce mini upsert eklemek gerekir.

2. **already_locked 409 mi, idempotent 200 mi?** F9 §98 belirtmiyor. Önerim: **409**. Sebep: lock semantiği "tek seferlik karar" — yanlışlıkla 2. tıklama silent geçerse kullanıcı reset'e gitmeyi unutur, eski çapa kalır. 409 ile FE "Çapa zaten kilitli. Reset?" diyalogu açar. Kabul mü?

3. **paper_id_not_in_candidates 409 vs 422?** Stage B kullanıcıya sadece 3 aday gösteriyor; FE 4. ID gönderirse manipülasyon. Önerim **409 conflict** (business rule), **422** değil (schema valid). Kabul mü?

4. **Lock sonrası `current_stage` ilerlet mi?** `projects.current_stage` var (0015:34). 2.1 → 2.2 geçişinde `current_stage = 'topic_selection'` UPDATE'i bu endpoint'te mi yoksa FE 2.2 mount'unda mı? Önerim: **bu endpoint'te aynı transaction**. Bağlı endpoint tek seferde tutarlı state bırakır.

5. **Stage C deferred açıkça mı yazılsın?** Response'a `"cluster_status": "pending"` eklenip FE'ye sinyal verilsin mi (Stage C henüz başlamadı, "Hazırlanıyor..." göstermesin)? Önerim: **evet**, response shape `{anchor_paper_id, locked_at, cluster_status: "pending"}`.

---

## §9 — 7-kontrol (DM_RULES R2)

1. **Literatür:** REST anchor-set pattern'i (PUT vs POST) — POST seçtik çünkü "kilit" durum değişimi. Idempotency yok bilinçli.
2. **Halüsinasyon:** Tüm path/satır referansları §3 tabloda doğrulandı.
3. **Fayda-maliyet:** ~110 LOC kod + ~150 LOC test → 11 sayfa açılır (2.2 Konu Belirleme, 2.5 Kavram Ağı, atölye papers hydration). Net pozitif.
4. **Daha kolayı:** Sadece `anchor_paper_id` UPDATE etmek, candidates_meta verification atlamak — ama o zaman manipülasyon kapısı açık. Verification ucuz (~5 LOC).
5. **Son kullanıcı:** FE "ÇAPA SEÇ" butonu çalışır hale gelir. Şu an deadlock.
6. **Rakip:** SciSpace anchor lock yok, Consensus tek-soru, Elicit literatür özet. PaperMind'ın "çapa = uzun süreli proje state" canonu rakipsiz (2.1 RTF §17-19).
7. **Lokal vs global:** Global — service + Pydantic + route pattern'i `research_area_reset`'in birebir kopyası. Hack yok.

---

## §10 — Risk

- **R1:** `anchor_finder.py` candidates_meta'ya yazmıyor olabilir (§8.1). Mitigasyon: plan onayı öncesi `Read api/services/anchor_finder.py`.
- **R2:** F9 §98 `202+job_id` spec'ten saptık. Mitigasyon: §2 DEFERRED'da açıkça yazılı; FE V1-S15 P002'de `200 senkron` bekleyecek.
- **R3:** `current_stage` update'i side-effect; ayrı endpoint olabilir. Mitigasyon: §8.4 soruda Omer kararı.
- **R4:** `cluster_status='pending'` çıktısı FE'yi yanıltabilir (Stage C başlıyor gibi). Mitigasyon: §8.5 response field açık.

---

## §11 — Uyum sinyali checklist (executor için)

Plan onaylandıktan sonra kod yazan asistan **doğrulamadan başlamasın**:

- [ ] CLAUDE.md §0 okundu (plan-first canon)
- [ ] Bu plan'ın tarihi 2026-05-13 mü (revize yoksa)
- [ ] `api/services/research_area_reset.py` pattern referans alındı
- [ ] `api/models/research_area.py` extra=forbid kullanılıyor
- [ ] K-031 manuel .eq("user_id", uid) zırhı uygulanıyor
- [ ] Test dosyası `api/tests/services/test_anchor_lock.py` + `api/tests/routes/test_research_area_lock.py`

Aksi halde **STOP**, plan revize.
