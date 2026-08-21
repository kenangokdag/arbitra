"""P002 db client unit tests (Supabase + Pinecone + Redis).

Mock-only — gerçek bağlantı YOK. Real connection smoke ileri sprint'e ait.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.db.pinecone_client import (
    MAX_RETRY,
    PineconeIndexWrapper,
    PineconeQueryError,
)
from api.db.redis_client import CacheNamespace, cache_get, cache_set
from api.db.supabase_client import (
    SupabaseQueryError,
    get_supabase_admin,
    get_supabase_anon,
    supabase_call_async,
)

pytestmark = pytest.mark.unit


# ---------- Supabase: env validation ----------


def test_supabase_admin_raises_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service-role client SUPABASE_URL veya SECRET_KEY yoksa raise."""
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    from api.config import get_settings

    get_settings.cache_clear()
    get_supabase_admin.cache_clear()

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        get_supabase_admin()


def test_supabase_anon_raises_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publishable client URL veya PUBLISHABLE_KEY yoksa raise."""
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "")
    from api.config import get_settings

    get_settings.cache_clear()
    get_supabase_anon.cache_clear()

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        get_supabase_anon()


# ---------- Supabase: P012 timeout + async helper ----------


def test_supabase_admin_uses_settings_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_client'a ClientOptions ile postgrest_client_timeout iletilir."""
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("SUPABASE_TIMEOUT_SECONDS", "7.0")
    from api.config import get_settings
    from api.db import supabase_client

    get_settings.cache_clear()
    supabase_client.get_supabase_admin.cache_clear()

    captured: dict[str, object] = {}

    def fake_create(url: str, key: str, options: object | None = None) -> MagicMock:
        captured["url"] = url
        captured["options"] = options
        return MagicMock()

    with patch.object(supabase_client, "create_client", side_effect=fake_create):
        supabase_client.get_supabase_admin()

    opts = captured["options"]
    assert opts is not None
    assert getattr(opts, "postgrest_client_timeout", None) == 7


@pytest.mark.asyncio
async def test_supabase_call_async_returns_value() -> None:
    """to_thread + with_timeout: callable sonucu olduğu gibi döner."""
    result = await supabase_call_async(lambda: {"data": [1, 2, 3]}, timeout=1.0)
    assert result == {"data": [1, 2, 3]}


@pytest.mark.asyncio
async def test_supabase_call_async_timeout_raises() -> None:
    """Yavaş çağrı timeout aşarsa ResilienceTimeoutError raise."""
    import time as _time

    from api.utils.resilience import ResilienceTimeoutError

    def slow() -> int:
        _time.sleep(0.5)
        return 1

    with pytest.raises(ResilienceTimeoutError):
        await supabase_call_async(slow, timeout=0.05)


@pytest.mark.asyncio
async def test_supabase_call_async_wraps_runtime_error() -> None:
    """Sync callable raise ederse SupabaseQueryError zarfı (cause = orijinal)."""

    def boom() -> int:
        raise ConnectionError("postgrest 500")

    with pytest.raises(SupabaseQueryError) as exc_info:
        await supabase_call_async(boom, timeout=1.0)

    assert isinstance(exc_info.value.__cause__, ConnectionError)


# ---------- Pinecone: retry mantığı ----------


def test_pinecone_query_succeeds_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    """İlk denemede başarılı → retry yok."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    from api.config import get_settings
    from api.db import pinecone_client

    get_settings.cache_clear()
    pinecone_client.get_pinecone_client.cache_clear()

    fake_index = MagicMock()
    fake_index.query.return_value = {"matches": [{"id": "p1", "score": 0.9}]}
    fake_pc = MagicMock()
    fake_pc.Index.return_value = fake_index

    with patch.object(pinecone_client, "Pinecone", return_value=fake_pc):
        wrapper = PineconeIndexWrapper()
        result = wrapper.query(vector=[0.1] * 1024, top_k=10)

    assert result == {"matches": [{"id": "p1", "score": 0.9}]}
    assert fake_index.query.call_count == 1


def test_pinecone_query_retries_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """İlk 2 deneme fail → 3. başarılı; backoff sleep mocked."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    from api.config import get_settings
    from api.db import pinecone_client

    get_settings.cache_clear()
    pinecone_client.get_pinecone_client.cache_clear()
    pinecone_client.get_pinecone_index.cache_clear()
    monkeypatch.setattr(pinecone_client.time, "sleep", lambda _s: None)

    fake_index = MagicMock()
    fake_index.query.side_effect = [
        ConnectionError("transient 1"),
        ConnectionError("transient 2"),
        {"matches": []},
    ]
    fake_pc = MagicMock()
    fake_pc.Index.return_value = fake_index

    with patch.object(pinecone_client, "Pinecone", return_value=fake_pc):
        wrapper = PineconeIndexWrapper()
        result = wrapper.query(vector=[0.1] * 1024)

    assert result == {"matches": []}
    assert fake_index.query.call_count == MAX_RETRY


