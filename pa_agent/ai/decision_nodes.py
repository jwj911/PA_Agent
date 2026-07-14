"""Deterministic decision node engine for PA_Agent.



This module contains:

- PreflightDataGate: pre-AI data quality check

- DecisionNodeEngine: deterministic judge for §1.1/§2.3/§2.4/§9/§11 nodes

- OverrideArbiter: controlled override adjudication

- Various helper functions and constants

"""

from __future__ import annotations



import logging

import math

from typing import Any



from pa_agent.ai.bar_geometry import (
    _count_trend_bars,
    _find_swings,
    _mean_overlap_ratio,
)
from pa_agent.ai.decision_thresholds import (
    AI_PRIMARY_NODES,
    AI_PRIMARY_SUPPLEMENT_NODES,
    ALWAYS_IN_NEAR_SAME_SIDE_RATIO,
    ALWAYS_IN_NEAR_WINDOW,
    ALWAYS_IN_PULLBACK_ATR_RATIO,
    ALWAYS_IN_SAME_SIDE_RATIO,
    ALWAYS_IN_WINDOW,
    BAR_COUNT_THRESHOLD,  # noqa: F401  # re-exported for tests; used in diagnostic_judges
    EMA_SLOPE_LOOKBACK,
    LOCKED_NODES,
    MOMENTUM_OVERLAP_WEAK,
    MOMENTUM_PULLBACK_DEEP_ATR,
    MOMENTUM_TREND_BAR_MIN_RATIO,
    MOMENTUM_TREND_RATIO_STRONG,
    OVERRIDABLE_NODES,
    SAFETY_GATE_NODES,
    SIGNAL_BAR_LONG_ATR_RATIO,  # noqa: F401  # re-exported for tests; used in signal_bar_judges
)
from pa_agent.ai.diagnostic_judges import judge_data_sufficiency, judge_market_chaos
from pa_agent.ai.direction_judge import judge_direction
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



# ── AlwaysInJudge ─────────────────────────────────────────────────────────────


def _weighted_ema_side_weights(
    bars: Any, N: int, ema20: tuple,
) -> tuple[float, float]:
    """Linear-decay weighted counts of closes above/below EMA in first N bars."""
    w_above = 0.0
    w_below = 0.0
    for i, bar in enumerate(list(bars)[:N]):
        if i >= len(ema20):
            break
        try:
            ema_val = float(ema20[i])
            close_val = float(bar.close)
        except (TypeError, ValueError, AttributeError):
            continue
        if math.isnan(ema_val):
            continue
        weight = float(N - i)
        if close_val > ema_val:
            w_above += weight
        elif close_val < ema_val:
            w_below += weight
    return w_above, w_below


