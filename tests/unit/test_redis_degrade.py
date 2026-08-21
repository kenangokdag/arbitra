"""Boş/geçersiz REDIS_URL → boot ÇÖKMEZ, zarif degrade (canlıya-çıkış testinde bulundu).

Kök neden: redis.Redis.from_url("") → ValueError; cache_health_probe + cache_get/set
yalnız redis.RedisError yakalıyordu → boot-time crash. config_validation boş Redis'i
"uyarı, devam" sayar; bu sözleşme from_url'ün ham ValueError'ı ile kırılıyordu.
Fix: from_url ValueError → redis.ConnectionError (RedisError) → mevcut degrade yolları kapsar.
"""

from __future__ import annotations

import redis

from api.db import redis_client


def _reset(monkeypatch, url: str) -> None:
    monkeypatch.setenv("REDIS_URL", url)
    from api.config import get_settings

    get_settings.cache_clear()
    redis_client.get_redis_sync.cache_clear()
    redis_client.get_redis_async.cache_clear()
    # conftest cache'i kapatıyor; gerçek degrade yolunu test etmek için aç
    redis_client._CACHE_DISABLED = False
    redis_client._DISABLED_UNTIL = 0.0


def test_empty_redis_url_raises_redis_error_not_valueerror(monkeypatch):
    """Boş REDIS_URL → ham ValueError DEĞİL, RedisError (degrade yolları yakalar)."""
    _reset(monkeypatch, "")
    raised: Exception | None = None
    try:
        redis_client.get_redis_sync()
    except redis.RedisError as exc:  # ConnectionError ⊂ RedisError
        raised = exc
    except ValueError as exc:  # eski kırık davranış
        raised = exc
        raise AssertionError(
            "boş REDIS_URL ham ValueError fırlattı — degrade yolları (except RedisError) "
            "bunu yakalayamaz, boot çöker"
        ) from exc
    assert isinstance(raised, redis.RedisError)


def test_health_probe_degrades_on_empty_url_no_crash(monkeypatch):
    """cache_health_probe boş URL'de False döner (çökmez) — boot devam eder."""
    _reset(monkeypatch, "")
    assert redis_client.cache_health_probe() is False
    assert redis_client._CACHE_DISABLED is True  # degrade işaretlendi


def test_cache_get_set_no_crash_on_empty_url(monkeypatch):
    """cache_get/set boş URL'de sessizce no-op — ham hata kaçmaz (500 yok)."""
    _reset(monkeypatch, "")
    assert redis_client.cache_get("q", "k") is None  # raise YOK
    redis_client.cache_set("q", "k", {"a": 1})  # raise YOK


def test_valid_url_still_builds_client(monkeypatch):
    """Geçerli scheme (ulaşılamaz olsa da) → client kurulur (regresyon yok)."""
    _reset(monkeypatch, "redis://localhost:6379/0")
    client = redis_client.get_redis_sync()
    assert isinstance(client, redis.Redis)
