"""Tests for the sanitized offline experience ranking evaluator."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pa_agent.records.experience_eval import (
    EXPERIENCE_EVAL_SCHEMA,
    EXPERIENCE_FEATURE_VERSION,
    EXPERIENCE_SPLIT_SCHEMA,
    ExperienceEvalCase,
    ExperienceEvalDataset,
    apply_fixed_split,
    build_fixed_split,
    dump_dataset,
    dump_split,
    evaluate_rankings,
    load_dataset,
    load_split,
)


def _dataset() -> ExperienceEvalDataset:
    return ExperienceEvalDataset(
        feature_version=EXPERIENCE_FEATURE_VERSION,
        cases=(
            ExperienceEvalCase(
                case_id="query-a",
                instrument_id="instrument-001",
                timeframe="5m",
                cycle_position="micro_channel",
                direction="bull",
                patterns=("wedge",),
                relevant_ids=("case-a1", "case-a2"),
                candidate_count=3,
            ),
            ExperienceEvalCase(
                case_id="query-b",
                instrument_id="instrument-002",
                timeframe="1h",
                cycle_position="trading_range",
                direction="bear",
                patterns=("breakout_failure",),
                relevant_ids=("case-b1",),
                candidate_count=2,
                similarity_fallback=True,
            ),
            ExperienceEvalCase(
                case_id="query-c",
                instrument_id="instrument-003",
                timeframe="15m",
                cycle_position="normal_channel",
                direction="bull",
                patterns=(),
                relevant_ids=("case-c1", "case-c2"),
                candidate_count=2,
            ),
        ),
    )


def test_evaluate_rankings_reports_metrics_and_stability() -> None:
    dataset = _dataset()
    rankings = {
        "query-a": ("case-a2", "unrelated", "case-a1"),
        "query-b": ("unrelated", "case-b1"),
        "query-c": ("case-c1", "case-c2"),
    }
    baseline = {
        "query-a": ("case-a1", "unrelated", "case-a2"),
        "query-b": ("case-b1",),
        "query-c": ("case-c2", "case-c1"),
    }
    metrics = evaluate_rankings(
        dataset,
        rankings,
        k=2,
        baseline_rankings=baseline,
        scores={
            "query-a": (0.9, 0.2, 0.1),
            "query-b": (0.8, 0.3),
            "query-c": (1.0, 0.7),
        },
    )

    assert metrics.query_count == 3
    assert metrics.recall_at_k == pytest.approx(5 / 6)
    ideal_two = 1 + 1 / math.log2(3)
    assert metrics.ndcg_at_k == pytest.approx((1 / ideal_two + 1 / math.log2(3) + 1.0) / 3)
    assert metrics.fallback_rate == pytest.approx(1 / 3)
    assert metrics.ranking_stability == pytest.approx(5 / 6)
    assert metrics.score_distribution["count"] == 7.0
    assert metrics.score_distribution["p50"] == pytest.approx(0.7)
    assert metrics.score_distribution["p95"] == pytest.approx(0.97)


def test_dataset_round_trip_has_version_and_no_raw_market_payload(tmp_path: Path) -> None:
    path = tmp_path / "experience_eval.json"
    dataset = _dataset()

    dump_dataset(path, dataset)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == EXPERIENCE_EVAL_SCHEMA
    assert payload["feature_version"] == EXPERIENCE_FEATURE_VERSION
    assert "kline_data" not in path.read_text(encoding="utf-8")
    assert load_dataset(path) == dataset


def test_dataset_rejects_unknown_schema_and_duplicate_case_ids(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps(
            {
                "schema": "pa-agent.experience-eval.v999",
                "feature_version": EXPERIENCE_FEATURE_VERSION,
                "cases": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported"):
        load_dataset(path)

    case = _dataset().cases[0]
    with pytest.raises(ValueError, match="case_id"):
        ExperienceEvalDataset(
            feature_version=EXPERIENCE_FEATURE_VERSION,
            cases=(case, case),
        )


def test_empty_dataset_and_invalid_k_are_explicit() -> None:
    empty = ExperienceEvalDataset(feature_version=EXPERIENCE_FEATURE_VERSION, cases=())
    metrics = evaluate_rankings(empty, {}, k=3)

    assert metrics.query_count == 0
    assert metrics.score_distribution == {"count": 0.0}
    with pytest.raises(ValueError, match="positive"):
        evaluate_rankings(empty, {}, k=0)


def test_fixed_split_is_deterministic_and_keeps_instruments_together(tmp_path: Path) -> None:
    base = _dataset()
    extra = ExperienceEvalCase(
        case_id="query-a2",
        instrument_id="instrument-001",
        timeframe="1h",
        cycle_position="micro_channel",
        direction="bull",
        patterns=("wedge",),
        relevant_ids=("case-a3",),
        candidate_count=1,
    )
    dataset = ExperienceEvalDataset(
        feature_version=EXPERIENCE_FEATURE_VERSION,
        cases=(*base.cases, extra),
    )

    split = build_fixed_split(dataset, evaluation_fraction=0.5)
    reversed_split = build_fixed_split(
        ExperienceEvalDataset(
            feature_version=dataset.feature_version,
            cases=tuple(reversed(dataset.cases)),
        ),
        evaluation_fraction=0.5,
    )
    train, evaluation = apply_fixed_split(dataset, split)

    assert split.schema == EXPERIENCE_SPLIT_SCHEMA
    assert split.dataset_digest == reversed_split.dataset_digest
    assert split.train_group_ids == reversed_split.train_group_ids
    assert split.evaluation_group_ids == reversed_split.evaluation_group_ids
    assert set(split.train_case_ids).isdisjoint(split.evaluation_case_ids)
    assert {case.instrument_id for case in train.cases}.isdisjoint(
        case.instrument_id for case in evaluation.cases
    )
    assert {case.case_id for case in train.cases} | {case.case_id for case in evaluation.cases} == {
        case.case_id for case in dataset.cases
    }

    path = tmp_path / "split.json"
    dump_split(path, split)
    assert load_split(path) == split
    assert "price" not in path.read_text(encoding="utf-8")


def test_fixed_split_rejects_single_group_and_digest_mismatch() -> None:
    dataset = _dataset()
    single_group = ExperienceEvalDataset(
        feature_version=dataset.feature_version,
        cases=tuple(
            ExperienceEvalCase(
                case_id=f"single-{index}",
                instrument_id="one-instrument",
                timeframe="5m",
                cycle_position="micro_channel",
                direction="bull",
                patterns=(),
                relevant_ids=(f"case-{index}",),
                candidate_count=1,
            )
            for index in range(2)
        ),
    )
    with pytest.raises(ValueError, match="at least two instrument groups"):
        build_fixed_split(single_group)

    split = build_fixed_split(dataset)
    with pytest.raises(ValueError, match="dataset digest"):
        apply_fixed_split(single_group, split)
