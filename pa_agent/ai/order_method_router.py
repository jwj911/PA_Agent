"""Order-method routing (§11) for PA_Agent.

Order-method-router cluster split out of :mod:`pa_agent.ai.decision_nodes`
(report §5.2 M3). Holds the deterministic §11 routing that maps the stage-1
``cycle_position`` (and the model's own order_type / entry-basis hints) to a
final order method — 市价单 / 突破单 / 限价单 / 不下单 — and emits the matching
§11 trace nodes:

- :func:`route_order_method` — route the order method from ``cycle_position``
  under the §10.3 / §14 safety gates and the spike-ending / breakout-fallback
  exceptions, returning §11 :class:`~pa_agent.ai.trace_nodes.NodeFill` nodes.
- ``_CYCLE_ORDER_METHOD`` — cycle_position → candidate order method table.

The cluster depends only on the trace result layer (``_coerce_dict`` /
``_coerce_trace_list`` / ``NodeFill`` from :mod:`pa_agent.ai.trace_nodes`); it
references no other judge and does not import :mod:`pa_agent.ai.decision_nodes`,
so ``order_method_router`` ← ``decision_nodes`` has no import cycle.
``decision_nodes`` re-exports :func:`route_order_method`, so existing
``from pa_agent.ai.decision_nodes import route_order_method`` sites keep working
byte-for-byte. Behaviour (routing table, safety-gate short-circuits, spike /
breakout exceptions, Chinese reason strings, §11 node answers) must stay
identical to the original.
"""
from __future__ import annotations

from typing import Any

from pa_agent.ai.trace_nodes import NodeFill, _coerce_dict, _coerce_trace_list

# ── OrderMethodRouter ─────────────────────────────────────────────────────────



# cycle_position → candidate order method

_CYCLE_ORDER_METHOD: dict[str, str] = {

    "spike": "市价单",

    "micro_channel": "突破单",

    "tight_channel": "突破单",

    "normal_channel": "突破单",

    "broad_channel": "限价单",

    "trading_range": "限价单",

    "trending_tr": "突破单",

    "extreme_tr": "不下单",

    "unknown": "不下单",

}





