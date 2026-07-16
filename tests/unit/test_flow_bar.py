"""Tests for the analysis flow bar widget."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.widgets.flow_bar import FlowBar

_APP: QApplication | None = None


def _make_flow_bar() -> FlowBar:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return FlowBar()


def test_flow_bar_initializes_default_steps() -> None:
    bar = _make_flow_bar()

    assert [step._name.text() for step in bar._steps] == ["数据", "快照", "诊断", "决策", "追问"]
    assert [step._caption.text() for step in bar._steps] == [
        "等待连接",
        "未获取",
        "等待阶段一",
        "等待阶段二",
        "等待完成",
    ]
    assert bar.objectName() == "flowBar"


def test_flow_bar_updates_step_status_and_caption() -> None:
    bar = _make_flow_bar()

    bar.set_step_status(2, "active")
    bar.set_step_caption(2, "阶段一进行中")

    assert "#38bdf8" in bar._steps[2]._dot.styleSheet()
    assert "rgba(56,189,248,0.20)" in bar._steps[2]._glow.styleSheet()
    assert bar._steps[2]._caption.text() == "阶段一进行中"


def test_flow_bar_ignores_out_of_range_step_updates() -> None:
    bar = _make_flow_bar()
    before = [step._caption.text() for step in bar._steps]

    bar.set_step_status(-1, "error")
    bar.set_step_status(99, "done")
    bar.set_step_caption(-1, "bad")
    bar.set_step_caption(99, "bad")

    assert [step._caption.text() for step in bar._steps] == before
    assert all("#484f58" in step._dot.styleSheet() for step in bar._steps)


def test_flow_bar_reset_all_restores_idle_default_captions() -> None:
    bar = _make_flow_bar()

    bar.set_step_status(0, "done")
    bar.set_step_status(1, "error")
    bar.set_step_caption(0, "已完成")
    bar.set_step_caption(1, "失败")

    bar.reset_all()

    assert [step._caption.text() for step in bar._steps] == [
        "等待连接",
        "未获取",
        "等待阶段一",
        "等待阶段二",
        "等待完成",
    ]
    assert all("#484f58" in step._dot.styleSheet() for step in bar._steps)
    assert all("transparent" in step._glow.styleSheet() for step in bar._steps)
