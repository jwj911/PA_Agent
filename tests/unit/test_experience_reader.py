"""Tests for experience-library selection."""

from __future__ import annotations

import json
from pathlib import Path

from pa_agent.data.base import KlineBar
from pa_agent.records.experience_reader import ExperienceReader
from pa_agent.records.experience_similarity import score_kline_similarity


def _write_case(
    root: Path,
    *,
    filename: str,
    direction: str,
    patterns: list[str],
    kline_data: list[dict] | None = None,
) -> None:
    path = root / "micro_channel" / "success_cases" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {"direction": direction, "detected_patterns": patterns}
    if kline_data is not None:
        content["kline_data"] = kline_data
    path.write_text(
        json.dumps(content),
        encoding="utf-8",
    )


def _bars() -> tuple[KlineBar, ...]:
    return (
        KlineBar(seq=1, ts_open=4, open=100, high=103, low=99, close=102, volume=1),
        KlineBar(seq=2, ts_open=3, open=102, high=104, low=100, close=101, volume=1),
        KlineBar(seq=3, ts_open=2, open=101, high=103, low=98, close=99, volume=1),
        KlineBar(seq=4, ts_open=1, open=99, high=101, low=97, close=100, volume=1),
    )


def _scaled_kline_data(bars: tuple[KlineBar, ...], scale: float = 1.0) -> list[dict]:
    return [
        {
            "open": bar.open * scale,
            "high": bar.high * scale,
            "low": bar.low * scale,
            "close": bar.close * scale,
        }
        for bar in bars
    ]


def test_kline_similarity_ignores_absolute_price_scale() -> None:
    bars = _bars()

    score = score_kline_similarity(
        bars,
        {"kline_data": _scaled_kline_data(bars, scale=10.0)},
    )

    assert score == 1.0


def test_kline_similarity_returns_none_for_legacy_or_malformed_entries() -> None:
    bars = _bars()

    assert score_kline_similarity(bars, {}) is None
    assert score_kline_similarity(bars, {"kline_data": [{"open": 1}] * 4}) is None
    assert score_kline_similarity(bars[:2], {"kline_data": _scaled_kline_data(bars)}) is None


def test_read_for_stage2_ranks_all_cases_before_truncating(tmp_path: Path) -> None:
    reader = ExperienceReader(experience_dir=tmp_path)

    for day in range(2, 7):
        _write_case(
            tmp_path,
            filename=f"2026-06-0{day}_09-00-00_newer_{day}.json",
            direction="bear",
            patterns=["broad_channel"],
        )
    _write_case(
        tmp_path,
        filename="2026-06-01_09-00-00_matching.json",
        direction="bull",
        patterns=["wedge"],
    )

    entries = reader.read_for_stage2(
        "micro_channel",
        direction="bull",
        patterns=["wedge"],
        max_entries=1,
    )

    assert [entry.filename for entry in entries] == ["2026-06-01_09-00-00_matching.json"]


def test_read_for_stage2_uses_kline_similarity_after_context_score(tmp_path: Path) -> None:
    reader = ExperienceReader(experience_dir=tmp_path)
    bars = _bars()

    _write_case(
        tmp_path,
        filename="2026-06-02_09-00-00_newer_dissimilar.json",
        direction="bull",
        patterns=["wedge"],
        kline_data=[
            {"open": 100, "high": 101, "low": 99, "close": 99},
            {"open": 99, "high": 100, "low": 98, "close": 98},
            {"open": 98, "high": 99, "low": 97, "close": 97},
            {"open": 97, "high": 98, "low": 96, "close": 96},
        ],
    )
    _write_case(
        tmp_path,
        filename="2026-06-01_09-00-00_older_similar.json",
        direction="bull",
        patterns=["wedge"],
        kline_data=_scaled_kline_data(bars, scale=10.0),
    )

    entries = reader.read_for_stage2(
        "micro_channel",
        direction="bull",
        patterns=["wedge"],
        max_entries=1,
        current_bars=bars,
    )

    assert [entry.filename for entry in entries] == ["2026-06-01_09-00-00_older_similar.json"]


def test_read_top5_keeps_newest_first_compatibility(tmp_path: Path) -> None:
    reader = ExperienceReader(experience_dir=tmp_path)

    for day in range(1, 7):
        _write_case(
            tmp_path,
            filename=f"2026-06-0{day}_09-00-00_case_{day}.json",
            direction="bull",
            patterns=[],
        )

    entries = reader.read_top5("micro_channel")

    assert [entry.filename for entry in entries] == [
        "2026-06-06_09-00-00_case_6.json",
        "2026-06-05_09-00-00_case_5.json",
        "2026-06-04_09-00-00_case_4.json",
        "2026-06-03_09-00-00_case_3.json",
        "2026-06-02_09-00-00_case_2.json",
    ]
