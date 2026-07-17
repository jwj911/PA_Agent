"""Tests for shared prediction display formatting helpers."""

from __future__ import annotations

from pa_agent.gui.prediction_format import (
    _dominant_prediction_direction,
    _format_prediction_probs_line,
)


def test_format_prediction_probs_line_uses_display_labels() -> None:
    assert _format_prediction_probs_line({"bullish": 60, "bearish": 25, "neutral": 15}) == (
        "\u9633\u7ebf\u7684\u6982\u7387\u4e3a60%  \u00b7  "
        "\u9634\u7ebf\u7684\u6982\u7387\u4e3a25%  \u00b7  "
        "\u4e2d\u6027\u7684\u6982\u7387\u4e3a15%"
    )


def test_format_prediction_probs_line_falls_back_to_question_marks() -> None:
    assert _format_prediction_probs_line({}) == (
        "\u9633\u7ebf\u7684\u6982\u7387\u4e3a?%  \u00b7  "
        "\u9634\u7ebf\u7684\u6982\u7387\u4e3a?%  \u00b7  "
        "\u4e2d\u6027\u7684\u6982\u7387\u4e3a?%"
    )


def test_dominant_prediction_direction_returns_highest_numeric_value() -> None:
    assert (
        _dominant_prediction_direction({"bullish": "40.5", "bearish": 41, "neutral": 18.5})
        == "bearish"
    )


def test_dominant_prediction_direction_ignores_invalid_values() -> None:
    assert (
        _dominant_prediction_direction({"bullish": "bad", "bearish": "", "neutral": 7}) == "neutral"
    )


def test_dominant_prediction_direction_returns_none_without_parseable_values() -> None:
    assert _dominant_prediction_direction({}) is None
    assert _dominant_prediction_direction({"bullish": None, "bearish": "x"}) is None
