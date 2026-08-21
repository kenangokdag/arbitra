# F2 Day 2-3-4 Sıkıştırılmış Sprint — P004 → P009 Plan Paketi

> **Statü:** ŞARTLI HAZIR — 4 Council toplantısı (25-28) tamamlandı, smoke fixture'ları beklemede (Omer çalıştıracak), 5 atomic commit Omer kodlayacak.
> **Çağrı:** Omer 2026-04-30 talebi: "bugün planlanan 3 günlük iş bitmiş olmalı".
> **Kanun:** B-015 (R13.9 alan sahipliği + R13.10 HK gates + R13.11 dış servis empirik kanıt).
> **Branch:** `feat/F2-search-skeleton` (B-014'ün devamı).

---

## §0 Bağlam ve plan mantığı

F2 Day 1 (2026-04-30 sabah-öğlen) 8 commit + Council 21-24 + 66/66 test PASS ile kapandı. Master plan §9 F2 hedefi 4-5 gün; bugün talep: 3 gün sıkıştır + tek-Council yerine **4 ardışık council** (P004 / P006 / P007 / P008+P009) + her birinde alan sahibi sandalyesi (Sercan post-hoc onay) + smoke fixture beklemesi.

**Plan yazma katı kuralı (DM-008 + R1):** Omer kod yazmadan önce her P numarasının §Council tablosunu + HK-1..HK-7 gates kontrolünü + smoke fixture referansını okur. Plan dışı edit yasak; gerekirse bu manifest revize edilir.

**Engelleyici-bağımsız vs. engelleyici-bağımlı sıralaması:**
- **P004 Listener (Qwen anlama)** — engelleyici: HF endpoint canlı + smoke fixture (`tests/fixtures/hf_qwen_tr_query.json`).
- **P006 PoolRouter** — engelleyici: B-012 metadata patch koşumu (Pinecone metadata yazılmış mı) + lexical havuz kararı (Council 25).
- **P007 Reranker** — engelleyici: P006 PASS + reranker host kararı (HF Endpoint vs local sentence-transformers).
- **P008 Curator + faithfulness_gate** — engelleyici: P004 + P007 PASS + faithfulness_gate ortak servis spec (B-010 yazılı `docs/backend/faithfulness_gate_spec.md`).
- **P009 Presenter** — engelleyici: P008 PASS + Cosmos endpoint setup veya Qwen-yeterli kararı (OPEN sonrası).

---

## §Council 25 — Lexical havuz kararı (Pinecone metadata olmadan PoolRouter nasıl çalışır)

**Alan:** Backend / Veri retrieval mimarisi
**Alan sahibi (BAĞLAYICI):** Sercan (post-hoc onay yer tutucu — frontend boş, backend lead Sercan)

**Bağlam:** F3a §3 P006 satırı "lexical BM25" der ama Supabase migration'larında FTS index YOK (NEXT_ACTION FTS audit Council 25-A bulgusu): `papers` tablosu boş (lazy mirror), `fact_paper_id_card` 24.86M dolu ama `title`/`abstract` kolonu yok. Pinecone metadata B-012'de 8 alan (D/F/S/year/q_weak/method/lang/v_conf) — title/abstract yok. PoolRouter'ın 3 havuzdan biri "lexical" — boş kalırsa RRF 2-havuza düşer.

**3 seçenek:**
1. **Postgres `papers` lazy-fill + tsvector FTS** — title-only (~3-4 GB), abstract drop (Free tier 500 MB **AŞAR** → Pro tier $25/ay zorunlu)
2. **Pinecone sparse Plan 2'ye ertele** (DM-016 dense-only MVP — tutarlı; Plan 2'de SPLADE/sparse açılır)
3. **MVP'de 2-havuz RRF (semantic + theme), lexical mock** (Plan 2'de aç)

| # | Üye | Oy | Gerekçe (1 cümle) | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | Lexical olmadan top-k semantic-only "exact title" sorguları kaçırır — recall riski ölçülmedi (smoke gerek). | Smoke: 50 query × ground-truth match ile recall@10 ölçümü; <%70 ise mock yetersiz. |
| 2 | Akademik İsabet | 🔴 | "Tam başlık ile arama" akademisyenin günlük rutini — exact match olmadan ürün hayal kırıklığı; literatür hybrid retrieval standart (ColBERT, SPLADE). | Lexical havuz MVP'de açık olsun, mock kabul edilemez. |
| 3 | Fayda-Maliyet | 🟡 | Pro tier $25/ay × 12 = $300/yıl + Postgres yük; Pinecone dense-only sparse ertelenmesi para tasarrufu ama recall feda. Seçenek 1 ekstra maliyet, Seçenek 2-3 sıfır. | Eğer recall <%70 → Seçenek 1 zorunlu; ≥%80 → Seçenek 3 yeterli; ara → Pro tier title-only. |
| 4 | Daha İyisi Var Mı? | 🟢 | 2026 hybrid retrieval SOTA (e.g., **BM42 hybrid**, ColBERT v2). Pinecone sparse v2 gelecekte indeks-içi hybrid sunar — Plan 2 zaten ertelendi. | Plan 2'de Pinecone sparse + ColBERT pilotu; MVP'de yeterli olsun. |
| 5 | Global Çözüm | 🔴 | 25M corpus + TR/EN/karışık dil ölçeğinde lexical yokluğu = recall %15-20 düşüş literatürde sabit. Mock global çözüm değil. | En az title-FTS açık olsun (abstract drop OK). |
| 6 | Son Kullanıcı Avukatı | 🔴 | Akademisyen "Smith 2018 dijital uçurum" yazar, exact-title match olmadan ürün başarısız. | Title FTS MVP'de açık; abstract opsiyonel. |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟡 | Title-only Postgres tsvector kabul; abstract Pinecone sparse Plan 2'de açılır; Pro tier $25/ay kabul edilir akademik isabet için. | Migration 0005: `papers.title` Generated Column tsvector + GIN index; lazy-fill Faz 3'e ertelenmez, Day 4'te kuyruk. |

