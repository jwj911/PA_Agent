"""Focused integration coverage for the opt-in PyQt-free RouteStep."""

from __future__ import annotations

from unittest.mock import MagicMock

from pa_agent.config.settings import Settings
from pa_agent.orchestrator.pipeline import PersistenceIntent, TerminalStatus
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply


def _orchestrator(router, *, settings: Settings | None = None):
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    assembler = MagicMock()
    assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
    assembler.build_stage2_continuation.return_value = [
        {"role": "system", "content": "stage2"},
    ]
    pending_writer = MagicMock()
    exp_reader = MagicMock()
    return (
        TwoStageOrchestrator(
            client=client,
            assembler=assembler,
            router=router,
            validator=schema_test_validator(),
            pending_writer=pending_writer,
            exp_reader=exp_reader,
            settings=settings,
        ),
        client,
        pending_writer,
        exp_reader,
    )


def test_route_step_uses_callable_router_and_preserves_file_order(frame) -> None:
    routed_diagnoses: list[dict] = []

    def router(stage1_json: dict) -> list[str]:
        routed_diagnoses.append(stage1_json)
        return ["first.txt", "second.txt", "third.txt"]

    orchestrator, _client, _writer, exp_reader = _orchestrator(router)
    exp_reader.read_for_stage2.return_value = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.strategy_files == ["first.txt", "second.txt", "third.txt"]
    assert state.route_outputs["strategy_files"] == state.strategy_files
    assert state.route_outputs["experience_entries"] == []
    assert len(routed_diagnoses) == 1
    assert routed_diagnoses[0]["cycle_position"] == VALID_STAGE1["cycle_position"]


def test_route_step_supports_object_router(frame) -> None:
    class Router:
        def route(self, stage1_json: dict) -> list[str]:
            assert stage1_json["cycle_position"] == VALID_STAGE1["cycle_position"]
            return ["object-first.txt", "object-second.txt"]

    orchestrator, _client, _writer, exp_reader = _orchestrator(Router())
    exp_reader.read_for_stage2.return_value = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.strategy_files == ["object-first.txt", "object-second.txt"]


def test_route_step_passes_experience_limits_and_current_bars(frame) -> None:
    settings = Settings(
        prompt={
            "experience_max_entries": 2,
            "experience_max_chars_per_entry": 321,
        }
    )
    entries = [{"filename": "one.json"}, {"filename": "two.json"}]
    orchestrator, _client, _writer, exp_reader = _orchestrator(
        lambda _stage1: ["strategy.txt"],
        settings=settings,
    )
    exp_reader.read_for_stage2.return_value = entries

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.experience_entries == entries
    exp_reader.read_for_stage2.assert_called_once_with(
        "normal_channel",
        direction="neutral",
        patterns=[],
        max_entries=2,
        max_chars_per_entry=321,
        current_bars=frame.bars,
    )


def test_route_step_keeps_empty_experience_library_empty(frame) -> None:
    settings = Settings(prompt={"experience_max_entries": 3})
    orchestrator, _client, _writer, exp_reader = _orchestrator(
        lambda _stage1: ["strategy.txt"],
        settings=settings,
    )
    exp_reader.read_for_stage2.return_value = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
    )

    assert state.terminal_status is TerminalStatus.COMPLETED
    assert state.experience_entries == []
    assert state.route_outputs["experience_entries"] == []


def test_route_step_preserves_pre_stage2_cancel_boundary(frame) -> None:
    cancel_token = CancelToken()

    def router(_stage1: dict) -> list[str]:
        cancel_token.set()
        return ["strategy.txt"]

    orchestrator, client, pending_writer, exp_reader = _orchestrator(router)
    exp_reader.read_for_stage2.return_value = []
    events: list[OrchestratorEvent] = []

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=cancel_token,
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.CANCELLED
    assert state.step_history == ["stage1", "route", "persist"]
    assert state.strategy_files == ["strategy.txt"]
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Cancelled,
    ]
    assert OrchestratorEvent.Stage2Started not in events
    assert client.stream_chat.call_count == 1
    pending_writer.save_partial.assert_called_once()
    assert pending_writer.save_partial.call_args.args[1] == "user_cancelled"


def test_route_step_maps_route_exception_to_partial_terminal(frame) -> None:
    def router(_stage1: dict) -> list[str]:
        raise RuntimeError("router unavailable")

    orchestrator, client, pending_writer, _exp_reader = _orchestrator(router)

    state = orchestrator.run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=lambda _event: None,
    )

    assert state.terminal_status is TerminalStatus.ROUTE_FAILED
    assert state.partial_reason == "route_failed"
    assert state.persistence_intent is PersistenceIntent.PARTIAL
    assert state.record is not None
    assert state.record.exception == {
        "type": "route_error",
        "stage": "route",
        "message": "router unavailable",
    }
    assert state.step_history == ["stage1", "route", "persist"]
    assert client.stream_chat.call_count == 1
    pending_writer.save_partial.assert_called_once()
    assert pending_writer.save_partial.call_args.args[1] == "route_failed"
