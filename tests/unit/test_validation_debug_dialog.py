"""Tests for the validation debug dialog helper."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QTextEdit

from pa_agent.gui.validation_debug_dialog import show_validation_debug_dialog

_APP: QApplication | None = None


def _ensure_app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_validation_debug_dialog_builds_scrollable_debug_content(monkeypatch) -> None:
    _ensure_app()
    dialogs: list[QDialog] = []

    def fake_exec(self: QDialog) -> int:
        dialogs.append(self)
        return 0

    monkeypatch.setattr(QDialog, "exec", fake_exec)

    show_validation_debug_dialog(
        None,
        title="Validation failed",
        summary="Missing field",
        body='{"error": true}',
    )

    assert len(dialogs) == 1
    dialog = dialogs[0]
    assert dialog.windowTitle() == "Validation failed"
    assert dialog.size().width() == 760
    assert dialog.size().height() == 520

    labels = {label.text(): label for label in dialog.findChildren(QLabel)}
    assert labels["Missing field"].wordWrap()

    edits = dialog.findChildren(QTextEdit)
    assert len(edits) == 1
    assert edits[0].isReadOnly()
    assert edits[0].toPlainText() == '{"error": true}'

    assert {button.text() for button in dialog.findChildren(QPushButton)} == {"复制全部", "关闭"}


def test_validation_debug_dialog_omits_blank_summary_and_copies_body(monkeypatch) -> None:
    app = _ensure_app()
    dialogs: list[QDialog] = []

    def fake_exec(self: QDialog) -> int:
        dialogs.append(self)
        copy_button = next(
            button for button in self.findChildren(QPushButton) if button.text() == "复制全部"
        )
        copy_button.click()
        return 0

    monkeypatch.setattr(QDialog, "exec", fake_exec)

    show_validation_debug_dialog(
        None,
        title="Debug",
        summary="   ",
        body="full body",
    )

    assert [label.text() for label in dialogs[0].findChildren(QLabel)] == []
    assert app.clipboard().text() == "full body"
