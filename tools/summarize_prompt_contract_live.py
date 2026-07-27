"""Summarize live Prompt-contract artifacts without exposing raw content."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.ai.json_repair import format_model_json_for_context  # noqa: E402
from pa_agent.ai.prompting import TEMPLATE_CATALOG, PromptCatalogError  # noqa: E402
from pa_agent.ai.router import route_strategy_files  # noqa: E402
from tools.validate_live_observation import (  # noqa: E402
    _load_json_object,
    validate_live_observation,
)

LIVE_AGGREGATE_SCHEMA = "pa-agent.prompt-contract-live-aggregate.v1"
_USAGE_KEYS = (
    "prompt_tokens",
    "cached_prompt_tokens",
    "completion_tokens",
    "total_tokens",
)
_PROVIDER_CONTRACT_KEYS = (
    "base_url",
    "model",
    "thinking",
    "reasoning_effort",
)
_IDENTITY_FIELDS = (
    "strategy_files_needed",
    "recommended_strategy_files",
)


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _usage_counts(record: dict[str, object]) -> dict[str, int]:
    usage = record.get("usage_total")
    if not isinstance(usage, dict):
        raise ValueError("record usage_total must be an object")
    return {key: _non_negative_int(usage.get(key, 0), f"usage_total.{key}") for key in _USAGE_KEYS}


def _raw_stage1_object(record: dict[str, object]) -> dict[str, Any] | None:
    response = record.get("stage1_response")
    if not isinstance(response, dict):
        return None
    content = response.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    formatted = format_model_json_for_context(content)
    if not formatted:
        return None
    try:
        value = json.loads(formatted)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _canonical_strategy_files(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    resolved: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            continue
        name = item.strip()
        try:
            prompt_id = TEMPLATE_CATALOG.resolve_legacy_filename(name)
            name = TEMPLATE_CATALOG.legacy_filename(prompt_id)
        except PromptCatalogError:
            pass
        if name not in resolved:
            resolved.append(name)
    return resolved


def _routing_identity_metrics(record: dict[str, object]) -> dict[str, bool]:
    raw = _raw_stage1_object(record)
    parseable = raw is not None
    if raw is None:
        return {
            "raw_stage1_json_parseable": False,
            "model_prompt_identity_output": False,
            "semantic_routing_conflict": False,
            "routing_comparable": False,
        }

    identity_present = any(field in raw for field in _IDENTITY_FIELDS)
    diagnosis = record.get("stage1_diagnosis")
    if not isinstance(diagnosis, dict):
        return {
            "raw_stage1_json_parseable": parseable,
            "model_prompt_identity_output": identity_present,
            "semantic_routing_conflict": identity_present,
            "routing_comparable": False,
        }
    try:
        expected = route_strategy_files(diagnosis)
    except Exception:
        return {
            "raw_stage1_json_parseable": parseable,
            "model_prompt_identity_output": identity_present,
            "semantic_routing_conflict": identity_present,
            "routing_comparable": False,
        }

    suggestions: list[str] | None = None
    if identity_present:
        suggestions = _canonical_strategy_files(raw.get("strategy_files_needed"))
        if suggestions is None:
            suggestions = _canonical_strategy_files(raw.get("recommended_strategy_files"))
    return {
        "raw_stage1_json_parseable": parseable,
        "model_prompt_identity_output": identity_present,
        "semantic_routing_conflict": identity_present and suggestions != expected,
        "routing_comparable": True,
    }


def _terminal_validation_failure(
    summary: dict[str, object],
    record: dict[str, object],
) -> bool:
    exception = record.get("exception")
    if not isinstance(exception, dict):
        return False
    category = str(exception.get("category") or "").lower()
    exception_type = str(exception.get("type") or summary.get("exception_type") or "").lower()
    stage = str(exception.get("stage") or "").lower()
    return (
        category in {"a", "b", "c", "d"}
        or "validation" in exception_type
        or exception_type.startswith(("stage1_", "stage2_"))
        or (stage in {"stage1", "stage2"} and category != "")
    )


def _contract_hashes(record: dict[str, object]) -> tuple[str, str]:
    meta = record.get("meta")
    if not isinstance(meta, dict):
        raise ValueError("record meta must be an object")
    provider = meta.get("ai_provider")
    if not isinstance(provider, dict):
        raise ValueError("record meta.ai_provider must be an object")
    provider_contract = {
        key: provider.get(key) for key in _PROVIDER_CONTRACT_KEYS if key in provider
    }
    fixture_contract = {
        "bar_count": meta.get("bar_count"),
        "timeframe": meta.get("timeframe"),
        "htf_text": record.get("htf_text"),
        "kline_data": record.get("kline_data"),
    }
    return _sha256_json(provider_contract), _sha256_json(fixture_contract)


def summarize_live_observation(
    *,
    summary_path: Path,
    events_path: Path,
    records_dir: Path,
) -> dict[str, object]:
    """Return aggregate-safe metrics for one validated live observation."""
    validation = validate_live_observation(
        summary_path=summary_path,
        events_path=events_path,
        records_dir=records_dir,
    )
    summary = _load_json_object(summary_path, "summary")
    if validation.get("record_written") is not True:
        raise ValueError("Prompt contract observation requires a written record")
    record_file = validation.get("record_file")
    if not isinstance(record_file, str) or not record_file:
        raise ValueError("Prompt contract observation record_file is missing")
    record = _load_json_object(Path(records_dir) / record_file, "record")

    events = summary.get("events")
    if not isinstance(events, list) or not all(isinstance(item, str) for item in events):
        raise ValueError("summary events must be an array of strings")
    stage1_retries = events.count("Stage1Retry")
    stage2_retries = events.count("Stage2Retry")
    identity = _routing_identity_metrics(record)
    provider_hash, fixture_hash = _contract_hashes(record)
    return {
        "pipeline_builder_enabled": bool(summary.get("pipeline_builder_enabled", False)),
        "completed": summary.get("status") == "completed",
        "provider_called": summary.get("provider_called") is True,
        "terminal_validation_failure": _terminal_validation_failure(summary, record),
        "stage1_retry_count": stage1_retries,
        "stage2_retry_count": stage2_retries,
        "validation_retry_count": stage1_retries + stage2_retries,
        "usage_counts": _usage_counts(record),
        "provider_contract_sha256": provider_hash,
        "fixture_contract_sha256": fixture_hash,
        **identity,
    }


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def aggregate_live_observations(
    *,
    observations_root: Path,
    contract_version: str,
) -> dict[str, object]:
    """Validate and aggregate every live summary below *observations_root*."""
    root = Path(observations_root)
    if not contract_version.strip():
        raise ValueError("contract_version must not be empty")
    summary_paths = sorted(root.rglob("summary.json"))
    if not summary_paths:
        raise ValueError("no live observation summaries found")

    observations: list[dict[str, object]] = []
    for summary_path in summary_paths:
        summary = _load_json_object(summary_path, "summary")
        event_file = summary.get("event_file")
        if not isinstance(event_file, str) or not event_file or Path(event_file).name != event_file:
            raise ValueError("summary event_file must be a local filename")
        observations.append(
            summarize_live_observation(
                summary_path=summary_path,
                events_path=summary_path.parent / event_file,
                records_dir=summary_path.parent / "records",
            )
        )

    count = len(observations)
    completed = sum(bool(item["completed"]) for item in observations)
    provider_called = sum(bool(item["provider_called"]) for item in observations)
    terminal_failures = sum(bool(item["terminal_validation_failure"]) for item in observations)
    stage1_retries = sum(int(item["stage1_retry_count"]) for item in observations)
    stage2_retries = sum(int(item["stage2_retry_count"]) for item in observations)
    retry_count = stage1_retries + stage2_retries
    runs_with_retry = sum(int(item["validation_retry_count"]) > 0 for item in observations)
    parseable = sum(bool(item["raw_stage1_json_parseable"]) for item in observations)
    identity_outputs = sum(bool(item["model_prompt_identity_output"]) for item in observations)
    comparable = sum(bool(item["routing_comparable"]) for item in observations)
    conflicts = sum(bool(item["semantic_routing_conflict"]) for item in observations)
    usage_totals = {
        key: sum(int(item["usage_counts"][key]) for item in observations) for key in _USAGE_KEYS
    }
    provider_hashes = sorted({str(item["provider_contract_sha256"]) for item in observations})
    fixture_hashes = sorted({str(item["fixture_contract_sha256"]) for item in observations})
    legacy_count = sum(not bool(item["pipeline_builder_enabled"]) for item in observations)
    pipeline_count = count - legacy_count

    return {
        "schema": LIVE_AGGREGATE_SCHEMA,
        "contract_version": contract_version.strip(),
        "observation_count": count,
        "execution_modes": {
            "legacy": legacy_count,
            "pipeline": pipeline_count,
        },
        "provider_contract_sha256s": provider_hashes,
        "fixture_contract_sha256s": fixture_hashes,
        "metrics": {
            "completed_runs": completed,
            "completed_rate": _rate(completed, count),
            "provider_called_runs": provider_called,
            "provider_called_rate": _rate(provider_called, count),
            "terminal_validation_failures": terminal_failures,
            "terminal_validation_failure_rate": _rate(terminal_failures, count),
            "stage1_retry_count": stage1_retries,
            "stage2_retry_count": stage2_retries,
            "validation_retry_count": retry_count,
            "runs_with_validation_retry": runs_with_retry,
            "validation_retry_run_rate": _rate(runs_with_retry, count),
            "raw_stage1_json_parseable_runs": parseable,
            "raw_stage1_json_parseable_rate": _rate(parseable, count),
            "routing_comparable_runs": comparable,
            "model_prompt_identity_output_runs": identity_outputs,
            "model_prompt_identity_output_rate": _rate(identity_outputs, count),
            "semantic_routing_conflicts": conflicts,
            "semantic_routing_conflict_rate": _rate(conflicts, count),
            "usage_totals": usage_totals,
            "usage_per_run_mean": {key: value / count for key, value in usage_totals.items()},
        },
        "gates": {
            "all_artifacts_valid": True,
            "all_runs_completed": completed == count,
            "all_runs_called_provider": provider_called == count,
            "all_stage1_json_parseable": parseable == count,
            "single_provider_contract": len(provider_hashes) == 1,
            "single_fixture_contract": len(fixture_hashes) == 1,
            "aggregate_only": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations-root", type=Path, required=True)
    parser.add_argument("--contract-version", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = aggregate_live_observations(
            observations_root=args.observations_root,
            contract_version=args.contract_version,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": LIVE_AGGREGATE_SCHEMA,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