def test_pinecone_query_raises_after_max_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """3 deneme de fail → PineconeQueryError; cause son ConnectionError."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    from api.config import get_settings
    from api.db import pinecone_client

    get_settings.cache_clear()
    pinecone_client.get_pinecone_client.cache_clear()
    pinecone_client.get_pinecone_index.cache_clear()
    monkeypatch.setattr(pinecone_client.time, "sleep", lambda _s: None)

    fake_index = MagicMock()
    fake_index.query.side_effect = ConnectionError("persistent")
    fake_pc = MagicMock()
    fake_pc.Index.return_value = fake_index

    with patch.object(pinecone_client, "Pinecone", return_value=fake_pc):
        wrapper = PineconeIndexWrapper()
        with pytest.raises(PineconeQueryError):
            wrapper.query(vector=[0.1] * 1024)

    assert fake_index.query.call_count == MAX_RETRY


def test_pinecone_get_index_singleton_returns_same_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_pinecone_index() lru_cache → aynı instance (B42-045 fan_out fix)."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    from api.config import get_settings
    from api.db import pinecone_client

    get_settings.cache_clear()
    pinecone_client.get_pinecone_client.cache_clear()
    pinecone_client.get_pinecone_index.cache_clear()

    fake_pc = MagicMock()
    fake_pc.Index.return_value = MagicMock()

    with patch.object(pinecone_client, "Pinecone", return_value=fake_pc):
        a = pinecone_client.get_pinecone_index()
        b = pinecone_client.get_pinecone_index()

    assert a is b


@pytest.mark.asyncio
async def test_pinecone_query_async_timeout_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """query_async timeout aşılırsa ResilienceTimeoutError raise."""
    import time as _time

    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    from api.config import get_settings
    from api.db import pinecone_client
    from api.utils.resilience import ResilienceTimeoutError

    get_settings.cache_clear()
    pinecone_client.get_pinecone_client.cache_clear()
    pinecone_client.get_pinecone_index.cache_clear()

    def slow_query(*_args: object, **_kwargs: object) -> dict[str, list[object]]:
        _time.sleep(0.5)
        return {"matches": []}

    fake_index = MagicMock()
    fake_index.query.side_effect = slow_query
    fake_pc = MagicMock()
    fake_pc.Index.return_value = fake_index

    with patch.object(pinecone_client, "Pinecone", return_value=fake_pc):
        wrapper = PineconeIndexWrapper()
        with pytest.raises(ResilienceTimeoutError):
            await wrapper.query_async(vector=[0.1] * 1024, timeout_seconds=0.05)


# ---------- Redis cache helpers ----------


def test_cache_namespace_ttl_constants() -> None:
    """3-katlı namespace TTL'ler doğru: q=1h, sum=24h, enrich=7d."""
    assert CacheNamespace.TTL_SECONDS[CacheNamespace.QUERY] == 3_600
    assert CacheNamespace.TTL_SECONDS[CacheNamespace.SUMMARY] == 86_400
    assert CacheNamespace.TTL_SECONDS[CacheNamespace.ENRICH] == 604_800


def test_cache_set_get_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Redis: set + get JSON roundtrip."""
    from api.db import redis_client

    redis_client.get_redis_sync.cache_clear()
    fake_redis = MagicMock()
    storage: dict[str, str] = {}

    def fake_setex(key: str, _ttl: int, value: str) -> None:
        storage[key] = value

    def fake_get(key: str) -> str | None:
        return storage.get(key)

    fake_redis.setex.side_effect = fake_setex
    fake_redis.get.side_effect = fake_get

    with patch.object(redis_client.redis.Redis, "from_url", return_value=fake_redis):
        cache_set(CacheNamespace.QUERY, "test-key", {"a": 1, "b": [2, 3]})
        result = cache_get(CacheNamespace.QUERY, "test-key")

    assert result == {"a": 1, "b": [2, 3]}
    fake_redis.setex.assert_called_once()
    args = fake_redis.setex.call_args[0]
    assert args[0] == "q:test-key"
    assert args[1] == 3_600


def test_cache_get_missing_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Olmayan key → None."""
    from api.db import redis_client

    redis_client.get_redis_sync.cache_clear()
    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    with patch.object(redis_client.redis.Redis, "from_url", return_value=fake_redis):
        result = cache_get(CacheNamespace.SUMMARY, "missing")

    assert result is None


def test_cache_set_custom_ttl_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom TTL override default'u kullanmaz."""
    from api.db import redis_client

    redis_client.get_redis_sync.cache_clear()
    fake_redis = MagicMock()

    with patch.object(redis_client.redis.Redis, "from_url", return_value=fake_redis):
        cache_set(CacheNamespace.QUERY, "k", "v", ttl=120)

    fake_redis.setex.assert_called_once_with("q:k", 120, "v")
