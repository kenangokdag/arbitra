# V1-S12 — Sesli Giriş + Sesli Dinlet (Web Speech + ElevenLabs TTS)

**Sub-sprint kodu:** V1-S12
**Önkoşullar:** V1-S11 PR (commit ön kuyruğunda; merge sonrası rebase main)
**Plan tarihi:** 2026-05-10
**Tek doğruluk kaynağı:** Bu manifest

---

## §0 — Amaç

`/q` vitrin sayfasında 2 sesli özellik:

1. **Sesli giriş:** mikrofona konuşan kullanıcı sorgu yazmadan arama yapsın
   (Web Speech API; tarayıcı native; $0 cost).
2. **Sesli dinlet:** literatür özeti üretildikten sonra "🔊 Dinle" butonu →
   ElevenLabs TTS ile özetin sesli versiyonu (özellikle mobil + görme desteği +
   "araba/yürüyüşte dinle" kullanım).

V1: **TR-only**. EN/ID dilleri V1.5'te (Omer 2026-05-10 onayı: "önce tr deneyelim,
güzelse diğerini").

---

## §1 — Mevcut durum (envanter)

- `web/src/app/(app)/q/page.tsx` — search input + ReviewPanel (V1-S10 + S11)
- `api/middleware/tier_gate.py:56-59` — QUOTA path-based dict (yeni endpoint
  eklenince satır eklenir)
