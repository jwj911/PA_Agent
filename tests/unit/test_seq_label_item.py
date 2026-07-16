"""Tests for the chart sequence label item."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.widgets.seq_label_item import SeqLabelItem

_APP: QApplication | None = None


def _make_seq_label(
    seq: int,
    x_pos: int,
    y_pos: float,
    *,
    font_pt: int = 7,
    forming: bool = False,
) -> SeqLabelItem:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return SeqLabelItem(seq, x_pos, y_pos, font_pt=font_pt, forming=forming)


def test_seq_label_item_uses_default_text_position_font_and_anchor() -> None:
    item = _make_seq_label(12, -1, 99.25)

    assert item.toPlainText() == "#12"
    assert item.pos().x() == -1.0
    assert item.pos().y() == 99.25
    assert item.textItem.defaultTextColor().getRgb() == (180, 180, 180, 255)
    assert item.textItem.font().pointSize() == 7
    assert item.anchor.x() == 0.5
    assert item.anchor.y() == 1.0


def test_seq_label_item_marks_forming_bar_with_custom_font_and_color() -> None:
    item = _make_seq_label(3, 2, 101.5, font_pt=9, forming=True)

    assert item.toPlainText() == "#3"
    assert item.pos().x() == 2.0
    assert item.pos().y() == 101.5
    assert item.textItem.defaultTextColor().getRgb() == (120, 200, 220, 200)
    assert item.textItem.font().pointSize() == 9
