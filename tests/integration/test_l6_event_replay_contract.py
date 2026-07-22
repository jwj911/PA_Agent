"""Cross-process JSONL event replay and correlation contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pa_agent.util.event_sink import JsonlEventSink
from pa_agent.util.events import AppEvent


def test_event_stream_replays_across_process_with_one_correlation_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run.jsonl"
    correlation_id = "l6-cross-process"
    events = (
        AppEvent.orchestrator(
            "Stage1Started",
            correlation_id=correlation_id,
            timestamp_ms=1,
        ),
        AppEvent.orchestrator(
            "Stage1Done",
            correlation_id=correlation_id,
            timestamp_ms=2,
        ),
        AppEvent.orchestrator(
            "RecordSaved",
            correlation_id=correlation_id,
            timestamp_ms=3,
        ),
    )

    with JsonlEventSink(path, require_correlation_id=True) as sink:
        for event in events:
            sink.publish(event)

    replay_code = """
import json
import sys
from pathlib import Path

from pa_agent.util.event_replay import replay_jsonl
from pa_agent.util.event_sink import CollectingEventSink

sink = CollectingEventSink()
count = replay_jsonl(
    Path(sys.argv[1]),
    sink,
    expected_correlation_id=sys.argv[2],
)
print(json.dumps({
    "count": count,
    "event_names": [event.payload["event"] for event in sink.events],
    "correlation_ids": [event.correlation_id for event in sink.events],
}, sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", replay_code, str(path), correlation_id],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "count": 3,
        "event_names": ["Stage1Started", "Stage1Done", "RecordSaved"],
        "correlation_ids": [correlation_id] * 3,
    }
