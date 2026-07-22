"""Tests for the public PyQt-free headless analysis adapter."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pa_agent.headless import HeadlessAdapterError, HeadlessAnalysisAdapter
from pa_agent.util.event_sink import CollectingEventSink
from pa_agent.util.threading import OrchestratorEvent


def test_headless_adapter_publishes_correlated_events(monkeypatch) -> None:
    sink = CollectingEventSink()
    record = SimpleNamespace(exception=None)

    class _FakeOrchestrator:
        def __init__(self, **kwargs) -> None:
            assert kwargs["settings"] is context.settings

        def submit(self, *, frame, cancel_token, on_event):
            assert frame is not None
            assert cancel_token is not None
            on_event(OrchestratorEvent.Stage1Started)
            on_event(OrchestratorEvent.Stage1Done)
            return record

    context = SimpleNamespace(
        settings=object(),
        client=object(),
        assembler=object(),
        router=object(),
        validator=object(),
        pending_writer=object(),
        exp_reader=object(),
        event_sink=sink,
    )
    monkeypatch.setattr("pa_agent.headless.TwoStageOrchestrator", _FakeOrchestrator)

    callback_events: list[OrchestratorEvent] = []
    frame = object()
    result = HeadlessAnalysisAdapter(
        context,
        correlation_id="headless-test",
    ).run(frame, on_event=callback_events.append)

    assert result.record is record
    assert result.correlation_id == "headless-test"
    assert result.event_names == ("Stage1Started", "Stage1Done")
    assert callback_events == [OrchestratorEvent.Stage1Started, OrchestratorEvent.Stage1Done]
    assert [event.payload["event"] for event in sink.events] == [
        "Stage1Started",
        "Stage1Done",
    ]
    assert {event.correlation_id for event in sink.events} == {"headless-test"}


def test_headless_adapter_rejects_missing_dependencies() -> None:
    context = SimpleNamespace(
        settings=object(),
        client=object(),
        assembler=None,
        router=object(),
        validator=object(),
        pending_writer=object(),
        exp_reader=object(),
    )

    with pytest.raises(HeadlessAdapterError, match="assembler"):
        HeadlessAnalysisAdapter(context).run(object())
