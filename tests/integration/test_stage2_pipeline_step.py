"""Focused integration coverage for the opt-in PyQt-free Stage2Step."""

from __future__ import annotations

import copy
import json
from unittest.mock import MagicMock

from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import Settings
from pa_agent.orchestrator.pipeline import PersistenceIntent, TerminalStatus
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply


def _assembler() -> MagicMock:
    assembler = MagicMock()
    assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
    assembler.build_stage2_continuation.return_value = [
        {"role": "system", "content": "stage2"},
        {"role": "user", "content": "continuation"},
    ]
    return assembler


def _orchestrator(
    client: MagicMock,
    *,
    assembler: MagicMock | None = None,
    settings: Settings | None = None,
    pending_writer: MagicMock | None = None,
) -> TwoStageOrchestrator:
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=assembler or _assembler(),
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer or MagicMock(),
        exp_reader=exp_reader,
        settings=settings,
    )


def _text_reply(text: str) -> MagicMock:
    reply = MagicMock()
    reply.content = text
    reply.reasoning_content = ""
    reply.raw = {"content": text}
    reply.usage = MagicMock(
        prompt_tokens=100,
        cached_prompt_tokens=0,
        completion_tokens=50,
        total_tokens=150,
    )
    reply.latency_ms = 1.0
    return reply


def _record_without_runtime_timestamp(record) -> dict:
    payload = copy.deepcopy(record.model_dump())
    payload["meta"].pop("timestamp_local_iso", None)
    payload["meta"].pop("timestamp_local_ms", None)
    return payload


def test_stage2_continuation_bytes_and_settings_flags_are_preserved(frame) -> None:
    settings = Settings(
        general={
            "enable_next_bar_prediction": True,
            "structure_flip_cooldown_bars": 7,
        }
    )

    legacy_assembler = _assembler()
    legacy_client = MagicMock()
    legacy_client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    legacy = _orchestrator(
        legacy_client,
        assembler=legacy_assembler,
        settings=settings,
    )
    legacy.submit(frame, CancelToken(), lambda _event: None)

    pipeline_assembler = _assembler()
    pipeline_client = MagicMock()
    pipeline_client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    pipeline = _orchestrator(
        pipeline_client,
        assembler=pipeline_assembler,
        settings=settings,
    )
    state = pipeline.run_pipeline(frame, CancelToken(), lambda _event: None)

    legacy_messages = legacy_assembler.build_stage2_continuation.return_value
    pipeline_messages = pipeline_assembler.build_stage2_continuation.return_value
    assert legacy_assembler.build_stage2_continuation.call_args.kwargs == (
        pipeline_assembler.build_stage2_continuation.call_args.kwargs
    )
    assert json.dumps(
        legacy_messages,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    ) == json.dumps(pipeline_messages, ensure_ascii=False, separators=(",", ":"),).encode("utf-8")
    assert state.stage2_messages[: len(pipeline_messages)] == pipeline_messages
    assert state.stage2_enable_next_bar_prediction is True
    assert state.stage2_structure_flip_cooldown_bars == 7
    assert state.feature_metadata == {
        "enable_next_bar_prediction": True,
        "structure_flip_cooldown_bars": 7,
    }


def test_stage2_pipeline_event_order_and_state_payload(frame) -> None:
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, CancelToken(), events.append)

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.persistence_intent is PersistenceIntent.FULL
    assert state.step_history == ["stage1", "route", "stage2", "persist"]
    assert state.stage2_normalized_json == state.record.stage2_decision
    assert state.stage2_reply == state.record.stage2_response
    assert state.stage2_usage == {
        "prompt_tokens": 100,
        "cached_prompt_tokens": 0,
        "completion_tokens": 50,
        "total_tokens": 150,
    }
    assert len(state.stage2_usage_calls) == 1
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Done,
        OrchestratorEvent.RecordSaved,
    ]
    pending_writer.save_full.assert_called_once_with(state.record)
    pending_writer.save_partial.assert_not_called()


def test_stage2_streaming_callbacks_receive_buffered_reasoning_and_content(frame) -> None:
    stage2_reply = make_reply(VALID_STAGE2)
    stage2_reply.reasoning_content = "stage2 reasoning"
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        stage2_reply,
    ]
    orchestrator = _orchestrator(client)
    reasoning: list[str] = []
    content: list[str] = []

    state = orchestrator.run_pipeline(
        frame,
        CancelToken(),
        lambda _event: None,
        on_stage2_reasoning=reasoning.append,
        on_stage2_content=content.append,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert "".join(reasoning) == stage2_reply.reasoning_content
    assert "".join(content) == stage2_reply.content


def test_stage2_gate_short_circuit_is_persisted_by_legacy_tail(frame) -> None:
    stage1_wait = copy.deepcopy(VALID_STAGE1)
    stage1_wait["gate_result"] = "wait"
    stage1_wait["gate_trace"] = [
        {
            "node_id": "1.2",
            "question": "是否能识别市场周期?",
            "answer": "否",
            "action": "等待",
            "reason": "无法识别周期",
            "bar_range": "K5-K1",
        }
    ]
    stage1_wait["cycle_position"] = "unknown"
    client = MagicMock()
    client.stream_chat.return_value = make_reply(stage1_wait)
    pending_writer = MagicMock()
    assembler = _assembler()
    orchestrator = _orchestrator(
        client,
        assembler=assembler,
        pending_writer=pending_writer,
    )
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, CancelToken(), events.append)

    assert client.stream_chat.call_count == 1
    assembler.build_stage2_continuation.assert_not_called()
    assert state.stage2_messages == []
    assert state.stage2_reply is None
    assert state.stage2_normalized_json["gate_shortcircuited"] is True
    assert state.record.stage2_decision == state.stage2_normalized_json
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Done,
        OrchestratorEvent.RecordSaved,
    ]
    pending_writer.save_full.assert_called_once_with(state.record)


