"""Tests for experience-library selection."""

from __future__ import annotations

import json
from pathlib import Path

from pa_agent.records.experience_reader import ExperienceReader


def _write_case(
    root: Path,
    *,
    filename: str,
    direction: str,
    patterns: list[str],
) -> None:
    path = root / "micro_channel" / "success_cases" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"direction": direction, "detected_patterns": patterns}),
        encoding="utf-8",
    )


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
