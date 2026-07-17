"""Pure bar-geometry primitives for the decision node engine.

Stdlib-only helpers (no project imports, no side effects) split out of
:mod:`pa_agent.ai.decision_nodes` (report §5.2 M3). These compute low-level
K-line geometry over a window of bars and are shared by both ``decision_nodes``
(which re-exports them so existing ``from pa_agent.ai.decision_nodes import ...``
sites keep working) and ``trend_context``.

Behaviour must stay identical to the originals: the section-judges depend on
these exact classification thresholds (trend-bar body/close-position cutoffs,
overlap ratio, 2-bar swing pivots).
"""

from __future__ import annotations

from typing import Any


def _count_trend_bars(bars: Any, W: int) -> tuple[int, int]:
    """Count bull-trend and bear-trend bars in the first W bars.

    A bull-trend bar: close > open AND close_position >= 0.65.
    A bear-trend bar: close < open AND close_position <= 0.35.
    Matches kline_features._classify_bar logic (inline for independence).
    """
    bull = 0
    bear = 0
    for bar in list(bars)[:W]:
        try:
            high = max(float(bar.high), float(bar.low))
            low = min(float(bar.high), float(bar.low))
            open_ = float(bar.open)
            close = float(bar.close)
            full_range = high - low
            if full_range <= 0:
                continue
            body = abs(close - open_)
            body_ratio = body / full_range
            close_pos = max(0.0, min(1.0, (close - low) / full_range))
            if body_ratio <= 0.25:
                continue  # doji — not a trend bar
            if close > open_ and close_pos >= 0.65:
                bull += 1
            elif close < open_ and close_pos <= 0.35:
                bear += 1
        except (TypeError, ValueError, AttributeError):
            continue
    return bull, bear


def _mean_overlap_ratio(bars: Any, W: int) -> float | None:
    """Compute mean overlap_prev_ratio for adjacent bar pairs in window.

    Returns None if fewer than 2 valid pairs.
    overlap = shared high-low range / union high-low range.
    """
    window = list(bars)[:W]
    ratios: list[float] = []
    for i in range(len(window) - 1):
        try:
            cur = window[i]
            prv = window[i + 1]
            cur_h = max(float(cur.high), float(cur.low))
            cur_l = min(float(cur.high), float(cur.low))
            prv_h = max(float(prv.high), float(prv.low))
            prv_l = min(float(prv.high), float(prv.low))
            overlap = max(0.0, min(cur_h, prv_h) - max(cur_l, prv_l))
            union = max(cur_h, prv_h) - min(cur_l, prv_l)
            if union > 0:
                ratios.append(overlap / union)
        except (TypeError, ValueError, AttributeError):
            continue
    if len(ratios) < 2:
        return None
    return sum(ratios) / len(ratios)


def _find_swings(bars: Any, W: int) -> tuple[list[float], list[float]]:
    """Find swing highs and lows using left/right 2-bar pivot detection."""
    window = list(bars[:W])
    if len(window) < 5:
        return [], []

    swing_highs: list[float] = []
    swing_lows: list[float] = []

    for i in range(2, len(window) - 2):
        h = float(window[i].high)
        if (
            float(window[i - 1].high) < h
            and float(window[i - 2].high) < h
            and float(window[i + 1].high) < h
            and float(window[i + 2].high) < h
        ):
            swing_highs.append(h)

        lo = float(window[i].low)
        if (
            float(window[i - 1].low) > lo
            and float(window[i - 2].low) > lo
            and float(window[i + 1].low) > lo
            and float(window[i + 2].low) > lo
        ):
            swing_lows.append(lo)

    return swing_highs, swing_lows
