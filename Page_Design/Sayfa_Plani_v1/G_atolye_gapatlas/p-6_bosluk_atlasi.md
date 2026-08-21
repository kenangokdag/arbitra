# p-6 · Boşluk Atlası (GapAtlas)

> Tezgah: **GapAtlas · işaretler** (3.x)
> 8 matris atlas · sweet spot 0.55-0.85 · r-ESTRA × a-ESTRA canlı bant · inverted lookup.
> **Boşluk işaretleme yalnız burada.**

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1446-1517`
- **Sidebar:** `PaperMind_mock_v1.0.html:615-617`
- **Section header:** `PaperMind_mock_v1.0.html:1442-1443` (8 matris formülü `0.25D + 0.20K + 0.20E + 0.15F + 0.20Y`)
- **Bu md:** `Page_Design/Sayfa_Plani_v1/G_atolye_gapatlas/p-6_bosluk_atlasi.md`

## ROL
Hangi soru henüz sorulmamış, hangi yöntem o konuda hiç denenmemiş, hangi bağlama bakılmamış? **8 boşluk haritası**. Boş hücre = fırsat, parlak ★ = altın fırsat. Öğrenci-danışman dahil — tek boşluk haritası bu (tüm vitrin/atölyede). Kullanıcı seçer, "★ Bu hücreyi boşluk olarak işaretle → G2'ye geç".

## BACKEND ⚠ kısmen var (önemli boşluklar)

### Mevcut
- `GET /api/gap-heatmap` → `api/routes/gap_heatmap.py:181-225`
- Query: `matrix_id ∈ {M1,M7,M8}` (sadece 3, mock 8 iddia ediyor), `top_methods ∈ [5,30] default 14`, `top_topics ∈ [5,50] default 18`
- Pydantic out: `GapHeatmapResponse{methods, topics, cells:list[GapCellItem{method_id, topic_id, n_papers, gap_score∈[0,1], depth_norm, is_gold:bool}], total_cells, matrix_id}` (`gap_heatmap.py:25-51`)
- **Gold threshold:** `gap_score >= 0.75` (`gap_heatmap.py:43, 153, 287`) — mock'ta sweet spot **0.55-0.85** (alt sınır farklı!)
- Cache: Redis `sha256("gap:{matrix_id}:{top_methods}:{top_topics}")[:32]` TTL 1h
- Method family heuristic (Fuzzy/Network/Reference-based/...) — MCDM domain (`gap_heatmap.py:165-178`)

### ⚠ Mock-backend uyumsuzluğu

| Mock iddiası | Gerçek backend |
|---|---|
| 8 matris (M1-M8) | Sadece M1/M7/M8 (`pattern="^(M1\|M7\|M8)$"`) |
| Sweet spot **0.55-0.85** yeşil bant | Tek eşik `is_gold = gap_score >= 0.75` |
| Formula `0.25D + 0.20K + 0.20E + 0.15F + 0.20Y` (5 boyut) | `gap_score` tek skor; D/K/E/F/Y breakdown YOK |
| `POST /api/gapatlas/matrix` | Endpoint `GET /api/gap-heatmap` (POST yok) |
| `POST /api/gapatlas/inverse-lookup` | ❌ route YOK |
| r-ESTRA × a-ESTRA kesişim | ❌ route'ta yok (advisor_profile, user_style_profile yok) |
| Method family **MCDM** ("Fuzzy/AHP/TOPSIS/...") | Mock metni "Yöntem × Örneklem" sleep/melatonin domain — MCDM ile tutarsız! |
| `advisor_profile` tablosu | ❌ DB'de yok |
| `user_style_profile` (r-ESTRA) | ❌ DB'de yok |
| `gap_signal`, `golden_gap` çıktı tablo | ❌ DB'de yok |

### ⚠ Kritik domain uyumsuzluğu
Backend `_infer_method_family` (`gap_heatmap.py:165-178`) **MCDM** domain (Fuzzy/AHP/TOPSIS) kategorilerini önerirken mock M3 "Yöntem × Örneklem" sleep/melatonin örnekleri veriyor. **Bu sayfa hangi domain için?** Karar gerekli.

## DB ⚠ kısmen var
- `fact_gap_matrix` → sorgulanıyor (`gap_heatmap.py:63-69`) — `axis_x` (theme_id), `axis_y` (metod_id), `depth`, `depth_norm`, `gap_value`, `matrix_id`. **Migration dosyası bu repoda görünmüyor** (0001-0008, 0011-0016 listesinde yok). Master ENVANTER B42 kararından geliyor olabilir.
- `dim_theme` → label join (`gap_heatmap.py:78-83`) — `theme_id`, `name_tr`, `metadata.group`
- `fact_paper_metod` → mock data iddiası, route'ta sorgulanmıyor
- `fact_paper_w_estra` → mock data iddiası, route'ta sorgulanmıyor

## PİLOT
- **LLM:** Yok (lookup-only — gap_value pre-computed)
- **Pre-compute:** `fact_gap_matrix` offline pipeline ile materialize (atölye batch)

## BAĞIMLILIK
- `project_pool` (havuz, p-5'ten) — inverted lookup için
- `user_style_profile` (r-ESTRA) — sweet spot bant
- `advisor_profile` (a-ESTRA) — kesişim
- `fact_gap_matrix` PASS (migration eksik; B42-ENVANTER kanonu ile yüklü olabilir)

---

## SAYFA YAPISI (ASCII)

```
┌── 6 · Boşluk Atlası ── 8 matris · sweet spot 0.55-0.85 ──────────────┐
│ Felsefe: 8 matriste fırsat hücresini gör, danışmanla kesiştir,      │
│         işaretle.                                                     │
│                                                                       │
│ Bu sayfada: 8 boşluk haritası. Boş hücre = fırsat, parlak ★ = altın. │
│ "Boşluğu işaretle" eylemi yalnız burada.                              │
│                                                                       │
│ ┌── Simülasyon · 8 matris atlas (M3 seçili) ─────────────────────┐  │
│ │  D ✓ ─ C ✓ ─ G ● ─ A ─ S    r-ESTRA × a-ESTRA 0.74 ✓ sweet     │  │
│ │                                                                  │  │
│ │  ┌─M1─┐ ┌─M2─┐ ┌─M3 ●─┐ ┌─M4─┐                                 │  │
│ │  │KxY │ │KxB │ │YxÖ ★4│ │BxS │                                 │  │
│ │  │3 ★ │ │1 ★ │ │altın │ │2 ★ │                                 │  │
│ │  └────┘ └────┘ └──────┘ └────┘                                 │  │
│ │  ┌─M5─┐ ┌─M6─┐ ┌─M7 ─┐ ┌─M8─┐                                 │  │
│ │  │KxB2│ │YxB │ │AxK ★2│ │SxY │                                 │  │
│ │  │3 ★ │ │1 ★ │ │altın │ │ 0  │                                 │  │
│ │  └────┘ └────┘ └──────┘ └────┘                                 │  │
│ │                                                                  │  │
│ │  M3 · Yöntem × Örneklem hücre haritası   8×8                    │  │
│ │  ┌──┬──┬──┬──┬──┬──┬──┬──┐                                     │  │
│ │  │12│21│ 0│ 3│ 0│ 9│ 0│ 0│                                     │  │
│ │  │28│52│ 5│ 0│ 2│14│ 4│ 0│                                     │  │
│ │  │ 0│ 3│ 0│ 0│ 0│ 2│ 0│★ │ ← [3,8] altın · seçili              │  │
│ │  │14│19│ 0│★ │ 0│11│ 3│ 0│                                     │  │
│ │  │ 2│ 8│ 0│ 0│ 0│ 3│ 0│ 0│                                     │  │
│ │  │22│41│ 4│ 0│ 3│10│ 0│★ │                                     │  │
│ │  │ 0│ 3│ 0│ 0│ 0│ 0│ 0│★ │                                     │  │
│ │  │ 7│17│ 0│ 0│ 0│ 5│ 0│ 0│                                     │  │
│ │  └──┴──┴──┴──┴──┴──┴──┴──┘                                     │  │
│ │  x = analiz tipi · y = örneklem tipi · sayı = paper · ★ = altın │  │
│ │                                                                  │  │
│ │  ── Seçili: hücre [3,8] · ★ altın ──                            │  │
│ │  tarif      RI-CLPM × pasif sensör örneklem                     │  │
│ │  paper      0 (boşluk)                                          │  │
│ │  D derinlik  0.78  K keskinlik 0.82  E evren 0.71               │  │
│ │  F fırsat    0.69  Y yapıt-uyum 0.74                            │  │
│ │  toplam     0.75 (golden) · a-ESTRA × r-ESTRA 0.74 ✓ sweet     │  │
│ │                                                                  │  │
│ │  ┌── ↩ Inverted lookup · havuzundan en yakın ──────────┐        │  │
│ │  │ P-019 (uyum %88) M3 hücresini %62 doldurur         │        │  │
│ │  │ P-053 (uyum %94) M7 hücresine daha yakın           │        │  │
│ │  └────────────────────────────────────────────────────┘        │  │
│ │                                                                  │  │
│ │  [ ★ Bu hücreyi boşluk olarak işaretle → G2'ye geç ]            │  │
│ └──────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **8 mini matris kartı:** her biri label (M1-M8) + tarif + ★ sayısı; hover → vurgu, click → seçili (alttaki ısı haritası açılır)
- **Seçili matris hücre haritası:** 8×8 grid, hücre rengi paper-yoğunluk (0-50+), ★ = sweet spot içi
- **Hücre seçimi:** [x,y] tıkla → alt panel "tarif + 5-formül breakdown + a×r kesişim"
- **Inverted lookup paneli:** `dbeafe` mavi blok, havuzdan en yakın 2 paper + uyum %
- **★ İşaretle CTA:** gapatlas yeşil `#047857`, "G2'ye geç" navigation
- **Funnel:** D ✓ · C ✓ · G ● · A · S
- **r-ESTRA × a-ESTRA chip:** sağ-üst, sweet spot `0.55-0.85` yeşil bant göstergesi

### Back (mevcut + öneri)
1. Mount → `GET /api/gap-heatmap?matrix_id=M1&top_methods=14&top_topics=18` → 8×8 hücre veri
2. Mini-matris üstü için: **`GET /api/gapatlas/atlas-overview?project_id=`** _(öneri)_ — 8 matris başlık + ★ count + sweet spot count batch
3. Hücre seçimi → **`GET /api/gapatlas/cell?matrix_id=M3&x=3&y=8`** _(öneri)_ — D/K/E/F/Y breakdown + a×r kesişim
4. Inverted lookup → **`POST /api/gapatlas/inverse-lookup`** _(öneri)_:
   - **In:** `{project_id, matrix_id, cell:[x,y]}`
   - **Out:** `list[{paper_id, fill_pct, role, w_estra}]` — havuzdaki paper'lardan hücre cosine'a en yakın 3'ü
   - **Flow:** `project_pool` papers ESTRA radar × cell vector cosine, top_3
5. İşaretle → **`POST /api/gapatlas/mark-gap`** _(öneri)_ → `gap_signal` insert → URL push `/p-7?gap_id=`

### Veri akışı
- **Pre-compute (offline):** `fact_paper_topic` × `fact_paper_metod` cross → her hücre için `n_papers, depth, gap_value` hesapla → `fact_gap_matrix` materialize
- **Run-time (read-only):** route 8×8 dilim al, label join `dim_theme`, response build, Redis cache 1h
- **Sweet spot bant:** front-end render — `gap_score ∈ [0.55, 0.85]` olan hücreyi yeşil çerçevele (mock canon)

### Formula breakdown (öneri — backend'e enjekte)
Mock formülü `gap_score = 0.25·D + 0.20·K + 0.20·E + 0.15·F + 0.20·Y`:
- **D · derinlik** — paper sayısı log-norm tersi (`1 - depth_norm`)
- **K · keskinlik** — concept density (theme cluster cohesion)
- **E · evren** — coverage breadth (alan-content cross)
- **F · fırsat** — citation velocity gap (ileri 5 yıl projection)
- **Y · yapıt-uyum** — w_estra × user_style cosine

`fact_gap_matrix` schema bu 5 alt-skoru kolon olarak tutmalı (öneri):
```sql
ALTER TABLE public.fact_gap_matrix
  ADD COLUMN gap_d numeric, ADD COLUMN gap_k numeric, ADD COLUMN gap_e numeric,
  ADD COLUMN gap_f numeric, ADD COLUMN gap_y numeric;
-- gap_value = 0.25*gap_d + 0.20*gap_k + 0.20*gap_e + 0.15*gap_f + 0.20*gap_y (GENERATED ALWAYS)
```

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** kapalı
- **Öğrenci / Araştırmacı / Profesyonel:** açık. Inverted lookup quota: ogrenci 5 / arastirmaci 20 / profesyonel sınırsız (LLM/cosine compute)

---

## AÇIK SORULAR
1. **8 matris vs 3 matris:** mock 8 iddiası, backend M1/M7/M8 pattern. Eksik 5 matris pre-compute pipeline'ı kurulu mu?
2. **Domain çatışması:** backend `_infer_method_family` MCDM (Fuzzy/AHP/TOPSIS) — mock sleep/melatonin örneği. Repo şu an MCDM (Papermind_V2 warehouse), mock farklı domain göstermek için demo mu? Karar?
3. **Sweet spot 0.55-0.85** — backend gold ≥0.75. Üst sınır 0.85 ne anlama geliyor? Karar B-NNN var mı?
4. **5-formül D/K/E/F/Y breakdown** kolonları `fact_gap_matrix`'te yok. Yeni migration?
5. **a-ESTRA (advisor_profile)** sayfa: danışman atanması nerede? Onboarding'de yok. F-N planı?
6. **`POST /api/gapatlas/inverse-lookup`** Wow #1 — yok. Yapım sırası?
7. **Gap işaretleme persistance:** `gap_signal` ↔ `golden_gap` ayrımı? Migration?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar GapAtlas 2 sayfa | `PaperMind_mock_v1.0.html` | 615-617 |
| 2 | Section header + 5-formül | `PaperMind_mock_v1.0.html` | 1442-1443 |
| 3 | p-6 page block | `PaperMind_mock_v1.0.html` | 1446-1517 |
| 4 | techspec back/front/data | `PaperMind_mock_v1.0.html` | 1452-1458 |
| 5 | 8-matris mini grid | `PaperMind_mock_v1.0.html` | 1471-1480 |
| 6 | M3 8×8 ısı haritası | `PaperMind_mock_v1.0.html` | 1483-1493 |
| 7 | Hücre [3,8] D/K/E/F/Y | `PaperMind_mock_v1.0.html` | 1495-1506 |
| 8 | Inverted lookup blok | `PaperMind_mock_v1.0.html` | 1508-1512 |
| 9 | İşaretle CTA → G2 | `PaperMind_mock_v1.0.html` | 1514 |
| 10 | Endpoint imzası | `api/routes/gap_heatmap.py` | 181-225 |
| 11 | matrix_id pattern M1\|M7\|M8 | `api/routes/gap_heatmap.py` | 183 |
| 12 | Pydantic GapCellItem | `api/routes/gap_heatmap.py` | 37-44 |
| 13 | is_gold ≥0.75 threshold | `api/routes/gap_heatmap.py` | 43, 287 |
| 14 | Method family MCDM heuristic | `api/routes/gap_heatmap.py` | 165-178 |
| 15 | Redis cache 1h sha256 key | `api/routes/gap_heatmap.py` | 22, 54-56 |
| 16 | `dim_theme` label join | `api/routes/gap_heatmap.py` | 73-87 |
