"""PyQt-free pipeline steps for the incremental orchestrator migration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pa_agent.orchestrator.pipeline.state import (
    PipelineState,
    TerminalStatus,
    terminal_status_for,
)
from pa_agent.orchestrator.pipeline.step import StepResult
from pa_agent.orchestrator.two_stage import (
    _accumulate_usage,
    _accumulate_usage_calls,
    _build_empty_record,
)
from pa_agent.util.threading import OrchestratorEvent


def _usage_snapshot(value: Any) -> dict[str, Any]:
    """Copy the stable usage counters from a reply or usage object."""
    source = value.get("usage") if isinstance(value, Mapping) else getattr(value, "usage", value)
    if source is None:
        return {}
    result: dict[str, Any] = {}
    for name in ("prompt_tokens", "cached_prompt_tokens", "completion_tokens", "total_tokens"):
        raw = source.get(name) if isinstance(source, Mapping) else getattr(source, name, None)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        result[name] = raw
    return result


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


def _set_terminal_from_record(state: PipelineState, record: Any) -> None:
    """Copy record metadata and derive the explicit pipeline terminal state."""
    state.record = record
    if state.partial_reason is None:
        exception = getattr(record, "exception", None)
        if isinstance(exception, Mapping):
            error_type = exception.get("type")
            stage = exception.get("stage")
            category = exception.get("category")
            if error_type == "network_error":
                state.partial_reason = "network_error"
            elif (
                error_type in {"provider_error", "validation_error"}
                and stage in {"stage1", "stage2"}
                and category in {"a", "b", "c", "d", "e"}
            ):
                state.partial_reason = f"{stage}_{category}"
    state.update_terminal_metadata(record)
    status = terminal_status_for(
        record,
        state.events,
        partial_reason=state.partial_reason,
    )
    state.mark_terminal(status)


def _set_stage1_record_snapshot(
    state: PipelineState,
    record: Any,
    *,
    preserve_usage_calls: bool = False,
) -> None:
    """Copy the Stage-1 fields that are available on a partial record."""
    state.stage1_messages = list(record.stage1_messages)
    state.stage1_reply = record.stage1_response
    state.stage1_normalized_json = record.stage1_diagnosis
    if not preserve_usage_calls or not state.stage1_usage:
        state.stage1_usage = _response_usage(record.stage1_response)
    if not preserve_usage_calls:
        state.stage1_usage_calls = _response_usage_calls(record.stage1_response)
    state.usage_total = dict(record.usage_total)


def _set_stage2_record_snapshot(state: PipelineState, record: Any) -> None:
    """Copy Stage-2 fields after the compatibility tail returns."""
    state.stage2_messages = list(record.stage2_messages)
    state.stage2_reply = record.stage2_response
    state.stage2_normalized_json = record.stage2_decision
    state.stage2_usage = _response_usage(record.stage2_response)
    state.stage2_usage_calls = _response_usage_calls(record.stage2_response)
    state.strategy_files = list(record.strategy_files_used)
    state.experience_entries = list(record.experience_loaded)
    state.route_outputs = {
        "strategy_files": list(state.strategy_files),
        "experience_entries": list(state.experience_entries),
    }
    state.usage_total = dict(record.usage_total)


def _set_stage1_runtime_snapshot(
    state: PipelineState,
    *,
    messages: list[dict[str, Any]],
    reply: Any,
    normalized_json: dict[str, Any],
    usage_calls: list[Any],
    thinking: bool,
    reasoning_effort: str,
    usage_total: dict[str, Any],
) -> None:
    """Copy the successful Stage-1 helper result into explicit pipeline state."""
    state.stage1_messages = list(messages)
    state.stage1_reply = reply
    state.stage1_normalized_json = normalized_json
    state.stage1_usage = _usage_snapshot(reply)
    state.stage1_usage_calls = list(usage_calls)
    state.usage_total = dict(usage_total)
    state.stage1_thinking = thinking
    state.stage1_reasoning_effort = reasoning_effort


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
        _set_stage1_record_snapshot(state, record)
        _set_stage2_record_snapshot(state, record)
        _set_terminal_from_record(state, record)
        return StepResult.complete(state)


class Stage1Step:
    """Execute only the real Stage-1 portion of ``TwoStageOrchestrator``."""

    name = "stage1"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Build, call, validate, and snapshot Stage 1 without Qt dependencies."""
        if state.record is None:
            state.record = _build_empty_record(state.frame, services._settings)

        if state.cancel_token.is_set():
            services._pending_writer.save_partial(state.record, "user_cancelled")
            state.partial_reason = "user_cancelled"
            state.emit(OrchestratorEvent.Cancelled)
            _set_terminal_from_record(state, state.record)
            return StepResult.fail(state)

        from pa_agent.ai.decision_nodes import check_preflight_data

        preflight = check_preflight_data(state.frame)
        if not preflight.ok:
            state.record = state.record.model_copy(
                update={
                    "exception": {
                        "type": "insufficient_data",
                        "stage": "preflight",
                        "failed_check": preflight.failed_check,
                        "message": preflight.reason,
                    }
                }
            )
            services._pending_writer.save_partial(state.record, "insufficient_data")
            state.partial_reason = "insufficient_data"
            state.emit(OrchestratorEvent.InsufficientData)
            _set_terminal_from_record(state, state.record)
            return StepResult.fail(state)

        result = services._run_stage1(
            record=state.record,
            on_event=state.emit,
            on_stage_prompt=state.on_stage_prompt,
            on_stage1_reasoning=state.on_stage1_reasoning,
            on_stage1_content=state.on_stage1_content,
            cancel_token=state.cancel_token,
            frame=state.frame,
            previous_record=state.previous_record,
            incremental_new_bar_count=state.incremental_new_bar_count,
        )
        if not isinstance(result, tuple):
            _set_stage1_record_snapshot(state, result)
            _set_terminal_from_record(state, result)
            return StepResult.fail(state)

        (
            stage1_json,
            messages_s1,
            reply_s1,
            usage_calls,
            thinking,
            reasoning_effort,
        ) = result
        usage_total = _accumulate_usage_calls(state.record.usage_total, usage_calls)
        _set_stage1_runtime_snapshot(
            state,
            messages=messages_s1,
            reply=reply_s1,
            normalized_json=stage1_json,
            usage_calls=usage_calls,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            usage_total=usage_total,
        )
        return StepResult.continue_(state)


