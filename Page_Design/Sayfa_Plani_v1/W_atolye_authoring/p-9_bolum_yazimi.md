# p-9 · Bölüm Yazımı (Authoring)

> Tezgah: **Authoring · yazar** (4.x)
> 11-kategori atıf rolü · bölüm-aware filtreleme. Yöntem ⇒ MTD/ANL/SMP; Bulgular ⇒ kıyaslama; Tartışma ⇒ sınır.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1648-1716`
- **Sidebar:** `PaperMind_mock_v1.0.html:621`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/W_atolye_authoring/p-9_bolum_yazimi.md`

## ROL
Atıf "kim demiş" değil "**nasıl konumlanmış**" sorusu. 11 kategori (FLD/CON/THR/MTD/ANL/SMP/CTX/INS/OUT/TEC/TMP) ve **bölüm-rol matris**. Bölüm seç (Giriş/Yöntem/Bulgular/Tartışma) → ilgili roller öne çıkar (Yöntem ⇒ MTD/ANL/SMP). Yan panelde rol-bazlı paper drawer. p-8'in 3 motoru (faithfulness + over-citation + atıfsız) burada da çalışır.

## BACKEND ❌ YOK
Mock claims:
- `GET /api/authoring/role-aware-papers?section=method&pool_id=`
- `POST /api/authoring/section-coherence` (bölüm sınır geçiş tutarlılık)
- p-8'in cite-verifier + faithfulness-scorer reuse

`api/routes/` içinde `authoring*` route YOK.

