"""Task 10 rollout evidence for the complete PyQt-free pipeline."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import Settings
from pa_agent.orchestrator.pipeline import TerminalStatus
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply


def _assembler() -> MagicMock:
    assembler = MagicMock()
    assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
    assembler.build_stage2_continuation.return_value = [
        {"role": "system", "content": "stage2"},
    ]
    return assembler


def _text_reply(text: str) -> MagicMock:
    reply = MagicMock()
    reply.content = text
    reply.reasoning_content = ""
    reply.raw = {"content": text}
    reply.latency_ms = 1.0
    reply.usage = SimpleNamespace(
        prompt_tokens=100,
        cached_prompt_tokens=0,
        completion_tokens=50,
        total_tokens=150,
    )
    return reply


def _orchestrator(
    *,
    replies: list[object] | None = None,
    chat_side_effect: object | None = None,
    settings: Settings | None = None,
    router: object = route_strategy_files,
    pending_writer: MagicMock | None = None,
) -> TwoStageOrchestrator:
    client = MagicMock()
    client.stream_chat.side_effect = (
        chat_side_effect if chat_side_effect is not None else list(replies or [])
    )
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=_assembler(),
        router=router,
        validator=schema_test_validator(),
        pending_writer=pending_writer or MagicMock(),
        exp_reader=exp_reader,
        settings=settings,
    )


def _normalized_record(record) -> dict:
    payload = copy.deepcopy(record.model_dump())
    payload["meta"].pop("timestamp_local_iso", None)
    payload["meta"].pop("timestamp_local_ms", None)
    return payload


def _submit_adapter(
    orchestrator: TwoStageOrchestrator,
    frame,
    *,
    events: list[OrchestratorEvent],
    prompts: list[tuple[str, str, str]],
    content: list[str],
) -> object:
    return orchestrator.submit(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=events.append,
        on_stage_prompt=lambda stage, system, user: prompts.append((stage, system, user)),
        on_stage1_content=content.append,
        on_stage2_content=content.append,
    )


def _headless_adapter(
    orchestrator: TwoStageOrchestrator,
    frame,
    *,
    events: list[OrchestratorEvent],
    prompts: list[tuple[str, str, str]],
    content: list[str],
) -> object:
    """Minimal Qt-free adapter representing the headless runner boundary."""
    return _submit_adapter(
        orchestrator,
        frame,
        events=events,
        prompts=prompts,
        content=content,
    )


def _gui_adapter(
    orchestrator: TwoStageOrchestrator,
    frame,
    *,
    events: list[OrchestratorEvent],
    prompts: list[tuple[str, str, str]],
    content: list[str],
) -> object:
    """Minimal Qt-free stand-in for the GUI worker's submit boundary."""
    return _submit_adapter(
        orchestrator,
        frame,
        events=events,
        prompts=prompts,
        content=content,
    )


def test_headless_gui_submit_and_direct_pipeline_are_equivalent_without_qt(frame) -> None:
    """Both adapter call sites use the same submit contract, with no Qt import."""
    legacy_events: list[OrchestratorEvent] = []
    legacy_prompts: list[tuple[str, str, str]] = []
    legacy_content: list[str] = []
    legacy_record = _headless_adapter(
        _orchestrator(
            replies=[make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)],
            settings=Settings(),
        ),
        frame,
        events=legacy_events,
        prompts=legacy_prompts,
        content=legacy_content,
    )

    gui_events: list[OrchestratorEvent] = []
    gui_prompts: list[tuple[str, str, str]] = []
    gui_content: list[str] = []
    gui_record = _gui_adapter(
        _orchestrator(
            replies=[make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)],
            settings=Settings(orchestrator={"pipeline_builder_enabled": True}),
        ),
        frame,
        events=gui_events,
        prompts=gui_prompts,
        content=gui_content,
    )

    pipeline_events: list[OrchestratorEvent] = []
    pipeline_prompts: list[tuple[str, str, str]] = []
    pipeline_content: list[str] = []
    pipeline_state = _orchestrator(
        replies=[make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)],
        settings=Settings(),
    ).run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=pipeline_events.append,
        on_stage_prompt=lambda stage, system, user: pipeline_prompts.append((stage, system, user)),
        on_stage1_content=pipeline_content.append,
        on_stage2_content=pipeline_content.append,
    )

    assert _normalized_record(gui_record) == _normalized_record(legacy_record)
    assert _normalized_record(pipeline_state.record) == _normalized_record(legacy_record)
    assert gui_events == legacy_events == pipeline_events
    assert gui_prompts == legacy_prompts == pipeline_prompts
    assert gui_content == legacy_content == pipeline_content
    assert pipeline_state.step_history == ["stage1", "route", "stage2", "persist"]


def test_submit_default_does_not_enter_pipeline(monkeypatch, frame) -> None:
    """The rollout switch remains off for Settings created without the section."""
    orchestrator = _orchestrator(
        replies=[make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)],
        settings=Settings(),
    )
    pipeline_called = MagicMock(side_effect=AssertionError("pipeline must stay opt-in"))
    monkeypatch.setattr(orchestrator, "submit_pipeline", pipeline_called)

    record = orchestrator.submit(frame, CancelToken(), lambda _event: None)

    assert record.exception is None
    pipeline_called.assert_not_called()


