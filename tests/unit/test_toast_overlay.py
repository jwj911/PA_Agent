"""Tests for the toast overlay widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from pa_agent.gui.widgets.toast import ToastOverlay, _ToastLabel

_APP: QApplication | None = None


def _ensure_app() -> None:
    global _APP
    _APP = QApplication.instance() or QApplication([])


def _make_parent(width: int = 500, height: int = 300) -> QWidget:
    _ensure_app()
    parent = QWidget()
    parent.resize(width, height)
    return parent


def test_toast_label_uses_wrapped_centered_message_style() -> None:
    _ensure_app()
    label = _ToastLabel("analysis complete")

    assert label.text() == "analysis complete"
    assert label.wordWrap() is True
    assert label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert "background-color: rgba(28,33,40,0.92)" in label.styleSheet()
    assert "border: 1px solid #38bdf8" in label.styleSheet()


def test_toast_overlay_adds_message_and_positions_bottom_right() -> None:
    parent = _make_parent()
    overlay = ToastOverlay(parent)

    overlay.show_message("done", duration_ms=600_000)

    assert [toast.text() for toast in overlay._toasts] == ["done"]
    assert overlay._layout.count() == 1
    assert overlay.geometry().x() == 164
    assert overlay.geometry().y() == 84
    assert overlay.geometry().width() == 320
    assert overlay.geometry().height() == 200


def test_toast_overlay_dismiss_removes_toast_and_layout_item() -> None:
    parent = _make_parent()
    overlay = ToastOverlay(parent)
    overlay.show_message("done", duration_ms=600_000)
    toast = overlay._toasts[0]

    overlay._dismiss(toast)

    assert overlay._toasts == []
    assert overlay._layout.count() == 0


def test_toast_overlay_without_parent_reposition_is_noop() -> None:
    _ensure_app()
    overlay = ToastOverlay()
    before = overlay.geometry()

    overlay._reposition()

    assert overlay.geometry() == before
