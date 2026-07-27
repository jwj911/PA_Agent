"""Tests for M3/M4 aggregate live Prompt-contract comparison."""

from __future__ import annotations

import json

from tools.compare_prompt_contract_live import (
    LIVE_COMPARISON_SCHEMA,
    compare_live_prompt_contracts,
)
from tools.summarize_prompt_contract_live import LIVE_AGGREGATE_SCHEMA


def _report(
    contract_version: str,
    *,
    prompt_tokens: float,
    retry_rate: float,
    identity_rate: float,
    conflict_rate: float,
    provider_hash: str = "provider-hash",
    fixture_hash: str = "fixture-hash",
) -> dict[str, object]:
    return {
        "schema": LIVE_AGGREGATE_SCHEMA,
        "contract_version": contract_version,
        "observation_count": 2,
        "execution_modes": {"legacy": 1, "pipeline": 1},
        "provider_contract_sha256s": [provider_hash],
        "fixture_contract_sha256s": [fixture_hash],
        "metrics": {
            "terminal_validation_failure_rate": 0.0,
            "validation_retry_run_rate": retry_rate,
            "model_prompt_identity_output_rate": identity_rate,
            "semantic_routing_conflict_rate": conflict_rate,
            "usage_per_run_mean": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 20.0,
                "total_tokens": prompt_tokens + 20.0,
            },
        },
        "gates": {
            "all_artifacts_valid": True,
            "all_runs_completed": True,
            "all_runs_called_provider": True,
            "all_stage1_json_parseable": True,
            "single_provider_contract": True,
            "single_fixture_contract": True,
            "aggregate_only": True,
        },
    }


def test_live_prompt_contract_comparison_passes_non_regression() -> None:
    baseline = _report(
        "m3-compatible",
        prompt_tokens=100.0,
        retry_rate=0.0,
        identity_rate=1.0,
        conflict_rate=1.0,
    )
    candidate = _report(
        "m4",
        prompt_tokens=105.0,
        retry_rate=0.0,
        identity_rate=0.0,
        conflict_rate=0.0,
    )

    report = compare_live_prompt_contracts(baseline, candidate)

    assert report["schema"] == LIVE_COMPARISON_SCHEMA
    assert report["deltas"]["mean_prompt_tokens_ratio"] == 0.05
    assert report["deltas"]["model_prompt_identity_output_rate"] == -1.0
    assert report["deltas"]["semantic_routing_conflict_rate"] == -1.0
    assert report["gates"]["live_gate_passed"] is True


def test_live_prompt_contract_comparison_rejects_retry_regression() -> None:
    baseline = _report(
        "m3-compatible",
        prompt_tokens=100.0,
        retry_rate=0.0,
        identity_rate=1.0,
        conflict_rate=1.0,
    )
    candidate = _report(
        "m4",
        prompt_tokens=100.0,
        retry_rate=0.5,
        identity_rate=0.0,
        conflict_rate=0.0,
    )

    report = compare_live_prompt_contracts(baseline, candidate)

    assert report["gates"]["validation_retry_non_regression"] is False
    assert report["gates"]["live_gate_passed"] is False


def test_live_prompt_contract_comparison_requires_same_contract_hashes() -> None:
    baseline = _report(
        "m3-compatible",
        prompt_tokens=100.0,
        retry_rate=0.0,
        identity_rate=1.0,
        conflict_rate=1.0,
    )
    candidate = _report(
        "m4",
        prompt_tokens=100.0,
        retry_rate=0.0,
        identity_rate=0.0,
        conflict_rate=0.0,
        fixture_hash="different-fixture",
    )

    report = compare_live_prompt_contracts(baseline, candidate)

    assert report["gates"]["same_fixture_contract"] is False
    assert report["gates"]["live_gate_passed"] is False


def test_live_prompt_contract_comparison_rejects_prompt_token_regression() -> None:
    baseline = _report(
        "m3-compatible",
        prompt_tokens=100.0,
        retry_rate=0.0,
        identity_rate=1.0,
        conflict_rate=1.0,
    )
    candidate = _report(
        "m4",
        prompt_tokens=111.0,
        retry_rate=0.0,
        identity_rate=0.0,
        conflict_rate=0.0,
    )

    report = compare_live_prompt_contracts(baseline, candidate)

    assert report["gates"]["prompt_token_non_regression"] is False
    assert report["gates"]["live_gate_passed"] is False


def test_live_prompt_contract_comparison_report_is_aggregate_only() -> None:
    report = compare_live_prompt_contracts(
        _report(
            "m3-compatible",
            prompt_tokens=100.0,
            retry_rate=0.0,
            identity_rate=1.0,
            conflict_rate=1.0,
        ),
        _report(
            "m4",
            prompt_tokens=100.0,
            retry_rate=0.0,
            identity_rate=0.0,
            conflict_rate=0.0,
        ),
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)

    assert '"content"' not in rendered
    assert '"symbol"' not in rendered
    assert '"price"' not in rendered
    assert "strategy_files_needed" not in rendered
