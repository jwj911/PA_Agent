"""Event bus for inter-component communication via Qt signals."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from pa_agent.data.base import KlineFrame
from pa_agent.records.schema import AlarmPayload
from pa_agent.util.events import (
    EVENT_DATA_FRAME,
    EVENT_DISK_ERROR,
    EVENT_EXCEPTION,
    EVENT_STATUS,
    EVENT_TOKEN_UPDATE,
    AppEvent,
)


class EventBus(QObject):
    """Central signal hub shared across GUI components and orchestrators.

    Signals
    -------
    data_frame  : emitted by RefreshLoop with the latest KlineFrame
    status      : emitted with a human-readable status string for the status bar
    exception   : emitted when a JSON-validation alarm fires (AlarmPayload)
    token_update: emitted with a dict of token/cost update data for Tab2
    disk_error  : emitted when persisting a record to disk fails
    """

    data_frame = pyqtSignal(object)  # KlineFrame
    status = pyqtSignal(str)  # status text
    exception = pyqtSignal(object)  # AlarmPayload
    token_update = pyqtSignal(dict)  # token/cost update dict
    disk_error = pyqtSignal(dict)  # {"path": str, "error": str}

    def publish(self, event: AppEvent) -> None:
        """Publish a PyQt-free application event through the existing Qt signals."""
        if event.type == EVENT_STATUS:
            self.emit_status(str(event.payload.get("text", "")))
        elif event.type == EVENT_EXCEPTION:
            self.emit_exception(event.payload.get("payload"))
        elif event.type == EVENT_DATA_FRAME:
            self.emit_data_frame(event.payload.get("frame"))
        elif event.type == EVENT_TOKEN_UPDATE:
            data = event.payload.get("data")
            self.emit_token_update(data if isinstance(data, dict) else {})
        elif event.type == EVENT_DISK_ERROR:
            data = event.payload.get("data")
            self.emit_disk_error(data if isinstance(data, dict) else {})

    def emit_status(self, text: str) -> None:
        """Convenience wrapper — emit a status string."""
        self.status.emit(text)

    def emit_exception(self, payload: AlarmPayload) -> None:
        """Convenience wrapper — emit an AlarmPayload."""
        self.exception.emit(payload)

    def emit_data_frame(self, frame: KlineFrame) -> None:
        """Convenience wrapper — emit a KlineFrame."""
        self.data_frame.emit(frame)

    def emit_token_update(self, data: dict) -> None:
        """Convenience wrapper — emit a token/cost update dict."""
        self.token_update.emit(data)

    def emit_disk_error(self, data: dict) -> None:
        """Convenience wrapper — emit a disk-error payload."""
        self.disk_error.emit(data)
