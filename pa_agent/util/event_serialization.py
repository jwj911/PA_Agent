"""PyQt-free serialization helpers for application events."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

from pa_agent.util.events import EVENT_ENVELOPE_SCHEMA, AppEvent


class EventSerializationError(ValueError):
    """Raised when an application event cannot be safely serialized or decoded."""


def _json_safe(value: Any) -> Any:
    """Convert event payload values into JSON-compatible primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump())
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    return str(value)


def event_to_dict(event: AppEvent) -> dict[str, Any]:
    """Return a JSON-compatible event envelope."""
    return {
        "schema": EVENT_ENVELOPE_SCHEMA,
        "type": str(event.type),
        "timestamp_ms": int(event.timestamp_ms),
        "correlation_id": (str(event.correlation_id) if event.correlation_id is not None else None),
        "payload": _json_safe(event.payload),
    }


def event_from_dict(value: Any) -> AppEvent:
    """Decode and validate one JSON event envelope."""
    if not isinstance(value, Mapping):
        raise EventSerializationError("Event envelope must be an object")
    event_type = value.get("type")
    timestamp_ms = value.get("timestamp_ms")
    correlation_id = value.get("correlation_id")
    payload = value.get("payload", {})
    schema = value.get("schema")
    if schema is not None and schema != EVENT_ENVELOPE_SCHEMA:
        raise EventSerializationError(f"Unsupported event schema: {schema!r}")
    if not isinstance(event_type, str) or not event_type.strip():
        raise EventSerializationError("Event type must be a non-empty string")
    if isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, int):
        raise EventSerializationError("Event timestamp_ms must be an integer")
    if correlation_id is not None and not isinstance(correlation_id, str):
        raise EventSerializationError("Event correlation_id must be a string or null")
    if not isinstance(payload, Mapping):
        raise EventSerializationError("Event payload must be an object")
    return AppEvent(
        type=event_type,
        timestamp_ms=timestamp_ms,
        correlation_id=correlation_id,
        payload=dict(payload),
    )
