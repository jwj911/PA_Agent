"""K-line table renderers for Stage 1/Stage 2 prompts.

Extracted from ``prompt_assembler.py`` (report §5.2 M1, the ``KlineTableRenderer``
产出). These are the pure text-table renderers (newest bar first) that ground the
model in the exact OHLC / EMA20 / ATR14 values and single-bar geometry features it
must analyze. They depend only on PyQt6-free leaf modules
(``kline_features`` / ``data.base`` / ``data.datetime_ts``), so this module stays
importable without the GUI stack. ``PromptAssembler`` re-binds
``render_kline_table`` / ``render_kline_feature_table`` as
``_render_kline_table`` / ``_render_kline_feature_table`` staticmethods so existing
``PromptAssembler._render_kline_table(...)`` call sites (``main_window`` / 测试)
keep working byte-for-byte. Table layout / column widths / Chinese headers / the
indicator note must stay byte-for-byte identical (the model is prompted against
this exact table shape).
"""
from __future__ import annotations

import math

from pa_agent.ai.kline_features import bar_candle_direction_label, compute_kline_geometry_features
from pa_agent.data.base import KlineFrame
from pa_agent.data.datetime_ts import format_epoch_for_display

_KLINE_INDICATOR_NOTE = (
    "说明：下表仅含最近 N 根已收盘 K 线；几何特征亦基于此 N 根。"
    "EMA20/ATR14 由程序在更老缓冲 K 线上预热后重算，与外盘图表「全历史延续」"
    "指标可能略有差异，勿逐点对比。"
)


def _fmt_feature(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def render_kline_table(frame: KlineFrame, limit: int | None = None) -> str:
    """Render the K-line data as a text table (newest bar first)."""
    lines = [
        "序号 | 时间                | 开盘价    | 最高价    | 最低价    | 收盘价    | 阳阴 | 成交量    | EMA20     | ATR14",
        "-----+--------------------+----------+----------+----------+----------+------+----------+-----------+----------",
    ]
    bars = frame.bars[:limit] if limit is not None else frame.bars
    for i, bar in enumerate(bars):
        ema = frame.indicators.ema20[i]
        atr = frame.indicators.atr14[i]
        ema_str = f"{ema:.4f}" if not math.isnan(ema) else "N/A"
        atr_str = f"{atr:.4f}" if not math.isnan(atr) else "N/A"
        yang_yin = bar_candle_direction_label(bar)
        dt = format_epoch_for_display(bar.ts_open, short=True)
        lines.append(
            f"{bar.seq:<4} | {dt:<19} | {bar.open:<9.4f} | {bar.high:<9.4f} | "
            f"{bar.low:<9.4f} | {bar.close:<9.4f} | {yang_yin:<4} | {bar.volume:<9.0f} | "
            f"{ema_str:<10} | {atr_str}"
        )
    lines.append(_KLINE_INDICATOR_NOTE)
    return "\n".join(lines)


def render_kline_feature_table(frame: KlineFrame, limit: int | None = None) -> str:
    """Render方案 A single-bar geometry features for prompt grounding."""
    shown = limit if limit is not None else len(frame.bars)
    lines = [
        f"（几何特征：最近 {shown} 根已收盘 K 线；「类型」= 单字段 bar_type，优先级 inside/outside > doji/trend/flat/other；多棒形态已用完整窗口计算）",
        "序号 | 类型          | 实体比 | 上影比 | 下影比 | 收盘位置 | Range/ATR | EMA关系 | 与前棒重叠 | ii/iii | ioi | 微双 | 缺口 | EMA缺口数 | 近5突破 | 后续",
        "-----+---------------+--------+--------+--------+----------+-----------+---------+------------+--------+-----+------+-------+-----------+---------+------",
    ]
    for feat in compute_kline_geometry_features(frame, limit=limit):
        lines.append(
            f"{feat.seq:<4} | {feat.bar_type:<13} | "
            f"{_fmt_feature(feat.body_ratio):<6} | "
            f"{_fmt_feature(feat.upper_wick_ratio):<6} | "
            f"{_fmt_feature(feat.lower_wick_ratio):<6} | "
            f"{_fmt_feature(feat.close_position):<8} | "
            f"{_fmt_feature(feat.range_atr_ratio):<9} | "
            f"{feat.ema_relation:<7} | "
            f"{_fmt_feature(feat.overlap_prev_ratio):<10} | "
            f"{feat.inside_sequence:<6} | "
            f"{str(feat.ioi_pattern):<3} | "
            f"{feat.micro_double:<4} | "
            f"{feat.gap_bar:<5} | "
            f"{feat.ema_gap_count:<9} | "
            f"{feat.breakout_prev:<7} | "
            f"{feat.follow_through_1_2}"
        )
    lines.append(_KLINE_INDICATOR_NOTE)
    return "\n".join(lines)
