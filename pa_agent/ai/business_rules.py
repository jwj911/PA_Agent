"""Business-rule cross-field validators for Stage 2 AI outputs.

Extracted from :mod:`pa_agent.ai.json_validator` (report §5.2 M2). These are the
deterministic §9/§11 order-decision checks that run after schema validation:

  - check_no_order_invariant     — 不下单 ↔ null iron law
  - check_breakout_order_basis   — breakout orders tied to a bar extreme
  - check_trade_metrics          — RR / trader equation from entry/stop/target
  - check_breakout_price_extreme — entry numerically outside the cited bar extreme
  - check_next_cycle_prediction  — cycle prediction sum / argmax / null rules
  - check_next_bar_prediction    — bar prediction sum / argmax / null rules
  - check_signal_chain           — order decisions grounded in §9 signal facts

Import-time dependencies are stdlib-only (``re`` / ``typing``); ``check_trade_metrics``
and ``check_next_cycle_prediction`` use call-time imports so importing this module
never pulls in PyQt6 (via ``pa_agent.util``) or the cycle enums.

``JsonValidator`` re-binds each ``check_x`` as a ``staticmethod`` named ``_check_x``
so existing ``JsonValidator._check_x(...)`` call sites (production and tests) keep
working byte-for-byte.
"""

from __future__ import annotations

import re
from typing import Any

# Tokens in §9 / decision reasoning that justify trading on weak|invalid signal_bar.
_EXPLICIT_S9_TRADABLE_TOKENS = (
    "弱",
    "瑕疵",
    "激进",
    "仍可",
    "例外",
    "次优",
    "等待信号",
    "无信号",
    "挂单",
    "计划型",
    "接受",
    "限价",
    "结构位",
    "边界",
    "宽通道",
    "回撤",
    "反弹",
    "tr_boundary",
)


def check_no_order_invariant(obj: dict) -> dict | None:
    """Explicitly enforce the 不下单 ↔ null iron law.

    Returns a dict with 'fields' and 'allowed' if violated, else None.
    """
    decision = obj.get("decision", {})
    if not isinstance(decision, dict):
        return None

    order_type = decision.get("order_type")
    price_fields = [
        "entry_price",
        "take_profit_price",
        "take_profit_price_2",
        "stop_loss_price",
        "order_direction",
    ]

    if order_type == "不下单":
        violated = [f for f in price_fields if decision.get(f) is not None]
        if violated:
            return {
                "fields": violated,
                "allowed": {f: [None] for f in violated},
            }
    elif order_type in ("限价单", "突破单", "市价单"):
        violated = [f for f in price_fields if decision.get(f) is None]
        if violated:
            return {
                "fields": violated,
                "allowed": {
                    "entry_price": ["<finite number>"],
                    "take_profit_price": ["<finite number>"],
                    "take_profit_price_2": ["<finite number>"],
                    "stop_loss_price": ["<finite number>"],
                    "order_direction": ["做多", "做空"],
                },
            }
    return None


def check_breakout_order_basis(obj: dict) -> dict | None:
    """Require breakout orders to be tied to a bar extreme, not a mid-bar price."""
    decision = obj.get("decision", {})
    if not isinstance(decision, dict) or decision.get("order_type") != "突破单":
        return None

    fields: list[str] = []
    allowed: dict[str, list] = {}
    direction = decision.get("order_direction")
    extreme = decision.get("entry_basis_extreme")

    if not decision.get("entry_basis_bar"):
        fields.append("decision.entry_basis_bar")
        allowed["decision.entry_basis_bar"] = ["K{n}"]
    if extreme not in ("high", "low"):
        fields.append("decision.entry_basis_extreme")
        allowed["decision.entry_basis_extreme"] = ["high", "low"]
    if not decision.get("entry_rule"):
        fields.append("decision.entry_rule")
        allowed["decision.entry_rule"] = [
            "做多突破单=依据K线高点上方1跳动",
            "做空突破单=依据K线低点下方1跳动",
        ]

    if direction == "做多" and extreme == "low":
        fields.append("decision.entry_basis_extreme")
        allowed["decision.entry_basis_extreme"] = ["做多突破单必须使用 high"]
    if direction == "做空" and extreme == "high":
        fields.append("decision.entry_basis_extreme")
        allowed["decision.entry_basis_extreme"] = ["做空突破单必须使用 low"]

    if fields:
        return {"fields": fields, "allowed": allowed}
    return None