- `api/config.py:52` — `GEMINI_API_KEY` env var pattern (ELEVENLABS aynı şekilde)
- `/Users/omer/youtube-bot/.env` — `ELEVENLABS_API_KEY` mevcut
- `/Users/omer/youtube-bot/config.py:14-16` — voice ID `xyqF3vGMQlPk3e7yA4DI`
  ("TR Voice 5 (Library)" — Omer'in seçtiği ses), model `eleven_multilingual_v2`
- ElevenLabs adapter PaperMind'da YOK — yeni servis

---

## §2 — Yeni davranış (KD-V1-S12-01..05)

### KD-V1-S12-01 — Sesli giriş = Web Speech API (browser native, $0)

`window.SpeechRecognition || window.webkitSpeechRecognition`. Hook
`useSpeechInput.ts`: `lang="tr-TR"`, `continuous=false`, `interimResults=false`.

Mic butonu search input'un yanında. Tıklayınca dinlemeye başlar; konuşma bittiğinde
text → `setQuery(text)` + auto-submit. Tarayıcı desteklemiyorsa (Firefox eski sürüm)
buton **gizlenir** (no error). Mobile Safari iOS 14.5+ destekler.

### KD-V1-S12-02 — TTS proxy backend (ElevenLabs API key gizli)

`POST /api/tts/literature-review` body: `{"content": str, "lang": "tr"}` →
`audio/mpeg` stream döner. Backend ElevenLabs'a proxy; **API key client'a sızmaz**.

ElevenLabs endpoint: `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
Body: `{"text": ..., "model_id": "eleven_multilingual_v2", "voice_settings":
{"stability": 0.5, "similarity_boost": 0.75}}`
Headers: `xi-api-key: <key>`, `Accept: audio/mpeg`

V1: TR-only — `lang` Literal["tr"] (EN/ID V1.5).

### KD-V1-S12-03 — TTS quota tier_gate üzerinden (ayrı counter YOK)

Path quota tablosuna eklenir: `"/api/tts/literature-review": {ANON: 1, AUTHED: 5}`.
Anon abuse'ı sınırla; authed bol ama sonsuz değil (cost: ~$0.10/özet).

Tekrar dinleme (replay) için **frontend audio blob cache** — kullanıcı "🔊 Dinle"
ye 2. kez tıklayınca backend çağırılmaz, blob URL'den oynatılır. Quota = "yeni audio
generate" sayısı.

### KD-V1-S12-04 — Frontend AudioPlayButton komponenti

`web/src/components/AudioPlayButton.tsx` props: `text: string`, `lang: "tr"`.
State: `isLoading`, `audioUrl: string | null`, `isPlaying`. Tıklama:
- audioUrl yoksa → `fetchTTS(text, lang)` → blob → `URL.createObjectURL` → set
- audioUrl varsa → `<audio>` element ref'inden play/pause toggle

ReviewPanel header'ında "Literatür İncelemesi" yazısının yanına eklenir.

### KD-V1-S12-05 — Cost guardrail: log + monitor

`api/services/elevenlabs_tts.py` her çağrıda log: char_count + tahmin cost
(~$0.30/1K char × multilingual_v2 = ~$0.0003/char). 400-kelime özet ≈ 2400 char ≈
$0.07. Anon limit=1/gün → max $0.07/anon/gün; authed limit=5 → $0.35/authed/gün
worst-case.

---

## §3 — Backend kontrat

```python
# api/models/tts.py — yeni
class TTSReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    content: str = Field(min_length=10, max_length=5000)
    lang: Literal["tr"] = "tr"  # V1: TR-only; EN/ID V1.5

# Response: streaming audio/mpeg (Pydantic model YOK; raw bytes)
```

Settings (env): `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`,
`ELEVENLABS_MODEL` (default `eleven_multilingual_v2`).

---

## §4 — Frontend kontrat

```typescript
// web/src/lib/tts-api.ts — yeni
export async function fetchTTS(
  content: string,
  lang: "tr",
  signal?: AbortSignal,
): Promise<Blob>;  // audio/mpeg blob

// web/src/hooks/useSpeechInput.ts — yeni
export function useSpeechInput(opts: {
  lang: string;
  onResult: (text: string) => void;
}): { isListening: boolean; isSupported: boolean; start: () => void; stop: () => void };
```

UI:
- Search input sağında **mic butonu** (Web Speech destekleniyorsa)
- ReviewPanel header'da **"🔊 Dinle"** butonu (özet üretildikten sonra görünür)

---

## §5 — Atomic commit boundary

| # | Commit | Dosya | LOC |
|---|---|---|---|
| V1-S12-01 | `feat(api): /api/tts/literature-review ElevenLabs proxy + quota` | `api/services/elevenlabs_tts.py` (yeni) + `api/routes/tts.py` (yeni) + `api/models/tts.py` (yeni) + `api/config.py` (env) + `tier_gate.py` QUOTA satırı + `api/main.py` router register + integration test | ~250 |
| V1-S12-02 | `feat(web): /q sesli giriş — Web Speech mic butonu` | `web/src/hooks/useSpeechInput.ts` (yeni) + test + `q/page.tsx` mic butonu | ~150 |
| V1-S12-03 | `feat(web): /q sesli dinlet — AudioPlayButton + tts-api adapter` | `web/src/lib/tts-api.ts` (yeni) + test + `web/src/components/AudioPlayButton.tsx` (yeni) + test + `q/page.tsx` ReviewPanel header'a entegre | ~200 |
| V1-S12-04 | `docs: V1 vitrin sprint manifest V1-S12 KAPANDI` | `docs/plans/V1_vitrin_sprint.md` (V1-S12 satır) | ~20 |

**Toplam:** ~620 yeni LOC.

---

## §6 — Test piramidi

| Katman | Dosya | Senaryo |
|---|---|---|
| Backend unit | `tests/unit/test_elevenlabs_tts.py` | (a) synthesize call → mock httpx → bytes döner, (b) HTTP 401 → ElevenLabsError, (c) char count log |
| Backend integration | `tests/integration/test_tts_routes.py` | (a) anon 1 TTS → 200 audio/mpeg, (b) anon 2. TTS → 429 quota, (c) authed 5 → 200, (d) içerik > 5000 char → 422, (e) ElevenLabs 5xx → 502 |
| Frontend hook | `web/src/hooks/useSpeechInput.test.ts` | (a) isSupported false (no SpeechRecognition) → start no-op, (b) onresult callback fired with transcript |
| Frontend component | `web/src/components/AudioPlayButton.test.tsx` | (a) ilk tık → fetchTTS çağırır, blob URL set, (b) 2. tık → cached blob, fetchTTS çağrılmaz, (c) loading state, (d) error state |
| Frontend adapter | `web/src/lib/tts-api.test.ts` | (a) snake body, (b) blob response döner |
| Manuel browser | `/q` | (a) mic → "transformer dikkat" konuş → input dolar + arama, (b) literatür özeti üret → 🔊 Dinle → ses çalar, (c) replay → cache (network tab'da yeni call yok) |

---

## §7 — Sınırlar (kapsam DIŞINDA)

- ❌ EN/ID dilleri (V1.5; sadece TR)
- ❌ Voice seçici UI (hardcoded Ahu/TR Voice 5)
- ❌ Server-side audio cache (Redis/S3) — frontend blob cache yeter V1
- ❌ Streaming TTS (chunk-by-chunk) — V1: tek seferde mp3
- ❌ Voice tone customization (stability/similarity slider)
- ❌ ConvAI tam ajan (V1.5+ pilot)
- ❌ Mic için server-side speech-to-text (Whisper) — Web Speech yeter
- ❌ Auto-play (kullanıcı butona basmalı; iOS auto-play yasağı)

---

## §8 — Riskler

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|---|---|---|---|
| 1 | Mobile Safari Web Speech tutarsız | Orta | Düşük | iOS 14.5+ destekler; desteklenmiyorsa buton gizlenir |
| 2 | ElevenLabs latency 3sn+ → UX yavaş | Düşük | Orta | Loading spinner + progress mesajı; cache replay anında |
| 3 | TTS abuse (anon X kez tetikler) | Düşük | Orta | tier_gate quota anon=1/gün; cost cap |
| 4 | TR ses akademik terim yanlış vurgu | Orta | Düşük | multilingual_v2 zaten TR optimize; manuel test sonucu karar |
| 5 | API key sızması | Düşük | Yüksek | Backend proxy; client'a key dökülmez; .env gitignore'da |

---

## §9 — DoD

- [ ] V1-S12-01: TTS endpoint + integration test (5 senaryo) PASS
- [ ] V1-S12-02: Web Speech hook + mic butonu + test PASS
- [ ] V1-S12-03: AudioPlayButton + tts-api adapter + test PASS
- [ ] V1-S12-04: sprint manifest §A V1-S12 KAPANDI satır
- [ ] tsc clean, vitest tüm suite PASS, pytest backend PASS, `npx next build` exit 0
- [ ] Manuel browser smoke (3 senaryo: mic / dinlet / replay cache)
- [ ] PR ayrı (V1-S11 merge sonrası rebase) + Omer browser onayı + squash merge

---

## §10 — Onay sinyali

Plan onaylandı sayılır:
- Omer "V1-S12 başla" der **veya** "direk uygula" der (2026-05-10 mesajı: ✓ alındı)

---

## §11 — Sıradaki adım (onay sonrası)

Branch `v1-s12-sesli-arama-ve-dinlet` (v1-s11-cift-dil-arama'dan), sıra:
V1-S12-01 backend → 02 mic → 03 dinlet → 04 docs.