def _eval_always_in_gates(
    bars: Any,
    N: int,
    ema20: tuple,
    atr14: tuple,
    n: int,
    *,
    slope_lookback: int,
    same_side_ratio: float,
) -> dict[str, Any]:
    """Evaluate AIL/AIS gate bundle for a window of N bars (index 0 = newest)."""
    w_above, w_below = _weighted_ema_side_weights(bars, N, ema20)
    valid_w = w_above + w_below
    if valid_w <= 0:
        above_ratio = below_ratio = 0.0
    else:
        above_ratio = w_above / valid_w
        below_ratio = w_below / valid_w

    slope_sign = 0
    slope_desc = "EMA斜率:0"
    try:
        if ema20 and len(ema20) >= 1 and not math.isnan(float(ema20[0])):
            k = min(slope_lookback, n - 1)
            if k >= 1 and len(ema20) > k and not math.isnan(float(ema20[k])):
                d = float(ema20[0]) - float(ema20[k])
                thr = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr = 0.05 * float(atr14[0])
                if d > thr:
                    slope_sign = 1
                    slope_desc = f"EMA斜率向上(d={d:.4f}>thr={thr:.4f})"
                elif d < -thr:
                    slope_sign = -1
                    slope_desc = f"EMA斜率向下(d={d:.4f}<-thr={thr:.4f})"
                else:
                    slope_desc = f"EMA斜率平坦(d={d:.4f},死区±{thr:.4f})"
    except (TypeError, ValueError):
        pass

    swing_confirms_bull = False
    swing_confirms_bear = False
    swing_desc = "波段结构:未验证"
    try:
        swing_highs, swing_lows = _find_swings(bars, N)
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            hh = swing_highs[0] > swing_highs[1]
            hl = swing_lows[0] > swing_lows[1]
            ll = swing_lows[0] < swing_lows[1]
            lh = swing_highs[0] < swing_highs[1]
            if hh and hl:
                swing_confirms_bull = True
                swing_desc = "波段结构HH+HL✓(多头)"
            elif ll and lh:
                swing_confirms_bear = True
                swing_desc = "波段结构LL+LH✓(空头)"
            else:
                swing_desc = f"波段结构混乱(HH={hh},HL={hl},LL={ll},LH={lh})"
        else:
            swing_desc = (
                f"波段结构:枢轴不足(highs={len(swing_highs)},lows={len(swing_lows)})"
            )
    except (TypeError, ValueError, IndexError):
        pass

    pullback_atr = _max_pullback_atr(bars, N, ema20, atr14)
    shallow = None
    pullback_desc = "回撤:未知(ATR缺失)"
    if pullback_atr is not None:
        shallow = pullback_atr <= ALWAYS_IN_PULLBACK_ATR_RATIO
        pullback_desc = (
            f"最大价格区间{pullback_atr:.2f}×ATR"
            f"({'≤' if shallow else '>'}{ALWAYS_IN_PULLBACK_ATR_RATIO}×阈值,"
            f"{'浅回撤✓' if shallow else '回撤较深✗'})"
        )

    bull_core = above_ratio >= same_side_ratio and slope_sign > 0
    bear_core = below_ratio >= same_side_ratio and slope_sign < 0
    gate3_bull = swing_confirms_bull and (shallow is None or shallow)
    gate3_bear = swing_confirms_bear and (shallow is None or shallow)

    return {
        "N": N,
        "above_ratio": above_ratio,
        "below_ratio": below_ratio,
        "slope_sign": slope_sign,
        "slope_desc": slope_desc,
        "swing_desc": swing_desc,
        "pullback_desc": pullback_desc,
        "bull_core": bull_core,
        "bear_core": bear_core,
        "gate3_bull": gate3_bull,
        "gate3_bear": gate3_bear,
    }


def _max_pullback_atr(bars: Any, N: int, ema20: tuple, atr14: tuple) -> float | None:
    """Compute the max intra-window pullback depth relative to ATR.

    For a bullish context (price above EMA), the pullback is the maximum
    distance from the highest close down to the lowest close within the window.
    Returns None if ATR is unavailable.

    Used by judge_always_in to verify §2.4 "回撤浅" condition.
    """
    try:
        if not atr14 or math.isnan(float(atr14[0])) or float(atr14[0]) <= 0:
            return None
        atr_val = float(atr14[0])
        closes = []
        for bar in list(bars)[:N]:
            try:
                closes.append(float(bar.close))
            except (TypeError, ValueError, AttributeError):
                pass
        if len(closes) < 2:
            return None
        max_range = max(closes) - min(closes)
        return max_range / atr_val
    except (TypeError, ValueError):
        return None