def check_trade_metrics(
    obj: dict,
    *,
    decision_stance: str | None = None,
    kline_frame: Any = None,
) -> list[str]:
    """Enforce RR and trader equation from entry/stop/target (not narrative distances)."""
    from pa_agent.util.trade_metrics import validate_order_trade_metrics

    decision = obj.get("decision", {})
    if not isinstance(decision, dict):
        return []
    return validate_order_trade_metrics(
        decision,
        decision_stance=decision_stance,
        kline_frame=kline_frame,
        bar_analysis=obj.get("bar_analysis") if isinstance(obj.get("bar_analysis"), dict) else None,
    )


def check_breakout_price_extreme(obj: dict, kline_frame: Any = None) -> list[str]:
    """Numerically verify breakout entry is outside the cited bar extreme."""
    if kline_frame is None:
        return []
    decision = obj.get("decision", {})
    if not isinstance(decision, dict) or decision.get("order_type") != "突破单":
        return []

    basis = _parse_k_seq(decision.get("entry_basis_bar"))
    if basis is None:
        return []
    bar = _bar_by_seq(kline_frame, basis)
    if bar is None:
        return [f"entry_basis_bar K{basis} not found in current K-line frame"]

    try:
        entry = float(decision.get("entry_price"))
    except (TypeError, ValueError):
        return []

    direction = decision.get("order_direction")
    extreme = decision.get("entry_basis_extreme")
    if direction == "做多" and extreme == "high" and entry <= float(bar.high):
        return [
            f"做多突破单 entry_price={entry:.6g} must be above "
            f"K{basis}.high={float(bar.high):.6g}"
        ]
    if direction == "做空" and extreme == "low" and entry >= float(bar.low):
        return [
            f"做空突破单 entry_price={entry:.6g} must be below "
            f"K{basis}.low={float(bar.low):.6g}"
        ]
    return []


def check_next_cycle_prediction(obj: dict) -> list[str]:
    """Cross-field validation for next_cycle_prediction.

    Returns error message list; caller adds each to invalid_fields.
    """
    from pa_agent.ai.cycle_enums import CYCLE_ENUM, CYCLE_ORDER

    pred = obj.get("next_cycle_prediction")
    if pred is None:
        return []  # Missing field is backward-compatible (R5.1)
    if not isinstance(pred, dict):
        return ["next_cycle_prediction: must be an object when present"]

    errors: list[str] = []
    unpredictable = bool(pred.get("unpredictable", False))

    if unpredictable:
        if pred.get("cycle") is not None:
            errors.append("next_cycle_prediction.cycle: must be null when unpredictable=true")
        if pred.get("direction") is not None:
            errors.append("next_cycle_prediction.direction: must be null when unpredictable=true")
        if pred.get("probabilities") is not None:
            errors.append(
                "next_cycle_prediction.probabilities: must be null when unpredictable=true"
            )
        return errors

    # unpredictable=false path
    cycle = pred.get("cycle")
    if cycle not in CYCLE_ENUM:
        errors.append(
            f"next_cycle_prediction.cycle: {cycle!r} is not a valid cycle enum value; "
            f"expected one of {list(CYCLE_ENUM)}"
        )

    probs = pred.get("probabilities")
    if not isinstance(probs, dict):
        return [
            *errors,
            "next_cycle_prediction.probabilities: must be an object when unpredictable=false",
        ]

    for key in CYCLE_ORDER:
        value = probs.get(key)
        if not isinstance(value, int) or not (0 <= value <= 100):
            errors.append(f"next_cycle_prediction.probabilities.{key}: must be int in [0, 100]")
    if errors:
        return errors

    # Sum constraint [99, 101]
    total = sum(probs[k] for k in CYCLE_ORDER)
    if not (99 <= total <= 101):
        errors.append(
            f"next_cycle_prediction.probabilities: sum={total}, must satisfy 99 <= sum <= 101"
        )

    # cycle = argmax (accept any tied winner)
    max_value = max(probs[k] for k in CYCLE_ORDER)
    tied_winners = [k for k in CYCLE_ORDER if probs[k] == max_value]
    if cycle not in tied_winners:
        errors.append(
            f"next_cycle_prediction.cycle: expected one of {tied_winners} "
            f"(argmax of probabilities), got {cycle!r}"
        )

    return errors


