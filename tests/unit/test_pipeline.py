"""Tests for the PyQt-free L3 pipeline state and step contracts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pa_agent.orchestrator.pipeline import (
    PipelineBuilder,
    PipelineState,
    StepResult,
    TerminalStatus,
    terminal_status_for,
)
from pa_agent.util.threading import CancelToken, OrchestratorEvent


class _ContinueStep:
    name = "continue"

    def run(self, state: PipelineState, _services: object) -> StepResult:
        state.step_history.append("body:continue")
        return StepResult.continue_(state)


class _CompleteStep:
    name = "complete"

    def run(self, state: PipelineState, _services: object) -> StepResult:
        state.step_history.append("body:complete")
        return StepResult.complete(state)


def _state() -> PipelineState:
    return PipelineState(frame=object(), cancel_token=CancelToken())


def test_pipeline_builder_runs_ordered_steps_and_marks_completion() -> None:
    state = _state()

    result = PipelineBuilder((_ContinueStep(), _CompleteStep())).run(state, services=object())

    assert result is state
    assert result.step_history == [
        "continue",
        "body:continue",
        "complete",
        "body:complete",
    ]
    assert result.terminal_status is TerminalStatus.COMPLETED


def test_pipeline_builder_without_steps_is_explicit_failure() -> None:
    result = PipelineBuilder(()).run(_state(), services=object())

    assert result.terminal_status is TerminalStatus.FAILED


def test_pipeline_state_rejects_terminal_status_rewrite() -> None:
    state = _state()
    state.mark_terminal(TerminalStatus.CANCELLED)

    with pytest.raises(ValueError, match="already terminated"):
        state.mark_terminal(TerminalStatus.COMPLETED)


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (OrchestratorEvent.Cancelled, TerminalStatus.CANCELLED),
        (OrchestratorEvent.InsufficientData, TerminalStatus.INSUFFICIENT_DATA),
        (OrchestratorEvent.Stage1Failed, TerminalStatus.STAGE1_FAILED),
        (OrchestratorEvent.Stage2Failed, TerminalStatus.STAGE2_FAILED),
    ],
)
def test_terminal_status_maps_legacy_events(event, expected) -> None:
    record = SimpleNamespace(exception={"type": "provider_error"})

    assert terminal_status_for(record, [event]) is expected


def test_terminal_status_maps_success_and_unexpected_failure() -> None:
    assert terminal_status_for(SimpleNamespace(exception=None), []) is TerminalStatus.COMPLETED
    assert terminal_status_for(SimpleNamespace(exception={"type": "program_error"}), []) is (
        TerminalStatus.FAILED
    )