def judge_always_in(frame: Any) -> NodeFill:
    """Judge Always In state (§2.4) with dual-window Brooks alignment.

    Near window (K8-K1) is authoritative — captures current inertia / spike.
    Background window (K20-K1) is reference only — does not veto near conclusion.

    Gate 1: weighted same-side ratio vs EMA.
    Gate 2: EMA slope confirms direction.
    Gate 3: swing structure + shallow pullback (strength label only).
    """
    bars = getattr(frame, "bars", ()) or ()
    indicators = getattr(frame, "indicators", None)
    ema20 = tuple(getattr(indicators, "ema20", ()) or ())
    atr14 = tuple(getattr(indicators, "atr14", ()) or ())

    n = 0
    try:
        n = max(int(getattr(b, "seq", 0)) for b in bars)
    except (TypeError, ValueError):
        n = len(bars)

    N_near = min(ALWAYS_IN_NEAR_WINDOW, n)
    N_bg = min(ALWAYS_IN_WINDOW, n)

    near = _eval_always_in_gates(
        bars, N_near, ema20, atr14, n,
        slope_lookback=min(5, n - 1),
        same_side_ratio=ALWAYS_IN_NEAR_SAME_SIDE_RATIO,
    )
    bg = _eval_always_in_gates(
        bars, N_bg, ema20, atr14, n,
        slope_lookback=EMA_SLOPE_LOOKBACK,
        same_side_ratio=ALWAYS_IN_SAME_SIDE_RATIO,
    )

    bar_range = f"K{N_near}-K1"
    conflict_note = ""

    if near["bull_core"]:
        answer = "是"
        branch = "AIL"
        strength = "（结构确认，强AIL）" if near["gate3_bull"] else "（结构弱/回撤深，弱AIL）"
        if bg["bear_core"]:
            conflict_note = (
                f" ⚠️ 近端K{N_near}-K1已切换多头惯性（加权同侧{near['above_ratio']:.0%}），"
                f"背景K{N_bg}-K1仍偏空（加权同侧{bg['below_ratio']:.0%}）——"
                "按Brooks并列原则：近端AIL为交易主方向，背景AIS仅作上方阻力风险提示，不否决做多。"
            )
        reason = (
            f"【近端主判K{N_near}-K1】加权收盘高于EMA占比{near['above_ratio']:.1%}"
            f"≥{ALWAYS_IN_NEAR_SAME_SIDE_RATIO:.0%}；{near['slope_desc']}；"
            f"{near['swing_desc']}；{near['pullback_desc']}。"
            f"判定为Always In Long（AIL）{strength}。"
            f"【背景参考K{N_bg}-K1】加权多侧{bg['above_ratio']:.1%}/空侧{bg['below_ratio']:.1%}；"
            f"{bg['slope_desc']}。"
            f"{conflict_note}"
        )
    elif near["bear_core"]:
        answer = "是"
        branch = "AIS"
        strength = "（结构确认，强AIS）" if near["gate3_bear"] else "（结构弱/回撤深，弱AIS）"
        if bg["bull_core"]:
            conflict_note = (
                f" ⚠️ 近端K{N_near}-K1已切换空头惯性（加权同侧{near['below_ratio']:.0%}），"
                f"背景K{N_bg}-K1仍偏多（加权同侧{bg['above_ratio']:.0%}）——"
                "按Brooks并列原则：近端AIS为交易主方向，背景AIL仅作下方支撑风险提示，不否决做空。"
            )
        reason = (
            f"【近端主判K{N_near}-K1】加权收盘低于EMA占比{near['below_ratio']:.1%}"
            f"≥{ALWAYS_IN_NEAR_SAME_SIDE_RATIO:.0%}；{near['slope_desc']}；"
            f"{near['swing_desc']}；{near['pullback_desc']}。"
            f"判定为Always In Short（AIS）{strength}。"
            f"【背景参考K{N_bg}-K1】加权多侧{bg['above_ratio']:.1%}/空侧{bg['below_ratio']:.1%}；"
            f"{bg['slope_desc']}。"
            f"{conflict_note}"
        )
    elif bg["bull_core"]:
        answer = "是"
        branch = "AIL"
        strength = "（仅背景确认，近端未共振，弱AIL）"
        reason = (
            f"【近端K{N_near}-K1】未达AIL阈值（多侧{near['above_ratio']:.1%}，{near['slope_desc']}）。"
            f"【背景K{N_bg}-K1】仍满足AIL（多侧{bg['above_ratio']:.1%}，{bg['slope_desc']}）"
            f"→弱AIL，优先等待近端结构确认。"
            f"{strength}"
        )
    elif bg["bear_core"]:
        answer = "是"
        branch = "AIS"
        strength = "（仅背景确认，近端未共振，弱AIS）"
        reason = (
            f"【近端K{N_near}-K1】未达AIS阈值（空侧{near['below_ratio']:.1%}，{near['slope_desc']}）。"
            f"【背景K{N_bg}-K1】仍满足AIS（空侧{bg['below_ratio']:.1%}，{bg['slope_desc']}）"
            f"→弱AIS，优先等待近端结构确认。"
            f"{strength}"
        )
    else:
        answer = "否"
        branch = None
        reason = (
            f"【近端K{N_near}-K1】多侧{near['above_ratio']:.1%}/空侧{near['below_ratio']:.1%}；"
            f"{near['slope_desc']}；{near['swing_desc']}。"
            f"【背景K{N_bg}-K1】多侧{bg['above_ratio']:.1%}/空侧{bg['below_ratio']:.1%}；"
            f"{bg['slope_desc']}。"
            "近端与背景均未达Always In阈值。"
        )

    return NodeFill(
        node_id="2.4",
        answer=answer,
        reason=reason,
        bar_range=bar_range,
        branch=branch,
    )


