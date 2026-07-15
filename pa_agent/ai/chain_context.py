"""Cross-stage carryover context builders for the prompt assembler.

This is a PyQt6-free leaf module extracted from ``prompt_assembler.py`` as the
fourth slice of the report §5.2 M1 split.  It groups four deterministic helpers
that serialize *prior-stage* results into fragments consumed by *downstream*
prompts:

- ``normalize_prev_stage1_assistant_for_incremental`` — reuse a previous run's
  validated Stage 1 diagnosis JSON (not its prose/markdown reply) as the
  assistant turn in incremental mode.
- ``render_previous_prediction`` — render the previous round's next-bar
  prediction as a compact reference block (R5.2).
- ``normalize_stage1_assistant_for_chain`` — compact the just-validated Stage 1
  JSON for the assistant turn in prefix-chain Stage 2 mode.
- ``compact_stage1_for_stage2`` — project the Stage 1 diagnosis onto the subset
  of fields Stage 2 actually needs (reduces prompt noise / token count).

These were formerly ``PromptAssembler`` ``@staticmethod`` methods
(``_normalize_prev_stage1_assistant_for_incremental`` /
``_render_previous_prediction`` / ``_normalize_stage1_assistant_for_chain`` /
``_compact_stage1_for_stage2``), each with only internal ``self._x(...)`` call
sites.  After migrating here (drop ``@staticmethod``, drop the leading
underscore) ``prompt_assembler.py`` re-binds them in the class body via
``_x = staticmethod(y)`` so the original call sites stay byte-for-byte
compatible.

Dependencies are near-stdlib: only ``json``/``logging``/``typing`` plus a
``TYPE_CHECKING``-only ``AnalysisRecord`` annotation import; the sole project
touch point (``format_model_json_for_context``) is a **call-time import** to
avoid pulling the ``market_features``→PyQt6 chain and to break any cycle.  Block
headers, Chinese reference strings, the direction/probability formatting and the
Stage 2 field whitelist must stay byte-for-byte identical (the model aligns to
these fragment shapes / the prefix KV cache is sensitive to the compacted JSON).
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pa_agent.records.schema import AnalysisRecord

logger = logging.getLogger(__name__)


def normalize_prev_stage1_assistant_for_incremental(
    previous_record: AnalysisRecord,
    raw_content: str,
) -> str:
    """Use validated diagnosis JSON in incremental context, not prose/markdown replies."""
    from pa_agent.ai.json_validator import format_model_json_for_context

    diag = getattr(previous_record, "stage1_diagnosis", None) or {}
    if isinstance(diag, dict) and diag:
        return json.dumps(diag, ensure_ascii=False, indent=2)

    formatted = format_model_json_for_context(raw_content)
    if formatted:
        return formatted

    logger.warning(
        "incremental stage1: could not normalize previous assistant to JSON; "
        "using raw stage1_response content (%d chars)",
        len(raw_content or ""),
    )
    return raw_content


def render_previous_prediction(previous_record: Any) -> str:
    """Render previous-bar prediction summary for incremental context (R5.2)."""
    if previous_record is None:
        return ""
    # previous_record may be AnalysisRecord or dict-like
    s2 = getattr(previous_record, "stage2_decision", None)
    if s2 is None and isinstance(previous_record, dict):
        s2 = previous_record.get("stage2_decision")
    if not isinstance(s2, dict):
        return ""
    pred = s2.get("next_bar_prediction")
    if not isinstance(pred, dict):
        return ""

    unpredictable = bool(pred.get("unpredictable", False))
    if unpredictable:
        return (
            "## 上一轮下一根K线预测\n\n"
            "上一轮标记为不可预测；本轮请独立判断。\n"
        )

    direction = pred.get("direction") or "—"
    probs = pred.get("probabilities") or {}
    bull = probs.get("bullish", "?")
    bear = probs.get("bearish", "?")
    neut = probs.get("neutral", "?")
    dir_zh = {"bullish": "阳线", "bearish": "阴线", "neutral": "中性"}.get(direction, direction)
    return (
        "## 上一轮下一根K线预测\n\n"
        f"方向：{dir_zh}（阳 {bull}% / 阴 {bear}% / 中性 {neut}%）。"
        "本轮请基于最新数据独立重新预测，不必延续上轮结论。\n"
    )


def normalize_stage1_assistant_for_chain(
    stage1_json: dict,
    stage1_reply_content: str,
) -> str:
    """Compact validated Stage 1 JSON for assistant turn in prefix-chain mode."""
    from pa_agent.ai.json_validator import format_model_json_for_context

    if isinstance(stage1_json, dict) and stage1_json:
        return json.dumps(stage1_json, ensure_ascii=False, indent=2)
    formatted = format_model_json_for_context(stage1_reply_content)
    if formatted:
        return formatted
    return stage1_reply_content or ""


def compact_stage1_for_stage2(stage1_json: dict) -> dict:
    """Subset of Stage 1 fields needed for Stage 2 (reduces prompt noise)."""
    keys = (
        "cycle_position",
        "alternative_cycle_position",
        "direction",
        "diagnosis_confidence",
        "spike_stage",
        "market_phase",
        "transition_risk",
        "detected_patterns",
        "key_signals",
        "htf_context",
        "trend_context",
        "entry_setup",
        "support_levels",
        "resistance_levels",
        "strategy_files_needed",
        "risk_warning",
        "bar_analysis",
        "bar_by_bar_summary",
        "gate_trace",
        "gate_result",
    )
    return {k: stage1_json[k] for k in keys if k in stage1_json}
