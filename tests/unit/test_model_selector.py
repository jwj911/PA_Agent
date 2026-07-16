"""Tests for the model selector widgets."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.widgets.model_selector import ModelDropdown, ModelSelector

_APP: QApplication | None = None


def _ensure_app() -> None:
    global _APP
    _APP = QApplication.instance() or QApplication([])


def _model_groups() -> list[tuple[str, list[tuple[str, str]]]]:
    return [
        ("Primary", [("deepseek-chat", "fast"), ("deepseek-reasoner", "slow")]),
        ("Backup", [("qclaw", "local")]),
    ]


def test_model_dropdown_populates_grouped_options_and_selection() -> None:
    _ensure_app()
    dropdown = ModelDropdown()

    dropdown.set_groups(_model_groups())
    dropdown.set_current_model("deepseek-reasoner")

    assert dropdown._layout.count() == 6
    assert [option._model_id for option in dropdown._options] == [
        "deepseek-chat",
        "deepseek-reasoner",
        "qclaw",
    ]
    assert [option._selected for option in dropdown._options] == [False, True, False]


def test_model_dropdown_rebuilds_options_when_groups_change() -> None:
    _ensure_app()
    dropdown = ModelDropdown()
    dropdown.set_groups(_model_groups())

    dropdown.set_groups([("Solo", [("local-model", "mock")])])

    assert dropdown._layout.count() == 2
    assert [option._model_id for option in dropdown._options] == ["local-model"]


def test_model_dropdown_selected_callback_emits_model_id() -> None:
    _ensure_app()
    dropdown = ModelDropdown()
    selected: list[str] = []
    dropdown.model_selected.connect(selected.append)

    dropdown._on_selected("qclaw")

    assert selected == ["qclaw"]


def test_model_selector_updates_name_groups_and_selection_signal() -> None:
    _ensure_app()
    selector = ModelSelector()
    selected: list[str] = []
    selector.model_selected.connect(selected.append)

    selector.set_model_groups(_model_groups())
    selector.set_model_name("deepseek-chat")
    selector._on_model_selected("qclaw")

    assert selector.objectName() == "modelSelector"
    assert selector._groups == _model_groups()
    assert selector._current_name == "qclaw"
    assert "qclaw" in selector._button.text()
    assert selected == ["qclaw"]
