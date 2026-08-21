"""P3 Redis cache_enabled flag + startup health probe unit tests.

CLAUDE.md §3.4 sığınak yasak: Redis ulaşılmazsa istek başına spam yerine
tek transition warn + 5dk re-arm window. Bu testler:
  - cache_health_probe success/failure
  - _CACHE_DISABLED transition warn (tek seferlik)
  - cache_get/set no-op when disabled (Redis.from_url asla çağrılmaz)
  - re-arm penceresi dolduğunda yeniden dene
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
import redis as redis_pkg

from api.db import redis_client
from api.db.redis_client import (
    CacheNamespace,
    _cache_disabled,
    cache_get,
    cache_health_probe,
    cache_set,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_cache_flag() -> Generator[None, None, None]:
    """Modül-seviye state'i her testin başında VE sonunda sıfırla.

    Teardown şart: aksi halde "disabled" bırakan testler diğer test dosyalarındaki
    cache_get/set roundtrip testlerini kirletir (test_db_clients.py).
    """
    redis_client._CACHE_DISABLED = False
    redis_client._DISABLED_UNTIL = 0.0
    redis_client.get_redis_sync.cache_clear()
    yield
    redis_client._CACHE_DISABLED = False
    redis_client._DISABLED_UNTIL = 0.0
    redis_client.get_redis_sync.cache_clear()


def test_cache_health_probe_returns_true_when_redis_reachable() -> None:
    """Ping başarılıysa probe True döner, flag set edilmez."""
    fake_redis = MagicMock()
    fake_redis.ping.return_value = True

    with patch.object(redis_pkg.Redis, "from_url", return_value=fake_redis):
        ok = cache_health_probe()

    assert ok is True
    assert _cache_disabled() is False
    fake_redis.ping.assert_called_once()


def test_cache_health_probe_returns_false_and_disables_when_redis_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ping fail → probe False + _CACHE_DISABLED True + tek warn log."""
    fake_redis = MagicMock()
    fake_redis.ping.side_effect = redis_pkg.ConnectionError("refused")

    with (
        patch.object(redis_pkg.Redis, "from_url", return_value=fake_redis),
        caplog.at_level(logging.WARNING, logger="api.db.redis_client"),
    ):
        ok = cache_health_probe()

    assert ok is False
    assert _cache_disabled() is True
    warn_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn_msgs) == 1
    assert "cache disabled" in warn_msgs[0].getMessage()


def test_cache_get_short_circuits_when_disabled() -> None:
    """Flag set ise cache_get Redis client'ı asla çağırmaz."""
    redis_client._CACHE_DISABLED = True
    redis_client._DISABLED_UNTIL = float("inf")

    with patch.object(redis_pkg.Redis, "from_url") as from_url:
        result = cache_get(CacheNamespace.QUERY, "anykey")

    assert result is None
    from_url.assert_not_called()


def test_cache_set_short_circuits_when_disabled() -> None:
    """Flag set ise cache_set Redis client'ı asla çağırmaz."""
    redis_client._CACHE_DISABLED = True
    redis_client._DISABLED_UNTIL = float("inf")

    with patch.object(redis_pkg.Redis, "from_url") as from_url:
        cache_set(CacheNamespace.QUERY, "k", "v")

    from_url.assert_not_called()


def test_cache_get_failure_logs_once_then_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """İki ardışık fail → tek warn (transition); ikinci çağrı sessiz no-op."""
    fake_redis = MagicMock()
    fake_redis.get.side_effect = redis_pkg.ConnectionError("refused")

    with (
        patch.object(redis_pkg.Redis, "from_url", return_value=fake_redis),
        caplog.at_level(logging.WARNING, logger="api.db.redis_client"),
    ):
        cache_get(CacheNamespace.QUERY, "k1")
        cache_get(CacheNamespace.QUERY, "k2")

    warn_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn_msgs) == 1
    # 2. çağrı flag aktifken short-circuit oldu → Redis'e gitmedi
    assert fake_redis.get.call_count == 1


def test_cache_disabled_re_arms_after_window_expires() -> None:
    """_DISABLED_UNTIL geçmişte ise flag temizlenir, _cache_disabled False döner."""
    redis_client._CACHE_DISABLED = True
    redis_client._DISABLED_UNTIL = 0.0  # geçmiş

    assert _cache_disabled() is False
    assert redis_client._CACHE_DISABLED is False


def test_cache_set_failure_marks_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """setex fail → flag set + warn; sonraki cache_set Redis'e gitmez."""
    fake_redis = MagicMock()
    fake_redis.setex.side_effect = redis_pkg.ConnectionError("refused")

    with (
        patch.object(redis_pkg.Redis, "from_url", return_value=fake_redis),
        caplog.at_level(logging.WARNING, logger="api.db.redis_client"),
    ):
        cache_set(CacheNamespace.QUERY, "k", "v")
        cache_set(CacheNamespace.QUERY, "k2", "v2")

    assert _cache_disabled() is True
    warn_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn_msgs) == 1
    assert fake_redis.setex.call_count == 1
