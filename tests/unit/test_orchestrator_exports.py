"""Tests for the orchestrator package exports."""
from __future__ import annotations

from pa_agent import orchestrator
from pa_agent.orchestrator.free_chat import FreeChatSession
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator


def test_orchestrator_package_exports_expected_public_names() -> None:
    assert orchestrator.__all__ == ["FreeChatSession", "TwoStageOrchestrator"]


def test_orchestrator_public_names_are_bound_to_orchestrator_classes() -> None:
    assert orchestrator.FreeChatSession is FreeChatSession
    assert orchestrator.TwoStageOrchestrator is TwoStageOrchestrator
