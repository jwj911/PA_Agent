"""Tests for the aggregate-only M4 Prompt contract evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evaluate_prompt_contract_m4 import (
    BASELINE_SCHEMA,
    REPORT_SCHEMA,
    _load_baseline,
    build_report,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "tests" / "fixtures" / "prompt_contract_m3_baseline.json"


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return build_report(
        root=ROOT,
        baseline_path=BASELINE_PATH,
        live_api_key_present=False,
    )


def test_m4_offline_contract_report_passes_without_claiming_live_exit(
    report: dict[str, object],
) -> None:
    baseline = report["baseline"]
    candidate = report["candidate"]
    deltas = report["deltas"]
    gates = report["gates"]

    assert report["schema"] == REPORT_SCHEMA
    assert baseline["contract_metrics"]["schema_validation_failures"] == 0
    assert candidate["contract_metrics"]["schema_validation_failures"] == 0
    assert baseline["contract_metrics"]["retry_required"] == 0
    assert candidate["contract_metrics"]["retry_required"] == 0
    assert baseline["contract_metrics"]["semantic_routing_conflicts"] == 2
    assert candidate["contract_metrics"]["semantic_routing_conflicts"] == 0
    assert deltas["prompt_aggregate"]["estimated_token_delta"] == -7
    assert gates["offline_gate_passed"] is True
    assert gates["m4_exit_gate_passed"] is False
    assert report["live_observation"]["status"] == "blocked_missing_session_api_key"


def test_m4_report_contains_only_aggregate_prompt_evidence(
    report: dict[str, object],
) -> None:
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)

    assert '"content"' not in rendered
    assert "strategy_files_needed" not in rendered
    assert "recommended_strategy_files" not in rendered
    assert "上涨通道分析识别.txt" not in rendered
    assert '"symbol"' not in rendered
    assert '"price"' not in rendered


def test_m4_report_keeps_each_prompt_variant_within_token_threshold(
    report: dict[str, object],
) -> None:
    threshold = report["thresholds"]["max_token_regression_ratio_per_prompt_variant"]
    variants = report["deltas"]["prompt_variants"]

    assert set(variants) == {
        "stage1",
        "stage2_standalone",
        "stage2_continuation_standalone",
        "stage2_continuation_prefix",
    }
    assert all(
        metrics["message_count_changed"] is False
        and metrics["estimated_token_delta_ratio"] <= threshold
        for metrics in variants.values()
    )


def test_m4_baseline_loader_rejects_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps({"schema": "unsupported", "prompt_metrics": {}, "contract_metrics": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="baseline schema"):
        _load_baseline(path)


def test_m4_baseline_fixture_schema_is_versioned() -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["schema"] == BASELINE_SCHEMA
    assert baseline["source_commit"] == "2fc73e23a532534c9b468bab54ab8559e44bf871"
