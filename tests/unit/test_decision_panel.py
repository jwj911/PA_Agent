"""Unit tests for DecisionPanel diagnosis and trade rendering."""
# ruff: noqa: RUF001
from __future__ import annotations

import sys
import time

import pytest
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st
from PyQt6.QtWidgets import QApplication

from pa_agent.gui.decision_panel import (
    DecisionPanel,
    _dominant_prediction_direction,
    _format_prediction_probs_line,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """Shared QApplication for this module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def panel(qapp: QApplication) -> DecisionPanel:
    p = DecisionPanel()
    p.show()
    qapp.processEvents()
    return p


def _valid_no_order() -> dict:
    """Minimal valid Stage 2 decision with 不下单."""
    return {
        "decision": {
            "order_type": "不下单",
            "order_direction": None,
            "entry_price": None,
            "take_profit_price": None,
            "stop_loss_price": None,
            "reasoning": "市场结构不明朗，暂不入场。",
            "diagnosis_confidence": 40,
            "diagnosis_confidence_reasoning": "方向仍需确认",
            "trade_confidence": 30,
            "trade_confidence_reasoning": "等待更强信号",
            "estimated_win_rate": None,
            "estimated_win_rate_reasoning": "无交易不估算",
            "key_factors": [],
            "watch_points": [],
            "risk_assessment": "等待",
            "invalidation_condition": "突破关键位",
        },
        "diagnosis_summary": {
            "cycle_position": "normal_channel",
            "direction": "bullish",
            "key_signals": [],
        },
        "decision_trace": [
            {
                "node_id": "10.3",
                "question": "q",
                "answer": "否",
                "reason": "r",
                "bar_range": "K1",
            },
        ],
        "terminal": {"node_id": "10.3", "outcome": "wait", "label": "test"},
    }


def _long_limit_decision() -> dict:
    base = _valid_no_order()["decision"].copy()
    base.update(
        {
            "order_type": "限价单",
            "order_direction": "做多",
            "entry_price": 100.0,
            "take_profit_price": 120.0,
            "take_profit_price_2": 130.0,
            "stop_loss_price": 95.0,
            "reasoning": "多头回调到支撑后考虑入场。",
            "trade_confidence": 75,
            "trade_confidence_reasoning": "结构与风险回报匹配",
            "estimated_win_rate": 55,
        }
    )
    return base


def test_prediction_probability_helpers_use_current_text_contract() -> None:
    probs = {"bullish": 70, "bearish": 20, "neutral": 10}
    assert _format_prediction_probs_line(probs) == (
        "阳线的概率为70%  ·  阴线的概率为20%  ·  中性的概率为10%"
    )
    assert _dominant_prediction_direction(probs) == "bullish"


def test_panel_no_order_renders_observation_state(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    panel.set_decision(data["decision"], diagnosis_summary=data["diagnosis_summary"])

    assert panel._conclusion_label.text() == "不下单"
    assert not panel._conclusion_bar.isVisible()
    assert not panel._trade_prices_row.isVisible()
    assert panel._trade_conf_inline_label.text() == "置信度 30 / 100 · 观望"
    assert "等待更强信号" in panel._trade_reasoning_label.text()
    assert panel._reasoning_edit.toPlainText() == "市场结构不明朗，暂不入场。"


def test_panel_diagnosis_summary_and_confidence(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    panel.set_decision(data["decision"], diagnosis_summary=data["diagnosis_summary"])

    assert "上涨" in panel._trend_label.text()
    assert "通道" in panel._cycle_label.text()
    assert panel._diag_conf_bar.value() == 40
    assert panel._diag_conf_label.text() == "评分 40 / 100"
    assert "方向仍需确认" in panel._diag_reasoning_label.text()


def test_panel_long_trade_renders_prices_and_metrics(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    decision = _long_limit_decision()
    panel.set_decision(decision, diagnosis_summary=data["diagnosis_summary"])

    assert panel._conclusion_label.text() == "限价单"
    assert panel._direction_inline_label.text() == "方向 做多"
    assert panel._trade_prices_row.isVisible()
    assert panel._entry_label.text() == "入场  100"
    assert panel._tp_label.text() == "TP1  120"
    assert panel._tp2_label.text() == "TP2  130"
    assert panel._sl_label.text() == "止损  95"
    assert "盈亏比" in panel._rr_inline_label.text()
    assert panel._win_rate_inline_label.text() == "预估胜率  55%"
    assert panel._trade_conf_inline_label.text() == "置信度 75 / 100 · 入场"


def test_panel_confidence_gate_suppresses_low_confidence_order(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    decision = _long_limit_decision()
    decision["trade_confidence"] = 25

    panel.set_decision(
        decision,
        diagnosis_summary=data["diagnosis_summary"],
        confidence_threshold=60,
    )

    assert panel._conclusion_label.text() == "不下单"
    assert not panel._trade_prices_row.isVisible()
    assert "有入场机会，但置信度未通过" in panel._reasoning_edit.toPlainText()
    assert panel._trade_conf_inline_label.text() == "置信度 25 / 100 · 观望"


def test_panel_bearish_range_trend_shows_biased_sideways(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    data["diagnosis_summary"] = {
        "cycle_position": "trading_range",
        "direction": "bearish",
        "alternative_cycle_position": "trending_tr",
        "key_signals": [],
    }
    panel.set_decision(data["decision"], diagnosis_summary=data["diagnosis_summary"])

    assert "震荡偏空" in panel._trend_label.text()
    assert "下跌交易区间" in panel._cycle_label.text()
    assert "#f85149" in panel._trend_label.styleSheet()


def test_panel_clear_resets_current_ui(panel: DecisionPanel) -> None:
    data = _valid_no_order()
    panel.set_decision(_long_limit_decision(), diagnosis_summary=data["diagnosis_summary"])

    panel.clear()

    assert panel._conclusion_label.text() == "等待分析"
    assert panel._reasoning_edit.toPlainText() == ""
    assert not panel._trade_prices_row.isVisible()
    assert not panel._trade_conf_inline_label.isVisible()


def test_panel_render_performance(panel: DecisionPanel) -> None:
    """set_decision should stay cheap enough for GUI refresh paths."""
    data = _valid_no_order()
    decision = _long_limit_decision()
    start = time.perf_counter()
    for _ in range(10):
        panel.set_decision(decision, diagnosis_summary=data["diagnosis_summary"])
    elapsed = (time.perf_counter() - start) / 10
    assert elapsed < 0.05, f"set_decision took {elapsed * 1000:.1f}ms per call"


_garbage_prediction = st.fixed_dictionaries(
    {},
    optional={
        "direction": st.one_of(st.none(), st.text(max_size=20), st.integers()),
        "probabilities": st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=10),
            st.dictionaries(
                st.text(max_size=10),
                st.one_of(st.integers(), st.text(), st.none()),
            ),
        ),
        "reasoning": st.one_of(
            st.none(),
            st.text(max_size=100),
            st.integers(),
            st.lists(st.integers()),
        ),
        "unpredictable": st.one_of(
            st.booleans(),
            st.none(),
            st.integers(),
            st.text(max_size=5),
        ),
        "features_used": st.one_of(
            st.none(),
            st.integers(),
            st.lists(st.one_of(st.text(), st.integers())),
        ),
    },
)


@given(pred=_garbage_prediction)
@h_settings(max_examples=100, deadline=None)
def test_panel_ignores_garbage_next_bar_prediction(pred: dict) -> None:
    """Garbage next_bar_prediction payloads must not break current rendering."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    panel = DecisionPanel()
    panel.show()
    app.processEvents()
    data = _valid_no_order()
    inner = {**data["decision"], "next_bar_prediction": pred}

    panel.set_decision(inner, diagnosis_summary=data.get("diagnosis_summary"))

    assert panel._conclusion_label.text() == "不下单"
