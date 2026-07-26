"""Tests for AnalysisRecord Prompt ID and legacy filename compatibility."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from pa_agent.ai import prompting
from pa_agent.ai.prompting import prompt_ids
from pa_agent.records.schema import AnalysisRecord, RecordMeta


def _record(**updates) -> AnalysisRecord:
    payload = {
        "meta": RecordMeta(
            timestamp_local_iso="2026-07-26T00:00:00",
            timestamp_local_ms=1,
            symbol="TEST",
            timeframe="5m",
            bar_count=1,
            ai_provider={},
        ),
        "kline_data": [],
        "htf_text": "",
        "stage1_messages": [],
        "stage1_response": None,
        "stage1_diagnosis": None,
        "stage2_messages": [],
        "stage2_response": None,
        "stage2_decision": None,
        "strategy_files_used": [],
        "experience_loaded": [],
        "exception": None,
        "usage_total": {},
    }
    payload.update(updates)
    return AnalysisRecord.model_validate(payload)


def test_legacy_record_derives_prompt_ids_and_round_trips() -> None:
    record = _record(
        strategy_files_used=[
            "上涨通道分析识别.txt",
            "上涨通道交易策略.txt",
        ]
    )

    assert record.strategy_prompt_ids_used == [
        prompt_ids.BULLISH_CHANNEL_ID,
        prompt_ids.BULLISH_CHANNEL_STRATEGY,
    ]
    reconstructed = AnalysisRecord.model_validate(json.loads(json.dumps(record.model_dump())))
    assert reconstructed == record


def test_prompt_id_record_projects_legacy_filenames() -> None:
    record = _record(
        strategy_prompt_ids_used=[
            prompt_ids.BULLISH_SPIKE_ID,
            prompt_ids.BULLISH_SPIKE_STRATEGY,
        ]
    )

    assert record.strategy_files_used == [
        "极速上涨分析识别.txt",
        "极速上涨交易策略.txt",
    ]


def test_unknown_legacy_filename_is_preserved_without_disk_identity() -> None:
    record = _record(strategy_files_used=["private-strategy-path"])

    assert record.strategy_files_used == ["private-strategy-path"]
    assert record.strategy_prompt_ids_used == []


def test_legacy_alias_is_canonicalized_for_stable_round_trip(monkeypatch) -> None:
    alias = "persona-legacy.txt"
    persona = prompting.TEMPLATE_CATALOG.spec(prompt_ids.PERSONA)
    manifest = tuple(
        replace(spec, legacy_aliases=(alias,)) if spec.prompt_id == prompt_ids.PERSONA else spec
        for spec in prompting.TEMPLATE_CATALOG.manifest
    )
    monkeypatch.setattr(prompting, "TEMPLATE_CATALOG", prompting.PromptCatalog(manifest))

    record = _record(strategy_files_used=[alias])

    assert record.strategy_prompt_ids_used == [prompt_ids.PERSONA]
    assert record.strategy_files_used == [persona.legacy_filename]
    assert AnalysisRecord.model_validate(record.model_dump()) == record


def test_model_copy_synchronizes_both_strategy_identity_directions() -> None:
    record = _record()

    from_files = record.model_copy(update={"strategy_files_used": ["震荡区间交易策略.txt"]})
    assert from_files.strategy_prompt_ids_used == [prompt_ids.RANGE_STRATEGY]

    from_ids = record.model_copy(update={"strategy_prompt_ids_used": [prompt_ids.MTR]})
    assert from_ids.strategy_files_used == ["文件25-主要趋势反转MTR.txt"]


def test_record_rejects_mismatched_prompt_ids_and_filenames() -> None:
    with pytest.raises(ValidationError, match="Prompt IDs and files do not match"):
        _record(
            strategy_files_used=["下跌通道分析识别.txt"],
            strategy_prompt_ids_used=[prompt_ids.BULLISH_CHANNEL_ID],
        )


def test_record_rejects_unknown_prompt_id() -> None:
    with pytest.raises(ValidationError, match="Unknown prompt ID"):
        _record(strategy_prompt_ids_used=["test.unknown"])


def test_model_copy_rejects_mismatched_prompt_ids_and_filenames() -> None:
    record = _record()

    with pytest.raises(ValueError, match="Prompt IDs and files do not match"):
        record.model_copy(
            update={
                "strategy_files_used": ["下跌通道分析识别.txt"],
                "strategy_prompt_ids_used": [prompt_ids.BULLISH_CHANNEL_ID],
            }
        )