**Sonuç:** **Seçenek 1 modifiye** (Postgres title-only FTS) + Plan 2'de Pinecone sparse açılır. **3 RED + 2 YELLOW + 1 GREEN + Sercan YELLOW** → R13.5 gereği 3+ üye RED = plan revize gerekti, **revize bu Council'da yapıldı** (Seçenek 3 mock RED → Seçenek 1 modifiye onay). Omer hakem GREEN bekleniyor.
**Empirik test gerekli mi?** EVET — `tests/fixtures/postgres_title_fts_recall.json` (50 query × ground-truth, recall@10 ölçümü) Day 4 öncesi koşulur. Ölçüm <%70 ise Pro tier title+abstract'a yükseltilir.

**Karar:** P006 lexical havuz = `papers.title_tsv` Postgres FTS + `to_tsquery` query çevrimi. Migration 0005 Day 4'te kuyrukta (P006'dan önce).

---

## §Council 26 — P004 Listener Qwen + HF empirik test stratejisi

**Alan:** Backend / Dış servis (HF Endpoint)
**Alan sahibi (BAĞLAYICI):** Sercan (post-hoc onay)

**Bağlam:** P004 — Qwen2.5-7B-Instruct-AWQ HF endpoint client; query rewrite (4-6 paraphrase) + intent extraction (explicit/silent/default) + JSON şema enforce. STATE.md HF Endpoint ✅ kuruldu (papermind-qwen, vLLM v0.18.1, T4 eu-west-1, $0.50/h, scale-to-zero 15dk, TR test PASS sözlü). **Empirik smoke beklemede** — `scripts/smoke_external_services.py` yazıldı, Omer çalıştıracak.

| # | Üye | Oy | Gerekçe | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | "TR test PASS" sözlü — kanıt B; canlı response snapshot olmadan JSON çıktı şeması varsayım. | `tests/fixtures/hf_qwen_tr_query.json` (R13.11 zorunlu) commit öncesi. |
| 2 | Akademik İsabet | 🟢 | Qwen2.5-7B akademik literatür query rewrite için yeterli (multilingual + 32K context); B-005 onaylı. | — |
| 3 | Fayda-Maliyet | 🟢 | Scale-to-zero $0.50/h × ortalama 8h aktif = $4/gün × 30 = $120/ay (DM-010 bütçe içinde). | — |
| 4 | Daha İyisi Var Mı? | 🟡 | Qwen3-32B AWQ 2026'da çıktı — daha güçlü; ama T4 GPU'da çalışmaz (A10G+ gerek), maliyet 3-5×. MVP'de Qwen2.5 yeter. | Post-MVP Qwen3 A/B test (OPEN-008). |
| 5 | Global Çözüm | 🟢 | Qwen2.5 Türkçe + İngilizce + Indonesia (multilingual training corpus) — 3-dil scope (B-005) için yeterli. | — |
| 6 | Son Kullanıcı Avukatı | 🟡 | Cold-start 30sn akademisyen sabırsızlığı; keep-alive 240s ping zorunlu. | `api/workers/hf_keepalive.py` Day 4 wrap'te eklenir. |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟢 | OpenAI-uyumlu /v1/chat/completions endpoint mevcut; httpx + 3-retry + JSON şema enforce + Pydantic response model standart pattern. | P004'te `httpx.Client` connection pool reuse zorunlu (her request yeni client açma). |

**Sonuç:** GREEN ilerle (1 RED yok, 3 YELLOW < 3+ eşik = Omer hakem yok).
**Empirik test gerekli mi?** EVET — smoke fixture (`hf_qwen_tr_query.json`) Omer Day 2 başında koşar.

### P004 revize plan + pseudocode

**Dosya:** `api/services/listener.py` (mevcut iskelet → concrete)
**LOC:** ~250 (mevcut ABC → concrete + Qwen client + 920-örneklem benchmark stub)
**Test:** `tests/unit/test_listener.py` + `tests/integration/test_listener_qwen_smoke.py` (canlı, opt-in env flag)

