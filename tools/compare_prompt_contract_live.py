"""Compare aggregate M3 and M4 live Prompt-contract reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.summarize_prompt_contract_live import LIVE_AGGREGATE_SCHEMA  # noqa: E402

LIVE_COMPARISON_SCHEMA = "pa-agent.prompt-contract-live-comparison.v1"
MAX_PROMPT_TOKEN_REGRESSION_RATIO = 0.10


def _load_report(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} report") from exc
    if not isinstance(value, dict) or value.get("schema") != LIVE_AGGREGATE_SCHEMA:
        raise ValueError(f"unsupported {label} report schema")
    return value


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _non_empty_hashes(value: object, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ValueError(f"{label} must be a non-empty string array")
    return list(value)


def _required_aggregate_gates(report: dict[str, Any]) -> bool:
    gates = _dict(report.get("gates"), "report gates")
    return all(
        gates.get(key) is True
        for key in (
            "all_artifacts_valid",
            "all_runs_completed",
            "all_runs_called_provider",
            "all_stage1_json_parseable",
            "single_provider_contract",
            "single_fixture_contract",
            "aggregate_only",
        )
    )


def compare_live_prompt_contracts(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    max_prompt_token_regression_ratio: float = MAX_PROMPT_TOKEN_REGRESSION_RATIO,
) -> dict[str, object]:
    """Compare two aggregate-only Prompt-contract reports."""
    if baseline.get("schema") != LIVE_AGGREGATE_SCHEMA:
        raise ValueError("unsupported baseline report schema")
    if candidate.get("schema") != LIVE_AGGREGATE_SCHEMA:
        raise ValueError("unsupported candidate report schema")
    if max_prompt_token_regression_ratio < 0:
        raise ValueError("max_prompt_token_regression_ratio must be non-negative")

    baseline_metrics = _dict(baseline.get("metrics"), "baseline metrics")
    candidate_metrics = _dict(candidate.get("metrics"), "candidate metrics")
    baseline_modes = _dict(baseline.get("execution_modes"), "baseline execution_modes")
    candidate_modes = _dict(candidate.get("execution_modes"), "candidate execution_modes")
    baseline_usage = _dict(
        baseline_metrics.get("usage_per_run_mean"),
        "baseline usage_per_run_mean",
    )
    candidate_usage = _dict(
        candidate_metrics.get("usage_per_run_mean"),
        "candidate usage_per_run_mean",
    )

    same_provider_contract = _non_empty_hashes(
        baseline.get("provider_contract_sha256s"),
        "baseline provider contracts",
    ) == _non_empty_hashes(
        candidate.get("provider_contract_sha256s"),
        "candidate provider contracts",
    )
    same_fixture_contract = _non_empty_hashes(
        baseline.get("fixture_contract_sha256s"),
        "baseline fixture contracts",
    ) == _non_empty_hashes(
        candidate.get("fixture_contract_sha256s"),
        "candidate fixture contracts",
    )
    baseline_has_pair = (
        _number(baseline_modes.get("legacy"), "baseline legacy count") >= 1
        and _number(baseline_modes.get("pipeline"), "baseline pipeline count") >= 1
    )
    candidate_has_pair = (
        _number(candidate_modes.get("legacy"), "candidate legacy count") >= 1
        and _number(candidate_modes.get("pipeline"), "candidate pipeline count") >= 1
    )

    rate_names = (
        "terminal_validation_failure_rate",
        "validation_retry_run_rate",
        "model_prompt_identity_output_rate",
        "semantic_routing_conflict_rate",
    )
    rate_deltas = {
        name: _number(candidate_metrics.get(name), f"candidate {name}")
        - _number(baseline_metrics.get(name), f"baseline {name}")
        for name in rate_names
    }
    terminal_non_regression = rate_deltas["terminal_validation_failure_rate"] <= 0
    retry_non_regression = rate_deltas["validation_retry_run_rate"] <= 0
    identity_non_regression = rate_deltas["model_prompt_identity_output_rate"] <= 0
    conflict_non_regression = rate_deltas["semantic_routing_conflict_rate"] <= 0

    baseline_prompt_tokens = _number(
        baseline_usage.get("prompt_tokens"),
        "baseline mean prompt_tokens",
    )
    candidate_prompt_tokens = _number(
        candidate_usage.get("prompt_tokens"),
        "candidate mean prompt_tokens",
    )
    prompt_token_delta = candidate_prompt_tokens - baseline_prompt_tokens
    prompt_token_delta_ratio = (
        prompt_token_delta / baseline_prompt_tokens if baseline_prompt_tokens else 0.0
    )
    prompt_token_non_regression = prompt_token_delta_ratio <= max_prompt_token_regression_ratio

    baseline_valid = _required_aggregate_gates(baseline)
    candidate_valid = _required_aggregate_gates(candidate)
    live_gate_passed = all(
        (
            baseline_valid,
            candidate_valid,
            baseline_has_pair,
            candidate_has_pair,
            same_provider_contract,
            same_fixture_contract,
            terminal_non_regression,
            retry_non_regression,
            identity_non_regression,
            conflict_non_regression,
            prompt_token_non_regression,
        )
    )
    return {
        "schema": LIVE_COMPARISON_SCHEMA,
        "baseline_contract_version": str(baseline.get("contract_version") or ""),
        "candidate_contract_version": str(candidate.get("contract_version") or ""),
        "observation_counts": {
            "baseline": int(
                _number(baseline.get("observation_count"), "baseline observation_count")
            ),
            "candidate": int(
                _number(candidate.get("observation_count"), "candidate observation_count")
            ),
        },
        "deltas": {
            **rate_deltas,
            "mean_prompt_tokens": prompt_token_delta,
            "mean_prompt_tokens_ratio": prompt_token_delta_ratio,
            "mean_completion_tokens": _number(
                candidate_usage.get("completion_tokens"),
                "candidate mean completion_tokens",
            )
            - _number(
                baseline_usage.get("completion_tokens"),
                "baseline mean completion_tokens",
            ),
            "mean_total_tokens": _number(
                candidate_usage.get("total_tokens"),
                "candidate mean total_tokens",
            )
            - _number(
                baseline_usage.get("total_tokens"),
                "baseline mean total_tokens",
            ),
        },
        "thresholds": {
            "max_mean_prompt_token_regression_ratio": max_prompt_token_regression_ratio,
        },
        "gates": {
            "baseline_valid": baseline_valid,
            "candidate_valid": candidate_valid,
            "baseline_has_legacy_pipeline_pair": baseline_has_pair,
            "candidate_has_legacy_pipeline_pair": candidate_has_pair,
            "same_provider_contract": same_provider_contract,
            "same_fixture_contract": same_fixture_contract,
            "terminal_validation_non_regression": terminal_non_regression,
            "validation_retry_non_regression": retry_non_regression,
            "model_prompt_identity_output_non_regression": identity_non_regression,
            "semantic_routing_conflict_non_regression": conflict_non_regression,
            "prompt_token_non_regression": prompt_token_non_regression,
            "live_gate_passed": live_gate_passed,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--max-prompt-token-regression-ratio",
        type=float,
        default=MAX_PROMPT_TOKEN_REGRESSION_RATIO,
    )
    args = parser.parse_args(argv)
    try:
        report = compare_live_prompt_contracts(
            _load_report(args.baseline, "baseline"),
            _load_report(args.candidate, "candidate"),
            max_prompt_token_regression_ratio=args.max_prompt_token_regression_ratio,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": LIVE_COMPARISON_SCHEMA,
                    "valid": False,
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["gates"]["live_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
