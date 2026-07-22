"""Run one explicit, sanitized live headless observation.

The command never reads ``config/settings.json`` and never runs unless
``--confirm-live`` and ``PA_AGENT_LIVE_API_KEY`` are both present.

Example:
    py -3.12 tools/run_live_headless_observation.py ^
      --confirm-live --output-dir artifacts/live-observation
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.config.settings import AIProviderSettings, GeneralSettings, Settings  # noqa: E402
from pa_agent.util.event_replay import replay_jsonl  # noqa: E402
from pa_agent.util.event_sink import CollectingEventSink, JsonlEventSink  # noqa: E402
from pa_agent.util.safe_filename import sanitize_filename_component  # noqa: E402

LIVE_OBSERVATION_SCHEMA = "pa-agent.live-observation.v1"
_DEFAULT_MODEL = "deepseek-v4-flash"
_DEFAULT_BASE_URL = "https://api.deepseek.com"
_BAR_COUNT = 30


def _make_frame() -> object:
    """Build a synthetic, opaque frame without reading a live data source."""
    from pa_agent.data.base import KlineBar, KlineFrame
    from pa_agent.data.snapshot import compute_indicators

    base_ts = 1_700_000_000_000
    bars = [
        KlineBar(
            seq=1,
            ts_open=base_ts,
            open=2010.0,
            high=2017.0,
            low=2008.0,
            close=2015.0,
            volume=120.0,
            closed=False,
        )
    ]
    for index in range(2, _BAR_COUNT + 2):
        opened = 1990.0 + index * 0.8
        closed = opened + 1.2
        bars.append(
            KlineBar(
                seq=index,
                ts_open=base_ts - (index - 1) * 900_000,
                open=opened,
                high=closed + 0.8,
                low=opened - 0.5,
                close=closed,
                volume=100.0 + index,
                closed=True,
            )
        )
    return KlineFrame(
        symbol="live-observation",
        timeframe="5m",
        bars=tuple(bars),
        indicators=compute_indicators(bars),
        snapshot_ts_local_ms=base_ts,
    )


def run_live_observation(
    *,
    output_dir: Path,
    api_key: str,
    base_url: str = _DEFAULT_BASE_URL,
    model: str = _DEFAULT_MODEL,
    correlation_id: str | None = None,
    pipeline_builder_enabled: bool = False,
    client: object | None = None,
) -> dict[str, object]:
    """Run one live headless request and write only sanitized evidence."""
    from pa_agent.ai.deepseek_client import DeepSeekClient
    from pa_agent.app_context import AppContext
    from pa_agent.headless import HeadlessAnalysisAdapter

    if not api_key.strip():
        raise ValueError("api key must be provided through PA_AGENT_LIVE_API_KEY")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records_dir = output_dir / "records"
    run_id = str(correlation_id or uuid.uuid4().hex).strip()
    if not run_id:
        raise ValueError("correlation_id must not be empty")

    events_path = output_dir / (
        f"{sanitize_filename_component(run_id, fallback='run')}.events.jsonl"
    )
    settings = Settings(
        provider=AIProviderSettings(
            api_key=api_key,
            base_url=base_url,
            model=model,
        ),
        general=GeneralSettings(
            last_symbol="live-observation",
            last_timeframe="5m",
        ),
        orchestrator={"pipeline_builder_enabled": pipeline_builder_enabled},
    )
    resolved_client = client or DeepSeekClient(
        settings=settings.provider,
        logger_=logging.getLogger("pa_agent.live_observation"),
    )

    with JsonlEventSink(events_path, require_correlation_id=True) as event_sink:
        context = AppContext.bootstrap_headless(
            settings=settings,
            client=resolved_client,
            event_sink=event_sink,
            records_pending_dir=records_dir,
            sync_providers=False,
            configure_logs=False,
        )
        result = HeadlessAnalysisAdapter(
            context,
            event_sink=event_sink,
            correlation_id=run_id,
        ).run(_make_frame())

    replay_sink = CollectingEventSink()
    replayed_count = replay_jsonl(
        events_path,
        replay_sink,
        expected_correlation_id=run_id,
    )
    record_paths = sorted(records_dir.glob("*.json"))
    record = result.record
    exception = getattr(record, "exception", None)
    exception_type = exception.get("type") if isinstance(exception, dict) else None
    status = "completed" if exception is None else "partial"
    summary = {
        "schema": LIVE_OBSERVATION_SCHEMA,
        "correlation_id": run_id,
        "pipeline_builder_enabled": pipeline_builder_enabled,
        "status": status,
        "provider_called": any(
            name in result.event_names for name in ("Stage1Started", "Stage2Started")
        ),
        "event_schema": "pa-agent.event.v1",
        "event_count": len(result.event_names),
        "replayed_event_count": replayed_count,
        "events": list(result.event_names),
        "record_written": bool(record_paths),
        "record_file": record_paths[0].name if record_paths else None,
        "exception_type": exception_type,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--base-url", default=os.environ.get("PA_AGENT_LIVE_BASE_URL", _DEFAULT_BASE_URL)
    )
    parser.add_argument("--model", default=os.environ.get("PA_AGENT_LIVE_MODEL", _DEFAULT_MODEL))
    parser.add_argument("--correlation-id")
    parser.add_argument(
        "--pipeline-builder-enabled",
        action="store_true",
        help="Opt into the Pipeline path for this explicit live observation",
    )
    args = parser.parse_args(argv)

    if not args.confirm_live:
        print("Live observation requires --confirm-live.", file=sys.stderr)
        return 2
    api_key = os.environ.get("PA_AGENT_LIVE_API_KEY", "").strip()
    if not api_key:
        print("Set PA_AGENT_LIVE_API_KEY before running live observation.", file=sys.stderr)
        return 2

    try:
        summary = run_live_observation(
            output_dir=args.output_dir,
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            correlation_id=args.correlation_id,
            pipeline_builder_enabled=args.pipeline_builder_enabled,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": LIVE_OBSERVATION_SCHEMA,
                    "status": "harness_error",
                    "error_type": type(exc).__name__,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
