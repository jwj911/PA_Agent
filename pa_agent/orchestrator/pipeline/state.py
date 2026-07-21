"""PyQt-free state values for the incremental pipeline migration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pa_agent.records.schema import AnalysisRecord
from pa_agent.util.threading import CancelToken, OrchestratorEvent


class TerminalStatus(StrEnum):
    """Explicit terminal status for one pipeline execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INSUFFICIENT_DATA = "insufficient_data"
    STAGE1_FAILED = "stage1_failed"
    STAGE2_FAILED = "stage2_failed"
    FAILED = "failed"


def terminal_status_for(
    record: AnalysisRecord | None,
    events: Sequence[OrchestratorEvent],
) -> TerminalStatus:
    """Map legacy record/events to the explicit pipeline terminal status."""
    event_set = set(events)
    if OrchestratorEvent.Cancelled in event_set:
        return TerminalStatus.CANCELLED
    if OrchestratorEvent.InsufficientData in event_set:
        return TerminalStatus.INSUFFICIENT_DATA
    if OrchestratorEvent.Stage1Failed in event_set:
        return TerminalStatus.STAGE1_FAILED
    if OrchestratorEvent.Stage2Failed in event_set:
        return TerminalStatus.STAGE2_FAILED
    if record is not None and record.exception is None:
        return TerminalStatus.COMPLETED
    return TerminalStatus.FAILED


@dataclass(slots=True)
class PipelineState:
    """Mutable execution state carried between pipeline steps.

    Runtime callbacks and service objects are intentionally kept at the
    adapter boundary. They are not serialized or exposed as record payload.
    """

    frame: Any
    cancel_token: CancelToken
    on_event: Callable[[OrchestratorEvent], None] = field(
        default=lambda _event: None,
        repr=False,
    )
    on_stage1_reasoning: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage1_content: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage2_reasoning: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage2_content: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage_prompt: Callable[[str, str, str], None] | None = field(default=None, repr=False)
    on_stage2_files: Callable[[list[str]], None] | None = field(default=None, repr=False)
    previous_record: AnalysisRecord | None = None
    incremental_new_bar_count: int | None = None
    record: AnalysisRecord | None = None
    terminal_status: TerminalStatus = TerminalStatus.RUNNING
    events: list[OrchestratorEvent] = field(default_factory=list)
    step_history: list[str] = field(default_factory=list)

    def emit(self, event: OrchestratorEvent) -> None:
        """Record and forward one legacy orchestrator event."""
        self.events.append(event)
        self.on_event(event)

    def mark_terminal(self, status: TerminalStatus) -> None:
        """Set a terminal status while preventing accidental rewrites."""
        if status is TerminalStatus.RUNNING:
            raise ValueError("Pipeline terminal status cannot be running")
        if self.terminal_status is not TerminalStatus.RUNNING and self.terminal_status is not status:
            raise ValueError(
                f"Pipeline already terminated with {self.terminal_status.value}"
            )
        self.terminal_status = status

    @property
    def event_names(self) -> tuple[str, ...]:
        """Return stable event names for snapshots and adapter output."""
        return tuple(event.name for event in self.events)
