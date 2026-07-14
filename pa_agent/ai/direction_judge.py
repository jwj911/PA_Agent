"""Direction section judge (§2.3) for the decision node engine.

Section-judge cluster split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). :func:`judge_direction` runs a five-signal vote (EMA slope, weighted
closing centre of gravity, swing structure, trend-bar dominance, K-line overlap)
with a medium-window confirmation filter to classify the market direction and
fill the §2.3 node.

Like ``signal_bar_judges`` this is a *self-contained* judge: it depends only on
leaf modules — ``NodeFill`` (from :mod:`pa_agent.ai.trace_nodes`), the geometry
primitives ``_count_trend_bars`` / ``_find_swings`` / ``_mean_overlap_ratio``
(from :mod:`pa_agent.ai.bar_geometry`) and the direction thresholds (from
:mod:`pa_agent.ai.decision_thresholds`) — so pulling it here creates no import
cycle. ``decision_nodes`` re-exports ``judge_direction``, so existing
``from pa_agent.ai.decision_nodes import judge_direction`` sites keep working
byte-for-byte. Behaviour (direction, answers, Chinese reason strings, score
arithmetic, bar_range) must stay identical to the original.
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
    DIRECTION_BEAR_THRESHOLD,
    DIRECTION_BULL_THRESHOLD,
    DIRECTION_STRONG_SHORT_SCORE,
    DIRECTION_WINDOW,
    DIRECTION_WINDOW_MED,
    EMA_SLOPE_LOOKBACK,
    OVERLAP_HIGH_THRESHOLD,
    OVERLAP_LOW_THRESHOLD,
    TREND_BAR_DOMINANCE_RATIO,
)
from pa_agent.ai.trace_nodes import NodeFill


def judge_direction(frame: Any) -> tuple[str, NodeFill]:
    """Five-signal vote to determine direction and fill §2.3 node.

    Signals (each contributes -1, 0, or +1 to the score):
      S1: EMA slope (10-bar lookback, ATR dead-zone filter)
      S2: Closing center of gravity – short window (20 bars, near half vs far half)
      S3: Swing structure HH+HL vs LL+LH (2-bar pivot detection in 20-bar window)
      S4: Trend-bar dominance (bull vs bear trend-bar count ratio in 20 bars)
      S5: K-line overlap ratio (low overlap → trending, high → ranging/no-dir)

    Medium-window confirmation (50-bar closing gravity) reduces |score| by 1
    when it contradicts the short-window result.

    Thresholds raised to ±3 (from ±2) so the signal survives wide channels
    and trading ranges better — consistent with §2.3 of 二元决策.txt.

    Returns (direction, NodeFill) where direction ∈ {bullish, bearish, neutral}.
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

    W = min(DIRECTION_WINDOW, n)
    W_med = min(DIRECTION_WINDOW_MED, n)

    # Get close prices (bars[0] is newest seq=1)
    close_prices = []
    for bar in list(bars)[:W]:
        try:
            close_prices.append(float(bar.close))
        except (TypeError, ValueError, AttributeError):
            close_prices.append(float("nan"))

    # ── Signal 1: EMA slope ───────────────────────────────────────────────────
    s1 = 0
    s1_desc = "EMA斜率:0"
    try:
        if ema20 and len(ema20) >= 1 and not math.isnan(float(ema20[0])):
            k = min(EMA_SLOPE_LOOKBACK, n - 1)
            if k >= 1 and len(ema20) > k and not math.isnan(float(ema20[k])):
                d = float(ema20[0]) - float(ema20[k])
                thr = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr = 0.05 * float(atr14[0])
                if d > thr:
                    s1 = 1
                    s1_desc = f"EMA斜率:+1(d={d:.4f}>thr={thr:.4f})"
                elif d < -thr:
                    s1 = -1
                    s1_desc = f"EMA斜率:-1(d={d:.4f}<-thr={-thr:.4f})"
                else:
                    s1_desc = f"EMA斜率:0(d={d:.4f},死区±{thr:.4f})"
    except (TypeError, ValueError):
        pass

    # ── Signal 2: Weighted closing center of gravity (short window) ─────────────
    # 线性递减权重：bars[0]=最新(权重W)，bars[W-1]=最老(权重1)。
    # 加权重心 = Σ(weight_i × close_i) / Σweight_i，近端与远端各占半窗口。
    # 这样最近1~(W/2)根K线对结论的影响远大于较老的K线。
    s2 = 0
    s2_desc = "收盘重心:0"
    try:
        h = W // 2
        if h >= 1 and len(close_prices) >= 2 * h:
            # 权重：index 0 最新 → 权重 W，index W-1 最老 → 权重 1
            def _weighted_avg(vals: list[float], start_idx: int) -> float:
                total_w = 0.0
                total_wv = 0.0
                for local_i, v in enumerate(vals):
                    if math.isnan(v):
                        continue
                    w = W - (start_idx + local_i)  # newer bars get higher weight
                    total_w += w
                    total_wv += w * v
                return total_wv / total_w if total_w > 0 else float("nan")

            near_vals = close_prices[:h]
            far_vals = close_prices[h:2 * h]
            near = _weighted_avg(near_vals, 0)
            far = _weighted_avg(far_vals, h)
            if not math.isnan(near) and not math.isnan(far):
                diff = near - far
                thr2 = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr2 = 0.1 * float(atr14[0])
                if diff > thr2:
                    s2 = 1
                    s2_desc = f"收盘重心(加权):+1(diff={diff:.4f}>thr={thr2:.4f})"
                elif diff < -thr2:
                    s2 = -1
                    s2_desc = f"收盘重心(加权):-1(diff={diff:.4f}<-thr={-thr2:.4f})"
                else:
                    s2_desc = f"收盘重心(加权):0(diff={diff:.4f},死区±{thr2:.4f})"
    except (TypeError, ValueError):
        pass

    # ── Signal 3: Swing structure HH/HL vs LL/LH ─────────────────────────────
    s3 = 0
    s3_desc = "波段结构:0"
    try:
        swing_highs, swing_lows = _find_swings(bars, W)
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            hh = swing_highs[0] > swing_highs[1]
            hl = swing_lows[0] > swing_lows[1]
            ll = swing_lows[0] < swing_lows[1]
            lh = swing_highs[0] < swing_highs[1]
            if hh and hl:
                s3 = 1
                s3_desc = "波段结构:+1(HH+HL)"
            elif ll and lh:
                s3 = -1
                s3_desc = "波段结构:-1(LL+LH)"
            else:
                s3_desc = f"波段结构:0(HH={hh},HL={hl},LL={ll},LH={lh})"
        else:
            s3_desc = (
                f"波段结构:0(枢轴不足,highs={len(swing_highs)},lows={len(swing_lows)})"
            )
    except (TypeError, ValueError, IndexError):
        pass

    # ── Signal 4: Trend-bar dominance ─────────────────────────────────────────
    # §2.3 "多头趋势棒占优" / "空头趋势棒占优"
    s4 = 0
    s4_desc = "趋势棒占比:0"
    try:
        bull_tb, bear_tb = _count_trend_bars(bars, W)
        if bull_tb + bear_tb > 0:
            if bull_tb > 0 and bear_tb == 0:
                s4 = 1
                s4_desc = f"趋势棒占比:+1(多头趋势棒{bull_tb}根,空头0根)"
            elif bear_tb > 0 and bull_tb == 0:
                s4 = -1
                s4_desc = f"趋势棒占比:-1(空头趋势棒{bear_tb}根,多头0根)"
            elif bull_tb >= bear_tb * TREND_BAR_DOMINANCE_RATIO:
                s4 = 1
                s4_desc = (
                    f"趋势棒占比:+1(多{bull_tb}/空{bear_tb}"
                    f"≥{TREND_BAR_DOMINANCE_RATIO:.1f}×)"
                )
            elif bear_tb >= bull_tb * TREND_BAR_DOMINANCE_RATIO:
                s4 = -1
                s4_desc = (
                    f"趋势棒占比:-1(空{bear_tb}/多{bull_tb}"
                    f"≥{TREND_BAR_DOMINANCE_RATIO:.1f}×)"
                )
            else:
                s4_desc = f"趋势棒占比:0(多{bull_tb}/空{bear_tb},无明显优势)"
        else:
            s4_desc = "趋势棒占比:0(窗口内无趋势棒)"
    except (TypeError, ValueError):
        pass

    # ── Signal 5: K-line overlap ratio ────────────────────────────────────────
    # §2.5 "K线重叠少→趋势强" / "K线重叠多→区间/无方向"
    # Low overlap earns ±1 aligned with EMA slope direction;
    # high overlap neutralises.
    s5 = 0
    s5_desc = "K线重叠:0"
    try:
        mean_overlap = _mean_overlap_ratio(bars, W)
        if mean_overlap is not None:
            if mean_overlap < OVERLAP_LOW_THRESHOLD:
                if s1 > 0:
                    s5 = 1
                    s5_desc = (
                        f"K线重叠:+1(均值重叠{mean_overlap:.3f}<{OVERLAP_LOW_THRESHOLD},"
                        "低重叠强化多头方向)"
                    )
                elif s1 < 0:
                    s5 = -1
                    s5_desc = (
                        f"K线重叠:-1(均值重叠{mean_overlap:.3f}<{OVERLAP_LOW_THRESHOLD},"
                        "低重叠强化空头方向)"
                    )
                else:
                    s5_desc = (
                        f"K线重叠:0(均值重叠{mean_overlap:.3f}<{OVERLAP_LOW_THRESHOLD},"
                        "EMA斜率中性,重叠信号不明)"
                    )
            elif mean_overlap > OVERLAP_HIGH_THRESHOLD:
                s5_desc = (
                    f"K线重叠:0(均值重叠{mean_overlap:.3f}>{OVERLAP_HIGH_THRESHOLD},"
                    "高重叠→区间,无方向贡献)"
                )
            else:
                s5_desc = f"K线重叠:0(均值重叠{mean_overlap:.3f},中等重叠)"
    except (TypeError, ValueError):
        pass

    score = s1 + s2 + s3 + s4 + s5

    # ── Medium-window confirmation filter ────────────────────────────────────
    # W_med-bar closing gravity (now 20 bars) contradicts short-window → |score| reduced by 1.
    # Also uses linear-decay weighting so recent bars dominate.
    med_confirm = 0
    med_confirm_desc = "中窗口重心:0"
    try:
        close_prices_med = []
        for bar in list(bars)[:W_med]:
            try:
                close_prices_med.append(float(bar.close))
            except (TypeError, ValueError, AttributeError):
                close_prices_med.append(float("nan"))
        hm = W_med // 2
        if hm >= 1 and len(close_prices_med) >= 2 * hm:
            def _weighted_avg_med(vals: list[float], start_idx: int) -> float:
                total_w = 0.0
                total_wv = 0.0
                for local_i, v in enumerate(vals):
                    if math.isnan(v):
                        continue
                    w = W_med - (start_idx + local_i)
                    total_w += w
                    total_wv += w * v
                return total_wv / total_w if total_w > 0 else float("nan")

            near_m_vals = close_prices_med[:hm]
            far_m_vals = close_prices_med[hm:2 * hm]
            near_m = _weighted_avg_med(near_m_vals, 0)
            far_m = _weighted_avg_med(far_m_vals, hm)
            if not math.isnan(near_m) and not math.isnan(far_m):
                diff_m = near_m - far_m
                thr_m = 0.0
                if atr14 and len(atr14) >= 1 and not math.isnan(float(atr14[0])):
                    thr_m = 0.1 * float(atr14[0])
                if diff_m > thr_m:
                    med_confirm = 1
                    med_confirm_desc = (
                        f"中窗口重心(加权):+1(diff={diff_m:.4f}>thr={thr_m:.4f},W={W_med})"
                    )
                elif diff_m < -thr_m:
                    med_confirm = -1
                    med_confirm_desc = (
                        f"中窗口重心(加权):-1(diff={diff_m:.4f}<-thr={-thr_m:.4f},W={W_med})"
                    )
                else:
                    med_confirm_desc = f"中窗口重心(加权):0(diff={diff_m:.4f},W={W_med})"
    except (TypeError, ValueError):
        pass

    if med_confirm != 0 and score != 0 and med_confirm != (1 if score > 0 else -1):
        if abs(score) >= DIRECTION_STRONG_SHORT_SCORE:
            med_confirm_desc += (
                f"（背景窗口与短窗口冲突，但|score|={abs(score)}"
                f"≥{DIRECTION_STRONG_SHORT_SCORE}，新趋势优先，不扣分）"
            )
        else:
            score_before = score
            score = score - (1 if score > 0 else -1)
            med_confirm_desc += f"（与短窗口冲突，score {score_before}→{score}）"
    else:
        if med_confirm != 0:
            med_confirm_desc += "（与短窗口一致）"

    if score >= DIRECTION_BULL_THRESHOLD:
        direction = "bullish"
        answer = "是"
        branch = "bullish"
    elif score <= DIRECTION_BEAR_THRESHOLD:
        direction = "bearish"
        answer = "是"
        branch = "bearish"
    else:
        direction = "neutral"
        answer = "中性"
        branch = "neutral"

    bar_range = f"K{W}-K1"

    reason = (
        f"五信号投票（阈值±{DIRECTION_BULL_THRESHOLD}）："
        f"{s1_desc}；{s2_desc}；{s3_desc}；{s4_desc}；{s5_desc}。"
        f"{med_confirm_desc}。"
        f"综合score={score}（≥+{DIRECTION_BULL_THRESHOLD}→多头，"
        f"≤{DIRECTION_BEAR_THRESHOLD}→空头，否则中性）→{direction}。"
    )

    fill = NodeFill(
        node_id="2.3",
        answer=answer,
        reason=reason,
        bar_range=bar_range,
        branch=branch,
    )

    return direction, fill
