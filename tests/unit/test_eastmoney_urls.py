"""Tests for East Money quote page URL helpers."""
from __future__ import annotations

from pa_agent.data.eastmoney_urls import quote_page_url, quote_page_url_simple


def test_quote_page_url_uses_shanghai_prefix_for_sh_stock() -> None:
    assert quote_page_url("SH600519", timeframe="1m") == (
        "https://quote.eastmoney.com/sh600519.html?klt=1"
    )


def test_quote_page_url_uses_shenzhen_prefix_for_sz_stock() -> None:
    assert quote_page_url("000001", timeframe="5m") == (
        "https://quote.eastmoney.com/sz000001.html?klt=5"
    )


def test_quote_page_url_uses_index_prefix_for_unprefixed_known_indices() -> None:
    assert quote_page_url("000300", timeframe="1w") == (
        "https://quote.eastmoney.com/zs000300.html?klt=102"
    )


def test_quote_page_url_preserves_explicit_exchange_prefix() -> None:
    assert quote_page_url("sh000300", timeframe="1w") == (
        "https://quote.eastmoney.com/sh000300.html?klt=102"
    )


def test_quote_page_url_defaults_unknown_timeframe_to_daily() -> None:
    assert quote_page_url("600519", timeframe="unknown") == (
        "https://quote.eastmoney.com/sh600519.html?klt=101"
    )


def test_quote_page_url_falls_back_for_empty_symbol() -> None:
    assert quote_page_url("", timeframe="1M") == (
        "https://quote.eastmoney.com/sh000001.html?klt=103"
    )


def test_quote_page_url_simple_omits_kline_hint() -> None:
    assert quote_page_url_simple("300750") == "https://quote.eastmoney.com/sz300750.html"
