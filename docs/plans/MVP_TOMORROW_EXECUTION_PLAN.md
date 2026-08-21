# MVP Yürütme Planı — 2026-05-14 (Yarınki Çalışma)

> **Tarih:** 2026-05-13 gece yazıldı · **Yürütme:** 2026-05-14 sabah başlar
> **Master plan:** `MVP_LIVE_TEST_PLAN_2026-05-14.md` (commit `06c000d`)
> **Bu dosya:** Her commit için tam dosya yolu + signature + commit mesajı + test isimleri. Agent veya Claude tek başına yürütebilsin diye yazıldı.

---

## §0 — Otonom çalışma yetkisi (Omer 2026-05-13 talebi)

> Omer: "yarın hepsini yapacağız. sen agent ile kod kısmını yapabilir misin? benden izin istemeden"

**Otonom YAPABİLECEKLERIM** (mikro-onay yok):
- `Edit`, `Write`, yeni dosya oluştur, mevcut dosya değiştir
- `Bash` (test çalıştır, build, lokal git commit, branch oluştur)
- Pytest + Vitest + tsc + next build
- `git commit` (lokal — push YOK)
- `git add` belirli dosyalar (`git add -A` yasak — secret leak riski)

**Otonom YAPMAYACAKLARIM** (Omer'i bekler):
- `git push origin` — uzaktaki branch'i değiştirmek visible action
- `git push --force`, `git reset --hard`, `git branch -D` — destructive
- Production env yazma (Render/Vercel dashboard)
- `pip install` veya `npm install` — yeni paket gelirse plan revize
- Migration apply (`psql -f`) — Supabase prod'a yazma
- `rm -rf`, dosya silme (kütüphane temizlik dışında)

**Otonom yetki SCOPE:**
- Sadece `/Users/omer/papermind-app` altında
- Sadece bu plan'da listelenen commit'ler (P001-P0NN numaralı)
- Plan dışı kod yazma yasak — gerekirse STOP + plan revize raporu

**Karar default'ları (Omer ters bulursa revert):**
- V1-S15.pre §8 5 sorusu → §A1 başında default'larım encode edildi
- B1 keyword kaynağı → `fact_paper_id_card.keywords` jsonb (bugün doğrulandı)
- B3 pilot allowlist → mevcut `waitlist` tablosuna `status='invited'` ekleme (yeni tablo değil)

---

## §1 — Yürütme sırası (Gün 1-2-3)

### Gün 1 sabah (2-3h)
1. **§A1** anchor lock endpoint (3 commit)
2. **§A2** ResearchAreaConfirm parsed_understanding wiring (1 commit)
3. **§A3** ResearchAreaConfirm ÇAPA SEÇ button (1 commit)

### Gün 1 öğle (1-2h)
4. Yerel smoke: `/project/{id}/discovery-1` golden path manuel (browser)
5. **§B2** ReferenceStyle FE wiring (2 commit)

### Gün 2 sabah (3-4h)
6. **§B1** ConceptNetwork endpoint + FE (4 commit)
7. **§B3** Pilot allowlist (2 commit)
8. Yerel full uçtan-uca smoke (10 sayfa)

### Gün 3 (Omer manuel)
9. `git push` (Omer)
10. Render + Vercel deploy (Omer)
11. Pilot smoke + 2-3 davet (Omer)

---

## §A1 — Anchor Lock Endpoint (3 commit, ~110 LOC)

**Plan referans:** `docs/plans/V1_S15_pre_anchor_lock.md`

### Default kararlar (Omer §3'te tersini söylerse revert)
- (1) İki kere lock → **409 already_locked**
- (2) Aday listede yok → **SKIP**; anchor_finder candidates_meta'ya yazmıyor (kanıt: `anchor_finder.py` grep `candidates_meta` boş). Security gap kabul; F9 P096'da kapanır.
- (3) `projects.current_stage = 'topic_selection'` aynı endpoint'te UPDATE (atomic)
- (4) Response'a `cluster_status: 'pending'` eklenir
- (5) **200 senkron**, 202 değil (Stage C cluster_expander yok)

### Commit P001 — Pydantic modelleri

**Dosya:** `api/models/research_area.py` (mevcut, +25 LOC sonuna)

```python
class LockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str = Field(min_length=1, max_length=64)

    @field_validator("paper_id")
    @classmethod
    def _strip_paper_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("paper_id boş olamaz")
        return s


class LockResponse(BaseModel):
    """V1-S15.pre — anchor lock 200 dönüşü.

    cluster_status='pending' Stage C henüz başlamadı sinyali (F9 P096 deferred).
    """
    model_config = ConfigDict(extra="forbid")
    anchor_paper_id: str = Field(min_length=1)
    locked_at: str = Field(min_length=1)  # ISO 8601
    cluster_status: Literal["pending", "expanding", "ready", "failed"] = "pending"
```

**Test:** `api/tests/models/test_research_area_lock.py` (yeni)
- `test_lock_request_empty_paper_id_422` — boş string ValidationError
- `test_lock_request_oversize_paper_id_422` — 65 char ValidationError
- `test_lock_response_extra_forbid` — extra alan ValidationError
- `test_lock_response_cluster_status_default_pending`

**Commit mesajı:**
```
feat(api): V1-S15.pre-P001 — LockRequest/LockResponse Pydantic

POST /research-area/anchor/lock için extra=forbid model'leri:
- LockRequest.paper_id min/max + strip validator
- LockResponse {anchor_paper_id, locked_at, cluster_status='pending'}

cluster_status='pending' Stage C cluster_expander (F9 P096) hazır
değil sinyali; FE "Hazırlanıyor..." göstermesin.
```

### Commit P002 — anchor_lock servisi

**Dosya:** `api/services/anchor_lock.py` (yeni, ~80 LOC)

Pattern: `api/services/research_area_reset.py` birebir referans.

```python
"""V1-S15.pre — POST /research-area/anchor/lock servisi.

Plan: docs/plans/V1_S15_pre_anchor_lock.md §5

Akış:
  1. _verify_ownership (K-031 manuel .eq("user_id"))
  2. _load_anchor_state — project_anchor satırı var mı, lock atılmış mı
  3. _lock_anchor — anchor_paper_id + locked_at + cluster_status='pending'
  4. _advance_project_stage — projects.current_stage = 'topic_selection'

Hatalar:
  - ProjectNotFoundError → 404
  - AnchorRowMissingError → 409 stage_b_incomplete (Stage B çağrılmadı)
  - AlreadyLockedError → 409
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, cast
from supabase import Client
from api.models.research_area import LockResponse


class ProjectNotFoundError(Exception): ...
class AnchorRowMissingError(Exception): ...
class AlreadyLockedError(Exception): ...


async def _verify_ownership(db: Client, project_id: str, user_id: str) -> None:
    # research_area_reset._verify_ownership pattern
    ...


async def _load_anchor_state(db, project_id) -> dict[str, Any]:
    """SELECT anchor_paper_id, locked_at FROM project_anchor WHERE project_id=$1"""
    ...


async def _lock_anchor(db, project_id, paper_id) -> str:
    """UPDATE + return locked_at ISO."""
    now = datetime.now(timezone.utc).isoformat()
    # project_anchor: anchor_paper_id, locked_at, cluster_status='pending'
    # Row may not exist (Stage B not called yet) — defensive: upsert with project_id PK
    ...
    return now


async def _advance_project_stage(db, project_id) -> None:
    """projects.current_stage = 'topic_selection' (2.2 Konu Belirleme sayfasına işaret)."""
    ...


async def run(*, db: Client, project_id: str, user_id: str, paper_id: str) -> LockResponse:
    await _verify_ownership(db, project_id, user_id)
    state = await _load_anchor_state(db, project_id)
    if state.get("anchor_paper_id") or state.get("locked_at"):
        raise AlreadyLockedError(...)
    locked_at = await _lock_anchor(db, project_id, paper_id)
    await _advance_project_stage(db, project_id)
    return LockResponse(anchor_paper_id=paper_id, locked_at=locked_at, cluster_status="pending")
```

**Test:** `api/tests/services/test_anchor_lock.py` (yeni)
- `test_anchor_lock_ownership_404` — başka user'ın projesi
- `test_anchor_lock_already_locked_409` — `anchor_paper_id` zaten dolu
- `test_anchor_lock_golden_path` — UPDATE + current_stage advance + LockResponse
- `test_anchor_lock_persists_iso_locked_at`
- Mock fixture: `_supabase_call_mock` lambda → fake row response

**Commit mesajı:**
```
feat(api): V1-S15.pre-P002 — anchor_lock servisi

Servis akışı: ownership zırh → state yükle → UPDATE
project_anchor.anchor_paper_id + locked_at + cluster_status='pending'
→ projects.current_stage = 'topic_selection' aynı flow.

K-031 manuel .eq("user_id") zırh + 3 hata sınıfı (ProjectNotFound /
AnchorRowMissing / AlreadyLocked). 4 unit test PASS.
```

### Commit P003 — route + integration

**Dosya:** `api/routes/research_area.py` (mevcut, +30 LOC)

```python
# Mevcut import'lara ekle
from api.models.research_area import LockRequest, LockResponse
from api.services import anchor_lock

@router.post(
    "/{project_id}/research-area/anchor/lock",
    response_model=LockResponse,
    status_code=status.HTTP_200_OK,
)
async def post_anchor_lock(
    project_id: str, req: LockRequest, request: Request
) -> LockResponse:
    """V1-S15.pre — çapa kilitle + current_stage ilerlet (atomic).

    409 already_locked: 2. lock denemesi (FE reset endpoint'ine yönlendir).
    """
    user_id = _user_id(request)
    db = _supabase()
    if db is None:
        raise HTTPException(status_code=503, detail="supabase_unavailable")
    try:
        return await anchor_lock.run(
            db=db, project_id=project_id, user_id=user_id, paper_id=req.paper_id
        )
    except anchor_lock.ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="project_not_found") from None
    except anchor_lock.AlreadyLockedError as exc:
        raise HTTPException(status_code=409, detail=f"already_locked: {exc}") from exc
```

**Test:** `api/tests/routes/test_research_area_lock.py` (yeni)
- `test_route_200_locks_anchor`
- `test_route_401_missing_user`
- `test_route_404_not_owner`
- `test_route_409_already_locked`
- `test_route_422_empty_paper_id`
- `test_route_503_supabase_unavailable`

**Commit mesajı:**
```
feat(api): V1-S15.pre-P003 — POST /research-area/anchor/lock route

Route: POST /{project_id}/research-area/anchor/lock body {paper_id}
→ 200 LockResponse. Hata mapping: 401/404/409 already_locked/422/503.

Stage A (messages) + Stage B (anchor-candidates) + Stage B-lock (bu)
+ Stage A-reset zinciri kapandı. Stage C (cluster_expander) F9 P096
deferred.
```

### A1 closure kapısı
- `cd /Users/omer/papermind-app && uv run pytest api/tests/services/test_anchor_lock.py api/tests/routes/test_research_area_lock.py -v` EXIT 0
- `uv run mypy --strict api/services/anchor_lock.py api/routes/research_area.py` clean

---

## §A2 — ResearchAreaConfirmPage parsed_understanding wiring (1 commit, ~80 LOC)

**Sorun:** `ResearchAreaConfirmPage.tsx:58` hardcoded `const PARSED = {...}` — 270-296 satırlar `PARSED.focuses`, `PARSED.field`, `PARSED.subfield`, `PARSED.interdisciplinary` kullanıyor.

**Hedef:** Gerçek `parsed_understanding` `/project/{id}/research-area/messages` son adviser turn'undan veya yeni `GET /project/{id}/research-area/state` endpoint'inden gelsin.

**Karar:** Yeni `GET` endpoint EKLEME — bunun yerine `GET /api/project/{id}` zaten döndüğü için (`anchor?` field, project.py:321-353) oraya `parsed_understanding` ek field koy.

### Commit P004 — Backend: GET /project/{id} response'a parsed_understanding ekle

**Dosya:** `api/routes/project.py` + `api/services/project_read.py` (varsa)

Akış: 
1. GET handler'da son `project_chat_messages` row'unu (`role='adviser'`, max attempt+turn) `select("parsed_understanding")` ile çek.
2. ProjectReadResponse'a `parsed_understanding: ParsedUnderstanding | None` ekle (mevcut Pydantic `extra="forbid"` ise alanı modele ekle).
3. Test: `test_get_project_returns_parsed_understanding`.

**Commit mesajı:**
```
feat(api): V1-S16-P001 — GET /project/{id} response.parsed_understanding

Son adviser turn'unun parsed_understanding'i (focuses + field + subfield
+ interdisc + confidence) project read response'una eklendi.

FE ResearchAreaConfirmPage hardcoded PARSED fixture'ı yerine bu veri
gösterilecek (V1-S16-P002).
```

### Commit P005 — FE: PARSED → gerçek parsed_understanding

**Dosya:** `web/src/components/project/ResearchAreaConfirmPage.tsx`

Değişiklikler:
- `const PARSED = {...}` SİL (satır 58-70)
- `useQuery` `/api/project/{id}` response'unda `parsed_understanding` field'ını al
- Type: `Project & { parsed_understanding: ParsedUnderstanding | null }`
- `PARSED.focuses` → `data.parsed_understanding?.focuses ?? []`
- `PARSED.field`/`subfield`/`interdisciplinary`/`adviserText` → karşılıkları
- `null` durumda: "Henüz analiz yok — geri dön ve Kütüphaneci ile sohbet et" hint
- Vitest: `ResearchAreaConfirmPage.test.tsx` (varsa update, yoksa skip)

**Commit mesajı:**
```
feat(web): V1-S16-P002 — ResearchAreaConfirmPage PARSED fixture sil

ResearchAreaConfirmPage.tsx:58 hardcoded PARSED → gerçek
parsed_understanding (GET /api/project/{id} response.parsed_understanding,
V1-S16-P001).

null durumda "Sohbete dön" hint. Hardcoded fixture (focuses, field,
subfield, interdisc) tamamen kaldırıldı.
```

---

## §A3 — ResearchAreaConfirmPage "ÇAPA SEÇ" button (1 commit, ~50 LOC)

**Hedef:** Sayfada 3 anchor candidate kartı altında "ÇAPA SEÇ" butonu → POST `/research-area/anchor/lock {paper_id}` → 200 + redirect `/project/{id}/discovery-2`.

### Commit P006 — FE: ÇAPA SEÇ button + lock mutation

**Dosya:** `web/src/components/project/ResearchAreaConfirmPage.tsx`

Eklemeler:
- `useMutation` lock POST: `apiFetch('/api/project/{id}/research-area/anchor/lock', { method: 'POST', body: { paper_id }})`
- Her candidate card'a "ÇAPA SEÇ" buton (kart sağ alt veya altına amber CTA)
- Click handler: confirm dialog → mutation → success → `router.push('/project/{id}/discovery-2')`
- 409 already_locked → toast "Çapa zaten kilitli. Reset?" + reset endpoint çağrısı için secondary button

**Commit mesajı:**
```
feat(web): V1-S16-P003 — ResearchAreaConfirmPage ÇAPA SEÇ → /anchor/lock

3 anchor candidate kartına "ÇAPA SEÇ" amber CTA. Mutation: POST
/research-area/anchor/lock → 200 → router.push(/discovery-2).

409 already_locked: toast + reset endpoint açma. F9 §4 senaryo madde
8-9 akışı kapandı (Stage B → Stage Lock → 2.2 Konu Belirleme).
```

### A2+A3 closure kapısı
- `cd web && npm run build` EXIT 0
- `npx vitest run` EXIT 0
- Manuel smoke: dev'de Stage A sohbet → 3 odak → confirm → 3 candidate → ÇAPA SEÇ → discovery-2 açıldı mı?

---

## §B1 — ConceptNetwork endpoint + FE (4 commit, ~280 LOC)

**Hedef:** `/project/{id}/discovery-2` (yanlış, doğrusu 2.5 → `/discovery-5` veya benzer) ConceptNetworkPage hardcoded NODES/EDGES yerine canlı subgraph.

### Plan revize gerekli (yarın sabah ilk iş)
Mevcut `docs/plans/V1_S15_concept_network_wiring.md` yanlış mimari (single T-code anchor). Doğru mimari (2.5 RTF):
- Anchor paper'ın top-10 keyword'ü → `fact_paper_id_card.keywords` jsonb (kanıt: `0022_extended_affinity.sql:82`)
- Her keyword için `dim_term_community` lookup → T-code + community_id
- T-code'lar için `fact_term_arm_static` (term_a, term_b, lift) + `fact_term_arm_temporal` (delta_lift) edge sorgusu
- 4-color modulo community renkleri
- Δlift > threshold → trending marker

### Commit P007 — Plan revize

**Dosya:** `docs/plans/V1_S15_concept_network_wiring.md` (mevcut, revize)

Eski "single T-code anchor" mimariyi sil, yerine "anchor paper top-10 keyword composite subgraph" yaz. Açık soru: anchor paper keyword listesi 10'dan az ise (ör. eski paper) nasıl davranır? Default: olduğu kadarı kullan.

### Commit P008 — Backend endpoint

**Dosya:** `api/routes/workshop.py` veya yeni `api/routes/concept_network.py`

```
GET /api/project/{project_id}/concept-network
Response 200:
{
  "nodes": [{id, keyword, t_code, community_id, color}],
  "edges": [{source_t, target_t, lift_static, delta_lift, trending}],
  "anchor_paper_id": "...",
  "anchor_keywords": [...]  # 10 keyword
}
```

Servis: `api/services/concept_network.py`
1. project_anchor → anchor_paper_id (yoksa 409)
2. fact_paper_id_card.keywords[anchor_paper_id] → top-10 keyword
3. dim_term_community lookup (term ↔ keyword join) — açık nokta: keyword'ler `dim_term_community.term` ile birebir mi eşleşiyor? (yarın doğrula)
4. fact_term_arm_static SELECT WHERE term_a IN (...) OR term_b IN (...)
5. fact_term_arm_temporal LEFT JOIN delta_lift
6. Subgraph DTO

**Test:** unit servis + integration route, 5-6 test.

**Commit mesajı:**
```
feat(api): V1-S15-P008 — GET /api/project/{id}/concept-network

Anchor paper top-10 keyword → dim_term_community lookup →
fact_term_arm_static (lift) + fact_term_arm_temporal (delta_lift)
subgraph. Response: nodes + edges + community color (4-modulo).

409 anchor_not_locked: project_anchor.anchor_paper_id null. Stage Lock
(V1-S15.pre) çalıştırılmamış demek.
```

### Commit P009 — Pydantic model'leri

**Dosya:** `api/models/concept_network.py` (yeni)

ConceptNode, ConceptEdge, ConceptNetworkResponse.

### Commit P010 — FE wiring

**Dosya:** `web/src/components/project/ConceptNetworkPage.tsx`

- `const NODES = [...]` ve `const EDGES = [...]` SİL (satır 29-83)
- `useQuery` GET `/api/project/{id}/concept-network`
- Loading skeleton + 409 anchor_not_locked durumunda "Önce çapa seç" CTA → router.push(2.1)
- React Flow veya benzeri graph lib? Önce: mevcut visualization library'yi grep'le, varsa kullan, yoksa basit SVG ile başla.

**Commit mesajı:**
```
feat(web): V1-S15-P010 — ConceptNetworkPage canlı subgraph

NODES/EDGES hardcoded fixture silindi → GET /api/project/{id}/
concept-network. Anchor paper top-10 keyword community graph.

409 anchor_not_locked → "Önce çapa seç" CTA. Δlift > 0.3 trending
marker (Spec 2.5 §V1 dokunuş 2).
```

### B1 closure kapısı
- Backend: pytest 6 test PASS
- FE: vitest + npm run build EXIT 0
- Manuel smoke: anchor lock'lu bir projede sayfaya gidip canlı graph görmek

### B1 risk
Eğer keyword ↔ dim_term_community.term mapping birebir değilse (örn. keyword "MCDM" ama term "T10050"), bir bridge tablosu lazım. Yarın bu doğrulanacak (`SELECT keyword FROM fact_paper_id_card LIMIT 5` örnek + `dim_term_community.term` örnek karşılaştır). Mapping yoksa: B1 P2'ye ertelenir, B2 + B3 ile MVP açılır.

---

## §B2 — ReferenceStylePage FE wiring (2 commit, ~120 LOC)

**Sorun:** `ReferenceStylePage.tsx` 10 hardcoded reference + 4 style (APA/MLA/Vancouver/IEEE) tutuyor. Backend `/api/workshop/citation-format` P074-077 hazır (F13 commit `a36b9da` "CitationQualityPage → 4 citation endpoint binding").

### Commit P011 — Endpoint inceleme + Pydantic doğrula

**Dosya:** sadece `Read` — `api/routes/workshop.py` veya nereye P074-077 yazıldıysa.

Eğer `/api/workshop/citation-format` style param alıyorsa (apa/mla/vancouver/ieee) ve project_papers listesi döndürüyorsa → direkt kullan.

### Commit P012 — FE wiring

**Dosya:** `web/src/components/project/ReferenceStylePage.tsx`

- Hardcoded 10 reference SİL
- `useQuery` GET project_papers + selected style param
- 4 style dropdown — switching style yeniden mutation
- Loading + empty state

**Commit mesajı:**
```
feat(web): V1-S17-P012 — ReferenceStylePage canlı project_papers

Hardcoded 10 reference fixture silindi → GET /api/workshop/citation-
format?style={apa,mla,vancouver,ieee}. project_papers listesi gerçek.

Stil değişiminde re-fetch. Empty state: "Henüz makale eklenmedi".
```

### B2 closure kapısı
- vitest + build EXIT 0
- Manuel smoke: proje açıp ReferenceStylePage'i aç, 4 stil arasında geç, format değişiyor mu?

---

## §B3 — Pilot allowlist (2 commit, ~150 LOC)

**Hedef:** Sadece davet edilen kullanıcılar giriş yapabilsin. Mevcut: `waitlist` tablosu (0017).

### Commit P013 — Migration: waitlist.status ENUM

**Dosya:** `db/migrations/0034_waitlist_invite_status.sql` (yeni)

```sql
ALTER TABLE public.waitlist
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending'
  CHECK (status IN ('pending', 'invited', 'active', 'declined'));

CREATE INDEX IF NOT EXISTS idx_waitlist_status ON public.waitlist(status);
```

Apply lokal değil — Supabase Dashboard'a Omer paste edecek (manuel ops).

### Commit P014 — Auth middleware allowlist kontrol

**Dosya:** `api/middleware/auth.py` (mevcut, +20 LOC)

JWT verify sonrası: `SELECT status FROM waitlist WHERE email = $auth_email` → `status != 'invited' AND status != 'active'` → 403 not_invited.

**Bypass:** `WAITLIST_BYPASS=true` env (dev için). Production'da unset.

**Test:**
- `test_auth_403_not_invited`
- `test_auth_200_invited`
- `test_auth_200_active`

**Commit mesajı:**
```
feat(api): V1-S18-P014 — Auth allowlist (waitlist.status gate)

Auth middleware: JWT verify sonrası waitlist.status ∈ {invited,active}
şartı. Aksi 403 not_invited.

WAITLIST_BYPASS=true env dev/CI için. Production unset.

Migration 0034 manuel apply (Omer).
```

### B3 closure kapısı
- pytest 3 test PASS
- Omer: Supabase Dashboard'da 0034 apply + kendi e-mail'i `status='invited'` UPDATE

---

## §2 — Toplam tahmin

| Sprint | Commit | LOC | Süre |
|---|---|---|---|
| A1 anchor lock | P001-P003 | 110 | 1h |
| A2+A3 confirm wiring | P004-P006 | 130 | 1h |
| B1 concept network | P007-P010 | 280 | 3h |
| B2 reference style | P011-P012 | 120 | 1h |
| B3 pilot allowlist | P013-P014 | 150 | 1h |
| **TOPLAM** | **14 commit** | **~790 LOC** | **~7h** |

Hata payı %30 → 9h. Bir günde biter. Gün 2 buffer + manuel smoke.

---

## §3 — Otonom çalışma execution log

Her commit sonrası bu dosyaya satır eklenir (Append-only execution log):

```
[2026-05-14 HH:MM] P001 anchor_lock Pydantic — commit abc1234 — pytest 4 PASS
[2026-05-14 HH:MM] P002 ...
```

Hata olursa: commit YAPILMAZ, log'a `FAIL: <hata>` satırı, sonraki commit'e geçilmez, STOP + Omer'i bekler.

---

## §4 — STOP koşulları (autonom çalışmayı kes)

- Her test fail
- `mypy --strict` veya `ruff` fail
- `npm run build` fail (Next.js)
- Plan dışı dosya edit gereksinimi
- §A1 default'larından sapma talebi
- B1 keyword ↔ term mapping doğrulanamadı (yarın `SELECT` ile test edilecek)
- Yeni paket install gerekir (`npm install x` veya `uv add x`)

Bu durumlarda: log'a `STOP: <neden>` yaz, Omer'i bekle.

---

## §5 — Plan onay etiketi

Omer onaylamak için bu satırın altına yazsın:

```
[ ] PLAN ONAYLANDI — Omer, 2026-05-XX HH:MM
```

Bu etiket olmadan otonom run **başlamaz**. CLAUDE.md §0 mutlak.
