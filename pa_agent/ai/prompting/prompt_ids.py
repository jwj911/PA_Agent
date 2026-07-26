"""Stable logical identities for the runtime prompt corpus."""

from __future__ import annotations

from typing import NewType

PromptId = NewType("PromptId", str)

# Shared system prompts.
PERSONA = PromptId("pa.persona")
BINARY_DECISION = PromptId("pa.binary_decision")

# Stage 1 diagnosis prompts.
MARKET_DIAGNOSIS = PromptId("pa.market_diagnosis")
KLINE_SIGNAL = PromptId("pa.kline_signal")

# Stage 2 base prompts.
BAR_CHECKLIST = PromptId("pa.bar_checklist")
STOP_TARGET_POSITION = PromptId("pa.stop_target_position")
MEASURED_MOVE = PromptId("pa.measured_move")

# Directional channel prompts.
BULLISH_CHANNEL_ID = PromptId("pa.channel.bullish.identification")
BULLISH_CHANNEL_STRATEGY = PromptId("pa.channel.bullish.strategy")
BEARISH_CHANNEL_ID = PromptId("pa.channel.bearish.identification")
BEARISH_CHANNEL_STRATEGY = PromptId("pa.channel.bearish.strategy")

# Directional spike prompts.
BULLISH_SPIKE_ID = PromptId("pa.spike.bullish.identification")
BULLISH_SPIKE_STRATEGY = PromptId("pa.spike.bullish.strategy")
BEARISH_SPIKE_ID = PromptId("pa.spike.bearish.identification")
BEARISH_SPIKE_STRATEGY = PromptId("pa.spike.bearish.strategy")

# Range prompts.
RANGE_ID = PromptId("pa.range.identification")
RANGE_STRATEGY = PromptId("pa.range.strategy")

# Pattern and context prompts.
CHANNEL_WIDTH = PromptId("pa.channel.width")
WEDGE = PromptId("pa.pattern.wedge")
REVERSAL = PromptId("pa.pattern.second_entry")
BREAKOUT_FAILURE = PromptId("pa.pattern.breakout_failure")
H1H2 = PromptId("pa.pattern.h1_h2_l1_l2")
ALWAYS_IN = PromptId("pa.context.always_in_20gb")
BARBWIRE = PromptId("pa.context.barbwire")
MAGNET = PromptId("pa.context.failed_signal_magnet")
FINAL_FLAG = PromptId("pa.pattern.final_flag")
MTR = PromptId("pa.pattern.mtr")
TRIANGLE = PromptId("pa.pattern.triangle")
DOUBLE_TOP_BOTTOM = PromptId("pa.pattern.double_top_bottom")

ALL_PROMPT_IDS: tuple[PromptId, ...] = (
    PERSONA,
    BINARY_DECISION,
    MARKET_DIAGNOSIS,
    KLINE_SIGNAL,
    BAR_CHECKLIST,
    STOP_TARGET_POSITION,
    MEASURED_MOVE,
    BULLISH_CHANNEL_ID,
    BULLISH_CHANNEL_STRATEGY,
    BEARISH_CHANNEL_ID,
    BEARISH_CHANNEL_STRATEGY,
    BULLISH_SPIKE_ID,
    BULLISH_SPIKE_STRATEGY,
    BEARISH_SPIKE_ID,
    BEARISH_SPIKE_STRATEGY,
    RANGE_ID,
    RANGE_STRATEGY,
    CHANNEL_WIDTH,
    WEDGE,
    REVERSAL,
    BREAKOUT_FAILURE,
    H1H2,
    ALWAYS_IN,
    BARBWIRE,
    MAGNET,
    FINAL_FLAG,
    MTR,
    TRIANGLE,
    DOUBLE_TOP_BOTTOM,
)

__all__ = [
    "ALL_PROMPT_IDS",
    "ALWAYS_IN",
    "BARBWIRE",
    "BAR_CHECKLIST",
    "BEARISH_CHANNEL_ID",
    "BEARISH_CHANNEL_STRATEGY",
    "BEARISH_SPIKE_ID",
    "BEARISH_SPIKE_STRATEGY",
    "BINARY_DECISION",
    "BREAKOUT_FAILURE",
    "BULLISH_CHANNEL_ID",
    "BULLISH_CHANNEL_STRATEGY",
    "BULLISH_SPIKE_ID",
    "BULLISH_SPIKE_STRATEGY",
    "CHANNEL_WIDTH",
    "DOUBLE_TOP_BOTTOM",
    "FINAL_FLAG",
    "H1H2",
    "KLINE_SIGNAL",
    "MAGNET",
    "MARKET_DIAGNOSIS",
    "MEASURED_MOVE",
    "MTR",
    "PERSONA",
    "RANGE_ID",
    "RANGE_STRATEGY",
    "REVERSAL",
    "STOP_TARGET_POSITION",
    "TRIANGLE",
    "WEDGE",
    "PromptId",
]
