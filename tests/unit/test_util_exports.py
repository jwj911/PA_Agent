"""Tests for the utility package exports."""

from __future__ import annotations

from pa_agent import util
from pa_agent.util.event_bus import EventBus
from pa_agent.util.logging import configure_logging, update_api_key
from pa_agent.util.threading import CancelToken, OrchestratorEvent


def test_util_package_exports_expected_public_names() -> None:
    assert util.__all__ == [
        "CancelToken",
        "EventBus",
        "OrchestratorEvent",
        "configure_logging",
        "update_api_key",
    ]


def test_util_public_names_are_bound_to_util_objects() -> None:
    assert util.CancelToken is CancelToken
    assert util.EventBus is EventBus
    assert util.OrchestratorEvent is OrchestratorEvent
    assert util.configure_logging is configure_logging
    assert util.update_api_key is update_api_key
