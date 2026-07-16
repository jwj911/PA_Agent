"""Tests for trace-node result helpers."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pa_agent.ai import decision_tree
from pa_agent.ai.trace_nodes import (
    NodeFill,
    _coerce_dict,
    _coerce_trace_list,
    _node_label,
    build_program_trace_node,
)


def test_coerce_dict_accepts_only_dict_values() -> None:
    value = {"node_id": "1.1"}

    assert _coerce_dict(value) is value
    assert _coerce_dict(None) == {}
    assert _coerce_dict([("node_id", "1.1")]) == {}


def test_coerce_trace_list_filters_non_dict_items() -> None:
    first = {"node_id": "1.1"}
    second = {"node_id": "2.3"}

    assert _coerce_trace_list([first, "noise", second, None]) == [first, second]
    assert _coerce_trace_list({"node_id": "1.1"}) == []
    assert _coerce_trace_list("not-a-list") == []


def test_node_fill_is_frozen_with_optional_metadata_defaults() -> None:
    fill = NodeFill("2.3", "neutral", "direction undecided", "K20-K1")

    assert fill.branch is None
    assert fill.section is None
    with pytest.raises(FrozenInstanceError):
        fill.answer = "yes"  # type: ignore[misc]


def test_build_program_trace_node_uses_decision_tree_label_and_optional_metadata() -> None:
    fill = NodeFill(
        "2.3",
        "yes",
        "direction agrees",
        "K20-K1",
        branch="bullish",
        section="trend",
    )
    tree = {"node_index": {"2.3": {"question": "direction question"}}}

    assert build_program_trace_node(fill, tree=tree) == {
        "node_id": "2.3",
        "question": "direction question",
        "answer": "yes",
        "reason": "direction agrees",
        "bar_range": "K20-K1",
        "skipped": False,
        "branch": "bullish",
        "section": "trend",
    }


def test_build_program_trace_node_omits_empty_optional_metadata() -> None:
    node = build_program_trace_node(
        NodeFill("9.1", "yes", "signal bar is closed", "K1"),
        tree={"node_index": {"9.1": {"question": "closed question"}}},
    )

    assert node == {
        "node_id": "9.1",
        "question": "closed question",
        "answer": "yes",
        "reason": "signal bar is closed",
        "bar_range": "K1",
        "skipped": False,
    }


def test_node_label_helpers_fall_back_to_node_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_node_label(*args: object, **kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(decision_tree, "node_label", fail_node_label)

    assert _node_label("missing") == "missing"
    assert build_program_trace_node(NodeFill("missing", "no", "fallback", "N/A")) == {
        "node_id": "missing",
        "question": "missing",
        "answer": "no",
        "reason": "fallback",
        "bar_range": "N/A",
        "skipped": False,
    }
