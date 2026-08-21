# Celery Worker Birleşik Setup — Ortak Servis Notu (B Grubu, 2026-04-30)

> **Statü**: TASLAK — Council 19. tur (B Grubu)
> **Bağlam**: F3c summarize_task (P017-P020) + F3d enrichment_task (P029) **aynı Celery app + Redis broker** üzerinde çalışır — tek setup, iki task; ayrı queue + ayrı worker pool
> **Owner**: Sercan (impl + Render service config)

---

## §0 Bağlam (3 cümle)

F3c P017 + F3d P029 her ikisi de Celery + Redis broker pattern'i kullanıyor; **tek `celery_app.py` + tek worker container** içinde iki task farklı queue ile koşar — `summarize_q` (LLM-heavy, 30-60s/task, max concurrency 2) + `enrichment_q` (HTTP-bound OpenAlex, 10-30s/task, max concurrency 8). Render service üzerinde iki ayrı service yerine **tek worker service** (Dockerfile multi-stage + supervisor) maliyet tasarrufu + deploy basitliği. Niş: ortak Celery app içinde priority routing + retry policy + dead-letter queue + Sentry breadcrumb tek yerden gelir.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| Tek `celery_app.py` + iki task module (F3c P017 + F3d P029 ortak) | DRY + master §11.4 | `api/workers/celery_app.py` |
| Redis broker namespace ayrımı: `celery_summarize_q` + `celery_enrichment_q` (cache `q:` + `sum:` + `enrich:` ile çakışmaz) | DM-006 + master §1 | broker URL aynı, queue ayrı |
| Worker concurrency: summarize_q `--concurrency=2` (LLM HF Endpoint TGI rate limit dostu) + enrichment_q `--concurrency=8` (HTTP I/O-bound) | F3c §1 + F3d §1 | `--queues=summarize_q,enrichment_q` |
| Retry policy: `autoretry_for=(LLMUnavailable, RateLimitExceeded)` + `retry_backoff=True` + `retry_backoff_max=60` + `max_retries=3` | F3c §1 + F3d §1 | task base class |
| Task time limit: summarize_q 90s soft + 120s hard (LLM 60s + buffer); enrichment_q 60s soft + 90s hard | F3c §3 + F3d §3 | `time_limit` config |
| Dead-letter queue: `celery_dlq` — retries exhausted task'lar buraya düşer; cron 1×/gün audit + Sentry alert | F1' §6.5 monitoring | DLQ exchange |
| Result backend: Redis aynı URL (TTL 24h) — task status polling buradan okur | F3c §3 P023 + F3d §3 P028 | `CELERY_RESULT_BACKEND=$REDIS_URL` |
| Worker container: tek Dockerfile + supervisor (api process + worker process aynı image; Render service tek) | DM-014 + master §11.4 | `deploy/Dockerfile` + `supervisord.conf` |
| Sentry breadcrumb: task_name + task_id + queue + retry_count + duration_ms | F1' monitoring | `Celery.task_prerun` + `task_postrun` signal |
| Celery flower (opsiyonel lokal monitoring): `celery -A api.workers.celery_app flower --port=5555` — prod'da Grafana panel kullanılır flower yerine | dev convenience | sadece lokal dev |

---

## §2 Celery app config

```python
# api/workers/celery_app.py
from celery import Celery
from kombu import Queue

app = Celery(
    "papermind",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=[
        "api.workers.tasks.summarize_task",   # F3c P020
        "api.workers.tasks.enrichment_task",  # F3d P029
    ],
)

app.conf.update(
    task_queues=(
        Queue("summarize_q", routing_key="summarize.#"),
        Queue("enrichment_q", routing_key="enrichment.#"),
        Queue("celery_dlq", routing_key="dlq.#"),
    ),
    task_default_queue="summarize_q",  # explicit routing_key gerekir
    task_routes={
        "summarize.*": {"queue": "summarize_q"},
        "enrichment.*": {"queue": "enrichment_q"},
    },
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=86400,  # 24h
    worker_prefetch_multiplier=1,  # LLM/HTTP heavy → fair distribution
    task_acks_late=True,            # crash retry
    task_reject_on_worker_lost=True,
)

# Sentry breadcrumb signals
@task_prerun.connect
def task_prerun_handler(task_id, task, **kwargs):
    sentry_sdk.add_breadcrumb(category="celery", message=f"start {task.name}", data={"task_id": task_id, "queue": task.queue})

@task_failure.connect
def task_failure_handler(task_id, exception, **kwargs):
    sentry_sdk.capture_exception(exception)
```

---

## §3 İki task ortak base + ayrı module

```python
# api/workers/tasks/_base.py (ortak)
from celery import Task

class FaithfulTask(Task):
    autoretry_for = (LLMUnavailable, RateLimitExceeded, ConnectionError)
    retry_backoff = True
    retry_backoff_max = 60
    max_retries = 3
    soft_time_limit = 90
    time_limit = 120


# api/workers/tasks/summarize_task.py (F3c P020)
@app.task(base=FaithfulTask, name="summarize.run", bind=True, queue="summarize_q")
def summarize_task(self, paper_id: str, mode: str = "detailed", user_id: str = None):
    # Qwen draft → Claude rötuş → LVR validator → cache
    ...


# api/workers/tasks/enrichment_task.py (F3d P029)
@app.task(base=FaithfulTask, name="enrichment.run", bind=True, queue="enrichment_q")
def enrichment_task(self, ghost_id: str, depth: int = 1, user_id: str = None):
    # OpenAlex polite pool → ghost_curator → write-back
    # Kısa time limit override
    self.soft_time_limit = 60
    self.time_limit = 90
    ...
```

