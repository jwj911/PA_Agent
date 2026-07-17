"""Tests for Exponential Moving Average helpers."""

from __future__ import annotations

import math

import pytest

from pa_agent.indicators.ema import ema_full, make_ema_state, state_after


def test_ema_full_returns_warmup_seed_and_smoothed_values() -> None:
    result = ema_full([10.0, 12.0, 14.0, 16.0], period=3)

    assert len(result) == 4
    assert math.isnan(result[0])
    assert math.isnan(result[1])
    assert result[2:] == [12.0, 14.0]


def test_ema_full_period_one_tracks_each_input_value() -> None:
    assert ema_full([10.0, 12.0, 14.0], period=1) == [10.0, 12.0, 14.0]


def test_ema_full_rejects_invalid_period() -> None:
    with pytest.raises(ValueError, match="period must be >= 1"):
        ema_full([10.0], period=0)


def test_make_ema_state_starts_in_warmup_state() -> None:
    state = make_ema_state(period=3)

    assert math.isnan(state.last)
    assert state.period == 3
    assert state.count == 0
    assert state._sum == 0.0


def test_state_after_matches_full_ema_last_value() -> None:
    values = [10.0, 12.0, 14.0, 16.0]
    state = state_after(values, period=3)

    assert state.last == ema_full(values, period=3)[-1]
    assert state.period == 3
    assert state.count == len(values)
    assert state._sum == 0.0
