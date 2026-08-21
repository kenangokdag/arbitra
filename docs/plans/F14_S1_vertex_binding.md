# F14-S1 — Vertex AI (Gemini) Binding + Provider Toggle (Plan Manifest)

> Handoff `docs/ARBITRA_HANDOFF.md` "Kalan adımlar §1" → litellm'i Gemini API-key'den **Vertex AI**'ye bağla.
> Master: `docs/plans/F14_hakemlik_master.md`. Kanıt seviyeleri: A = bu oturumda Read/grep ile gördüm · B = doc/handoff'ta yazılı · C = doğrulayamadım.

---

## §0 — AMAÇ (3 cümle)
ARBITRA'nın LLM çağrıları şu an `gemini/gemini-2.5-flash` (Gemini API key) üzerinden gidiyor; bunu Omer'in Google Cloud kredileriyle çalışan **Vertex AI** sağlayıcısına taşıyacağız. Kod (LLMService/Router/alias'lar) **değişmez**; sadece `config/litellm_models.yaml` `litellm_params` + bir provider toggle + credential bağlama değişir. Vertex hazır değilken sistem mevcut Gemini-key yoluna **kırılmadan** düşebilmeli (fail-safe toggle).

## §1 — MEVCUT DURUM (kanıt A — bu oturumda Read)
- **Chokepoint:** `api/services/litellm_router.py:42-53` `get_router()` → yaml `model_list` okur, `${VAR}` env substitution yapar (`_substitute_env`, satır 28-39), `litellm.router.Router(model_list=...)` döndürür. Tüm çağrılar `acompletion()` (satır 56-57) üzerinden. **(A)**
- **Alias resolve:** `api/services/llm_service.py:150-156` `_model_for_tier` → `flash`→`gemini-flash-tr`, `pro`→`gemini-pro-tiebreak`. Bu alias'lar **korunacak** (kod dokunulmaz). **(A)**
- **yaml mevcut:** `config/litellm_models.yaml` — 4 model (`gemini-flash-tr/en/id`, `gemini-pro-tiebreak`), hepsi `model: gemini/gemini-2.5-*` + `api_key: ${GEMINI_API_KEY}`. **(A)**
- **config.py:** `api/config.py:81-82` `GEMINI_API_KEY`, `GEMINI_FLASH_MODEL`, satır 99-100 `LITELLM_TIMEOUT_SECONDS`, `LITELLM_CONFIG_PATH`. Vertex ayarı **yok**. **(A)**
- **deps:** `pyproject.toml:27` `litellm>=1.50,<2.0`, satır 42 `google-auth>=2.30,<3.0` (Vertex ADC/SA için zaten eklenmiş). **(A)**
- **litellm Vertex param adları (Context7 doğrulaması, B):** `model: vertex_ai/<model>`, `vertex_ai_project` / `vertex_ai_location` (alias: `vertex_project`/`vertex_location`); location ayrıca `VERTEXAI_LOCATION`/`VERTEX_LOCATION` env'den okunur. SA kimliği ADC ile (`GOOGLE_APPLICATION_CREDENTIALS`) veya `vertex_credentials` param ile verilir.

## §2 — BLOKERLER (Omer aksiyonu — kod ilerlemeden çözülmeli)
- **BLOKER-1 (Omer / GCP konsol):** SA `arbitra-vertex@translate-500019.iam.gserviceaccount.com`'a IAM'de **`roles/aiplatform.user`** verilmeli. Handoff §1: çağrı şu an **403 `aiplatform.endpoints.predict`**. Bu rol olmadan canlı doğrulama imkansız. **(B)**
- **BLOKER-2 (key dosyası eksik — bu oturumda kanıtlandı, A):** Handoff `Desktop/keys/translate-500019-*.json` diyor ama `/Users/omer/Desktop/keys/` içinde **bu dosya YOK**. Mevcut: `lacuna-vertex-sa.json` (**0 byte, boş**) ve `vertex_oauth.json` (327 byte, OAuth client olabilir — SA key değil). **ARBITRA'nın Vertex SA JSON'u temin edilmeli** (GCP konsol → SA → Keys → JSON indir → `Desktop/keys/`'e koy). **(A)**
- İki bloker de **Omer-kararı/manuel**; kod tarafı (S-adımları) bunlar çözülünce uygulanır. Kod-yazımı yapılabilir parçaları aşağıda; canlı doğrulama blokerlere bağlı.

## §3 — KARARLAR
- **DM-VTX-1 — ADC tercih:** Credential, yaml'a gömülmez (sızıntı yasağı). `GOOGLE_APPLICATION_CREDENTIALS=<SA json path>` env ile ADC kullanılır; google-auth otomatik alır. (Alternatif `vertex_credentials` param'ı yaml'a yol yazar — reddedildi: yol/secret yaml'da görünür, global değil.)
- **DM-VTX-2 — Provider toggle (fail-safe):** `LLM_PROVIDER` env (`vertex` | `gemini`, default `gemini`). yaml tek dosya kalır; `litellm_router.py` provider'a göre `model`/credential alanlarını override eder VEYA iki yaml profili. **Seçim:** tek yaml + router-side override (yaml duplikasyonu yok, drift yok). Vertex hazır değilse `gemini`'de kalır, sistem kırılmaz.
- **DM-VTX-3 — Alias dokunulmaz:** `gemini-flash-tr/en/id`, `gemini-pro-tiebreak` adları sabit; `_model_for_tier` değişmez. Sadece resolve hedefi değişir.
- **DM-VTX-4 — Bölge:** `vertex_ai_location` = `europe-west4` (handoff önerisi), `vertex_ai_project` = `translate-500019`. Config'den (env) gelir, hardcode değil.

## §4 — SCOPE & ATOMİK COMMIT HARİTASI
| # | Commit | Dosya | İçerik | Bloker'a bağlı? |
|---|---|---|---|---|
| S1a | `feat(F14-S1): vertex config settings` | `api/config.py` | `LLM_PROVIDER`, `VERTEX_PROJECT`, `VERTEX_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` alanları (default'lar güvenli: provider=`gemini`) | Hayır (yazılabilir) |
| S1b | `feat(F14-S1): router vertex resolve` | `api/services/litellm_router.py` | `get_router()`: `LLM_PROVIDER==vertex` ise model_list'i `vertex_ai/...` + `vertex_ai_project/location`'a map et, `api_key` alanını düş | Hayır (yazılabilir) |
| S1c | `chore(F14-S1): env.example + yaml comment` | `.env.example`, `config/litellm_models.yaml` | yeni env'ler + yaml'a provider-toggle açıklaması (yaml model satırları aynen kalır) | Hayır |
| S1d | `test(F14-S1): vertex router unit` | `tests/...` | toggle=vertex iken model_list `vertex_ai/`'ye map oluyor + project/location set + api_key yok; toggle=gemini iken eski davranış (regresyon) — **canlı çağrı YOK, mock** | Hayır |
| S1e | (commit değil) **canlı doğrulama** | — | SA → token → gerçek `generateContent` → "krediden indi" teyidi | **EVET (BLOKER-1+2)** |

## §5 — UYGULAMA YETKİSİ
- S1a–S1d: kod + mock test, bloker'sız — onay sonrası otonom uygulanır.
- S1e (canlı smoke): BLOKER-1 (IAM rol) + BLOKER-2 (SA key dosyası) çözülmeden **yapılamaz** → `OPEN_WORK`'e park, Omer çözünce koşulur.

## §6 — TEST / DoD
- `tests/` yeni unit: `LLM_PROVIDER=vertex` → resolve edilen model_list'te `model` `vertex_ai/gemini-2.5-flash`, `vertex_ai_project=translate-500019`, `vertex_ai_location=europe-west4`, `api_key` anahtarı **yok**. `LLM_PROVIDER=gemini` → eski `gemini/...`+`api_key` korunur (regresyon guard).
- `uv run pytest` tüm mevcut 68 test PASS kalmalı (kırma yok).
- `ruff check` temiz, FE etkilenmez (`tsc` koşulmaz — sadece backend).
- **Canlı DoD (S1e, bloker sonrası):** gerçek Vertex çağrısı 200 döner + GCP faturada kredi düşüşü gözlenir. Doğrulanana kadar "Vertex çalışıyor" denmez (itiraf protokolü).

## §7 — AÇIK SORULAR (Omer)
1. **BLOKER-2 — SA key dosyasını sağlar mısın?** GCP → IAM → SA `arbitra-vertex@translate-500019` → Keys → Add Key (JSON) → `Desktop/keys/`'e koy. (Veya: ADC yerine `gcloud auth application-default login` ile kişisel ADC — ama prod/Railway için SA JSON gerekir.)
2. **BLOKER-1 — `roles/aiplatform.user`** SA'ya verildi mi? (403 bunu işaret ediyor.)
3. **Bölge** `europe-west4` onaylı mı, yoksa `us-central1` mı? (Gemini 2.5 Flash bölge erişilebilirliği bölgeye göre değişir — C, doğrulanmalı.)

## §8 — RİSK
- R-A: `vertex_ai_location`'da `gemini-2.5-flash` mevcut olmayabilir → 404. Mitigasyon: S1e'de bölge teyidi, gerekirse `us-central1`.
- R-B: litellm `<2.0` Vertex param adı sürümle değişebilir → S1b implement öncesi kurulu sürümde `python -c "import litellm; print(litellm.version)"` + param teyidi (ezberden değil).
- R-C: Railway prod'da SA JSON dosya yolu yok → orada `GOOGLE_APPLICATION_CREDENTIALS` yerine JSON içeriğini env'e koyup geçici dosyaya yazma gerekebilir (deploy adımının işi, S1 scope dışı — `OPEN_WORK`'e not).

## §9 — REFERANS
- Chokepoint: `api/services/litellm_router.py` · `api/services/llm_service.py:150-156` · `api/config.py:81-100`
- yaml: `config/litellm_models.yaml` · F8 plan §9.1 (`docs/plans/F8_llm_provider_unification.md:269`)
- Handoff: `docs/ARBITRA_HANDOFF.md` §"Kalan adımlar 1" · Master §13 O-1
