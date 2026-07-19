"""Tests for AppContext headless and GUI bootstrap wiring."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from pa_agent.app_context import AppContext
from pa_agent.config.settings import Settings
from pa_agent.data.snapshot import build_analysis_frame
from pa_agent.util.event_sink import CollectingEventSink
from pa_agent.util.events import EVENT_DISK_ERROR
from tests.fixtures.kline_bars import make_newest_first_bars


class _FakeEventBus:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


class _FakeDataSource:
    def __init__(self) -> None:
        self.connected = False
        self.subscriptions: list[tuple[str, str]] = []

    def connect(self) -> None:
        self.connected = True

    def subscribe(self, symbol: str, timeframe: str) -> None:
        self.subscriptions.append((symbol, timeframe))


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

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_shared_core_build_does_not_import_qt_event_bus(tmp_path: Path) -> None:
    code = f"""
import sys
from pathlib import Path
from pa_agent.app_context import AppContext
from pa_agent.config.settings import Settings
from pa_agent.util.event_sink import CollectingEventSink

ctx = AppContext._build_core(
    settings=Settings(),
    event_sink=CollectingEventSink(),
    records_pending_dir=Path(r"{tmp_path}"),
    sync_providers=False,
    configure_logs=False,
    apply_kline_adjust=False,
)
assert ctx.event_bus is None
assert "pa_agent.util.event_bus" not in sys.modules
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_headless_and_gui_core_build_same_stage1_prompt(tmp_path: Path) -> None:
    settings = Settings()
    frame = build_analysis_frame(
        make_newest_first_bars(25, with_forming=False),
        20,
        "TEST",
        "5m",
    )
    assert frame is not None

    headless = AppContext._build_core(
        settings=settings,
        event_sink=CollectingEventSink(),
        records_pending_dir=tmp_path / "headless",
        sync_providers=False,
        configure_logs=False,
        apply_kline_adjust=False,
    )
    gui_core = AppContext._build_core(
        settings=settings,
        event_sink=_FakeEventBus(),
        event_bus=_FakeEventBus(),
        data_source=_FakeDataSource(),
        records_pending_dir=tmp_path / "gui",
        sync_providers=False,
        configure_logs=False,
        apply_kline_adjust=False,
    )

    assert headless.assembler is not None
    assert gui_core.assembler is not None
    assert headless.assembler.build_stage1(frame) == gui_core.assembler.build_stage1(frame)


def test_bootstrap_preserves_gui_event_bus_data_source_and_event_sink(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_settings = Settings()
    app_settings.general.last_symbol = "TEST:SYMBOL"
    app_settings.general.last_timeframe = "5m"
    data_source = _FakeDataSource()
    fake_client = object()
    logger = logging.getLogger("pa_agent.test_app_context")
    event_bus_module = ModuleType("pa_agent.util.event_bus")
    event_bus_module.EventBus = _FakeEventBus

    def fake_resolve_settings(
        *,
        settings: Settings | None,
        settings_path: Path | None,
        sync_providers: bool | None,
    ) -> tuple[Settings, Path]:
        return settings or app_settings, settings_path or tmp_path / "settings.json"

    def fake_configure_app_logging(
        _settings: Settings,
        *,
        configure_logs: bool,
    ) -> logging.Logger:
        return logger

    def fake_create_data_source(kind: str | None, settings: Settings) -> _FakeDataSource:
        assert kind == "mt5"
        assert settings is app_settings
        return data_source

    def fake_create_ai_client(provider, logger_=None):
        assert provider is app_settings.provider
        assert logger_ is logger
        return fake_client

    monkeypatch.setitem(sys.modules, "pa_agent.util.event_bus", event_bus_module)
    monkeypatch.setattr(
        AppContext,
        "_resolve_settings",
        staticmethod(fake_resolve_settings),
    )
    monkeypatch.setattr(
        AppContext,
        "_configure_app_logging",
        staticmethod(fake_configure_app_logging),
    )
    monkeypatch.setattr("pa_agent.data.factory.normalize_data_source_kind", lambda _kind: "mt5")
    monkeypatch.setattr("pa_agent.data.factory.create_data_source", fake_create_data_source)
    monkeypatch.setattr(
        "pa_agent.data.kline_adjust.apply_kline_adjust_from_settings",
        lambda _settings: None,
    )
    monkeypatch.setattr("pa_agent.ai.client_factory.create_ai_client", fake_create_ai_client)
    monkeypatch.setattr("pa_agent.config.paths.PROMPT_DIR", tmp_path / "prompts")
    monkeypatch.setattr("pa_agent.config.paths.EXPERIENCE_DIR", tmp_path / "experience")
    monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", tmp_path / "pending")

    ctx = AppContext.bootstrap()

    assert ctx.settings is app_settings
    assert isinstance(ctx.event_bus, _FakeEventBus)
    assert ctx.event_sink is ctx.event_bus
    assert ctx.data_source is data_source
    assert ctx.client is fake_client
    assert data_source.connected is True
    assert data_source.subscriptions == [("TEST:SYMBOL", "5m")]
