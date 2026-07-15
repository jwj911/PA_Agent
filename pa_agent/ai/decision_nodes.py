"""Compatibility facade for deterministic decision node helpers.

The section judges and shared helpers live in focused modules. This module keeps
the historical ``from pa_agent.ai.decision_nodes import ...`` import path stable.
"""
from __future__ import annotations

from pa_agent.ai.always_in_judges import judge_always_in, judge_momentum_strength
from pa_agent.ai.decision_node_engine import DecisionNodeEngine
from pa_agent.ai.decision_thresholds import (
    ALWAYS_IN_SAME_SIDE_RATIO,
    BAR_COUNT_THRESHOLD,
    SIGNAL_BAR_LONG_ATR_RATIO,
)
from pa_agent.ai.diagnostic_judges import judge_data_sufficiency, judge_market_chaos
from pa_agent.ai.direction_judge import judge_direction
from pa_agent.ai.order_method_router import route_order_method
from pa_agent.ai.override_arbiter import (
    apply_overrides,
    merge_program_nodes,
    merge_program_nodes_head,
    write_override_trace,
)
from pa_agent.ai.preflight import PreflightResult, check_preflight_data
from pa_agent.ai.signal_bar_judges import (
    judge_follow_through,
    judge_signal_bar_closed,
    judge_signal_bar_direction,
    judge_signal_bar_length,
)
from pa_agent.ai.signal_context import (
    _get_signal_seq,
    has_background_limit_path,
    is_planned_limit_order,
)
from pa_agent.ai.trace_nodes import (
    NodeFill,
    _coerce_dict,
    _coerce_trace_list,
    build_program_trace_node,
)

__all__ = [
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
