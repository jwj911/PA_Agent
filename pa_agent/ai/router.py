"""Strategy file router — maps Stage 1 diagnosis to strategy file list.

Implements 使用说明 §11 routing table exactly.
This is a pure function: no side effects, no external state.
"""

from __future__ import annotations

import logging
from typing import Any

from pa_agent.ai.pattern_routing import merge_detected_patterns
from pa_agent.ai.prompting import prompt_ids as pid
from pa_agent.ai.prompting.prompt_ids import PromptId
from pa_agent.ai.prompting.template_manifest import TEMPLATE_CATALOG

logger = logging.getLogger(__name__)

# ── Stable Prompt ID groups ───────────────────────────────────────────────────

_BULLISH_CHANNEL_PROMPT_IDS = [
    pid.BULLISH_CHANNEL_ID,
    pid.BULLISH_CHANNEL_STRATEGY,
]
_BEARISH_CHANNEL_PROMPT_IDS = [
    pid.BEARISH_CHANNEL_ID,
    pid.BEARISH_CHANNEL_STRATEGY,
]
_CHANNEL_WIDTH_PROMPT_ID = pid.CHANNEL_WIDTH

_BULLISH_SPIKE_PROMPT_IDS = [
    pid.BULLISH_SPIKE_ID,
    pid.BULLISH_SPIKE_STRATEGY,
]
_BEARISH_SPIKE_PROMPT_IDS = [
    pid.BEARISH_SPIKE_ID,
    pid.BEARISH_SPIKE_STRATEGY,
]

_RANGE_PROMPT_IDS = [
    pid.RANGE_ID,
    pid.RANGE_STRATEGY,
]

_WEDGE_PROMPT_ID = pid.WEDGE
_REVERSAL_PROMPT_ID = pid.REVERSAL
_BREAKOUT_FAILURE_PROMPT_ID = pid.BREAKOUT_FAILURE
_H1H2_PROMPT_ID = pid.H1H2
_ALWAYS_IN_PROMPT_ID = pid.ALWAYS_IN
_BARBWIRE_PROMPT_ID = pid.BARBWIRE
_MAGNET_PROMPT_ID = pid.MAGNET
_MTR_PROMPT_ID = pid.MTR
_FINAL_FLAG_PROMPT_ID = pid.FINAL_FLAG
_TRIANGLE_PROMPT_ID = pid.TRIANGLE
_DOUBLE_TOP_BOTTOM_PROMPT_ID = pid.DOUBLE_TOP_BOTTOM

# All valid IDs accepted by the current strategy/prompt registry.
_ALL_VALID_PROMPT_IDS: frozenset[PromptId] = frozenset(
    [
        pid.PERSONA,
        pid.MARKET_DIAGNOSIS,
        pid.KLINE_SIGNAL,
        pid.STOP_TARGET_POSITION,
        pid.MEASURED_MOVE,
        pid.BULLISH_CHANNEL_ID,
        pid.BULLISH_CHANNEL_STRATEGY,
        pid.CHANNEL_WIDTH,
        pid.BEARISH_CHANNEL_ID,
        pid.BEARISH_CHANNEL_STRATEGY,
        pid.BULLISH_SPIKE_ID,
        pid.BULLISH_SPIKE_STRATEGY,
        pid.BEARISH_SPIKE_ID,
        pid.BEARISH_SPIKE_STRATEGY,
        pid.RANGE_ID,
        pid.RANGE_STRATEGY,
        pid.WEDGE,
        pid.REVERSAL,
        pid.BREAKOUT_FAILURE,
        pid.H1H2,
        pid.ALWAYS_IN,
        pid.BARBWIRE,
        pid.MAGNET,
        pid.FINAL_FLAG,
        pid.MTR,
        pid.TRIANGLE,
        pid.DOUBLE_TOP_BOTTOM,
    ]
)


def _legacy_filenames(prompt_ids: list[PromptId] | frozenset[PromptId]) -> list[str]:
    """Project IDs through the catalog without consulting physical paths."""
    return list(TEMPLATE_CATALOG.legacy_filenames(tuple(prompt_ids)))


