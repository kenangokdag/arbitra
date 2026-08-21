# F8 — LLM Provider Unification (Gemini 2.5) + Page-Aware Advisor Layer

> **Statü:** TASLAK — Omer onayı bekleniyor (2026-05-03)
> **Üst plan:** F1 master_plan §LLM_layer + Council 17 §post-MVP unification
> **Şablon:** ARCHITECT_PROMPT_TEMPLATE §0..§18
> **Owner:** Omer (frontend wiring + .env + deploy) · Sercan (backend services + tests)
> **Sprint LOC tahmini:** ~600–800 (refactor + advisor layer + 3 pilot ROLE_MODULE)
> **Sprint süre tahmini:** 1.5–2 gün

---

## §0 — Bağlam (3 cümle)

Sistem 3 farklı LLM erişim katmanına bölünmüş: `chat.py` direkt Gemini SDK (✅ aktif), `presenter.py` OpenAI gpt-4o-mini via litellm (❌ pahalı), `listener.py` Qwen HF endpoint (❌ cold-start + ek ücret) — F8 bu üçünü tek **Gemini 2.5 Flash + Pro** provider'ına birleştirir, LiteLLM tek abstraction haline gelir, OpenAI + Qwen tamamen kaldırılır. İkinci eksen: kullanıcı her sayfada "Danışmana Sor" butonuna bastığında, advisor LLM o sayfanın amacını + kullanıcının proje state'ini deterministik bilir — F8 **PageContext + ProjectContext injection layer**'ı kurar (3 pilot sayfa modülü; kalan 12 modül F9'a). Niş ayrım: rakipler stateless query-respond; PaperMind = state-driven advisor → "metod sayfasında alakasız öneri" sorunu deterministik kapanır.

---

## §1 — Hedef

F8 = **Tek LLM provider + page-aware advisor altyapısı.**

1. **Provider unification** — chat + listener + presenter → tek Gemini 2.5 (Flash default, Pro tiebreaker)
2. **LiteLLM tek abstraction** — `litellm.acompletion` her yerde; chat.py direkt SDK kullanımı kaldırılır
3. **`LLMService` katmanı** — `api/services/llm_service.py` yeni dosya: provider-agnostic, model routing, retry, structured output, ProjectContext + PageContext otomatik injection
4. **3 pilot ROLE_MODULE** — `topic_exploration`, `method_selection`, `gap_heatmap` (en sık kullanılacaklar)
5. **OpenAI + Qwen tamamen sil** — `OpenAIListener`, `QwenListener` class'ları, `OPENAI_API_KEY` env, `gpt-mini-*` litellm entry'leri, HF endpoint config

---

## §2 — Kapsam

**IN (F8):**

| Slice | İş | Dosya |
|---|---|---|
| **A** | LiteLLM config + .env + deploy env swap | `config/litellm_models.yaml`, `.env.example`, `deploy/render.yaml`, `deploy/docker-compose.yml`, `api/config.py` |
| **B** | `LLMService` skeleton + `ProjectContext` + `PageContext` model'leri | `api/services/llm_service.py` (yeni), `api/models/llm.py` (yeni) |
| **C** | Listener refactor: `Listener` ABC + `GeminiListener` (Qwen + OpenAI sınıfları silinir) | `api/services/listener.py` |
| **D** | Presenter refactor: gpt-mini → Gemini Flash, litellm path korunur | `api/services/presenter.py` |
| **E** | Chat refactor: direkt Gemini SDK → `LLMService` çağrısı; `mode` field → ROLE_MODULE registry | `api/routes/chat.py` |
| **F** | 3 pilot ROLE_MODULE brief'i + AdvisorButton frontend skeleton | `api/services/role_modules/` (yeni dizin), `web/src/components/AdvisorButton.tsx` (yeni) |
| **G** | Tests: smoke (`scripts/smoke_external_services.py`), unit (`tests/unit/test_llm_service.py`), integration (chat + listener + presenter) | tests/ + scripts/ |

