"""Replay JSONL application events through a PyQt-free event sink."""

from __future__ import annotations

import json
from pathlib import Path

from pa_agent.util.event_serialization import EventSerializationError, event_from_dict
from pa_agent.util.event_sink import EventSink


class EventReplayError(ValueError):
    """Raised when a JSONL event stream is malformed."""


def replay_jsonl(
    path: Path,
    sink: EventSink,
    *,
    expected_correlation_id: str | None = None,
    require_correlation_id: bool = False,
) -> int:
    """Replay events, optionally enforcing one cross-process correlation id.

    The default keeps legacy replay behavior.  Strict callers can provide an
    expected id and require every event in the stream to carry that exact
    non-empty id; validation completes before publishing any event.
    """
    if expected_correlation_id is not None and not expected_correlation_id:
        raise ValueError("expected_correlation_id must not be empty")
    if expected_correlation_id is not None:
        require_correlation_id = True
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EventReplayError(f"Unable to read JSONL event stream: {path}: {exc}") from exc

    events = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = event_from_dict(json.loads(line))
        except (json.JSONDecodeError, EventSerializationError) as exc:
            raise EventReplayError(f"Invalid JSONL event at line {line_number}: {exc}") from exc
        if require_correlation_id and not event.correlation_id:
            raise EventReplayError(f"Event at line {line_number} is missing a correlation_id")
        if expected_correlation_id is not None and event.correlation_id != expected_correlation_id:
            raise EventReplayError(
                f"Event at line {line_number} has correlation_id "
                f"{event.correlation_id!r}, expected {expected_correlation_id!r}"
            )
        events.append(event)

    for event in events:
        sink.publish(event)
    return len(events)
