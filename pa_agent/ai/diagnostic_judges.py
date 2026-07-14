"""Stage-1 diagnostic section judges (§1.1, §1.3) for the decision node engine.

Section-judge cluster split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). Holds the two deterministic §1 market-diagnosis judges that
``DecisionNodeEngine.apply_stage1`` fills:

- :func:`judge_data_sufficiency` — §1.1 data sufficiency (always 是; the
  PreflightDataGate has already passed, so this records the closed-bar count).
- :func:`judge_market_chaos` — §1.3 extreme-chaos diagnosis. Per design it
  always returns 否 (extreme_tr needs holistic AI judgement, no hard program
  gate) but embeds three objective chaos-signal counts (flat EMA slope, high
  overlap, no directional conviction) so the AI can decide whether to submit a
  §1.3=是 node_override.

Like the other extracted judges this cluster depends only on leaf modules —
``NodeFill`` (from :mod:`pa_agent.ai.trace_nodes`), the geometry primitives
``_count_trend_bars`` / ``_mean_overlap_ratio`` (from
:mod:`pa_agent.ai.bar_geometry`) and the diagnosis thresholds (from
:mod:`pa_agent.ai.decision_thresholds`) — so pulling it here creates no import
cycle. ``decision_nodes`` re-exports both judges, so existing
``from pa_agent.ai.decision_nodes import judge_data_sufficiency`` sites keep
working byte-for-byte. Behaviour (answers, Chinese reason strings, chaos_score
arithmetic, bar_range) must stay identical to the original.
"""
from __future__ import annotations

import math
from typing import Any

from pa_agent.ai.bar_geometry import _count_trend_bars, _mean_overlap_ratio
from pa_agent.ai.decision_thresholds import (
    ALWAYS_IN_WINDOW,
    BAR_COUNT_THRESHOLD,
    CHAOS_DIRECTION_SCORE_MAX,
    CHAOS_EMA_FLAT_ATR_RATIO,
    CHAOS_OVERLAP_THRESHOLD,
    EMA_SLOPE_LOOKBACK,
    TREND_BAR_DOMINANCE_RATIO,
)
from pa_agent.ai.trace_nodes import NodeFill

# ── DataSufficiencyJudge ──────────────────────────────────────────────────────



def judge_data_sufficiency(frame: Any) -> NodeFill:

    """Fill §1.1=是 (data already sufficient, PreflightDataGate already passed)."""

    bars = getattr(frame, "bars", ()) or ()

    try:

        n = max(int(getattr(b, "seq", 0)) for b in bars)

    except (TypeError, ValueError):

        n = len(bars)

    return NodeFill(

        node_id="1.1",

        answer="是",

        reason=f"已收盘K线 {n} 根 ≥ {BAR_COUNT_THRESHOLD} 根阈值（已通过前置数据闸门），数据量满足分析要求。",

        bar_range=f"K{n}-K1",

    )





# ── MarketChaosJudge ──────────────────────────────────────────────────────────


