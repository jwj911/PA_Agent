"""Run the deterministic L4 synthetic performance benchmark suite."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.ai.kline_features import compute_kline_geometry_features  # noqa: E402
from pa_agent.data.base import KlineBar, KlineFrame  # noqa: E402
from pa_agent.data.snapshot import build_analysis_frame, compute_indicators  # noqa: E402
from pa_agent.perf.benchmark import (  # noqa: E402
    PERFORMANCE_BENCHMARK_VERSION,
    PERFORMANCE_REPORT_SCHEMA,
    run_suite,
    write_report,
)

_SIZES = (100, 500, 5000)
_P95_BUDGETS_MS = {
    "snapshot_build_100": 20.0,
    "snapshot_build_500": 100.0,
    "snapshot_build_5000": 1500.0,
    "indicators_100": 10.0,
    "indicators_500": 50.0,
    "indicators_5000": 500.0,
    "geometry_100": 20.0,
    "geometry_500": 100.0,
    "geometry_5000": 1000.0,
}
_SAMPLE_REPEATS = {
    "snapshot_build_100": 20,
    "indicators_100": 100,
    "geometry_100": 10,
    "snapshot_build_500": 5,
    "indicators_500": 25,
    "geometry_500": 2,
    "snapshot_build_5000": 1,
    "indicators_5000": 3,
    "geometry_5000": 1,
}


def _bars(count: int) -> list[KlineBar]:
    """Build newest-first OHLC bars without network or filesystem inputs."""
    return [
        KlineBar(
            seq=index + 1,
            ts_open=1_700_000_000_000 - index * 60_000,
            open=1000.0 + (count - index) * 0.2,
            high=1002.0 + (count - index) * 0.2,
            low=998.0 + (count - index) * 0.2,
            close=1001.0 + (count - index) * 0.2,
            volume=100.0,
            closed=True,
        )
        for index in range(count)
    ]


def _frame(count: int) -> KlineFrame:
    bars = _bars(count)
    return KlineFrame(
        symbol="benchmark",
        timeframe="5m",
        bars=tuple(bars),
        indicators=compute_indicators(bars),
        snapshot_ts_local_ms=1_700_000_000_000,
    )


def _operations() -> dict[str, Callable[[], object]]:
    operations: dict[str, Callable[[], object]] = {}
    for size in _SIZES:
        raw_bars = _bars(size + 50)
        frame = _frame(size)
        operations[f"snapshot_build_{size}"] = lambda raw_bars=raw_bars, size=size: (
            build_analysis_frame(
                raw_bars,
                size,
                "benchmark",
                "5m",
                now_ms=1_700_000_000_000,
            )
        )
        operations[f"indicators_{size}"] = lambda raw_bars=raw_bars: compute_indicators(raw_bars)
        operations[f"geometry_{size}"] = lambda frame=frame: compute_kline_geometry_features(frame)
    return operations


def _load_baselines(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != PERFORMANCE_REPORT_SCHEMA:
        raise ValueError("unsupported benchmark baseline schema")
    if payload.get("benchmark_version") != PERFORMANCE_BENCHMARK_VERSION:
        raise ValueError("benchmark baseline version does not match current suite")
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("benchmark baseline results must be an array")
    return {
        str(item["name"]): float(item["p95_ms"])
        for item in results
        if isinstance(item, dict) and "name" in item and "p95_ms" in item
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args(argv)

    report = run_suite(
        "l4-synthetic",
        _operations(),
        iterations=args.iterations,
        warmups=args.warmups,
        sample_repeats=_SAMPLE_REPEATS,
        budgets_p95_ms=_P95_BUDGETS_MS,
        baselines_p95_ms=_load_baselines(args.baseline),
    )
    if args.output is not None:
        write_report(args.output, report)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
