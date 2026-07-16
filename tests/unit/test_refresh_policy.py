"""Tests for data refresh policy helpers."""
from __future__ import annotations

from pa_agent.data.refresh_policy import (
    DEFAULT_ZOMBIE_JOIN_MS,
    HTTP_MIN_REFRESH_MS,
    HTTP_SNAPSHOT_CACHE_TTL_1D_S,
    HTTP_SNAPSHOT_CACHE_TTL_S,
    HTTP_ZOMBIE_JOIN_MS,
    effective_refresh_interval_ms,
    is_http_poll_source,
    snapshot_cache_ttl_s,
    zombie_join_timeout_ms,
)


def test_http_poll_sources_are_clamped() -> None:
    assert is_http_poll_source("eastmoney")
    assert is_http_poll_source("akshare")
    assert not is_http_poll_source("mt5")

    assert effective_refresh_interval_ms("eastmoney", 500) == HTTP_MIN_REFRESH_MS
    assert effective_refresh_interval_ms("mt5", 100) == 500


def test_daily_http_refresh_has_higher_floor() -> None:
    assert effective_refresh_interval_ms("eastmoney", 2500, timeframe="1d") == 3000
    assert effective_refresh_interval_ms("eastmoney", 3500, timeframe="1d") == 3500


def test_snapshot_cache_ttl_by_timeframe() -> None:
    assert snapshot_cache_ttl_s("1m") == 4.0
    assert snapshot_cache_ttl_s("5m") == HTTP_SNAPSHOT_CACHE_TTL_S
    assert snapshot_cache_ttl_s("1d") == HTTP_SNAPSHOT_CACHE_TTL_1D_S
    assert snapshot_cache_ttl_s("1w") == HTTP_SNAPSHOT_CACHE_TTL_1D_S
    assert snapshot_cache_ttl_s("1M") == HTTP_SNAPSHOT_CACHE_TTL_1D_S


def test_zombie_join_timeout_by_source() -> None:
    assert zombie_join_timeout_ms("eastmoney") == HTTP_ZOMBIE_JOIN_MS
    assert zombie_join_timeout_ms("akshare") == HTTP_ZOMBIE_JOIN_MS
    assert zombie_join_timeout_ms("mt5") == DEFAULT_ZOMBIE_JOIN_MS