def judge_market_chaos(frame: Any) -> NodeFill:
    """Judge §1.3: is the market in extreme chaos (extreme_tr)?

    Per 市场诊断框架.txt: extreme_tr判定依赖模型综合判断，不设硬性量化门槛。
    宁可稍晚输出，也不要过早输出而错过交易机会。

    Therefore this function ALWAYS returns answer=否 (default conservative).
    The reason text includes objective chaos signal counts so the AI has
    concrete data to decide whether to submit a node_override with answer=是.

    Three chaos signals assessed (each contributes 1 point to chaos_score):
      C1: EMA slope essentially flat (|slope| < CHAOS_EMA_FLAT_ATR_RATIO × ATR)
      C2: Mean bar overlap very high (≥ CHAOS_OVERLAP_THRESHOLD)
      C3: No directional conviction (|simple_direction_score| ≤ CHAOS_DIRECTION_SCORE_MAX)

    The program always outputs 否; AI should override to 是 only when all three
    signals are strongly present AND its holistic reading confirms extreme chaos.
    """
    bars = getattr(frame, "bars", ()) or ()
    indicators = getattr(frame, "indicators", None)
    ema20 = tuple(getattr(indicators, "ema20", ()) or ())
    atr14 = tuple(getattr(indicators, "atr14", ()) or ())

    try:
        n = max(int(getattr(b, "seq", 0)) for b in bars)
    except (TypeError, ValueError):
        n = len(bars)

    W = min(ALWAYS_IN_WINDOW, n)  # use same 20-bar window for consistency
    bar_range = f"K{W}-K1"

    # ── C1: EMA slope flatness ────────────────────────────────────────────────
    ema_flat = False
    c1_desc = "EMA斜率:无法计算"
    try:
        if ema20 and len(ema20) >= 1 and not math.isnan(float(ema20[0])):
            k = min(EMA_SLOPE_LOOKBACK, n - 1)
            if k >= 1 and len(ema20) > k and not math.isnan(float(ema20[k])):
                slope = float(ema20[0]) - float(ema20[k])
                thr = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr = CHAOS_EMA_FLAT_ATR_RATIO * float(atr14[0])
                ema_flat = abs(slope) < thr
                c1_desc = (
                    f"EMA斜率({'平坦✓' if ema_flat else '有方向✗'}"
                    f",d={slope:.4f},阈值±{thr:.4f})"
                )
    except (TypeError, ValueError):
        pass

    # ── C2: High overlap ──────────────────────────────────────────────────────
    mean_overlap = _mean_overlap_ratio(bars, W)
    high_overlap = mean_overlap is not None and mean_overlap >= CHAOS_OVERLAP_THRESHOLD
    if mean_overlap is None:
        c2_desc = "K线重叠:数据不足"
    else:
        c2_desc = (
            f"K线重叠均值{mean_overlap:.2f}"
            f"({'≥' if high_overlap else '<'}{CHAOS_OVERLAP_THRESHOLD}阈值,"
            f"{'重叠高✓' if high_overlap else '重叠适中✗'})"
        )

    # ── C3: No directional conviction — reuse direction score from §2.3 ──────
    # We compute a simplified 2-signal score here to avoid calling judge_direction
    # twice; the full 5-signal §2.3 result will still be injected separately.
    bull_tb, bear_tb = _count_trend_bars(bars, W)
    total_tb = bull_tb + bear_tb
    tb_score = 0
    if total_tb >= 3:
        if bull_tb >= TREND_BAR_DOMINANCE_RATIO * max(bear_tb, 1):
            tb_score = 1
        elif bear_tb >= TREND_BAR_DOMINANCE_RATIO * max(bull_tb, 1):
            tb_score = -1

    # EMA slope direction (simple ±1)
    slope_score = 0
    try:
        if ema20 and len(ema20) >= 1 and not math.isnan(float(ema20[0])):
            k = min(EMA_SLOPE_LOOKBACK, n - 1)
            if k >= 1 and len(ema20) > k and not math.isnan(float(ema20[k])):
                slope = float(ema20[0]) - float(ema20[k])
                thr = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr = CHAOS_EMA_FLAT_ATR_RATIO * float(atr14[0])
                if slope > thr:
                    slope_score = 1
                elif slope < -thr:
                    slope_score = -1
    except (TypeError, ValueError):
        pass

    simple_score = tb_score + slope_score
    no_direction = abs(simple_score) <= CHAOS_DIRECTION_SCORE_MAX
    c3_desc = (
        f"方向信号(趋势棒score={tb_score},EMA score={slope_score}→合计{simple_score},"
        f"{'无明显方向✓' if no_direction else '方向明确✗'})"
    )

    # ── Decision ──────────────────────────────────────────────────────────────
    # Per design doc: extreme_tr requires AI holistic judgement; program must NOT
    # output 是 to avoid premature gate=wait that kills valid trade opportunities.
    # Program always outputs 否; reason text provides the chaos_score data so AI
    # can override with 是 when ALL three signals are convincingly present.
    chaos_score = int(ema_flat) + int(high_overlap) + int(no_direction)

    answer = "否"
    if chaos_score == 3:
        warning = (
            f" ⚠️ 三项混乱指标全部触发（{chaos_score}/3），"
            "如AI综合判断确认极端混乱，可在 node_overrides 中提交 §1.3=是 覆盖。"
        )
    elif chaos_score == 2:
        warning = (
            f" ⚠️ 两项混乱指标触发（{chaos_score}/3），"
            "AI可结合整体K线结构判断是否构成极端混乱；若是，可提交 node_overrides §1.3=是。"
        )
    else:
        warning = ""

    reason = (
        f"程序默认否（极端混乱需AI综合判断，不设硬性程序门槛）。"
        f"客观混乱信号{chaos_score}/3：{c1_desc}；{c2_desc}；{c3_desc}。"
        f"市场未被程序判定为极端混乱，继续方向判断。{warning}"
    )

    return NodeFill(
        node_id="1.3",
        answer=answer,
        reason=reason,
        bar_range=bar_range,
    )
