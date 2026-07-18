"""Tests for PyQt-free AppContext headless bootstrap."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pa_agent.app_context import AppContext
from pa_agent.config.settings import Settings
from pa_agent.util.event_sink import CollectingEventSink
from pa_agent.util.events import EVENT_DISK_ERROR


def test_bootstrap_headless_builds_core_without_event_bus(tmp_path: Path) -> None:
    settings = Settings()
    sink = CollectingEventSink()

    ctx = AppContext.bootstrap_headless(
        settings=settings,
        event_sink=sink,
        records_pending_dir=tmp_path,
        sync_providers=False,
        configure_logs=False,
    )

    assert ctx.settings is settings
    assert ctx.event_bus is None
    assert ctx.event_sink is sink
    assert ctx.data_source is None
    assert ctx.client is not None
    assert ctx.assembler is not None
    assert ctx.router is not None
    assert ctx.validator is not None
    assert ctx.pending_writer is not None
    assert ctx.exp_reader is not None
    assert ctx.ledger is not None


def test_bootstrap_headless_can_publish_pending_writer_disk_errors(tmp_path: Path) -> None:
    sink = CollectingEventSink()
    ctx = AppContext.bootstrap_headless(
        settings=Settings(),
        event_sink=sink,
        records_pending_dir=tmp_path,
        sync_providers=False,
        configure_logs=False,
    )

    assert ctx.pending_writer is not None
    ctx.pending_writer._handle_disk_error(OSError("boom"), tmp_path / "record.json")

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.type == EVENT_DISK_ERROR
    assert event.payload["data"]["path"].endswith("record.json")
    assert event.payload["data"]["error"] == "boom"


def test_bootstrap_headless_does_not_import_qt_event_bus(tmp_path: Path) -> None:
    code = f"""
import sys
from pathlib import Path
from pa_agent.app_context import AppContext
from pa_agent.config.settings import Settings
from pa_agent.util.event_sink import CollectingEventSink

ctx = AppContext.bootstrap_headless(
    settings=Settings(),
    event_sink=CollectingEventSink(),
    records_pending_dir=Path(r"{tmp_path}"),
    sync_providers=False,
    configure_logs=False,
)
assert ctx.event_bus is None
assert "pa_agent.util.event_bus" not in sys.modules
"""

    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0
