"""Tests for legacy/Pipeline live observation pair validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pa_agent.util.event_sink import JsonlEventSink
from pa_agent.util.events import AppEvent
from tools.compare_live_observations import compare_live_observations

_EVENT_NAMES = (
    "Stage1Started",
    "Stage1Done",
    "Stage2Started",
    "Stage2Done",
    "RecordSaved",
)


def _write_observation(
    root: Path,
    *,
    correlation_id: str,
    pipeline_enabled: bool,
    private_marker: str,
    events: tuple[str, ...] = _EVENT_NAMES,
) -> tuple[Path, Path, Path]:
    root.mkdir()
    events_path = root / "events.jsonl"
    records_dir = root / "records"
    records_dir.mkdir()
    record_file = "record.json"
    record = {
        "meta": {
            "timestamp_local_iso": "opaque-time",
            "timestamp_local_ms": 1,
            "symbol": private_marker,
            "timeframe": "opaque",
            "bar_count": 1,
            "ai_provider": {"model": private_marker},
            "decision_stance": "conservative",
        },
        "kline_data": [{"private": private_marker}],
        "htf_text": private_marker,
        "stage1_messages": [{"role": "system", "content": private_marker}],
        "stage1_response": {"content": private_marker},
        "stage1_diagnosis": {"private": private_marker},
        "stage2_messages": [
            {"role": "system", "content": private_marker},
            {"role": "assistant", "content": private_marker},
            {"role": "user", "content": private_marker},
        ],
        "stage2_response": {"content": private_marker},
        "stage2_decision": {"private": private_marker},
        "strategy_files_used": [private_marker],
        "experience_loaded": [{"private": private_marker}],
        "exception": None,
        "usage_total": {"total_tokens": 1 if not pipeline_enabled else 999},
    }
    (records_dir / record_file).write_text(json.dumps(record), encoding="utf-8")

    with JsonlEventSink(events_path, require_correlation_id=True) as sink:
        for index, name in enumerate(events):
            sink.publish(
                AppEvent.orchestrator(
                    name,
                    correlation_id=correlation_id,
                    timestamp_ms=index + 1,
                )
            )

    summary_path = root / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "schema": "pa-agent.live-observation.v1",
                "correlation_id": correlation_id,
                "event_file": events_path.name,
                "pipeline_builder_enabled": pipeline_enabled,
                "status": "completed",
                "provider_called": True,
                "event_schema": "pa-agent.event.v1",
                "event_count": len(events),
                "replayed_event_count": len(events),
                "events": list(events),
                "record_written": True,
                "record_file": record_file,
                "exception_type": None,
            }
        ),
        encoding="utf-8",
    )
    return summary_path, events_path, records_dir


def _pair(tmp_path: Path) -> tuple[tuple[Path, Path, Path], tuple[Path, Path, Path]]:
    return (
        _write_observation(
            tmp_path / "legacy",
            correlation_id="legacy-live",
            pipeline_enabled=False,
            private_marker="LEGACY_PRIVATE",
        ),
        _write_observation(
            tmp_path / "pipeline",
            correlation_id="pipeline-live",
            pipeline_enabled=True,
            private_marker="PIPELINE_PRIVATE",
        ),
    )


def test_pair_validator_compares_contract_without_exposing_payloads(tmp_path: Path) -> None:
    legacy, pipeline = _pair(tmp_path)

    result = compare_live_observations(
        legacy_summary_path=legacy[0],
        legacy_events_path=legacy[1],
        legacy_records_dir=legacy[2],
        pipeline_summary_path=pipeline[0],
        pipeline_events_path=pipeline[1],
        pipeline_records_dir=pipeline[2],
    )

    assert result["valid"] is True
    assert result["events"] == list(_EVENT_NAMES)
    assert result["record_contract"]["stage2_message_roles"] == [
        "system",
        "assistant",
        "user",
    ]
    rendered = json.dumps(result)
    assert "LEGACY_PRIVATE" not in rendered
    assert "PIPELINE_PRIVATE" not in rendered
    assert "total_tokens" in rendered
    assert "999" not in rendered


def test_pair_validator_rejects_event_sequence_mismatch(tmp_path: Path) -> None:
    legacy, _pipeline = _pair(tmp_path)
    pipeline = _write_observation(
        tmp_path / "pipeline-mismatch",
        correlation_id="pipeline-mismatch",
        pipeline_enabled=True,
        private_marker="PIPELINE_PRIVATE",
        events=(*_EVENT_NAMES[:-1], "Stage2Failed"),
    )

    with pytest.raises(ValueError, match="event sequence"):
        compare_live_observations(
            legacy_summary_path=legacy[0],
            legacy_events_path=legacy[1],
            legacy_records_dir=legacy[2],
            pipeline_summary_path=pipeline[0],
            pipeline_events_path=pipeline[1],
            pipeline_records_dir=pipeline[2],
        )


def test_pair_validator_rejects_record_structure_mismatch(tmp_path: Path) -> None:
    legacy, _pipeline = _pair(tmp_path)
    pipeline = _write_observation(
        tmp_path / "pipeline-mismatch",
        correlation_id="pipeline-mismatch",
        pipeline_enabled=True,
        private_marker="PIPELINE_PRIVATE",
    )
    record_path = pipeline[2] / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["stage2_messages"] = [{"role": "system", "content": "PIPELINE_PRIVATE"}]
    record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="record structure"):
        compare_live_observations(
            legacy_summary_path=legacy[0],
            legacy_events_path=legacy[1],
            legacy_records_dir=legacy[2],
            pipeline_summary_path=pipeline[0],
            pipeline_events_path=pipeline[1],
            pipeline_records_dir=pipeline[2],
        )


def test_pair_validator_requires_legacy_and_pipeline_modes(tmp_path: Path) -> None:
    legacy, pipeline = _pair(tmp_path)
    payload = json.loads(pipeline[0].read_text(encoding="utf-8"))
    payload["pipeline_builder_enabled"] = False
    pipeline[0].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="must enable Pipeline"):
        compare_live_observations(
            legacy_summary_path=legacy[0],
            legacy_events_path=legacy[1],
            legacy_records_dir=legacy[2],
            pipeline_summary_path=pipeline[0],
            pipeline_events_path=pipeline[1],
            pipeline_records_dir=pipeline[2],
        )