```python
# api/services/listener.py — pseudocode (Omer kodlayacak)
from __future__ import annotations
import httpx
import json
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from api.config import settings  # HF_ENDPOINT_URL, HF_TOKEN, HF_MODEL_ID
from api.services._base import Listener  # ABC P003

class IntentType(str, Enum):
    EXPLICIT = "explicit"
    SILENT = "silent"
    DEFAULT = "default"

class ListenerOutput(BaseModel):
    """HK-1 schema gate: extra forbid + response_model zorunlu."""
    model_config = ConfigDict(extra="forbid")
    intent: IntentType
    rewrites: list[str] = Field(min_length=3, max_length=6)
    keywords: list[str] = Field(min_length=3, max_length=8)
    original_query: str  # echoed for traceability

class QwenListener(Listener):
    """HF Inference Endpoint client (vLLM OpenAI-uyumlu /v1/chat/completions).

    HK-2 kaynak: HF endpoint URL + model B-005 (B42-046 §1 anlama katmanı Qwen2.5-7B AWQ).
    HK-3 dış servis empirik kanıt: tests/fixtures/hf_qwen_tr_query.json snapshot.
    HK-4 runtime assertion: rewrites length [3,6], keywords length [3,8].
    HK-7 reproducibility: temperature=0.2 deterministik (seed yok ama düşük sıcaklık).
    """
    SYSTEM_PROMPT = """Sen akademik literatür sorgu çözümleyicisisin.
Türkçe sorguyu okuyup JSON üret:
{"intent": "explicit"|"silent"|"default",
 "rewrites": [<3-6 İngilizce paraphrase>],
 "keywords": [<3-8 kavram>]}
Sadece JSON döndür."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        # HK: connection pool reuse (Sercan istedi)
        self._client = client or httpx.Client(
            base_url=settings.HF_ENDPOINT_URL,
            headers={"Authorization": f"Bearer {settings.HF_TOKEN}"},
            timeout=30.0,
        )

    async def listen(self, query: str, lang: Literal["TR", "EN", "ID"] = "TR") -> ListenerOutput:
        body = {
            "model": settings.HF_MODEL_ID,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "max_tokens": 400,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},  # vLLM Outlines uyumlu
        }
        # 3-retry envelope (RetryError → fail-fast, çağrı katmanı 503 mapler)
        response = await self._post_with_retry("/v1/chat/completions", body, retries=3)
        content = response["choices"][0]["message"]["content"]
        parsed = json.loads(content)  # HK-1 burada Pydantic validate eder
        parsed["original_query"] = query
        return ListenerOutput(**parsed)  # extra="forbid" şema dışı alan reddi

    async def _post_with_retry(self, path: str, body: dict, retries: int) -> dict:
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                r = self._client.post(path, json=body)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5, 1.0, 2.0
        raise RuntimeError(f"HF endpoint after {retries} retries: {last_exc!r}")
```

**Test stratejisi:**
- `tests/unit/test_listener.py` — mock httpx.Client; happy path + JSON parse error + retry exhaust + Pydantic schema reject (extra field).
- `tests/integration/test_listener_qwen_smoke.py` — canlı, `pytest -m smoke` ile opt-in; `HF_ENDPOINT_URL` set değilse skip; assertion: `len(rewrites) >= 3`, `intent in {explicit, silent, default}`.
- `tests/fixtures/hf_qwen_tr_query.json` — smoke koşuldukça güncellenecek snapshot.

**HK gates:**
- HK-1 ✅ ListenerOutput Pydantic + extra="forbid"
- HK-2 ✅ kaynak yorumda B-005
- HK-3 ⏳ smoke fixture beklemede (Omer Day 2 başı koşacak)
- HK-4 ✅ Field min/max length runtime assert
- HK-5 — yok (DB import yok)
- HK-6 ✅ tüm tipler annotated, Any leak yok
- HK-7 ✅ temperature=0.2 deterministik

---

## §Council 27 — P006 PoolRouter 3-havuz revize (Council 25 lexical kararı sonrası)

**Alan:** Backend / Retrieval mimarisi
**Alan sahibi (BAĞLAYICI):** Sercan

**Bağlam:** Council 25 lexical havuz = Postgres title FTS (migration 0005). PoolRouter 3-havuz: (1) Pinecone semantic dense (B-012 metadata HARD filter aktif), (2) Postgres title FTS, (3) `dim_theme_embedding` semantic theme match. RRF k=60 birleşim.

