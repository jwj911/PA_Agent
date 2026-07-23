"""Controlled L3 flag-off/flag-on rollout observation."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest

from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import Settings
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2, make_reply

OBSERVATION_ROUNDS = 3
OBSERVATION_CASES = (
    "happy",
    "stage1_network",
    "stage2_network",
    "cancel",
    "stage1_validation",
)


def _invalid_reply() -> MagicMock:
    reply = MagicMock()
    reply.content = "not json"
    reply.reasoning_content = ""
    reply.raw = {"content": reply.content}
    reply.latency_ms = 1.0
    reply.usage = MagicMock(
        prompt_tokens=100,
        completion_tokens=50,
        cached_prompt_tokens=0,
        total_tokens=150,
    )
    return reply


def _make_orchestrator(
    *,
    case: str,
    pipeline_enabled: bool,
    cancel_token: CancelToken,
    pending_writer: MagicMock,
) -> TwoStageOrchestrator:
    client = MagicMock()
    if case == "happy":
        client.stream_chat.side_effect = [
            make_reply(VALID_STAGE1),
            make_reply(VALID_STAGE2),
        ]
    elif case == "stage1_network":
        client.stream_chat.side_effect = [ConnectionResetError("connection reset")]
    elif case == "stage2_network":
        client.stream_chat.side_effect = [
            make_reply(VALID_STAGE1),
            ConnectionResetError("connection reset"),
        ]
    elif case == "stage1_validation":
        client.stream_chat.side_effect = [_invalid_reply()]
    else:
        cancel_token.set()
        client.stream_chat.side_effect = []

    assembler = MagicMock()
    assembler.build_stage1.return_value = [{"role": "system", "content": "stage1"}]
    assembler.build_stage2_continuation.return_value = [
        {"role": "system", "content": "stage2"},
    ]
    exp_reader = MagicMock()
    exp_reader.read_for_stage2.return_value = []
    settings = Settings(
        orchestrator={"pipeline_builder_enabled": pipeline_enabled},
        validation=({"retry_enabled": False} if case == "stage1_validation" else {}),
    )
    return TwoStageOrchestrator(
        client=client,
        assembler=assembler,
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer,
        exp_reader=exp_reader,
        settings=settings,
    )


def _record_snapshot(record) -> dict:
    payload = copy.deepcopy(record.model_dump())
    payload["meta"].pop("timestamp_local_iso", None)
    payload["meta"].pop("timestamp_local_ms", None)
    return payload


def _run_case(frame, *, case: str, pipeline_enabled: bool) -> dict:
    cancel_token = CancelToken()
    pending_writer = MagicMock()
    orchestrator = _make_orchestrator(
        case=case,
        pipeline_enabled=pipeline_enabled,
        cancel_token=cancel_token,
        pending_writer=pending_writer,
    )
    events: list[OrchestratorEvent] = []
    prompts: list[tuple[str, str, str]] = []
    content: list[tuple[str, str]] = []
    reasoning: list[tuple[str, str]] = []
    strategy_files: list[list[str]] = []
    record = orchestrator.submit(
        frame=frame,
        cancel_token=cancel_token,
        on_event=events.append,
        on_stage_prompt=lambda stage, system, user: prompts.append((stage, system, user)),
        on_stage1_reasoning=lambda chunk: reasoning.append(("stage1", chunk)),
        on_stage1_content=lambda chunk: content.append(("stage1", chunk)),
        on_stage2_reasoning=lambda chunk: reasoning.append(("stage2", chunk)),
        on_stage2_content=lambda chunk: content.append(("stage2", chunk)),
        on_stage2_files=strategy_files.append,
    )
    return {
        "record": record,
        "events": events,
        "prompts": prompts,
        "content": content,
        "reasoning": reasoning,
        "strategy_files": strategy_files,
        "writer": pending_writer,
    }


@pytest.mark.parametrize("case", OBSERVATION_CASES)
def test_flag_on_matches_legacy_across_controlled_observation_rounds(frame, case: str) -> None:
    """Repeat each terminal fixture to detect deterministic rollout drift."""
    for _round in range(OBSERVATION_ROUNDS):
        legacy = _run_case(frame, case=case, pipeline_enabled=False)
        pipeline = _run_case(frame, case=case, pipeline_enabled=True)

        assert _record_snapshot(pipeline["record"]) == _record_snapshot(legacy["record"])
        assert pipeline["events"] == legacy["events"]
        assert pipeline["prompts"] == legacy["prompts"]
        assert pipeline["content"] == legacy["content"]
        assert pipeline["reasoning"] == legacy["reasoning"]
        assert pipeline["strategy_files"] == legacy["strategy_files"]

        if case == "happy":
            pipeline["writer"].save_full.assert_called_once_with(pipeline["record"])
            legacy["writer"].save_full.assert_called_once_with(legacy["record"])
            pipeline["writer"].save_partial.assert_not_called()
            legacy["writer"].save_partial.assert_not_called()
        else:
            pipeline["writer"].save_partial.assert_called_once()
            legacy["writer"].save_partial.assert_called_once()
            pipeline["writer"].save_full.assert_not_called()
            legacy["writer"].save_full.assert_not_called()
