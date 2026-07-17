"""Tests for the GUI widgets package exports."""

from __future__ import annotations

from pa_agent.gui import widgets
from pa_agent.gui.widgets.candle_item import CandleItem
from pa_agent.gui.widgets.chart_panel import ChartPanel
from pa_agent.gui.widgets.flow_bar import FlowBar
from pa_agent.gui.widgets.model_selector import ModelSelector
from pa_agent.gui.widgets.overlay_lines import OverlayLines
from pa_agent.gui.widgets.seq_label_item import SeqLabelItem
from pa_agent.gui.widgets.status_bar import EnhancedStatusBar
from pa_agent.gui.widgets.summary_strip import SummaryStrip
from pa_agent.gui.widgets.toast import ToastOverlay


def test_widgets_package_exports_expected_public_names() -> None:
    assert widgets.__all__ == [
        "CandleItem",
        "ChartPanel",
        "EnhancedStatusBar",
        "FlowBar",
        "ModelSelector",
        "OverlayLines",
        "SeqLabelItem",
        "SummaryStrip",
        "ToastOverlay",
    ]


def test_widgets_package_public_names_are_bound_to_widget_classes() -> None:
    assert widgets.CandleItem is CandleItem
    assert widgets.ChartPanel is ChartPanel
    assert widgets.EnhancedStatusBar is EnhancedStatusBar
    assert widgets.FlowBar is FlowBar
    assert widgets.ModelSelector is ModelSelector
    assert widgets.OverlayLines is OverlayLines
    assert widgets.SeqLabelItem is SeqLabelItem
    assert widgets.SummaryStrip is SummaryStrip
    assert widgets.ToastOverlay is ToastOverlay
