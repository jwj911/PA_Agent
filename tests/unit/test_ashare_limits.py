"""Tests for A-share limit-up / limit-down helpers."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pa_agent.data.ashare_limits import (
    effective_pct_chg,
    limit_bar_label,
    limit_labels_for_frame,
    limit_pct,
    limit_prices,
    normalize_stock_code,
)
from pa_agent.data.base import KlineBar


def _ts_ms(year: int, month: int, day: int) -> int:
    dt = datetime(year, month, day, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    return int(dt.timestamp() * 1000)


def _bar(
    *,
    seq: int,
    day: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    pct_chg: float | None = None,
) -> KlineBar:
    return KlineBar(
        seq=seq,
        ts_open=_ts_ms(2026, 7, day),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
        pct_chg=pct_chg,
    )


def test_normalize_stock_code_accepts_common_inputs() -> None:
    assert normalize_stock_code("SH600519") == "600519"
    assert normalize_stock_code("sz000001") == "000001"
    assert normalize_stock_code("600519.SH") == "600519"
    assert normalize_stock_code("988") == "988"


def test_limit_pct_by_board_and_st_name() -> None:
    assert limit_pct("600519") == 0.10
    assert limit_pct("300750") == 0.20
    assert limit_pct("688981") == 0.20
    assert limit_pct("430047") == 0.30
    assert limit_pct("600000", "st sample") == 0.05


def test_limit_prices_round_to_two_decimals() -> None:
    assert limit_prices(10.03, 0.10) == (11.03, 9.03)


def test_effective_pct_chg_prefers_api_value() -> None:
    bar = _bar(seq=1, day=16, open_=10.0, high=10.5, low=9.8, close=10.2, pct_chg=1.5)

    assert effective_pct_chg(bar, prev_close=10.0) == 1.5


def test_limit_bar_label_detects_one_word_limits() -> None:
    up = _bar(seq=1, day=16, open_=11.0, high=11.0, low=11.0, close=11.0)
    down = _bar(seq=1, day=16, open_=9.0, high=9.0, low=9.0, close=9.0)

    assert limit_bar_label(up, prev_close=10.0, symbol="600519") == "一字涨停"
    assert limit_bar_label(down, prev_close=10.0, symbol="600519") == "一字跌停"


def test_limit_labels_for_frame_uses_previous_trading_day_close() -> None:
    bars = [
        _bar(seq=1, day=16, open_=11.0, high=11.0, low=10.5, close=11.0),
        _bar(seq=2, day=15, open_=10.0, high=10.2, low=9.8, close=10.0),
    ]

    assert limit_labels_for_frame(bars, "600519") == ["涨停", ""]
