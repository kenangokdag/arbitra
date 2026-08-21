# p-4 · Connected Papers (Curation)

> Tezgah: **Curation · seçer** (2.x)
> Anchor → bibliographic coupling top-50 ağı + ESTRA Pasaport sticky panel.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1272-1358`
- **Sidebar:** `PaperMind_mock_v1.0.html:611-612`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/C_atolye_curation/p-4_connected_papers.md`

## ROL
Anchor (proje çapası) etrafındaki paper komşuluğu — bibliographic coupling lookup, hesap yok. Renk=yıl, boyut=atıf, çizgi=yakınlık. Filtreler: yıl/benzerlik/tema/★◆◇ rozet. **ESTRA Pasaport sticky panel** sağda (eski hover-card 7 sinyali sıkıştırıyordu — bilişsel yük yüksekti, sticky'ye taşındı).

## BACKEND ✅ var (kısmi — mock fazla iddialı)
- `GET /api/connected-papers/{paper_id}?top_k=20` → `api/routes/connected_papers.py:77-121`
- Pydantic out: `ConnectedPapersResponse{source_paper_id, neighbors:list[ConnectedPaper{paper_id,title,cosine_score,raw_count,rank}], total}` (`connected_papers.py:26-37`)
- Title enrichment: OpenAlex batch (`/works?filter=ids.openalex:{...}`) — `connected_papers.py:53-74`
- Cache: Redis `connpap:{paper_id}:{top_k}` TTL 1h (`connected_papers.py:23, 83-86, 120`)
- top_k validate `ge=1, le=50` (`connected_papers.py:80`)

### ⚠ Mock-backend uyumsuzluğu
| Mock iddiası | Gerçek |
|---|---|
| `GET /api/discovery/anchor?paper_id=` | `GET /api/connected-papers/{paper_id}` |
| `mart_cocitation_pair` 2-hop | YOK (sadece direct bibcoupling) |
| `fact_paper_quality_v3` join | YOK (route'ta sorgulanmıyor) |
| `fact_paper_w_estra` 7-boyut radar | YOK route'ta — Pasaport panel için ek endpoint gerekli |
| ★◆◇ rozet (CD/Beauty/Uzzi) filter | route döndürmüyor — ek endpoint gerekli |

## DB ✅ var
- `fact_paper_bibcoupling_top50` → `db/migrations/0008_neighbor_bibcoupling.sql:26-37` — 643M satır, 4.81 GB parquet, `(paper_id, neighbor_id) PK`, `cosine_score real ∈ [0,1]`, `rank smallint ∈ [1,50]`, **NO FK** (loader anti-join, disk tasarrufu B42-030)
- Coverage: 15.87M paper (%63.8 master 24.87M)
- ⚠ ESTRA radar için `fact_paper_w_estra` (0005 migration), CD/Uzzi için `fact_paper_quality_v3` (0007) — bu route'ta join YOK

## PİLOT
- **LLM:** Yok (lookup-only, hesap yok)
- **Hesap:** Bibcoupling önceden materialize (offline pipeline → parquet → Postgres)

## BAĞIMLILIK
- **Anchor seçimi:** P094+ (`project_anchor.anchor_paper_id` set olmalı) — yoksa sayfa kapı: "önce 1.1'de anchor kilitle"
- `0008_neighbor_bibcoupling` PASS
- OpenAlex `OPENALEX_EMAIL` config (yoksa graceful fallback `connected_papers.py:73-74`)

---

## SAYFA YAPISI (ASCII)

```
┌── 4 · Connected Papers ────── Anchor → bibcoupling 50 ──────────────┐
│                                                                      │
│ Felsefe: Anchor etrafındaki komşuluk; lookup, hesap yok.            │
│ Pasaport sticky panelde.                                             │
│                                                                      │
│ Bu sayfada ne yapılır: anchor merkezli ağ; 50-100 akraba; renk/yıl, │
│ boyut/atıf, çizgi/yakınlık. Filtreler: yıl/benzerlik/tema/★◆◇.     │
│ Sepete at. Pasaport sağda (tıkla → 6 sinyal).                       │
│                                                                      │
│ ┌── Simülasyon · anchor ağı + pasaport (P-001 merkez) ─────────┐    │
│ │  D ✓ ─ C ● ─ G ─ A ─ S        r-ESTRA cesur 0.71 derin 0.58  │    │
│ │  ┌──────────────── ağ SVG ────┐  ┌── ESTRA Pasaport ──────┐  │    │
│ │  │      P-046                  │  │  P-019 · 2020          │  │    │
│ │  │   ●  (2022)                 │  │  RCR 2.4   FCR 1.9     │  │    │
│ │  │     \                       │  │  SJR Q1·4.2  CD ★ 0.42 │  │    │
│ │  │      \  P-019  P-053        │  │  Uzzi 62%              │  │    │
│ │  │       ●═════●═●             │  │  ── 7-radar ──         │  │    │
│ │  │      /  P-001              │  │  canon  .78  ▓▓▓▓▓░░░  │  │    │
│ │  │  P-074 (anchor amber)       │  │  empirik .91 ▓▓▓▓▓▓▓░  │  │    │
│ │  │   ●  P-088 P-091            │  │  replik. .34 ▓▓░░░░░░  │  │    │
│ │  │      ●  ●                   │  │  novelty .62 ▓▓▓▓░░░░  │  │    │
│ │  └─────────────────────────────┘  └────────────────────────┘  │    │
│ │                                                                │    │
│ │  Filtreler: ★ atılım · ◆ uyanan · ◇ novel · 🟢 mühür · 2020+ │    │
│ │            52 paper · seçili 7                                 │    │
│ │                                                                │    │
│ │  □ P-019 · Blue light suppression and sleep onset (2020)       │    │
│ │      1,847 atıf · benzerlik 0.84 · 🟢 ★ CD 0.42 · 2020         │    │
│ │  □ P-046 · Pre-2010 melatonin study (2008, uyandı 2020)        │    │
│ │      1,289 atıf · benzerlik 0.61 · 🟢 ◆ B 8.7                  │    │
│ │  □ P-053 · Atypical biomarker model (2022)                     │    │
│ │      89 atıf · benzerlik 0.72 · 🟡 ◇ Uzzi 92%                  │    │
│ │                                                                │    │
│ │  [ Sepete at (3) → Havuzum ]                                   │    │
│ └────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Ana ağ:** SVG node-link (anchor merkez amber `#b45309`, komşular renk=yıl gradient, boyut=atıf log scale, çizgi kalınlık=cosine_score). 50 paper default, 100'e kadar genişler.
- **Filtreler:** yıl slider · benzerlik threshold · tema chip · ★◆◇ rozet toggle (★=CD>0.3, ◆=Beauty>5, ◇=Uzzi>80%)
- **Sticky Pasaport panel (sağ):** node tıklanınca yenilenir — RCR/FCR/SJR/CD/Uzzi metrik blok + 7-boyut radar (canon/teorik/empirik/methodol./replikasyon/novelty/ölçek)
- **Komşu kart liste:** seçili paper'lar checkbox + atıf + benzerlik + rozet
- **Sepet CTA:** `Sepete at (N) → Havuzum` (curation amber)
- **Funnel:** D done · C active · G/A/S todo
- **r-ESTRA chip:** sağ-üst (cesur/derin skor)

### Back
- **Mevcut:** `GET /api/connected-papers/{paper_id}?top_k=20` → 20 komşu (id, title, cosine, rank)
- **Eksik (öneri):** Pasaport panel için **`GET /api/connected-papers/{paper_id}/passport?neighbor_ids=...`** → batch ESTRA radar + quality:
  - Pydantic out: `list[PassportItem{paper_id, rcr, fcr, sjr_quartile, cd_index, uzzi_novelty, w_estra_canon, w_estra_teorik, w_estra_empirik, w_estra_methodol, w_estra_replikasyon, w_estra_novelty, w_estra_olcek}]`
  - Join: `fact_paper_quality_v3` (RCR/FCR/CD) + `fact_paper_metadata` (SJR) + `fact_paper_w_estra` (7-boyut)
  - Cache: `connpap:passport:{paper_id_hash}` TTL 1h
- **Eksik (öneri):** Rozet filtre için `GET /api/connected-papers/{paper_id}?badge=star|diamond|circle` query param — server-side filter (çünkü 50 paper × 6 sinyal client'a indirmek istemeyiz)

### Veri akışı
1. Sayfa mount → `project_anchor.anchor_paper_id` oku → yoksa kilit
2. `GET /api/connected-papers/{anchor_id}?top_k=20` → 20 neighbor
3. Render ağ (SVG) — anchor merkez, neighbor'lar etrafa
4. Node click → **`GET /api/connected-papers/{anchor_id}/passport?neighbor_ids=`** _(öneri)_ → sticky panel render
5. Checkbox seçim → state buffer (front)
6. "Sepete at" → `POST /api/reading-list` (mevcut, p-5'te) — paper_id batch insert

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** kapalı (vitrin Q ile sınırlı, atölye yok)
- **Öğrenci / Araştırmacı / Profesyonel:** açık. top_k quota: ogrenci 20 / arastirmaci 35 / profesyonel 50 (öneri — backend henüz uygulamıyor)

---

## AÇIK SORULAR
1. **`fact_paper_quality_v3`** schema'sı 0007'de — RCR/FCR/CD kolonları var mı? Kontrol gerekli.
2. **`fact_paper_w_estra`** 7-boyut sütun adları — 0005 migration'da tam isimler ne? (canon/teorik/empirik...)
3. **`mart_cocitation_pair`** 2-hop için — mock iddiası ama 0008'de yok. Co-citation tablosu ileri faz mı?
4. **★◆◇ rozet eşikleri** kim belirler? Karar B-NNN var mı yoksa heuristik mi?
5. **Pool size 50 vs 100** — mock "50-100" diyor, backend max 50. 100 isterse 2 batch çağrı?
6. **r-ESTRA chip kaynağı** — anchor'ın kendi w-ESTRA'sı mı, yoksa havuz aggregate mi?
7. **2020+ year filter** server-side mı client-side mı? Bibcoupling tablosunda yıl yok → join `fact_paper_anchor` (0003)

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Curation 2 sayfa | `PaperMind_mock_v1.0.html` | 611-613 |
| 2 | p-4 page block | `PaperMind_mock_v1.0.html` | 1272-1358 |
| 3 | techspec back/front/data | `PaperMind_mock_v1.0.html` | 1278-1284 |
| 4 | ESTRA Pasaport sim | `PaperMind_mock_v1.0.html` | 1315-1335 |
| 5 | Komşu kart + rozet | `PaperMind_mock_v1.0.html` | 1337-1352 |
| 6 | Sepete at CTA | `PaperMind_mock_v1.0.html` | 1353-1355 |
| 7 | Endpoint imzası | `api/routes/connected_papers.py` | 77-121 |
| 8 | Pydantic schema in/out | `api/routes/connected_papers.py` | 26-37 |
| 9 | Redis cache 1h | `api/routes/connected_papers.py` | 23, 83-86, 120 |
| 10 | OpenAlex title enrichment | `api/routes/connected_papers.py` | 53-74 |
| 11 | top_k 1..50 validate | `api/routes/connected_papers.py` | 80 |
| 12 | `fact_paper_bibcoupling_top50` schema | `db/migrations/0008_neighbor_bibcoupling.sql` | 26-37 |
| 13 | NO FK kararı (B42-030) | `db/migrations/0008_neighbor_bibcoupling.sql` | 12-15 |
| 14 | RLS read_all authenticated | `db/migrations/0008_neighbor_bibcoupling.sql` | 39-43 |
