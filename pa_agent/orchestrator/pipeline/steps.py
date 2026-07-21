"""Compatibility steps that wrap the existing orchestrator implementation."""

from __future__ import annotations

from typing import Any

from pa_agent.orchestrator.pipeline.state import PipelineState, terminal_status_for
from pa_agent.orchestrator.pipeline.step import StepResult


class LegacySubmitStep:
    """Run the unchanged ``TwoStageOrchestrator.submit`` implementation."""

    name = "legacy_submit"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Execute the legacy method and translate its terminal state."""
        record = services.submit(
            frame=state.frame,
            cancel_token=state.cancel_token,
            on_event=state.emit,
            on_stage1_reasoning=state.on_stage1_reasoning,
            on_stage1_content=state.on_stage1_content,
            on_stage2_reasoning=state.on_stage2_reasoning,
            on_stage2_content=state.on_stage2_content,
            on_stage_prompt=state.on_stage_prompt,
            on_stage2_files=state.on_stage2_files,
            previous_record=state.previous_record,
            incremental_new_bar_count=state.incremental_new_bar_count,
        )
        state.record = record
        state.mark_terminal(terminal_status_for(record, state.events))
        return StepResult.complete(state)
