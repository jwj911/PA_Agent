"""PyQt-free application event value objects for GUI and headless adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pa_agent.util.timefmt import now_local_ms

EVENT_STATUS = "status"
EVENT_EXCEPTION = "exception"
EVENT_DATA_FRAME = "data_frame"
EVENT_TOKEN_UPDATE = "token_update"
EVENT_DISK_ERROR = "disk_error"


@dataclass(frozen=True)
class AppEvent:
    """Serializable application event passed through :class:`EventSink` ports."""

    type: str
    timestamp_ms: int
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build an event, filling ``timestamp_ms`` when omitted."""
        return cls(
            type=event_type,
            timestamp_ms=now_local_ms() if timestamp_ms is None else timestamp_ms,
            correlation_id=correlation_id,
            payload=dict(payload or {}),
        )

    @classmethod
    def status(
        cls,
        text: str,
        *,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build a status-text event."""
        return cls.create(
            EVENT_STATUS,
            payload={"text": text},
            correlation_id=correlation_id,
            timestamp_ms=timestamp_ms,
        )

    @classmethod
    def exception(
        cls,
        payload: Any,
        *,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build a validation/exception event."""
        return cls.create(
            EVENT_EXCEPTION,
            payload={"payload": payload},
            correlation_id=correlation_id,
            timestamp_ms=timestamp_ms,
        )

    @classmethod
    def data_frame(
        cls,
        frame: Any,
        *,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build a K-line frame event."""
        return cls.create(
            EVENT_DATA_FRAME,
            payload={"frame": frame},
            correlation_id=correlation_id,
            timestamp_ms=timestamp_ms,
        )

    @classmethod
    def token_update(
        cls,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build a token/cost update event."""
        return cls.create(
            EVENT_TOKEN_UPDATE,
            payload={"data": dict(data)},
            correlation_id=correlation_id,
            timestamp_ms=timestamp_ms,
        )

    @classmethod
    def disk_error(
        cls,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> AppEvent:
        """Build a disk-error event."""
        return cls.create(
            EVENT_DISK_ERROR,
            payload={"data": dict(data)},
            correlation_id=correlation_id,
            timestamp_ms=timestamp_ms,
        )