def test_stage2_retry_preserves_messages_usage_and_event_order(frame) -> None:
    bad_stage2 = copy.deepcopy(VALID_STAGE2)
    bad_stage2.pop("terminal")
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(bad_stage2),
        make_reply(VALID_STAGE2),
    ]
    settings = Settings(validation={"retry_max": 1})
    orchestrator = _orchestrator(client, settings=settings)
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, CancelToken(), events.append)

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.stage2_normalized_json is not None
    assert client.stream_chat.call_count == 3
    assert len(state.stage2_usage_calls) == 2
    assert len(state.stage2_messages) == 5
    assert state.stage2_messages[-3]["role"] == "assistant"
    assert state.stage2_messages[-2]["role"] == "user"
    assert state.stage2_messages[-1]["role"] == "assistant"
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Retry,
        OrchestratorEvent.Stage2Done,
        OrchestratorEvent.RecordSaved,
    ]


def test_stage2_network_failure_is_partial_and_persisted_once(frame) -> None:
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        ConnectionResetError("connection reset"),
    ]
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, CancelToken(), events.append)

    assert state.terminal_status is TerminalStatus.STAGE2_FAILED
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.partial_reason == "network_error"
    assert state.record.stage2_messages
    assert state.record.stage2_response is None
    assert state.step_history == ["stage1", "route", "stage2", "persist"]
    assert state.persistence_pending is False
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Failed,
    ]
    pending_writer.save_partial.assert_called_once_with(
        state.record,
        "network_error",
    )
    pending_writer.save_full.assert_not_called()


def test_stage2_validation_failure_is_partial_and_keeps_payload(frame) -> None:
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        _text_reply("not json"),
    ]
    settings = Settings(validation={"retry_enabled": False})
    pending_writer = MagicMock()
    orchestrator = _orchestrator(
        client,
        settings=settings,
        pending_writer=pending_writer,
    )
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, CancelToken(), events.append)

    assert state.terminal_status is TerminalStatus.STAGE2_FAILED
    assert state.partial_reason == "stage2_d"
    assert state.stage2_messages
    assert state.stage2_reply == state.record.stage2_response
    assert state.stage2_normalized_json is None
    assert state.record.exception["type"] == "validation_error"
    assert events[-1] is OrchestratorEvent.Stage2Failed
    pending_writer.save_partial.assert_called_once()
    assert pending_writer.save_partial.call_args.args[1] == "stage2_d"
    pending_writer.save_full.assert_not_called()


def test_stage2_post_call_cancel_preserves_reply_and_persists_partial_once(frame) -> None:
    cancel_token = CancelToken()
    call_number = 0

    def chat_side_effect(_messages, **_kwargs):
        nonlocal call_number
        call_number += 1
        if call_number == 2:
            cancel_token.set()
            return make_reply(VALID_STAGE2)
        return make_reply(VALID_STAGE1)

    client = MagicMock()
    client.stream_chat.side_effect = chat_side_effect
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(frame, cancel_token, events.append)

    assert state.terminal_status is TerminalStatus.CANCELLED
    assert state.partial_reason == "user_cancelled"
    assert state.stage2_reply == state.record.stage2_response
    assert state.stage2_normalized_json is None
    assert state.step_history == ["stage1", "route", "stage2", "persist"]
    assert state.persistence_pending is False
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Cancelled,
    ]
    pending_writer.save_partial.assert_called_once_with(
        state.record,
        "user_cancelled",
    )
    pending_writer.save_full.assert_not_called()


def test_stage2_partial_record_matches_legacy_submit(frame) -> None:
    settings = Settings(validation={"retry_enabled": False})
    legacy_client = MagicMock()
    legacy_client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        _text_reply("not json"),
    ]
    legacy_events: list[OrchestratorEvent] = []
    legacy = _orchestrator(legacy_client, settings=settings)
    legacy_record = legacy.submit(frame, CancelToken(), legacy_events.append)

    pipeline_client = MagicMock()
    pipeline_client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        _text_reply("not json"),
    ]
    pipeline_events: list[OrchestratorEvent] = []
    pipeline = _orchestrator(pipeline_client, settings=settings)
    state = pipeline.run_pipeline(frame, CancelToken(), pipeline_events.append)

    assert state.terminal_status is TerminalStatus.STAGE2_FAILED
    assert pipeline_events == legacy_events
    assert state.record is not None
    assert _record_without_runtime_timestamp(state.record) == (
        _record_without_runtime_timestamp(legacy_record)
    )
