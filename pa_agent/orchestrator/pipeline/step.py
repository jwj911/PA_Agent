"""PyQt-free step protocol and result values for the pipeline migration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pa_agent.orchestrator.pipeline.state import PipelineState


class StepOutcome(StrEnum):
    """Control signal returned by one pipeline step."""

    CONTINUE = "continue"
    COMPLETE = "complete"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class StepResult:
    """Result envelope returned by a :class:`PipelineStep`."""

    state: PipelineState
    outcome: StepOutcome

    @classmethod
    def continue_(cls, state: PipelineState) -> StepResult:
        """Continue with the next registered step."""
        return cls(state=state, outcome=StepOutcome.CONTINUE)

    @classmethod
    def complete(cls, state: PipelineState) -> StepResult:
        """Stop successfully after the current step."""
        return cls(state=state, outcome=StepOutcome.COMPLETE)

    @classmethod
    def fail(cls, state: PipelineState) -> StepResult:
        """Stop with a failed terminal status after the current step."""
        return cls(state=state, outcome=StepOutcome.FAIL)


class PipelineStep(Protocol):
    """Structural contract for a PyQt-free pipeline step."""

    name: str

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Advance *state* using explicitly supplied application services."""