**OUT (F9 sonraya ertelendi):**

- Reviewer pipeline (Mod A + B + JuryMind tiebreaker) — F8'de sadece interface; gerçek implementasyon F9
- Kalan 12 ROLE_MODULE (`gap_profile`, `concept_network`, ..., `step_assessment`)
- Embedding model swap (HF E5-large kalır — ML pipeline, LLM değil)
- Reranker swap (BGE kalır — ML pipeline)
- Conversation memory layer (DM-LLM-9 reddedildi — kalıcı out-of-scope)

**OUT (kapsam dışı):**

- Frontend page-by-page AdvisorButton bağlama (F4-S4 ChatboxPanel zaten kapalı; F8'de sadece `<AdvisorButton>` shared component yazılır, 15 sayfaya enjekte F9-S2)
- Embedding compute migration (F2 phase3 warehouse mirror'da)
- F6 listener regression — F8 bu sorunu **otomatik çözer** (GeminiListener doğdukça search.py:33 import'u GeminiListener'a değişir)

---

## §3 — Önkoşullar + Envanter

**Mevcut state (kanıtlı):**

| Komponent | Konum | Durum | Provider |
|---|---|---|---|
| Chatbox endpoint | `api/routes/chat.py` | ✅ Aktif (working tree handover prep) | Gemini 2.5 Flash (direkt SDK) |
| Presenter | `api/services/presenter.py` | ✅ Aktif | OpenAI gpt-4o-mini via litellm |
| Listener | `api/services/listener.py` | ❌ HEAD'de OpenAIListener YOK (F6 regression); working tree'de var ama kullanmıyoruz | Qwen HF (yazılı, kullanılmadı) + OpenAI (working tree, F8'de silinecek) |
| LiteLLM router | `config/litellm_models.yaml` | ✅ Aktif | gpt-4o-mini × 3 dil + gpt-4o tiebreaker |
| Frontend ChatboxPanel | `web/src/components/ChatboxPanel.tsx` | ✅ KAPANDI 2026-05-01 (F4-S4) | UI hazır, mode field var |
| `<ChatThread>` shared | `web/src/components/` | ✅ F4-S4'te yazıldı | Reuse hazır |

**Engelleyici yok:**
- chat.py'deki Gemini implementation handover prep'in parçası, working tree'de mevcut
- LiteLLM Gemini desteği `litellm>=1.50` ile native (pyproject.toml uyumlu)
- F4-S4 frontend `mode` field'ı backend'in ROLE_MODULE registry'siyle 1:1 eşlenir

**Bağımlılıklar:**

- F8 başlamadan önce **F6 fix iptal kararı** (DM-LLM-10): F6'da OpenAIListener'ı geri koymuyoruz, F8'de doğrudan GeminiListener yazıyoruz; ara çözüm yok.
- F5-S2 (FieldPicker UI) F8 ile bağımsız çalışır — ayrı PR'larda paralel ilerleyebilir.

---

## §4 — Karar günlüğü (DM-LLM-1..10)

| # | Karar | Why | Etki |
|---|---|---|---|
| **DM-LLM-1** | Tek provider Gemini 2.5; OpenAI + Qwen kaldırılır | Maliyet ~%55 düşüş, tek API key, tek hata yüzeyi | `litellm_models.yaml` baştan yazılır |
| **DM-LLM-2** | 2 model katmanı: Flash default + Pro sadece JuryMind tiebreaker | Flash listener/narrator/advisor için yeterli; Pro pahalı, disagreement <5% | `LLMService.call(tier="flash"\|"pro")` |
| **DM-LLM-3** | Tek abstraction LiteLLM; chat.py refactor (direkt SDK → `litellm.acompletion`) | Provider swap yaml'da biter, kod stabil; tek hata yüzeyi | `chat.py` ~80 satır refactor |
| **DM-LLM-4** | ProjectContext otomatik injection (Supabase'den çekilir, prompt'a sokulur) | Cross-step coherence: konu seçildi → metod sayfasında alakasız öneri olmaz | `LLMService` her çağrıda project_id alır |
| **DM-LLM-5** | Conversation memory **reddedildi** | Token explosion + halüsinasyon amplifikasyonu + state-driven daha temiz | Out-of-scope kalıcı |
| **DM-LLM-6** | Reviewer (Mod A/B + tiebreaker) F8'de sadece interface; gerçek implementasyon F9 | F8 zaten 7 slice; reviewer ayrı complexity | F8 kapsamı temiz |
| **DM-LLM-7** | PageContext layer = `mode` field reuse + ROLE_MODULE[mode] registry | F4-S4 frontend zaten `mode` gönderiyor; pattern hazır | Backend'de ROLE_MODULE dosyaları |
| **DM-LLM-8** | `<AdvisorButton mode pageState>` shared component; F8'de sadece component yazılır, 15 sayfaya enjekte F9-S2 | DRY; tek-yerden değişiklik kolay | Frontend tek dosya |
| **DM-LLM-9** | Stateless advisor: her çağrı bağımsız, sadece ProjectContext + PageContext + tek mesaj | DM-LLM-5 ile tutarlı; Redis cache zaten 1h aynı (msg+session+lang+mode) hash'ine sahip | Memory layer yok |
| **DM-LLM-10** | F6 listener regression F8'de doğrudan GeminiListener ile çözülür; OpenAIListener restore yapılmaz | Kısa vadede 15 dk fix vs 2 saat sonra silme = boşa iş | F6 task #14 → F8 kapsamına alınır |

---

## §5 — Atomik commit boundary

| # | Commit | Kapsam | Slice | Dosya sayısı |
|---|---|---|---|---|
| 1 | `chore(config): swap litellm_models to Gemini 2.5 Flash + Pro` | yaml + .env + config.py | A | 3 |
| 2 | `feat(api): LLMService + ProjectContext + PageContext` | yeni servis + model | B | 2 |
| 3 | `refactor(api): GeminiListener via LiteLLM (Qwen + OpenAI sınıfları silindi)` | listener.py | C | 1 |
| 4 | `refactor(api): Presenter Gemini Flash (gpt-mini kaldırıldı)` | presenter.py | D | 1 |
| 5 | `refactor(api): chat route via LLMService (direkt SDK kaldırıldı)` | chat.py | E | 1 |
| 6 | `feat(api): 3 pilot ROLE_MODULE (topic/method/gap_heatmap)` | role_modules/ | F | 3 |
| 7 | `feat(web): AdvisorButton shared component` | AdvisorButton.tsx | F | 1 |
| 8 | `chore(deploy): env var swap OPENAI → GEMINI` | render.yaml + docker-compose.yml | A | 2 |
| 9 | `test(api): LLMService + listener + chat + presenter` | tests/ | G | 4 |
| 10 | `chore: smoke external services Gemini` | smoke script | G | 1 |

**Commit boundary kuralları:**
- Her commit bağımsız test geçer (TestClient boot + import path)
- Slice C (listener) Slice B (LLMService) tamamlanmadan başlamaz (sıralı)
- Slice F (ROLE_MODULE) Slice E (chat refactor) tamamlanmadan başlamaz
- Diğer slice'lar paralel commitable

---

## §6 — Mimari katman + kod yapısı

```
api/
├── services/
│   ├── llm_service.py        ← YENİ (Slice B)
│   │   class LLMService:
│   │     async def call(
│   │       prompt: str,
│   │       tier: Literal["flash","pro"] = "flash",
│   │       mode: str = "default",          ← ROLE_MODULE seçimi
│   │       project_id: str | None = None,  ← ProjectContext fetch
│   │       page_state: dict | None = None,
│   │       structured_output_schema: type[BaseModel] | None = None,
│   │     ) -> LLMResponse
│   │
│   ├── role_modules/         ← YENİ (Slice F)
│   │   ├── __init__.py       (registry: ROLE_MODULES dict)
│   │   ├── base.py           (RoleModule class)
│   │   ├── topic_exploration.py
│   │   ├── method_selection.py
│   │   └── gap_heatmap.py
│   │
│   ├── listener.py           ← REFACTOR (Slice C)
│   │   class Listener(ABC)            # korunur
│   │   class GeminiListener(Listener) # YENİ — LLMService kullanır
│   │   __all__ = ["Listener", "GeminiListener"]
│   │   # OpenAIListener + QwenListener SİLİNDİ
│   │
│   ├── presenter.py          ← REFACTOR (Slice D)
│   │   model: gpt-4o-mini → gemini-flash (litellm yaml swap yeter)
│   │
│   └── (curator, faithfulness_gate, anchor, reranker — DOKUNULMADI)
│
├── models/
│   └── llm.py                ← YENİ (Slice B)
│       class ProjectContext (BaseModel, frozen=True)
│       class PageContext    (BaseModel, frozen=True)
│       class LLMResponse    (BaseModel, frozen=True)
│
├── routes/
│   ├── chat.py               ← REFACTOR (Slice E)
│   │   POST /api/chat → LLMService.call(mode=req.mode, ...)
│   │
│   └── search.py             ← OTOMATIK FIX
│       satır 33: Listener, GeminiListener (OpenAIListener silindi)
│
└── config.py                 ← REFACTOR (Slice A)
    GEMINI_API_KEY: str
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    # OPENAI_API_KEY + OPENAI_MODEL + ... SİLİNDİ
```

---

## §7 — Schema + sözleşme

### §7.1 ProjectContext (Pydantic v2, frozen)

```python
class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    user_id: str
    topic: str | None = Field(default=None, max_length=500)
    hypothesis: str | None = Field(default=None, max_length=1000)
    selected_method: str | None = None
    corpus_filter: dict[str, Any] | None = None
    last_decisions: list[str] = Field(default_factory=list, max_length=5)
    # last_decisions = son 5 karar özeti (örn. "metod=panel_data", "year>=2018")
```

### §7.2 PageContext

```python
class PageContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str  # ROLE_MODULE registry key
    page_state: dict[str, Any] | None = None
```

### §7.3 ROLE_MODULE base

```python
class RoleModule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str
    page_purpose: str        # "Bu sayfa: kullanıcı tezi için metod seçiyor."
    visible_data_template: str  # "Sayfada görünen: 13 sinyal scorecard + 3 öneri"
    advisor_role: str         # "Senin işin: topic+hipoteze uygun metodu öner."
```

### §7.4 LLMService.call sözleşmesi

```python
async def call(
    prompt: str,                                # user mesajı
    tier: Literal["flash","pro"] = "flash",
    mode: str = "default",
    project_ctx: ProjectContext | None = None,
    page_state: dict | None = None,
    structured_output_schema: type[BaseModel] | None = None,
) -> LLMResponse:
    """
    System prompt = BASE_PERSONA
                  + ROLE_MODULES[mode].render()
                  + (ProjectContext'i prompt'a serialize et)
                  + (PageState'i prompt'a serialize et)
    """
```

---

## §8 — Test stratejisi

| Test | Slice | Tip | Kanıt |
|---|---|---|---|
| `test_llm_service_call_flash` | B | unit | Mock litellm, struct output validate |
| `test_llm_service_project_context_injection` | B | unit | ProjectContext system prompt'ta görünür |
| `test_llm_service_page_state_injection` | B | unit | page_state JSON serialize, prompt'ta |
| `test_llm_service_structured_output` | B | unit | Pydantic schema strict mode parse |
| `test_listener_gemini_subqueries` | C | unit | "ML in healthcare" → 3-5 alt sorgu list[str] |
| `test_listener_invalid_json_retry` | C | unit | İlk fail → temperature=0 retry; ikinci fail → HTTPException |
| `test_chat_route_advisor_mode` | E | integration | POST /api/chat with mode=method_selection → ROLE_MODULE injected |
| `test_chat_route_no_project_id` | E | integration | project_id null → ProjectContext injection skip, no error |
| `test_presenter_gemini_flash` | D | unit | signals_13 + citations → 1-2 cümle TR/EN |
| `smoke_external_services_gemini` | A | smoke | Gemini API canary call (2 sn timeout) |
| `test_search_route_uses_gemini_listener` | C | integration | TestClient boot ✓, /api/search 200 |
| `test_no_openai_imports_remain` | A | static | grep -r "openai\|OpenAI" = 0 dosya |

**DoD:**
- Onboarding tests 13/13 PASS (F6 dolaylı çözüldü)
- Yeni LLM tests yazılan: minimum 12, hepsi PASS
- Smoke external services Gemini canary 200 OK
- `grep -r "openai\|gpt-4o\|qwen\|QwenListener\|OpenAIListener"` zero matches

---

## §9 — Konfigürasyon migration

### §9.1 `config/litellm_models.yaml` (full rewrite)

```yaml
# F8 Gemini 2.5 unified provider (DM-LLM-1)

model_list:
  - model_name: gemini-flash-tr
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: ${GEMINI_API_KEY}
      max_tokens: 600
      temperature: 0.2

  - model_name: gemini-flash-en
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: ${GEMINI_API_KEY}
      max_tokens: 600
      temperature: 0.2

  - model_name: gemini-flash-id
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: ${GEMINI_API_KEY}
      max_tokens: 600
      temperature: 0.2

  - model_name: gemini-pro-tiebreak
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: ${GEMINI_API_KEY}
      max_tokens: 800
      temperature: 0.1

router_settings:
  PRESENTER_TR_MODEL: gemini-flash-tr
  PRESENTER_EN_MODEL: gemini-flash-en
  PRESENTER_ID_MODEL: gemini-flash-id
  LISTENER_MODEL: gemini-flash-en
  CHAT_ADVISOR_MODEL: gemini-flash-tr
  TIEBREAK_MODEL: gemini-pro-tiebreak
```

### §9.2 `.env.example` swap

```diff
- # ===== OpenAI LLM (dil katmanı — B42-052) =====
- OPENAI_API_KEY=
- OPENAI_MODEL=gpt-4o-mini
- OPENAI_TIEBREAK_MODEL=gpt-4o
+ # ===== Gemini LLM (F8 unified — DM-LLM-1) =====
+ GEMINI_API_KEY=
+ GEMINI_FLASH_MODEL=gemini-2.5-flash
+ GEMINI_PRO_MODEL=gemini-2.5-pro
- # ===== Qwen HF (KALDIRILDI F8 — cold-start + ek ücret) =====
- # HF_LISTENER_ENDPOINT=
- # HF_TOKEN=
```

### §9.3 `deploy/render.yaml` + `deploy/docker-compose.yml`

`OPENAI_API_KEY` → `GEMINI_API_KEY` env var swap.

---

## §10 — Open Questions (kapatıldıktan sonra plan onayı)

| OQ | Soru | Default önerim |
|---|---|---|
| **OQ-A** | Gemini API key kullanıcı başına mı, sistem genelinde tek mi? | Tek sistem key (tüm kullanıcılar paylaşır) |
| **OQ-B** | ProjectContext fetch nasıl? Her LLM çağrısında DB query (latency +50ms) mi, frontend payload'a koyalım mı (trust but verify)? | Frontend payload — backend lightweight validate |
| **OQ-C** | LiteLLM Gemini structured output desteği — `response_format=json_schema` çalışıyor mu yoksa Outlines kullanmalı mıyız? | LiteLLM tool_calling deneriz; çalışmazsa Outlines fallback |
| **OQ-D** | Pilot 3 sayfa modülü hangisi? (önerim: topic_exploration, method_selection, gap_heatmap) | Önerim devam |
| **OQ-E** | F4-S4 ChatboxPanel `mode` field şu an default "genel" — bu mode'u "default" ROLE_MODULE'e mi map edelim, hata mı verelim? | "default" mode → BASE_PERSONA only, ROLE_MODULE skip |
| **OQ-F** | Presenter dil parametresi — Gemini Flash 3 dilde de aynı model kullanır, neden 3 entry? | 3 entry korunur (router_settings dil bazlı) |
| **OQ-G** | Reviewer interface F8'de yazılır mı, F9'a ertelenir mi? | F9'a (DM-LLM-6) |
| **OQ-H** | Frontend AdvisorButton 15 sayfaya F8'de mi enjekte edilir? | F9-S2 (component F8'de hazırlanır, mount sonra) |

---

## §11 — Maliyet projeksiyonu + observability

**Aylık baseline (100 aktif user × 50 query/ay = 5000 query):**

| Use case | Frekans | Tokens (in/out) | Cost/call | Aylık |
|---|---|---|---|---|
| Listener | 5000 | 200/200 | $0.0001 | $0.50 |
| Presenter | 5000 × 5 paper avg = 25000 | 800/100 | $0.0002 | $5.00 |
| Chat advisor | 5000 × 0.4 (40% query → advisor) = 2000 | 1000/300 | $0.0003 | $0.60 |
| Reviewer (F9) | 5000 × 0.2 = 1000 | 3000/500 | $0.0005 | $0.50 |
| Tiebreaker | 5000 × 0.05 = 250 | 4000/600 | $0.005 | $1.25 |
| **Toplam (F8 sonrası)** | | | | **~$8/ay** |
| **Toplam (mevcut OpenAI)** | | | | **~$22/ay** |

**Observability (Slice G):**
- LiteLLM `success_callback=["langfuse"]` ileride; F8'de stdout structured log yeter
- Sentry custom span: `llm.call` her çağrıda model + tokens + latency
- Maliyet metric: Prometheus counter `llm_tokens_total{model, tier, mode}` — F7 quality_deploy dashboard'a inject

---

## §12 — Acceptance Criteria (DoD)

| # | AC | Doğrulama |
|---|---|---|
| 1 | LiteLLM yaml sadece Gemini model'leri içerir | `grep -E "gpt|openai" config/litellm_models.yaml` = 0 |
| 2 | `.env.example` `OPENAI_API_KEY` içermez | grep |
| 3 | `OpenAIListener` + `QwenListener` class'ları silindi | `grep -rn "class.*Listener" api/` = 1 (`Listener` ABC) + 1 (`GeminiListener`) |
| 4 | `LLMService` çağrısı 100% LiteLLM'den geçer (direkt SDK YOK) | `grep -rn "google.generativeai\|openai\.\|anthropic\." api/` = 0 |
| 5 | ProjectContext otomatik prompt'a inject edilir (call has `project_id`) | `test_llm_service_project_context_injection` PASS |
| 6 | 3 pilot ROLE_MODULE çalışır (topic/method/gap_heatmap) | `test_chat_route_advisor_mode` 3 mode PASS |
| 7 | TestClient boot ERROR yok (F6 çözüldü) | onboarding 13/13 PASS |
| 8 | Smoke external Gemini canary 200 | `python scripts/smoke_external_services.py` exit 0 |
| 9 | Frontend AdvisorButton component yazıldı (mount edilmedi) | dosya var, type-check PASS |
| 10 | Aylık maliyet projeksiyonu güncellenir, DECISIONS.md'ye işlenir | `docs/DECISIONS.md` DM-LLM-1..10 girdi |

---

## §13 — Validation queries / smoke

### §13.1 Code grep audit (CI'da çalışacak)

```bash
# OpenAI sıfır olmalı
grep -rn "openai\|OpenAI\|gpt-4o\|gpt-mini" \
  --include="*.py" --include="*.yaml" --include="*.example" \
  --exclude-dir=.git --exclude-dir=.venv api/ config/ deploy/ .env.example scripts/

# Qwen sıfır olmalı
grep -rn "qwen\|Qwen\|HF_LISTENER\|hf_endpoint" \
  --include="*.py" --include="*.yaml" api/ config/

# Direct LLM SDK sıfır olmalı (LiteLLM dışında)
grep -rn "google.generativeai\|from openai\|from anthropic" \
  --include="*.py" api/
```

Beklenen: 3 query × 0 sonuç.

### §13.2 Runtime smoke (Slice G)

```bash
# 1. TestClient boot
pytest tests/unit/test_onboarding_route.py -k boot --tb=short

# 2. Gemini canary
GEMINI_API_KEY=... python scripts/smoke_external_services.py
# Beklenen: "✓ Gemini Flash canary 200 (lat=Xms)"

# 3. /api/search end-to-end
curl -X POST localhost:8000/api/search -d '{"query":"ML bias","k":5}'
# Beklenen: 200, 5 paper card with Gemini-narrated summary
```

### §13.3 Manuel "Danışmana Sor" testi

3 pilot sayfayı (curl) tetikle:

```bash
for mode in topic_exploration method_selection gap_heatmap; do
  curl -X POST localhost:8000/api/chat \
    -d "{\"message\":\"Yardım edin\",\"mode\":\"$mode\",\"page_state\":{}}"
done
```

Beklenen: 3 farklı response, her biri o sayfanın amacına spesifik.

---

## §14 — Rollback

**Senaryo: Gemini production'da hata veriyor (rate limit, key invalid, response timeout)**

**Hızlı rollback (5 dk):**
1. `config/litellm_models.yaml` git revert son commit
2. `.env`'de `OPENAI_API_KEY` geri ekle (yedek tutulur)
3. Eski OpenAI yaml ile redeploy

**Tam rollback (1 saat):**
- F8 PR revert
- `git revert <merge_sha>`
- Alternative: feature flag `LLM_PROVIDER=openai|gemini` (F8'de yapmıyoruz; gerekirse F9'da eklenir)

**Geri dönüş emniyeti:**
- F8 öncesi son commit SHA'sı: `e07e9e5` (PR #4 merge)
- Backup branch: `backup-local-main-2026-05-03` (zaten var)

---

## §15 — Branch + PR strategy

**Branch:** `f8-llm-provider-unification`

**Pre-flight (mecburi):**

```bash
git status -s | wc -l  # = 64 şu an (handover prep)
# F8 BRANCH AÇILMADAN ÖNCE: 64 dosyalık handover prep'i sıralı PR'lara böl
# F8 ile çakışan dosyalar: chat.py, listener.py, presenter.py, .env.example,
#                          config.py, litellm_models.yaml, search.py
```

**Çakışma çözümü 2 yol:**

**Yol 1 (önerilen):** Önce F8-relevant dosyaları main'e taşı (F8 öncesi PR), sonra F8 branch ondan üretilir.

```bash
git checkout -b f8-prep-cleanup main
git add api/services/listener.py api/routes/chat.py api/services/presenter.py
git commit -m "chore: stage handover prep for F8 unification"
# main'e merge et
# Sonra F8 branch yeni main'den
```

**Yol 2:** F8 branch'i şu anki working tree'den (handover prep dahil) aç, ama F8 commit'lerini sadece F8 dosyalarına sınırla.

```bash
git checkout -b f8-llm-provider-unification main
# working tree dosyaları korunur
git add -p api/services/listener.py  # sadece F8 değişikliklerini stage
```

**Karar (OQ-I):** Hangi yol? **Yol 2 önerim** — handover prep'i ayrı PR'lara bölmek 60+ dosya × ~10 PR = haftalık iş; F8 öncelikli.

**PR sırası:**

1. **PR #5: F8 Slice A** (config + .env) — küçük, hızlı review
2. **PR #6: F8 Slice B** (LLMService skeleton) — yeni dosya, izole
3. **PR #7: F8 Slice C+D+E** (listener + presenter + chat refactor) — bundle (3 service tutarlı bir arada)
4. **PR #8: F8 Slice F+G** (ROLE_MODULE + AdvisorButton + tests + smoke)

Veya **tek mega PR (F4-S4 precedent — 8 commit tek PR)** — Omer karar verecek.

---

## §16 — Compliance signals (executor brief uyum sinyali)

Executor (ayrı Claude Code session) brief'i okurken eski versiyon olmadığını grep'le doğrulasın:

- [ ] `config/litellm_models.yaml` rewrite'ında `gemini/gemini-2.5-flash` model satırı var mı?
- [ ] `api/services/llm_service.py` yeni dosya mı (HEAD'de yok)?
- [ ] `api/services/listener.py` rewrite'ında `class GeminiListener` var mı? `class OpenAIListener` YOK mu?
- [ ] `api/routes/chat.py` rewrite'ında `from api.services.llm_service import LLMService` var mı? `import google.generativeai` YOK mu?
- [ ] §13 grep audit komutları çalıştırılırsa 3 × 0 sonuç dönüyor mu?

Hayır = STOP, ana oturuma sor. Brief revize tarihi: 2026-05-03.

---

## §17 — Decisions log + References

**DM-LLM-1..10** yukarıda §4. Plan onayı sonrası bu DM'ler `docs/DECISIONS.md`'ye işlenir.

**Referans dosyalar:**

- `docs/plans/F4_S4_advisor_chatbox.md` — frontend ChatboxPanel canon (kapanmış)
- `config/litellm_models.yaml` — mevcut OpenAI yaml (F8'de rewrite)
- `api/routes/chat.py` (working tree) — Gemini SDK direkt kullanım (F8'de litellm'e geçirilecek)
- `api/services/listener.py` (working tree) — OpenAIListener (silinecek), Listener ABC korunacak
- `reference/COUNCIL_OTURUM_2026_05_01.md` — niş ayrım kararları
- Memory: `project_reviewer_pipeline.md` — Gemini 2.5 Flash precedent + ALAN_KURALLARI 6 alan

**Out-of-scope referansları:**

- F9 plan: 12 ROLE_MODULE + Reviewer pipeline + AdvisorButton mount — F8 kapandıktan sonra
- F2 phase3 warehouse mirror — embedding ML pipeline (LLM değil, kapsam dışı)

---

## §18 — Onay + sonraki adım

**Plan onayı için kontrol listesi (Omer):**

- [ ] §0 bağlam doğru mu? (3 farklı LLM erişim → tek Gemini)
- [ ] §2 IN/OUT kapsamı net mi? Reviewer F9'a ertelenir doğru mu?
- [ ] §4 DM-LLM-1..10 imzalanabilir mi?
- [ ] §10 OQ-A..H için default önerilerim onaylanır mı? Hayır ise hangisi farklı?
- [ ] §15 branch stratejisi: Yol 2 (working tree üstünde) vs Yol 1 (handover prep önce) — hangisi?

**Onay bekleniyor** → `Onaylıyorum, F8 başla` veya `Onaylıyorum ama OQ-X şöyle olsun`.

**Onay sonrası:**

1. `docs/DECISIONS.md`'ye DM-LLM-1..10 inline yazılır
2. F8 executor brief yazılır (`docs/plans/F8_PROMPT_executor_brief.md`)
3. Branch açılır, slice sırası uygulanır
4. PR'lar sırayla açılır

**Tahmin:** Plan onayından F8 merge'e ~36 saat (1.5 gün) Sercan tam zamanlı çalışırsa.
