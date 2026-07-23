"""Compare sanitized legacy and Pipeline live observation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.validate_live_observation import (  # noqa: E402
    _load_json_object,
    validate_live_observation,
)

PAIR_VALIDATION_SCHEMA = "pa-agent.live-observation-pair-validation.v1"
_REQUIRED_RECORD_FIELDS = {
    "exception",
    "experience_loaded",
    "htf_text",
    "kline_data",
    "meta",
    "stage1_diagnosis",
    "stage1_messages",
    "stage1_response",
    "stage2_decision",
    "stage2_messages",
    "stage2_response",
    "strategy_files_used",
    "usage_total",
}
_REQUIRED_META_FIELDS = {
    "ai_provider",
    "bar_count",
    "decision_stance",
    "symbol",
    "timeframe",
    "timestamp_local_iso",
    "timestamp_local_ms",
}


def compare_live_observations(
    *,
    legacy_summary_path: Path,
    legacy_events_path: Path,
    legacy_records_dir: Path,
    pipeline_summary_path: Path,
    pipeline_events_path: Path,
    pipeline_records_dir: Path,
) -> dict[str, object]:
    """Validate and compare a legacy/Pipeline live observation pair."""
    legacy_validation = validate_live_observation(
        summary_path=legacy_summary_path,
        events_path=legacy_events_path,
        records_dir=legacy_records_dir,
    )
    pipeline_validation = validate_live_observation(
        summary_path=pipeline_summary_path,
        events_path=pipeline_events_path,
        records_dir=pipeline_records_dir,
    )
    legacy_summary = _load_json_object(legacy_summary_path, "legacy summary")
    pipeline_summary = _load_json_object(pipeline_summary_path, "pipeline summary")

    if legacy_summary.get("pipeline_builder_enabled") is not False:
        raise ValueError("legacy observation must disable Pipeline")
    if pipeline_summary.get("pipeline_builder_enabled") is not True:
        raise ValueError("pipeline observation must enable Pipeline")
    if legacy_summary.get("provider_called") is not True:
        raise ValueError("legacy observation did not call the Provider")
    if pipeline_summary.get("provider_called") is not True:
        raise ValueError("pipeline observation did not call the Provider")

    legacy_correlation_id = str(legacy_validation["correlation_id"])
    pipeline_correlation_id = str(pipeline_validation["correlation_id"])
    if legacy_correlation_id == pipeline_correlation_id:
        raise ValueError("legacy and Pipeline observations require distinct correlation ids")

    _require_equal("terminal status", legacy_summary.get("status"), pipeline_summary.get("status"))
    _require_equal(
        "exception type",
        legacy_summary.get("exception_type"),
        pipeline_summary.get("exception_type"),
    )
    _require_equal("event sequence", legacy_summary.get("events"), pipeline_summary.get("events"))
    _require_equal(
        "record write outcome",
        legacy_summary.get("record_written"),
        pipeline_summary.get("record_written"),
    )

    legacy_contract = _load_record_contract(legacy_records_dir, legacy_summary)
    pipeline_contract = _load_record_contract(pipeline_records_dir, pipeline_summary)
    _require_equal("record structure", legacy_contract, pipeline_contract)

    return {
        "schema": PAIR_VALIDATION_SCHEMA,
        "valid": True,
        "legacy_correlation_id": legacy_correlation_id,
        "pipeline_correlation_id": pipeline_correlation_id,
        "status": legacy_summary["status"],
        "exception_type": legacy_summary.get("exception_type"),
        "event_count": legacy_validation["event_count"],
        "events": list(legacy_summary["events"]),
        "record_written": legacy_validation["record_written"],
        "record_contract": legacy_contract,
    }


def _require_equal(label: str, legacy_value: Any, pipeline_value: Any) -> None:
    if legacy_value != pipeline_value:
        raise ValueError(f"legacy/Pipeline {label} mismatch")


def _load_record_contract(
    records_dir: Path,
    summary: dict[str, object],
) -> dict[str, object] | None:
    if summary.get("record_written") is not True:
        return None
    record_file = summary.get("record_file")
    if not isinstance(record_file, str) or not record_file:
        raise ValueError("record_file is required for record contract comparison")
    record_path = (Path(records_dir) / record_file).resolve()
    record = _load_json_object(record_path, "record")
    missing_fields = sorted(_REQUIRED_RECORD_FIELDS.difference(record))
    if missing_fields:
        raise ValueError("record is missing required fields")

    meta = record.get("meta")
    if not isinstance(meta, dict) or _REQUIRED_META_FIELDS.difference(meta):
        raise ValueError("record meta is missing required fields")
    kline_data = record.get("kline_data")
    if not isinstance(kline_data, list):
        raise ValueError("record kline_data must be an array")

    exception = record.get("exception")
    if exception is not None and not isinstance(exception, dict):
        raise ValueError("record exception must be an object or null")
    usage_total = record.get("usage_total")
    if not isinstance(usage_total, dict):
        raise ValueError("record usage_total must be an object")

    return {
        "record_fields": sorted(record),
        "meta_fields": sorted(meta),
        "bar_count": _non_negative_int(meta.get("bar_count"), "record meta bar_count"),
        "kline_bar_count": len(kline_data),
        "stage1_message_roles": _message_roles(record.get("stage1_messages"), "stage1"),
        "stage2_message_roles": _message_roles(record.get("stage2_messages"), "stage2"),
        "payload_presence": {
            "stage1_response": record.get("stage1_response") is not None,
            "stage1_diagnosis": record.get("stage1_diagnosis") is not None,
            "stage2_response": record.get("stage2_response") is not None,
            "stage2_decision": record.get("stage2_decision") is not None,
        },
        "exception_fields": sorted(exception) if exception is not None else [],
        "exception_type": exception.get("type") if exception is not None else None,
        "exception_stage": exception.get("stage") if exception is not None else None,
        "usage_fields": sorted(usage_total),
    }


def _message_roles(value: object, stage: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"record {stage}_messages must be an array")
    roles: list[str] = []
    for message in value:
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            raise ValueError(f"record {stage}_messages must contain role objects")
        roles.append(str(message["role"]))
    return roles


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-summary", type=Path, required=True)
    parser.add_argument("--legacy-events", type=Path, required=True)
    parser.add_argument("--legacy-records-dir", type=Path, required=True)
    parser.add_argument("--pipeline-summary", type=Path, required=True)
    parser.add_argument("--pipeline-events", type=Path, required=True)
    parser.add_argument("--pipeline-records-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_live_observations(
            legacy_summary_path=args.legacy_summary,
            legacy_events_path=args.legacy_events,
            legacy_records_dir=args.legacy_records_dir,
            pipeline_summary_path=args.pipeline_summary,
            pipeline_events_path=args.pipeline_events,
            pipeline_records_dir=args.pipeline_records_dir,
        )
    except ValueError as exc:
        print(
            json.dumps(
                {"schema": PAIR_VALIDATION_SCHEMA, "valid": False, "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
