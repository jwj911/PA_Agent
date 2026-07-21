"""Replay JSONL application events through a PyQt-free event sink."""

from __future__ import annotations

import json
from pathlib import Path

from pa_agent.util.event_serialization import EventSerializationError, event_from_dict
from pa_agent.util.event_sink import EventSink


class EventReplayError(ValueError):
    """Raised when a JSONL event stream is malformed."""


def replay_jsonl(path: Path, sink: EventSink) -> int:
    """Replay all events from *path* into *sink* and return the event count."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EventReplayError(f"Unable to read JSONL event stream: {path}: {exc}") from exc

    count = 0
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = event_from_dict(json.loads(line))
        except (json.JSONDecodeError, EventSerializationError) as exc:
            raise EventReplayError(f"Invalid JSONL event at line {line_number}: {exc}") from exc
        sink.publish(event)
        count += 1
    return count
