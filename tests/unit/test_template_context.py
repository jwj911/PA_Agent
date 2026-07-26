"""Tests for the explicit prompt template context boundary."""

from __future__ import annotations

import json

import pytest

from pa_agent.ai.prompting import PromptId, TemplateContext, prompt_ids
from tests.unit.test_prompt_assembler import _make_frame


def test_stage2_context_is_json_serializable_and_does_not_keep_runtime_objects() -> None:
    frame = _make_frame()
    previous_record = {"meta": {"symbol": "XAUUSD"}, "usage_total": {"total": 3}}

    context = TemplateContext.from_stage2_inputs(
        frame,
        {"direction": "bullish", "gate_result": "proceed"},
        ["上涨通道分析识别.txt"],
        [{"outcome": "success"}],
        decision_stance="balanced",
        previous_record=previous_record,
        feature_flags={"prefix_chain": True},
        template_versions={"上涨通道分析识别.txt": "v1"},
    )

    payload = context.to_dict()
    json.dumps(payload, ensure_ascii=False, sort_keys=True)

    assert payload["stage"] == "stage2"
    assert payload["symbol"] == "XAUUSD"
    assert payload["bar_count"] == len(frame.bars)
    assert payload["strategy_prompt_ids"] == ["pa.channel.bullish.identification"]
    assert payload["strategy_files"] == ["上涨通道分析识别.txt"]
    assert payload["feature_flags"] == {"prefix_chain": True}
    assert payload["template_versions"] == {"pa.channel.bullish.identification": "v1"}
    assert not hasattr(context, "settings")
    assert not hasattr(context, "client")


def test_stage2_context_from_ids_projects_legacy_files_and_rejects_mismatch() -> None:
    frame = _make_frame()
    context = TemplateContext.from_stage2_prompt_ids(
        frame,
        {"direction": "bullish"},
        [prompt_ids.BULLISH_CHANNEL_ID],
        [],
        decision_stance="balanced",
    )

    assert context.strategy_prompt_ids == (prompt_ids.BULLISH_CHANNEL_ID,)
    assert context.strategy_files == ("上涨通道分析识别.txt",)

    with pytest.raises(ValueError, match="strategy IDs and files do not match"):
        TemplateContext(
            stage="stage2",
            symbol="TEST",
            timeframe="5m",
            bar_count=1,
            strategy_prompt_ids=(prompt_ids.BULLISH_CHANNEL_ID,),
            strategy_files=("下跌通道分析识别.txt",),
        )

    with pytest.raises(ValueError, match="Unknown prompt ID"):
        TemplateContext(
            stage="stage2",
            symbol="TEST",
            timeframe="5m",
            bar_count=1,
            strategy_prompt_ids=(PromptId("pa.unknown"),),
        )


def test_template_context_rejects_invalid_stage_and_bar_count() -> None:
    with pytest.raises(ValueError, match="Unknown template context stage"):
        TemplateContext(stage="stage3", symbol="X", timeframe="1m", bar_count=1)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must not be negative"):
        TemplateContext(stage="stage2", symbol="X", timeframe="1m", bar_count=-1)
