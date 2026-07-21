"""Focused integration coverage for the opt-in PyQt-free PersistStep."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import Settings
from pa_agent.orchestrator.pipeline import PersistenceIntent, TerminalStatus
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply


def _orchestrator(
    client: MagicMock,
    pending_writer: MagicMock,
    *,
    settings: Settings | None = None,
) -> TwoStageOrchestrator:
    assembler = MagicMock()
    assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
    assembler.build_stage2_continuation.return_value = [
        {"role": "system", "content": "stage2"},
    ]
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=assembler,
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer,
        exp_reader=exp_reader,
        settings=settings,
    )


def _valid_client() -> MagicMock:
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    return client


def _invalid_reply() -> MagicMock:
    reply = MagicMock()
    reply.content = "not json"
    reply.reasoning_content = ""
    reply.raw = {"content": "not json"}
    reply.usage = MagicMock(
        prompt_tokens=100,
        cached_prompt_tokens=0,
        completion_tokens=50,
        total_tokens=150,
    )
    return reply


def test_persist_step_owns_full_write_and_record_saved_order(frame) -> None:
    pending_writer = MagicMock()
    events: list[OrchestratorEvent] = []

    state = _orchestrator(_valid_client(), pending_writer).run_pipeline(
        frame,
        CancelToken(),
        events.append,
    )

    assert state.step_history == ["stage1", "route", "stage2", "persist"]
    assert state.persistence_intent is PersistenceIntent.FULL
    assert state.persistence_pending is False
    assert pending_writer.save_full.call_count == 1
    assert pending_writer.save_partial.call_count == 0
    assert events[-1] is OrchestratorEvent.RecordSaved


def test_persist_step_writes_partial_once_without_record_saved(frame) -> None:
    pending_writer = MagicMock()
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        ConnectionResetError("connection reset"),
    ]
    events: list[OrchestratorEvent] = []

    state = _orchestrator(client, pending_writer).run_pipeline(
        frame,
        CancelToken(),
        events.append,
    )

    assert state.terminal_status is TerminalStatus.STAGE2_FAILED
    assert state.partial_reason == "network_error"
    assert state.step_history == ["stage1", "route", "stage2", "persist"]
    pending_writer.save_partial.assert_called_once_with(state.record, "network_error")
    pending_writer.save_full.assert_not_called()
    assert OrchestratorEvent.RecordSaved not in events


def test_persist_step_writes_insufficient_data_partial(monkeypatch, frame) -> None:
    monkeypatch.setattr(
        "pa_agent.ai.decision_nodes.check_preflight_data",
        lambda _frame: SimpleNamespace(
            ok=False,
            failed_check="bars",
            reason="not enough bars",
        ),
    )
    pending_writer = MagicMock()
    events: list[OrchestratorEvent] = []

    state = _orchestrator(MagicMock(), pending_writer).run_pipeline(
        frame,
        CancelToken(),
        events.append,
    )

    assert state.terminal_status is TerminalStatus.INSUFFICIENT_DATA
    assert state.partial_reason == "insufficient_data"
    assert state.step_history == ["stage1", "persist"]
    pending_writer.save_partial.assert_called_once_with(
        state.record,
        "insufficient_data",
    )
    pending_writer.save_full.assert_not_called()
    assert events == [OrchestratorEvent.InsufficientData]


def test_persist_step_maps_full_disk_failure_without_record_saved(frame) -> None:
    pending_writer = MagicMock()
    pending_writer.save_full.return_value = False
    events: list[OrchestratorEvent] = []

    state = _orchestrator(_valid_client(), pending_writer).run_pipeline(
        frame,
        CancelToken(),
        events.append,
    )

    assert state.terminal_status is TerminalStatus.PERSIST_FAILED
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.partial_reason == "disk_error"
    assert state.persistence_error is True
    assert state.record.exception == {
        "type": "persist_error",
        "stage": "persist",
    }
    assert OrchestratorEvent.RecordSaved not in events
    pending_writer.save_partial.assert_not_called()


def test_persist_step_keeps_partial_reason_when_partial_disk_write_fails(frame) -> None:
    pending_writer = MagicMock()
    pending_writer.save_partial.return_value = False
    client = MagicMock()
    client.stream_chat.return_value = _invalid_reply()
    settings = Settings(validation={"retry_enabled": False})

    state = _orchestrator(
        client,
        pending_writer,
        settings=settings,
    ).run_pipeline(frame, CancelToken(), lambda _event: None)

    assert state.terminal_status is TerminalStatus.STAGE1_FAILED
    assert state.partial_reason == "stage1_d"
    assert state.persistence_error is True
    pending_writer.save_partial.assert_called_once_with(state.record, "stage1_d")
    pending_writer.save_full.assert_not_called()
