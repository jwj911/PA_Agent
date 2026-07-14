"""Always-In (§2.4) and momentum-strength (§2.5) section judges.

Section-judge cluster split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). Holds the two §2 trend-state judges that
``DecisionNodeEngine.apply_stage2`` fills:

- :func:`judge_always_in` — §2.4 Always-In state with dual-window (near K8-K1
  authoritative, background K20-K1 reference) Brooks alignment.
- :func:`judge_momentum_strength` — §2.5 momentum strength (dual-window,
  three near-term signals: trend-bar dominance, bar overlap, pullback depth).

These two judges share the private helper :func:`_max_pullback_atr` (also used
by ``_eval_always_in_gates``), so they are extracted together as one cluster
rather than one at a time. The cluster depends only on leaf modules —
``NodeFill`` (from :mod:`pa_agent.ai.trace_nodes`), the geometry primitives
``_count_trend_bars`` / ``_find_swings`` / ``_mean_overlap_ratio`` (from
:mod:`pa_agent.ai.bar_geometry`) and the Always-In / momentum thresholds (from
:mod:`pa_agent.ai.decision_thresholds`) — so pulling it here creates no import
cycle. ``decision_nodes`` re-exports both judges, so existing
``from pa_agent.ai.decision_nodes import judge_always_in`` sites keep working
byte-for-byte. Behaviour (answers, Chinese reason strings, gate arithmetic,
bar_range) must stay identical to the original.
"""
from __future__ import annotations

import math
from typing import Any

from pa_agent.ai.bar_geometry import (
    _count_trend_bars,
    _find_swings,
    _mean_overlap_ratio,
)
from pa_agent.ai.decision_thresholds import (
    ALWAYS_IN_NEAR_SAME_SIDE_RATIO,
    ALWAYS_IN_NEAR_WINDOW,
    ALWAYS_IN_PULLBACK_ATR_RATIO,
    ALWAYS_IN_SAME_SIDE_RATIO,
    ALWAYS_IN_WINDOW,
    EMA_SLOPE_LOOKBACK,
    MOMENTUM_OVERLAP_WEAK,
    MOMENTUM_PULLBACK_DEEP_ATR,
    MOMENTUM_TREND_BAR_MIN_RATIO,
    MOMENTUM_TREND_RATIO_STRONG,
)
from pa_agent.ai.trace_nodes import NodeFill

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
