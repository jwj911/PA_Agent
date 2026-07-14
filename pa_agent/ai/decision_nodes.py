"""Deterministic decision node engine for PA_Agent.



This module contains:

- PreflightDataGate: pre-AI data quality check

- DecisionNodeEngine: deterministic judge for §1.1/§2.3/§2.4/§9/§11 nodes

- OverrideArbiter: controlled override adjudication

- Various helper functions and constants

"""

from __future__ import annotations



import logging

from typing import Any



from pa_agent.ai.always_in_judges import judge_always_in, judge_momentum_strength
from pa_agent.ai.decision_thresholds import (
    ALWAYS_IN_SAME_SIDE_RATIO,  # noqa: F401  # re-exported for tests; used in always_in_judges
    BAR_COUNT_THRESHOLD,  # noqa: F401  # re-exported for tests; used in diagnostic_judges
    SIGNAL_BAR_LONG_ATR_RATIO,  # noqa: F401  # re-exported for tests; used in signal_bar_judges
)
from pa_agent.ai.diagnostic_judges import judge_data_sufficiency, judge_market_chaos
from pa_agent.ai.direction_judge import judge_direction
from pa_agent.ai.override_arbiter import (
    apply_overrides,
    merge_program_nodes,
    merge_program_nodes_head,
    write_override_trace,  # noqa: F401  # re-exported for tests; used in override_arbiter
)
from pa_agent.ai.preflight import (  # noqa: F401
    PreflightResult,
    check_preflight_data,
)
from pa_agent.ai.signal_bar_judges import (
    judge_follow_through,
    judge_signal_bar_closed,
    judge_signal_bar_direction,
    judge_signal_bar_length,
)
from pa_agent.ai.trace_nodes import (
    NodeFill,
    _coerce_dict,
    _coerce_trace_list,
    build_program_trace_node,
)



logger = logging.getLogger(__name__)



# ── SignalBarJudge ─────────────────────────────────────────────────────────────




def _get_signal_seq(out: dict[str, Any], bars: Any) -> int:

    """Locate signal bar seq: prefer bar_analysis.signal_bar.bar, else K1."""

    try:

        from pa_agent.util.price_tick import parse_k_seq

        bar_analysis = out.get("bar_analysis")

        if isinstance(bar_analysis, dict):

            signal_bar = bar_analysis.get("signal_bar")

            if isinstance(signal_bar, dict):

                bar_str = signal_bar.get("bar")

                if bar_str:

                    seq = parse_k_seq(bar_str)

                    if seq is not None and seq >= 1:

                        return seq

    except Exception:  # noqa: BLE001

        logger.debug("signal bar seq parse failed", exc_info=True)

    return 1  # default to K1


def has_background_limit_path(out: dict[str, Any]) -> bool:
    """True when decision_trace records §9.0P=是 (background-driven limit path)."""
    trace = out.get("decision_trace")
    if not isinstance(trace, list):
        return False
    for item in trace:
        if not isinstance(item, dict):
            continue
        if str(item.get("node_id", "")).strip() != "9.0P":
            continue
        return str(item.get("answer", "") or "").strip() == "是"
    return False


def is_planned_limit_order(out: dict[str, Any]) -> bool:
    """True when order is a pending limit plan without requiring a closed signal bar."""
    decision = out.get("decision")
    if not isinstance(decision, dict) or decision.get("order_type") != "限价单":
        return False
    if has_background_limit_path(out):
        return True
    bar_analysis = out.get("bar_analysis")
    if not isinstance(bar_analysis, dict):
        return False
    entry_bar = bar_analysis.get("entry_bar")
    signal_bar = bar_analysis.get("signal_bar")
    if not isinstance(entry_bar, dict) or not isinstance(signal_bar, dict):
        return False
    strength = str(entry_bar.get("strength", "") or "").strip().lower()
    freshness = str(entry_bar.get("freshness", "") or "").strip().lower()
    pending = (
        strength == "not_triggered"
        or entry_bar.get("bar") is None
        or freshness == "pending"
    )
    if not pending:
        return False
    quality = str(signal_bar.get("quality", "") or "").strip().lower()
    pattern = str(signal_bar.get("pattern", "") or "").strip().lower()
    if signal_bar.get("bar") is None and quality in ("invalid", "weak"):
        return True
    if quality == "weak" and pattern in (
        "",
        "none",
        "tr_boundary",
        "breakout_pullback",
        "h1",
        "h2",
        "l1",
        "l2",
        "wedge",
        "mtr",
        "trendline",
    ):
        return True
    return False





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





