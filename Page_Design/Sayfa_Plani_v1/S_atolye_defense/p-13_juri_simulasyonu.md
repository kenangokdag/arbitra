# p-13 · Jüri Simülasyonu (Defense)

> Tezgah: **Defense · savunma** (5.x)
> 5 jüri üyesi · 30sn timer · zincir derinlik 2 · arka plan **HyDE → fan-out → RRF → rerank** (sinyal #4).

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1929-1999`
- **Sidebar:** `PaperMind_mock_v1.0.html:628`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/S_atolye_defense/p-13_juri_simulasyonu.md`

## ROL
Tez savunması, hakem incelemesinden **farklı bir oyun**: 4-5 jüri *aynı anda* sorar, zaman baskısı vardır, sözlü cevap istenir. PaperMind 5 üyeyi (Profesyonel canlı, Anti-tez, Yöntemci, Disiplin-dışı, Pratisyen) tarz/uzmanlık/baskı seviyesiyle ayrıştırır + her cevap için **HyDE → fan-out → RRF → rerank** ile arka plandan kanıt çekerek "olası iyi cevap" simüle eder. Kullanıcı sözlü cevap dener (mikrofon) ya da yazılı; sistem cevabın **kanıt-kapsamını** puanlar. **30sn / soru** + zincir derinlik max 2.

## BACKEND ❌ YOK
`api/routes/` listesinde `defense*` yok. Mock claims:
- `POST /api/defense/jury-question` (5-üye paralel · derinlik 2 hard-cap)
- `POST /api/defense/hyde-fanout-rerank` (sinyal #4)
- `POST /api/defense/answer-score` (kullanıcı cevabı × beklenen kanıt overlap)

## DB ❌ YOK
- `mart_jury_persona_template` (5 tip + uzmanlık alanları) — yok
- `fact_user_jury_session` (her soru/cevap log + zaman) — yok
- `fact_paper_quality_v3` — mevcut envanter belirsiz, mock'ta var-saymış

---

## ÖNERİ: Eksik Backend

### `0025_jury_simulation.sql`

```sql
-- mart_jury_persona_template — 5 jüri tipi (sabit seed)
CREATE TABLE public.mart_jury_persona_template (
  persona_key       text PRIMARY KEY
                    CHECK (persona_key IN ('canli','anti_tez','yontemci','dis_disiplin','pratisyen')),
  display_name      text NOT NULL,        -- "Prof. A", "Prof. B", ...
  expertise_label   text NOT NULL,        -- "uyku", "anti-tez", "yöntemci", ...
  pressure_level    text NOT NULL CHECK (pressure_level IN ('green','yellow','red')),
  prompt_seed       text NOT NULL,
  question_count    int NOT NULL DEFAULT 4 CHECK (question_count BETWEEN 3 AND 5),
  chain_max_depth   int NOT NULL DEFAULT 2
);

-- fact_user_jury_session — her soru/cevap log
CREATE TABLE public.fact_user_jury_session (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  defense_session_id uuid REFERENCES public.fact_user_defense_session(id) ON DELETE CASCADE,
  persona_key     text NOT NULL REFERENCES public.mart_jury_persona_template(persona_key),
  question_idx    int NOT NULL,
  question_text   text NOT NULL,
  question_depth  int NOT NULL CHECK (question_depth BETWEEN 1 AND 2),
  parent_question_id uuid REFERENCES public.fact_user_jury_session(id),  -- alt-soru için
  user_answer     text,
  answer_mode     text CHECK (answer_mode IN ('voice','text')),
  answer_seconds  real,                  -- 0-30 (timer)
  evidence_coverage real CHECK (evidence_coverage BETWEEN 0 AND 1),
  hyde_evidence_chunks jsonb,            -- [{paper_id, chunk_idx, score}]
  jury_reaction   text CHECK (jury_reaction IN ('satisfied','probing','dissatisfied')),
  asked_at        timestamptz NOT NULL DEFAULT now(),
  answered_at     timestamptz
);

CREATE INDEX idx_jury_session_defense
  ON public.fact_user_jury_session (defense_session_id, asked_at);
```

### Yeni endpoint'ler

#### `POST /api/defense/jury-question`
- **In:** `{user_id, project_id, defense_session_id, full_text, persona_key?}`
- **Out:**
  ```json
  {
    "questions": [
      {"persona":"canli","idx":1,"text":"Çalışmanızın temel iddiası ne?","depth":1,"pressure":"green"},
      {"persona":"anti_tez","idx":1,"text":"Niçin pasif sensör? Aktigrafi yeterli olmaz mı?","depth":1,"pressure":"red"},
      {"persona":"yontemci","idx":3,"text":"RI-CLPM modelinde rastgele etkilerin yapı geçerliliğini nasıl doğruladınız?","depth":1,"pressure":"red","follow_up_template":"Cross-loadings için ek model uyum testleri raporlanmış mı?"},
      ...
    ],
    "active_persona": "yontemci",
    "active_idx": 3,
    "timer_seconds": 30
  }
  ```
- **Flow:**
  1. 5 persona paralel LLM call (Gemini Flash 2.0)
  2. Her persona 3-5 soru üretir; sıralanır (canlı → anti-tez → yöntemci → dış-disiplin → pratisyen)
  3. **Hard-cap 2:** depth ≤ 2; alt-soru `parent_question_id` ile bağlanır
  4. Insert `fact_user_jury_session`

#### `POST /api/defense/hyde-fanout-rerank` (sinyal #4)
- **In:** `{question_text, project_id, full_text}`
- **Out:**
  ```json
  {
    "hyde_hypotheticals": ["Modelin uyum indekslerini Tablo 4'te...", "..."],
    "fan_out_chunks": [
      {"paper_id":"P-088","chunk_idx":12,"text":"...","score":0.84},
      {"paper_id":"P-091","chunk_idx":3,"text":"...","score":0.76},
      ...23 chunk
    ],
    "rrf_rerank": [
      {"paper_id":"P-088","chunk_idx":12,"final_score":0.91,"sentence":"..."},
      ...4 cümle
    ],
    "missing_in_thesis": ["Modification indices"]
  }
  ```
- **Flow (sinyal #4):**
  1. **HyDE:** LLM "5 hipotetik mükemmel cevap" üret (prompt: "soru X için ideal cevap nasıl olur?")
  2. Her hipotetik → bge-m3 embed → Pinecone fan-out top-50 (project paper'ları + tez içi)
  3. **RRF:** `score = sum(1 / (60 + rank_i))` her chunk için
  4. **Rerank:** Cohere rerank-3 (top-50 → top-5)
  5. **Missing detection:** rerank top-5'in tezde olmayan kavramlar → "alt soru olasılığı yüksek" uyarı

#### `POST /api/defense/answer-score`
- **In:** `{jury_session_row_id, user_answer, answer_seconds, mode:'voice'|'text'}`
- **Out:** `{evidence_coverage:0.71, missing_concepts:["modification indices"], jury_reaction:"probing"}`
- **Flow:**
  1. User answer → bge-m3 embed
  2. HyDE rerank top-5 chunks ile cosine
  3. `evidence_coverage` = mean(top-3 cosine)
  4. `jury_reaction` rule: ≥0.8 satisfied / 0.55-0.8 probing / <0.55 dissatisfied
  5. Eksik concepts varsa parent → child question oluştur (depth 2)

---

## SAYFA YAPISI (ASCII)

```
┌── 13 · Jüri Simülasyonu ── 5 üye · zincir derinlik 2 · zaman baskısı ────┐
│ Felsefe: Tez savunması farklı oyun; 5 jüri paralel + arka plan HyDE→RRF.│
│                                                                            │
│ ┌── Simülasyon · 5 jüri + HyDE arka plan (tez · 12 sf) ────────────────┐│
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ✓ ─ S ●   r-ESTRA cesur 0.71 · derin 0.66          ││
│ │                                                                          ││
│ │ ┌Prof.A┐ ┌Prof.B┐ ┌Prof.C★┐ ┌Doç.D┐ ┌Dr.E┐                           ││
│ │ │canlı │ │anti  │ │yöntemci│ │dış  │ │klin│                            ││
│ │ │uyku  │ │ tez  │ │ aktif  │ │info │ │uygu│                            ││
│ │ │🟢dest│ │🔴sıkı│ │🔴 soru │ │🟡nöt│ │🟡 │                             ││
│ │ └──────┘ └──────┘ └────────┘ └─────┘ └────┘                            ││
│ │                                                                          ││
│ │ ┌── Prof. C · soru 3/5 · ⏱ 23sn ─────────────────────────────────────┐││
│ │ │ "RI-CLPM modelinizde rastgele etkilerin yapı geçerliliğini nasıl   │││
│ │ │  doğruladınız? Cross-loadings için ek model uyum testleri raporlan-│││
│ │ │  mış mı?"                                          ↳ derinlik 1/2  │││
│ │ └────────────────────────────────────────────────────────────────────┘││
│ │                                                                          ││
│ │ ┌── Kullanıcı cevap · canlı (mikrofon) ──┐ ┌── 🔁 HyDE → fan-out → RRF┐││
│ │ │ "Modelin uyum indekslerini Tablo 4'te │ │ • HyDE: 5 hipotetik     │││
│ │ │  raporladım: CFI .94, RMSEA .052,     │ │ • fan-out: 23 paragraf  │││
│ │ │  SRMR .041. Cross-loadings için       │ │   (P-088 + P-091 + tez) │││
│ │ │  modification indices'i incelemedim,   │ │ • RRF + rerank: 4 cümle │││
│ │ │  bu eksik bir nokta…"                  │ │ ⚠ 'Modification indices'│││
│ │ │ kanıt-kapsam 0.71 🟢 · eksik kabul 🟡 │ │   tezde yok — alt soru  │││
│ │ │                                       │ │   olasılığı yüksek       │││
│ │ └───────────────────────────────────────┘ └─────────────────────────┘││
│ └──────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Üst 5-grid:** 5 jüri kartı (avatar yok, isim + uzmanlık etiketi `var(--muted)` + baskı 🟢🟡🔴)
- **Aktif soru kartı:** border-left 4px `var(--defense)`, mono başlık "Prof. C · soru 3/5 · ⏱ 23sn", soru italik 12px Lora
- **Sol alt:** Kullanıcı cevap (mikrofon ikonu + canlı transcript) + 2 chip (kanıt-kapsam yeşil/sarı/kırmızı + eksik kabul)
- **Sağ alt:** **HyDE → fan-out → RRF arka plan** paneli — 4 satır mono adımlar + ⚠ kırmızı uyarı (eksik concept)
- **Funnel:** D ✓ C ✓ G ✓ A ✓ S ● (final stop yaklaşıyor)

### D17 sahne (cinematic curtain) tetikleyici?
Mock'ta D17 **bu sayfada yok** — sadece D-canon listesinde "S3 D17 perde" varsayımı vardı. Kontrol edilmeli: jüri başlangıcı dramatik açılış mı (D17), yoksa sade liste mi (mock'ta sade).

### Back (öneri)
1. Sayfa mount → `POST /jury-question` (5 paralel LLM)
2. Aktif soru render → `POST /hyde-fanout-rerank` (background, ~3-5sn)
3. 30sn timer başlar; user mikrofon/yazı cevap
4. Cevap submit → `POST /answer-score` → coverage + reaction
5. Reaction = 'probing' ve eksik concept varsa → depth 2 alt-soru üret

### 30sn timer UX
- Mock'ta `⏱ 23sn` görünüyor (geriye sayım)
- Süre doldu → "süre doldu, sonraki soru" + cevap eksik (`evidence_coverage = 0`)
- Kullanıcı manuel "süre uzat" butonu? Mock'ta YOK → eklenmemeli (gerçek savunma simülasyonu)

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı
- **Araştırmacı:** açık (5-jüri paralel + HyDE)
- **Profesyonel:** Gemini 2.5 Pro daha sofistike persona + Cohere rerank-3
- **Mikrofon:** Web Speech API (browser native) — backend gerekmez; transcript front-end'de oluşur, backend'e text gider

---

## AÇIK SORULAR
1. **D17 sahne (cinematic curtain) bu sayfada mı?** Mock satır 1929-1999 incelemesi: dramatik perde animasyonu yok, sade liste. D17 muhtemelen başka yerde (S4 final stop?). D-canon doc kontrol gerekli.
2. **HyDE prompt mühendisliği:** "5 hipotetik mükemmel cevap" — kalite garantisi nasıl? Gemini Flash 2.0 yeterli mi yoksa profesyonel tier'da 2.5 Pro şart mı?
3. **Pinecone fan-out scope:** project paper'lar + tez içi → tez kaç chunk'a bölünecek? bge-m3 embed hangi pipeline'da yapılacak (Authoring'de mi, Defense'de mi)?
4. **Mikrofon transcript doğruluk:** TR/EN Web Speech API kalitesi düşük → cevap puanlama yanlış olabilir. Backend'de Whisper-large fallback gerekli mi (profesyonel tier'a özel)?
5. **30sn timer hard-cap kanıt:** Gerçek savunmada 30sn ortalama mı? Bu rakam mock canon mu, B-NNN var mı?
6. **`fact_paper_quality_v3` belirsizlik:** Mock'ta var-saymış ama envanter (`_envanter_felsefe.md` 30 tablo) içinde adı netleşmemiş. v1, v2, v3 farkı?
7. **Jury reaction üç seviyeli:** satisfied/probing/dissatisfied threshold (0.8 / 0.55) keyfi → kullanıcı testi gerekli.
8. **Multi-language jüri:** TR tezde TR jüri sorusu, EN tezde EN soru — persona prompt seed dile göre ayrı mı?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Defense p-13 | `PaperMind_mock_v1.0.html` | 628 |
| 2 | p-13 page block | `PaperMind_mock_v1.0.html` | 1929-1999 |
| 3 | techspec endpoint (jury-question/hyde-fanout/answer-score) | `PaperMind_mock_v1.0.html` | 1938 |
| 4 | data tables (jury_persona_template, jury_session, paper_quality_v3) | `PaperMind_mock_v1.0.html` | 1939 |
| 5 | Sinyal #4 (HyDE→RRF→rerank) ayırt edici | `PaperMind_mock_v1.0.html` | 1942 |
| 6 | Δ revize: HyDE görünür hale getirildi | `PaperMind_mock_v1.0.html` | 1943 |
| 7 | 5 jüri grid (Prof.A/B/C/Doç.D/Dr.E + baskı🟢🟡🔴) | `PaperMind_mock_v1.0.html` | 1954-1970 |
| 8 | Aktif soru "Prof. C · soru 3/5 · ⏱ 23sn" | `PaperMind_mock_v1.0.html` | 1972-1976 |
| 9 | Kullanıcı cevap + kanıt-kapsam 0.71 | `PaperMind_mock_v1.0.html` | 1979-1985 |
| 10 | HyDE → fan-out → RRF arka plan paneli | `PaperMind_mock_v1.0.html` | 1987-1995 |
| 11 | api/routes/ — defense* yok | `api/routes/` (ls) | — |
