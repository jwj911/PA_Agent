"""Public PyQt-free adapter for headless two-stage analysis."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.event_sink import EventSink, NullEventSink
from pa_agent.util.events import AppEvent
from pa_agent.util.threading import CancelToken, OrchestratorEvent

if TYPE_CHECKING:
    from pa_agent.app_context import AppContext
    from pa_agent.data.base import KlineFrame
    from pa_agent.records.schema import AnalysisRecord


class HeadlessAdapterError(RuntimeError):
    """Raised when the headless context cannot execute an analysis."""


@dataclass(frozen=True, slots=True)
class HeadlessAnalysisResult:
    """Stable result envelope returned by the public headless adapter."""

    record: AnalysisRecord
    correlation_id: str
    event_names: tuple[str, ...]


class HeadlessAnalysisAdapter:
    """Run one analysis through shared core services without importing Qt."""

    def __init__(
        self,
        context: AppContext,
        *,
        event_sink: EventSink | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._context = context
        self._event_sink = event_sink or getattr(context, "event_sink", None) or NullEventSink()
        self._correlation_id = str(correlation_id or uuid.uuid4().hex)

    @property
    def correlation_id(self) -> str:
        """Return the correlation id used for all emitted application events."""
        return self._correlation_id

    def run(
        self,
        frame: KlineFrame,
        *,
        cancel_token: CancelToken | None = None,
        on_event: Callable[[OrchestratorEvent], None] | None = None,
    ) -> HeadlessAnalysisResult:
        """Execute one two-stage analysis and publish milestone events."""
        self._require_dependencies()
        event_names: list[str] = []
        token = cancel_token or CancelToken()

        def emit(event: OrchestratorEvent) -> None:
            name = event.name if isinstance(event, OrchestratorEvent) else str(event)
            event_names.append(name)
            self._event_sink.publish(
                AppEvent.orchestrator(name, correlation_id=self._correlation_id)
            )
            if on_event is not None:
                on_event(event)

        orchestrator = TwoStageOrchestrator(
            client=self._context.client,
            assembler=self._context.assembler,
            router=self._context.router,
            validator=self._context.validator,
            pending_writer=self._context.pending_writer,
            exp_reader=self._context.exp_reader,
            settings=self._context.settings,
        )
        record = orchestrator.submit(
            frame=frame,
            cancel_token=token,
            on_event=emit,
        )
        return HeadlessAnalysisResult(
            record=record,
            correlation_id=self._correlation_id,
            event_names=tuple(event_names),
        )

    def _require_dependencies(self) -> None:
        required = (
            "client",
            "assembler",
            "router",
            "validator",
            "pending_writer",
            "exp_reader",
        )
        missing = [name for name in required if getattr(self._context, name, None) is None]
        if missing:
            raise HeadlessAdapterError(
                f"headless runner dependencies missing: {', '.join(missing)}"
            )


__all__ = [
    "HeadlessAdapterError",
    "HeadlessAnalysisAdapter",
    "HeadlessAnalysisResult",
]