# ── MomentumStrengthJudge ──────────────────────────────────────────────────────


def judge_momentum_strength(frame: Any, direction: str = "neutral") -> NodeFill:
    """Judge §2.5: is current momentum strong enough to support trend-following?

    Uses a DUAL-WINDOW approach: near-term (8 bars) as primary judge of CURRENT
    momentum, 20-bar background as supplementary reference only.
    Momentum is a "current state" concept — recent bars dominate the assessment.

    Three signals assessed over W_near (min(8, n)):
      M1: Trend-bar dominance — ratio of direction-aligned to opposing trend bars
      M2: Bar overlap — low overlap → strong momentum, high overlap → weak
      M3: Pullback depth — shallow pullback (≤ MOMENTUM_PULLBACK_DEEP_ATR × ATR)

    Scoring:
      strong_count ≥ 2 → answer=是  (strong momentum, trend-following allowed)
      strong_count == 1 → answer=中性 (moderate; branch=broad_channel; caution)
      strong_count == 0 → answer=否  (weak; NOT gate=wait per §2.5 rules)

    Since §2.5 is AI_PRIMARY, if AI already wrote this node the program result
    becomes supplementary reference data appended to the AI node's reason.
    """
    bars = getattr(frame, "bars", ()) or ()
    indicators = getattr(frame, "indicators", None)
    ema20 = tuple(getattr(indicators, "ema20", ()) or ())
    atr14 = tuple(getattr(indicators, "atr14", ()) or ())

    try:
        n = max(int(getattr(b, "seq", 0)) for b in bars)
    except (TypeError, ValueError):
        n = len(bars)

    MOMENTUM_NEAR_WINDOW: int = 8
    W_near = min(MOMENTUM_NEAR_WINDOW, n)
    W_bg = min(ALWAYS_IN_WINDOW, n)
    bar_range = f"K{W_near}-K1"

    # ── M1: Trend-bar dominance (near-term) ──────────────────────────────────
    bull_tb, bear_tb = _count_trend_bars(bars, W_near)
    total_tb = bull_tb + bear_tb
    total_bars_in_window = min(W_near, len(list(bars)))
    # Absolute floor: directional trend bars must make up ≥ MOMENTUM_TREND_BAR_MIN_RATIO
    # of ALL bars in the window.  Without this, 2 bear vs 1 bull in 8 bars triggers
    # "dominant" even though 63% of bars are doji/inside (hesitation, not trend).
    abs_floor_met = (
        total_bars_in_window > 0
        and total_tb / total_bars_in_window >= MOMENTUM_TREND_BAR_MIN_RATIO
    )
    m1_strong = False
    if abs_floor_met:
        if direction == "bullish" and bull_tb >= MOMENTUM_TREND_RATIO_STRONG * max(bear_tb, 1):
            m1_strong = True
        elif direction == "bearish" and bear_tb >= MOMENTUM_TREND_RATIO_STRONG * max(bull_tb, 1):
            m1_strong = True
        # direction=neutral: M1 cannot be "dominant" — if the program itself calls
        # the direction neutral it means neither side leads convincingly.
        # A 3:2 ratio in 8 bars is noise, not momentum.  Leave m1_strong=False.
    abs_ratio_str = f"{total_tb}/{total_bars_in_window}={total_tb/max(total_bars_in_window,1):.0%}" if total_bars_in_window else "N/A"
    m1_desc = (
        f"近{W_near}根趋势棒（多{bull_tb}/空{bear_tb}，总趋势棒占比{abs_ratio_str}，"
        f"方向={direction}，"
        f"{'占优✓' if m1_strong else ('中性方向无占优✗' if direction == 'neutral' and abs_floor_met else '占比不足✗' if not abs_floor_met else '不占优✗')}）"
    )

    # ── M2: Bar overlap (near-term) ───────────────────────────────────────────
    mean_overlap = _mean_overlap_ratio(bars, W_near)
    m2_strong = mean_overlap is not None and mean_overlap < MOMENTUM_OVERLAP_WEAK
    if mean_overlap is None:
        m2_desc = "K线重叠:数据不足"
    else:
        m2_desc = (
            f"近{W_near}根重叠均值{mean_overlap:.2f}"
            f"({'<' if m2_strong else '≥'}{MOMENTUM_OVERLAP_WEAK}阈值,"
            f"{'重叠低✓' if m2_strong else '重叠高✗'})"
        )

    # ── M3: Pullback depth (near-term) ────────────────────────────────────────
    pullback_atr = _max_pullback_atr(bars, W_near, ema20, atr14)
    if pullback_atr is None:
        m3_strong = None
        m3_desc = "回撤深度:ATR不可用"
    else:
        m3_strong = pullback_atr <= MOMENTUM_PULLBACK_DEEP_ATR
        m3_desc = (
            f"近{W_near}根最大回撤{pullback_atr:.2f}×ATR"
            f"({'≤' if m3_strong else '>'}{MOMENTUM_PULLBACK_DEEP_ATR}×阈值,"
            f"{'回撤浅✓' if m3_strong else '回撤深✗'})"
        )

    # ── Background metrics (20-bar, reference only) ──────────────────────────
    bull_tb_bg, bear_tb_bg = _count_trend_bars(bars, W_bg)
    overlap_bg = _mean_overlap_ratio(bars, W_bg)
    bg_desc = (
        f"背景参考K{W_bg}-K1（趋势棒多{bull_tb_bg}/空{bear_tb_bg}，"
        f"重叠{f'{overlap_bg:.2f}' if overlap_bg is not None else 'N/A'}）"
    )

    # ── Scoring ───────────────────────────────────────────────────────────────
    strong_count = int(m1_strong) + int(m2_strong) + (int(m3_strong) if m3_strong is not None else 0)

    if strong_count >= 2:
        answer = "是"
        branch = None
        conclusion = "惯性强，支持趋势跟踪。"
    elif strong_count == 1:
        answer = "中性"
        branch = "broad_channel"
        conclusion = "惯性中等，宜转为等待反弹衰竭信号，不宜激进追势。"
    else:
        answer = "否"
        branch = None
        conclusion = (
            "惯性偏弱，不宜趋势跟踪；但§2.5否不触发gate=wait，"
            "继续进入策略分支等待合适入场时机。"
        )

    reason = (
        f"近端强度信号{strong_count}/3（主判K{W_near}-K1）："
        f"{m1_desc}；{m2_desc}；{m3_desc}。{conclusion}"
        f" {bg_desc}。"
    )

    return NodeFill(
        node_id="2.5",
        answer=answer,
        reason=reason,
        bar_range=bar_range,
        branch=branch,
    )


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





