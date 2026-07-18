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

    @classmethod
    def bootstrap(cls) -> AppContext:
        """Wire all real components and return a fully initialised AppContext."""
        from pa_agent.ai.json_validator import JsonValidator
        from pa_agent.ai.prompt_assembler import PromptAssembler
        from pa_agent.ai.router import route_strategy_files
        from pa_agent.ai.session_ledger import SessionTokenLedger
        from pa_agent.config.paths import (
            EXPERIENCE_DIR,
            PROMPT_DIR,
            RECORDS_PENDING_DIR,
            SETTINGS_JSON_PATH,
        )
        from pa_agent.config.settings import load_settings
        from pa_agent.data.factory import create_data_source, normalize_data_source_kind
        from pa_agent.records.experience_reader import ExperienceReader
        from pa_agent.records.pending_writer import PendingWriter
        from pa_agent.util.event_bus import EventBus
        from pa_agent.util.logging import configure_logging

        # ── Settings ──────────────────────────────────────────────────────────
        settings = load_settings(SETTINGS_JSON_PATH)
        from pa_agent.ai.provider_sync_service import sync_providers_on_load

        sync_providers_on_load(settings, save_path=SETTINGS_JSON_PATH)

        # ── Logging (with API key masking) ────────────────────────────────────
        configure_logging(api_key=settings.provider.api_key)

        app_logger = logging.getLogger("pa_agent")

        # ── Event bus ─────────────────────────────────────────────────────────
        event_bus = EventBus()

        # ── Data layer ────────────────────────────────────────────────────────
        from pa_agent.data.kline_adjust import apply_kline_adjust_from_settings

        apply_kline_adjust_from_settings(settings)
        ds_kind = normalize_data_source_kind(getattr(settings.general, "last_data_source", "mt5"))
        data_source = create_data_source(ds_kind, settings)

        # Subscribe to the last-used symbol/timeframe from settings
        try:
            data_source.connect()
            if ds_kind == "tradingview":
                from pa_agent.data.tradingview import TradingViewSource

                if isinstance(data_source, TradingViewSource):
                    # Use saved exchange setting, default to auto (empty).
                    saved_exchange = (
                        getattr(settings.general, "last_tradingview_exchange", "") or ""
                    )
                    data_source.set_exchange(saved_exchange)
            data_source.subscribe(
                settings.general.last_symbol,
                settings.general.last_timeframe,
            )
            app_logger.info(
                "Data source %s subscribed to %s %s",
                ds_kind,
                settings.general.last_symbol,
                settings.general.last_timeframe,
            )
        except Exception as exc:
            app_logger.warning("Initial data source subscription failed: %s", exc)

        # ── AI client ─────────────────────────────────────────────────────────
        from pa_agent.ai.client_factory import create_ai_client

        client = create_ai_client(settings.provider, logger_=app_logger)

        # ── Prompt assembler ──────────────────────────────────────────────────
        exp_reader = ExperienceReader(experience_dir=EXPERIENCE_DIR, logger=app_logger)
        assembler = PromptAssembler(
            prompt_dir=PROMPT_DIR,
            experience_reader=exp_reader,
            prompt_settings=settings.prompt,
        )

        # ── Validator & router ────────────────────────────────────────────────
        validator = JsonValidator(settings)
        router = route_strategy_files

        # ── Pending writer ────────────────────────────────────────────────────
        pending_writer = PendingWriter(
            pending_dir=RECORDS_PENDING_DIR,
            event_bus=event_bus,
            api_key=settings.provider.api_key,
        )

        # ── Session ledger ────────────────────────────────────────────────────
        ledger = SessionTokenLedger(
            context_window=settings.provider.context_window,
            warn_pct=settings.general.context_warning_threshold_pct,
        )

        return cls(
            settings=settings,
            logger=app_logger,
            event_bus=event_bus,
            event_sink=event_bus,
            data_source=data_source,
            client=client,
            assembler=assembler,
            router=router,
            validator=validator,
            pending_writer=pending_writer,
            exp_reader=exp_reader,
            ledger=ledger,
        )

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
        from pa_agent.ai.json_validator import JsonValidator
        from pa_agent.ai.prompt_assembler import PromptAssembler
        from pa_agent.ai.router import route_strategy_files
        from pa_agent.ai.session_ledger import SessionTokenLedger
        from pa_agent.config.paths import (
            EXPERIENCE_DIR,
            PROMPT_DIR,
            RECORDS_PENDING_DIR,
            SETTINGS_JSON_PATH,
        )
        from pa_agent.config.settings import load_settings
        from pa_agent.records.experience_reader import ExperienceReader
        from pa_agent.records.pending_writer import PendingWriter
        from pa_agent.util.event_sink import NullEventSink
        from pa_agent.util.logging import configure_logging

        loaded_from_disk = settings is None
        settings_path = settings_path or SETTINGS_JSON_PATH
        if settings is None:
            settings = load_settings(settings_path)

        should_sync = loaded_from_disk if sync_providers is None else sync_providers
        if should_sync:
            from pa_agent.ai.provider_sync_service import sync_providers_on_load

            sync_providers_on_load(settings, save_path=settings_path if loaded_from_disk else None)

        if configure_logs:
            configure_logging(api_key=settings.provider.api_key)

        app_logger = logging.getLogger("pa_agent")
        sink = event_sink or NullEventSink()
        prompt_dir = prompt_dir or PROMPT_DIR
        experience_dir = experience_dir or EXPERIENCE_DIR
        records_pending_dir = records_pending_dir or RECORDS_PENDING_DIR

        from pa_agent.data.kline_adjust import apply_kline_adjust_from_settings

        apply_kline_adjust_from_settings(settings)

        from pa_agent.ai.client_factory import create_ai_client

        client = create_ai_client(settings.provider, logger_=app_logger)
        exp_reader = ExperienceReader(experience_dir=experience_dir, logger=app_logger)
        assembler = PromptAssembler(
            prompt_dir=prompt_dir,
            experience_reader=exp_reader,
            prompt_settings=settings.prompt,
        )
        validator = JsonValidator(settings)
        pending_writer = PendingWriter(
            pending_dir=records_pending_dir,
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
            event_bus=None,
            event_sink=sink,
            data_source=None,
            client=client,
            assembler=assembler,
            router=route_strategy_files,
            validator=validator,
            pending_writer=pending_writer,
            exp_reader=exp_reader,
            ledger=ledger,
        )
