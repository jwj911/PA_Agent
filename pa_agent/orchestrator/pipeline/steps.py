"""PyQt-free pipeline steps for the incremental orchestrator migration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pa_agent.orchestrator.pipeline.state import (
    PersistenceIntent,
    PipelineState,
    TerminalStatus,
    terminal_status_for,
)
from pa_agent.orchestrator.pipeline.step import StepOutcome, StepResult
from pa_agent.orchestrator.two_stage import (
    _LEGACY_SUBMIT,
    TwoStageOrchestrator,
    _accumulate_usage_calls,
    _build_empty_record,
)
from pa_agent.util.threading import OrchestratorEvent

logger = logging.getLogger(__name__)


def _log(state: PipelineState, event: str, **fields: Any) -> None:
    """Emit only allowlisted, scalar lifecycle fields for one pipeline."""
    logger.info(
        "pipeline.step",
        extra={
            "trace_id": state.trace_id,
            "pipeline_event": event,
            **fields,
        },
    )


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


def _raw_reply(reply: Any) -> Any:
    """Return the record-shaped raw reply for runtime or compatibility values."""
    if reply is None:
        return None
    return getattr(reply, "raw", reply)


def _experience_payload(entries: list[Any], fallback: list[dict]) -> list[dict]:
    """Convert runtime experience entries while preserving the record schema."""
    if not entries and fallback:
        return list(fallback)
    return [
        entry.model_dump() if hasattr(entry, "model_dump") else dict(entry) for entry in entries
    ]


def _assemble_pipeline_record(state: PipelineState, *, full: bool) -> Any:
    """Assemble the canonical record from state snapshots at the persist boundary."""
    if state.record is None:
        return None

    record = state.record
    stage1_messages = state.stage1_messages or record.stage1_messages
    stage1_reply = (
        _raw_reply(state.stage1_reply) if state.stage1_reply is not None else record.stage1_response
    )
    stage1_json = (
        state.stage1_normalized_json
        if state.stage1_normalized_json is not None
        else record.stage1_diagnosis
    )
    stage2_messages = state.stage2_messages or record.stage2_messages
    stage2_reply = (
        _raw_reply(state.stage2_reply) if state.stage2_reply is not None else record.stage2_response
    )
    stage2_json = (
        state.stage2_normalized_json
        if state.stage2_normalized_json is not None
        else record.stage2_decision
    )
    strategy_files = state.strategy_files or record.strategy_files_used
    experience_loaded = _experience_payload(
        state.experience_entries,
        record.experience_loaded,
    )
    usage_total = dict(state.usage_total or record.usage_total)
    updates = {
        "stage1_messages": list(stage1_messages),
        "stage1_response": stage1_reply,
        "stage1_diagnosis": stage1_json,
        "stage2_messages": list(stage2_messages),
        "stage2_response": stage2_reply,
        "stage2_decision": stage2_json,
        "strategy_files_used": list(strategy_files),
        "experience_loaded": experience_loaded,
        "usage_total": usage_total,
    }
    if full:
        updates["exception"] = None
    return record.model_copy(update=updates)


def _set_terminal_from_record(
    state: PipelineState,
    record: Any,
    *,
    persistence_pending: bool = False,
) -> None:
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
    if persistence_pending:
        state.defer_persistence()


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


def _set_stage2_record_snapshot(
    state: PipelineState,
    record: Any,
    *,
    usage_calls: list[Any] | None = None,
) -> None:
    """Copy Stage-2 payload, usage, and route fields into pipeline state."""
    state.stage2_messages = list(record.stage2_messages)
    state.stage2_reply = record.stage2_response
    state.stage2_normalized_json = record.stage2_decision
    state.stage2_usage_calls = (
        list(usage_calls)
        if usage_calls is not None
        else _response_usage_calls(record.stage2_response)
    )
    state.stage2_usage = _response_usage(record.stage2_response)
    if not state.stage2_usage and state.stage2_usage_calls:
        state.stage2_usage = _usage_snapshot({"usage": state.stage2_usage_calls[-1]})
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


def _record_with_route_snapshot(
    state: PipelineState,
    *,
    strategy_files: list[str],
    experience_entries: list[Any],
    exception: dict[str, Any] | None = None,
) -> Any:
    """Build a partial record containing the completed Stage-1/route data."""
    if state.record is None or state.stage1_reply is None:
        return state.record
    updates: dict[str, Any] = {
        "stage1_messages": state.stage1_messages,
        "stage1_response": state.stage1_reply.raw,
        "stage1_diagnosis": state.stage1_normalized_json,
        "strategy_files_used": strategy_files,
        "experience_loaded": [
            entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)
            for entry in experience_entries
        ],
        "usage_total": state.usage_total,
    }
    if exception is not None:
        updates["exception"] = exception
    return state.record.model_copy(update=updates)


class LegacySubmitStep:
    """Run the unchanged ``TwoStageOrchestrator.submit`` implementation."""

    name = "legacy_submit"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Execute the legacy method and translate its terminal state."""
        if isinstance(services, TwoStageOrchestrator):
            submit = _LEGACY_SUBMIT
            submit_args = (services,)
        else:
            submit = services.submit
            submit_args = ()
        record = submit(
            *submit_args,
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
        _log(state, "preflight_start", pipeline_step=self.name)
        if state.record is None:
            state.record = _build_empty_record(state.frame, services._settings)

        if state.cancel_token.is_set():
            _log(state, "preflight_result", pipeline_step=self.name, pipeline_status="cancelled")
            state.partial_reason = "user_cancelled"
            state.emit(OrchestratorEvent.Cancelled)
            _set_terminal_from_record(
                state,
                state.record,
                persistence_pending=True,
            )
            return StepResult.fail(state)

        from pa_agent.ai.decision_nodes import check_preflight_data

        preflight = check_preflight_data(state.frame)
        _log(
            state,
            "preflight_result",
            pipeline_step=self.name,
            pipeline_status="passed" if preflight.ok else "insufficient_data",
        )
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
            state.partial_reason = "insufficient_data"
            state.emit(OrchestratorEvent.InsufficientData)
            _set_terminal_from_record(
                state,
                state.record,
                persistence_pending=True,
            )
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
            persist=False,
        )
        if not isinstance(result, tuple):
            _log(
                state,
                "stage_result",
                pipeline_step=self.name,
                pipeline_status="failed",
                pipeline_reason=state.partial_reason or "stage1_failed",
            )
            _set_stage1_record_snapshot(state, result)
            _set_terminal_from_record(
                state,
                result,
                persistence_pending=True,
            )
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
        _log(
            state,
            "stage_result",
            pipeline_step=self.name,
            pipeline_status="succeeded",
            pipeline_message_count=len(messages_s1),
            pipeline_usage_call_count=len(usage_calls),
        )
        return StepResult.continue_(state)


