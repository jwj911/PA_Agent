"""PyQt-free application event sink ports."""

from __future__ import annotations

from threading import Lock
from typing import Protocol

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