# Compatibility constants for existing callers and tests. They are derived
# from Prompt IDs and never used as the routing source of truth.
_BULLISH_CHANNEL_FILES = _legacy_filenames(_BULLISH_CHANNEL_PROMPT_IDS)
_BEARISH_CHANNEL_FILES = _legacy_filenames(_BEARISH_CHANNEL_PROMPT_IDS)
_CHANNEL_WIDTH_FILE = TEMPLATE_CATALOG.legacy_filename(_CHANNEL_WIDTH_PROMPT_ID)
_BULLISH_SPIKE_FILES = _legacy_filenames(_BULLISH_SPIKE_PROMPT_IDS)
_BEARISH_SPIKE_FILES = _legacy_filenames(_BEARISH_SPIKE_PROMPT_IDS)
_RANGE_FILES = _legacy_filenames(_RANGE_PROMPT_IDS)
_WEDGE_FILE = TEMPLATE_CATALOG.legacy_filename(_WEDGE_PROMPT_ID)
_REVERSAL_FILE = TEMPLATE_CATALOG.legacy_filename(_REVERSAL_PROMPT_ID)
_BREAKOUT_FAILURE_FILE = TEMPLATE_CATALOG.legacy_filename(_BREAKOUT_FAILURE_PROMPT_ID)
_H1H2_FILE = TEMPLATE_CATALOG.legacy_filename(_H1H2_PROMPT_ID)
_ALWAYS_IN_FILE = TEMPLATE_CATALOG.legacy_filename(_ALWAYS_IN_PROMPT_ID)
_BARBWIRE_FILE = TEMPLATE_CATALOG.legacy_filename(_BARBWIRE_PROMPT_ID)
_MAGNET_FILE = TEMPLATE_CATALOG.legacy_filename(_MAGNET_PROMPT_ID)
_MTR_FILE = TEMPLATE_CATALOG.legacy_filename(_MTR_PROMPT_ID)
_FINAL_FLAG_FILE = TEMPLATE_CATALOG.legacy_filename(_FINAL_FLAG_PROMPT_ID)
_TRIANGLE_FILE = TEMPLATE_CATALOG.legacy_filename(_TRIANGLE_PROMPT_ID)
_DOUBLE_TOP_BOTTOM_FILE = TEMPLATE_CATALOG.legacy_filename(_DOUBLE_TOP_BOTTOM_PROMPT_ID)
_ALL_VALID_FILES: frozenset[str] = frozenset(
    TEMPLATE_CATALOG.legacy_filenames(tuple(_ALL_VALID_PROMPT_IDS))
)

_CHANNEL_STATES = frozenset(["micro_channel", "tight_channel", "normal_channel", "broad_channel"])
_RANGE_STATES = frozenset(["trading_range", "trending_tr"])
_SKIP_STATES = frozenset(["extreme_tr", "unknown"])


def route_strategy_prompt_ids(stage1_json: dict[str, Any]) -> list[PromptId]:
    """Return ordered, deduplicated strategy Prompt IDs for Stage 2.

    Args:
        stage1_json: The validated Stage 1 diagnosis JSON object.

    Returns:
        Stable Prompt IDs in the order they should appear in the Stage 2
        prompt. Always a subset of the registered prompt IDs.
        Empty list means "do not trade" (extreme_tr / unknown).
    """
    cp = stage1_json.get("cycle_position", "unknown")
    direction = stage1_json.get("direction", "neutral")
    patterns = merge_detected_patterns(stage1_json)
    spike_stage = stage1_json.get("spike_stage")
    alternative_cp = stage1_json.get("alternative_cycle_position")

    prompt_ids: list[PromptId] = []
    prompt_ids.extend(_base_prompt_ids_for_cycle(cp, direction, spike_stage=spike_stage))

    # Brooks: near-term spike is trading core even when cycle_position is channel/range
    tc = stage1_json.get("trend_context") or {}
    recent_spike = tc.get("recent_spike") if isinstance(tc, dict) else None
    if recent_spike == "bullish" and cp != "spike" and direction == "bullish":
        prompt_ids.extend(_BULLISH_SPIKE_PROMPT_IDS)
    elif recent_spike == "bearish" and cp != "spike" and direction == "bearish":
        prompt_ids.extend(_BEARISH_SPIKE_PROMPT_IDS)

    if alternative_cp and alternative_cp != cp:
        prompt_ids.extend(
            _base_prompt_ids_for_cycle(str(alternative_cp), direction, spike_stage=None)
        )

    # ── Pattern overlays ──────────────────────────────────────────────────────
    if "wedge" in patterns:
        prompt_ids.append(_WEDGE_PROMPT_ID)
    if (
        cp in _CHANNEL_STATES
        or "reversal_attempt" in patterns
        or "mtr" in patterns
        or "final_flag" in patterns
        or "h2" in patterns
        or "l2" in patterns
    ):
        prompt_ids.append(_REVERSAL_PROMPT_ID)
    if "mtr" in patterns:
        prompt_ids.append(_MTR_PROMPT_ID)
    if "final_flag" in patterns:
        prompt_ids.append(_FINAL_FLAG_PROMPT_ID)
    if cp in _CHANNEL_STATES or any(p in patterns for p in ("h1", "h2", "l1", "l2")):
        prompt_ids.append(_H1H2_PROMPT_ID)
    if any(
        p in patterns
        for p in ("breakout_failure", "failed_breakout", "breakout_test", "breakout_pullback")
    ):
        prompt_ids.append(_BREAKOUT_FAILURE_PROMPT_ID)
    if any(p in patterns for p in ("always_in", "ail", "ais", "20gb", "gap_bar")):
        prompt_ids.append(_ALWAYS_IN_PROMPT_ID)
    if cp in _RANGE_STATES or any(
        p in patterns for p in ("barbwire", "wire", "overlap", "middle_range")
    ):
        prompt_ids.append(_BARBWIRE_PROMPT_ID)
    if any(
        p in patterns
        for p in (
            "failed_signal",
            "breakout_failure",
            "failed_breakout",
            "magnet",
            "trapped_traders",
        )
    ):
        prompt_ids.append(_MAGNET_PROMPT_ID)
    if any(
        p in patterns
        for p in (
            "ascending_triangle",
            "descending_triangle",
            "symmetrical_triangle",
            "expanding_triangle",
        )
    ):
        prompt_ids.append(_TRIANGLE_PROMPT_ID)
    if "double_top_bottom" in patterns:
        prompt_ids.append(_DOUBLE_TOP_BOTTOM_PROMPT_ID)

    # ── Stable dedup (preserve first occurrence) ──────────────────────────────
    seen: set[PromptId] = set()
    deduped: list[PromptId] = []
    for prompt_id in prompt_ids:
        if prompt_id not in seen:
            seen.add(prompt_id)
            deduped.append(prompt_id)

    return deduped