class RouteStep:
    """Route Stage 1 and load bounded experience entries without Qt."""

    name = "route"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Reuse the legacy route helper and expose its output in state."""
        _log(state, "route_start", pipeline_step=self.name)
        if state.record is None or state.stage1_reply is None:
            state.mark_terminal(TerminalStatus.STAGE1_FAILED)
            return StepResult.fail(state)

        stage1_json = state.stage1_normalized_json or {}
        try:
            strategy_files, experience_entries = services._route_and_load_experience(
                stage1_json,
                current_bars=state.frame.bars,
            )
            strategy_files = list(strategy_files)
            experience_entries = list(experience_entries)
        except Exception as exc:
            _log(
                state,
                "route_result",
                pipeline_step=self.name,
                pipeline_status="failed",
                pipeline_exception_type=type(exc).__name__,
            )
            state.partial_reason = "route_failed"
            state.set_persistence_intent("partial")
            state.record = _record_with_route_snapshot(
                state,
                strategy_files=[],
                experience_entries=[],
                exception={
                    "type": "route_error",
                    "stage": "route",
                    "message": str(exc) or type(exc).__name__,
                },
            )
            _set_terminal_from_record(
                state,
                state.record,
                persistence_pending=True,
            )
            return StepResult.fail(state)

        state.set_route_outputs(
            strategy_files=strategy_files,
            experience_entries=experience_entries,
        )
        _log(
            state,
            "route_result",
            pipeline_step=self.name,
            pipeline_status="succeeded",
            pipeline_strategy_file_count=len(strategy_files),
            pipeline_experience_entry_count=len(experience_entries),
        )

        if state.cancel_token.is_set():
            _log(state, "route_cancelled", pipeline_step=self.name)
            state.record = _record_with_route_snapshot(
                state,
                strategy_files=strategy_files,
                experience_entries=experience_entries,
            )
            state.partial_reason = "user_cancelled"
            state.emit(OrchestratorEvent.Cancelled)
            _set_stage1_record_snapshot(state, state.record, preserve_usage_calls=True)
            _set_terminal_from_record(
                state,
                state.record,
                persistence_pending=True,
            )
            return StepResult.fail(state)

        return StepResult.continue_(state)


class Stage2Step:
    """Execute Stage 2 while leaving record persistence to PersistStep."""

    name = "stage2"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Build, call, validate, and snapshot Stage 2 without Qt dependencies."""
        _log(state, "stage2_start", pipeline_step=self.name)
        if state.record is None or state.stage1_reply is None:
            state.mark_terminal(TerminalStatus.STAGE1_FAILED)
            return StepResult.fail(state)

        stage1_json = state.stage1_normalized_json or {}
        messages_s1 = state.stage1_messages
        reply_s1 = state.stage1_reply
        strategy_files = list(state.strategy_files)
        experience_entries = list(state.experience_entries)

        state.emit(OrchestratorEvent.Stage2Started)
        if state.on_stage2_files is not None:
            state.on_stage2_files(list(strategy_files))

        enable_next_bar, flip_cooldown = services._stage2_feature_flags()
        state.stage2_enable_next_bar_prediction = enable_next_bar
        state.stage2_structure_flip_cooldown_bars = flip_cooldown
        state.feature_metadata.update(
            {
                "enable_next_bar_prediction": enable_next_bar,
                "structure_flip_cooldown_bars": flip_cooldown,
            }
        )
        _log(
            state,
            "stage2_flags",
            pipeline_step=self.name,
            pipeline_enable_next_bar=enable_next_bar,
            pipeline_structure_flip_cooldown_bars=flip_cooldown,
        )

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
            persist=False,
        )
        if gate_record is not None:
            _log(
                state,
                "stage2_gate",
                pipeline_step=self.name,
                pipeline_status="short_circuit",
            )
            state.record = gate_record
            _set_stage1_record_snapshot(state, gate_record, preserve_usage_calls=True)
            _set_stage2_record_snapshot(state, gate_record)
            return StepResult.continue_(state)

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
        s2_usage_calls: list[Any] = []
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
            persist=False,
            s2_usage_calls_out=s2_usage_calls,
        )
        _log(
            state,
            "stage2_result",
            pipeline_step=self.name,
            pipeline_status=(
                "cancelled"
                if OrchestratorEvent.Cancelled in state.events
                else "failed"
                if OrchestratorEvent.Stage2Failed in state.events
                else "succeeded"
            ),
            pipeline_usage_call_count=len(s2_usage_calls),
        )
        _set_stage1_record_snapshot(state, state.record, preserve_usage_calls=True)
        _set_stage2_record_snapshot(state, state.record, usage_calls=s2_usage_calls)
        if (
            OrchestratorEvent.Stage2Failed in state.events
            or OrchestratorEvent.Cancelled in state.events
        ):
            _set_terminal_from_record(
                state,
                state.record,
                persistence_pending=True,
            )
            return StepResult.fail(state)
        return StepResult.continue_(state)


