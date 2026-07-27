"""Evaluate M4 Prompt contract drift against the frozen M3.3 baseline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.ai.prompt_assembler import PromptAssembler  # noqa: E402
from pa_agent.ai.prompting.template_manifest import MANIFEST_VERSION  # noqa: E402
from pa_agent.ai.prompts.schemas import (  # noqa: E402
    STAGE1_SCHEMA,
    STAGE1_SCHEMA_VERSION,
)
from pa_agent.ai.router import route_strategy_files  # noqa: E402
from pa_agent.ai.stage1_normalizer import normalize_stage1  # noqa: E402
from pa_agent.ai.token_counter import estimate_tokens  # noqa: E402
from pa_agent.data.snapshot import build_analysis_frame  # noqa: E402
from tests.fixtures.kline_bars import make_newest_first_bars  # noqa: E402
from tests.integration.conftest import VALID_STAGE1  # noqa: E402

REPORT_SCHEMA = "pa-agent.prompt-contract-evaluation.v1"
BASELINE_SCHEMA = "pa-agent.prompt-contract-baseline.v1"
TOKENIZER_PACKAGE = "tiktoken"
TOKENIZER_ENCODING = "cl100k_base"
MAX_TOKEN_REGRESSION_RATIO = 0.001
_FIXTURE_KEYS = (
    "symbol",
    "timeframe",
    "bar_count",
    "stage1_json",
    "strategy_files",
    "reply",
)


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_baseline(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != BASELINE_SCHEMA:
        raise ValueError("unsupported Prompt contract baseline schema")
    if not isinstance(payload.get("prompt_metrics"), dict):
        raise ValueError("baseline prompt_metrics must be an object")
    if not isinstance(payload.get("contract_metrics"), dict):
        raise ValueError("baseline contract_metrics must be an object")
    if not isinstance(payload.get("tokenizer"), dict):
        raise ValueError("baseline tokenizer must be an object")
    return payload


def _load_prompt_fixture(root: Path) -> tuple[dict[str, Any], str]:
    fixture_path = root / "tests" / "fixtures" / "prompt_golden.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture = payload.get("stage2_fixture")
    if not isinstance(fixture, dict):
        raise ValueError("prompt golden stage2_fixture must be an object")
    fixture_inputs = {key: fixture[key] for key in _FIXTURE_KEYS}
    return fixture, _sha256_json(fixture_inputs)


def _prompt_metric(messages: list[dict[str, Any]]) -> dict[str, object]:
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    return {
        "message_count": len(messages),
        "byte_length": sum(len(str(item["content"]).encode("utf-8")) for item in messages),
        "char_length": sum(len(str(item["content"])) for item in messages),
        "estimated_tokens": estimate_tokens(messages, TOKENIZER_ENCODING),
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _build_prompt_metrics(root: Path, fixture: dict[str, Any]) -> dict[str, dict[str, object]]:
    frame = build_analysis_frame(
        make_newest_first_bars(int(fixture["bar_count"]), with_forming=False),
        20,
        str(fixture["symbol"]),
        str(fixture["timeframe"]),
    )
    if frame is None:
        raise ValueError("fixed Prompt evaluation frame could not be built")

    assembler = PromptAssembler(prompt_dir=root / "prompt_engineering")
    stage1 = assembler.build_stage1(frame)
    standalone = assembler.build_stage2(
        frame,
        fixture["stage1_json"],
        fixture["strategy_files"],
        [],
    )
    continuation_kwargs = {
        "frame": frame,
        "stage1_messages": stage1,
        "stage1_reply_content": fixture["reply"],
        "stage1_json": fixture["stage1_json"],
        "strategy_files": fixture["strategy_files"],
        "experience_entries": [],
    }
    variants = {
        "stage1": stage1,
        "stage2_standalone": standalone,
        "stage2_continuation_standalone": assembler.build_stage2_continuation(
            **continuation_kwargs,
            use_prefix_chain=False,
        ),
        "stage2_continuation_prefix": assembler.build_stage2_continuation(
            **continuation_kwargs,
            use_prefix_chain=True,
        ),
    }
    return {name: _prompt_metric(messages) for name, messages in variants.items()}


def _routing_contract_cases() -> list[dict[str, Any]]:
    base = copy.deepcopy(VALID_STAGE1)
    expected_files = route_strategy_files(base)

    matching = copy.deepcopy(base)
    matching["strategy_files_needed"] = expected_files

    no_identity = copy.deepcopy(base)
    no_identity.pop("strategy_files_needed", None)

    conflicting = copy.deepcopy(base)
    conflicting["strategy_files_needed"] = ["下跌通道分析识别.txt"]

    alias_conflicting = copy.deepcopy(base)
    alias_conflicting.pop("strategy_files_needed", None)
    alias_conflicting["recommended_strategy_files"] = ["下跌通道分析识别.txt"]
    return [matching, no_identity, conflicting, alias_conflicting]


def _with_rates(metrics: dict[str, int]) -> dict[str, int | float]:
    case_count = metrics["case_count"]
    if case_count <= 0:
        raise ValueError("Prompt contract corpus must contain at least one case")
    return {
        **metrics,
        "schema_validation_failure_rate": metrics["schema_validation_failures"] / case_count,
        "retry_required_rate": metrics["retry_required"] / case_count,
        "semantic_routing_conflict_rate": metrics["semantic_routing_conflicts"] / case_count,
    }


def _build_candidate_contract_metrics() -> dict[str, int | float]:
    validator = Draft7Validator(STAGE1_SCHEMA)
    cases = _routing_contract_cases()
    schema_failures = 0
    routing_conflicts = 0
    identity_output_cases = 0
    for payload in cases:
        identity_output_cases += int(
            "strategy_files_needed" in payload or "recommended_strategy_files" in payload
        )
        normalized = normalize_stage1(payload)
        schema_failures += int(not validator.is_valid(normalized))
        routing_conflicts += int(
            normalized.get("strategy_files_needed") != route_strategy_files(normalized)
        )
    return _with_rates(
        {
            "case_count": len(cases),
            "identity_output_cases": identity_output_cases,
            "schema_validation_failures": schema_failures,
            "retry_required": schema_failures,
            "semantic_routing_conflicts": routing_conflicts,
        }
    )


def _prompt_deltas(
    baseline: dict[str, Any],
    candidate: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, int | float | bool]], dict[str, int | float]]:
    if set(baseline) != set(candidate):
        raise ValueError("baseline and candidate Prompt variants do not match")
    deltas: dict[str, dict[str, int | float | bool]] = {}
    baseline_total = 0
    candidate_total = 0
    for name in sorted(candidate):
        old = baseline[name]
        new = candidate[name]
        old_tokens = int(old["estimated_tokens"])
        new_tokens = int(new["estimated_tokens"])
        baseline_total += old_tokens
        candidate_total += new_tokens
        deltas[name] = {
            "message_count_changed": int(old["message_count"]) != int(new["message_count"]),
            "byte_length_delta": int(new["byte_length"]) - int(old["byte_length"]),
            "char_length_delta": int(new["char_length"]) - int(old["char_length"]),
            "estimated_token_delta": new_tokens - old_tokens,
            "estimated_token_delta_ratio": (
                (new_tokens - old_tokens) / old_tokens if old_tokens else 0.0
            ),
            "sha256_changed": str(old["sha256"]) != str(new["sha256"]),
        }
    aggregate = {
        "baseline_estimated_tokens": baseline_total,
        "candidate_estimated_tokens": candidate_total,
        "estimated_token_delta": candidate_total - baseline_total,
        "estimated_token_delta_ratio": (
            (candidate_total - baseline_total) / baseline_total if baseline_total else 0.0
        ),
    }
    return deltas, aggregate


def build_report(
    *,
    root: Path = ROOT,
    baseline_path: Path | None = None,
    live_api_key_present: bool | None = None,
) -> dict[str, object]:
    """Build an aggregate-only M4 contract evaluation report."""
    root = Path(root)
    baseline_path = baseline_path or (
        root / "tests" / "fixtures" / "prompt_contract_m3_baseline.json"
    )
    baseline = _load_baseline(baseline_path)
    fixture, fixture_sha256 = _load_prompt_fixture(root)
    candidate_prompt_metrics = _build_prompt_metrics(root, fixture)
    candidate_contract_metrics = _build_candidate_contract_metrics()
    baseline_contract_metrics = _with_rates(
        {key: int(value) for key, value in baseline["contract_metrics"].items()}
    )

    installed_tokenizer_version = version(TOKENIZER_PACKAGE)
    tokenizer = baseline["tokenizer"]
    tokenizer_comparable = (
        tokenizer.get("package") == TOKENIZER_PACKAGE
        and tokenizer.get("encoding") == TOKENIZER_ENCODING
        and tokenizer.get("version") == installed_tokenizer_version
    )
    fixture_unchanged = baseline.get("fixture_input_sha256") == fixture_sha256
    prompt_deltas, aggregate_delta = _prompt_deltas(
        baseline["prompt_metrics"],
        candidate_prompt_metrics,
    )

    schema_non_regression = (
        candidate_contract_metrics["schema_validation_failure_rate"]
        <= baseline_contract_metrics["schema_validation_failure_rate"]
    )
    retry_non_regression = (
        candidate_contract_metrics["retry_required_rate"]
        <= baseline_contract_metrics["retry_required_rate"]
    )
    routing_conflict_non_regression = (
        candidate_contract_metrics["semantic_routing_conflict_rate"]
        <= baseline_contract_metrics["semantic_routing_conflict_rate"]
    )
    token_non_regression = all(
        not metrics["message_count_changed"]
        and float(metrics["estimated_token_delta_ratio"]) <= MAX_TOKEN_REGRESSION_RATIO
        for metrics in prompt_deltas.values()
    )
    offline_gate_passed = all(
        (
            fixture_unchanged,
            tokenizer_comparable,
            schema_non_regression,
            retry_non_regression,
            routing_conflict_non_regression,
            token_non_regression,
        )
    )

    if live_api_key_present is None:
        live_api_key_present = bool(os.environ.get("PA_AGENT_LIVE_API_KEY", "").strip())
    live_status = "ready" if live_api_key_present else "blocked_missing_session_api_key"
    live_evidence_collected = False

    return {
        "schema": REPORT_SCHEMA,
        "baseline": {
            "name": baseline["baseline"],
            "source_commit": baseline["source_commit"],
            "fixture_input_sha256": baseline["fixture_input_sha256"],
            "tokenizer": baseline["tokenizer"],
            "prompt_metrics": baseline["prompt_metrics"],
            "contract_metrics": baseline_contract_metrics,
        },
        "candidate": {
            "name": "m4.2",
            "manifest_version": MANIFEST_VERSION,
            "stage1_schema_version": STAGE1_SCHEMA_VERSION,
            "fixture_input_sha256": fixture_sha256,
            "tokenizer": {
                "package": TOKENIZER_PACKAGE,
                "version": installed_tokenizer_version,
                "encoding": TOKENIZER_ENCODING,
            },
            "prompt_metrics": candidate_prompt_metrics,
            "contract_metrics": candidate_contract_metrics,
        },
        "deltas": {
            "prompt_variants": prompt_deltas,
            "prompt_aggregate": aggregate_delta,
            "schema_validation_failure_rate": (
                candidate_contract_metrics["schema_validation_failure_rate"]
                - baseline_contract_metrics["schema_validation_failure_rate"]
            ),
            "retry_required_rate": (
                candidate_contract_metrics["retry_required_rate"]
                - baseline_contract_metrics["retry_required_rate"]
            ),
            "semantic_routing_conflict_rate": (
                candidate_contract_metrics["semantic_routing_conflict_rate"]
                - baseline_contract_metrics["semantic_routing_conflict_rate"]
            ),
        },
        "thresholds": {
            "max_token_regression_ratio_per_prompt_variant": MAX_TOKEN_REGRESSION_RATIO,
        },
        "gates": {
            "fixture_unchanged": fixture_unchanged,
            "tokenizer_comparable": tokenizer_comparable,
            "schema_validation_non_regression": schema_non_regression,
            "retry_non_regression": retry_non_regression,
            "semantic_routing_conflict_non_regression": routing_conflict_non_regression,
            "token_non_regression": token_non_regression,
            "offline_gate_passed": offline_gate_passed,
            "m4_exit_gate_passed": offline_gate_passed and live_evidence_collected,
        },
        "live_observation": {
            "status": live_status,
            "evidence_collected": live_evidence_collected,
            "runbook": "docs/live_observation_runbook.md",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "prompt_contract_m3_baseline.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_report(root=ROOT, baseline_path=args.baseline)
    except (KeyError, OSError, PackageNotFoundError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": REPORT_SCHEMA,
                    "offline_gate_passed": False,
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
    return 0 if report["gates"]["offline_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
