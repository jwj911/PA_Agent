"""Tests for PyQt-free application event sinks."""

from __future__ import annotations

import subprocess
import sys

from pa_agent.util.event_sink import CollectingEventSink, NullEventSink
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


def test_importing_util_package_does_not_eagerly_import_qt_event_bus() -> None:
    code = (
        "import sys; import pa_agent.util; "
        "raise SystemExit(1 if 'pa_agent.util.event_bus' in sys.modules else 0)"
    )

    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0
