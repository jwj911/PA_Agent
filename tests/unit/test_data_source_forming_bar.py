"""Tests for DataSource-level forming-bar semantics."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pa_agent.data.akshare_source import AkShareSource
from pa_agent.data.bar_close_wait import has_forming_bar_at_head
from pa_agent.data.base import DataSource, KlineBar
from pa_agent.data.eastmoney_source import EastMoneySource
from pa_agent.data.snapshot import build_analysis_frame


class _Source(DataSource):
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def list_symbols(self) -> list[str]:
        return []

    def supported_timeframes(self) -> list[str]:
        return []

    def subscribe(self, symbol: str, timeframe: str) -> None:
        pass

    def unsubscribe(self) -> None:
        pass

    def latest_snapshot(self, n: int) -> list[KlineBar]:
        return []


class _AlwaysFormingSource(_Source):
    def has_forming_bar_at_head(
        self,
        bars_newest_first: list[KlineBar],
        timeframe: str | None = None,
        *,
        now_ms: int | None = None,
        symbol: str | None = None,
    ) -> bool:
        return bool(bars_newest_first)


def _bar(ts_ms: float, *, close: float, closed: bool = False) -> KlineBar:
    return KlineBar(
        seq=1,
        ts_open=ts_ms,
        open=close - 0.5,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=100.0,
        closed=closed,
    )


def _cn_ms(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
) -> int:
    return int(
        datetime(
            year,
            month,
            day,
            hour,
            minute,
            tzinfo=ZoneInfo("Asia/Shanghai"),
        ).timestamp()
        * 1000
    )


def test_data_source_default_forming_detection_matches_shared_helper() -> None:
    ts_open = 1_700_000_000_000.0
    now_ms = int(ts_open) + 30 * 60 * 1000
    bars = [_bar(ts_open, close=10.0)]

    source = _Source()

    assert not has_forming_bar_at_head(bars, "15m", now_ms=now_ms)
    assert not source.has_forming_bar_at_head(bars, "15m", now_ms=now_ms)


def test_data_source_default_detects_active_forming_bar() -> None:
    ts_open = 1_700_000_000_000.0
    now_ms = int(ts_open) + 5 * 60 * 1000

    assert _Source().has_forming_bar_at_head(
        [_bar(ts_open, close=10.0)],
        "15m",
        now_ms=now_ms,
    )


def test_snapshot_uses_data_source_forming_override() -> None:
    now_ms = 1_700_000_000_000
    bars = [
        _bar(float(now_ms), close=10.0, closed=True),
        _bar(float(now_ms - 15 * 60 * 1000), close=9.0, closed=True),
    ]

    frame = build_analysis_frame(
        bars,
        1,
        "XAUUSD",
        "15m",
        now_ms=now_ms,
        data_source=_AlwaysFormingSource(),
    )

    assert frame is not None
    assert frame.bars[0].close == 9.0


def test_eastmoney_daily_head_stays_forming_during_lunch_break() -> None:
    """EastMoney daily bars stay live through the A-share lunch break."""
    lunch_ms = _cn_ms(2026, 7, 13, 12, 0)
    source = EastMoneySource()

    assert source.has_forming_bar_at_head(
        [_bar(float(lunch_ms), close=10.0)],
        "1d",
        now_ms=lunch_ms,
        symbol="600519",
    )


def test_akshare_daily_head_is_not_forming_during_lunch_break() -> None:
    """AkShare keeps its existing continuous-session-only live-head rule."""
    lunch_ms = _cn_ms(2026, 7, 13, 12, 0)
    source = AkShareSource()

    assert not source.has_forming_bar_at_head(
        [_bar(float(lunch_ms), close=10.0)],
        "1d",
        now_ms=lunch_ms,
        symbol="600519",
    )