# ── OverrideArbiter ───────────────────────────────────────────────────────────



def _conservativeness_rank(node_id: str, answer: str) -> int:

    """Return conservativeness rank for safety gate ordering (higher = more conservative)."""

    nid = str(node_id).strip()

    ans = str(answer).strip()



    if nid == "10.3":

        return 5 if ans == "否" else 3

    if nid == "14":

        return 5 if ans == "是" else 3

    # order_type dimension (§11 nodes)

    if nid in ("11.1", "11.2", "11.3", "11.4"):

        return 5 if ans == "不下单" else 3

    return 3





def write_override_trace(node: dict[str, Any], override: dict[str, Any]) -> None:

    """Write override trace fields to node (in-place). Records program original values."""

    node["program_answer"] = node.get("answer")

    if "branch" in node:

        node["program_branch"] = node.get("branch")

    node["answer"] = override["answer"]

    if override.get("branch"):

        node["branch"] = override["branch"]

    node["override_reason"] = str(override.get("override_reason", "")).strip()

    node["overridden_by_ai"] = True





def _node_id_sort_key(node_id: str) -> tuple[int, int, str]:
    """Numeric sort key for gate_trace node_id values.

    Converts '1.1' -> (1, 1, '1.1'), '2.3' -> (2, 3, '2.3') so that merged
    program nodes sort into natural chapter-section order regardless of how
    the AI ordered its trace entries.
    """
    parts = str(node_id or "").split(".", 1)
    try:
        major = int(parts[0])
    except (ValueError, IndexError):
        return (999, 999, node_id)
    if len(parts) == 1:
        return (major, 0, node_id)
    sub = parts[1]
    try:
        return (major, int(sub), node_id)
    except ValueError:
        return (major, 999, node_id)


