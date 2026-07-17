"""Tests for validation error summary formatting."""

from __future__ import annotations

from pa_agent.ai.validation_messages import _label_one, format_validation_errors


def test_format_validation_errors_includes_missing_fields_first() -> None:
    summary = format_validation_errors(
        ["s1: direction invalid"],
        missing_fields=["decision.order_type", "bar_analysis.signal_bar"],
    )

    assert summary == (
        "\u7f3a\u5c11\u5b57\u6bb5: decision.order_type, bar_analysis.signal_bar"
        "\uff1b\u3010\u9636\u6bb5\u4e00\u3011direction invalid"
    )


def test_format_validation_errors_limits_invalid_items_and_reports_extra() -> None:
    summary = format_validation_errors(
        [
            "trace: node missing",
            "metrics: bad rr",
            "breakout_price: inside bar",
        ],
        max_items=2,
    )

    assert summary == (
        "\u3010\u51b3\u7b56\u8def\u5f84\u3011node missing"
        "\uff1b\u3010\u76c8\u4e8f\u6bd4/\u65b9\u7a0b\u3011bad rr"
        "\uff1b\u2026\u53e6\u6709 1 \u6761"
    )


def test_format_validation_errors_returns_empty_for_no_errors() -> None:
    assert format_validation_errors([]) == ""
    assert format_validation_errors([], missing_fields=[]) == ""


def test_label_one_matches_prefix_or_embedded_prefix() -> None:
    assert _label_one(" provider:quota_exhausted daily limit ") == (
        "\u3010API \u989d\u5ea6\u3011quota_exhausted daily limit"
    )
    assert _label_one("failed terminal.outcome mismatch") == (
        "\u3010\u7ec8\u5c40\u7ed3\u679c\u3011failed terminal.outcome mismatch"
    )


def test_label_one_falls_back_to_stripped_text() -> None:
    assert _label_one("  unknown problem  ") == "unknown problem"
