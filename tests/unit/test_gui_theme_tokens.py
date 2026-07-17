"""Tests for GUI theme design tokens."""

from __future__ import annotations

import re

from pa_agent.gui.theme import tokens

_HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$")
_RGBA_COLOR = re.compile(r"^rgba\(\d{1,3},\d{1,3},\d{1,3},0\.\d{2}\)$")


def test_theme_canonical_color_tokens_use_expected_formats() -> None:
    for name in (
        "BG",
        "SURFACE_1",
        "SURFACE_2",
        "SURFACE_3",
        "SURFACE_4",
        "FG",
        "FG_2",
        "FG_3",
        "ACCENT",
        "ACCENT_2",
        "ACCENT_3",
        "SUCCESS",
        "DANGER",
        "WARNING",
        "INFO",
        "CHART_UP",
        "CHART_DOWN",
        "CHART_GRID",
        "CHART_LINE",
        "CHART_LINE_2",
        "CHART_LINE_3",
    ):
        assert _HEX_COLOR.fullmatch(getattr(tokens, name))


def test_theme_pill_tokens_keep_rgba_background_and_border_formats() -> None:
    for prefix in ("GREEN", "AMBER", "BLUE", "RED", "CYAN"):
        assert _HEX_COLOR.fullmatch(getattr(tokens, f"PILL_{prefix}_TEXT"))
        assert _RGBA_COLOR.fullmatch(getattr(tokens, f"PILL_{prefix}_BORDER"))
        assert _RGBA_COLOR.fullmatch(getattr(tokens, f"PILL_{prefix}_BG"))


def test_theme_typography_and_layout_tokens_keep_expected_values() -> None:
    assert tokens.FONT_UI == '"Segoe UI", "Microsoft YaHei UI", sans-serif'
    assert tokens.FONT_MONO == '"JetBrains Mono", "Cascadia Mono", "Consolas", monospace'
    assert tokens.RADIUS == 6
    assert tokens.SPACING == 8


def test_theme_legacy_aliases_are_bound_to_canonical_tokens() -> None:
    assert tokens.BG_BASE == tokens.BG
    assert tokens.BG_PANEL == tokens.SURFACE_1
    assert tokens.BG_ELEVATED == tokens.SURFACE_2
    assert tokens.BORDER == tokens.SURFACE_4
    assert tokens.BORDER_MUTED == tokens.SURFACE_3
    assert tokens.TEXT_PRIMARY == tokens.FG
    assert tokens.TEXT_SECONDARY == tokens.FG_2
    assert tokens.TEXT_MUTED == tokens.FG_3
    assert tokens.ACCENT_PRIMARY == tokens.ACCENT_3
    assert tokens.ACCENT_REASONING == tokens.ACCENT
    assert tokens.ACCENT_SUCCESS == tokens.SUCCESS
    assert tokens.ACCENT_WARNING == tokens.WARNING
    assert tokens.ACCENT_DANGER == tokens.DANGER
    assert tokens.TRADE_LONG == tokens.CHART_UP
    assert tokens.TRADE_SHORT == tokens.CHART_DOWN
    assert tokens.TRADE_NEUTRAL == tokens.FG_2
    assert tokens.TOKEN_YELLOW == tokens.WARNING
    assert tokens.TOKEN_RED == tokens.DANGER
