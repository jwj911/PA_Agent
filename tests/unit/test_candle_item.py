"""Tests for the chart candlestick graphics item."""
from __future__ import annotations

import pytest

from pa_agent.data.base import KlineBar
from pa_agent.gui.widgets.candle_item import CandleItem


def _bar(
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    seq: int = 1,
    closed: bool = True,
) -> KlineBar:
    return KlineBar(
        seq=seq,
        ts_open=0.0,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1.0,
        closed=closed,
    )


def test_candle_item_body_bounds_follow_open_close_extremes() -> None:
    bullish = _bar(open_=10.0, high=13.0, low=9.0, close=12.0)
    bearish = _bar(open_=12.0, high=13.0, low=9.0, close=10.0)

    assert CandleItem._body_bounds(bullish) == (12.0, 10.0)
    assert CandleItem._body_bounds(bearish) == (12.0, 10.0)


def test_candle_item_body_bounds_expands_flat_doji() -> None:
    doji = _bar(open_=10.0, high=11.0, low=9.0, close=10.0)

    body_top, body_bottom = CandleItem._body_bounds(doji)

    assert body_top == pytest.approx(10.00000001)
    assert body_bottom == pytest.approx(9.99999999)


def test_candle_item_bounding_rect_uses_closed_body_width_and_price_margin() -> None:
    item = CandleItem(_bar(open_=10.0, high=13.0, low=9.0, close=12.0), 4)

    rect = item.boundingRect()

    assert rect.x() == pytest.approx(3.66)
    assert rect.y() == pytest.approx(8.79999999)
    assert rect.width() == pytest.approx(0.68)
    assert rect.height() == pytest.approx(4.40000002)


def test_candle_item_update_bar_switches_to_forming_geometry() -> None:
    item = CandleItem(_bar(open_=10.0, high=13.0, low=9.0, close=12.0), 4)
    forming_bar = _bar(
        open_=10.0,
        high=10.0,
        low=10.0,
        close=10.0,
        seq=0,
        closed=False,
    )

    item.update_bar(forming_bar, forming=True)
    rect = item.boundingRect()

    assert item._bar is forming_bar
    assert item._forming is True
    assert rect.x() == pytest.approx(3.71)
    assert rect.y() == pytest.approx(9.99999999)
    assert rect.width() == pytest.approx(0.58)
    assert rect.height() == pytest.approx(0.00000002)
