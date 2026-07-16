"""Unit tests for EventBus signal hub."""
from __future__ import annotations

from unittest.mock import MagicMock

from pa_agent.util.event_bus import EventBus


def test_event_bus_initializes_with_signals() -> None:
    bus = EventBus()
    assert bus.data_frame is not None
    assert bus.status is not None
    assert bus.exception is not None
    assert bus.token_update is not None
    assert bus.disk_error is not None


def test_emit_status_forwards_to_signal() -> None:
    bus = EventBus()
    mock_receiver = MagicMock()
    bus.status.connect(mock_receiver)
    bus.emit_status("test status")
    mock_receiver.assert_called_once_with("test status")


def test_emit_exception_forwards_to_signal() -> None:
    bus = EventBus()
    mock_receiver = MagicMock()
    bus.exception.connect(mock_receiver)
    payload = {"test": "payload"}
    bus.emit_exception(payload)
    mock_receiver.assert_called_once_with(payload)


def test_emit_data_frame_forwards_to_signal() -> None:
    bus = EventBus()
    mock_receiver = MagicMock()
    bus.data_frame.connect(mock_receiver)
    frame = {"bars": []}
    bus.emit_data_frame(frame)
    mock_receiver.assert_called_once_with(frame)


def test_emit_token_update_forwards_to_signal() -> None:
    bus = EventBus()
    mock_receiver = MagicMock()
    bus.token_update.connect(mock_receiver)
    data = {"tokens": 100, "cost": 0.01}
    bus.emit_token_update(data)
    mock_receiver.assert_called_once_with(data)


def test_emit_disk_error_forwards_to_signal() -> None:
    bus = EventBus()
    mock_receiver = MagicMock()
    bus.disk_error.connect(mock_receiver)
    data = {"path": "/test/path", "error": "write failed"}
    bus.emit_disk_error(data)
    mock_receiver.assert_called_once_with(data)
