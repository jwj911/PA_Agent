"""Tests for signal-bar context helpers."""
from __future__ import annotations

from pa_agent.ai.signal_context import (
    _get_signal_seq,
    has_background_limit_path,
    is_planned_limit_order,
)


def test_get_signal_seq_prefers_valid_signal_bar_seq() -> None:
    out = {"bar_analysis": {"signal_bar": {"bar": "K12"}}}

    assert _get_signal_seq(out, bars=()) == 12


def test_get_signal_seq_falls_back_to_k1_for_missing_or_invalid_values() -> None:
    assert _get_signal_seq({}, bars=()) == 1
    assert _get_signal_seq({"bar_analysis": {"signal_bar": {"bar": "bad"}}}, bars=()) == 1
    assert _get_signal_seq({"bar_analysis": {"signal_bar": {"bar": "K0"}}}, bars=()) == 1


def test_has_background_limit_path_detects_yes_answer_only() -> None:
    assert has_background_limit_path({"decision_trace": [{"node_id": "9.0P", "answer": "是"}]})
    assert has_background_limit_path({"decision_trace": [{"node_id": " 9.0P ", "answer": " 是 "}]})
    assert not has_background_limit_path({"decision_trace": [{"node_id": "9.0P", "answer": "否"}]})
    assert not has_background_limit_path({"decision_trace": [{"node_id": "9.1", "answer": "是"}]})
    assert not has_background_limit_path({"decision_trace": "not-a-list"})


def test_planned_limit_order_accepts_background_limit_path() -> None:
    out = {
        "decision": {"order_type": "限价单"},
        "decision_trace": [{"node_id": "9.0P", "answer": "是"}],
    }

    assert is_planned_limit_order(out)


def test_planned_limit_order_accepts_pending_entry_without_signal_bar() -> None:
    out = {
        "decision": {"order_type": "限价单"},
        "bar_analysis": {
            "entry_bar": {"strength": "not_triggered", "freshness": "pending"},
            "signal_bar": {"bar": None, "quality": "invalid"},
        },
    }

    assert is_planned_limit_order(out)


def test_planned_limit_order_accepts_weak_structural_patterns() -> None:
    out = {
        "decision": {"order_type": "限价单"},
        "bar_analysis": {
            "entry_bar": {"bar": None},
            "signal_bar": {"bar": "K3", "quality": "weak", "pattern": "breakout_pullback"},
        },
    }

    assert is_planned_limit_order(out)


def test_planned_limit_order_rejects_non_pending_or_non_limit_orders() -> None:
    non_limit = {
        "decision": {"order_type": "突破单"},
        "bar_analysis": {
            "entry_bar": {"strength": "not_triggered"},
            "signal_bar": {"bar": None, "quality": "invalid"},
        },
    }
    already_triggered = {
        "decision": {"order_type": "限价单"},
        "bar_analysis": {
            "entry_bar": {"bar": "K2", "strength": "confirmed", "freshness": "fresh"},
            "signal_bar": {"bar": "K2", "quality": "weak", "pattern": "h1"},
        },
    }

    assert not is_planned_limit_order(non_limit)
    assert not is_planned_limit_order(already_triggered)
