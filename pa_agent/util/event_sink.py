"""PyQt-free application event sink ports."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Protocol

from pa_agent.util.event_serialization import event_to_dict
from pa_agent.util.events import AppEvent


class EventSink(Protocol):
    """Minimal port implemented by GUI and headless event adapters."""

    def publish(self, event: AppEvent) -> None:
        """Publish one application event."""


class NullEventSink:
    """Event sink that intentionally drops all events."""

    def publish(self, event: AppEvent) -> None:
        del event


class CollectingEventSink:
    """Thread-safe in-memory event sink for tests and headless orchestration."""

    def __init__(self) -> None:
        self._events: list[AppEvent] = []
        self._lock = Lock()

    def publish(self, event: AppEvent) -> None:
        with self._lock:
            self._events.append(event)

    @property
    def events(self) -> tuple[AppEvent, ...]:
        """Collected events as an immutable snapshot."""
        with self._lock:
            return tuple(self._events)

    def clear(self) -> None:
        """Remove all collected events."""
        with self._lock:
            self._events.clear()


class JsonlEventSink:
    """Append application events as one deterministic JSON object per line."""

    def __init__(
        self,
        path: Path,
        *,
        require_correlation_id: bool = False,
    ) -> None:
        self._path = Path(path)
        self._require_correlation_id = require_correlation_id
        self._lock = Lock()
        self._closed = False

    @property
    def path(self) -> Path:
        """Return the JSONL output path."""
        return self._path

    def publish(self, event: AppEvent) -> None:
        """Append one event and flush it before returning."""
        if self._require_correlation_id and not event.correlation_id:
            raise ValueError("JSONL event requires a correlation_id")
        line = json.dumps(
            event_to_dict(event),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        with self._lock:
            if self._closed:
                raise RuntimeError("JSONL event sink is closed")
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.write("\n")

    def close(self) -> None:
        """Prevent further writes; existing JSONL content remains intact."""
        with self._lock:
            self._closed = True

    def __enter__(self) -> JsonlEventSink:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()
