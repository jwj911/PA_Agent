"""Tests for East Money Baostock fallback helpers."""

from __future__ import annotations

import pytest

from pa_agent.data.base import DataSourceTransientError
from pa_agent.data.eastmoney_baostock import (
    _baostock_code,
    eastmoney_rolling_cap,
    fetch_minute_history_baostock,
    needs_baostock_history,
)


def test_eastmoney_rolling_cap_defaults_to_128():
    assert eastmoney_rolling_cap("60") == 128
    assert eastmoney_rolling_cap("unknown") == 128


def test_needs_baostock_history_compares_requested_window():
    assert needs_baostock_history("1h", "60", 120) is False
    assert needs_baostock_history("1h", "60", 121) is True
    assert needs_baostock_history("4h", "60", 30) is False
    assert needs_baostock_history("4h", "60", 31) is True


def test_baostock_code_normalizes_exchange_prefixes():
    assert _baostock_code("600519") == "sh.600519"
    assert _baostock_code("000001") == "sz.000001"
    assert _baostock_code("sh600519") == "sh.600519"


def test_fetch_minute_history_rejects_index_before_importing_baostock():
    with pytest.raises(DataSourceTransientError, match="指数分钟线"):
        fetch_minute_history_baostock("000300", "1h", 10)