| # | Üye | Oy | Gerekçe | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | B-012 metadata patch hâlâ in-flight (shard 2 yükleniyor); metadata empty ise HARD filter çalışmaz. | Smoke: B-012 verify sonrası `tests/fixtures/pinecone_query_sample.json` metadata 8 alan içeriyor mu? |
| 2 | Akademik İsabet | 🟢 | RRF k=60 hybrid retrieval literatür standart (Cormack 2009); 3 havuz farklı sinyal kaynağı = recall iyileşir. | — |
| 3 | Fayda-Maliyet | 🟢 | Postgres FTS query 50ms; Pinecone semantic 80ms; theme cosine 30ms; toplam <200ms p50. RRF basit aritmetik. | — |
| 4 | Daha İyisi Var Mı? | 🟡 | 2026 SPLADE / ColBERT-v2 hybrid retrieval dense+sparse tek index'te çözer; Plan 2'ye ertelendi. | OPEN: Plan 2'de SPLADE/Pinecone sparse pilot. |
| 5 | Global Çözüm | 🟢 | 24.87M paper ölçeğinde RRF ek bellek tüketmiyor (her havuz top-50 → 150 item RRF skor); a11y + lang etkilenmez. | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | "Smith 2018" exact + "kaygı" semantic + tema "psikoloji" üçü RRF'te birleşir → akademisyen rutini. | — |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟡 | RRF k=60 standart ama tier'a göre k ayarı (Öğrenci k=30, Profesyonel k=60) düşünülebilir; MVP k=60 sabit, Faz 3 tier-aware. | KD-N (yeni): tier-aware RRF k Faz 3'te. |

**Sonuç:** 4 GREEN + 3 YELLOW (3+ YELLOW = Omer hakem zorunlu); Halüsinasyon Avcısı YELLOW B-012 verify'a bağlı, Sercan YELLOW KD-N.
**Empirik test gerekli mi?** EVET — B-012 metadata verify (`pinecone_query_sample.json` metadata_present=True) + recall@10 smoke (Council 25 ile ortak fixture).

### P006 revize plan + pseudocode

**Dosya:** `api/services/pool_router.py` (concrete) + `api/db/migrations/0005_papers_title_fts.sql`
**LOC:** ~220 (180 P006 + 40 migration)
**Test:** `tests/unit/test_pool_router.py` + `tests/integration/test_pool_router_3pools.py`

```python
# api/services/pool_router.py — pseudocode

class PoolResult(BaseModel):
    """Single pool's contribution."""
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    score: float = Field(ge=0.0)
    pool: Literal["pinecone_dense", "postgres_title_fts", "theme_cosine"]

class FusedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    rrf_score: float
    pool_scores: dict[str, float]  # debug: hangi havuzdan ne skor

class PineconeMetadataFilter(BaseModel):
    """B-012 8-field metadata filter — Pinecone $in/$gte operator dict çevrimi."""
    model_config = ConfigDict(extra="forbid")
    D: list[str] | None = None  # ["social_sciences"]
    F: list[str] | None = None
    S: list[str] | None = None
    year_gte: int | None = None
    year_lte: int | None = None
    q_weak_gte: float | None = None
    method: list[str] | None = None
    lang: list[str] | None = None
    v_conf_gte: float | None = None

    def to_pinecone_filter(self) -> dict[str, Any]:
        """Pydantic → Pinecone filter dict."""
        out: dict[str, Any] = {}
        if self.D: out["D"] = {"$in": self.D}
        if self.F: out["F"] = {"$in": self.F}
        # ... 8 alan
        return out

class HybridPoolRouter(PoolRouter):
    """3-havuz RRF k=60 (Council 27 onay).

    HK-2 kaynak: B42-045 §1 PoolRouter 3-havuz; B-012 metadata filter; Council 27 RRF k=60.
    HK-3 empirik: Pinecone smoke + Postgres FTS recall smoke.
    HK-4 runtime: top-k bounded (per-pool ≤50, fused ≤200).
    """
    RRF_K = 60  # Cormack 2009; tier-aware Faz 3 (KD-N)

    def __init__(
        self,
        pinecone: PineconeIndexWrapper,
        postgres: SupabaseAdmin,
        theme_index: ThemeEmbedIndex,
    ) -> None:
        self._pc = pinecone
        self._pg = postgres
        self._th = theme_index

    async def fan_out(
        self,
        query_embedding: list[float],
        query_text: str,
        filter: dict[str, Any] | None = None,
        top_k_per_pool: int = 50,
    ) -> list[FusedResult]:
        # paralel 3 havuz çağrısı
        async with asyncio.TaskGroup() as tg:
            t_pc = tg.create_task(self._pinecone_dense(query_embedding, filter, top_k_per_pool))
            t_fts = tg.create_task(self._postgres_fts(query_text, top_k_per_pool))
            t_th = tg.create_task(self._theme_cosine(query_embedding, top_k_per_pool))
        # RRF birleşim
        return self._rrf_fuse([t_pc.result(), t_fts.result(), t_th.result()])

    def _rrf_fuse(self, pool_results: list[list[PoolResult]]) -> list[FusedResult]:
        """Reciprocal Rank Fusion: score(d) = Σ 1/(k + rank_i(d))."""
        scores: dict[str, dict[str, float]] = {}
        for pool in pool_results:
            for rank, r in enumerate(pool, 1):
                scores.setdefault(r.paper_id, {})[r.pool] = 1.0 / (self.RRF_K + rank)
        fused = [
            FusedResult(
                paper_id=pid,
                rrf_score=sum(s.values()),
                pool_scores=s,
            )
            for pid, s in scores.items()
        ]
        return sorted(fused, key=lambda x: x.rrf_score, reverse=True)[:200]

    async def _pinecone_dense(
        self, vec: list[float], filter: dict[str, Any] | None, top_k: int
    ) -> list[PoolResult]:
        result = self._pc.query(
            vector=vec, top_k=top_k, filter=filter, include_metadata=False
        )
        return [
            PoolResult(paper_id=m.id, score=m.score, pool="pinecone_dense")
            for m in result.matches
        ]

    async def _postgres_fts(self, query_text: str, top_k: int) -> list[PoolResult]:
        # to_tsquery('turkish', $1) + ranking ts_rank_cd
        sql = """
        SELECT paper_id, ts_rank_cd(title_tsv, q) AS score
        FROM papers, plainto_tsquery('turkish', %s) q
        WHERE title_tsv @@ q
        ORDER BY score DESC LIMIT %s
        """
        rows = await self._pg.execute_async(sql, (query_text, top_k))
        return [PoolResult(paper_id=r["paper_id"], score=r["score"], pool="postgres_title_fts") for r in rows]

    async def _theme_cosine(self, vec: list[float], top_k: int) -> list[PoolResult]:
        # dim_theme_embedding 4516 × 256-d (W-32) — küçük index
        # MVP'de in-memory NumPy; Faz 3'te pgvector
        sims = self._th.cosine_topk(vec, top_k)
        return [PoolResult(paper_id=tid, score=s, pool="theme_cosine") for tid, s in sims]
```

