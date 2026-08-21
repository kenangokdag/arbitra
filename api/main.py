"""Arbitra v4 FastAPI application bootstrap (P001)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import Settings, get_settings
from api.db.redis_client import cache_health_probe
from api.middleware import AuthMiddleware, RateLimitMiddleware, init_sentry
from api.routes import (
    account_router,
    chat_router,
    completion_router,
    connected_papers_router,
    diary_router,
    dim_router,
    enrich_router,
    gap_heatmap_router,
    gap_profile_router,
    notes_router,
    onboarding_router,
    paper_detail_router,
    project_bibliometrics_router,
    project_graph_router,
    project_router,
    q_router,
    reading_list_router,
    research_area_router,
    review_router,
    search_router,
    summarize_router,
    theme_router,
    top5_router,
    tts_router,
    waitlist_router,
    workshop_router,
)

# 2026-08-15: uvicorn'un --log-level bayrağı SADECE uvicorn'un KENDİ logger'larını
# (uvicorn.access/uvicorn.error) yapılandırıyor — api/ ve engine/ genelinde
# kullanılan `logging.getLogger(__name__)` çağrıları hiçbir handler'a bağlı
# değildi, bu yüzden logger.info(...) seviyesindeki TÜM tanılama logları
# (örn. review_service.py'deki "verdict override llm=%s -> deterministic=%s"
# denetim izi) sessizce kayboluyordu — sadece WARNING+ Python'un "last resort"
# stderr handler'ı sayesinde görünüyordu. Saf gözlemsellik/tanılama düzeltmesi
# — iş mantığına dokunmuyor.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def _warm_bge(settings: Settings) -> None:
    """N-8: BGE-M3 query encoder + cross-encoder reranker preload.

    İlk gerçek `/api/search`'in ~33sn cold-start cezası boot'a kaydırılır.
    BGE_WARMUP_ENABLED=false (default) → atlanır; küçük instance/dev için.
    Hata yutmaz (warn'la geçer) — model yoksa yine de servis ayağa kalksın.
    """
    try:
        from api.routes.search import get_pool_router, get_reranker

        pool = get_pool_router()
        reranker = get_reranker()
        if hasattr(pool, "_encoder"):
            pool._encoder.encode(["warmup"])
        await reranker.rerank(
            candidates=["w-id"],
            query="warmup",
            top_k=1,
            candidate_texts={"w-id": "warmup"},
        )
        logger.info("BGE warm-up complete")
    except Exception as exc:
        logger.warning("BGE warm-up failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Lifespan: Sentry init + Redis health probe + (opsiyonel) BGE warm-up.

    cache_health_probe() Redis ulaşılmazsa _CACHE_DISABLED flag'ini set eder;
    cache_get/set istek başına spam yerine tek transition warn yazar.
    BGE_WARMUP_ENABLED set ise BGE-M3 + reranker boot'ta yüklenir (N-8).
    """
    settings = get_settings()
    init_sentry(settings)
    cache_health_probe()
    if settings.BGE_WARMUP_ENABLED:
        await _warm_bge(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    # SEC-1 / P01-T01·T04: production güvenlik ön-koşulları boot'ta doğrulanır.
    # Eksikse ProductionConfigError yükselir → uygulama AYAĞA KALKMAZ (fail-fast).
    from api.config_validation import validate_runtime_config

    validate_runtime_config(settings)
    app = FastAPI(
        title="Arbitra API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Middleware order (Starlette: last-added = outermost)
    # Stack: CORS → Auth → RateLimit → endpoint
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    if settings.APP_ENV == "production":
        cors_origins = [
            o.strip() for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()
        ]
    else:
        cors_origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "env": settings.APP_ENV,
        }

    app.include_router(search_router)
    app.include_router(chat_router)
    app.include_router(summarize_router)
    app.include_router(enrich_router)
    app.include_router(reading_list_router)
    app.include_router(onboarding_router)
    app.include_router(top5_router)
    app.include_router(paper_detail_router)
    app.include_router(project_router)
    app.include_router(project_bibliometrics_router)
    app.include_router(project_graph_router)
    app.include_router(research_area_router)
    app.include_router(notes_router)
    app.include_router(gap_heatmap_router)
    app.include_router(connected_papers_router)
    app.include_router(diary_router)
    app.include_router(gap_profile_router)
    app.include_router(dim_router)
    app.include_router(q_router)
    app.include_router(tts_router)
    app.include_router(waitlist_router)
    app.include_router(workshop_router)
    app.include_router(completion_router)
    app.include_router(review_router)
    app.include_router(theme_router)
    app.include_router(account_router)
    return app


app = create_app()
