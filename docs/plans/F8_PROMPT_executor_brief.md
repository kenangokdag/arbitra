# F8 EXECUTOR BRIEF — LLM Provider Unification (Gemini 2.5)

> **Revize:** 2026-05-03 — DM-LLM-1..10 onaylandı (DECISIONS.md DM-035..044)
> **Plan manifest:** `docs/plans/F8_llm_provider_unification.md` (§0..§18)
> **Hedef:** chat + listener + presenter → tek Gemini 2.5 (Flash + Pro); LiteLLM tek abstraction; 3 pilot ROLE_MODULE + AdvisorButton component
> **Sprint LOC:** ~600–800 · **Süre:** 1.5–2 gün
> **Branch:** `f8-llm-provider-unification` (worktree variant — ana repo dokunulmaz)
> **PR:** 4 ayrı (Slice A / B / C+D+E / F+G — S1A/S1B precedent)

---

## §0 — UYUM SİNYALİ (executor başlamadan önce grep'le doğrula)

Brief eski versiyon mu okuyorsun? Aşağıdaki 5 madde doğru çıkmalı; **hayır = STOP, ana oturuma sor**.

- [ ] **§A** Aşağıda `config/litellm_models.yaml` rewrite'ında `model: gemini/gemini-2.5-flash` satırı var mı?
- [ ] **§B** `api/services/llm_service.py` YENİ dosya mı (HEAD'de yok, brief'te skeleton var)?
- [ ] **§C** Brief `api/services/listener.py` rewrite'ında `class GeminiListener(Listener)` ve `__all__ = ["Listener", "GeminiListener"]` var mı? `class OpenAIListener` ve `class QwenListener` YOK mu?
- [ ] **§E** Brief `api/routes/chat.py` rewrite'ında (§6.1) `from api.services.llm_service import call as llm_call` var mı? `import google.generativeai` (yorum-dışı kod) YOK mu?
- [ ] **§9 DoD** §9 grep audit komutları (3 query) brief'te listeli mi, beklenen sonuç "3 × 0 satır" yazıyor mu?

5/5 ✓ → devam. Aksi halde **STOP** + ana oturum bilgilendir.

---

## §1 — PRE-FLIGHT (worktree variant — ana repo working tree DOKUNULMAZ)

**Mevcut state (brief yazımında doğrulandı):**