def check_next_bar_prediction(obj: dict) -> list[str]:
    """Cross-field validation: sum constraint, direction=argmax, null consistency.

    Returns error message list; caller adds each to invalid_fields.
    """
    pred = obj.get("next_bar_prediction")
    if pred is None:
        return []  # Missing field is backward-compatible (R2.3, R7.3)
    if not isinstance(pred, dict):
        return ["next_bar_prediction: must be an object when present"]

    errors: list[str] = []
    unpredictable = bool(pred.get("unpredictable", False))

    if unpredictable:
        if pred.get("direction") is not None:
            errors.append("next_bar_prediction.direction: must be null when unpredictable=true")
        if pred.get("probabilities") is not None:
            errors.append("next_bar_prediction.probabilities: must be null when unpredictable=true")
        return errors

    # unpredictable=false path
    probs = pred.get("probabilities")
    if not isinstance(probs, dict):
        return ["next_bar_prediction.probabilities: must be an object when unpredictable=false"]

    for key in ("bullish", "bearish", "neutral"):
        value = probs.get(key)
        if not isinstance(value, int) or not (0 <= value <= 100):
            errors.append(f"next_bar_prediction.probabilities.{key}: must be int in [0, 100]")
    if errors:
        return errors

    # R3.2: sum in [99, 101]
    total = probs["bullish"] + probs["bearish"] + probs["neutral"]
    if not (99 <= total <= 101):
        errors.append(
            f"next_bar_prediction.probabilities: sum={total}, must satisfy 99 <= sum <= 101"
        )

    # R3.3: direction = argmax, accept any tied winner
    order = ("bullish", "bearish", "neutral")
    max_value = max(probs[k] for k in order)
    tied_winners = [k for k in order if probs[k] == max_value]
    direction = pred.get("direction")
    if direction not in tied_winners:
        errors.append(
            f"next_bar_prediction.direction: expected one of {tied_winners} "
            f"(argmax of probabilities), got {direction!r}"
        )

    return errors


