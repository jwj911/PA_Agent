"""Tests for data source factory and settings."""

from __future__ import annotations

import pytest

from pa_agent.config.settings import GeneralSettings
from pa_agent.data.eastmoney_source import EastMoneySource
from pa_agent.data.factory import (
    DATA_SOURCE_CHOICES,
    create_data_source,
    data_source_choices,
    default_symbol_for_kind,
    default_tradingview_exchange,
    normalize_data_source_kind,
    register_data_source,
    unregister_data_source,
)
from pa_agent.data.mt5 import MT5Source
from pa_agent.data.tradingview import TradingViewSource
from pa_agent.data.tushare_source import TushareSource


def test_normalize_data_source_kind_defaults_unknown():
    assert normalize_data_source_kind("invalid") == "mt5"
    assert normalize_data_source_kind(None) == "mt5"


def test_normalize_data_source_kind_hidden_sources():
    assert normalize_data_source_kind("akshare") == "akshare"
    assert normalize_data_source_kind("eastmoney") == "eastmoney"
    assert normalize_data_source_kind("tushare") == "tushare"
    assert normalize_data_source_kind("yfinance") == "yfinance"


def test_eastmoney_not_in_ui_choices():
    ui_kinds = {k for k, _ in DATA_SOURCE_CHOICES}
    assert "eastmoney" not in ui_kinds
    assert "akshare" not in ui_kinds


def test_tushare_not_in_ui_choices():
    ui_kinds = {k for k, _ in DATA_SOURCE_CHOICES}
    assert "tushare" not in ui_kinds


def test_create_data_source_returns_expected_types():
    assert isinstance(create_data_source("mt5"), MT5Source)
    assert isinstance(create_data_source("tradingview"), TradingViewSource)
    assert isinstance(create_data_source("eastmoney"), EastMoneySource)
    assert isinstance(create_data_source("tushare"), TushareSource)


def test_default_symbols_per_kind():
    assert default_symbol_for_kind("mt5") == "XAUUSDm"
    assert default_symbol_for_kind("tradingview") == "XAUUSD"
    assert default_symbol_for_kind("eastmoney") == "000001"
    assert default_symbol_for_kind("tushare") == "000001"


def test_default_tradingview_exchange_is_auto():
    assert default_tradingview_exchange() == ""


def test_runtime_data_source_registration_is_visible_and_creatable():
    custom = MT5Source()
    register_data_source(
        "test_source",
        label="测试数据源",
        default_symbol="TEST",
        builder=lambda _settings: custom,
        visible=True,
    )
    try:
        assert normalize_data_source_kind("test_source") == "test_source"
        assert ("test_source", "测试数据源") in data_source_choices()
        assert default_symbol_for_kind("test_source") == "TEST"
        assert create_data_source("test_source") is custom
    finally:
        unregister_data_source("test_source")


def test_runtime_data_source_registration_rejects_duplicate_kind():
    register_data_source(
        "test_source",
        label="测试数据源",
        default_symbol="TEST",
        builder=lambda _settings: MT5Source(),
    )
    try:
        with pytest.raises(ValueError, match="already registered"):
            register_data_source(
                "test_source",
                label="重复数据源",
                default_symbol="TEST2",
                builder=lambda _settings: MT5Source(),
            )
    finally:
        unregister_data_source("test_source")


def test_general_settings_last_data_source_default():
    g = GeneralSettings()
    assert g.last_data_source == "mt5"
