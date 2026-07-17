"""Tests for lightweight threading helpers."""

from __future__ import annotations

from pa_agent.util.threading import CancelToken, OrchestratorEvent


def test_cancel_token_set_clear_and_wait() -> None:
    token = CancelToken()

    assert not token.is_set()
    assert not token.wait(timeout=0)

    token.set()
    assert token.is_set()
    assert token.wait(timeout=0)

    token.clear()
    assert not token.is_set()


def test_orchestrator_event_names_are_stable() -> None:
    assert [event.name for event in OrchestratorEvent] == [
        "Stage1Started",
        "Stage1Retry",
        "Stage1Done",
        "Stage1Failed",
        "Stage2Started",
        "Stage2Retry",
        "Stage2Done",
        "Stage2Failed",
        "RecordSaved",
        "Cancelled",
        "InsufficientData",
    ]