## DB ❌ YOK
Mock data iddiaları:
- `fact_paper_citation_role_v2` (sinyal #35 — 11 kategori) — repo'da yok
- `mart_pool_role_distribution` (havuz × bölüm × rol matrisi) — yok
- `fact_user_authoring_session` (p-8'de öneri olarak belirtildi)

---

## ÖNERİ: Eksik Backend

### `0021_citation_role.sql`

```sql
-- fact_paper_citation_role_v2 — paper'ın yapısal atıf rolü (sinyal #35)
CREATE TABLE public.fact_paper_citation_role_v2 (
  paper_id      text NOT NULL,
  role          text NOT NULL CHECK (role IN (
                  'FLD',  -- Field — alan/disiplin tanımı
                  'CON',  -- Conceptual — kavram canon
                  'THR',  -- Theoretical — teorik çerçeve
                  'MTD',  -- Method — yöntem canon
                  'ANL',  -- Analytical — analiz aracı/paket
                  'SMP',  -- Sampling — örneklem stratejisi
                  'CTX',  -- Context — bağlam (kültür/popülasyon)
                  'INS',  -- Instrument — ölçek/anket
                  'OUT',  -- Outcome — bulgu kıyaslama
                  'TEC',  -- Technology — donanım/teknoloji
                  'TMP'   -- Temporal — zamansal/longitudinal
                )),
  confidence    real NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  source        text NOT NULL CHECK (source IN ('llm','heuristic','manual')),
  inferred_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (paper_id, role)  -- bir paper birden fazla rol alabilir
);

CREATE INDEX idx_role_v2_paper ON public.fact_paper_citation_role_v2 (paper_id);
CREATE INDEX idx_role_v2_role  ON public.fact_paper_citation_role_v2 (role, confidence DESC);

-- mart_pool_role_distribution — havuz × bölüm × rol matrisi (materialize)
CREATE MATERIALIZED VIEW public.mart_pool_role_distribution AS
SELECT
  pp.project_id,
  fcr.role,
  COUNT(*) AS paper_count,
  AVG(fcr.confidence) AS avg_confidence,
  array_agg(fcr.paper_id) AS paper_ids
FROM public.project_pool pp
JOIN public.fact_paper_citation_role_v2 fcr ON pp.paper_id = fcr.paper_id
WHERE pp.role != 'disla'  -- p-5'teki dışlanmamış paper'lar
GROUP BY pp.project_id, fcr.role;

-- Bölüm-rol uyum hedef matrisi (sabit referans)
CREATE TABLE public.section_role_target (
  section       text NOT NULL CHECK (section IN ('intro','method','results','discussion')),
  role          text NOT NULL,
  min_count     int NOT NULL DEFAULT 0,
  weight        real NOT NULL DEFAULT 1.0,
  PRIMARY KEY (section, role)
);
INSERT INTO public.section_role_target VALUES
  ('intro',    'FLD', 1, 1.0), ('intro',    'CON', 2, 1.0), ('intro',    'THR', 1, 0.8),
  ('method',   'MTD', 2, 1.5), ('method',   'ANL', 1, 1.2), ('method',   'SMP', 1, 1.0),
  ('method',   'INS', 1, 0.8), ('method',   'TEC', 1, 0.6),
  ('results',  'OUT', 2, 1.5), ('results',  'CTX', 1, 0.8),
  ('discussion','OUT', 2, 1.0), ('discussion','THR', 1, 1.2), ('discussion','TMP', 1, 0.6);
```

### Yeni endpoint'ler

#### `GET /api/authoring/role-aware-papers?section=&project_id=`
- **In:** `section ∈ {intro,method,results,discussion}`, `project_id`, `top_k=10`
- **Out:**
  ```json
  {
    "section": "method",
    "expected_roles": [{"role":"MTD","min":2,"weight":1.5},{"role":"ANL","min":1,...}],
    "papers": [
      {"paper_id":"P-088","year":2017,"role":"MTD","confidence":0.92,
       "reason":"RI-CLPM canon — yöntem bölümü için ana referans",
       "badges":["🟢","canon"]},
      ...
    ]
  }
  ```
- **Flow:**
  1. `section_role_target` lookup → expected roles
  2. `mart_pool_role_distribution` filter project_id + role IN expected → paper list
  3. Each paper join `fact_paper_quality_v3` (mühür) + `fact_paper_w_estra` (rozet)
  4. Cache: `role-aware:{project_id}:{section}` TTL 1h

#### `POST /api/authoring/section-coherence`
- **In:** `{project_id, section, current_paragraph_text, citations:list[{paper_id, span}]}`
- **Out:**
  ```json
  {
    "uyum_matrix": {"MTD":1, "TEC":1, "SMP":1, "atifsiz":1},
    "target":      {"MTD":2, "ANL":1, "SMP":1},
    "warnings": [
      "Yöntem cümlesi atıfsız (TEC/ANL bekleniyor)",
      "MTD eksik (1/2 hedef)"
    ],
    "suggestions": [
      {"role":"ANL","paper_id":"P-091","reason":"lavaan implementasyonu"}
    ]
  }
  ```
- **Flow:** mevcut atıfların role lookup → bölüm hedefiyle delta → eksik rolleri öner

#### Reuse `POST /api/authoring/sentence` (p-8'den)
- Aynı endpoint, `page='p-9'` flag'i ile
- Ek: response içinde `role_match:bool` (bölüm beklentisiyle uyumlu mu)

---

## SAYFA YAPISI (ASCII)

```
┌── 9 · Bölüm Yazımı ── 11-kategori atıf rolü ──────────────────────────┐
│ Felsefe: atıf rolüyle (FLD/CON/THR/MTD/ANL/SMP/CTX/INS/OUT/TEC/TMP)  │
│ bölüm-aware filtreleme.                                                │
│                                                                        │
│ ┌── Simülasyon · Yöntem bölümü · rol-aware ────────────────────────┐  │
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ● ─ S   r-ESTRA derin 0.66 ↑.05            │  │
│ │                                                                    │  │
│ │ [Giriş] [Yöntem ✓] [Bulgular] [Tartışma]                          │  │
│ │                                                                    │  │
│ │ ┌── editör ──────────────────┐ ┌── rol-aware drawer ──────────┐ │  │
│ │ │ Çalışma RI-CLPM çerçeve... │ │ Yöntem bölümü · rol önerisi  │ │  │
│ │ │ [P-088 · MTD] (yeşil ✓)    │ │ ┌──────────────────────────┐ │ │  │
│ │ │                            │ │ │ MTD  P-088 · 2017        │ │ │  │
│ │ │ ... aktigrafiyle ölçül...  │ │ │ RI-CLPM canon · 🟢 canon │ │ │  │
│ │ │ [P-053 · TEC] (yeşil)      │ │ ├──────────────────────────┤ │ │  │
│ │ │                            │ │ │ ANL  P-091 · 2021        │ │ │  │
│ │ │ Örneklem 14-17 yaş 312...  │ │ │ lavaan paket · 🟢 ◇ Uzzi │ │ │  │
│ │ │ [P-074 · SMP] (sarı ⚠)     │ │ ├──────────────────────────┤ │ │  │
│ │ │                            │ │ │ SMP  P-019 · 2020        │ │ │  │
│ │ │ Veri analizi standart      │ │ │ benzer örneklem strat.   │ │ │  │
│ │ │ paket programlarla yapıl.  │ │ └──────────────────────────┘ │ │  │
│ │ │ (kırmızı atıfsız ⚠)        │ │                              │ │  │
│ │ │ ⚠ TEC/ANL bekleniyor       │ │                              │ │  │
│ │ └────────────────────────────┘ └──────────────────────────────┘ │  │
│ │                                                                    │  │
│ │ ┌── Bölüm-rol uyum matrisi ──────────────────────────────┐        │  │
│ │ │ Yöntem bölümünde 4 atıf: 1 MTD ✓ · 1 TEC ✓ · 1 SMP ⚠ · │        │  │
│ │ │ 1 atıfsız ⚠   Hedef: en az 2 MTD + 1 ANL              │        │  │
│ │ └────────────────────────────────────────────────────────┘        │  │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Üst sekme:** Giriş / Yöntem ✓ / Bulgular / Tartışma — aktif olanın authoring amber alt-bant
- **Sol editör:** p-8 stilinde cümle-bazlı highlight + inline `[P-NNN · ROL]` rank-tag
- **Sağ rol-drawer:** seçili bölüm için 3-5 paper kart (rol renk-kodu: MTD=mavi, ANL=mor, SMP=yeşil...)
- **Alt uyum matris şeridi:** mevcut atıfların rol dağılımı + hedef + eksiklikler
- **Bölüm geçişinde:** auto `POST /section-coherence` → koherans uyarısı modal

### 11 rol renk paleti (öneri)
| Rol | Renk | Anlam |
|---|---|---|
| FLD | `#64748b` | alan tanımı |
| CON | `#0891b2` | kavram canon |
| THR | `#7c3aed` | teorik |
| MTD | `#3b82f6` | yöntem |
| ANL | `#7c3aed` | analiz |
| SMP | `#10b981` | örneklem |
| CTX | `#f59e0b` | bağlam |
| INS | `#06b6d4` | ölçek |
| OUT | `#dc2626` | bulgu |
| TEC | `#84cc16` | teknoloji |
| TMP | `#a855f7` | zaman |

### Back (öneri)
1. Sekme tıklanma → `GET /role-aware-papers?section=method` → drawer dolar
2. Cümle yaz (p-8'den reuse) → `POST /sentence` (page='p-9') → response içinde `role_match`
3. Bölüm geçişi → `POST /section-coherence` → uyumsuzluk uyarısı

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı
- **Araştırmacı:** açık. Quota: role-aware fetch sınırsız (cache), section-coherence günlük 50
- **Profesyonel:** + Gemini 2.5 Pro + quota 2× artar

---

## AÇIK SORULAR
1. **11 rol enum kararı:** B-NNN var mı? Sinyal #35 ENVANTER'da kanon mu yoksa mock icat mı?
2. **`fact_paper_citation_role_v2` üretimi:** offline LLM batch mi, anlık inference mi? Maliyet?
3. **Bölüm-rol hedef matrisi** (yukarıda örnek) — `section_role_target` kararı kim verir? Akademik canon literatürü?
4. **Bir paper birden fazla rol alabilir mi?** PK `(paper_id, role)` — evet. Ama "primary_role" gerek mi?
5. **Multi-section editor state:** kullanıcı 4 bölüm paralel yazıyor — state DB'de mi tutulacak (auto-save) yoksa client localStorage mı?
6. **Bölüm sınır geçiş tutarlılık:** `POST /section-coherence` ne sıklıkla? Her sekme değişiminde mi, yalnız bölüm bittiğinde mi?
7. **TEC vs MTD ayrımı:** mock "TEC=ölçek aracı, MTD=RI-CLPM canon" diyor; ama "ölçek" INS'e daha yakın. Tanım netleştirme.

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Authoring p-9 | `PaperMind_mock_v1.0.html` | 621 |
| 2 | p-9 page block | `PaperMind_mock_v1.0.html` | 1648-1716 |
| 3 | techspec endpoint + 11 rol | `PaperMind_mock_v1.0.html` | 1654-1660 |
| 4 | Sekmeli bölüm seçici | `PaperMind_mock_v1.0.html` | 1673-1678 |
| 5 | 4 cümle (Yöntem) örnek | `PaperMind_mock_v1.0.html` | 1681-1687 |
| 6 | Rol-aware drawer 3 paper | `PaperMind_mock_v1.0.html` | 1689-1708 |
| 7 | Bölüm-rol uyum matrisi şeridi | `PaperMind_mock_v1.0.html` | 1711-1713 |
| 8 | api/routes/ — authoring* yok | `api/routes/` (ls) | — |
| 9 | p-8 sentence reuse | `Page_Design/Sayfa_Plani_v1/W_atolye_authoring/p-8_literatur_yazimi.md` | §ÖNERİ |
