"""Tests for PyQt-free application event sinks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pa_agent.util.event_replay import EventReplayError, replay_jsonl
from pa_agent.util.event_sink import CollectingEventSink, JsonlEventSink, NullEventSink
from pa_agent.util.events import (
    EVENT_STATUS,
    AppEvent,
)


def test_app_event_factories_build_expected_payloads() -> None:
    event = AppEvent.status("ready", correlation_id="abc", timestamp_ms=123)

    assert event.type == EVENT_STATUS
    assert event.timestamp_ms == 123
    assert event.correlation_id == "abc"
    assert event.payload == {"text": "ready"}


def test_collecting_event_sink_returns_snapshot_and_can_clear() -> None:
    sink = CollectingEventSink()
    first = AppEvent.status("one", timestamp_ms=1)
    second = AppEvent.token_update({"tokens": 2}, timestamp_ms=2)

    sink.publish(first)
    snapshot = sink.events
    sink.publish(second)

    assert snapshot == (first,)
    assert sink.events == (first, second)

    sink.clear()
    assert sink.events == ()


def test_null_event_sink_drops_events() -> None:
    sink = NullEventSink()

    sink.publish(AppEvent.status("ignored", timestamp_ms=1))


def test_jsonl_event_sink_writes_and_replays_events(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "events.jsonl"
    first = AppEvent.status("ready", correlation_id="run-1", timestamp_ms=1)
    second = AppEvent.token_update(
        {"input_tokens": 3},
        correlation_id="run-1",
        timestamp_ms=2,
    )

    with JsonlEventSink(path, require_correlation_id=True) as sink:
        sink.publish(first)
        sink.publish(second)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"correlation_id":"run-1"' in lines[0]

    replayed = CollectingEventSink()
    assert replay_jsonl(path, replayed) == 2
    assert replayed.events == (first, second)

    with pytest.raises(RuntimeError, match="closed"):
        sink.publish(first)


def test_jsonl_event_sink_requires_correlation_id(tmp_path: Path) -> None:
    sink = JsonlEventSink(tmp_path / "events.jsonl", require_correlation_id=True)

    with pytest.raises(ValueError, match="correlation_id"):
        sink.publish(AppEvent.status("missing", timestamp_ms=1))


def test_replay_jsonl_reports_malformed_line(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"type":"status","timestamp_ms":1}\n{broken\n', encoding="utf-8")

    with pytest.raises(EventReplayError, match="line 2"):
        replay_jsonl(path, CollectingEventSink())


def test_importing_util_package_does_not_eagerly_import_qt_event_bus() -> None:
    code = (
        "import sys; import pa_agent.util; "
        "raise SystemExit(1 if 'pa_agent.util.event_bus' in sys.modules else 0)"
    )

    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0
