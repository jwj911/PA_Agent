"""Tests for deterministic L4 benchmark contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pa_agent.perf.benchmark import (
    PERFORMANCE_REPORT_SCHEMA,
    run_benchmark,
    run_suite,
    write_report,
)


def test_run_benchmark_reports_percentiles_and_regression() -> None:
    clock_values = iter(
        (
            0,
            1_000_000,
            1_000_000,
            3_000_000,
            3_000_000,
            6_000_000,
        )
    )
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1

    result = run_benchmark(
        "fixture",
        operation,
        iterations=3,
        warmups=1,
        budget_p95_ms=3.0,
        baseline_p95_ms=2.5,
        clock_ns=lambda: next(clock_values),
    )

    assert calls == 4
    assert result.p50_ms == pytest.approx(2.0)
    assert result.p95_ms == pytest.approx(2.9)
    assert result.regression_pct == pytest.approx(16.0)
    assert result.passed is False


def test_suite_report_is_versioned_and_writable(tmp_path: Path) -> None:
    report = run_suite(
        "test-suite",
        {"one": lambda: None, "two": lambda: None},
        iterations=1,
        warmups=0,
    )
    path = tmp_path / "nested" / "report.json"

    write_report(path, report)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert report.passed is True
    assert payload["schema"] == PERFORMANCE_REPORT_SCHEMA
    assert [item["name"] for item in payload["results"]] == ["one", "two"]


def test_benchmark_rejects_invalid_iteration_and_percentile_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        run_benchmark("bad", lambda: None, iterations=0)

    with pytest.raises(ValueError, match="percentile"):
        from pa_agent.perf.benchmark import percentile

        percentile([], 0.5)