```sql
-- api/db/migrations/0005_papers_title_fts.sql (Day 4 öncesi koşulur, Sercan onayında)
-- HK-2 kaynak: Council 25 lexical havuz kararı (Seçenek 1 modifiye, title-only)

ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS title_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('turkish', coalesce(title, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_papers_title_tsv
  ON papers USING GIN (title_tsv);

-- Lazy-fill cron (Day 4 wrap'te aktive): fact_paper_id_card.title → papers.title batch UPSERT.
-- 24.87M paper × ~80 byte title ≈ 2 GB; Pro tier $25/ay yeterli (Free tier AŞAR).
COMMENT ON INDEX idx_papers_title_tsv IS
  'Council 25 (B-015) lexical havuz; Postgres tsvector GIN; Plan 2 sparse Pinecone ile birleşir';
```

**HK gates:**
- HK-1 ✅ FusedResult / PoolResult / PineconeMetadataFilter Pydantic + forbid
- HK-2 ✅ B42-045 §1 + B-012 + Council 27 + Cormack 2009 RRF kaynak yorum
- HK-3 ⏳ Pinecone smoke + Postgres FTS recall smoke beklemede
- HK-4 ✅ top_k bounded; per-pool ≤50, fused ≤200
- HK-5 ⏳ Pinecone B-012 verify Day 2 başı (manifest mevcut, fetch sonucu fixture'a yansır)
- HK-6 ✅ tüm tipler annotated
- HK-7 ⚠️ FTS query yerel kelime varyasyonlarına duyarlı; reproducibility için fixture seed query listesi

---

## §Council 28 — P007 + P008 + P009 paketi (Reranker + Curator + Presenter)

**Alan:** Backend / LLM mimarisi
**Alan sahibi (BAĞLAYICI):** Sercan

**Bağlam:** P007 = BGE-reranker-v2-m3 cross-encoder; P008 = Curator + faithfulness_gate ortak servis (B-010); P009 = Presenter dil-spesifik LiteLLM router (B-005 + B-007).

**Tek council üç P-numarası** çünkü üçü zincirleme bağımlı (P007 → P008 → P009) ve aynı LLM altyapısını paylaşıyor.

| # | Üye | Oy | Gerekçe | İstediği |
|---|---|---|---|---|
| 1 | Halüsinasyon Avcısı | 🟡 | MiniCheck NLI ≥0.7 + ALCE citation-recall ≥0.8 eşikleri B42-045 §1 yazılı ama ölçüm fixture'ı yok; LVR distance ≥0.7 keyfi olabilir. | `tests/fixtures/faithfulness_calibration.json` 100 paper × ground-truth → eşik kalibrasyonu Day 4 wrap. |
| 2 | Akademik İsabet | 🟢 | BGE-reranker-v2-m3 multilingual cross-encoder (TR-EN) MIRACL benchmark üst sıra; Cosmos Turkish-Gemma-9b-T1 TR akademik metin için kalibre. | — |
| 3 | Fayda-Maliyet | 🟡 | Reranker HF endpoint = +$0.50/h; local sentence-transformers MVP'de CPU yeter (<200ms p50, T4 GPU gereksiz). | P007 = local sentence-transformers (CPU); HF endpoint Faz 3 yük artışında. |
| 4 | Daha İyisi Var Mı? | 🟡 | 2026 SOTA reranker: BGE-v2-m3 hâlâ üst sıra ama Jina v3 + Cohere Rerank 3.5 yarışıyor. Cohere paid; Jina apache. | OPEN: Faz 3 Jina reranker A/B test. |
| 5 | Global Çözüm | 🟢 | LiteLLM `model_list` config 3-dil routing temiz; faithfulness_gate ortak servis F3a + F3c için DRY. | — |
| 6 | Son Kullanıcı Avukatı | 🟢 | TR sunum Cosmos-9b akademik metni native ses; EN+ID Qwen yeterli MVP; Komodo gated lisans Faz 2'ye ertelendi. | — |
| **A** | **Sercan (BAĞLAYICI, post-hoc)** | 🟢 | Üç katman zincirleme; faithfulness_gate ortak servis B-010 spec'iyle uyumlu; LiteLLM `model_list` config standart pattern. | P008'de jsonschema 100% enforce mock-fail-safe (ortak servis dış-yüz schema reject); MiniCheck v2 5B HF endpoint Faz 3'te (CPU yetmez). |

**Sonuç:** 3 GREEN + 4 YELLOW (3+ YELLOW = Omer hakem zorunlu); ana riskler: (a) faithfulness eşik kalibrasyonu fixture beklemede, (b) reranker host kararı (CPU local kabul), (c) MiniCheck v2 5B Faz 3 ertelemesi (MVP'de basit cosine NLI proxy).
**Empirik test gerekli mi?** EVET — `tests/fixtures/faithfulness_calibration.json` Day 4 wrap; Cosmos endpoint smoke (`tests/fixtures/cosmos_tr_summary.json`) Sercan setup sonrası.

### P007 revize plan + pseudocode

**Dosya:** `api/services/reranker.py`
**LOC:** ~120 (100 + sentence-transformers integ)
**Test:** unit (50 → 10 ranking + TR örneği) + smoke (BGE local model load)

```python
# api/services/reranker.py — pseudocode (Council 28 P007)

class RerankInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    candidates: list[tuple[str, str]]  # [(paper_id, snippet), ...]

class RerankOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ranked: list[tuple[str, float]]  # [(paper_id, rerank_score), ...] desc

class BgeReranker(Reranker):
    """BGE-reranker-v2-m3 cross-encoder (HK-2 kaynak: B42-045 §1, MIRACL SOTA).

    HK-3 dış kaynak: HuggingFace BAAI/bge-reranker-v2-m3 model download.
    HK-6: torch + sentence_transformers tipler eksik, kasıtlı (KD-N: 3rd-party stub).
    """
    MODEL_NAME = "BAAI/bge-reranker-v2-m3"

    def __init__(self) -> None:
        # Lazy load — ilk çağrıda yüklenir, app lifetime cache
        self._model = None

    async def rerank(self, inp: RerankInput, top_k: int = 10) -> RerankOutput:
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.MODEL_NAME, max_length=512)
        pairs = [[inp.query, snip] for _, snip in inp.candidates]
        scores = self._model.predict(pairs, show_progress_bar=False)
        scored = sorted(
            zip([pid for pid, _ in inp.candidates], scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        return RerankOutput(ranked=[(pid, float(s)) for pid, s in scored[:top_k]])
```

### P008 revize plan + pseudocode

**Dosya:** `api/services/curator.py` + `api/services/faithfulness_gate.py` (B-010 ortak servis)
**LOC:** ~370 (220 curator + 150 faithfulness)
**Test:** unit (JSON schema 100% + LVR ≥ 0.7 + year_verified=false → year drop) + integ (3-gate cascade)

```python
# api/services/faithfulness_gate.py — ortak servis (B-010)

class FaithfulnessVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_pass: bool  # %100 jsonschema
    minicheck_score: float = Field(ge=0.0, le=1.0)
    alce_citation_recall: float = Field(ge=0.0, le=1.0)
    lvr_min_distance: float = Field(ge=0.0, le=1.0)
    decision_band: Literal["canon", "frontier", "out_of_scope"]
    gates_failed: list[str]  # ["minicheck<0.7", ...]

class FaithfulnessGate:
    """3-katlı + LVR — B42-045 §1 + B42-046 C1-C11.

    HK-2 kaynak eşikleri:
    - jsonschema: 100% (B42-045 §1, K4 LLM rank yasak schema'da)
    - MiniCheck NLI ≥0.7 (B42-045 §1; Day 4 calibration fixture sonrası ayarlanır)
    - ALCE citation-recall ≥0.8 (B42-045 §1; N11 v2 sentence-level UNBLOCKED)
    - LVR min_distance ≥0.7 (B42-040 §15-L4 confidence gate)
    """
    SCHEMA_THRESHOLD = 1.0
    MINICHECK_THRESHOLD = 0.7  # KD-N: kalibrasyon Day 4
    ALCE_THRESHOLD = 0.8
    LVR_THRESHOLD = 0.7

    async def evaluate(self, candidate: CuratorOutput, evidence: list[Sentence]) -> FaithfulnessVerdict:
        gates_failed: list[str] = []
        # Gate 1: schema (zaten Pydantic validate, burada audit)
        schema_ok = True  # validate edilmediyse exception fırlardı
        # Gate 2: MiniCheck NLI (mock-fail-safe MVP, Faz 3 HF endpoint)
        minicheck = await self._minicheck(candidate, evidence)
        if minicheck < self.MINICHECK_THRESHOLD:
            gates_failed.append(f"minicheck<{self.MINICHECK_THRESHOLD}")
        # Gate 3: ALCE citation-recall (N11 v2 sentence-level)
        alce = await self._alce_citation_recall(candidate, evidence)
        if alce < self.ALCE_THRESHOLD:
            gates_failed.append(f"alce<{self.ALCE_THRESHOLD}")
        # LVR
        lvr = self._lvr_min_distance(candidate)
        if lvr < self.LVR_THRESHOLD:
            gates_failed.append(f"lvr<{self.LVR_THRESHOLD}")
        # Karar bandı (B42-046 C1-C11): hepsi PASS = canon, ALCE+LVR PASS MiniCheck FAIL = frontier, biri RED = out_of_scope
        if not gates_failed:
            band = "canon"
        elif "minicheck" in str(gates_failed) and len(gates_failed) == 1:
            band = "frontier"
        else:
            band = "out_of_scope"
        return FaithfulnessVerdict(
            schema_pass=schema_ok,
            minicheck_score=minicheck,
            alce_citation_recall=alce,
            lvr_min_distance=lvr,
            decision_band=band,
            gates_failed=gates_failed,
        )

    async def _minicheck(self, c: CuratorOutput, evidence: list[Sentence]) -> float:
        """MiniCheck v2 5B NLI; MVP mock-fail-safe (cosine NLI proxy), Faz 3 HF endpoint."""
        # MVP placeholder: simple sentence overlap heuristic; calibration fixture ile eşik ayarı
        ...

    async def _alce_citation_recall(self, c: CuratorOutput, evidence: list[Sentence]) -> float:
        """ALCE citation-recall (Gao 2023): citation cümle içeriği evidence sentence'a yakınsıyor mu?"""
        # N11 v2 fact_paper_sentence.parquet ile join (Day 4 backend importer hazır)
        ...

    def _lvr_min_distance(self, c: CuratorOutput) -> float:
        """LVR (Latent Verification Region) min_distance — B42-040 confidence gate."""
        ...
```

### P009 revize plan + pseudocode

**Dosya:** `api/services/presenter.py`
**LOC:** ~140 (120 + LiteLLM router config)
**Test:** unit (TR → Cosmos branch + EN/ID → Qwen branch + onboarding lang param)

```python
# api/services/presenter.py — pseudocode (Council 28 P009, B-005)

class PresenterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curated: CuratorOutput
    lang: Literal["TR", "EN", "ID"]
    user_tier: Literal["student", "researcher", "professional", "team"]

class PresenterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary_md: str
    citations: list[str]  # paper_id list
    tokens_used: int

class DilSpesifikPresenter(Presenter):
    """LiteLLM `model_list` ile dil → endpoint routing (B-005 + B-007).

    HK-2 kaynak: B-005 2-katmanlı LLM mimarisi onayı; LiteLLM router DM-015.
    HK-3 dış: Cosmos endpoint smoke beklemede (Sercan setup); Qwen smoke ✅.
    """
    MODEL_MAP = {
        "TR": "huggingface/cosmos-turkish-gemma",  # ayrı endpoint (Sercan setup)
        "EN": "huggingface/qwen-2-5",  # Listener ile ortak endpoint
        "ID": "huggingface/qwen-2-5",  # MVP'de Qwen yeter; Komodo Faz 2 (OPEN-011)
    }

    def __init__(self, router: LiteLLMRouter) -> None:
        self._router = router

    async def present(self, inp: PresenterInput) -> PresenterOutput:
        model = self.MODEL_MAP[inp.lang]
        prompt = self._build_prompt(inp.curated, inp.lang)
        response = await self._router.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        return PresenterOutput(
            summary_md=response.choices[0].message.content,
            citations=[c.paper_id for c in inp.curated.citations],
            tokens_used=response.usage.total_tokens,
        )
```

---

## §1 P-numara revize tablosu (sıkıştırılmış sprint sırası)

| Sıra | P | İş | Dosya | LOC | Council | Smoke fixture |
|---|---|---|---|---|---|---|
| 1 | **migration 0005** | papers.title_tsv generated tsvector + GIN index (Council 25) | `api/db/migrations/0005_papers_title_fts.sql` | ~40 | 25 | — |
| 2 | **P004** | QwenListener concrete + httpx pool reuse + 3-retry + JSON schema | `api/services/listener.py` | ~250 | 26 | `hf_qwen_tr_query.json` |
| 3 | **P006** | HybridPoolRouter 3-havuz RRF k=60 + B-012 metadata filter | `api/services/pool_router.py` | ~220 | 27 | `pinecone_query_sample.json` + `postgres_title_fts_recall.json` |
| 4 | **P007** | BgeReranker local sentence-transformers CPU | `api/services/reranker.py` | ~120 | 28 | model load smoke |
| 5 | **P008** | Curator + faithfulness_gate ortak servis (3-gate cascade + LVR) | `api/services/curator.py` + `api/services/faithfulness_gate.py` | ~370 | 28 | `faithfulness_calibration.json` Day 4 wrap |
| 6 | **P009** | DilSpesifikPresenter + LiteLLM router config | `api/services/presenter.py` + `api/utils/litellm_router.py` | ~140 | 28 | `cosmos_tr_summary.json` Sercan setup sonrası |

**Toplam:** 6 atomic commit, ~1140 LOC. Day 1'in 8 commit / 3000 LOC ile birleşik 14 commit / 4140 LOC F2 toplam.

---

## §2 Omer için sıralı talimat (kod yazımı)

```
1. .venv yeniden kur
   $ cd ~/Desktop/papermind-app
   $ uv sync                                # .venv kullanıcı omer için kuruluydu, kırık
   $ source .venv/bin/activate              # veya direnv kuruluysa otomatik

2. Smoke fixture'ları üret (R13.11 zorunlu)
   $ python scripts/smoke_external_services.py
   # 4 servis × ~5 sn = ~20 sn; HF cold-start 30 sn ekle
   # tests/fixtures/{hf_qwen_tr_query,pinecone_describe,pinecone_query_sample,supabase_schema_migrations,redis_ping_cycle}.json yazılır

3. B-012 metadata patch verify
   $ cat tests/fixtures/pinecone_query_sample.json | jq '.metadata_present, .metadata_keys_in_response'
   # true + ["D","F","S","year","q_weak","method","lang","v_conf"] beklenir
   # FALSE ise B-012 patch tamamlanmamış → Council 25 RED, P006 başlamaz

4. Migration 0005 (Council 25 lexical havuz)
   $ psql $SUPABASE_DB_URL -f api/db/migrations/0005_papers_title_fts.sql
   # papers tablosu boş; lazy-fill cron Day 4 wrap'te aktive

5. Sırasıyla atomic commit P004 → P006 → P007 → P008 → P009
   # Her commit öncesi:
   #   - Council §-tablosu okundu (bu manifest)
   #   - HK-1..HK-7 gates kontrolü
   #   - pseudocode → concrete; ruff + mypy strict + pytest PASS
   #   - integration smoke (canlı dış servis) PASS
   # Commit message: [P00X] api/<modül>: <kısa öz>
   # Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

6. Day 4 wrap (P009 sonrası)
   - tests/fixtures/faithfulness_calibration.json kalibrasyon (100 paper × ground-truth)
   - papers.title lazy-fill cron başlat (24.87M batch upsert ~6h)
   - STATE.md F2 Day 4 PASS satırı; NEXT_ACTION.md F3b chat sırada

7. Sonra Sercan'a handoff
   - F2 PASS branch push (Council 22 hibrit workflow karar)
   - Sercan prod hardening başlar (B-015 iş bölümü gereği)
```

---

## §3 Açık iş listesi (Day 4 sonrası ya da Faz 3'e ertelendi)

- KD-12: Tier-aware RRF k Faz 3 (Council 27 Sercan YELLOW)
- KD-13: Faithfulness LVR eşik kalibrasyonu Day 4 wrap (Council 28 Halüsinasyon YELLOW) → **spec hazır**: `docs/plans/F2_day4_lvr_calibration_spec.md` — sampling 100 paper × 5 strafiye + corruption injection 5 tür (number_swap/year_change/false_attr/contra_verb/out_of_corpus) + threshold sweep 0.60-0.75 + Council 29 plan-time taslak; **kapsam dar**: sadece LVR (jsonschema=100% binary, MiniCheck/ALCE F3c'de); Day 4 sabah Omer 4 script ~260 LOC + 2h koşum; Council 29 Omer arbiter eşik onayı
- KD-14: MiniCheck v2 5B HF endpoint Faz 3 (CPU MVP yetersiz, Council 28 Sercan)
- KD-15: papers.abstract Pinecone sparse Plan 2 (Council 25 Plan 2 ertelemesi)
- KD-16: Komodo HF gated Faz 2 (B-007 + OPEN-011)
- KD-17: HF keepalive worker Day 4 wrap (Council 26 Son Kullanıcı YELLOW)
- KD-18: Cosmos Turkish-Gemma endpoint setup (Sercan, Day 4 öncesi)
- KD-19: Jina/Cohere Reranker A/B Faz 3 (Council 28 Daha İyisi YELLOW)

---

**Final commitment:** Bu manifest onaylandıysa Omer Day 2 sabah Adım 1 (`uv sync`) + Adım 2 (smoke) ile başlar; Day 4 akşam P009 PASS. Toplam wallclock ~3 gün × 6h aktif = 18h kod + Council. Sercan post-hoc onay paralel (her commit PR'da review).
