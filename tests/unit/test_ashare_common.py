"""Tests for shared A-share data helpers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pa_agent.data.ashare_common import (
    apply_session_quote_to_forming_row,
    ashare_head_bar_live,
    ashare_session_open,
    ashare_trading_day,
    index_symbol_for_api,
    is_index_symbol,
    normalize_ashare_symbol,
    quote_volume_lots_to_shares,
    resample_rows_to_4h,
)

_CN_TZ = ZoneInfo("Asia/Shanghai")


def test_normalize_ashare_symbol_preserves_known_index_prefixes() -> None:
    assert normalize_ashare_symbol(" sh000300 ") == "sh000300"
    assert normalize_ashare_symbol("sz399006") == "sz399006"
    assert normalize_ashare_symbol("SH600519") == "600519"
    assert normalize_ashare_symbol("600519.XSHG") == "600519"
    assert normalize_ashare_symbol("") == ""


def test_index_symbol_helpers_classify_common_indices() -> None:
    assert is_index_symbol("000300")
    assert is_index_symbol("sh000016")
    assert not is_index_symbol("600519")
    assert index_symbol_for_api("399006") == "sz399006"
    assert index_symbol_for_api("000300") == "sh000300"


def test_ashare_session_and_trading_day_boundaries() -> None:
    monday_open = datetime(2026, 7, 13, 9, 30, tzinfo=_CN_TZ)
    lunch_break = datetime(2026, 7, 13, 12, 0, tzinfo=_CN_TZ)
    after_close = datetime(2026, 7, 13, 15, 0, tzinfo=_CN_TZ)
    weekend = datetime(2026, 7, 18, 10, 0, tzinfo=_CN_TZ)

    assert ashare_session_open(monday_open)
    assert not ashare_session_open(lunch_break)
    assert ashare_trading_day(lunch_break)
    assert not ashare_trading_day(after_close)
    assert not ashare_trading_day(weekend)
    assert ashare_head_bar_live("1d", lunch_break)
    assert not ashare_head_bar_live("1h", lunch_break)


def test_quote_volume_lots_to_shares_keeps_index_volume_units() -> None:
    assert quote_volume_lots_to_shares(12.5, symbol="600519") == 1250.0
    assert quote_volume_lots_to_shares(12.5, symbol="000300") == 12.5
    assert quote_volume_lots_to_shares(0, symbol="600519") == 0.0


def test_apply_session_quote_to_forming_row_updates_daily_bar() -> None:
    row = {
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.0,
        "volume": 0.0,
        "amount": 0.0,
    }

    apply_session_quote_to_forming_row(
        row,
        price=11.0,
        open_=10.2,
        high=11.3,
        low=10.1,
        volume=5.0,
        amount=123.0,
        prev_close=10.0,
        daily=True,
        volume_lots=True,
        symbol="600519",
    )

    assert row == {
        "open": 10.2,
        "high": 11.3,
        "low": 10.1,
        "close": 11.0,
        "volume": 500.0,
        "amount": 123.0,
        "pct_chg": 10.0,
    }


def test_resample_rows_to_4h_merges_chunks_and_keeps_tail_bucket() -> None:
    rows = [
        {"ts_open": 1, "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5, "volume": 1.0},
        {"ts_open": 2, "open": 10.5, "high": 12.0, "low": 10.0, "close": 11.0, "volume": 2.0},
        {"ts_open": 3, "open": 11.0, "high": 13.0, "low": 10.5, "close": 12.0, "volume": 3.0},
        {"ts_open": 4, "open": 12.0, "high": 12.5, "low": 11.5, "close": 12.2, "volume": 4.0},
        {"ts_open": 5, "open": 12.2, "high": 12.8, "low": 12.0, "close": 12.4, "volume": 5.0},
    ]

    assert resample_rows_to_4h(rows) == [
        {"ts_open": 1, "open": 10.0, "high": 13.0, "low": 9.0, "close": 12.2, "volume": 10.0},
        {"ts_open": 5, "open": 12.2, "high": 12.8, "low": 12.0, "close": 12.4, "volume": 5.0},
    ]
