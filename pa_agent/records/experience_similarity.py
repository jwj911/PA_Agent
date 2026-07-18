"""Deterministic K-line similarity scoring for experience retrieval.

The experience library stores arbitrary JSON dictionaries, so similarity is
optional and must degrade cleanly for legacy entries without ``kline_data``.
Scores are based on scale-free recent-bar geometry rather than absolute prices:
body ratio, close position, candle direction, and range relative to the local
median range.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from statistics import median
from typing import Any

from pa_agent.data.base import KlineBar

DEFAULT_SIMILARITY_WINDOW = 12


def score_kline_similarity(
    current_bars: Sequence[KlineBar],
    candidate_content: Mapping[str, Any],
    *,
    window: int = DEFAULT_SIMILARITY_WINDOW,
) -> float | None:
    """Return a scale-free geometry similarity score in ``[0, 1]``.

    ``None`` means that either side has fewer than three usable bars or the
    candidate does not contain a supported bar list.  Bars are newest-first,
    matching ``KlineFrame.bars`` and persisted ``AnalysisRecord.kline_data``.
    The score intentionally ignores timestamps and absolute price levels.
    """
    if window <= 0:
        return None

    candidate_bars = _extract_candidate_bars(candidate_content)
    if candidate_bars is None:
        return None

    current = _bar_signatures(list(current_bars)[:window])
    candidate = _mapping_signatures(candidate_bars[:window])
    count = min(len(current), len(candidate))
    if count < 3:
        return None

    current = _with_relative_ranges(current[:count])
    candidate = _with_relative_ranges(candidate[:count])

    # Direction, body shape and close location carry the most structural
    # information. Relative range prevents a large/small volatility regime
    # from being treated as identical while remaining instrument-independent.
    weights = (1.2, 1.0, 1.0, 0.8)
    distances: list[float] = []
    for left, right in zip(current, candidate, strict=True):
        values = (
            abs(left[0] - right[0]) / 2.0,
            abs(left[1] - right[1]),
            abs(left[2] - right[2]),
            min(abs(left[3] - right[3]) / 4.0, 1.0),
        )
        distances.append(sum(value * weight for value, weight in zip(values, weights, strict=True)))

    max_distance = sum(weights)
    return max(0.0, min(1.0, 1.0 - sum(distances) / (len(distances) * max_distance)))


def _extract_candidate_bars(content: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    raw: Any = content.get("kline_data")
    if not isinstance(raw, list):
        nested = content.get("record")
        if isinstance(nested, Mapping):
            raw = nested.get("kline_data")
    if not isinstance(raw, list) or not raw:
        return None
    if not all(isinstance(item, Mapping) for item in raw):
        return None
    return raw


def _bar_signatures(bars: Sequence[KlineBar]) -> list[tuple[float, float, float, float]]:
    return _build_signatures([(bar.open, bar.high, bar.low, bar.close) for bar in bars])


def _mapping_signatures(
    bars: Sequence[Mapping[str, Any]],
) -> list[tuple[float, float, float, float]]:
    values: list[tuple[float, float, float, float]] = []
    for bar in bars:
        try:
            values.append(
                (
                    float(bar["open"]),
                    float(bar["high"]),
                    float(bar["low"]),
                    float(bar["close"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            return []
    return _build_signatures(values)


def _build_signatures(
    bars: Sequence[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    signatures: list[tuple[float, float, float, float]] = []
    for open_, high, low, close in bars:
        if not all(math.isfinite(value) for value in (open_, high, low, close)):
            return []
        high = max(high, low)
        low = min(high, low)
        full_range = high - low
        if full_range > 0:
            body_ratio = min(abs(close - open_) / full_range, 1.0)
            close_position = max(0.0, min(1.0, (close - low) / full_range))
        else:
            body_ratio = 0.0
            close_position = 0.5
        direction = 1.0 if close > open_ else -1.0 if close < open_ else 0.0
        signatures.append((direction, body_ratio, close_position, full_range))
    return signatures


def _with_relative_ranges(
    signatures: Sequence[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    positive_ranges = [item[3] for item in signatures if item[3] > 0]
    scale = median(positive_ranges) if positive_ranges else 1.0
    return [
        (direction, body_ratio, close_position, min(full_range / scale, 4.0))
        for direction, body_ratio, close_position, full_range in signatures
    ]
