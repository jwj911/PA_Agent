"""Tests for the PyQt-free L3 pipeline state and step contracts."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from pa_agent.orchestrator.pipeline import (
    PersistenceIntent,
    PipelineBuilder,
    PipelineState,
    StepResult,
    TerminalStatus,
    terminal_status_for,
)
from pa_agent.orchestrator.pipeline.steps import LegacySubmitStep
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.records.schema import AnalysisRecord, RecordMeta
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


class _RaiseStep:
    name = "raise"

    def run(self, _state: PipelineState, _services: object) -> StepResult:
        raise ValueError("PRIVATE_EXCEPTION_TEXT")


class _InvalidResultStep:
    name = "invalid"

    def run(self, _state: PipelineState, _services: object) -> object:
        return object()


class _TerminalPendingStep:
    name = "terminal_pending"

    def run(self, state: PipelineState, _services: object) -> StepResult:
        state.mark_terminal(TerminalStatus.CANCELLED)
        state.defer_persistence()
        return StepResult.fail(state)


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


def test_pipeline_builder_logs_ordered_safe_lifecycle(caplog) -> None:
    state = _state()
    state.stage1_messages = [{"role": "user", "content": "PRIVATE_PROMPT"}]
    state.stage1_reply = SimpleNamespace(content="PRIVATE_REPLY", raw="PRIVATE_RAW")
    state.settings_metadata = {"provider": {"api_key": "PRIVATE_KEY"}}

    with caplog.at_level(logging.INFO, logger="pa_agent.orchestrator.pipeline.builder"):
        result = PipelineBuilder((_ContinueStep(), _CompleteStep())).run(
            state,
            services=object(),
        )

    records = [record for record in caplog.records if record.name.endswith("pipeline.builder")]
    assert [record.pipeline_event for record in records] == [
        "start",
        "step_start",
        "step_result",
        "step_start",
        "step_result",
        "terminal",
        "end",
    ]
    assert {record.trace_id for record in records} == {result.trace_id}
    assert all(record.pipeline_elapsed_ms >= 0 for record in records if hasattr(record, "pipeline_elapsed_ms"))
    rendered = "\n".join(record.getMessage() + repr(record.__dict__) for record in records)
    assert "PRIVATE_PROMPT" not in rendered
    assert "PRIVATE_REPLY" not in rendered
    assert "PRIVATE_RAW" not in rendered
    assert "PRIVATE_KEY" not in rendered


@pytest.mark.parametrize(
    ("step", "exception_type"),
    [
        (_RaiseStep(), "ValueError"),
        (_InvalidResultStep(), "PipelineExecutionError"),
    ],
)
def test_pipeline_builder_logs_step_errors_and_always_ends(
    caplog,
    step,
    exception_type,
) -> None:
    state = _state()

    with (
        caplog.at_level(logging.INFO, logger="pa_agent.orchestrator.pipeline.builder"),
        pytest.raises((ValueError, RuntimeError)),
    ):
        PipelineBuilder((step,)).run(state, services=object())

    records = [record for record in caplog.records if record.name.endswith("pipeline.builder")]
    assert [record.pipeline_event for record in records] == [
        "start",
        "step_start",
        "step_error",
        "end",
    ]
    assert records[2].pipeline_exception_type == exception_type
    assert records[-1].pipeline_exception_type == exception_type
    assert {record.trace_id for record in records} == {state.trace_id}
    rendered = "\n".join(record.getMessage() + repr(record.__dict__) for record in records)
    assert "PRIVATE_EXCEPTION_TEXT" not in rendered


def test_pipeline_state_logs_safe_orchestrator_events(caplog) -> None:
    state = _state()
    state.step_history.append("stage1")
    state.stage1_messages = [{"role": "user", "content": "PRIVATE_PROMPT"}]
    state.stage1_reply = SimpleNamespace(content="PRIVATE_REPLY", raw="PRIVATE_RAW")

    with caplog.at_level(logging.INFO, logger="pa_agent.orchestrator.pipeline.state"):
        state.emit(OrchestratorEvent.Stage1Retry)
        state.emit(OrchestratorEvent.Cancelled)

    records = [
        record
        for record in caplog.records
        if record.name.endswith("pipeline.state") and record.pipeline_event == "orchestrator_event"
    ]
    assert [record.pipeline_orchestrator_event for record in records] == [
        "Stage1Retry",
        "Cancelled",
    ]
    assert {record.trace_id for record in records} == {state.trace_id}
    assert {record.pipeline_current_step for record in records} == {"stage1"}
    assert {record.pipeline_terminal_status for record in records} == {"running"}
    rendered = "\n".join(record.getMessage() + repr(record.__dict__) for record in records)
    assert "PRIVATE_PROMPT" not in rendered
    assert "PRIVATE_REPLY" not in rendered
    assert "PRIVATE_RAW" not in rendered


def test_pipeline_builder_logs_terminal_step_skip(caplog) -> None:
    state = _state()
    state.stage1_messages = [{"role": "user", "content": "PRIVATE_PROMPT"}]

    with caplog.at_level(logging.INFO, logger="pa_agent.orchestrator.pipeline.builder"):
        result = PipelineBuilder((_TerminalPendingStep(), _ContinueStep())).run(
            state,
            services=object(),
        )

    records = [record for record in caplog.records if record.name.endswith("pipeline.builder")]
    skip = next(record for record in records if record.pipeline_event == "step_skip")
    assert skip.pipeline_step == "continue"
    assert skip.pipeline_skip_reason == "terminal_state"
    assert skip.pipeline_terminal_status == "cancelled"
    assert skip.trace_id == result.trace_id
    rendered = "\n".join(record.getMessage() + repr(record.__dict__) for record in records)
    assert "PRIVATE_PROMPT" not in rendered


def test_pipeline_builder_without_steps_is_explicit_failure() -> None:
    result = PipelineBuilder(()).run(_state(), services=object())

    assert result.terminal_status is TerminalStatus.FAILED


def test_pipeline_state_rejects_terminal_status_rewrite() -> None:
    state = _state()
    state.mark_terminal("cancelled")

    with pytest.raises(ValueError, match="already terminated"):
        state.mark_terminal(TerminalStatus.COMPLETED)


def test_pipeline_state_normalizes_enum_constructor_inputs() -> None:
    state = PipelineState(
        frame=object(),
        cancel_token=CancelToken(),
        terminal_status="running",
        persistence_intent="partial",
    )

    assert state.terminal_status is TerminalStatus.RUNNING
    assert state.persistence_intent is PersistenceIntent.PARTIAL


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


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        ({"stage": "route", "type": "route_error"}, TerminalStatus.ROUTE_FAILED),
        ({"stage": "routing", "type": "program_error"}, TerminalStatus.ROUTE_FAILED),
        ({"stage": "persist", "type": "persist_error"}, TerminalStatus.PERSIST_FAILED),
        ({"stage": "persistence", "type": "program_error"}, TerminalStatus.PERSIST_FAILED),
    ],
)
def test_terminal_status_maps_route_and_persist_failures(
    exception: dict[str, str],
    expected: TerminalStatus,
) -> None:
    assert terminal_status_for(SimpleNamespace(exception=exception), []) is expected


def test_pipeline_state_carries_stage_route_and_persistence_runtime_data() -> None:
    state = PipelineState(frame=object(), cancel_token=CancelToken())

    state.stage1_messages = [{"role": "user", "content": "stage 1 prompt"}]
    state.stage1_reply = SimpleNamespace(content="stage 1 reply", raw={"secret": "reply"})
    state.stage1_normalized_json = {"direction": "up"}
    state.stage1_usage = {"prompt_tokens": 10, "completion_tokens": 4}
    state.stage2_messages = [{"role": "system", "content": "stage 2 prompt"}]
    state.stage2_reply = SimpleNamespace(content="stage 2 reply", raw={"secret": "reply"})
    state.stage2_normalized_json = {"decision": "wait"}
    state.stage2_usage = {"prompt_tokens": 20, "completion_tokens": 5}
    state.set_route_outputs(
        strategy_files=["strategy.txt"],
        experience_entries=[{"filename": "experience.json"}],
    )
    state.partial_reason = "user_cancelled"
    state.set_persistence_intent(PersistenceIntent.PARTIAL)

    assert state.stage1_messages[0]["content"] == "stage 1 prompt"
    assert state.stage1_reply.content == "stage 1 reply"
    assert state.stage1_normalized_json == {"direction": "up"}
    assert state.stage2_usage["completion_tokens"] == 5
    assert state.route_outputs["strategy_files"] == ["strategy.txt"]
    assert state.persistence_intent is PersistenceIntent.PARTIAL


def test_pipeline_state_safe_serialization_excludes_runtime_payloads() -> None:
    prompt = "private prompt body"
    market_value = "private market data"
    api_key = "sk-private-api-key"
    state = PipelineState(
        frame=SimpleNamespace(symbol="SECRET-SYMBOL", bars=[market_value]),
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
        stage1_messages=[{"role": "user", "content": prompt}],
        stage1_reply=SimpleNamespace(
            content="private provider reply",
            raw={"content": "private raw response"},
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
        ),
        stage1_normalized_json={"entry_price": market_value},
        stage1_usage={"prompt_tokens": 3, "completion_tokens": 2},
        settings_metadata={
            "provider": {
                "model": "test-model",
                "base_url": "https://provider.test",
                "api_key": api_key,
                "client": object(),
            },
        },
        feature_metadata={"enable_next_bar_prediction": True},
    )
    state.partial_reason = "persist_failed"
    state.set_persistence_intent("partial")

    summary = state.safe_summary()
    serialized = state.to_safe_json()

    assert summary["stage1"] == {
        "message_count": 1,
        "message_roles": ["user"],
        "reply": {
            "present": True,
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        },
        "normalized_json_present": True,
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        "usage_call_count": 0,
    }
    assert summary["settings"] == {
        "provider": {
            "model": "test-model",
            "base_url": "https://provider.test",
        }
    }
    assert summary["features"] == {"enable_next_bar_prediction": True}
    assert summary["partial_reason"] == "persist_failed"
    assert prompt not in serialized
    assert market_value not in serialized
    assert api_key not in serialized
    assert "private provider reply" not in serialized
    assert "private raw response" not in serialized
    assert "SECRET-SYMBOL" not in serialized


def test_safe_summary_reads_usage_from_legacy_raw_response_and_redacts_url_path() -> None:
    state = PipelineState(
        frame=object(),
        cancel_token=CancelToken(),
        stage1_reply={"usage": {"prompt_tokens": 7}},
        settings_metadata={
            "provider": {
                "base_url": "https://provider.test/sk-provider-secret/v1",
            },
        },
    )

    summary = state.safe_summary()

    assert summary["stage1"]["reply"]["usage"] == {"prompt_tokens": 7}
    assert summary["settings"] == {"provider": {"base_url": "https://provider.test"}}
    assert "sk-provider-secret" not in state.to_safe_json()


def test_legacy_submit_step_recovers_final_usage_call_snapshots() -> None:
    record = AnalysisRecord(
        meta=RecordMeta(
            timestamp_local_iso="2026-07-22T00:00:00.000",
            timestamp_local_ms=1,
            symbol="TEST",
            timeframe="1m",
            bar_count=1,
            ai_provider={},
        ),
        kline_data=[],
        htf_text="",
        stage1_messages=[{"role": "user", "content": "stage1"}],
        stage1_response={"usage": {"prompt_tokens": 10, "total_tokens": 12}},
        stage1_diagnosis={"gate_result": "proceed"},
        stage2_messages=[{"role": "user", "content": "stage2"}],
        stage2_response={"usage": {"prompt_tokens": 20, "total_tokens": 23}},
        stage2_decision={"decision": {"order_type": "不下单"}},
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={"prompt_tokens": 30, "total_tokens": 35},
    )

    class _Services:
        def submit(self, **_kwargs: object) -> AnalysisRecord:
            return record

    state = _state()
    result = LegacySubmitStep().run(state, _Services())

    assert result.state is state
    assert state.stage1_usage_calls == [{"prompt_tokens": 10, "total_tokens": 12}]
    assert state.stage2_usage_calls == [{"prompt_tokens": 20, "total_tokens": 23}]
    assert state.usage_total == {"prompt_tokens": 30, "total_tokens": 35}


def test_legacy_submit_step_bypasses_rollout_facade_for_orchestrator(monkeypatch) -> None:
    """The compatibility step must not re-enter the flag wrapper."""
    record = AnalysisRecord(
        meta=RecordMeta(
            timestamp_local_iso="2026-07-22T00:00:00.000",
            timestamp_local_ms=1,
            symbol="TEST",
            timeframe="1m",
            bar_count=1,
            ai_provider={},
        ),
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis={},
        stage2_messages=[],
        stage2_response=None,
        stage2_decision={},
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )
    calls: list[object] = []

    def legacy_submit(_services, **_kwargs):
        calls.append(_services)
        return record

    monkeypatch.setattr(
        "pa_agent.orchestrator.pipeline.steps._LEGACY_SUBMIT",
        legacy_submit,
    )
    services = TwoStageOrchestrator.__new__(TwoStageOrchestrator)

    result = LegacySubmitStep().run(_state(), services)

    assert result.state.record is record
    assert calls == [services]
