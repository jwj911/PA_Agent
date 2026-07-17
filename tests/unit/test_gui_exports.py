"""Tests for the GUI package exports."""

from __future__ import annotations

from pa_agent import gui
from pa_agent.gui.chart_widget import ChartWidget
from pa_agent.gui.conversation_widget import ConversationWidget
from pa_agent.gui.debug_widget import DebugWidget
from pa_agent.gui.decision_panel import DecisionPanel
from pa_agent.gui.main_window import MainWindow
from pa_agent.gui.settings_dialog import SettingsDialog


def test_gui_package_exports_expected_public_names() -> None:
    assert gui.__all__ == [
        "ChartWidget",
        "ConversationWidget",
        "DebugWidget",
        "DecisionPanel",
        "MainWindow",
        "SettingsDialog",
    ]


def test_gui_package_public_names_are_bound_to_gui_classes() -> None:
    assert gui.ChartWidget is ChartWidget
    assert gui.ConversationWidget is ConversationWidget
    assert gui.DebugWidget is DebugWidget
    assert gui.DecisionPanel is DecisionPanel
    assert gui.MainWindow is MainWindow
    assert gui.SettingsDialog is SettingsDialog
