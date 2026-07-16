"""Tests for the decision node compatibility facade exports."""
from __future__ import annotations

from pa_agent.ai import (
    always_in_judges,
    decision_node_engine,
    decision_nodes,
    decision_thresholds,
    diagnostic_judges,
    direction_judge,
    order_method_router,
    override_arbiter,
    preflight,
    signal_bar_judges,
    signal_context,
    trace_nodes,
)


def test_decision_nodes_facade_exports_expected_public_names() -> None:
    assert decision_nodes.__all__ == [
        "ALWAYS_IN_SAME_SIDE_RATIO",
        "BAR_COUNT_THRESHOLD",
        "SIGNAL_BAR_LONG_ATR_RATIO",
        "DecisionNodeEngine",
        "NodeFill",
        "PreflightResult",
        "_coerce_dict",
        "_coerce_trace_list",
        "_get_signal_seq",
        "apply_overrides",
        "build_program_trace_node",
        "check_preflight_data",
        "has_background_limit_path",
        "is_planned_limit_order",
        "judge_always_in",
        "judge_data_sufficiency",
        "judge_direction",
        "judge_follow_through",
        "judge_market_chaos",
        "judge_momentum_strength",
        "judge_signal_bar_closed",
        "judge_signal_bar_direction",
        "judge_signal_bar_length",
        "merge_program_nodes",
        "merge_program_nodes_head",
        "route_order_method",
        "write_override_trace",
    ]


def test_decision_nodes_facade_public_names_are_bound_to_source_objects() -> None:
    expected_bindings = {
        "ALWAYS_IN_SAME_SIDE_RATIO": decision_thresholds.ALWAYS_IN_SAME_SIDE_RATIO,
        "BAR_COUNT_THRESHOLD": decision_thresholds.BAR_COUNT_THRESHOLD,
        "SIGNAL_BAR_LONG_ATR_RATIO": decision_thresholds.SIGNAL_BAR_LONG_ATR_RATIO,
        "DecisionNodeEngine": decision_node_engine.DecisionNodeEngine,
        "NodeFill": trace_nodes.NodeFill,
        "PreflightResult": preflight.PreflightResult,
        "_coerce_dict": trace_nodes._coerce_dict,
        "_coerce_trace_list": trace_nodes._coerce_trace_list,
        "_get_signal_seq": signal_context._get_signal_seq,
        "apply_overrides": override_arbiter.apply_overrides,
        "build_program_trace_node": trace_nodes.build_program_trace_node,
        "check_preflight_data": preflight.check_preflight_data,
        "has_background_limit_path": signal_context.has_background_limit_path,
        "is_planned_limit_order": signal_context.is_planned_limit_order,
        "judge_always_in": always_in_judges.judge_always_in,
        "judge_data_sufficiency": diagnostic_judges.judge_data_sufficiency,
        "judge_direction": direction_judge.judge_direction,
        "judge_follow_through": signal_bar_judges.judge_follow_through,
        "judge_market_chaos": diagnostic_judges.judge_market_chaos,
        "judge_momentum_strength": always_in_judges.judge_momentum_strength,
        "judge_signal_bar_closed": signal_bar_judges.judge_signal_bar_closed,
        "judge_signal_bar_direction": signal_bar_judges.judge_signal_bar_direction,
        "judge_signal_bar_length": signal_bar_judges.judge_signal_bar_length,
        "merge_program_nodes": override_arbiter.merge_program_nodes,
        "merge_program_nodes_head": override_arbiter.merge_program_nodes_head,
        "route_order_method": order_method_router.route_order_method,
        "write_override_trace": override_arbiter.write_override_trace,
    }

    for name, expected in expected_bindings.items():
        assert getattr(decision_nodes, name) is expected
