"""Tests for the enhanced status bar widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.widgets.status_bar import EnhancedStatusBar

_APP: QApplication | None = None


def _make_status_bar() -> EnhancedStatusBar:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return EnhancedStatusBar()


def test_status_bar_message_aliases() -> None:
    bar = _make_status_bar()

    bar.set_message("ready")
    assert bar.currentMessage() == "ready"

    bar.showMessage("running")
    assert bar.currentMessage() == "running"


def test_status_bar_progress_updates_value_and_label() -> None:
    bar = _make_status_bar()

    bar.set_progress(42.8)
    assert bar._progress.value() == 42
    assert bar._progress_label.text() == "42.8%"

    bar.set_progress(12, label="12% \u00b7 120 / 1000")
    assert bar._progress.value() == 12
    assert bar._progress_label.text() == "12% \u00b7 120 / 1000"


def test_status_bar_progress_color_falls_back_to_normal() -> None:
    bar = _make_status_bar()

    bar.set_progress_color("red")
    assert "#ef4444" in bar._progress.styleSheet()

    bar.set_progress_color("unknown")
    assert "#38bdf8" in bar._progress.styleSheet()


def test_status_bar_tps_label_shows_positive_values_and_hides_zero() -> None:
    bar = _make_status_bar()

    bar.set_tps(8.25)
    assert bar._tps_label.text() == "8.2 TPS"
    assert not bar._tps_label.isHidden()

    bar.set_tps(1.0, label="custom")
    assert bar._tps_label.text() == "custom"
    assert not bar._tps_label.isHidden()

    bar.set_tps(0)
    assert bar._tps_label.isHidden()