def route_strategy_files(stage1_json: dict[str, Any]) -> list[str]:
    """Return legacy strategy filenames projected from stable Prompt IDs."""
    return list(TEMPLATE_CATALOG.legacy_filenames(route_strategy_prompt_ids(stage1_json)))


def _base_prompt_ids_for_cycle(
    cp: str,
    direction: str,
    *,
    spike_stage: Any = None,
) -> list[PromptId]:
    """Return base strategy Prompt IDs before pattern overlays."""
    prompt_ids: list[PromptId] = []

    # spike transitioning is already behaving like a channel; ending keeps spike
    # context but preloads channel rules for the likely spike-and-channel shift.
    if cp == "spike" and spike_stage == "transitioning":
        return _channel_prompt_ids(direction)

    # ── Channel states ────────────────────────────────────────────────────────
    if cp in _CHANNEL_STATES:
        prompt_ids.extend(_channel_prompt_ids(direction))
        # micro_channel is often spike on the signal window; load spike playbooks when active/ending.
        if cp == "micro_channel" and spike_stage in ("active", "ending"):
            if direction == "bullish":
                prompt_ids.extend(_BULLISH_SPIKE_PROMPT_IDS)
            elif direction == "bearish":
                prompt_ids.extend(_BEARISH_SPIKE_PROMPT_IDS)

    # ── Spike state ───────────────────────────────────────────────────────────
    elif cp == "spike":
        if direction == "bullish":
            prompt_ids.extend(_BULLISH_SPIKE_PROMPT_IDS)
        elif direction == "bearish":
            prompt_ids.extend(_BEARISH_SPIKE_PROMPT_IDS)
        else:
            logger.info("Spike with neutral direction — no spike strategy files loaded")
        if spike_stage == "ending":
            prompt_ids.extend(_channel_prompt_ids(direction))

    # ── Range states ──────────────────────────────────────────────────────────
    elif cp in _RANGE_STATES:
        prompt_ids.extend(_RANGE_PROMPT_IDS)

    # ── Skip states (extreme_tr / unknown) ────────────────────────────────────
    elif cp in _SKIP_STATES:
        pass  # no strategy files — do not trade

    else:
        logger.warning(
            "Unknown cycle_position %r — no strategy files loaded. "
            "If this is a pattern name (e.g. 'descending_triangle'), it belongs in "
            "detected_patterns, not cycle_position. "
            "Run normalize_stage1() before routing to auto-correct.",
            cp,
        )

    return prompt_ids


def _channel_prompt_ids(direction: str) -> list[PromptId]:
    prompt_ids: list[PromptId] = []
    if direction == "bullish":
        prompt_ids.extend(_BULLISH_CHANNEL_PROMPT_IDS)
    elif direction == "bearish":
        prompt_ids.extend(_BEARISH_CHANNEL_PROMPT_IDS)
    else:
        # Neutral in a channel: skip directional channel files, but preload
        # range strategy for boundary planned-limit setups (§9.0 path).
        logger.info(
            "Channel-like state with neutral direction — "
            "no directional channel files; loading range strategy for boundary setups"
        )
        prompt_ids.extend(_RANGE_PROMPT_IDS)
    prompt_ids.append(_CHANNEL_WIDTH_PROMPT_ID)
    return prompt_ids


def _base_files_for_cycle(
    cp: str,
    direction: str,
    *,
    spike_stage: Any = None,
) -> list[str]:
    """Compatibility wrapper returning legacy filenames."""
    return list(
        TEMPLATE_CATALOG.legacy_filenames(
            _base_prompt_ids_for_cycle(cp, direction, spike_stage=spike_stage)
        )
    )


def _channel_files(direction: str) -> list[str]:
    """Compatibility wrapper returning legacy filenames."""
    return list(TEMPLATE_CATALOG.legacy_filenames(_channel_prompt_ids(direction)))
