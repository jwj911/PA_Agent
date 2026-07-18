"""Application context wiring shared resources without global singletons."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from pa_agent.ai.cursor_sdk_client import CursorSdkClient
    from pa_agent.ai.deepseek_client import DeepSeekClient
    from pa_agent.ai.json_validator import JsonValidator
    from pa_agent.ai.prompt_assembler import PromptAssembler
    from pa_agent.ai.session_ledger import SessionTokenLedger
    from pa_agent.config.settings import Settings
    from pa_agent.data.base import DataSource
    from pa_agent.records.experience_reader import ExperienceReader
    from pa_agent.records.pending_writer import PendingWriter
    from pa_agent.util.event_bus import EventBus
    from pa_agent.util.event_sink import EventSink


@dataclass(slots=True)
class AppContext:
    """Carries shared resources to GUI widgets and orchestrators."""

    settings: Settings | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("pa_agent"))
    event_bus: EventBus | None = None
    event_sink: EventSink | None = None

    # Data layer
    data_source: DataSource | None = None

    # AI / orchestration layer
    client: DeepSeekClient | CursorSdkClient | None = None
    assembler: PromptAssembler | None = None
    router: Callable[[dict[str, Any]], list[str]] | None = None
    validator: JsonValidator | None = None
    pending_writer: PendingWriter | None = None
    exp_reader: ExperienceReader | None = None
    ledger: SessionTokenLedger | None = None

    @staticmethod
    def _resolve_settings(
        *,
        settings: Settings | None,
        settings_path: Path | None,
        sync_providers: bool | None,
    ) -> tuple[Settings, Path]:
        from pa_agent.config.paths import SETTINGS_JSON_PATH
        from pa_agent.config.settings import load_settings

        loaded_from_disk = settings is None
        resolved_settings_path = settings_path or SETTINGS_JSON_PATH
        if settings is None:
            settings = load_settings(resolved_settings_path)

        should_sync = loaded_from_disk if sync_providers is None else sync_providers
        if should_sync:
            from pa_agent.ai.provider_sync_service import sync_providers_on_load

            sync_providers_on_load(
                settings,
                save_path=resolved_settings_path if loaded_from_disk else None,
            )

        return settings, resolved_settings_path

    @staticmethod
    def _configure_app_logging(
        settings: Settings,
        *,
        configure_logs: bool,
    ) -> logging.Logger:
        if configure_logs:
            from pa_agent.util.logging import configure_logging

            configure_logging(api_key=settings.provider.api_key)

        return logging.getLogger("pa_agent")

    @classmethod
    def _build_core(
        cls,
        *,
        settings: Settings | None = None,
        settings_path: Path | None = None,
        event_sink: EventSink | None = None,
        prompt_dir: Path | None = None,
        experience_dir: Path | None = None,
        records_pending_dir: Path | None = None,
        sync_providers: bool | None = None,
        configure_logs: bool = True,
        event_bus: EventBus | None = None,
        data_source: DataSource | None = None,
        apply_kline_adjust: bool = True,
    ) -> AppContext:
        from pa_agent.ai.client_factory import create_ai_client
        from pa_agent.ai.json_validator import JsonValidator
        from pa_agent.ai.prompt_assembler import PromptAssembler
        from pa_agent.ai.router import route_strategy_files
        from pa_agent.ai.session_ledger import SessionTokenLedger
        from pa_agent.config.paths import EXPERIENCE_DIR, PROMPT_DIR, RECORDS_PENDING_DIR
        from pa_agent.records.experience_reader import ExperienceReader
        from pa_agent.records.pending_writer import PendingWriter
        from pa_agent.util.event_sink import NullEventSink

        settings, _ = cls._resolve_settings(
            settings=settings,
            settings_path=settings_path,
            sync_providers=sync_providers,
        )
        app_logger = cls._configure_app_logging(settings, configure_logs=configure_logs)
        sink = event_sink if event_sink is not None else NullEventSink()
        resolved_prompt_dir = prompt_dir if prompt_dir is not None else PROMPT_DIR
        resolved_experience_dir = (
            experience_dir if experience_dir is not None else EXPERIENCE_DIR
        )
        resolved_records_pending_dir = (
            records_pending_dir if records_pending_dir is not None else RECORDS_PENDING_DIR
        )

        if apply_kline_adjust:
            from pa_agent.data.kline_adjust import apply_kline_adjust_from_settings

            apply_kline_adjust_from_settings(settings)

        client = create_ai_client(settings.provider, logger_=app_logger)
        exp_reader = ExperienceReader(experience_dir=resolved_experience_dir, logger=app_logger)
        assembler = PromptAssembler(
            prompt_dir=resolved_prompt_dir,
            experience_reader=exp_reader,
            prompt_settings=settings.prompt,
        )
        validator = JsonValidator(settings)
        pending_writer = PendingWriter(
            pending_dir=resolved_records_pending_dir,
            event_bus=sink,
            api_key=settings.provider.api_key,
        )
        ledger = SessionTokenLedger(
            context_window=settings.provider.context_window,
            warn_pct=settings.general.context_warning_threshold_pct,
        )

        return cls(
            settings=settings,
            logger=app_logger,
            event_bus=event_bus,
            event_sink=sink,
            data_source=data_source,
            client=client,
            assembler=assembler,
            router=route_strategy_files,
            validator=validator,
            pending_writer=pending_writer,
            exp_reader=exp_reader,
            ledger=ledger,
        )

    @staticmethod
    def _connect_gui_data_source(
        *,
        settings: Settings,
        logger: logging.Logger,
    ) -> DataSource:
        from pa_agent.data.factory import create_data_source, normalize_data_source_kind
        from pa_agent.data.kline_adjust import apply_kline_adjust_from_settings

        apply_kline_adjust_from_settings(settings)
        ds_kind = normalize_data_source_kind(getattr(settings.general, "last_data_source", "mt5"))
        data_source = create_data_source(ds_kind, settings)

        try:
            data_source.connect()
            if ds_kind == "tradingview":
                from pa_agent.data.tradingview import TradingViewSource

                if isinstance(data_source, TradingViewSource):
                    saved_exchange = (
                        getattr(settings.general, "last_tradingview_exchange", "") or ""
                    )
                    data_source.set_exchange(saved_exchange)
            data_source.subscribe(
                settings.general.last_symbol,
                settings.general.last_timeframe,
            )
            logger.info(
                "Data source %s subscribed to %s %s",
                ds_kind,
                settings.general.last_symbol,
                settings.general.last_timeframe,
            )
        except Exception as exc:
            logger.warning("Initial data source subscription failed: %s", exc)

        return data_source

    @classmethod
    def bootstrap_gui(cls) -> AppContext:
        """Wire GUI adapters and shared core services."""
        from pa_agent.util.event_bus import EventBus

        settings, settings_path = cls._resolve_settings(
            settings=None,
            settings_path=None,
            sync_providers=None,
        )
        app_logger = cls._configure_app_logging(settings, configure_logs=True)
        event_bus = EventBus()
        data_source = cls._connect_gui_data_source(settings=settings, logger=app_logger)

        return cls._build_core(
            settings=settings,
            settings_path=settings_path,
            event_sink=event_bus,
            sync_providers=False,
            configure_logs=False,
            event_bus=event_bus,
            data_source=data_source,
            apply_kline_adjust=False,
        )

    @classmethod
    def bootstrap(cls) -> AppContext:
        """GUI-compatible startup facade."""
        return cls.bootstrap_gui()

    @classmethod
    def bootstrap_headless(
        cls,
        *,
        settings: Settings | None = None,
        settings_path: Path | None = None,
        event_sink: EventSink | None = None,
        prompt_dir: Path | None = None,
        experience_dir: Path | None = None,
        records_pending_dir: Path | None = None,
        sync_providers: bool | None = None,
        configure_logs: bool = True,
    ) -> AppContext:
        """Build core services without creating Qt objects or connecting data sources.

        Passing an in-memory ``settings`` skips settings file IO by default. When
        ``settings`` is omitted, the configured settings file is loaded and special
        provider routes are synced, matching GUI bootstrap behavior.
        """
        return cls._build_core(
            settings=settings,
            settings_path=settings_path,
            event_sink=event_sink,
            prompt_dir=prompt_dir,
            experience_dir=experience_dir,
            records_pending_dir=records_pending_dir,
            sync_providers=sync_providers,
            configure_logs=configure_logs,
            event_bus=None,
            data_source=None,
        )
