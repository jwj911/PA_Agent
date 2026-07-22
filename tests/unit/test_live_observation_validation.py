"""Tests for sanitized live observation artifact validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pa_agent.util.event_sink import JsonlEventSink
from pa_agent.util.events import AppEvent
from tools.validate_live_observation import validate_live_observation


def _write_artifacts(tmp_path: Path, *, event_names: tuple[str, ...]) -> tuple[Path, Path, Path]:
    correlation_id = "validation-run"
    events_path = tmp_path / "events.jsonl"
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    record_file = "record.json"
    (records_dir / record_file).write_text("{}", encoding="utf-8")
    with JsonlEventSink(events_path, require_correlation_id=True) as sink:
        for index, name in enumerate(event_names):
            sink.publish(
                AppEvent.orchestrator(
                    name,
                    correlation_id=correlation_id,
                    timestamp_ms=index + 1,
                )
            )
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "pa-agent.live-observation.v1",
                "correlation_id": correlation_id,
                "event_file": events_path.name,
                "pipeline_builder_enabled": False,
                "status": "completed",
                "provider_called": True,
                "event_schema": "pa-agent.event.v1",
                "event_count": len(event_names),
                "replayed_event_count": len(event_names),
                "events": list(event_names),
                "record_written": True,
                "record_file": record_file,
                "exception_type": None,
            }
        ),
        encoding="utf-8",
    )
    return summary_path, events_path, records_dir


def test_live_observation_validator_checks_event_and_record_contract(tmp_path: Path) -> None:
    summary_path, events_path, records_dir = _write_artifacts(
        tmp_path,
        event_names=("Stage1Started", "RecordSaved"),
    )

    result = validate_live_observation(
        summary_path=summary_path,
        events_path=events_path,
        records_dir=records_dir,
    )

    assert result["valid"] is True
    assert result["event_count"] == 2
    assert result["event_file"] == "events.jsonl"
    assert result["record_file"] == "record.json"


def test_live_observation_validator_rejects_sequence_mismatch(tmp_path: Path) -> None:
    summary_path, events_path, records_dir = _write_artifacts(
        tmp_path,
        event_names=("Stage1Started", "RecordSaved"),
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["events"] = ["Stage1Started", "Stage2Done"]
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="event sequence"):
        validate_live_observation(
            summary_path=summary_path,
            events_path=events_path,
            records_dir=records_dir,
        )
