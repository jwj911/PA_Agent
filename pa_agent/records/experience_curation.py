"""Curate completed analysis records into local experience cases."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pa_agent.ai.cycle_enums import CYCLE_POSITION_ZH
from pa_agent.records.schema import AnalysisRecord
from pa_agent.util.mask_secret import mask_secret

EXPERIENCE_CURATION_SCHEMA = "pa-agent.experience-curation.v1"
EXPERIENCE_CURATION_SCAN_SCHEMA = "pa-agent.experience-curation-scan.v1"
CURATED_EXPERIENCE_CASE_SCHEMA = "pa-agent.curated-experience-case.v1"

_VALID_OUTCOMES = frozenset({"success", "failure"})
_REASON_ELIGIBLE = "eligible"
_REASON_INVALID_JSON = "invalid_json"
_REASON_INVALID_RECORD = "invalid_record"
_REASON_PARTIAL_RECORD = "partial_record"
_REASON_INCOMPLETE_ANALYSIS = "incomplete_analysis"
_REASON_INVALID_CYCLE = "invalid_cycle_position"
_REASON_INVALID_DIRECTION = "invalid_direction"
_REASON_INVALID_PATTERNS = "invalid_patterns"
_REASON_INVALID_KLINE = "invalid_kline_data"


def scan_record_directory(records_dir: Path) -> dict[str, object]:
    """Return a shape-only eligibility summary for local analysis records."""
    paths = sorted(Path(records_dir).rglob("*.json"), key=lambda path: path.as_posix())
    reasons: Counter[str] = Counter()
    cycles: Counter[str] = Counter()
    for path in paths:
        reason, record = _inspect_record(path)
        reasons[reason] += 1
        if reason == _REASON_ELIGIBLE and record is not None:
            diagnosis = record.stage1_diagnosis or {}
            cycles[str(diagnosis["cycle_position"])] += 1
    return {
        "schema": EXPERIENCE_CURATION_SCAN_SCHEMA,
        "record_count": len(paths),
        "eligible_count": reasons[_REASON_ELIGIBLE],
        "reason_counts": dict(sorted(reasons.items())),
        "cycle_position_counts": dict(sorted(cycles.items())),
    }


def curate_record(
    record_path: Path,
    experience_dir: Path,
    *,
    outcome: str,
    sensitive_values: Iterable[str] = (),
) -> dict[str, object]:
    """Write one explicitly labeled, minimal experience case.

    The caller must provide the observed trade outcome. Existing cases are
    idempotent; changing the outcome or cycle for the same record is rejected.
    """
    normalized_outcome = str(outcome or "").strip().lower()
    if normalized_outcome not in _VALID_OUTCOMES:
        raise ValueError("experience outcome must be success or failure")

    reason, record = _inspect_record(Path(record_path))
    if reason != _REASON_ELIGIBLE or record is None:
        raise ValueError(f"analysis record is not eligible: {reason}")

    diagnosis = dict(record.stage1_diagnosis or {})
    cycle_position = str(diagnosis["cycle_position"])
    payload = _build_case_payload(
        record,
        diagnosis,
        outcome=normalized_outcome,
        sensitive_values=sensitive_values,
    )
    digest = _record_digest(payload)
    payload["meta"]["record_digest"] = digest
    timestamp = _timestamp_key(record.meta.timestamp_local_ms)
    filename = f"{timestamp}_record-{digest[:16]}.json"
    target = Path(experience_dir) / cycle_position / f"{normalized_outcome}_cases" / filename

    conflicts = sorted(Path(experience_dir).glob(f"*/*_cases/*_record-{digest[:16]}.json"))
    if conflicts:
        if len(conflicts) == 1 and conflicts[0].resolve() == target.resolve():
            existing = _load_json_object(conflicts[0])
            if existing == payload:
                return _curation_result(
                    target,
                    cycle_position=cycle_position,
                    outcome=normalized_outcome,
                    digest=digest,
                    imported=False,
                )
        raise ValueError("analysis record already curated with conflicting metadata")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return _curation_result(
        target,
        cycle_position=cycle_position,
        outcome=normalized_outcome,
        digest=digest,
        imported=True,
    )


def _inspect_record(path: Path) -> tuple[str, AnalysisRecord | None]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _REASON_INVALID_JSON, None
    if not isinstance(raw, dict):
        return _REASON_INVALID_RECORD, None
    if "_partial_reason" in raw or raw.get("exception") is not None:
        return _REASON_PARTIAL_RECORD, None
    try:
        record = AnalysisRecord.model_validate(raw)
    except ValidationError:
        return _REASON_INVALID_RECORD, None
    if record.stage1_diagnosis is None or record.stage2_decision is None:
        return _REASON_INCOMPLETE_ANALYSIS, None

    diagnosis = record.stage1_diagnosis
    cycle_position = str(diagnosis.get("cycle_position") or "").strip().lower()
    if cycle_position not in CYCLE_POSITION_ZH:
        return _REASON_INVALID_CYCLE, None
    diagnosis["cycle_position"] = cycle_position
    if not str(diagnosis.get("direction") or "").strip():
        return _REASON_INVALID_DIRECTION, None
    patterns = diagnosis.get("detected_patterns")
    if not isinstance(patterns, list):
        return _REASON_INVALID_PATTERNS, None
    if not _valid_kline_data(record.kline_data):
        return _REASON_INVALID_KLINE, None
    return _REASON_ELIGIBLE, record


def _build_case_payload(
    record: AnalysisRecord,
    diagnosis: dict[str, Any],
    *,
    outcome: str,
    sensitive_values: Iterable[str],
) -> dict[str, Any]:
    patterns = list(
        dict.fromkeys(
            text for value in diagnosis["detected_patterns"] if (text := str(value).strip())
        )
    )
    payload: dict[str, Any] = {
        "schema": CURATED_EXPERIENCE_CASE_SCHEMA,
        "meta": {
            "symbol": record.meta.symbol,
            "timeframe": record.meta.timeframe,
            "timestamp_local_ms": record.meta.timestamp_local_ms,
        },
        "cycle_position": diagnosis["cycle_position"],
        "direction": str(diagnosis["direction"]).strip(),
        "detected_patterns": patterns,
        "outcome": outcome,
        "kline_data": record.kline_data,
        "stage1_diagnosis": diagnosis,
        "stage2_decision": record.stage2_decision,
    }
    return _sanitize(payload, sensitive_values)


def _valid_kline_data(value: object) -> bool:
    if not isinstance(value, list) or len(value) < 3:
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        try:
            prices = tuple(float(item[key]) for key in ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError):
            return False
        if not all(math.isfinite(price) for price in prices):
            return False
    return True


def _sanitize(value: dict[str, Any], sensitive_values: Iterable[str]) -> dict[str, Any]:
    secrets = tuple(dict.fromkeys(str(secret) for secret in sensitive_values if str(secret)))

    def walk(node: Any) -> Any:
        if isinstance(node, str):
            for secret in secrets:
                node = node.replace(secret, mask_secret(secret))
            return node
        if isinstance(node, dict):
            return {key: walk(item) for key, item in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(value)


def _record_digest(payload: dict[str, Any]) -> str:
    identity = {key: value for key, value in payload.items() if key != "outcome"}
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _timestamp_key(timestamp_ms: int) -> str:
    value = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).astimezone()
    return value.strftime("%Y-%m-%d_%H-%M-%S")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("existing curated experience case is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("existing curated experience case must be an object")
    return value


def _curation_result(
    target: Path,
    *,
    cycle_position: str,
    outcome: str,
    digest: str,
    imported: bool,
) -> dict[str, object]:
    return {
        "schema": EXPERIENCE_CURATION_SCHEMA,
        "imported": imported,
        "cycle_position": cycle_position,
        "outcome": outcome,
        "record_digest": digest,
        "output_file": target.name,
    }


__all__ = [
    "CURATED_EXPERIENCE_CASE_SCHEMA",
    "EXPERIENCE_CURATION_SCAN_SCHEMA",
    "EXPERIENCE_CURATION_SCHEMA",
    "curate_record",
    "scan_record_directory",
]