def merge_program_nodes(

    trace: list[dict[str, Any]],

    program_nodes: list[dict[str, Any]],

) -> list[dict[str, Any]]:

    """Merge program nodes into trace by node_id.

    Two merge modes based on node type:

    PROGRAM-AUTHORITATIVE (default):
      Program result replaces the AI node entirely.  Used for §1.1, §2.3, §2.4
      where the program has definitive computed data.

    AI-PRIMARY (AI_PRIMARY_NODES — §1.3 and §2.5):
      If the AI already wrote the node, preserve the AI version (no program append).

    New program nodes not already in the AI trace are inserted in chapter-section
    order (1.1 < 1.2 < 2.3 < 2.5) so the UI renders the correct decision path.
    """

    result = _coerce_trace_list(trace)

    prog_by_id = {n["node_id"]: n for n in program_nodes if isinstance(n, dict) and "node_id" in n}



    replaced_ids: set[str] = set()

    for i, item in enumerate(result):

        if not isinstance(item, dict):

            continue

        nid = str(item.get("node_id", "")).strip()

        if nid not in prog_by_id:

            continue

        if nid in AI_PRIMARY_NODES:

            if nid in AI_PRIMARY_SUPPLEMENT_NODES:
                # AI-primary + program supplement in reason (§1.3 only)
                prog_node = prog_by_id[nid]
                prog_reason = str(prog_node.get("reason", "") or "").strip()
                prog_bar_range = str(prog_node.get("bar_range", "") or "").strip()
                if prog_reason:
                    ai_reason = str(item.get("reason", "") or "").strip()
                    supplement = f"【程序参考数据（{prog_bar_range}）：{prog_reason}】"
                    if supplement not in ai_reason:
                        result[i] = dict(item)
                        result[i]["reason"] = f"{ai_reason} {supplement}".strip()
            # §2.5: keep AI node as-is; program metrics are not appended to reason.

        else:

            # Program-authoritative: program result replaces AI node
            result[i] = prog_by_id[nid]

        replaced_ids.add(nid)



    # Insert new nodes then re-sort by numeric node_id so injected program nodes
    # land in their natural document position (1.1 < 1.2 < 2.3 < 2.5) rather
    # than being appended to the tail of whatever order the AI produced.

    new_nodes = [node for nid, node in prog_by_id.items() if nid not in replaced_ids]

    if new_nodes:

        result.extend(new_nodes)

        result.sort(

            key=lambda x: _node_id_sort_key(str(x.get("node_id", "")))

            if isinstance(x, dict) else (999, 999, "")

        )



    return result


