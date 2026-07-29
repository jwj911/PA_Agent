"""Tests for the aggregate-only M4 Prompt contract evaluator."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from tools.compare_prompt_contract_live import compare_live_prompt_contracts
from tools.evaluate_prompt_contract_m4 import (
    BASELINE_SCHEMA,
    REPORT_SCHEMA,
    _load_baseline,
    build_report,
    main,
)
from tools.summarize_prompt_contract_live import LIVE_AGGREGATE_SCHEMA

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "tests" / "fixtures" / "prompt_contract_m3_baseline.json"
LIVE_BASELINE_PATH = (
    ROOT / "docs" / "evaluations" / "prompt_contract_live_m3_baseline_2026-07-27.json"
)
LIVE_CANDIDATE_PATH = (
    ROOT / "docs" / "evaluations" / "prompt_contract_live_m4_candidate_2026-07-29.json"
)
LIVE_COMPARISON_PATH = (
    ROOT / "docs" / "evaluations" / "prompt_contract_live_m4_comparison_2026-07-29.json"
)
M4_EXIT_REPORT_PATH = ROOT / "docs" / "evaluations" / "prompt_contract_m4_exit_2026-07-29.json"


def _live_report(contract_version: str, *, prompt_tokens: float) -> dict[str, object]:
    return {
        "schema": LIVE_AGGREGATE_SCHEMA,
        "contract_version": contract_version,
        "observation_count": 2,
        "execution_modes": {"legacy": 1, "pipeline": 1},
        "provider_contract_sha256s": ["provider-hash"],
        "fixture_contract_sha256s": ["fixture-hash"],
        "metrics": {
            "terminal_validation_failure_rate": 0.0,
            "validation_retry_run_rate": 0.0,
            "model_prompt_identity_output_rate": (
                1.0 if contract_version == "m3-compatible" else 0.0
            ),
            "semantic_routing_conflict_rate": (1.0 if contract_version == "m3-compatible" else 0.0),
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


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def test_project_pins_the_baseline_tokenizer_version() -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    tokenizer = baseline["tokenizer"]

    assert f"{tokenizer['package']}=={tokenizer['version']}" in project["dependencies"]


def test_m4_report_passes_exit_gate_with_verified_live_evidence(tmp_path: Path) -> None:
    live_baseline = _live_report("m3-compatible", prompt_tokens=100.0)
    live_candidate = _live_report("m4.2", prompt_tokens=99.0)
    live_comparison = compare_live_prompt_contracts(live_baseline, live_candidate)
    baseline_path = tmp_path / "live-baseline.json"
    candidate_path = tmp_path / "live-candidate.json"
    comparison_path = tmp_path / "live-comparison.json"
    _write_json(baseline_path, live_baseline)
    _write_json(candidate_path, live_candidate)
    _write_json(comparison_path, live_comparison)

    live_report = build_report(
        root=ROOT,
        baseline_path=BASELINE_PATH,
        live_baseline_path=baseline_path,
        live_candidate_path=candidate_path,
        live_comparison_path=comparison_path,
    )

    assert live_report["gates"]["offline_gate_passed"] is True
    assert live_report["gates"]["live_gate_passed"] is True
    assert live_report["gates"]["m4_exit_gate_passed"] is True
    assert live_report["live_observation"]["status"] == "passed"
    assert live_report["live_observation"]["evidence_collected"] is True
    assert len(live_report["live_observation"]["candidate_aggregate_sha256"]) == 64
    assert len(live_report["live_observation"]["comparison_sha256"]) == 64


def test_m4_cli_requires_live_gate_when_evidence_is_requested(tmp_path: Path) -> None:
    live_baseline = _live_report("m3-compatible", prompt_tokens=100.0)
    live_candidate = _live_report("m4.2", prompt_tokens=120.0)
    live_comparison = compare_live_prompt_contracts(live_baseline, live_candidate)
    baseline_path = tmp_path / "live-baseline.json"
    candidate_path = tmp_path / "live-candidate.json"
    comparison_path = tmp_path / "live-comparison.json"
    _write_json(baseline_path, live_baseline)
    _write_json(candidate_path, live_candidate)
    _write_json(comparison_path, live_comparison)

    exit_code = main(
        [
            "--live-baseline",
            str(baseline_path),
            "--live-candidate",
            str(candidate_path),
            "--live-comparison",
            str(comparison_path),
        ]
    )

    assert live_comparison["gates"]["live_gate_passed"] is False
    assert exit_code == 1


def test_m4_report_rejects_tampered_live_comparison(tmp_path: Path) -> None:
    live_baseline = _live_report("m3-compatible", prompt_tokens=100.0)
    live_candidate = _live_report("m4.2", prompt_tokens=99.0)
    live_comparison = compare_live_prompt_contracts(live_baseline, live_candidate)
    live_comparison["gates"]["live_gate_passed"] = False
    baseline_path = tmp_path / "live-baseline.json"
    candidate_path = tmp_path / "live-candidate.json"
    comparison_path = tmp_path / "live-comparison.json"
    _write_json(baseline_path, live_baseline)
    _write_json(candidate_path, live_candidate)
    _write_json(comparison_path, live_comparison)

    with pytest.raises(ValueError, match="does not match recomputed"):
        build_report(
            root=ROOT,
            baseline_path=BASELINE_PATH,
            live_baseline_path=baseline_path,
            live_candidate_path=candidate_path,
            live_comparison_path=comparison_path,
        )


def test_m4_report_rejects_partial_live_evidence_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        build_report(
            root=ROOT,
            baseline_path=BASELINE_PATH,
            live_baseline_path=tmp_path / "live-baseline.json",
        )


def test_m4_final_exit_report_is_reproducible() -> None:
    expected = json.loads(M4_EXIT_REPORT_PATH.read_text(encoding="utf-8"))

    actual = build_report(
        root=ROOT,
        baseline_path=BASELINE_PATH,
        live_baseline_path=LIVE_BASELINE_PATH,
        live_candidate_path=LIVE_CANDIDATE_PATH,
        live_comparison_path=LIVE_COMPARISON_PATH,
    )

    assert actual == expected
    assert actual["gates"]["m4_exit_gate_passed"] is True
