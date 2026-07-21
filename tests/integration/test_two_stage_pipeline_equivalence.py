"""Legacy/opt-in pipeline adapter equivalence tests."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

from pa_agent.ai.router import route_strategy_files
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


def _orchestrator() -> TwoStageOrchestrator:
    client = MagicMock()
    client.stream_chat.side_effect = [
        make_reply(VALID_STAGE1),
        make_reply(VALID_STAGE2),
    ]
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    return TwoStageOrchestrator(
        client=client,
        assembler=_assembler(),
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=MagicMock(),
        exp_reader=exp_reader,
    )


def _record_without_runtime_timestamp(record) -> dict:
    payload = copy.deepcopy(record.model_dump())
    payload["meta"].pop("timestamp_local_iso", None)
    payload["meta"].pop("timestamp_local_ms", None)
    return payload


def test_opt_in_pipeline_matches_legacy_record_and_events(frame) -> None:
    legacy_events: list[OrchestratorEvent] = []
    legacy_record = _orchestrator().submit(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=legacy_events.append,
    )

    pipeline_events: list[OrchestratorEvent] = []
    pipeline_state = _orchestrator().run_pipeline(
        frame=frame,
        cancel_token=CancelToken(),
        on_event=pipeline_events.append,
    )

    assert pipeline_state.terminal_status is TerminalStatus.COMPLETED
    assert pipeline_state.step_history == ["stage1", "legacy_post_stage1"]
    assert pipeline_state.record is not None
    assert pipeline_events == legacy_events
    assert _record_without_runtime_timestamp(pipeline_state.record) == (
        _record_without_runtime_timestamp(legacy_record)
    )


def test_opt_in_pipeline_maps_preflight_cancel_to_terminal_status(frame) -> None:
    cancel_token = CancelToken()
    cancel_token.set()
    events: list[OrchestratorEvent] = []

    state = _orchestrator().run_pipeline(
        frame=frame,
        cancel_token=cancel_token,
        on_event=events.append,
    )

    assert state.terminal_status is TerminalStatus.CANCELLED
    assert events == [OrchestratorEvent.Cancelled]
    assert state.record is not None
    assert state.record.exception is None
