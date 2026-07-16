"""Tests for the demo package exports."""
from __future__ import annotations

from pa_agent import demo
from pa_agent.demo.record_loader import (
    frame_from_record_klines,
    is_demo_playable,
    list_pending_record_paths,
    load_analysis_record,
    pick_playable_demo_record,
    pick_random_record_path,
    try_load_analysis_record,
)
from pa_agent.demo.replayer import DemoReplayer


def test_demo_package_exports_expected_public_names() -> None:
    assert demo.__all__ == [
        "DemoReplayer",
        "frame_from_record_klines",
        "is_demo_playable",
        "list_pending_record_paths",
        "load_analysis_record",
        "pick_playable_demo_record",
        "pick_random_record_path",
        "try_load_analysis_record",
    ]


def test_demo_public_names_are_bound_to_demo_objects() -> None:
    assert demo.DemoReplayer is DemoReplayer
    assert demo.frame_from_record_klines is frame_from_record_klines
    assert demo.is_demo_playable is is_demo_playable
    assert demo.list_pending_record_paths is list_pending_record_paths
    assert demo.load_analysis_record is load_analysis_record
    assert demo.pick_playable_demo_record is pick_playable_demo_record
    assert demo.pick_random_record_path is pick_random_record_path
    assert demo.try_load_analysis_record is try_load_analysis_record
