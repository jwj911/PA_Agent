"""Tests for filename component sanitization."""

from __future__ import annotations

import pytest

from pa_agent.util.safe_filename import sanitize_filename_component


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("XAU/USD", "XAU-USD"),
        ("../../etc/passwd", "etc-passwd"),
        ('bad<name>:"quote"|?.txt', "bad-name---quote---.txt"),
        (" name. ", "name"),
        ("---symbol---", "symbol"),
        ("\x00bad\x1fname", "bad-name"),
        ("15m", "15m"),
    ],
)
def test_sanitize_filename_component_replaces_or_strips_unsafe_characters(
    value: str,
    expected: str,
) -> None:
    assert sanitize_filename_component(value) == expected


@pytest.mark.parametrize("value", ["", " ", "...", "---", " .-. "])
def test_sanitize_filename_component_uses_fallback_for_empty_result(value: str) -> None:
    assert sanitize_filename_component(value, fallback="fallback") == "fallback"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("CON", "_CON"),
        ("nul.csv", "_nul.csv"),
        ("COM1", "_COM1"),
        ("lpt9.log", "_lpt9.log"),
    ],
)
def test_sanitize_filename_component_prefixes_windows_reserved_names(
    value: str,
    expected: str,
) -> None:
    assert sanitize_filename_component(value) == expected