- Local main = origin/main = `e07e9e5` (PR #4 merge, F5-S1B v2 KAPANDI)
- `git status -s | wc -l` = 64 dosya (handover prep dirty, KORUNMALI)
- `git stash list` = boş

**Worktree açılışı (ana repo dokunulmaz, F8 ayrı dizinde):**

```bash
cd ~/Code/papermind-app

# State doğrulama (brief'le tutarlı mı?)
git rev-parse HEAD                          # = e07e9e5 olmalı
git status -s | wc -l                       # = 64 olmalı (HANDOVER PREP)
git stash list                              # = boş olmalı

# Worktree yarat — ana repo working tree dokunulmaz
git worktree add ../papermind-f8 -b f8-llm-provider-unification origin/main

# F8 dizinine geç
cd ../papermind-f8

# Verify: working tree boş, branch yeni
git status                                  # nothing to commit
git log -1 --oneline                        # = e07e9e5 ...
git branch --show-current                   # = f8-llm-provider-unification

# Python venv aktif et
source ~/.zshrc                             # veya conda activate
which python                                # papermind venv yolu
```

**Kanıtla devam:** `git status` boş + `git log -1` = `e07e9e5` görmedikçe Slice A'ya başlama.

---

## §2 — SLICE A: Config swap (Commit 1)

**Hedef:** OpenAI → Gemini config rewrite. 3 dosya değişir, tek commit.

### §2.1 `config/litellm_models.yaml` (full rewrite)

```yaml
# F8 Gemini 2.5 unified provider (DM-LLM-1)
# Plan: docs/plans/F8_llm_provider_unification.md §9.1

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

### §2.2 `.env.example` swap

Mevcut OpenAI bloğunu sil, Gemini bloğu ekle:

```diff
- # ===== OpenAI LLM (dil katmanı — B42-052) =====
- OPENAI_API_KEY=
- OPENAI_MODEL=gpt-4o-mini
- OPENAI_TIEBREAK_MODEL=gpt-4o
+ # ===== Gemini LLM (F8 unified — DM-LLM-1) =====
+ GEMINI_API_KEY=
+ GEMINI_FLASH_MODEL=gemini-2.5-flash
+ GEMINI_PRO_MODEL=gemini-2.5-pro
```

Qwen + HF bloğu (varsa) tamamen sil.

### §2.3 `api/config.py` Settings güncellemesi

Settings class'ından OpenAI alanlarını sil, Gemini alanları ekle:

```python
# SİL:
# OPENAI_API_KEY: str = ""
# OPENAI_MODEL: str = "gpt-4o-mini"
# OPENAI_TIEBREAK_MODEL: str = "gpt-4o"

# EKLE:
GEMINI_API_KEY: str = ""
GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
```

### §2.4 Slice A commit

```bash
git add config/litellm_models.yaml .env.example api/config.py
git status                                  # 3 dosya staged olmalı
git diff --cached                           # son okuma
git commit -m "chore(config): swap LiteLLM router to Gemini 2.5 (DM-LLM-1)

- gpt-4o-mini × 3 dil + gpt-4o tiebreak → gemini-2.5-flash × 3 + gemini-2.5-pro
- OPENAI_API_KEY/OPENAI_MODEL → GEMINI_API_KEY/GEMINI_FLASH_MODEL/GEMINI_PRO_MODEL
- Settings.OPENAI_* fields removed
- Plan: docs/plans/F8_llm_provider_unification.md §9.1
- Decision: DECISIONS.md DM-035 (F8 DM-LLM-1)"
```

---

## §3 — SLICE B: LLMService + Context modelleri (Commit 2)

**Hedef:** Provider-agnostic LLM çağrı katmanı + ProjectContext + PageContext + LLMResponse Pydantic modelleri.

### §3.1 `api/models/llm.py` (YENİ dosya)

```python
"""F8 LLM context + response models (DM-LLM-4 + DM-LLM-7).

ProjectContext = cross-step coherence için Supabase'den çekilen state.
PageContext = "Danışmana Sor" butonunun gönderdiği sayfa-spesifik state.
LLMResponse = LLMService dönüş tipi; structured_output_schema verilirse parsed_output set.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    user_id: str
    topic: str | None = Field(default=None, max_length=500)
    hypothesis: str | None = Field(default=None, max_length=1000)
    selected_method: str | None = Field(default=None, max_length=200)
    corpus_filter: dict[str, Any] | None = None
    last_decisions: list[str] = Field(default_factory=list, max_length=5)


class PageContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str = Field(min_length=1, max_length=80)
    page_state: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    parsed_output: BaseModel | None = None
    model_used: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
```

### §3.2 `api/services/llm_service.py` (YENİ dosya)

```python
"""F8 LLMService — provider-agnostic LLM çağrı katmanı (DM-LLM-3 + DM-LLM-4).

Mimari:
  call(prompt, tier, mode, project_ctx, page_state, structured_output_schema)
    ↓ build system prompt: BASE_PERSONA + ROLE_MODULES[mode] + ProjectContext + PageState
    ↓ litellm.acompletion(model_for_tier, messages, ...)
    ↓ structured_output parse (Pydantic) varsa
    ↓ LLMResponse

Tier routing:
  flash → router_settings.CHAT_ADVISOR_MODEL (Gemini Flash)
  pro   → router_settings.TIEBREAK_MODEL    (Gemini Pro)

HK-1 Pydantic forbid; HK-2 model_id config'den; HK-7 temperature seed.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

import litellm
from pydantic import BaseModel

from api.config import Settings, get_settings
from api.models.llm import LLMResponse, PageContext, ProjectContext

logger = logging.getLogger(__name__)

BASE_PERSONA = """Sen ALI — Adaptive Literature Intelligence danışmanısın.
Akademik araştırmacılara tez sürecinde rehberlik edersin.
Tarz: net, kanıt-odaklı, jargon yok, kullanıcının diline uyumlu.
Yasak: kanıtsız iddia, hatırlamadığın detayı uydurma, generic SaaS cevap.
"""

# ROLE_MODULE registry import — circular avoid için lazy
def _get_role_modules() -> dict[str, str]:
    from api.services.role_modules import ROLE_MODULES
    return ROLE_MODULES


class LLMServiceError(Exception):
    """LLM çağrı hatası."""


async def call(
    prompt: str,
    *,
    tier: Literal["flash", "pro"] = "flash",
    mode: str = "default",
    project_ctx: ProjectContext | None = None,
    page_state: dict[str, Any] | None = None,
    structured_output_schema: type[BaseModel] | None = None,
    settings: Settings | None = None,
) -> LLMResponse:
    """LLM çağrısı + ProjectContext + PageContext otomatik prompt injection."""
    settings = settings or get_settings()
    role_modules = _get_role_modules()

    system_parts = [BASE_PERSONA]

    role_brief = role_modules.get(mode)
    if role_brief is not None:
        system_parts.append(role_brief)

    if project_ctx is not None:
        system_parts.append(_serialize_project_ctx(project_ctx))

    if page_state is not None:
        system_parts.append(f"Sayfada şu an görünen veri: {page_state}")

    system_prompt = "\n\n".join(system_parts)

    model = _model_for_tier(tier)

    t0 = time.perf_counter()
    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            api_key=settings.GEMINI_API_KEY,
            temperature=0.2 if tier == "flash" else 0.1,
            max_tokens=600 if tier == "flash" else 800,
        )
    except Exception as e:
        logger.exception("LLM call failed")
        raise LLMServiceError(f"LLM çağrısı başarısız: {e}") from e

    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = response.choices[0].message.content
    parsed = None
    if structured_output_schema is not None:
        parsed = structured_output_schema.model_validate_json(text)

    return LLMResponse(
        text=text,
        parsed_output=parsed,
        model_used=model,
        tokens_in=response.usage.prompt_tokens,
        tokens_out=response.usage.completion_tokens,
        latency_ms=latency_ms,
    )


