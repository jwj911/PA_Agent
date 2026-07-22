"""Validate sanitized live observation summary, event stream, and record output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.util.event_replay import replay_jsonl  # noqa: E402
from pa_agent.util.event_sink import CollectingEventSink  # noqa: E402
from tools.run_live_headless_observation import LIVE_OBSERVATION_SCHEMA  # noqa: E402

VALIDATION_SCHEMA = "pa-agent.live-observation-validation.v1"
EVENT_SCHEMA = "pa-agent.event.v1"


def validate_live_observation(
    *,
    summary_path: Path,
    events_path: Path,
    records_dir: Path,
) -> dict[str, object]:
    """Validate one live observation without contacting a Provider."""
    summary = _load_json_object(summary_path, "summary")
    if summary.get("schema") != LIVE_OBSERVATION_SCHEMA:
        raise ValueError("unsupported live observation summary schema")
    correlation_id = summary.get("correlation_id")
    if not isinstance(correlation_id, str) or not correlation_id:
        raise ValueError("summary correlation_id must be a non-empty string")
    event_file = summary.get("event_file")
    if not isinstance(event_file, str) or event_file != Path(events_path).name:
        raise ValueError("summary event_file does not match events path")
    if summary.get("event_schema") != EVENT_SCHEMA:
        raise ValueError("summary event schema mismatch")

    event_names = summary.get("events")
    if not isinstance(event_names, list) or not all(isinstance(item, str) for item in event_names):
        raise ValueError("summary events must be an array of strings")
    event_count = summary.get("event_count")
    replayed_event_count = summary.get("replayed_event_count")
    if not isinstance(event_count, int) or not isinstance(replayed_event_count, int):
        raise ValueError("summary event counts must be integers")

    sink = CollectingEventSink()
    replay_count = replay_jsonl(
        events_path,
        sink,
        expected_correlation_id=correlation_id,
    )
    replayed_names = [
        str(event.payload.get("event"))
        for event in sink.events
        if isinstance(event.payload, dict) and "event" in event.payload
    ]
    if replay_count != event_count or replay_count != replayed_event_count:
        raise ValueError("summary event counts do not match replayed events")
    if replayed_names != event_names:
        raise ValueError("summary event sequence does not match replayed events")

    record_written = summary.get("record_written")
    record_file = summary.get("record_file")
    if not isinstance(record_written, bool):
        raise ValueError("summary record_written must be boolean")
    if record_written:
        if not isinstance(record_file, str) or not record_file:
            raise ValueError("summary record_file is required when record_written is true")
        candidate = (Path(records_dir) / record_file).resolve()
        if candidate.parent != Path(records_dir).resolve() or not candidate.is_file():
            raise ValueError("summary record_file is missing or outside records_dir")
    elif record_file is not None:
        raise ValueError("summary record_file must be null when record_written is false")

    return {
        "schema": VALIDATION_SCHEMA,
        "valid": True,
        "correlation_id": correlation_id,
        "pipeline_builder_enabled": bool(summary.get("pipeline_builder_enabled", False)),
        "event_count": replay_count,
        "event_file": event_file,
        "record_written": record_written,
        "record_file": record_file,
    }


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} JSON must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--records-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate_live_observation(
            summary_path=args.summary,
            events_path=args.events,
            records_dir=args.records_dir,
        )
    except ValueError as exc:
        print(json.dumps({"schema": VALIDATION_SCHEMA, "valid": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
