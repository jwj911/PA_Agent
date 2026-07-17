"""Tests for the AI summary strip widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.widgets.summary_strip import SummaryStrip

_APP: QApplication | None = None


def _make_summary_strip() -> SummaryStrip:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return SummaryStrip()


def _card_values(strip: SummaryStrip) -> dict[str, str]:
    return {card._title.text(): card._value.text() for card in strip._cards}


def test_summary_strip_initializes_default_metric_cards() -> None:
    strip = _make_summary_strip()

    assert strip.objectName() == "summaryStrip"
    assert list(_card_values(strip)) == [
        "当前趋势",
        "当前市场周期",
        "下一个市场周期",
        "支撑区",
        "阻力区",
    ]
    assert set(_card_values(strip).values()) == {"—"}
    assert strip._layout.count() == 5
    assert strip._columns == 5


def test_summary_strip_updates_matching_metrics_only() -> None:
    strip = _make_summary_strip()

    strip.set_metrics(
        {
            "当前趋势": "上涨",
            "阻力区": "3100-3120",
            "未知字段": "should be ignored",
        }
    )

    assert _card_values(strip) == {
        "当前趋势": "上涨",
        "当前市场周期": "—",
        "下一个市场周期": "—",
        "支撑区": "—",
        "阻力区": "3100-3120",
    }


def test_summary_strip_reset_restores_default_values() -> None:
    strip = _make_summary_strip()

    strip.set_metrics({"当前趋势": "下跌", "支撑区": "3000"})
    strip.reset()

    assert set(_card_values(strip).values()) == {"—"}


def test_summary_strip_relayout_keeps_all_cards_in_grid() -> None:
    strip = _make_summary_strip()

    strip._columns = 0
    strip._relayout()

    assert strip._layout.count() == 5
    assert [strip._layout.itemAt(i).widget() for i in range(strip._layout.count())] == strip._cards