---

## §4 Verification

```bash
# S1: Worker boot smoke
celery -A api.workers.celery_app worker --queues=summarize_q,enrichment_q --concurrency=2 --loglevel=info
# Beklenen: log "celery@hostname ready" + 2 queue listed

# S2: Task enqueue + execute
python -c "from api.workers.tasks.summarize_task import summarize_task; r = summarize_task.delay('W123', 'detailed'); print(r.id, r.status)"
# Beklenen: task_id + status PENDING → STARTED → SUCCESS (~25-30s)

# S3: Queue routing
celery -A api.workers.celery_app inspect active_queues
# Beklenen: 2 queue (summarize_q + enrichment_q) worker'a kayıtlı

# S4: Retry + DLQ smoke
# Mock LLMUnavailable raise → 3 retry exponential → DLQ
celery -A api.workers.celery_app inspect stats | grep dlq
# Beklenen: celery_dlq routing'de 1+ message (retry exhausted)

# S5: Time limit
# Mock 130s sleep → SoftTimeLimitExceeded sonra TimeLimitExceeded
# Beklenen: 90s'de soft warning + 120s'de hard kill + Sentry capture
```

---

## §5 Critical files

### Backend touch
- `api/workers/celery_app.py` (yeni, ~80 LOC) — F3c P017'de skeleton; F3d P029'da reuse
- `api/workers/tasks/_base.py` (yeni, ~30 LOC) — `FaithfulTask` ortak base
- `api/workers/tasks/summarize_task.py` (F3c P020)
- `api/workers/tasks/enrichment_task.py` (F3d P029)

### Deploy touch
- `deploy/Dockerfile` (multi-stage api + worker tek image)
- `deploy/supervisord.conf` (api uvicorn + celery worker iki process)
- `deploy/render.yaml` (tek service iki process — `web` for api + `worker` for celery; aynı image, farklı startCommand)

### Tests touch
- `tests/unit/test_celery_routing.py` (queue routing + retry)
- `tests/integration/test_summarize_celery.py` (F3c S3)
- `tests/integration/test_enrichment_celery.py` (F3d S2)

---

## §6 TODO(sercan)

- [ ] Render service: tek service `api-worker` + 2 startCommand (`uvicorn` ve `celery worker`); env var REDIS_URL ortak
- [ ] Redis Upstash plan: F3c summarize 5 detailed/saat × 5 user × 2 hafta = 350 task; F3d enrichment 50 ghost/saat = ~16K task; Upstash free tier (10K req/gün) yeterli pilot için, prod ölçek Faz 2
- [ ] Celery flower lokal dev (opsiyonel, prod'da Grafana panel)
- [ ] DLQ audit cron 1×/gün → Sentry alert eğer >0
- [ ] Sentry signal bağlama (task_prerun + task_failure)

---

## §Council — R13 19. tur (Celery Setup, 2026-04-30)

| # | Üye | Verdict | Gerekçe |
|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | ✅ GREEN | Celery + Redis broker pattern F3c §1 + F3d §1 ile uyumlu; queue routing standart Celery API; `acks_late` + `reject_on_worker_lost` doğru pattern |
| 2 | **Akademik İsabet** | ✅ GREEN | Task type ayrımı (LLM-heavy vs HTTP-bound) concurrency optimizasyonu doğru; akademik kalite kontrolü `FaithfulTask` base ile entegre |
| 3 | **Fayda-Maliyet Hakemi** | ✅ GREEN | Tek service iki process Render maliyet 2× yerine 1× (tasarruf $7-15/ay); kod ~110 LOC tek modül |
| 4 | **Daha İyisi Var Mı?** | ⚠️ YELLOW | 2026'da **Dramatiq** (Celery'den modern, async-first, daha az config) veya **Arq** (Python asyncio-native, hafif) alternatif var; ama Celery ekosistem büyük + Render dokümantasyon mevcut + flower mature | İstiyor: §1'e "Celery tercih gerekçesi: ekosistem büyük + Render integration mature + flower monitoring + retry/DLQ pattern hazır; Faz 2 Dramatiq async-first değerlendirilir" eklensin |
| 5 | **Global Çözüm Mühendisi** | ✅ GREEN | Tek Redis broker + tek worker service tüm endpoint'lere hizmet; lokasyon Render eu region (KVKK uyum); UTC timezone global standart |
| 6 | **Son Kullanıcı Avukatı** | ✅ GREEN | Polling pattern frontend'de transparent (F6 P056/P060); task time limit makul (kullanıcı 30-60s bekleme dürüst pozisyonlama) |

**Karar (R13.5)**: 5 GREEN + 1 YELLOW; düzeltme:
- §1'e Celery tercih gerekçesi eklendi: "Celery: ekosistem mature + Render integration + flower + retry/DLQ pattern hazır; Faz 2 Dramatiq/Arq async-first değerlendirilir"

---

**Final commitment**: Bu setup F3c P017 (Celery skeleton) sprint'inde implementasyon; F3d P029'da sadece task module eklenir, Celery app reuse. Sercan tek service deploy + Render config 1 günde tamam.
