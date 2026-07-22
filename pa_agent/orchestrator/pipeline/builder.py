"""Small deterministic pipeline runner used during incremental migration."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from typing import Any

from pa_agent.orchestrator.pipeline.state import PipelineState, TerminalStatus
from pa_agent.orchestrator.pipeline.step import PipelineStep, StepOutcome, StepResult

logger = logging.getLogger(__name__)


class PipelineExecutionError(RuntimeError):
    """Raised when a pipeline step violates the step contract."""


class PipelineBuilder:
    """Run an ordered sequence of explicit steps without GUI dependencies."""

    def __init__(self, steps: Sequence[PipelineStep], *, max_steps: int = 32) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self._steps = tuple(steps)
        self._max_steps = max_steps

    @property
    def steps(self) -> tuple[PipelineStep, ...]:
        """Return the immutable step sequence."""
        return self._steps

    def run(self, state: PipelineState, services: Any) -> PipelineState:
        """Run steps until a terminal result is produced."""
        started_at = time.monotonic()
        current = state
        logger.info(
            "pipeline.lifecycle",
            extra={
                "trace_id": state.trace_id,
                "pipeline_event": "start",
                "pipeline_step_count": len(self._steps),
                "pipeline_summary": state.safe_summary(),
            },
        )
        exception_type: str | None = None
        try:
            if state.terminal_status is not TerminalStatus.RUNNING:
                for index, step in enumerate(self._steps):
                    self._log_step_skip(
                        state,
                        step,
                        index,
                        reason="terminal_state",
                    )
                return state
            if not self._steps:
                current.mark_terminal(TerminalStatus.FAILED)
                self._log_terminal(current, started_at)
                return current

            for index, step in enumerate(self._steps):
                if index >= self._max_steps:
                    raise PipelineExecutionError("Pipeline exceeded max_steps")
                if current.terminal_status is not TerminalStatus.RUNNING and not (
                    current.persistence_pending and getattr(step, "is_persistence_step", False)
                ):
                    self._log_step_skip(current, step, index, reason="terminal_state")
                    continue
                current.step_history.append(step.name)
                step_started_at = time.monotonic()
                logger.info(
                    "pipeline.lifecycle",
                    extra={
                        "trace_id": current.trace_id,
                        "pipeline_event": "step_start",
                        "pipeline_step": step.name,
                        "pipeline_step_index": index,
                    },
                )
                result = step.run(current, services)
                if not isinstance(result, StepResult):
                    exception_type = PipelineExecutionError.__name__
                    logger.warning(
                        "pipeline.lifecycle",
                        extra={
                            "trace_id": current.trace_id,
                            "pipeline_event": "step_error",
                            "pipeline_step": step.name,
                            "pipeline_exception_type": exception_type,
                        },
                    )
                    raise PipelineExecutionError(
                        f"Pipeline step {step.name!r} returned an invalid result"
                    )
                current = result.state
                logger.info(
                    "pipeline.lifecycle",
                    extra={
                        "trace_id": current.trace_id,
                        "pipeline_event": "step_result",
                        "pipeline_step": step.name,
                        "pipeline_outcome": result.outcome.value,
                        "pipeline_step_elapsed_ms": _elapsed_ms(step_started_at),
                        "pipeline_summary": current.safe_summary(),
                    },
                )
                if result.outcome is StepOutcome.COMPLETE:
                    if current.terminal_status is TerminalStatus.RUNNING:
                        current.mark_terminal(TerminalStatus.COMPLETED)
                    self._log_terminal(current, started_at)
                    break
                if result.outcome is StepOutcome.FAIL:
                    if current.terminal_status is TerminalStatus.RUNNING:
                        current.mark_terminal(TerminalStatus.FAILED)
                    if current.persistence_pending:
                        continue
                    self._log_terminal(current, started_at)
                    break
            else:
                if current.terminal_status is TerminalStatus.RUNNING:
                    current.mark_terminal(TerminalStatus.FAILED)
                self._log_terminal(current, started_at)
            return current
        except Exception as exc:
            if exception_type is None:
                exception_type = type(exc).__name__
                logger.warning(
                    "pipeline.lifecycle",
                    extra={
                        "trace_id": current.trace_id,
                        "pipeline_event": "step_error",
                        "pipeline_exception_type": exception_type,
                    },
                )
            raise
        finally:
            self._log_end(current, started_at, exception_type=exception_type)

    @staticmethod
    def _log_terminal(state: PipelineState, started_at: float) -> None:
        logger.info(
            "pipeline.lifecycle",
            extra={
                "trace_id": state.trace_id,
                "pipeline_event": "terminal",
                "pipeline_terminal_status": state.terminal_status.value,
                "pipeline_elapsed_ms": _elapsed_ms(started_at),
                "pipeline_summary": state.safe_summary(),
            },
        )

    @staticmethod
    def _log_step_skip(
        state: PipelineState,
        step: PipelineStep,
        index: int,
        *,
        reason: str,
    ) -> None:
        logger.info(
            "pipeline.lifecycle",
            extra={
                "trace_id": state.trace_id,
                "pipeline_event": "step_skip",
                "pipeline_step": step.name,
                "pipeline_step_index": index,
                "pipeline_skip_reason": reason,
                "pipeline_terminal_status": state.terminal_status.value,
            },
        )

    @staticmethod
    def _log_end(
        state: PipelineState,
        started_at: float,
        *,
        exception_type: str | None = None,
    ) -> None:
        fields: dict[str, Any] = {
            "trace_id": state.trace_id,
            "pipeline_event": "end",
            "pipeline_elapsed_ms": _elapsed_ms(started_at),
            "pipeline_summary": state.safe_summary(),
        }
        if exception_type is not None:
            fields["pipeline_exception_type"] = exception_type
        logger.info(
            "pipeline.lifecycle",
            extra=fields,
        )


def _elapsed_ms(started_at: float) -> int:
    """Return a monotonic duration suitable for stable operational logging."""
    return max(0, int((time.monotonic() - started_at) * 1000))
