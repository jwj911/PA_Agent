"""Deterministic benchmark runner with p50/p95 budget checks."""

from __future__ import annotations

import json
import math
import platform
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PERFORMANCE_REPORT_SCHEMA = "pa-agent.performance.v1"
PERFORMANCE_BENCHMARK_VERSION = "l4.synthetic.v2"
DEFAULT_MAX_REGRESSION_PCT = 10.0


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """One benchmark result and its optional budget comparison."""

    name: str
    iterations: int
    sample_repeats: int
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    budget_p95_ms: float | None
    baseline_p95_ms: float | None
    regression_pct: float | None
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe result."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Versioned report envelope for a fixed benchmark suite."""

    suite: str
    iterations: int
    warmups: int
    results: tuple[BenchmarkResult, ...]
    schema: str = PERFORMANCE_REPORT_SCHEMA
    benchmark_version: str = PERFORMANCE_BENCHMARK_VERSION
    python_version: str = sys.version.split()[0]
    platform_name: str = platform.platform()

    def __post_init__(self) -> None:
        if self.schema != PERFORMANCE_REPORT_SCHEMA:
            raise ValueError(f"unsupported performance report schema: {self.schema!r}")
        if self.iterations <= 0:
            raise ValueError("iterations must be positive")
        if self.warmups < 0:
            raise ValueError("warmups must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible report."""
        return {
            "schema": self.schema,
            "benchmark_version": self.benchmark_version,
            "suite": self.suite,
            "python_version": self.python_version,
            "platform": self.platform_name,
            "iterations": self.iterations,
            "warmups": self.warmups,
            "results": [result.to_dict() for result in self.results],
        }

    @property
    def passed(self) -> bool:
        """Whether every benchmark met its configured budget."""
        return all(result.passed for result in self.results)


def run_benchmark(
    name: str,
    operation: Callable[[], Any],
    *,
    iterations: int = 30,
    warmups: int = 5,
    sample_repeats: int = 1,
    budget_p95_ms: float | None = None,
    baseline_p95_ms: float | None = None,
    max_regression_pct: float = DEFAULT_MAX_REGRESSION_PCT,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> BenchmarkResult:
    """Measure one operation and evaluate p95/regression budgets."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    if sample_repeats <= 0:
        raise ValueError("sample_repeats must be positive")
    if budget_p95_ms is not None and budget_p95_ms < 0:
        raise ValueError("budget_p95_ms must be non-negative")
    if baseline_p95_ms is not None and baseline_p95_ms <= 0:
        raise ValueError("baseline_p95_ms must be positive")
    if max_regression_pct < 0:
        raise ValueError("max_regression_pct must be non-negative")

    for _ in range(warmups):
        for _repeat in range(sample_repeats):
            operation()

    samples: list[float] = []
    for _ in range(iterations):
        started_ns = clock_ns()
        for _repeat in range(sample_repeats):
            operation()
        elapsed_ms = (clock_ns() - started_ns) / 1_000_000.0
        samples.append(max(0.0, elapsed_ms / sample_repeats))

    p50_ms = percentile(samples, 0.50)
    p95_ms = percentile(samples, 0.95)
    regression_pct = None
    if baseline_p95_ms is not None:
        regression_pct = ((p95_ms - baseline_p95_ms) / baseline_p95_ms) * 100.0
    passed = True
    if budget_p95_ms is not None:
        passed = p95_ms <= budget_p95_ms
    if regression_pct is not None:
        passed = passed and regression_pct <= max_regression_pct
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        sample_repeats=sample_repeats,
        p50_ms=p50_ms,
        p95_ms=p95_ms,
        min_ms=min(samples),
        max_ms=max(samples),
        mean_ms=sum(samples) / len(samples),
        budget_p95_ms=budget_p95_ms,
        baseline_p95_ms=baseline_p95_ms,
        regression_pct=regression_pct,
        passed=passed,
    )


def run_suite(
    suite: str,
    operations: Mapping[str, Callable[[], Any]],
    *,
    iterations: int = 30,
    warmups: int = 5,
    sample_repeats: Mapping[str, int] | None = None,
    budgets_p95_ms: Mapping[str, float] | None = None,
    baselines_p95_ms: Mapping[str, float] | None = None,
    max_regression_pct: float = DEFAULT_MAX_REGRESSION_PCT,
) -> BenchmarkReport:
    """Run a named suite in insertion order and build a versioned report."""
    results = tuple(
        run_benchmark(
            name,
            operation,
            iterations=iterations,
            warmups=warmups,
            sample_repeats=(sample_repeats or {}).get(name, 1),
            budget_p95_ms=(budgets_p95_ms or {}).get(name),
            baseline_p95_ms=(baselines_p95_ms or {}).get(name),
            max_regression_pct=max_regression_pct,
        )
        for name, operation in operations.items()
    )
    return BenchmarkReport(
        suite=suite,
        iterations=iterations,
        warmups=warmups,
        results=results,
    )


def write_report(path: Path, report: BenchmarkReport) -> None:
    """Write a benchmark report as UTF-8 JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def percentile(values: list[float], quantile: float) -> float:
    """Return a linearly interpolated percentile for non-empty values."""
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


__all__ = [
    "DEFAULT_MAX_REGRESSION_PCT",
    "PERFORMANCE_BENCHMARK_VERSION",
    "PERFORMANCE_REPORT_SCHEMA",
    "BenchmarkReport",
    "BenchmarkResult",
    "percentile",
    "run_benchmark",
    "run_suite",
    "write_report",
]