def check_signal_chain(
    obj: dict,
    kline_frame: Any = None,
    *,
    lenient: bool = False,
) -> list[str]:
    """Require order decisions to ground §9 in signal/entry/follow-through facts."""
    decision = obj.get("decision", {})
    if not isinstance(decision, dict):
        return []
    if decision.get("order_type") not in ("限价单", "突破单", "市价单"):
        return []

    errors: list[str] = []
    bar_analysis = obj.get("bar_analysis")
    if not isinstance(bar_analysis, dict):
        return ["bar_analysis is required when placing an order"]

    signal_bar = bar_analysis.get("signal_bar")
    entry_bar = bar_analysis.get("entry_bar")
    if not isinstance(signal_bar, dict):
        errors.append("bar_analysis.signal_bar is required when placing an order")
    if not isinstance(entry_bar, dict):
        errors.append("bar_analysis.entry_bar is required when placing an order")
    if errors:
        return errors

    sig_seq = _parse_k_seq(signal_bar.get("bar"))
    entry_seq = _parse_k_seq(entry_bar.get("bar"))
    strength = str(entry_bar.get("strength", "") or "").strip().lower()
    freshness = str(entry_bar.get("freshness", "fresh")).strip().lower()
    quality = str(signal_bar.get("quality", "")).strip().lower()
    pattern = str(signal_bar.get("pattern", "") or "").strip().lower()
    pending_entry = (
        strength == "not_triggered" or freshness == "pending" or entry_bar.get("bar") is None
    )
    order_type = decision.get("order_type")
    planned_without_signal = (
        pending_entry
        and order_type in ("限价单", "突破单")
        and quality == "invalid"
        and pattern in ("", "none", "not_triggered", "pending")
        and signal_bar.get("bar") is None
    )
    _planned_limit_boundary_patterns = (
        "tr_boundary",
        "breakout_pullback",
        "h1",
        "h2",
        "l1",
        "l2",
        "wedge",
        "mtr",
    )
    planned_limit_weak = (
        pending_entry
        and order_type == "限价单"
        and quality == "weak"
        and (
            signal_bar.get("bar") is None
            or pattern in ("", "none", *_planned_limit_boundary_patterns)
        )
    )
    # §9.0P planned limit: invalid + boundary pattern + no closed signal bar.
    planned_limit_invalid_boundary = (
        pending_entry
        and order_type == "限价单"
        and quality == "invalid"
        and pattern in _planned_limit_boundary_patterns
        and signal_bar.get("bar") is None
    )
    planned_entry = planned_without_signal or planned_limit_weak or planned_limit_invalid_boundary
    if sig_seq is None and not planned_entry:
        errors.append("bar_analysis.signal_bar.bar must be a K{n} reference")
    if entry_seq is None and not pending_entry:
        errors.append("bar_analysis.entry_bar.bar must be a K{n} reference")
    if pending_entry and decision.get("order_type") == "市价单":
        errors.append("market order requires a concrete entry_bar.bar")
    if sig_seq is not None and entry_seq is not None and sig_seq <= entry_seq:
        errors.append(
            "signal_bar must be older than entry_bar "
            f"(expected signal K seq > entry K seq, got K{sig_seq} and K{entry_seq})"
        )
    if kline_frame is not None:
        for label, seq in (("signal_bar", sig_seq), ("entry_bar", entry_seq)):
            if seq is not None and _bar_by_seq(kline_frame, seq) is None:
                errors.append(f"bar_analysis.{label}.bar K{seq} not found in current K-line frame")

    if not lenient and quality in ("weak", "invalid") and not planned_entry:
        reasons = _all_stage2_reasons(obj)
        if not any(token in reasons for token in _EXPLICIT_S9_TRADABLE_TOKENS):
            errors.append(
                "weak/invalid signal_bar requires explicit §9 reasoning for why the setup remains tradable"
            )

    follow = entry_bar.get("follow_through")
    no_follow = follow is False or str(follow).strip().lower() in ("false", "no", "failed")
    trade_conf = decision.get("trade_confidence")
    try:
        trade_conf_num = int(trade_conf)
    except (TypeError, ValueError):
        trade_conf_num = 0
    if freshness in ("stale", "invalid") and not (lenient and pending_entry):
        errors.append("entry_bar.freshness stale/invalid cannot support a new order")
    if not lenient and no_follow and not pending_entry and trade_conf_num >= 50:
        errors.append("entry_bar.follow_through=false/failed cannot support trade_confidence >= 50")
    return errors


def _parse_k_seq(value: object) -> int | None:
    if value is None:
        return None
    m = re.search(r"K\s*(\d+)", str(value), flags=re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


def _bar_by_seq(kline_frame: Any, seq: int) -> Any | None:
    for bar in getattr(kline_frame, "bars", ()) or ():
        if getattr(bar, "seq", None) == seq:
            return bar
    return None


def _all_stage2_reasons(obj: dict) -> str:
    parts: list[str] = []
    decision = obj.get("decision", {})
    if isinstance(decision, dict):
        for key in ("reasoning", "trade_confidence_reasoning", "risk_assessment"):
            parts.append(str(decision.get(key, "") or ""))
    for item in obj.get("decision_trace", []) or []:
        if isinstance(item, dict):
            parts.append(str(item.get("reason", "") or ""))
    return "\n".join(parts)