def _model_for_tier(tier: str) -> str:
    if tier == "flash":
        return "gemini-flash-tr"
    if tier == "pro":
        return "gemini-pro-tiebreak"
    raise ValueError(f"Unknown tier: {tier}")


def _serialize_project_ctx(ctx: ProjectContext) -> str:
    parts = [f"Proje bağlamı (project_id={ctx.project_id}):"]
    if ctx.topic:
        parts.append(f"  - Konu: {ctx.topic}")
    if ctx.hypothesis:
        parts.append(f"  - Hipotez: {ctx.hypothesis}")
    if ctx.selected_method:
        parts.append(f"  - Seçilen metod: {ctx.selected_method}")
    if ctx.corpus_filter:
        parts.append(f"  - Korpus filtresi: {ctx.corpus_filter}")
    if ctx.last_decisions:
        parts.append(f"  - Son 5 karar: {', '.join(ctx.last_decisions)}")
    parts.append("Önerilerin bu bağlamla çelişmesin.")
    return "\n".join(parts)
```

### §3.3 Slice B commit

```bash
git add api/models/llm.py api/services/llm_service.py
git commit -m "feat(api): LLMService + ProjectContext + PageContext (DM-LLM-3/4/7)

- LLMService.call() = LiteLLM tek abstraction; provider-agnostic
- ProjectContext = cross-step coherence (Supabase'den fetch, prompt'a inject)
- PageContext = mode + page_state (advisor sayfa-aware)
- BASE_PERSONA + ROLE_MODULES[mode] + project_ctx + page_state pipeline
- structured_output_schema desteği (Pydantic parse)
- Plan: docs/plans/F8_llm_provider_unification.md §6 + §7
- Decisions: DM-037 (LiteLLM tek), DM-038 (ProjectContext), DM-041 (mode reuse)"
```

---

## §4 — SLICE C: Listener refactor → GeminiListener (Commit 3)

**Hedef:** Mevcut `Listener` ABC korunur; `OpenAIListener` + `QwenListener` SİLİNİR; `GeminiListener` LLMService kullanır.

### §4.1 `api/services/listener.py` (rewrite)

```python
"""Listener — query rewrite + multi-query expansion (B42-045 §1, F8 DM-LLM-10).

F8 unification: OpenAI + Qwen sınıfları kaldırıldı; tek implementasyon GeminiListener.
GeminiListener LLMService üzerinden Gemini 2.5 Flash kullanır (yapısal JSON output).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from api.services.llm_service import LLMServiceError, call as llm_call

logger = logging.getLogger(__name__)


class _ListenerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sub_queries: list[str] = Field(min_length=3, max_length=5)


class Listener(ABC):
    @abstractmethod
    async def listen(self, query: str, *, lang: str = "en") -> list[str]:
        """Original query → 3-5 alt sorgu."""


class GeminiListener(Listener):
    """Gemini 2.5 Flash ile alt-sorgu üretimi (DM-LLM-1)."""

    PROMPT_TEMPLATE = (
        "Kullanıcı sorgusunu 3-5 alt sorguya genişlet. "
        "Her alt sorgu OpenAlex'te aranabilir, kısa, semantik anlamlı olmalı. "
        "Çıktı JSON: {{\"sub_queries\": [\"...\", ...]}}\n\n"
        "Dil: {lang}\nSorgu: {query}"
    )

    async def listen(self, query: str, *, lang: str = "en") -> list[str]:
        prompt = self.PROMPT_TEMPLATE.format(lang=lang, query=query)
        try:
            resp = await llm_call(
                prompt=prompt,
                tier="flash",
                mode="listener",
                structured_output_schema=_ListenerOutput,
            )
        except LLMServiceError:
            logger.warning("listener LLM call failed; fallback = [query]")
            return [query]

        if resp.parsed_output is None:
            logger.warning("listener parsed_output None; fallback = [query]")
            return [query]

        return resp.parsed_output.sub_queries


__all__ = ["Listener", "GeminiListener"]
```

### §4.2 `api/routes/search.py:33` import güncelle

```python
# ESKİ (kırık):
# from api.services.listener import Listener, OpenAIListener, QwenListener

# YENİ:
from api.services.listener import GeminiListener, Listener
```

Ayrıca search.py içinde `OpenAIListener()` veya `QwenListener()` instance'ı varsa `GeminiListener()` ile değiştir.

### §4.3 Slice C commit

```bash
git add api/services/listener.py api/routes/search.py
git commit -m "refactor(api): GeminiListener via LLMService — Qwen+OpenAI removed (DM-LLM-10)

- Listener ABC korundu (interface contract)
- OpenAIListener + QwenListener SİLİNDİ (Qwen HF cold-start + ek ücret; OpenAI maliyet)
- GeminiListener = LLMService.call(tier=flash, mode=listener, schema=_ListenerOutput)
- search.py:33 import OpenAIListener → GeminiListener (F6 regression auto-fix)
- Plan: §6 + §7.4
- Decision: DM-044 (F6 doğrudan F8'de çözülür)"
```

---

## §5 — SLICE D: Presenter refactor (Commit 4)

**Hedef:** Presenter mevcut LiteLLM call'ını kullanır; sadece model adı değişir (yaml'da gemini-flash'a swap edildi). Ek olarak: hard-coded `gpt-mini-*` referansları temizlenir.

### §5.1 `api/services/presenter.py` değişiklikler

- Header docstring'de "GPT-4o-mini" referansını "Gemini 2.5 Flash" ile değiştir.
- `model` parametresi config'den okunuyorsa (router_settings) DOKUNULMAZ — yaml swap yeter.
- Hard-coded `"gpt-mini-tr"` veya `"gpt-4o-mini"` string'i varsa router_settings env var ile değiştir (`PRESENTER_TR_MODEL` vb).
- Test fixture'ında `gpt-` referansı varsa `gemini-` olarak güncelle.

### §5.2 Slice D commit

```bash
git add api/services/presenter.py
git commit -m "refactor(api): Presenter Gemini 2.5 Flash (gpt-mini removed) (DM-LLM-1)

- Header + docstring güncel: GPT-4o-mini → Gemini 2.5 Flash
- Hard-coded model string'leri router_settings env var'a çekildi
- LiteLLM acompletion path korundu (yaml swap'la otomatik)
- Plan: §2 Slice D"
```

---

## §6 — SLICE E: Chat refactor → LLMService (Commit 5)

**Hedef:** `api/routes/chat.py` mevcut **direkt Gemini SDK** kullanımını LLMService'e geçir. `mode` field zaten var (F4-S4'ten); ROLE_MODULE registry üzerinden çalışır.

### §6.1 `api/routes/chat.py` rewrite (kritik bölüm)

Mevcut yapı: `import google.generativeai as genai` + `genai.GenerativeModel(...)`. Yeni:

```python
# SİL:
# import google.generativeai as genai
# model = genai.GenerativeModel(...)

# EKLE:
from api.services.llm_service import call as llm_call
from api.models.llm import ProjectContext

# Endpoint içi:
project_ctx = None
if req.project_id:
    project_ctx = await _fetch_project_context(req.project_id)

resp = await llm_call(
    prompt=req.message,
    tier="flash",
    mode=req.mode or "default",
    project_ctx=project_ctx,
    page_state=req.page_state,
)
return ChatResponse(message=resp.text, model_used=resp.model_used)
```

### §6.2 `_fetch_project_context` helper

```python
async def _fetch_project_context(project_id: str) -> ProjectContext | None:
    """Supabase'den project state çek. Yoksa None döndür."""
    # MVP basit: supabase_call_async ile project tablosundan oku
    # Şimdilik mock — gerçek Supabase project tablosu F9-S0'da yazılacak
    return None  # F9-S0'da implementasyon
