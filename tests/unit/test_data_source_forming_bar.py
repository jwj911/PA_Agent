"""Tests for DataSource-level forming-bar semantics."""
from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from pa_agent.data.akshare_source import AkShareSource
from pa_agent.data.bar_close_wait import has_forming_bar_at_head
from pa_agent.data.base import DataSource, KlineBar
from pa_agent.data.eastmoney_source import EastMoneySource
from pa_agent.data.mt5 import MT5Source
from pa_agent.data.snapshot import build_analysis_frame
from pa_agent.data.tradingview import TradingViewSource
from pa_agent.data.yfinance_source import YFinanceSource


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


def test_tradingview_override_detects_active_head_by_countdown() -> None:
    ts_open = 1_700_000_000_000.0
    now_ms = int(ts_open) + 5 * 60 * 1000

    assert TradingViewSource().has_forming_bar_at_head(
        [_bar(ts_open, close=10.0, closed=True)],
        "15m",
        now_ms=now_ms,
    )


def test_tradingview_override_marks_boundary_head_closed() -> None:
    ts_open = 1_700_000_000_000.0
    now_ms = int(ts_open) + 30 * 60 * 1000

    assert not TradingViewSource().has_forming_bar_at_head(
        [_bar(ts_open, close=10.0)],
        "15m",
        now_ms=now_ms,
    )


def test_tradingview_latest_snapshot_reuses_override(monkeypatch) -> None:
    calls: list[tuple[str | None, bool]] = []

    class _Source(TradingViewSource):
        def has_forming_bar_at_head(
            self,
            bars_newest_first: list[KlineBar],
            timeframe: str | None = None,
            *,
            now_ms: int | None = None,
            symbol: str | None = None,
        ) -> bool:
            calls.append((timeframe, bars_newest_first[0].closed))
            return True

    src = _Source()
    src._tv = object()
    src._symbol = "XAUUSD"
    src._timeframe = "15m"

    monkeypatch.setitem(
        sys.modules,
        "tvDatafeed",
        SimpleNamespace(Interval=SimpleNamespace(in_15_minute="15m")),
    )
    monkeypatch.setattr(
        src,
        "_fetch_hist_with_retry",
        lambda **kwargs: pd.DataFrame(
            [
                {
                    "datetime": datetime(2026, 7, 15, 9, 30),
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 100.0,
                }
            ]
        ),
    )

    bars = src._latest_snapshot_inner(1)

    assert calls == [("15m", True)]
    assert len(bars) == 1
    assert not bars[0].closed


def test_yfinance_latest_snapshot_reuses_data_source_forming_entry(monkeypatch) -> None:
    calls: list[tuple[str | None, bool]] = []

    class _Source(YFinanceSource):
        def has_forming_bar_at_head(
            self,
            bars_newest_first: list[KlineBar],
            timeframe: str | None = None,
            *,
            now_ms: int | None = None,
            symbol: str | None = None,
        ) -> bool:
            calls.append((timeframe, bars_newest_first[0].closed))
            return False

    df = pd.DataFrame(
        [
            {
                "Open": 10.0,
                "High": 11.0,
                "Low": 9.0,
                "Close": 10.5,
                "Volume": 100.0,
            }
        ],
        index=pd.DatetimeIndex([datetime(2026, 7, 15, 9, 30)], name="Datetime"),
    )
    ticker = SimpleNamespace(history=lambda **kwargs: df)
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda symbol: ticker),
    )

    src = _Source()
    src._connected = True
    src._symbol = "GC=F"
    src._timeframe = "15m"

    bars = src.latest_snapshot(1)

    assert calls == [("15m", False)]
    assert len(bars) == 1
    assert bars[0].closed


def test_mt5_latest_snapshot_reuses_data_source_forming_entry(monkeypatch) -> None:
    calls: list[tuple[str | None, bool]] = []

    class _Source(MT5Source):
        def has_forming_bar_at_head(
            self,
            bars_newest_first: list[KlineBar],
            timeframe: str | None = None,
            *,
            now_ms: int | None = None,
            symbol: str | None = None,
        ) -> bool:
            calls.append((timeframe, bars_newest_first[0].closed))
            return False

    rates = [
        {
            "time": 1_700_000_000,
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.5,
            "tick_volume": 100.0,
        }
    ]
    monkeypatch.setitem(
        sys.modules,
        "MetaTrader5",
        SimpleNamespace(
            TIMEFRAME_M15="M15",
            symbol_select=lambda symbol, selected: True,
            copy_rates_from_pos=lambda symbol, timeframe, start, count: rates,
            last_error=lambda: (0, "ok"),
        ),
    )

    src = _Source()
    src._connected = True
    src._symbol = "XAUUSD"
    src._timeframe = "15m"

    bars = src.latest_snapshot(1)

    assert calls == [("15m", False)]
    assert len(bars) == 1
    assert bars[0].closed