def merge_program_nodes_head(

    trace: list[dict[str, Any]],

    program_nodes: list[dict[str, Any]],

) -> list[dict[str, Any]]:

    """Merge program nodes into trace, placing NEW nodes at the HEAD (before AI nodes).

    Used when gate_result=wait/unknown so the AI's terminating node stays at the end.
    Applies the same AI-PRIMARY / program-authoritative distinction as merge_program_nodes:
    §1.3 and §2.5 preserve the AI version without appending program data to reason.
    """

    # First replace existing entries in-place (same as merge_program_nodes)
    result = _coerce_trace_list(trace)

    prog_by_id = {n["node_id"]: n for n in program_nodes if isinstance(n, dict) and "node_id" in n}

    replaced_ids: set[str] = set()

    for i, item in enumerate(result):

        if not isinstance(item, dict):

            continue

        nid = str(item.get("node_id", "")).strip()

        if nid not in prog_by_id:

            continue

        if nid in AI_PRIMARY_NODES:

            if nid in AI_PRIMARY_SUPPLEMENT_NODES:
                prog_node = prog_by_id[nid]
                prog_reason = str(prog_node.get("reason", "") or "").strip()
                prog_bar_range = str(prog_node.get("bar_range", "") or "").strip()
                if prog_reason:
                    ai_reason = str(item.get("reason", "") or "").strip()
                    supplement = f"【程序参考数据（{prog_bar_range}）：{prog_reason}】"
                    if supplement not in ai_reason:
                        result[i] = dict(item)
                        result[i]["reason"] = f"{ai_reason} {supplement}".strip()

        else:

            result[i] = prog_by_id[nid]

        replaced_ids.add(nid)

    # Sort new nodes by node_id then prepend before the AI's existing nodes so
    # injected program nodes appear in chapter order, while the AI's terminating
    # node (answer=否/等待) remains at the end of the trace.
    new_nodes = sorted(
        [node for nid, node in prog_by_id.items() if nid not in replaced_ids],
        key=lambda x: _node_id_sort_key(str(x.get("node_id", ""))) if isinstance(x, dict) else (999, 999, ""),
    )

    return new_nodes + result





def apply_overrides(

    program_nodes: list[dict[str, Any]],

    node_overrides: Any,

    *,

    out: dict[str, Any],

    stage: str,

) -> list[dict[str, Any]]:

    """Apply controlled overrides to program nodes. Returns final node list with traces.



    Rules (in order):

    1. node_overrides not a list → ignore all

    2. invalid element → skip

    3. locked node → ignore (log)

    4. missing override_reason → reject

    5. safety gate in aggressive direction → reject

    6. §2.3 direction consistency check

    7. valid override → accept, write trace

    """

    from pa_agent.ai.decision_tree import TRACE_ANSWERS



    result = [dict(n) for n in program_nodes]

    prog_ids = {n["node_id"] for n in result if isinstance(n, dict) and "node_id" in n}



    if not isinstance(node_overrides, list):

        return result



    # Build index for fast lookup

    node_index = {n["node_id"]: i for i, n in enumerate(result) if isinstance(n, dict) and "node_id" in n}



    seen_overrides: set[str] = set()



    for ov in node_overrides:

        if not isinstance(ov, dict):

            continue

        node_id = str(ov.get("node_id", "")).strip()

        if not node_id:

            continue

        if node_id not in prog_ids:

            continue

        answer = str(ov.get("answer", "")).strip()

        if answer not in TRACE_ANSWERS:

            continue



        # Take first valid override per node_id

        if node_id in seen_overrides:

            continue

        seen_overrides.add(node_id)



        # Rule 3: locked node

        if node_id in LOCKED_NODES:

            logger.info(

                "apply_overrides: ignoring override for locked node %s (stage=%s)",

                node_id, stage,

            )

            continue



        # Rule 4: missing override_reason

        override_reason = str(ov.get("override_reason", "") or "").strip()

        if not override_reason:

            logger.debug(

                "apply_overrides: rejecting override for %s - missing override_reason",

                node_id,

            )

            continue



        # Rule 5: safety gate direction check

        if node_id in SAFETY_GATE_NODES:

            idx = node_index.get(node_id)

            if idx is not None:

                current_answer = str(result[idx].get("answer", "")).strip()

                current_rank = _conservativeness_rank(node_id, current_answer)

                new_rank = _conservativeness_rank(node_id, answer)

                if new_rank < current_rank:

                    logger.debug(

                        "apply_overrides: rejecting aggressive safety gate override "

                        "for %s (rank %d -> %d is less conservative)",

                        node_id, current_rank, new_rank,

                    )

                    continue



        # Rule 6: §2.3 direction consistency

        if node_id == "2.3":

            branch = str(ov.get("branch", "") or "").strip()

            valid = _validate_dir_override(answer, branch)

            if not valid:

                logger.debug(

                    "apply_overrides: rejecting §2.3 override - "

                    "answer/branch inconsistent: answer=%s branch=%s",

                    answer, branch,

                )

                continue

            # Accept: write trace and sync direction

            idx = node_index.get(node_id)

            if idx is not None:

                write_override_trace(result[idx], ov)

                # Sync direction field

                direction_map = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}

                if branch in direction_map:

                    out["direction"] = direction_map[branch]

            continue



        # Rule 7: accept override for OVERRIDABLE_NODES

        if node_id in OVERRIDABLE_NODES:

            idx = node_index.get(node_id)

            if idx is not None:

                write_override_trace(result[idx], ov)

                # §11 override: sync order_type

                if node_id in ("11.1", "11.2", "11.3", "11.4"):

                    _sync_order_type_from_11_override(out, result[idx], ov)

                # §2.4 override: sync bar_analysis.always_in so the field stays
                # consistent with the final (possibly AI-overridden) §2.4 branch.
                # Without this, bar_analysis.always_in keeps the program's value
                # while direction/gate_trace reflect the AI's override — self-contradiction.
                if node_id == "2.4":

                    _sync_always_in_from_24_override(out, ov)



    return result





