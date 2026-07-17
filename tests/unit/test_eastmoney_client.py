"""Tests for East Money low-level client helpers."""

from __future__ import annotations

from datetime import datetime

from pa_agent.data.eastmoney_client import (
    _daily_kline_params,
    _parse_clist_rows,
    _parse_klines,
    index_secid,
    stock_market_code,
    stock_secid,
)


def test_stock_and_index_secid_helpers_choose_expected_market_prefix() -> None:
    assert stock_market_code("600519") == 1
    assert stock_market_code("000001") == 0
    assert stock_secid("sh600519") == "1.600519"
    assert stock_secid("000001") == "0.000001"
    assert index_secid("sh000300") == "1.000300"
    assert index_secid("sz399001") == "0.399001"
    assert index_secid("399006") == "0.399006"
    assert index_secid("000300") == "1.000300"


def test_parse_klines_accepts_daily_minute_and_seconds_rows() -> None:
    rows = _parse_klines(
        [
            "2026-07-15,10,11,12,9,100,200,unused,1.5",
            "2026-07-15 09:30,11,12,13,10,110",
            "2026-07-15 09:31:45,12,13,14,11,120,240",
            "bad,row",
        ]
    )

    assert rows == [
        {
            "time": datetime(2026, 7, 15),
            "open": 10.0,
            "close": 11.0,
            "high": 12.0,
            "low": 9.0,
            "volume": 100.0,
            "amount": 200.0,
            "pct_chg": 1.5,
        },
        {
            "time": datetime(2026, 7, 15, 9, 30),
            "open": 11.0,
            "close": 12.0,
            "high": 13.0,
            "low": 10.0,
            "volume": 110.0,
            "amount": 0.0,
            "pct_chg": None,
        },
        {
            "time": datetime(2026, 7, 15, 9, 31, 45),
            "open": 12.0,
            "close": 13.0,
            "high": 14.0,
            "low": 11.0,
            "volume": 120.0,
            "amount": 240.0,
            "pct_chg": None,
        },
    ]


def test_parse_clist_rows_filters_invalid_items_and_safely_casts_numbers() -> None:
    rows = _parse_clist_rows(
        [
            {"f12": "600519", "f14": "Kweichow", "f2": "1688.5", "f3": "-", "f5": 10},
            {"f12": "bad", "f14": "ignored"},
            "noise",
        ]
    )

    assert rows == [
        {
            "code": "600519",
            "name": "Kweichow",
            "price": 1688.5,
            "pct_chg": None,
            "volume": 10.0,
            "amount": None,
            "turnover_pct": None,
            "volume_ratio": None,
            "total_cap": None,
            "float_cap": None,
        }
    ]


def test_daily_kline_params_support_date_range_and_recent_limit_modes() -> None:
    ranged = _daily_kline_params("600519", adjust="hfq", beg="20260101", end="20260716")
    recent = _daily_kline_params("000001", adjust="none", klt="102", lmt=2)

    assert ranged["secid"] == "1.600519"
    assert ranged["fqt"] == "2"
    assert ranged["beg"] == "20260101"
    assert ranged["end"] == "20260716"
    assert "lmt" not in ranged
    assert recent["secid"] == "0.000001"
    assert recent["klt"] == "102"
    assert recent["fqt"] == "0"
    assert recent["end"] == "20500101"
    assert recent["lmt"] == "5"
