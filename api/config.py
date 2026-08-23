"""Application configuration via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "0.1.0"
    APP_LOG_LEVEL: str = "INFO"
    APP_PORT: int = 8000

    # F14 Hakemlik admin paneli allowlist (virgül-ayrılmış user_id/sub).
    # Prod'da boş = admin uçları KAPALI (fail-closed, R-4); dev'de boş = bypass.
    ADMIN_USER_IDS: str = ""

    # Production CORS: virgül-ayrılmış kaynak listesi (https://app.example.com,https://staging.example.com).
    # Boş ise production'da hiçbir cross-origin istek geçmez — set edilmesi zorunludur.
    # Dev/staging'de görmezden gelinir (allow_origins=["*"]).
    FRONTEND_ORIGINS: str = ""

    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_JWKS_URL: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # F14 hakemlik — review_job IZOLE tablosu ayrı bir Supabase projesinde
    # (Clarus, project_ref qoojmhaagwbvxjlthjaa) tutulur (B-F14-09). Set değilse
    # default SUPABASE_* kullanılır (dev/test). Service-role key — RLS bypass.
    REVIEW_SUPABASE_URL: str = ""
    REVIEW_SUPABASE_SECRET_KEY: str = ""

    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "papers-bgem3"
    PINECONE_NAMESPACE: str = "mdv1"
    PINECONE_TIMEOUT_SECONDS: float = 10.0

    SUPABASE_TIMEOUT_SECONDS: float = 10.0

    RETRY_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_SECONDS: float = 0.2
    RETRY_MAX_DELAY_SECONDS: float = 5.0
    RETRY_JITTER: bool = True

    EMBEDDING_MODEL_ID: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 16

    # N-8 lifespan warm-up flag. BGE-M3 + reranker birlikte ~1GB RAM yükler;
    # bu yüzden default kapalı. Bellek tabanı uygun prod instance'ında
    # `BGE_WARMUP_ENABLED=true` ile aç → ilk request cold-start cezası kalkar.
    BGE_WARMUP_ENABLED: bool = False

    # M-15 (kısmi): HF Inference Endpoint URL'i set ise pool_router HTTP'ye gider;
    # boş ise local BGE-M3 (CPU). Endpoint deploy'u ayrı Sprint'te.
    EMBEDDING_API_URL: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    RATE_LIMIT_OGRENCI_PER_MIN: int = 60

    # V1-S18-P014 pilot allowlist gate. Default true = dev/test bypass.
    # Production'da explicit false ile waitlist.status ∈ {invited, active}
    # kontrolü açılır.
    WAITLIST_BYPASS: bool = True

    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    GEMINI_API_KEY: str = ""
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"

    # F14-S1 Vertex AI binding (provider toggle — DM-VTX-1/2)
    # LLM_PROVIDER=vertex → litellm_router alias'ları vertex_ai/...'e map eder
    # (kod/alias adları değişmez, DM-VTX-3). Default "gemini" = mevcut API-key
    # yolu (fail-safe; Vertex hazır değilken sistem kırılmaz).
    # Kimlik ADC ile: GOOGLE_APPLICATION_CREDENTIALS = SA JSON yolu (yaml'a
    # secret gömülmez, DM-VTX-1).
    LLM_PROVIDER: Literal["gemini", "vertex"] = "gemini"
    VERTEX_PROJECT: str = ""
    VERTEX_LOCATION: str = "europe-west4"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # F14-S2 Claude fallback (Sonnet 4.6 - Omer karari, token maliyeti nedeniyle Fable yerine)
    # ANTHROPIC_API_KEY set + LLM_FALLBACK_ENABLED ise: Gemini/Vertex çağrısı
    # başarısız olursa litellm Router otomatik claude-sonnet-4-6'ya düşer
    # (yalnız arıza yolu). Key boşsa fallback pasif; sistem kırılmaz.
    ANTHROPIC_API_KEY: str = ""
    LLM_FALLBACK_ENABLED: bool = True

    # V1-S12 ElevenLabs TTS (sesli dinlet — KD-V1-S12-02)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "xyqF3vGMQlPk3e7yA4DI"
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_TIMEOUT_SECONDS: float = 30.0

    # V1 Vitrin (anon + ogrenci) — OpenAlex polite-pool + Crossref
    # kaynak: docs/plans/V1_S5_backend_tier_canon.md §1
    # LLM = Gemini Flash (F8 LLMService mevcut); HF Qwen V1'de kullanılmaz.
    OPENALEX_EMAIL: str = "dr.ofrencber@gaziantep.edu.tr"
    # 2026-08-10: OpenAlex kullanım-bazlı ücretlendirmeye geçti (mailto-only artık
    # en düşük katman: $0.10/gün ≈100 arama çağrısı). Ücretsiz key ile 10x
    # ($1/gün ≈1000 çağrı) — bkz. PDF_PIPELINE_CALISMA_GUNLUGU.md §36.
    # Boşsa (key yok) eski mailto-only davranışa dürüstçe düşer.
    OPENALEX_API_KEY: str = ""
    OPENALEX_TIMEOUT_SECONDS: float = 10.0
    CROSSREF_EMAIL: str = "dr.ofrencber@gaziantep.edu.tr"
    CROSSREF_TIMEOUT_SECONDS: float = 10.0

    # 2026-08-23: Semantic Scholar (S2) — OpenAlex not_found_in_index derse
    # fallback (engine/providers/semantic_scholar.py). Boşsa (key yok) S2
    # HİÇ ÇAĞRILMAZ (dürüstçe atlanır, ağ çağrısı YAPILMAZ) — canlı testte
    # kanıtlandı: key'siz anonim kota HEMEN 429 veriyor (ham S2 yanıtı:
    # "apply for a key for higher rate limits"), boşuna gecikme eklemesin
    # diye key yoksa mekanizma tamamen devre dışı kalır. Ücretsiz key:
    # https://www.semanticscholar.org/product/api#api-key-form
    SEMANTIC_SCHOLAR_API_KEY: str = ""

    LITELLM_TIMEOUT_SECONDS: int = 30
    LITELLM_CONFIG_PATH: str = "config/litellm_models.yaml"
    PRESENTER_TR_MODEL: str = "gemini-flash-tr"
    PRESENTER_EN_MODEL: str = "gemini-flash-en"
    PRESENTER_ID_MODEL: str = "gemini-flash-id"

    RERANKER_MODEL_ID: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_DEVICE: Literal["cpu", "mps", "cuda"] = "cpu"
    RERANKER_BATCH_SIZE: int = 8
    RERANKER_MAX_LEN: int = 512

    FAITHFULNESS_THRESHOLDS_PATH: str = "config/faithfulness_thresholds.yaml"

    OPENALEX_BASE_URL: str = "https://api.openalex.org"
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