```

### §6.3 `ChatRequest` model'ine `project_id` + `page_state` field ekle

`api/models/chat.py`:

```python
class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
    mode: str = "default"
    project_id: str | None = None  # F8 yeni
    page_state: dict[str, Any] | None = None  # F8 yeni
    # ... mevcut diğer alanlar
```

### §6.4 Slice E commit

```bash
git add api/routes/chat.py api/models/chat.py
git commit -m "refactor(api): chat route via LLMService (direct Gemini SDK removed) (DM-LLM-3)

- import google.generativeai → from api.services.llm_service import call
- mode field reuse → ROLE_MODULES[mode] auto-injection
- ChatRequest: project_id + page_state alanları eklendi
- _fetch_project_context skeleton (F9-S0'da Supabase fetch)
- Plan: §6 Slice E"
```

---

## §7 — SLICE F: 3 Pilot ROLE_MODULE + AdvisorButton (Commit 6 + 7)

### §7.1 `api/services/role_modules/__init__.py` (registry)

```python
"""F8 ROLE_MODULES registry (DM-LLM-7).

Pilot 3 mode (F8); kalan 12 mode F9-S2.
"""

from api.services.role_modules.topic_exploration import TOPIC_EXPLORATION_BRIEF
from api.services.role_modules.method_selection import METHOD_SELECTION_BRIEF
from api.services.role_modules.gap_heatmap import GAP_HEATMAP_BRIEF

ROLE_MODULES: dict[str, str] = {
    "topic_exploration": TOPIC_EXPLORATION_BRIEF,
    "method_selection": METHOD_SELECTION_BRIEF,
    "gap_heatmap": GAP_HEATMAP_BRIEF,
}

__all__ = ["ROLE_MODULES"]
```

### §7.2 3 ROLE_MODULE dosyası (her biri ~100 satır brief)

`api/services/role_modules/topic_exploration.py`:

```python
"""F8 pilot ROLE_MODULE: topic_exploration sayfası advisor brief'i."""

TOPIC_EXPLORATION_BRIEF = """
Sayfa: Topic Exploration — kullanıcı tezi için araştırma konusunu daraltıyor.

Bu sayfada görünen veri:
  - 3-5 önerilen konu kartı (gap-driven scoring ile)
  - Her kart: konu adı, son 5 yıl yayın trendi, 3-5 kritik gap
  - "Bu konuya odaklan" butonu (seçim → ProjectContext.topic update)

Senin işin (advisor):
  - Kullanıcı bir konu seçmek için tereddüt ediyorsa: gap density + literatür yoğunluğu trade-off'unu açıkla
  - Hipotez şekillendirmeye yardım et: "X konusuna odaklanırsan, hipotez Y/Z olabilir"
  - Eğer kullanıcı 2 konu arasında kararsızsa: rakip avantajlarını göster
  - Generic öneri yasak: kullanıcının gördüğü 3-5 konu dışına çıkma
"""
```

`api/services/role_modules/method_selection.py`:

```python
"""F8 pilot ROLE_MODULE: method_selection sayfası advisor brief'i."""

METHOD_SELECTION_BRIEF = """
Sayfa: Method Selection — kullanıcı tezi için araştırma yöntemi seçiyor.

Bu sayfada görünen veri:
  - 3 önerilen metod (topic + corpus + gap'a uygun)
  - Her metod: ad, kullanılan paper sayısı, etik kontrol noktaları
  - 13 sinyal scorecard (her metodun gücü/zayıflığı)

Senin işin (advisor):
  - Kullanıcı topic'iyle uyumlu metod öner (ProjectContext.topic kontrol et)
  - Etik konuları belirginleştir (insan deneği, veri gizliliği vb)
  - Eğer kullanıcı "deneysel" istiyor ama topic survey-only ise uyar
  - Generic öneri yasak: sadece gördüğü 3 metod arasında karar yardımı
"""
```

`api/services/role_modules/gap_heatmap.py`:

```python
"""F8 pilot ROLE_MODULE: gap_heatmap sayfası advisor brief'i."""

GAP_HEATMAP_BRIEF = """
Sayfa: Gap Heatmap — kullanıcı literatür boşluk haritasına bakıyor.

Bu sayfada görünen veri:
  - 11 gap tipinin × topic'in heatmap'i (renk = gap density)
  - Tıklanabilir hücreler → gap profile sayfasına geçiş
  - Filter: yıl aralığı, paper sayısı min, alt-alan

Senin işin (advisor):
  - Kullanıcı haritada hangi hücrenin önemli olduğunu sorarsa: density + recency birleşimini açıkla
  - "Bu gap araştırmaya değer mi?" sorusuna: scientometric kanıtla cevap (CD₅, beauty coef, ref_age)
  - Birden fazla gap arası karşılaştırma yardımı
  - Generic literatür özeti yasak: kullanıcının gördüğü heatmap'e bağlı kal
"""
```

### §7.3 Slice F commit (1)

```bash
git add api/services/role_modules/
git commit -m "feat(api): 3 pilot ROLE_MODULE briefs — topic/method/gap_heatmap (DM-LLM-7)

- registry: api/services/role_modules/__init__.py (ROLE_MODULES dict)
- topic_exploration: konu daraltma + hipotez şekillendirme
- method_selection: metod uygunluğu + etik kontrolü
- gap_heatmap: density + scientometric kanıt
- Kalan 12 ROLE_MODULE F9-S2'ye ertelendi
- Plan: §6 + §7.3"
```

### §7.4 Frontend `<AdvisorButton>` shared component

`web/src/components/AdvisorButton.tsx`:

```tsx
"use client";

import { useUiStore } from "@/lib/ui-store";

interface AdvisorButtonProps {
  mode: string;            // ROLE_MODULE registry key
  pageState?: Record<string, unknown>;
  label?: string;
}

export function AdvisorButton({ mode, pageState, label = "Danışmana Sor" }: AdvisorButtonProps) {
  const openChatbox = useUiStore((s) => s.openChatbox);

  return (
    <button
      type="button"
      onClick={() => openChatbox({ mode, pageState })}
      className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-50"
    >
      {label}
    </button>
  );
}
```

**Not:** F4-S4 ChatboxPanel zaten `useUiStore`'a sahip; `openChatbox({mode, pageState})` action'ı F4-S4 store'una eklenmesi gerekebilir — kontrol et + minimal extension yap.

### §7.5 Slice F commit (2)

```bash
git add web/src/components/AdvisorButton.tsx web/src/lib/ui-store.ts  # store değişti ise
git commit -m "feat(web): AdvisorButton shared component (DM-LLM-8)

- mode + pageState prop ile her sayfaya copy-paste enjekte edilebilir
- useUiStore.openChatbox({mode, pageState}) → F4-S4 ChatboxPanel açar
- 15 sayfa mount F9-S2 sprint'e ertelendi
- Plan: §6 + §7"
```

---

## §8 — SLICE G: Tests + smoke (Commit 8 + 9 + 10)

### §8.1 Unit testler (`tests/unit/test_llm_service.py`)

12 test minimum:

1. `test_llm_service_call_flash_basic`
2. `test_llm_service_call_pro_tiebreak`
3. `test_llm_service_project_context_injection`
4. `test_llm_service_page_state_injection`
5. `test_llm_service_structured_output_parse`
6. `test_llm_service_litellm_error_raises_LLMServiceError`
7. `test_listener_gemini_subqueries_3_to_5`
8. `test_listener_invalid_json_fallback_to_query`
9. `test_chat_route_advisor_mode_topic_exploration`
10. `test_chat_route_advisor_mode_method_selection`
11. `test_chat_route_advisor_mode_gap_heatmap`
12. `test_chat_route_no_project_id_skips_context_injection`

LiteLLM mock pattern:

```python
@pytest.fixture
def mock_litellm_completion(monkeypatch):
    async def fake(*args, **kwargs):
        class _Choice:
            class _Msg:
                content = '{"sub_queries":["a","b","c"]}'
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
            class _Usage:
                prompt_tokens = 100
                completion_tokens = 50
            usage = _Usage()
        return _Resp()
    monkeypatch.setattr("litellm.acompletion", fake)
```

### §8.2 Smoke external services (`scripts/smoke_external_services.py`)

OpenAI smoke kısmını sil, Gemini canary ekle:

```python
async def smoke_gemini():
    """Gemini Flash 2 sn timeout canary."""
    from api.services.llm_service import call
    try:
        resp = await asyncio.wait_for(
            call(prompt="ping", tier="flash"),
            timeout=2.0,
        )
        print(f"✓ Gemini Flash canary 200 (lat={resp.latency_ms}ms)")
    except Exception as e:
        print(f"✗ Gemini Flash canary FAIL: {e}")
        sys.exit(1)
```

### §8.3 Slice G commit'leri

```bash
# Commit 8: deploy env swap
git add deploy/render.yaml deploy/docker-compose.yml
git commit -m "chore(deploy): env var swap OPENAI_API_KEY → GEMINI_API_KEY"

# Commit 9: tests
git add tests/unit/test_llm_service.py tests/unit/test_listener.py tests/unit/test_chat_route_advisor.py
git commit -m "test(api): LLMService + GeminiListener + chat advisor mode (12 test)"

# Commit 10: smoke
git add scripts/smoke_external_services.py
git commit -m "chore(scripts): Gemini Flash canary smoke (OpenAI canary removed)"
```

---

## §9 — DoD checklist (PR açmadan önce executor'ın tamamlaması zorunlu)

- [ ] **Grep audit (3 query × 0 sonuç):**
  ```bash
  grep -rn "openai\|OpenAI\|gpt-4o\|gpt-mini" --include="*.py" --include="*.yaml" --include="*.example" --exclude-dir=.git api/ config/ deploy/ .env.example scripts/
  grep -rn "qwen\|Qwen\|HF_LISTENER\|hf_endpoint" --include="*.py" --include="*.yaml" api/ config/
  grep -rn "google.generativeai\|from openai\|from anthropic" --include="*.py" api/
  ```
- [ ] **TestClient boot:** `pytest tests/unit/test_onboarding_route.py -k boot` PASS (F6 dolaylı çözüldü)
- [ ] **Onboarding 13/13 PASS:** `pytest tests/unit/test_onboarding_route.py -v` 13/13
- [ ] **Yeni LLM testler:** `pytest tests/unit/test_llm_service.py tests/unit/test_listener.py tests/unit/test_chat_route_advisor.py -v` minimum 12/12 PASS
- [ ] **Smoke Gemini canary:** `GEMINI_API_KEY=... python scripts/smoke_external_services.py` exit 0
- [ ] **3 ROLE_MODULE manuel test:**
  ```bash
  for mode in topic_exploration method_selection gap_heatmap; do
    curl -sX POST localhost:8000/api/chat -d "{\"message\":\"ping\",\"mode\":\"$mode\"}" | jq .
  done
  ```
  3 farklı response (her biri sayfa-spesifik)
- [ ] **Type check:** `mypy api/` 0 hata
- [ ] **Lint:** `ruff check api/` 0 hata

---

## §10 — PR strategy: 4 ayrı PR (S1A/S1B precedent)

| PR # | Slice | Commit'ler | Kapsam |
|---|---|---|---|
| **PR #5** | A | 1 | config + .env + Settings (3 dosya) |
| **PR #6** | B | 2 | LLMService + models/llm.py (2 yeni dosya) |
| **PR #7** | C+D+E | 3, 4, 5 | listener + presenter + chat refactor (3 service consistent) |
| **PR #8** | F+G | 6, 7, 8, 9, 10 | ROLE_MODULES + AdvisorButton + tests + deploy + smoke |

**PR #5 sırası:**

```bash
git push -u origin f8-llm-provider-unification
gh pr create --title "F8 Slice A: LiteLLM Gemini 2.5 swap (DM-LLM-1)" \
  --body "$(cat <<'EOF'
## Summary
- LiteLLM router OpenAI → Gemini 2.5 Flash + Pro
- .env.example + Settings field swap

## Plan
docs/plans/F8_llm_provider_unification.md §2 Slice A

## DoD
- [ ] config/litellm_models.yaml grep "gpt" = 0
- [ ] .env.example grep "OPENAI" = 0
- [ ] api/config.py Settings.OPENAI_* removed

## Decisions applied
- DM-LLM-1 / DM-035 (DECISIONS.md)

## Test plan
- [ ] `python -c "from api.config import get_settings; s=get_settings(); print(s.GEMINI_API_KEY)"`

🤖 F8 LLM Unification
EOF
)"
```

PR #6, #7, #8 benzer şablonla — her biri kendi Slice'ını release notes'a yazar.

---

## §11 — Rollback (Plan §14)

**Hızlı rollback (PR #5 merged ama sonraki Slice'ler patladı):**

```bash
# F8 branch'i geri al
gh pr revert <pr_number>

