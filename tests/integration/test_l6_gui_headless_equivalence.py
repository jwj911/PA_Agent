"""L6 GUI/headless full-chain equivalence evidence."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt6")

from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import Settings
from pa_agent.gui.main_window import _AnalysisWorker
from pa_agent.headless import HeadlessAnalysisAdapter
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.event_sink import CollectingEventSink
from pa_agent.util.events import EVENT_ORCHESTRATOR
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


def _invalid_reply(text: str = "not json") -> MagicMock:
    reply = MagicMock()
    reply.content = text
    reply.reasoning_content = ""
    reply.raw = {"content": text}
    reply.latency_ms = 1.0
    reply.usage = SimpleNamespace(
        prompt_tokens=100,
        completion_tokens=50,
        cached_prompt_tokens=0,
        total_tokens=150,
    )
    return reply


def _orchestrator(
    *,
    responses: list[object],
    settings: Settings,
    pending_writer: MagicMock,
) -> TwoStageOrchestrator:
    client = MagicMock()
    client.stream_chat.side_effect = list(responses)
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=_assembler(),
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer,
        exp_reader=exp_reader,
        settings=settings,
    )


def _context(
    *,
    orchestrator: TwoStageOrchestrator,
    sink: CollectingEventSink,
) -> SimpleNamespace:
    return SimpleNamespace(
        settings=orchestrator._settings,
        client=orchestrator._client,
        assembler=orchestrator._assembler,
        router=orchestrator._router,
        validator=orchestrator._validator,
        pending_writer=orchestrator._pending_writer,
        exp_reader=orchestrator._exp_reader,
        event_sink=sink,
    )


def _record_snapshot(record) -> dict:
    payload = copy.deepcopy(record.model_dump())
    payload["meta"].pop("timestamp_local_iso", None)
    payload["meta"].pop("timestamp_local_ms", None)
    return payload


def _event_names(events: list[OrchestratorEvent]) -> list[str]:
    return [event.name for event in events]


@pytest.mark.parametrize("case", ["final", "partial", "cancel", "failure"])
def test_gui_and_headless_match_full_chain_for_each_terminal_case(qtbot, frame, case: str) -> None:
    """Compare real GUI worker and public headless adapter boundaries."""
    settings = Settings(
        validation={"retry_enabled": False} if case == "failure" else {},
    )
    if case == "final":
        responses: list[object] = [make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)]
    elif case == "partial":
        responses = [make_reply(VALID_STAGE1), ConnectionResetError("connection reset")]
    elif case == "cancel":
        responses = []
    else:
        responses = [_invalid_reply()]

    headless_token = CancelToken()
    gui_token = CancelToken()
    if case == "cancel":
        headless_token.set()
        gui_token.set()

    headless_writer = MagicMock()
    gui_writer = MagicMock()
    headless_orchestrator = _orchestrator(
        responses=responses,
        settings=settings,
        pending_writer=headless_writer,
    )
    gui_orchestrator = _orchestrator(
        responses=responses,
        settings=settings,
        pending_writer=gui_writer,
    )
    sink = CollectingEventSink()
    context = _context(orchestrator=headless_orchestrator, sink=sink)

    headless_events: list[OrchestratorEvent] = []
    headless_prompts: list[tuple[str, str, str]] = []
    headless_content: list[tuple[str, str]] = []
    headless_reasoning: list[tuple[str, str]] = []
    headless_files: list[list[str]] = []
    headless_result = HeadlessAnalysisAdapter(
        context,
        event_sink=sink,
        correlation_id=f"l6-{case}",
    ).run(
        frame,
        cancel_token=headless_token,
        on_event=headless_events.append,
        on_stage_prompt=lambda stage, system, user: headless_prompts.append((stage, system, user)),
        on_stage1_reasoning=lambda chunk: headless_reasoning.append(("stage1", chunk)),
        on_stage1_content=lambda chunk: headless_content.append(("stage1", chunk)),
        on_stage2_reasoning=lambda chunk: headless_reasoning.append(("stage2", chunk)),
        on_stage2_content=lambda chunk: headless_content.append(("stage2", chunk)),
        on_stage2_files=headless_files.append,
    )

    gui_status: list[str] = []
    gui_prompts: list[tuple[str, str, str]] = []
    gui_content: list[tuple[str, str]] = []
    gui_reasoning: list[tuple[str, str]] = []
    gui_files: list[list[str]] = []
    gui_records: list[object] = []
    gui_errors: list[str] = []
    worker = _AnalysisWorker(gui_orchestrator, frame, gui_token)
    worker.status_update.connect(gui_status.append)
    worker.stage_prompt_ready.connect(lambda *value: gui_prompts.append(value))
    worker.content_token.connect(lambda *value: gui_content.append(value))
    worker.reasoning_token.connect(lambda *value: gui_reasoning.append(value))
    worker.stage2_files_ready.connect(gui_files.append)
    worker.record_ready.connect(gui_records.append)
    worker.error_occurred.connect(gui_errors.append)
    worker.run()

    assert gui_errors == []
    assert len(gui_records) == 1
    assert _record_snapshot(gui_records[0]) == _record_snapshot(headless_result.record)
    status_labels = {
        OrchestratorEvent.Stage1Started: "阶段一分析中…",
        OrchestratorEvent.Stage1Retry: "阶段一重试",
        OrchestratorEvent.Stage1Done: "阶段一完成",
        OrchestratorEvent.Stage1Failed: "阶段一失败",
        OrchestratorEvent.Stage2Started: "阶段二分析中…",
        OrchestratorEvent.Stage2Retry: "阶段二重试",
        OrchestratorEvent.Stage2Done: "阶段二完成",
        OrchestratorEvent.Stage2Failed: "阶段二失败",
        OrchestratorEvent.RecordSaved: "记录已保存",
        OrchestratorEvent.Cancelled: "已取消",
        OrchestratorEvent.InsufficientData: "InsufficientData",
    }
    assert gui_status == [status_labels[event] for event in headless_events]
    assert gui_prompts == headless_prompts
    assert gui_content == headless_content
    assert gui_reasoning == headless_reasoning
    assert gui_files == headless_files

    envelope_events = sink.events
    assert all(event.type == EVENT_ORCHESTRATOR for event in envelope_events)
    assert [event.payload["event"] for event in envelope_events] == _event_names(headless_events)
    assert {event.correlation_id for event in envelope_events} == {f"l6-{case}"}

    if case == "final":
        assert headless_result.record.exception is None
        headless_writer.save_full.assert_called_once_with(headless_result.record)
        gui_writer.save_full.assert_called_once_with(gui_records[0])
    else:
        assert headless_result.record.exception is not None or case == "cancel"
        headless_writer.save_partial.assert_called_once()
        gui_writer.save_partial.assert_called_once()


def test_gui_worker_reports_the_same_milestone_stream_as_headless(qtbot, frame) -> None:
    """The GUI status adapter reports the same milestone sequence as headless."""
    writer = MagicMock()
    worker = _AnalysisWorker(
        _orchestrator(
            responses=[make_reply(VALID_STAGE1), make_reply(VALID_STAGE2)],
            settings=Settings(),
            pending_writer=writer,
        ),
        frame,
        CancelToken(),
    )
    status: list[str] = []
    worker.status_update.connect(status.append)

    worker.run()

    assert status == [
        "阶段一分析中…",
        "阶段一完成",
        "阶段二分析中…",
        "阶段二完成",
        "记录已保存",
    ]
