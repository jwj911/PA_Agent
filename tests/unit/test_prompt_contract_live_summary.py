"""Tests for aggregate-only live Prompt-contract summaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pa_agent.util.event_sink import JsonlEventSink
from pa_agent.util.events import AppEvent
from tools.summarize_prompt_contract_live import (
    LIVE_AGGREGATE_SCHEMA,
    aggregate_live_observations,
    summarize_live_observation,
)


def _write_observation(
    root: Path,
    *,
    name: str,
    pipeline_enabled: bool,
    with_retry: bool,
    with_identity_conflict: bool,
    terminal_validation_failure: bool = False,
    prompt_tokens: int = 100,
) -> tuple[Path, Path, Path]:
    observation_dir = root / name
    records_dir = observation_dir / "records"
    records_dir.mkdir(parents=True)
    correlation_id = f"{name}-correlation"
    events_path = observation_dir / f"{name}.events.jsonl"
    event_names = ["Stage1Started"]
    if with_retry:
        event_names.append("Stage1Retry")
    event_names.extend(("Stage1Done", "Stage2Started", "Stage2Done", "RecordSaved"))
    with JsonlEventSink(events_path, require_correlation_id=True) as sink:
        for index, event_name in enumerate(event_names):
            sink.publish(
                AppEvent.orchestrator(
                    event_name,
                    correlation_id=correlation_id,
                    timestamp_ms=index + 1,
                )
            )

    stage1_payload: dict[str, object] = {
        "cycle_position": "normal_channel",
        "direction": "bullish",
    }
    if with_identity_conflict:
        stage1_payload["strategy_files_needed"] = ["下跌通道分析识别.txt"]
    exception = (
        {"type": "stage1_validation_error", "stage": "stage1", "category": "c"}
        if terminal_validation_failure
        else None
    )
    record_file = f"{name}.json"
    (records_dir / record_file).write_text(
        json.dumps(
            {
                "meta": {
                    "bar_count": 2,
                    "timeframe": "5m",
                    "ai_provider": {
                        "base_url": "https://provider.invalid",
                        "model": "fixture-model",
                    },
                },
                "kline_data": [{"private_market_marker": "do-not-export"}],
                "htf_text": "private-htf-marker",
                "stage1_response": {"content": json.dumps(stage1_payload, ensure_ascii=False)},
                "stage1_diagnosis": {
                    "cycle_position": "normal_channel",
                    "direction": "bullish",
                    "detected_patterns": [],
                },
                "usage_total": {
                    "prompt_tokens": prompt_tokens,
                    "cached_prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": prompt_tokens + 20,
                },
                "exception": exception,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary_path = observation_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "pa-agent.live-observation.v1",
                "correlation_id": correlation_id,
                "event_file": events_path.name,
                "pipeline_builder_enabled": pipeline_enabled,
                "status": "partial" if terminal_validation_failure else "completed",
                "provider_called": True,
                "event_schema": "pa-agent.event.v1",
                "event_count": len(event_names),
                "replayed_event_count": len(event_names),
                "events": event_names,
                "record_written": True,
                "record_file": record_file,
                "exception_type": (
                    "stage1_validation_error" if terminal_validation_failure else None
                ),
            }
        ),
        encoding="utf-8",
    )
    return summary_path, events_path, records_dir


def test_live_prompt_contract_aggregate_counts_retries_usage_and_conflicts(
    tmp_path: Path,
) -> None:
    _write_observation(
        tmp_path,
        name="legacy",
        pipeline_enabled=False,
        with_retry=True,
        with_identity_conflict=True,
        prompt_tokens=100,
    )
    _write_observation(
        tmp_path,
        name="pipeline",
        pipeline_enabled=True,
        with_retry=False,
        with_identity_conflict=False,
        prompt_tokens=200,
    )

    report = aggregate_live_observations(
        observations_root=tmp_path,
        contract_version="fixture-contract",
    )
    metrics = report["metrics"]

    assert report["schema"] == LIVE_AGGREGATE_SCHEMA
    assert report["observation_count"] == 2
    assert report["execution_modes"] == {"legacy": 1, "pipeline": 1}
    assert metrics["stage1_retry_count"] == 1
    assert metrics["validation_retry_count"] == 1
    assert metrics["validation_retry_run_rate"] == 0.5
    assert metrics["model_prompt_identity_output_runs"] == 1
    assert metrics["semantic_routing_conflicts"] == 1
    assert metrics["semantic_routing_conflict_rate"] == 0.5
    assert metrics["usage_totals"]["prompt_tokens"] == 300
    assert report["gates"]["single_provider_contract"] is True
    assert report["gates"]["single_fixture_contract"] is True


def test_live_prompt_contract_report_does_not_expose_raw_artifact_content(
    tmp_path: Path,
) -> None:
    _write_observation(
        tmp_path,
        name="private",
        pipeline_enabled=False,
        with_retry=False,
        with_identity_conflict=True,
    )

    report = aggregate_live_observations(
        observations_root=tmp_path,
        contract_version="fixture-contract",
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)

    assert "do-not-export" not in rendered
    assert "private-htf-marker" not in rendered
    assert "下跌通道分析识别.txt" not in rendered
    assert "correlation" not in rendered
    assert str(tmp_path) not in rendered
    assert '"content"' not in rendered


def test_live_prompt_contract_summary_detects_terminal_validation_failure(
    tmp_path: Path,
) -> None:
    summary_path, events_path, records_dir = _write_observation(
        tmp_path,
        name="failure",
        pipeline_enabled=False,
        with_retry=False,
        with_identity_conflict=False,
        terminal_validation_failure=True,
    )

    result = summarize_live_observation(
        summary_path=summary_path,
        events_path=events_path,
        records_dir=records_dir,
    )

    assert result["terminal_validation_failure"] is True
    assert result["completed"] is False


def test_live_prompt_contract_aggregate_requires_observations(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no live observation summaries"):
        aggregate_live_observations(
            observations_root=tmp_path,
            contract_version="fixture-contract",
        )