def route_order_method(

    stage1_json: dict[str, Any] | None,

    decision: dict[str, Any],

    decision_trace: list[dict[str, Any]],

) -> list[dict[str, Any]]:

    """Route order method based on cycle_position; return §11 trace nodes."""

    decision = _coerce_dict(decision)

    stage1 = _coerce_dict(stage1_json)

    decision_trace = _coerce_trace_list(decision_trace)

    order_type = decision.get("order_type")



    # Safety: if already no-order, don't inject §11 nodes

    if order_type == "不下单":

        return []



    # Check safety gates: §10.3=否 or §14 violation

    def _trace_answer(trace: list, node_id: str) -> str | None:

        for item in trace:

            if not isinstance(item, dict):

                continue

            if str(item.get("node_id", "")).strip() == node_id:

                return str(item.get("answer", "")).strip()

        return None



    if _trace_answer(decision_trace, "10.3") == "否":

        return []



    def _sec14_violated(trace: list) -> bool:

        _DENIAL_PHRASES = ("未触犯", "未违反", "无触犯", "无违规", "通过扫描", "扫描通过", "无禁止", "未触发")

        for item in trace:

            if not isinstance(item, dict):

                continue

            nid = str(item.get("node_id", "")).strip()

            if not nid.startswith("14"):

                continue

            if str(item.get("answer", "")).strip() != "是":

                continue

            # Cross-check reason: if it contains denial phrases the AI used wrong answer
            reason = str(item.get("reason", "") or "")

            if any(phrase in reason for phrase in _DENIAL_PHRASES):

                continue

            return True

        return False



    if _sec14_violated(decision_trace):

        return []



    cycle = "unknown"

    if stage1:

        cycle = str(stage1.get("cycle_position", "unknown") or "unknown").strip()



    candidate = _CYCLE_ORDER_METHOD.get(cycle, "不下单")

    model_order_type = str(decision.get("order_type") or "").strip()

    def _has_trade_prices() -> bool:
        return all(
            decision.get(k) is not None
            for k in (
                "entry_price",
                "stop_loss_price",
                "take_profit_price",
                "take_profit_price_2",
            )
        )

    # Preserve model's explicit limit/market choice when §10.3 already passed.
    if (
        model_order_type == "限价单"
        and _trace_answer(decision_trace, "10.3") == "是"
        and _has_trade_prices()
    ):
        candidate = "限价单"
    elif (
        model_order_type == "市价单"
        and _trace_answer(decision_trace, "10.3") == "是"
        and _has_trade_prices()
    ):
        candidate = "市价单"
    elif (
        model_order_type == "突破单"
        and _trace_answer(decision_trace, "10.3") == "是"
        and _has_trade_prices()
        and decision.get("entry_basis_bar")
        and decision.get("entry_basis_extreme")
    ):
        # broad_channel defaults to 限价单, but a pending breakdown/breakout
        # at basis±tick is not a sell-limit-above-market plan — preserve 突破单.
        candidate = "突破单"

    if candidate == "不下单":

        # Not a trading context for this cycle

        return []



    # ── spike_ending / spike_pullback exception ───────────────────────────────
    # When cycle_position=spike but spike_stage indicates the spike has already
    # ended (ending/pullback/channel), the default candidate is 市价单 (for active
    # spike chasing).  However, once the spike exhausts itself the market enters a
    # consolidation/pullback phase where waiting for a breakout of the signal bar
    # is the textbook entry (§3.4 SPS / §3.5 path-A).  Forcing 市价单 on a pending
    # 突破单 is wrong: the entry hasn't triggered yet (entry_bar.strength=not_triggered
    # / freshness=pending) and the signal_chain validator would reject it.
    # Preserve the model's 突破单 choice when:
    #   1. spike_stage is ending / pullback / channel  (spike already exhausted)
    #   2. model chose 突破单
    #   3. a valid entry_basis_bar + entry_basis_extreme are present (breakout anchor)
    if cycle == "spike" and candidate == "市价单":

        spike_stage = str(stage1.get("spike_stage") or "").strip().lower()

        if spike_stage in ("ending", "pullback", "channel") and model_order_type == "突破单":

            has_basis = bool(

                decision.get("entry_basis_bar") and decision.get("entry_basis_extreme")

            )

            if has_basis:

                candidate = "突破单"

        return []



    # Breakout order: check for valid entry_basis; fall back to limit when unavailable.

    breakout_fallback_to_limit = False

    if candidate == "突破单":

        has_basis = bool(

            decision.get("entry_basis_bar") and decision.get("entry_basis_extreme")

        )

        if not has_basis:

            # No breakout anchor → try limit at structural level (if §10.3 already passed).

            breakout_fallback_to_limit = True

            candidate = "限价单"



    # Determine which §11 node corresponds to the final method

    # §11 structure:

    # 11.1: 趋势/尖峰 → 市价单 (spike)

    # 11.2: 通道 → 突破单 (channel)

    # 11.3: 区间 → 限价单 (range)

    # 11.4: broad_channel → 限价单 (broad)

    _METHOD_NODE: dict[str, tuple[str, str]] = {

        "spike":         ("11.1", "市价单"),

        "micro_channel": ("11.2", "突破单"),

        "tight_channel": ("11.2", "突破单"),

        "normal_channel":("11.2", "突破单"),

        "broad_channel": ("11.2", "限价单"),

        "trading_range": ("11.3", "限价单"),

        "trending_tr":   ("11.2", "突破单"),

    }



    cycle_node_info = _METHOD_NODE.get(cycle)

    if not cycle_node_info:

        return []



    final_node_id, _ = cycle_node_info



    # Update decision order_type to match candidate

    decision["order_type"] = candidate



    nodes = []

    # Build §11 trace nodes: the final one gets answer=是, prior ones get answer=否

    all_nodes = ["11.1", "11.2", "11.3", "11.4"]

    final_idx = all_nodes.index(final_node_id) if final_node_id in all_nodes else -1



    _node_reasons: dict[str, str] = {

        "11.1": "趋势/尖峰阶段，价格快速移动，适合市价单立即入场。",

        "11.2": "通道结构，等待突破确认，使用突破单。",

        "11.3": "交易区间，在区间边界附近使用限价单。",

        "11.4": "宽通道/特殊情况，使用限价单。",

    }



    for i, nid in enumerate(all_nodes):

        if i > final_idx:

            break

        answer = "是" if nid == final_node_id else "否"

        reason = _node_reasons.get(nid, f"§{nid}判定。")

        if nid == final_node_id:

            # For spike_ending exception: the candidate was overridden to 突破单,
            # make the reason explicit so the audit trail is clear.
            spike_stage_label = str(stage1.get("spike_stage") or "").strip().lower()
            if cycle == "spike" and candidate == "突破单" and spike_stage_label in ("ending", "pullback", "channel"):
                reason = (
                    f"cycle_position={cycle}（spike_stage={spike_stage_label}，尖峰已结束）"
                    f"→{candidate}（保留模型突破单选择；尖峰结束后等待信号棒突破确认是正确做法，"
                    "不应强制市价单立即追入）。" + reason
                )
            elif breakout_fallback_to_limit and candidate == "限价单":
                reason = (
                    f"cycle_position={cycle} 默认突破单，但无有效 entry_basis_bar/extreme；"
                    f"§10.3 已通过 → 改用限价单在结构位挂单（回撤/反弹到位入场）。"
                    + reason
                )
            else:
                reason = f"cycle_position={cycle}→{candidate}。" + reason

        nodes.append(NodeFill(

            node_id=nid,

            answer=answer,

            reason=reason,

            bar_range="K1",

        ))



    return nodes