# ── DecisionNodeEngine ────────────────────────────────────────────────────────



class DecisionNodeEngine:

    """Deterministic decision node engine (stateless, pure-function based)."""



    @staticmethod

    def apply_stage1(out: dict[str, Any], frame: Any) -> None:

        """In-place modify stage1 JSON: fill §1.1/§2.3/§2.4, apply overrides, update direction."""

        # Ensure gate_trace exists

        out.setdefault("gate_trace", [])



        # Step 1: DataSufficiencyJudge → §1.1=是

        fill_11 = judge_data_sufficiency(frame)



        # Step 1b: MarketChaosJudge → §1.3
        # Checks EMA flatness + high bar overlap + no directional signal.
        # Overridable: AI can disagree based on holistic reading.

        fill_13 = judge_market_chaos(frame)



        # Step 2: DirectionJudge → §2.3 + direction field

        direction, fill_23 = judge_direction(frame)

        out["direction"] = direction



        # Step 3: AlwaysInJudge → §2.4

        fill_24 = judge_always_in(frame)



        # Step 3b: MomentumStrengthJudge → §2.5
        # Assesses trend-bar dominance, overlap, pullback depth.
        # Overridable; per §2.5 rules, answer=否 does NOT trigger gate=wait.

        fill_25 = judge_momentum_strength(frame, direction=direction)



        # Convert NodeFill → trace dicts

        node_11 = build_program_trace_node(fill_11)

        node_13 = build_program_trace_node(fill_13)

        node_23 = build_program_trace_node(fill_23)

        node_24 = build_program_trace_node(fill_24)

        node_25 = build_program_trace_node(fill_25)

        # §2.5 is a NON-BLOCKING gate node: any answer (是/中性/否) still results in
        # gate_result=proceed.  Mark it explicitly so UI and audit readers are not
        # misled into thinking a 否 answer blocked the gate.
        node_25["non_blocking"] = True



        program_nodes = [node_11, node_13, node_23, node_24, node_25]



        # Step 4: Apply overrides

        node_overrides = out.get("node_overrides")

        final_nodes = apply_overrides(

            program_nodes,

            node_overrides,

            out=out,

            stage="stage1",

        )



        # Step 5: Merge into gate_trace
        # If gate_result is wait/unknown, prepend program nodes so the AI's terminating
        # node (answer=否/等待) remains at the end (validates "末条 answer ∈ {否,等待}").
        gate_result = str(out.get("gate_result", "")).lower()
        if gate_result in ("wait", "unknown"):
            out["gate_trace"] = merge_program_nodes_head(out["gate_trace"], final_nodes)
        else:
            out["gate_trace"] = merge_program_nodes(out["gate_trace"], final_nodes)

        # Step 6: Sync bar_analysis.always_in from the program-determined §2.4 node.
        # apply_overrides already handles the AI-override path via
        # _sync_always_in_from_24_override; this step covers the non-override path
        # where the program fills §2.4 directly and bar_analysis.always_in must match.
        node_24_final = next(
            (n for n in final_nodes if isinstance(n, dict) and str(n.get("node_id", "")) == "2.4"),
            None,
        )
        if node_24_final is not None:
            bar_analysis = out.get("bar_analysis")
            if isinstance(bar_analysis, dict):
                branch_24 = str(node_24_final.get("branch", "") or "").strip()
                answer_24 = str(node_24_final.get("answer", "") or "").strip()
                if branch_24 == "AIL":
                    bar_analysis["always_in"] = "long"
                elif branch_24 == "AIS":
                    bar_analysis["always_in"] = "short"
                elif answer_24 == "否":
                    bar_analysis["always_in"] = "neutral"

        # Step 7: Brooks trend_context (background vs trading direction)
        try:
            from pa_agent.ai.trend_context import build_trend_context

            out["trend_context"] = build_trend_context(frame, str(out.get("direction", "neutral")))
        except Exception as exc:  # noqa: BLE001
            logger.warning("build_trend_context failed: %s", exc)



    @staticmethod

    def apply_stage2(

        out: dict[str, Any],

        frame: Any,

        stage1_json: dict[str, Any] | None,

    ) -> None:

        """In-place modify stage2 JSON: fill §9.1/§9.2/§9.3/§9.5/§11, apply overrides."""

        # Short-circuit for gate-shortcircuited stage2

        if out.get("gate_shortcircuited"):

            return



        # Ensure decision_trace exists

        out.setdefault("decision_trace", [])

        out["decision_trace"] = _coerce_trace_list(out.get("decision_trace"))

        raw_decision = out.get("decision")
        decision = _coerce_dict(raw_decision)
        if raw_decision is not None and not isinstance(raw_decision, dict):
            out["decision"] = decision

        order_direction = str(decision.get("order_direction", "") or "").strip() or None



        # Get geometry features

        features: dict[int, Any] = {}

        try:

            from pa_agent.ai.kline_features import compute_kline_geometry_features

            raw_features = compute_kline_geometry_features(frame)

            features = {f.seq: f for f in raw_features}

        except Exception:  # noqa: BLE001

            logger.debug("kline geometry feature computation failed", exc_info=True)



        # Locate signal bar seq

        sig = _get_signal_seq(out, getattr(frame, "bars", ()))



        # Check §9.0 answer: if AI said no valid signal bar, skip §9.1-9.5
        # rather than injecting misleading program-computed values.
        # "否"  = no valid signal bar exists right now
        # "等待" = AI semantically means "no valid signal bar" (should be "否" but
        #          AI sometimes conflates "does it exist?" with "should I wait?").
        # Both map to skip §9.1-9.5 — unless this is a planned limit order.
        _dt = out["decision_trace"]
        _node_90 = next(
            (x for x in _dt if isinstance(x, dict) and str(x.get("node_id", "")) == "9.0"),
            None,
        )
        _planned_limit = is_planned_limit_order(out)
        _section9_has_signal = True
        if _node_90 is not None:
            _ans_90 = str(_node_90.get("answer", "") or "").strip()
            if _ans_90 in ("否", "等待") and not _planned_limit:
                _section9_has_signal = False
            elif _ans_90 in ("否", "等待") and has_background_limit_path(out):
                _section9_has_signal = True



        # Step 1: SignalBarJudge → §9.1, §9.2, §9.3

        fill_91 = judge_signal_bar_closed(sig, frame)

        fill_92 = judge_signal_bar_direction(sig, order_direction, features)

        fill_93 = judge_signal_bar_length(sig, features)



        # Step 2: FollowThroughJudge → §9.5

        fill_95 = judge_follow_through(sig, features)



        # Step 3: OrderMethodRouter → §11 nodes

        # Only inject if order is a trade type (not 不下单)

        current_order_type = decision.get("order_type")

        decision_trace = out["decision_trace"]

        sec11_fills: list[NodeFill] = []

        if current_order_type != "不下单":

            sec11_fills = route_order_method(stage1_json, decision, decision_trace)



        # Convert to dicts

        node_91 = build_program_trace_node(fill_91)

        node_92 = build_program_trace_node(fill_92)

        if fill_92.answer == "不适用":

            node_92["skipped"] = True

        node_93 = build_program_trace_node(fill_93)

        node_95 = build_program_trace_node(fill_95)

        # When §9.0=否 (no valid signal bar), mark §9.1-9.5 as skipped so they
        # don't appear as contradictory program-filled nodes in the trace.
        if not _section9_has_signal:
            _skip_reason = "§9.0=否（无有效信号棒），§9.1-9.5不适用，程序跳过。"
            for _node in (node_91, node_92, node_93, node_95):
                _node["skipped"] = True
                _node["answer"] = "不适用"
                _node["reason"] = _skip_reason
        elif _planned_limit:
            _bar_analysis = out.get("bar_analysis")
            _signal_bar = (
                _bar_analysis.get("signal_bar")
                if isinstance(_bar_analysis, dict)
                else None
            )
            _no_signal_bar = (
                not isinstance(_signal_bar, dict) or not _signal_bar.get("bar")
            )
            if _no_signal_bar or has_background_limit_path(out):
                _skip_reason = (
                    "计划型限价单（§9.0P 或 §9.0 背景路径），尚无已收盘信号棒，"
                    "§9.1-9.3不适用。"
                )
                for _node in (node_91, node_92, node_93):
                    _node["skipped"] = True
                    _node["answer"] = "不适用"
                    _node["reason"] = _skip_reason



        sec11_nodes = [build_program_trace_node(f) for f in sec11_fills]



        program_nodes = [node_91, node_92, node_93, node_95] + sec11_nodes



        # Step 4: Apply overrides

        node_overrides = out.get("node_overrides")

        final_nodes = apply_overrides(

            program_nodes,

            node_overrides,

            out=out,

            stage="stage2",

        )



        # Step 5: Merge into decision_trace

        out["decision_trace"] = merge_program_nodes(

            out["decision_trace"], final_nodes

        )

