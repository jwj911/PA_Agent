"""Tests for the indicators package marker."""

from __future__ import annotations

import importlib


def test_indicators_package_marker_imports_without_public_exports() -> None:
    module = importlib.import_module("pa_agent.indicators")

    assert module.__name__ == "pa_agent.indicators"
    assert module.__doc__ == "PA Agent indicators package."
    assert not hasattr(module, "__all__")
    assert not hasattr(module, "atr_full")
    assert not hasattr(module, "ema_full")