def _validate_dir_override(answer: str, branch: str) -> bool:

    """Validate §2.3 answer/branch consistency."""

    if branch in ("bullish", "bearish"):

        return answer == "是"

    elif branch == "neutral":

        return answer == "中性"

    return False  # invalid branch





def _sync_always_in_from_24_override(
    out: dict[str, Any],
    override: dict[str, Any],
) -> None:
    """After §2.4 override accepted, sync bar_analysis.always_in to match the
    AI-overridden branch.  Without this sync, bar_analysis.always_in keeps the
    program's original value while the gate_trace §2.4 node shows the overridden
    branch — a self-contradiction that caused the confusion in the pending record.

    Mapping:
      branch=AIL  → always_in="long"
      branch=AIS  → always_in="short"
      answer=否   → always_in="neutral"
    """
    bar_analysis = out.get("bar_analysis")
    if not isinstance(bar_analysis, dict):
        return

    branch = str(override.get("branch", "") or "").strip()
    answer = str(override.get("answer", "") or "").strip()

    if branch == "AIL":
        bar_analysis["always_in"] = "long"
    elif branch == "AIS":
        bar_analysis["always_in"] = "short"
    elif answer == "否":
        bar_analysis["always_in"] = "neutral"
    # If branch is unrecognised or missing, leave as-is to avoid silent corruption.


def _sync_order_type_from_11_override(

    out: dict[str, Any],

    node: dict[str, Any],

    override: dict[str, Any],

) -> None:

    """After §11 override accepted, sync decision.order_type if not 不下单."""

    decision = out.get("decision")

    if not isinstance(decision, dict):

        return



    new_answer = str(override.get("answer", "")).strip()

    if new_answer != "是":

        return



    node_id = str(node.get("node_id", ""))

    node_method_map = {

        "11.1": "市价单",

        "11.2": "突破单",

        "11.3": "限价单",

        "11.4": "限价单",

    }

    method = node_method_map.get(node_id)

    if not method or decision.get("order_type") == "不下单":

        return



    existing = str(decision.get("order_type") or "").strip()

    has_basis = bool(

        decision.get("entry_basis_bar") and decision.get("entry_basis_extreme")

    )

    # Mirror judge_section11 breakout_fallback_to_limit: §11.2 defaults to 突破单,

    # but without basis fields the schema rejects null entry_basis_*. Preserve an

    # explicit 限价单/市价单 plan (e.g. §9.0P planned limit) instead of forcing 突破单.

    if method == "突破单" and not has_basis:

        if existing in ("限价单", "市价单"):

            return

        method = "限价单"



    decision["order_type"] = method





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

