"""Focused integration coverage for the opt-in PyQt-free Stage1Step."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest

from pa_agent.ai.router import route_strategy_files
from pa_agent.orchestrator.pipeline import PersistenceIntent, TerminalStatus
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply


def _orchestrator(
    client: MagicMock,
    assembler: MagicMock | None = None,
    *,
    pending_writer: MagicMock | None = None,
):
    if assembler is None:
        assembler = MagicMock()
        assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
        assembler.build_incremental_stage1.return_value = [
            {"role": "system", "content": "incremental stage1"}
        ]
        assembler.build_stage2_continuation.return_value = [{"role": "system", "content": "stage2"}]
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=assembler,
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer or MagicMock(),
        exp_reader=exp_reader,
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
    return reply


def test_stage1_pipeline_happy_path_snapshots_callbacks_and_usage(frame) -> None:
    stage1_reply = make_reply(VALID_STAGE1)
    stage1_reply.reasoning_content = "stage1 reasoning"
    stage2_reply = make_reply(VALID_STAGE2)
    client = MagicMock()
    client.stream_chat.side_effect = [stage1_reply, stage2_reply]
    orchestrator = _orchestrator(client)

    events = []
    reasoning: list[str] = []
    content: list[str] = []
    prompts: list[tuple[str, str, str]] = []
    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=events.append,
        on_stage1_reasoning=reasoning.append,
        on_stage1_content=content.append,
        on_stage_prompt=lambda stage, system, user: prompts.append((stage, system, user)),
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.persistence_intent is PersistenceIntent.FULL
    assert state.stage1_normalized_json == state.record.stage1_diagnosis
    assert state.stage1_normalized_json is not None
    assert state.stage1_messages
    assert state.stage1_usage == {
        "prompt_tokens": 100,
        "cached_prompt_tokens": 0,
        "completion_tokens": 50,
        "total_tokens": 150,
    }
    assert len(state.stage1_usage_calls) == 1
    assert "".join(reasoning) == stage1_reply.reasoning_content
    assert "".join(content) == stage1_reply.content
    assert prompts[0][0] == "stage1"
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Done,
        OrchestratorEvent.RecordSaved,
    ]


def test_stage1_pipeline_retries_validation_and_preserves_call_history(frame) -> None:
    bad_stage1 = copy.deepcopy(VALID_STAGE1)
    bad_stage1.pop("cycle_position")
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(bad_stage1),
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    orchestrator = _orchestrator(client)
    events = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert events[:3] == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Retry,
        OrchestratorEvent.Stage1Done,
    ]
    assert client.stream_chat.call_count == 3
    assert len(state.stage1_usage_calls) == 2
    assert len(state.stage1_messages) == 4
    assert state.stage1_messages[-1]["role"] == "assistant"


def test_stage1_pipeline_network_error_is_explicit_partial_terminal(frame) -> None:
    httpx = pytest.importorskip("httpx")
    client = MagicMock()
    client.stream_chat.side_effect = httpx.ReadError("connection reset")
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.STAGE1_FAILED
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.partial_reason == "network_error"
    assert state.record is not None
    assert state.record.exception["type"] == "network_error"
    assert state.step_history == ["stage1", "persist"]
    pending_writer.save_partial.assert_called_once_with(state.record, "network_error")
    pending_writer.save_full.assert_not_called()
    assert events == [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Failed]


def test_stage1_pipeline_validation_failure_stops_before_stage2(frame) -> None:
    client = MagicMock()
    client.stream_chat.return_value = _text_reply("not json")
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.STAGE1_FAILED
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.partial_reason == "stage1_d"
    assert state.record is not None
    assert state.record.exception["type"] == "validation_error"
    assert OrchestratorEvent.Stage2Started not in events
    assert state.stage2_messages == []
    assert state.step_history == ["stage1", "persist"]
    pending_writer.save_partial.assert_called_once_with(state.record, "stage1_d")
    pending_writer.save_full.assert_not_called()


def test_stage1_pipeline_post_call_cancel_preserves_partial_state(frame) -> None:
    cancel_token = CancelToken()
    stage1_reply = make_reply(VALID_STAGE1)

    def return_and_cancel(_messages, **_kwargs):
        cancel_token.set()
        return stage1_reply

    client = MagicMock()
    client.stream_chat.side_effect = return_and_cancel
    pending_writer = MagicMock()
    orchestrator = _orchestrator(client, pending_writer=pending_writer)
    events = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=cancel_token,
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.CANCELLED
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.partial_reason == "user_cancelled"
    assert state.stage1_messages
    assert state.stage1_reply == stage1_reply.raw
    assert state.step_history == ["stage1", "persist"]
    pending_writer.save_partial.assert_called_once_with(state.record, "user_cancelled")
    pending_writer.save_full.assert_not_called()
    assert events == [OrchestratorEvent.Stage1Started, OrchestratorEvent.Cancelled]


def test_stage1_pipeline_uses_incremental_prompt_context(frame) -> None:
    previous_record = MagicMock()
    previous_record.stage1_diagnosis = copy.deepcopy(VALID_STAGE1)
    client = MagicMock()
    client.stream_chat.side_effect = [make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)]
    assembler = MagicMock()
    assembler.build_incremental_stage1.return_value = [
        {"role": "system", "content": "incremental stage1"}
    ]
    assembler.build_stage2_continuation.return_value = [{"role": "system", "content": "stage2"}]
    orchestrator = _orchestrator(client, assembler)

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
        previous_record=previous_record,
        incremental_new_bar_count=2,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assembler.build_incremental_stage1.assert_called_once_with(
        frame,
        previous_record,
        2,
        analysis_mode="original",
        provider_settings=None,
    )
    assembler.build_stage1.assert_not_called()
    assert state.incremental_new_bar_count == 2
    assert state.stage1_normalized_json == state.record.stage1_diagnosis
    assert state.stage1_normalized_json is not None