@pytest.mark.parametrize(
    ("case", "status", "reason", "steps", "expected_events"),
    [
        (
            "happy",
            TerminalStatus.COMPLETED,
            None,
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Stage2Done,
                OrchestratorEvent.RecordSaved,
            ],
        ),
        (
            "preflight_insufficient",
            TerminalStatus.INSUFFICIENT_DATA,
            "insufficient_data",
            ["stage1", "persist"],
            [OrchestratorEvent.InsufficientData],
        ),
        (
            "cancel",
            TerminalStatus.CANCELLED,
            "user_cancelled",
            ["stage1", "persist"],
            [OrchestratorEvent.Cancelled],
        ),
        (
            "stage1_network",
            TerminalStatus.STAGE1_FAILED,
            "network_error",
            ["stage1", "persist"],
            [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Failed],
        ),
        (
            "stage1_validation",
            TerminalStatus.STAGE1_FAILED,
            "stage1_d",
            ["stage1", "persist"],
            [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Failed],
        ),
        (
            "route_failure",
            TerminalStatus.ROUTE_FAILED,
            "route_failed",
            ["stage1", "route", "persist"],
            [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Done],
        ),
        (
            "route_cancel",
            TerminalStatus.CANCELLED,
            "user_cancelled",
            ["stage1", "route", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Cancelled,
            ],
        ),
        (
            "stage2_gate",
            TerminalStatus.COMPLETED,
            None,
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Stage2Done,
                OrchestratorEvent.RecordSaved,
            ],
        ),
        (
            "stage2_network",
            TerminalStatus.STAGE2_FAILED,
            "network_error",
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Stage2Failed,
            ],
        ),
        (
            "stage2_validation",
            TerminalStatus.STAGE2_FAILED,
            "stage2_d",
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Stage2Failed,
            ],
        ),
        (
            "stage2_cancel",
            TerminalStatus.CANCELLED,
            "user_cancelled",
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Cancelled,
            ],
        ),
        (
            "persist_full_disk_failure",
            TerminalStatus.PERSIST_FAILED,
            "disk_error",
            ["stage1", "route", "stage2", "persist"],
            [
                OrchestratorEvent.Stage1Started,
                OrchestratorEvent.Stage1Done,
                OrchestratorEvent.Stage2Started,
                OrchestratorEvent.Stage2Done,
            ],
        ),
        (
            "persist_partial_disk_failure",
            TerminalStatus.STAGE1_FAILED,
            "stage1_d",
            ["stage1", "persist"],
            [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Failed],
        ),
    ],
)
def test_opt_in_terminal_matrix(
    monkeypatch,
    frame,
    case,
    status,
    reason,
    steps,
    expected_events,
) -> None:
    """Every Task 10 terminal fixture reaches PersistStep exactly once."""
    cancel_token = CancelToken()
    pending_writer = MagicMock()
    settings = None
    router = route_strategy_files
    chat_side_effect = None
    replies: list[object]

    if case == "happy":
        replies = [make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)]
    elif case == "preflight_insufficient":
        monkeypatch.setattr(
            "pa_agent.ai.decision_nodes.check_preflight_data",
            lambda _frame: SimpleNamespace(
                ok=False,
                failed_check="bars",
                reason="not enough bars",
            ),
        )
        replies = []
    elif case == "cancel":
        cancel_token.set()
        replies = []
    elif case == "stage1_network":
        replies = [ConnectionResetError("connection reset")]
    elif case == "stage1_validation":
        settings = Settings(validation={"retry_enabled": False})
        replies = [_text_reply("not json")]
    elif case == "route_failure":

        def failing_router(_stage1: dict) -> list[str]:
            raise RuntimeError("router unavailable")

        router = failing_router
        replies = [make_reply(VALID_STAGE1)]
    elif case == "route_cancel":

        def cancelling_router(_stage1: dict) -> list[str]:
            cancel_token.set()
            return []

        router = cancelling_router
        replies = [make_reply(VALID_STAGE1)]
    elif case == "stage2_gate":
        stage1_wait = copy.deepcopy(VALID_STAGE1)
        stage1_wait["gate_result"] = "wait"
        stage1_wait["cycle_position"] = "unknown"
        replies = [make_reply(stage1_wait)]
    elif case == "stage2_network":
        replies = [make_reply(VALID_STAGE1), ConnectionResetError("connection reset")]
    elif case == "stage2_validation":
        settings = Settings(validation={"retry_enabled": False})
        replies = [make_reply(VALID_STAGE1), _text_reply("not json")]
    elif case == "stage2_cancel":
        calls = 0

        def cancel_after_stage1(_messages, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                cancel_token.set()
                return make_reply(VALID_STAGE2)
            return make_reply(VALID_STAGE1)

        chat_side_effect = cancel_after_stage1
        replies = []
    elif case == "persist_full_disk_failure":
        pending_writer.save_full.return_value = False
        replies = [make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)]
    else:
        settings = Settings(validation={"retry_enabled": False})
        pending_writer.save_partial.return_value = False
        replies = [_text_reply("not json")]

    orchestrator = _orchestrator(
        replies=replies,
        chat_side_effect=chat_side_effect,
        settings=settings,
        router=router,
        pending_writer=pending_writer,
    )
    actual_events: list[OrchestratorEvent] = []
    state = orchestrator.run_pipeline(frame, cancel_token, actual_events.append)

    assert state.terminal_status is status
    assert state.partial_reason == reason
    assert state.step_history == steps
    assert actual_events == expected_events
    assert state.record is not None
    assert state.persistence_pending is False

    if status is TerminalStatus.COMPLETED:
        pending_writer.save_full.assert_called_once_with(state.record)
        pending_writer.save_partial.assert_not_called()
    elif case == "persist_full_disk_failure":
        pending_writer.save_full.assert_called_once()
        pending_writer.save_partial.assert_not_called()
        assert state.persistence_error is True
        assert state.record.exception == {
            "type": "persist_error",
            "stage": "persist",
        }
    else:
        pending_writer.save_partial.assert_called_once_with(state.record, reason)
        pending_writer.save_full.assert_not_called()
