"""Small deterministic pipeline runner used during incremental migration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pa_agent.orchestrator.pipeline.state import PipelineState, TerminalStatus
from pa_agent.orchestrator.pipeline.step import PipelineStep, StepOutcome, StepResult


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
        if state.terminal_status is not TerminalStatus.RUNNING:
            return state
        if not self._steps:
            state.mark_terminal(TerminalStatus.FAILED)
            return state

        current = state
        for index, step in enumerate(self._steps):
            if index >= self._max_steps:
                raise PipelineExecutionError("Pipeline exceeded max_steps")
            if current.terminal_status is not TerminalStatus.RUNNING:
                break
            current.step_history.append(step.name)
            result = step.run(current, services)
            if not isinstance(result, StepResult):
                raise PipelineExecutionError(
                    f"Pipeline step {step.name!r} returned an invalid result"
                )
            current = result.state
            if result.outcome is StepOutcome.COMPLETE:
                if current.terminal_status is TerminalStatus.RUNNING:
                    current.mark_terminal(TerminalStatus.COMPLETED)
                break
            if result.outcome is StepOutcome.FAIL:
                if current.terminal_status is TerminalStatus.RUNNING:
                    current.mark_terminal(TerminalStatus.FAILED)
                break
        else:
            if current.terminal_status is TerminalStatus.RUNNING:
                current.mark_terminal(TerminalStatus.FAILED)
        return current
