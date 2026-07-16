"""Tests for the snapshot fetch worker."""
from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QApplication

from pa_agent.gui.snapshot_worker import SnapshotFetchWorker

_APP: QApplication | None = None


def _ensure_app() -> None:
    global _APP
    _APP = QApplication.instance() or QApplication([])


class _FakeSource:
    def __init__(self, result: list[Any] | None = None, error: Exception | None = None) -> None:
        self.result = result or []
        self.error = error
        self.calls: list[int] = []

    def latest_snapshot(self, n_bars: int) -> list[Any]:
        self.calls.append(n_bars)
        if self.error is not None:
            raise self.error
        return self.result


def test_snapshot_worker_emits_bars_ready_with_latest_snapshot() -> None:
    _ensure_app()
    source = _FakeSource(result=["bar-1", "bar-2"])
    worker = SnapshotFetchWorker(source, 2)
    ready: list[list[Any]] = []
    failed: list[str] = []
    worker.bars_ready.connect(ready.append)
    worker.failed.connect(failed.append)

    worker.run()

    assert source.calls == [2]
    assert ready == [["bar-1", "bar-2"]]
    assert failed == []


def test_snapshot_worker_emits_failed_message_on_exception() -> None:
    _ensure_app()
    source = _FakeSource(error=RuntimeError("snapshot unavailable"))
    worker = SnapshotFetchWorker(source, 3)
    ready: list[list[Any]] = []
    failed: list[str] = []
    worker.bars_ready.connect(ready.append)
    worker.failed.connect(failed.append)

    worker.run()

    assert source.calls == [3]
    assert ready == []
    assert failed == ["snapshot unavailable"]
