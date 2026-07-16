"""Tests for pure bar-geometry primitives."""
from __future__ import annotations

from types import SimpleNamespace

from pa_agent.ai.bar_geometry import _count_trend_bars, _find_swings, _mean_overlap_ratio


def _bar(open_: float, high: float, low: float, close: float) -> SimpleNamespace:
    return SimpleNamespace(open=open_, high=high, low=low, close=close)


def test_count_trend_bars_uses_body_and_close_position_thresholds() -> None:
    bars = [
        _bar(10.0, 13.0, 9.0, 12.0),   # bull trend, close position 0.75
        _bar(12.0, 13.0, 9.0, 10.0),   # bear trend, close position 0.25
        _bar(10.0, 13.0, 9.0, 10.8),   # body ratio <= 0.25, ignored
        SimpleNamespace(open=1.0),      # malformed, ignored
    ]

    assert _count_trend_bars(bars, W=10) == (1, 1)


def test_mean_overlap_ratio_requires_two_valid_pairs() -> None:
    bars = [
        _bar(0.0, 10.0, 0.0, 5.0),
        _bar(0.0, 8.0, 2.0, 5.0),
        _bar(0.0, 12.0, 6.0, 9.0),
    ]

    # pair ratios: 6/10 and 2/10
    assert _mean_overlap_ratio(bars, W=3) == 0.4
    assert _mean_overlap_ratio(bars[:2], W=2) is None


def test_find_swings_uses_two_bar_pivots() -> None:
    bars = [
        _bar(0.0, 8.0, 5.0, 6.0),
        _bar(0.0, 9.0, 4.0, 6.0),
        _bar(0.0, 12.0, 2.0, 6.0),
        _bar(0.0, 9.0, 4.0, 6.0),
        _bar(0.0, 8.0, 5.0, 6.0),
    ]

    assert _find_swings(bars, W=5) == ([12.0], [2.0])


def test_find_swings_returns_empty_for_short_windows() -> None:
    assert _find_swings([_bar(0.0, 1.0, 0.0, 0.5)] * 4, W=4) == ([], [])
