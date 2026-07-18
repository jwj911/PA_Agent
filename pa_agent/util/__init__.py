"""PA Agent utility package."""

from pa_agent.util.event_sink import CollectingEventSink, EventSink, NullEventSink
from pa_agent.util.events import AppEvent
from pa_agent.util.logging import configure_logging, update_api_key
from pa_agent.util.threading import CancelToken, OrchestratorEvent

__all__ = [
    "AppEvent",
    "CancelToken",
    "CollectingEventSink",
    "EventBus",
    "EventSink",
    "NullEventSink",
    "OrchestratorEvent",
    "configure_logging",
    "update_api_key",
]


def __getattr__(name: str):
    """Lazy-load Qt-backed exports so headless imports stay PyQt6-free."""
    if name == "EventBus":
        from pa_agent.util.event_bus import EventBus

        return EventBus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
