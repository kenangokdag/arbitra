# p-8 · Literatür Yazımı (Authoring)

> Tezgah: **Authoring · yazar** (4.x) — cite-bound · faithfulness denetimi
> Cümle-bazlı denetimli paraphrase: faithfulness < 0.70 → kırmızı + alternatif paper. Over-citation tespiti. Atıfsız iddia altı çizik.

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1593-1645`
- **Sidebar:** `PaperMind_mock_v1.0.html:619-620`
- **Section header:** `PaperMind_mock_v1.0.html:1590` (Authoring rol: faithfulness denetimli atıf-bağı yazım)
- **Bu md:** `Page_Design/Sayfa_Plani_v1/W_atolye_authoring/p-8_literatur_yazimi.md`

## ROL
"Boş sayfa korkusu yapay zekâyla bitmez — denetimli atıf-bağı yazımıyla biter." Cümle yazılır → arka planda faithfulness skoru → 0.70 altı kırmızı + alternatif paper önerisi (Pinecone bgem3). Over-citation: aynı paper 5+ tekrar uyarısı. Kanıtsız iddia altı çizik. **3 motor:** cite-verifier, faithfulness-scorer, atıfsız-detection.

## BACKEND ❌ YOK
Mock claims:
- `POST /api/authoring/sentence` `{sentence, evidence_paper_ids[]}` → cite-verifier + faithfulness-scorer
- `POST /api/authoring/draft-paragraph`
- `GET /api/authoring/r-estra-live?session_id=`

`api/routes/` içinde `authoring*` route YOK. Tüm sayfa öneri.

## DB ❌ YOK
Mock data iddiaları:
- `fact_paper_quality_v3` (✅ 0007 migration mevcut — RCR/FCR/CD)
- `fact_paper_w_estra` (✅ 0005 migration mevcut)
- `mart_paper_keybert_extraction` (kanıt yok — ENVANTER B42 olabilir)
- `fact_user_authoring_session` (❌ yok — yeni)
- `fact_user_r_estra_paper_level` (❌ yok — yeni)

---

## ÖNERİ: Eksik Backend

### `0020_authoring_session.sql`

```sql
-- fact_user_authoring_session — cümle-by-cümle log + faithfulness
CREATE TABLE public.fact_user_authoring_session (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  page            text NOT NULL CHECK (page IN ('p-8','p-9','p-10')),
  paragraph_idx   int NOT NULL,
  sentence_idx    int NOT NULL,
  sentence_text   text NOT NULL,
  evidence_paper_ids text[] NOT NULL DEFAULT '{}',
  faithfulness    real CHECK (faithfulness IS NULL OR faithfulness BETWEEN 0 AND 1),
  status          text CHECK (status IN ('ok','warn','err','unverified')),
  -- err = faithfulness < 0.70; warn = single-cite hedge; ok = >= 0.85; unverified = no cite
  alt_paper_suggested text,  -- pinecone semantic en yakın
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- fact_user_r_estra_paper_level — paper eklendikçe r-ESTRA güncelleme
CREATE TABLE public.fact_user_r_estra_paper_level (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  paper_id        text NOT NULL,
  cesur_delta     numeric,
  derin_delta     numeric,
  tarafsiz_delta  numeric,
  cumulative_cesur     numeric,
  cumulative_derin     numeric,
  cumulative_tarafsiz  numeric,
  added_at        timestamptz NOT NULL DEFAULT now()
);
```

### Yeni endpoint'ler

#### `POST /api/authoring/sentence`
- **In:** `{project_id, page:'p-8', sentence:str, evidence_paper_ids:list[str]}`
- **Out:**
  ```json
  {
    "faithfulness": 0.83,
    "status": "ok",
    "missing_evidence_pos": [12, 24],  // atıfsız iddia char index
    "over_citation": {"paper_id":"P-019", "count":5, "variants":["P-046","P-088"]},
    "alt_paper": {"paper_id":"P-053", "sim":0.81, "reason":"semantic match"}
  }
  ```
- **Flow:**
  1. Sentence + evidence_paper_ids içeriği fetch (paper abstract via `papers` tablo)
  2. **Faithfulness scorer:** Gemini Flash 2.0 prompt — "evidence içerikleri sentence'ı destekliyor mu? 0-1 skor"
  3. **Cite-verifier:** evidence_paper_ids `project_pool` içinde mi? Gate.
  4. **Atıfsız iddia detection:** sentence içinde rakam/kıyaslama var mı + evidence_paper_ids boş mu? → underline span'ler
  5. **Over-citation:** session'da aynı paper count >= 5 → varyant öner (Pinecone semantic)
  6. **Alt paper (eğer faithfulness < 0.70):** Pinecone semantic search (sentence embed) → top-1 farklı paper
  7. Insert/update `fact_user_authoring_session` row

#### `POST /api/authoring/draft-paragraph`
- **In:** `{project_id, outline_text, target_paper_ids:list[str]}`
- **Out:** `{paragraph:str, sentences:list[{text, evidence}]}`
- LLM Gemini Flash 2.0 — outline'dan paragraf üret, her cümleye Q1-style inline `[Pxx]` rank-tag
- Faithfulness gate: her citation `target_paper_ids ⊆ project_pool`

#### `GET /api/authoring/r-estra-live?session_id=`
- **Out:** `{cesur:0.74, derin:0.61, tarafsiz:0.58, deltas:{cesur:+0.03, ...}}`
- Flow: session'daki paper'ların `fact_paper_w_estra` aggregate → kullanıcı cumulative profil

---

## SAYFA YAPISI (ASCII)

```
┌── 8 · Literatür Yazımı ── cite-bound · faithfulness ──────────────────┐
│ Felsefe: cümle başına kanıt zinciri. Bağsız iddia kırmızı altı çizik. │
│                                                                        │
│ ┌── Simülasyon · cümle-bazlı faithfulness ─────────────────────────┐  │
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ● ─ S    r-ESTRA cesur 0.74 ↑.03           │  │
│ │                                                                    │  │
│ │ ┌─────────── editör ──────────────────────────────────────┐      │  │
│ │ │ Ergenlerde akşam ekran maruziyetinin uyku başlangıç     │      │  │
│ │ │ süresi üzerindeki etkisi son on yılda artan biçimde     │      │  │
│ │ │ belgelenmiştir [P-019; P-046]. (yeşil ✓ 0.85)          │      │  │
│ │ │ Bu etkinin nedensel yönü ... bir kısıtıdır [P-019].     │      │  │
│ │ │ (sarı ⚠ 0.68)                                           │      │  │
│ │ │ Pasif sensörlerle yapılan çalışmaların sayısı sınırlı   │      │  │
│ │ │ kalmıştır ve bu durum literatürün önemli bir boşluğudur.│      │  │
│ │ │ (kırmızı ✗ 0.41 — atıfsız iddia altı çizik)            │      │  │
│ │ │ RI-CLPM gibi panel modeller... [P-088]. (yeşil 0.92)   │      │  │
│ │ └────────────────────────────────────────────────────────┘       │  │
│ │                                                                    │  │
│ │ ┌── ⚠ Faithfulness 0.41 ──┐  ┌── ⚠ Over-citation P-019 ──┐       │  │
│ │ │ "Pasif sensör..." kanıt │  │ Bu paragrafta 5 kez. Var. │       │  │
│ │ │ yok. P-053 destekliyor? │  │ P-046 (◆ B 8.7) ya da     │       │  │
│ │ │ [P-053 ekle · yeniden ölç]│ │ P-088 (RI-CLPM canon)     │       │  │
│ │ └─────────────────────────┘  └────────────────────────────┘       │  │
│ │                                                                    │  │
│ │ ┌── Aktif paper · ESTRA Pasaport (D2/G1 propagasyonu) ──┐         │  │
│ │ │ P-019 · 2020 · Q1 (4.2)  [🟢 mühür][★ CD 0.42][CON]   │         │  │
│ │ │ RCR 2.4  FCR 1.9  faithfulness ort. 0.83 (4 cümle)    │         │  │
│ │ └────────────────────────────────────────────────────────┘         │  │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Sol editör:** cümle-by-cümle highlight (yeşil ok / sarı warn / kırmızı err / underline=atıfsız)
- **Sağ üst:** Aktif paper kartı (ESTRA Pasaport propagasyonu p-4'ten)
- **Alt panel:** 2 grid — Faithfulness alert + Over-citation alert (gerektiğinde görünür)
- **r-ESTRA mini şerit:** sağ-üst, eklenen her atıfla cesur/derin delta gösterir

### Back (öneri)
- Sentence yazıldığı an (debounce 800ms) → `POST /api/authoring/sentence`
- Async UI render: status renk + alt paneller
- "Ekle" butonu → sentence rewrite + tekrar score

### Veri akışı
1. p-7 → "Authoring'e taşı" → push `/p-8?package_id=` (RQ + havuz miras)
2. Editor mount → empty state veya G2 outline import
3. Cümle yaz → debounce → `POST /sentence` → render
4. Save draft → `fact_user_authoring_session` rows
5. Bitir → push `/p-9` (Bölüm Yazımı)

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı (Authoring profesyonel ihtiyaç)
- **Araştırmacı:** açık. Quota günlük 100 sentence-score, Pinecone alt-paper-suggest 30
- **Profesyonel:** Gemini 2.5 Pro (uzun bağlam + paragraph-level coherence) + quota 2× artar

---

## AÇIK SORULAR
1. **Faithfulness threshold 0.70:** karar B-NNN var mı? Q1 vitrin'de Pydantic gate kullanıyor (`citations[i].paper_ids ⊆ used_paper_ids`) — atölyede `< 0.70 = err` kuralı eski mock'tan mı?
2. **`mart_paper_keybert_extraction`** ENVANTER kanon mu, yoksa mock icat mı? Bağımsız doğrulama gerek.
3. **Pinecone bgem3 model:** repo'da Pinecone client kurulu mu? `vector_index_name` ne?
4. **Atıfsız iddia regex/heuristic:** rakam + kıyaslama detection nasıl? LLM mi heuristic mi?
5. **Over-citation eşiği:** 5+ sabit mi, paragraf uzunluğuna göre dinamik mi?
6. **r-ESTRA `tarafsız` boyutu:** mock'ta görünür ama `fact_paper_w_estra` 7-boyut canon (canon/teorik/empirik/methodol/replikasyon/novelty/ölçek) — `tarafsız` ekstra mı, eşleştirme mi?
7. **Session isolation:** aynı kullanıcı 2 proje paralel — `paragraph_idx` global mi proje-bazlı mı?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Authoring 3 sayfa | `PaperMind_mock_v1.0.html` | 619-622 |
| 2 | Authoring section header | `PaperMind_mock_v1.0.html` | 1590 |
| 3 | p-8 page block | `PaperMind_mock_v1.0.html` | 1593-1645 |
| 4 | techspec endpoint adları | `PaperMind_mock_v1.0.html` | 1599-1604 |
| 5 | 4-cümle paragraf (ok/warn/err/ok) | `PaperMind_mock_v1.0.html` | 1618-1623 |
| 6 | Faithfulness 0.41 alert | `PaperMind_mock_v1.0.html` | 1626-1630 |
| 7 | Over-citation P-019 alert | `PaperMind_mock_v1.0.html` | 1631-1634 |
| 8 | Aktif paper Pasaport | `PaperMind_mock_v1.0.html` | 1637-1642 |
| 9 | api/routes/ — authoring* yok | `api/routes/` (ls) | — |
| 10 | Q1 faithfulness gate canon | `Page_Design/Sayfa_Plani_v1/_envanter_felsefe.md` | §11 |
