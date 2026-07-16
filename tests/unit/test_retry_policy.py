"""Tests for validation retry policy helpers."""
from __future__ import annotations

from dataclasses import dataclass

from pa_agent.ai.retry_policy import (
    detect_cheat,
    extract_feedback_targets,
    max_retries_for_category,
    should_retry,
)


@dataclass
class _Settings:
    retry_enabled: bool = True
    retry_max: int = 3
    retry_max_semantic: int = 1


def test_max_retries_respects_category_and_settings() -> None:
    assert max_retries_for_category("a", _Settings(retry_max=2)) == 2
    assert max_retries_for_category("c", _Settings(retry_max=3, retry_max_semantic=2)) == 2
    assert max_retries_for_category("c", _Settings(retry_max=1, retry_max_semantic=3)) == 1
    assert max_retries_for_category("e", _Settings()) == 0
    assert max_retries_for_category("a", _Settings(retry_enabled=False)) == 0
    assert max_retries_for_category("unknown", _Settings()) == 0


def test_should_retry_stops_at_attempt_limit() -> None:
    settings = _Settings(retry_max=2, retry_max_semantic=1)

    assert should_retry("a", [], [], attempt=1, settings=settings)
    assert not should_retry("a", [], [], attempt=2, settings=settings)
    assert should_retry("c", ["trace:bad"], [], attempt=0, settings=settings)
    assert not should_retry("c", ["trace:bad"], [], attempt=1, settings=settings)


def test_should_retry_semantic_rejects_non_retryable_prefixes() -> None:
    settings = _Settings(retry_max=3, retry_max_semantic=2)

    assert not should_retry("c", ["metrics:bad rr"], [], attempt=0, settings=settings)
    assert not should_retry("c", ["trace:§14 safety gate"], [], attempt=0, settings=settings)
    assert not should_retry("c", ["s2:order_direction mismatch"], [], attempt=0, settings=settings)


def test_detect_cheat_flags_stage2_diagnosis_summary_changes() -> None:
    before = {"diagnosis_summary": {"cycle_position": "broad_channel"}}
    after = {"diagnosis_summary": {"cycle_position": "spike"}}
    flags = detect_cheat("stage2", before, after)

    assert len(flags) == 1
    assert "diagnosis_summary.cycle_position" in flags[0]
    assert "broad_channel" in flags[0]
    assert "spike" in flags[0]


def test_detect_cheat_allows_mentioned_stage2_diagnosis_summary_change() -> None:
    before = {"diagnosis_summary": {"cycle_position": "broad_channel"}}
    after = {"diagnosis_summary": {"cycle_position": "spike"}}

    assert (
        detect_cheat(
            "stage2",
            before,
            after,
            feedback_mentioned={"diagnosis_summary.cycle_position"},
        )
        == []
    )


def test_extract_feedback_targets_maps_known_field_names() -> None:
    targets = extract_feedback_targets(
        invalid_fields=[
            "s1: direction invalid",
            "next_bar_prediction.probabilities sum invalid",
            "ignored",
        ],
        missing_fields=["diagnosis_summary.cycle_position", "decision.order_type"],
    )

    assert targets == {
        "cycle_position",
        "diagnosis_summary",
        "direction",
        "next_bar_prediction",
        "order_type",
    }
