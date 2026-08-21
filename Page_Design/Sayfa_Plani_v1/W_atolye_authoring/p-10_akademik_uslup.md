# p-10 · Akademik Üslup (Authoring)

> Tezgah: **Authoring · yazar** (4.x)
> Sycophant kilidi · sessiz öğrenme defteri · "tut + buda" modu (akademize değil).

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:1719-1791`
- **Sidebar:** `PaperMind_mock_v1.0.html:622`
- **Bu md:** `Page_Design/Sayfa_Plani_v1/W_atolye_authoring/p-10_akademik_uslup.md`

## ROL
"Yapay zekâ sesi" gerçek bir koku verir; akademize ederken kullanıcının **kendi sesini** bozmaz, sadece üslup-disiplini uygular. Üst-ses (LLM) bastırılır; alt-ses (kullanıcı tarzı) korunur. **Sycophant kilidi:** AI 7 günde 10+ red alırsa otomatik kilitlenir, tarz önerisi 24h durur. **Sessiz öğrenme defteri:** kullanıcının kabul/red ettiği önerilerin 30g log'u — şeffaflık + KVKK uyumu.

## BACKEND ❌ YOK
Mock claims:
- `POST /api/authoring/style-suggest` `{paragraph, user_voice_profile}`
- `GET /api/authoring/sycophant-status?user_id=` (10/7g eşik)
- `GET /api/authoring/silent-ledger?days=30`

## DB ❌ YOK
- `fact_user_voice_profile` (passive %, hedge dağılımı, kelime yoğunluğu) — yok
- `fact_user_style_suggestion_log` (kabul/red + zamanlama → sycophant detection) — yok
- `mart_user_silent_ledger_30d` — yok

---

## ÖNERİ: Eksik Backend

### `0022_user_voice_style.sql`

```sql
-- fact_user_voice_profile — kullanıcı tarz fingerprint (yıllık güncel)
CREATE TABLE public.fact_user_voice_profile (
  user_id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  passive_pct      real CHECK (passive_pct BETWEEN 0 AND 1),
  hedge_consistency real CHECK (hedge_consistency BETWEEN 0 AND 1),
  jargon_density   real CHECK (jargon_density BETWEEN 0 AND 1),
  avg_sentence_len real,
  preferred_register text  CHECK (preferred_register IN ('formal','semi_formal','assertive')),
  -- "sen yumuşatma istemiyorsun" gibi öğrenilen tercihler
  learned_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
  -- {"yumusatma":"reject","passive_to_active":"mixed","epistemik_hedge":"keep"}
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- fact_user_style_suggestion_log — her öneri/karar log (sycophant detection)
CREATE TABLE public.fact_user_style_suggestion_log (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id      uuid REFERENCES public.projects(id) ON DELETE SET NULL,
  paragraph_text  text NOT NULL,
  suggestion_text text NOT NULL,
  suggestion_type text NOT NULL,  -- 'passive_to_active','remove_filler','hedge_swap',...
  user_decision   text NOT NULL CHECK (user_decision IN ('accept','reject','ignore')),
  reject_reason   text,           -- 'yumuşatma','tarz değişikliği','anlam kayması'
  decided_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_style_log_user_recent
  ON public.fact_user_style_suggestion_log (user_id, decided_at DESC);

-- mart_user_silent_ledger_30d — kullanıcı tarafından öğrenilen patern özet (30g)
CREATE MATERIALIZED VIEW public.mart_user_silent_ledger_30d AS
SELECT
  user_id,
  suggestion_type,
  COUNT(*) FILTER (WHERE user_decision = 'accept') AS accept_count,
  COUNT(*) FILTER (WHERE user_decision = 'reject') AS reject_count,
  COUNT(*) AS total,
  array_agg(DISTINCT reject_reason) FILTER (WHERE reject_reason IS NOT NULL) AS reject_reasons
FROM public.fact_user_style_suggestion_log
WHERE decided_at >= now() - interval '30 days'
GROUP BY user_id, suggestion_type;

-- Sycophant lock state (UI gerçek-zamanlı)
CREATE TABLE public.user_sycophant_lock (
  user_id       uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  status        text NOT NULL DEFAULT 'green'
                CHECK (status IN ('green','yellow','red','locked')),
  reject_count_7d int NOT NULL DEFAULT 0,
  accept_count_7d int NOT NULL DEFAULT 0,
  locked_until  timestamptz,  -- 24h auto-lock
  last_checked  timestamptz NOT NULL DEFAULT now()
);
```

### Yeni endpoint'ler

#### `POST /api/authoring/style-suggest`
- **In:** `{user_id, paragraph_idx, sentence:str, project_id}`
- **Out:**
  ```json
  {
    "original": "Bizim çalışmamız ... gerçekten doğru bir şekilde ölçmüştür.",
    "suggestion": "Bu çalışma ... ölçmüştür.",
    "delta_metrics": {
      "passive_delta": 0,
      "filler_removed": ["gerçekten","doğru bir şekilde"],
      "hedge_added": [],
      "epistemic_neutral": true
    },
    "suggestion_type": "remove_filler",
    "lock_status": "green"  // sycophant lock kontrolü
  }
  ```
- **Flow:**
  1. Sycophant lock check (`user_sycophant_lock.status`) — `locked` ise 423 dön (öneri durdu)
  2. `fact_user_voice_profile` fetch (`learned_preferences` jsonb)
  3. **LLM Gemini Flash 2.0** prompt: "tut + buda" mode — passive %, hedge tutarlığı, filler removal. **Anti-yumuşatma:** `learned_preferences.yumusatma == "reject"` ise yumuşatma önerme.
  4. Suggestion + delta metrics dön

#### `POST /api/authoring/style-decide`
- **In:** `{suggestion_log_id, decision:'accept'|'reject'|'ignore', reject_reason?}`
- **Out:** updated row + sycophant lock güncel durumu
- **Flow:**
  1. `fact_user_style_suggestion_log` insert/update
  2. Sycophant detection: 7g window, reject_count >= 10 → `user_sycophant_lock.status='red'` + `locked_until = now() + 24h`
  3. Voice profile güncelleme (incremental): kabul edilen tarz delta'ları → `fact_user_voice_profile`

#### `GET /api/authoring/sycophant-status?user_id=`
- **Out:** `{status:'green', reject_7d:2, accept_7d:14, ratio:0.13}`
- 7g window aggregate

#### `GET /api/authoring/silent-ledger?user_id=&days=30`
- **Out:** `mart_user_silent_ledger_30d` row'ları formatlı:
  ```json
  [
    {"pattern":"\"gerçekten / aslında\" → kaldır", "count":12, "decision":"accept"},
    {"pattern":"passive → active", "count":14, "decision":"mixed", "ratio":"8/14"},
    {"pattern":"\"ihmal edilmiş\" → \"sınırlı kalmış\"", "count":3, "decision":"reject",
     "note":"yumuşatma istemiyorsun"},
    {"pattern":"epistemik hedge (\"muhtemelen\")", "count":9, "decision":"keep"}
  ]
  ```

---

## SAYFA YAPISI (ASCII)

```
┌── 10 · Akademik Üslup ── sycophant kilidi · sessiz öğrenme ───────────┐
│ Felsefe: AI sesi koku verir; "tut + buda", "akademize" değil.         │
│ Üst-ses bastırılır, alt-ses (kullanıcı) korunur.                      │
│                                                                        │
│ ┌── Simülasyon · stil + sycophant şeffaflığı (paragraf 4/12) ────┐    │
│ │ D ✓ ─ C ✓ ─ G ✓ ─ A ● ─ S   r-ESTRA tarafsız 0.69 ↑.08         │    │
│ │                                                                  │    │
│ │ ┌── editör ───────────────────┐ ┌── 🔓 Sycophant lock · YEŞİL ─┐│    │
│ │ │ Asıl cümle (kullanıcı)      │ │ Son 7g · 2 red / 14 kabul    ││    │
│ │ │ "Bizim çalışmamız ihmal     │ │ → sağlıklı oran. Kilit aktif ││    │
│ │ │  edilmiş olan ... gerçekten │ │ değil.                       ││    │
│ │ │  doğru bir şekilde ölçtü."  │ ├──────────────────────────────┤│    │
│ │ │                             │ │ Sessiz öğrenme defteri · 30g ││    │
│ │ │ Tut + buda (önerilen)       │ │ • "gerçekten/aslında" → kal- ││    │
│ │ │ "Bu çalışma ... pasif       │ │   dır (12 kabul)             ││    │
│ │ │  sensör yaklaşımıyla        │ │ • passive → active (8/14)    ││    │
│ │ │  ergenlerde uyku gecikmesi- │ │ • "ihmal" → "sınırlı" (3 RED ││    │
│ │ │  ni ölçmüştür."             │ │   — yumuşatma istemiyorsun)  ││    │
│ │ │                             │ │ • epistemik hedge → koru (9) ││    │
│ │ │ [Kabul] [Red (yumuşatma)]   │ │ → 30g öğrenmesi: tarafsızlık ││    │
│ │ │                             │ │   + güçlü iddia + jargon     ││    │
│ │ │ Δ passive 0% · hedge yok    │ │   yumuşatma yok              ││    │
│ │ └─────────────────────────────┘ └──────────────────────────────┘│    │
│ │                                                                  │    │
│ │ ┌──────┬─────────────┬──────────────┬─────────────────┐         │    │
│ │ │passive│hedge tutarl.│jargon yoğun. │ cümle uzunluğu │         │    │
│ │ │ 14% 🟢│  0.81 🟢    │  0.62 🟡     │  19 kel 🟢     │         │    │
│ │ └──────┴─────────────┴──────────────┴─────────────────┘         │    │
│ └──────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front
- **Sol editör:** Asıl cümle (üstte, mono small-caps başlık) + Tut+buda önerisi (italik) + 2 buton (Kabul authoring amber / Red beyaz)
- **Sağ üst:** Sycophant lock gösterge — yeşil/sarı/kırmızı blok + 7g sayaç (`#dcfce7` yeşil bg / `#fffbeb` sarı / `#fef2f2` kırmızı)
- **Sağ alt:** Sessiz öğrenme defteri 30g — bullet list, red'leri kırmızı renkle vurgula
- **Alt 4-grid metrik şeridi:** passive % / hedge tutarlığı / jargon yoğunluğu / cümle uzunluğu — her hücre renkli emoji
- **r-ESTRA tarafsız ekseni** burada en aktif (mock canlı δ gösterir)

### Back (öneri)
1. Paragraf seçilir → `POST /style-suggest` → öneri + lock status
2. Kullanıcı kabul/red → `POST /style-decide` → log + lock güncel
3. Sayfa mount → paralel: `GET /sycophant-status` + `GET /silent-ledger?days=30`
4. Lock = `red`/`locked` ise editör read-only banner + 24h countdown

### Sycophant detection algoritması
```python
# Her style-decide call'da:
window_start = now() - 7*24h
recent = SELECT user_decision FROM fact_user_style_suggestion_log
         WHERE user_id = :uid AND decided_at >= window_start
reject_count = sum(1 for d in recent if d == 'reject')
accept_count = sum(1 for d in recent if d == 'accept')

if reject_count >= 10 and reject_count / max(reject_count + accept_count, 1) > 0.4:
    UPDATE user_sycophant_lock SET status='locked',
           locked_until = now() + interval '24 hours'
elif reject_count >= 5:
    status = 'red'
elif reject_count >= 3:
    status = 'yellow'
else:
    status = 'green'
```

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon / Öğrenci:** kapalı
- **Araştırmacı:** açık. Lock + ledger şeffaflık herkese açık (Authoring tier'larında)
- **Profesyonel:** Gemini 2.5 Pro → daha hassas tarz önerisi (kullanıcı sesi daha iyi tutulur)
- **KVKK:** Sessiz öğrenme defteri kullanıcıya görünür → şeffaflık + silme hakkı (`DELETE /api/authoring/silent-ledger?user_id=` → log + voice_profile reset)

---

## AÇIK SORULAR
1. **Sycophant eşiği 10/7g** mock canon — karar B-NNN var mı?
2. **`learned_preferences` jsonb şema kararı:** anahtar listesi ne (yumusatma, passive_to_active, epistemik_hedge, ...)? Sabit enum mu, açık mı?
3. **Voice profile cold start:** yeni kullanıcı default değerleri ne? (passive_pct=0.5, hedge_consistency=null, ...)
4. **"Tut + buda" prompt mühendisliği:** LLM nasıl emin olur kullanıcı sesini bozmaz? Few-shot example bankası gerekli.
5. **Multi-language:** TR/EN/ID — passive %/hedge metrikleri dile göre farklı tanımlanmalı. Voice profile dile göre ayrışsın mı?
6. **Lock unlock:** 24h sonra otomatik mi, kullanıcı manuel mi açar? Mock'ta açık değil.
7. **r-ESTRA tarafsız boyutu** ile voice_profile.preferred_register ilişkisi: tarafsız=`formal_neutral` mı?

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar Authoring p-10 | `PaperMind_mock_v1.0.html` | 622 |
| 2 | p-10 page block | `PaperMind_mock_v1.0.html` | 1719-1791 |
| 3 | techspec endpoint | `PaperMind_mock_v1.0.html` | 1725-1731 |
| 4 | Asıl cümle + Tut+buda | `PaperMind_mock_v1.0.html` | 1745-1755 |
| 5 | Sycophant lock yeşil blok | `PaperMind_mock_v1.0.html` | 1758-1761 |
| 6 | Sessiz öğrenme defteri 30g | `PaperMind_mock_v1.0.html` | 1762-1771 |
| 7 | 4-metrik şerit (passive/hedge/jargon/uzunluk) | `PaperMind_mock_v1.0.html` | 1775-1788 |
| 8 | api/routes/ — authoring* yok | `api/routes/` (ls) | — |
