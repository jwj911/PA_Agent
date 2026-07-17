"""Tests for Average True Range helpers."""

from __future__ import annotations

import math

import pytest

from pa_agent.indicators.atr import atr_full, make_atr_state, state_after_atr


def test_atr_full_returns_warmup_seed_and_wilder_smoothed_values() -> None:
    result = atr_full(
        highs=[11.0, 13.0, 16.0, 20.0],
        lows=[9.0, 10.0, 12.0, 13.0],
        closes=[10.0, 12.0, 14.0, 15.0],
        period=3,
    )

    assert len(result) == 4
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2] == 3.0
    assert result[3] == pytest.approx(13.0 / 3.0)


def test_atr_full_period_one_tracks_each_true_range() -> None:
    assert atr_full(
        highs=[11.0, 15.0],
        lows=[9.0, 10.0],
        closes=[10.0, 12.0],
        period=1,
    ) == [2.0, 5.0]


def test_atr_full_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="period must be >= 1"):
        atr_full([11.0], [9.0], [10.0], period=0)


def test_atr_full_rejects_mismatched_input_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        atr_full([11.0], [9.0, 10.0], [10.0], period=1)


def test_make_atr_state_starts_in_warmup_state() -> None:
    state = make_atr_state(period=3)

    assert math.isnan(state.last)
    assert state.period == 3
    assert state.count == 0
    assert math.isnan(state.prev_close)
    assert state._sum_tr == 0.0


def test_state_after_atr_matches_full_atr_last_value() -> None:
    highs = [11.0, 13.0, 16.0, 20.0]
    lows = [9.0, 10.0, 12.0, 13.0]
    closes = [10.0, 12.0, 14.0, 15.0]
    state = state_after_atr(highs, lows, closes, period=3)

    assert state.last == pytest.approx(atr_full(highs, lows, closes, period=3)[-1])
    assert state.period == 3
    assert state.count == len(highs)
    assert state.prev_close == closes[-1]
    assert state._sum_tr == 0.0
