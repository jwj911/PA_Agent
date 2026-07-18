"""Unit tests for EventBus signal hub."""

from __future__ import annotations

from unittest.mock import MagicMock

from pa_agent.util.event_bus import EventBus
from pa_agent.util.events import AppEvent


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


def test_publish_forwards_app_events_to_existing_signals() -> None:
    bus = EventBus()
    status = MagicMock()
    exception = MagicMock()
    data_frame = MagicMock()
    token_update = MagicMock()
    disk_error = MagicMock()
    bus.status.connect(status)
    bus.exception.connect(exception)
    bus.data_frame.connect(data_frame)
    bus.token_update.connect(token_update)
    bus.disk_error.connect(disk_error)

    bus.publish(AppEvent.status("ready", timestamp_ms=1))
    bus.publish(AppEvent.exception({"category": "a"}, timestamp_ms=2))
    bus.publish(AppEvent.data_frame({"bars": []}, timestamp_ms=3))
    bus.publish(AppEvent.token_update({"tokens": 1}, timestamp_ms=4))
    bus.publish(AppEvent.disk_error({"path": "x", "error": "failed"}, timestamp_ms=5))

    status.assert_called_once_with("ready")
    exception.assert_called_once_with({"category": "a"})
    data_frame.assert_called_once_with({"bars": []})
    token_update.assert_called_once_with({"tokens": 1})
    disk_error.assert_called_once_with({"path": "x", "error": "failed"})
