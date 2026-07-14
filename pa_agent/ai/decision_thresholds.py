"""Tuning constants and node-permission sets for the decision node engine.

Pure data module (no imports, no side effects) split out of
:mod:`pa_agent.ai.decision_nodes` (report §5.2 M3). Holds every module-level
threshold used by the deterministic §1.1/§2.3/§2.4/§2.5/§9 judges plus the
override permission sets. Both ``decision_nodes`` (which re-exports these names
so existing ``from pa_agent.ai.decision_nodes import ...`` sites keep working
byte-for-byte) and ``trend_context`` import from here.

Values must stay byte-identical to the originals: they encode tuned Brooks
price-action thresholds and gate/override policy referenced across the engine.
"""
from __future__ import annotations

# ── Threshold constants ────────────────────────────────────────────────────────

BAR_COUNT_THRESHOLD: int = 20  # §1.1 data sufficiency threshold

DIRECTION_WINDOW: int = 8  # §2.3 direction voting window (short) — 缩小到8根，重点捕捉近期结构突变
DIRECTION_WINDOW_MED: int = 20  # §2.3 medium window — 仅作背景参考，强短窗口时不扣分
DIRECTION_STRONG_SHORT_SCORE: int = 4  # |score|≥此值时忽略中窗口冲突（新趋势优先于旧背景）

ALWAYS_IN_NEAR_WINDOW: int = 8  # §2.4 近端主判（Brooks：惯性=刚刚在做的事）
ALWAYS_IN_WINDOW: int = 20  # §2.4 背景参考窗口（不否决近端结论）
ALWAYS_IN_NEAR_SAME_SIDE_RATIO: float = 0.65  # 近端加权同侧占比（8根窗口略低于20根阈值）

ALWAYS_IN_SAME_SIDE_RATIO: float = 0.7  # §2.4 same-side ratio threshold
ALWAYS_IN_PULLBACK_ATR_RATIO: float = 1.5  # §2.4 max pullback depth (×ATR) for AIL/AIS

SIGNAL_BAR_LONG_ATR_RATIO: float = 2.0  # §9.3 overlong threshold

EMA_SLOPE_LOOKBACK: int = 10  # EMA slope lookback bars

# ── §2.3 direction vote thresholds ────────────────────────────────────────────
# Score from 5 signals (EMA slope, close gravity, HH/HL structure,
# trend-bar dominance, overlap ratio).  Medium-window confirmation can
# reduce the score by 1 when it contradicts the short-window result.
# Thresholds: ≥+3 → bullish, ≤-3 → bearish, otherwise neutral.
DIRECTION_BULL_THRESHOLD: int = 3
DIRECTION_BEAR_THRESHOLD: int = -3

# Trend-bar dominance: bull_trend_bars / bear_trend_bars ratio to earn ±1
TREND_BAR_DOMINANCE_RATIO: float = 1.5
# Overlap: mean overlap_prev_ratio below this → low overlap → trend signal
OVERLAP_LOW_THRESHOLD: float = 0.45
# Overlap: mean overlap_prev_ratio above this → high overlap → range / no trend
OVERLAP_HIGH_THRESHOLD: float = 0.65


# ── Override permission sets ──────────────────────────────────────────────────

LOCKED_NODES: frozenset[str] = frozenset({"1.1", "9.1"})

OVERRIDABLE_NODES: frozenset[str] = frozenset(
    {
        "1.3", "2.3", "2.4", "2.5", "9.2", "9.3", "11.1", "11.2", "11.3", "11.4",
    }
)

# Nodes where the AI is the primary judge; program does not replace AI when AI wrote the node.
# The program node is used as-is only when the AI omitted the node entirely.
AI_PRIMARY_NODES: frozenset[str] = frozenset({"1.3", "2.5"})
# AI-primary nodes that receive appended program metrics in reason (currently none).
AI_PRIMARY_SUPPLEMENT_NODES: frozenset[str] = frozenset()

# §1.3 extreme chaos thresholds
CHAOS_OVERLAP_THRESHOLD: float = 0.70  # mean overlap_prev_ratio above this → chaotic
CHAOS_EMA_FLAT_ATR_RATIO: float = 0.05  # EMA slope dead-zone (×ATR) for "flat" check
CHAOS_DIRECTION_SCORE_MAX: int = 1  # |direction score| ≤ this → no clear direction

# §2.5 momentum strength thresholds
MOMENTUM_OVERLAP_WEAK: float = 0.50  # above → weak momentum (lots of overlap)
# 0.50 is conservative: healthy trends show <0.3-0.4 overlap
MOMENTUM_TREND_RATIO_STRONG: float = 1.5  # bull/bear trend bar ratio ≥ this → strong side
MOMENTUM_PULLBACK_DEEP_ATR: float = 3.0  # pullback > this×ATR → deep (weak momentum)
# M1 absolute floor: directional trend bars must be ≥ this fraction of ALL bars
# in the near-term window.  Prevents "2 bear vs 1 bull = dominant" from triggering
# when 5 out of 8 bars are doji/inside/other (market is hesitating, not trending).
# Set to 0.50: if fewer than half the bars are trend bars, the market is hesitating.
MOMENTUM_TREND_BAR_MIN_RATIO: float = 0.50  # ≥50% of all bars must be trend bars

SAFETY_GATE_NODES: frozenset[str] = frozenset({"1.1", "10.3", "14"})