class PersistStep:
    """Assemble and persist the terminal record for the opt-in pipeline."""

    name = "persist"
    is_persistence_step = True

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Write exactly one full or partial record and finish the pipeline."""
        _log(
            state,
            "persist_start",
            pipeline_step=self.name,
            pipeline_intent=state.persistence_intent.value,
        )
        if state.record is None:
            state.partial_reason = state.partial_reason or "persist_failed"
            state.set_persistence_intent(PersistenceIntent.PARTIAL)
            state.persistence_pending = False
            if state.terminal_status is TerminalStatus.RUNNING:
                state.mark_terminal(TerminalStatus.PERSIST_FAILED)
            return StepResult.fail(state)

        is_full = (
            state.terminal_status is TerminalStatus.RUNNING
            and state.partial_reason is None
            and state.record.exception is None
        )
        writer = services._pending_writer
        if is_full:
            record = _assemble_pipeline_record(state, full=True)
            state.record = record
            state.set_persistence_intent(PersistenceIntent.FULL)
            try:
                result = writer.save_full(record)
            except OSError as exc:
                _log(
                    state,
                    "persist_write",
                    pipeline_step=self.name,
                    pipeline_write_kind="full",
                    pipeline_write_status="error",
                    pipeline_exception_type=type(exc).__name__,
                )
                state.persistence_error = True
                state.partial_reason = "disk_error"
                state.set_persistence_intent(PersistenceIntent.PARTIAL)
                state.record = record.model_copy(
                    update={
                        "exception": {
                            "type": "persist_error",
                            "stage": "persist",
                        }
                    }
                )
                state.persistence_pending = False
                state.mark_terminal(TerminalStatus.PERSIST_FAILED)
                return StepResult.fail(state)
            if not _write_succeeded(writer, result):
                _log(
                    state,
                    "persist_write",
                    pipeline_step=self.name,
                    pipeline_write_kind="full",
                    pipeline_write_status="failed",
                )
                state.persistence_error = True
                state.partial_reason = "disk_error"
                state.set_persistence_intent(PersistenceIntent.PARTIAL)
                state.record = record.model_copy(
                    update={
                        "exception": {
                            "type": "persist_error",
                            "stage": "persist",
                        }
                    }
                )
                state.persistence_pending = False
                state.mark_terminal(TerminalStatus.PERSIST_FAILED)
                return StepResult.fail(state)
            state.persistence_pending = False
            _log(
                state,
                "persist_write",
                pipeline_step=self.name,
                pipeline_write_kind="full",
                pipeline_write_status="succeeded",
            )
            state.emit(OrchestratorEvent.RecordSaved)
            state.mark_terminal(TerminalStatus.COMPLETED)
            return StepResult.complete(state)

        reason = _partial_reason(state)
        record = _assemble_pipeline_record(state, full=False)
        state.record = record
        state.set_persistence_intent(PersistenceIntent.PARTIAL)
        try:
            result = writer.save_partial(record, reason)
        except OSError as exc:
            _log(
                state,
                "persist_write",
                pipeline_step=self.name,
                pipeline_write_kind="partial",
                pipeline_write_status="error",
                pipeline_exception_type=type(exc).__name__,
            )
            state.persistence_error = True
            state.persistence_pending = False
            return StepResult.fail(state)
        state.persistence_pending = False
        if not _write_succeeded(writer, result):
            _log(
                state,
                "persist_write",
                pipeline_step=self.name,
                pipeline_write_kind="partial",
                pipeline_write_status="failed",
            )
            state.persistence_error = True
            return StepResult.fail(state)
        _log(
            state,
            "persist_write",
            pipeline_step=self.name,
            pipeline_write_kind="partial",
            pipeline_write_status="succeeded",
        )
        return StepResult.complete(state)


def _write_succeeded(writer: Any, result: Any) -> bool:
    """Read optional writer status without constraining compatibility fakes."""
    if isinstance(result, bool):
        return result
    status = getattr(writer, "last_write_succeeded", None)
    return status if isinstance(status, bool) else True


def _partial_reason(state: PipelineState) -> str:
    """Return the stable reason expected by PendingWriter.save_partial()."""
    if state.partial_reason:
        return state.partial_reason
    state.update_terminal_metadata(state.record)
    return state.partial_reason or "failed"


class LegacyPersistStep(PersistStep):
    """Compatibility name for callers that still refer to the old tail."""

    name = "legacy_persist"


class LegacyStage2PersistStep:
    """Compatibility composite for callers using the pre-Task-8 name."""

    name = "legacy_stage2_persist"

    def run(self, state: PipelineState, services: Any) -> StepResult:
        """Run the new Stage2 boundary followed by the legacy writer."""
        result = Stage2Step().run(state, services)
        if result.outcome is not StepOutcome.CONTINUE and not state.persistence_pending:
            return result
        return PersistStep().run(state, services)


# Keep the old internal name importable while the opt-in history uses the
# explicit boundary between Route and the legacy Stage-2/persistence tail.
LegacyPostStage1Step = LegacyStage2PersistStep
