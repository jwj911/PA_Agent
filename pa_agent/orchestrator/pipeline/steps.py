"""Compatibility steps that wrap the existing orchestrator implementation."""

from __future__ import annotations

from typing import Any

from pa_agent.orchestrator.pipeline.state import PipelineState, terminal_status_for
from pa_agent.orchestrator.pipeline.step import StepResult


def _response_usage(response: object) -> dict[str, object]:
    """Read provider usage from a record response without retaining the reply."""
    if not isinstance(response, dict):
        return {}
    usage = response.get("usage")
    return dict(usage) if isinstance(usage, dict) else {}


def _response_usage_calls(response: object) -> list[dict[str, object]]:
    """Recover the final call usage available in the legacy record.

    ``AnalysisRecord`` stores only the final raw response, so retry history
    cannot be reconstructed here. Returning one final-call snapshot is the
    most that the compatibility adapter can prove from the record.
    """
    usage = _response_usage(response)
    return [usage] if usage else []


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
        state.stage1_messages = list(record.stage1_messages)
        state.stage1_reply = record.stage1_response
        state.stage1_normalized_json = record.stage1_diagnosis
        state.stage1_usage = _response_usage(record.stage1_response)
        state.stage1_usage_calls = _response_usage_calls(record.stage1_response)
        state.stage2_messages = list(record.stage2_messages)
        state.stage2_reply = record.stage2_response
        state.stage2_normalized_json = record.stage2_decision
        state.stage2_usage = _response_usage(record.stage2_response)
        state.stage2_usage_calls = _response_usage_calls(record.stage2_response)
        state.strategy_files = list(record.strategy_files_used)
        state.experience_entries = list(record.experience_loaded)
        state.usage_total = dict(record.usage_total)
        state.route_outputs = {
            "strategy_files": list(state.strategy_files),
            "experience_entries": list(state.experience_entries),
        }
        state.update_terminal_metadata(record)
        state.mark_terminal(terminal_status_for(record, state.events))
        return StepResult.complete(state)
