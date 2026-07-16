"""Tests for the GUI theme package exports."""
from __future__ import annotations

from pa_agent.gui import theme
from pa_agent.gui.theme.apply import apply_theme


def test_gui_theme_package_exports_expected_public_names() -> None:
    assert theme.__all__ == ["apply_theme"]


def test_gui_theme_public_names_are_bound_to_theme_functions() -> None:
    assert theme.apply_theme is apply_theme
