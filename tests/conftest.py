"""Shared pytest fixtures + env override (Sentry/Settings izole)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ortamı izolasyonu: SENTRY_DSN boş + APP_ENV development + Settings cache temiz."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SENTRY_DSN", "")
    monkeypatch.setenv("PINECONE_API_KEY", "")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "x")  # test tokens are HS256("x")
    # B-3: auth middleware JWKS path'i prod canon; testlerde HS256 path aktif kalsın.
    monkeypatch.setenv("SUPABASE_JWKS_URL", "")
    # Force in-memory fallback — test user_id is not a real UUID
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    from api.config import get_settings
    from api.db import redis_client
    from api.db.supabase_client import get_supabase_admin, get_supabase_anon

    get_settings.cache_clear()
    get_supabase_admin.cache_clear()
    get_supabase_anon.cache_clear()
    # Redis lokalde başlatılınca cross-test cache leakage çıktı: aynı session_id/query
    # collision'ı fake-LLM mock'unun çağrılmasını engelliyor. Testlerde gerçek Redis'i
    # bypass ediyoruz; cache davranışını test eden suite'ler kendi monkeypatch'iyle
    # in-memory store'a yönlendirir (örn. test_search_endpoint._clear_state).
    redis_client._CACHE_DISABLED = True
    redis_client._DISABLED_UNTIL = 0.0
    redis_client.get_redis_sync.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from api.main import create_app
    from api.routes.search import get_reranker
    from api.services._mocks import MockReranker

    app = create_app()
    # Hermetik test: OPENALEX_EMAIL boş-olmayan default (config.py:112) yüzünden get_reranker
    # gerçek BgeReranker döndürür → ilk rerank'ta BAAI/bge-reranker-v2-m3 HF'den yüklenir.
    # CI offline (HF_HUB_OFFLINE=1) + cache yok → LocalEntryNotFoundError (pre-existing CI kırmızı).
    # Testler zaten MockReranker varsayıyor (bkz test_skeleton_endpoints "first score=1.0");
    # dependency override ile modeli hiç yükletmeden o niyeti garanti ediyoruz. BgeReranker'ın
    # kendi davranışı unit testlerde scorer-injection ile ayrıca kapsanır.
    app.dependency_overrides[get_reranker] = MockReranker
    with TestClient(app) as c:
        yield c