# Veya: F8 branch'i sıfırdan başlat
git checkout main
git pull
git branch -D f8-llm-provider-unification
git worktree remove ../papermind-f8
git worktree add ../papermind-f8 -b f8-llm-provider-unification origin/main
```

**Tam rollback (F8 production'da hata):**
- Backup branch zaten var: `backup-local-main-2026-05-03`
- F8 PR'ları revert
- `.env`'ye `OPENAI_API_KEY` geri ekle (yedek tutulur)
- Eski `litellm_models.yaml` (gpt-mini) git revert
- Redeploy

---

## §12 — Executor → ana oturum sinyali (her Slice sonrası)

Slice tamamlandığında ana oturuma şu şablonla bildir:

```
Slice <X> tamamlandı. PR #<N>: <url>
Commit'ler: <sha1>, <sha2>...
DoD: <checklist madde madde geçti>
Engelleyici: <varsa>
Sonraki Slice'a geçiyorum.
```

PR review için ana oturum onayı bekle — F8 plan §15'te 4 PR sırası onaylı, ancak her PR review aşamasında ana oturum yorum yazabilir.

---

## §13 — Bitiş kriteri (F8 KAPANDI verdict)

F8 KAPANDI denilebilmesi için:

1. ✅ 4 PR merge edildi (rebase, atomic commit'ler korundu)
2. ✅ §9 DoD 7/7 PASS
3. ✅ Backend production'da Gemini canary 200
4. ✅ Onboarding tests 13/13 PASS
5. ✅ DECISIONS.md DM-035..044 aktif statüde
6. ✅ docs/STATE.md F8 KAPANDI olarak güncellendi
7. ✅ Ana oturum F8 closure verdict'ini yazdı

Sonra: F9 plan manifest açılır (12 ROLE_MODULE + Reviewer pipeline + AdvisorButton 15 sayfa mount).

---

**Brief sonu. Soru olursa STOP, ana oturuma yaz.**