class LegacyPostStage1Step:
    """Run the existing route/Stage-2/persistence tail after ``Stage1Step``."""

    name = "legacy_post_stage1"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Reuse legacy helpers until the remaining real steps are migrated."""
        if state.record is None or state.stage1_reply is None:
            state.mark_terminal(TerminalStatus.STAGE1_FAILED)
            return StepResult.fail(state)

        stage1_json = state.stage1_normalized_json or {}
        messages_s1 = state.stage1_messages
        reply_s1 = state.stage1_reply
        strategy_files, experience_entries = services._route_and_load_experience(
            stage1_json,
            current_bars=state.frame.bars,
        )
        state.set_route_outputs(
            strategy_files=strategy_files,
            experience_entries=experience_entries,
        )

        if state.cancel_token.is_set():
            state.record = state.record.model_copy(
                update={
                    "stage1_messages": messages_s1,
                    "stage1_response": reply_s1.raw,
                    "stage1_diagnosis": stage1_json,
                    "strategy_files_used": strategy_files,
                    "experience_loaded": [
                        e.model_dump() if hasattr(e, "model_dump") else dict(e)
                        for e in experience_entries
                    ],
                    "usage_total": _accumulate_usage(
                        state.record.usage_total,
                        reply_s1.usage,
                    ),
                }
            )
            services._pending_writer.save_partial(state.record, "user_cancelled")
            state.partial_reason = "user_cancelled"
            state.emit(OrchestratorEvent.Cancelled)
            _set_stage1_record_snapshot(state, state.record, preserve_usage_calls=True)
            _set_terminal_from_record(state, state.record)
            return StepResult.fail(state)

        state.emit(OrchestratorEvent.Stage2Started)
        if state.on_stage2_files is not None:
            state.on_stage2_files(list(strategy_files))

        gate_record = services._try_gate_short_circuit(
            record=state.record,
            on_event=state.emit,
            on_stage_prompt=state.on_stage_prompt,
            on_stage2_content=state.on_stage2_content,
            stage1_json=stage1_json,
            messages_s1=messages_s1,
            reply_s1=reply_s1,
            strategy_files=strategy_files,
            experience_entries=experience_entries,
        )
        if gate_record is not None:
            state.record = gate_record
            _set_stage1_record_snapshot(state, gate_record, preserve_usage_calls=True)
            _set_stage2_record_snapshot(state, gate_record)
            _set_terminal_from_record(state, gate_record)
            return StepResult.complete(state)

        messages_s2, enable_next_bar, flip_cooldown = services._build_stage2_messages(
            frame=state.frame,
            messages_s1=messages_s1,
            reply_s1=reply_s1,
            stage1_json=stage1_json,
            strategy_files=strategy_files,
            experience_entries=experience_entries,
            record=state.record,
            previous_record=state.previous_record,
        )
        state.stage2_messages = list(messages_s2)
        state.record = services._run_stage2(
            record=state.record,
            on_event=state.emit,
            on_stage_prompt=state.on_stage_prompt,
            on_stage2_reasoning=state.on_stage2_reasoning,
            on_stage2_content=state.on_stage2_content,
            cancel_token=state.cancel_token,
            frame=state.frame,
            messages_s1=messages_s1,
            reply_s1=reply_s1,
            stage1_json=stage1_json,
            strategy_files=strategy_files,
            experience_entries=experience_entries,
            messages_s2=messages_s2,
            previous_record=state.previous_record,
            _enable_next_bar=enable_next_bar,
            _flip_cooldown=flip_cooldown,
            _thinking=state.stage1_thinking,
            _effort=state.stage1_reasoning_effort,
            s1_usage_calls=state.stage1_usage_calls,
        )
        _set_stage1_record_snapshot(state, state.record, preserve_usage_calls=True)
        _set_stage2_record_snapshot(state, state.record)
        _set_terminal_from_record(state, state.record)
        if state.terminal_status is TerminalStatus.COMPLETED:
            return StepResult.complete(state)
        return StepResult.fail(state)
