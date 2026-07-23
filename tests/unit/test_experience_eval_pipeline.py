"""Tests for sanitized experience export and offline report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pa_agent.records.experience_eval_pipeline import (
    EXPERIENCE_ANNOTATION_SCHEMA,
    EXPERIENCE_REPORT_SCHEMA,
    evaluate_annotated_experience,
    export_annotation_template,
)
from tools.run_experience_evaluation import SALT_ENV, main

_SALT = "fixed-test-salt-value"


def _write_case(
    root: Path,
    *,
    cycle: str,
    outcome: str,
    filename: str,
    symbol: str,
    timeframe: str,
    direction: str,
    patterns: list[str],
    closes: list[float],
) -> None:
    path = root / cycle / f"{outcome}_cases" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "meta": {"symbol": symbol, "timeframe": timeframe},
                "direction": direction,
                "detected_patterns": patterns,
                "kline_data": [
                    {
                        "open": close - 0.4,
                        "high": close + 0.5,
                        "low": close - 0.7,
                        "close": close,
                    }
                    for close in closes
                ],
                "private_path": f"C:/private/{symbol}",
                "api_key": "PRIVATE_KEY",
            }
        ),
        encoding="utf-8",
    )


def _experience_library(tmp_path: Path) -> Path:
    root = tmp_path / "experience"
    _write_case(
        root,
        cycle="micro_channel",
        outcome="success",
        filename="2026-01-01_09-00-00_a.json",
        symbol="PRIVATE_SYMBOL_A",
        timeframe="5m",
        direction="bullish",
        patterns=["wedge"],
        closes=[10, 11, 12, 13],
    )
    _write_case(
        root,
        cycle="micro_channel",
        outcome="failure",
        filename="2026-01-02_09-00-00_b.json",
        symbol="PRIVATE_SYMBOL_A",
        timeframe="5m",
        direction="bullish",
        patterns=["wedge"],
        closes=[20, 21, 22, 23],
    )
    _write_case(
        root,
        cycle="micro_channel",
        outcome="success",
        filename="2026-01-03_09-00-00_c.json",
        symbol="PRIVATE_SYMBOL_B",
        timeframe="15m",
        direction="bearish",
        patterns=["breakout_failure"],
        closes=[30, 29, 28, 27],
    )
    _write_case(
        root,
        cycle="micro_channel",
        outcome="failure",
        filename="2026-01-04_09-00-00_d.json",
        symbol="PRIVATE_SYMBOL_B",
        timeframe="15m",
        direction="bearish",
        patterns=["breakout_failure"],
        closes=[40, 39, 38, 37],
    )
    return root


def _review_all(template: dict[str, object]) -> dict[str, object]:
    reviewed = json.loads(json.dumps(template))
    for case in reviewed["cases"]:
        case["reviewed"] = True
        case["relevant_ids"] = case["candidate_ids"][:1]
    return reviewed


def test_export_template_is_opaque_and_contains_no_raw_market_payload(
    tmp_path: Path,
) -> None:
    experience_dir = _experience_library(tmp_path)

    template = export_annotation_template(experience_dir, salt=_SALT)
    rendered = json.dumps(template)

    assert template["schema"] == EXPERIENCE_ANNOTATION_SCHEMA
    assert len(template["cases"]) == 4
    assert len({case["instrument_id"] for case in template["cases"]}) == 2
    for private_value in (
        "PRIVATE_SYMBOL_A",
        "PRIVATE_SYMBOL_B",
        "PRIVATE_KEY",
        "private_path",
        "kline_data",
        "open",
        "close",
        str(experience_dir),
        _SALT,
    ):
        assert private_value not in rendered


def test_evaluation_generates_fixed_split_and_metrics_without_changing_online_sort(
    tmp_path: Path,
) -> None:
    experience_dir = _experience_library(tmp_path)
    annotations = _review_all(export_annotation_template(experience_dir, salt=_SALT))

    dataset, split, report = evaluate_annotated_experience(
        experience_dir,
        annotations,
        salt=_SALT,
        evaluation_fraction=0.5,
        k=2,
    )
    repeated_dataset, repeated_split, repeated_report = evaluate_annotated_experience(
        experience_dir,
        annotations,
        salt=_SALT,
        evaluation_fraction=0.5,
        k=2,
    )

    assert len(dataset.cases) == 4
    assert repeated_dataset == dataset
    assert repeated_split == split
    assert repeated_report == report
    assert len(split.train_group_ids) == 1
    assert len(split.evaluation_group_ids) == 1
    assert set(split.train_group_ids).isdisjoint(split.evaluation_group_ids)
    assert report["schema"] == EXPERIENCE_REPORT_SCHEMA
    assert report["case_count"] == 4
    assert report["evaluation_case_count"] == 2
    assert report["online_sorting_changed"] is False
    assert report["legacy_metrics"]["query_count"] == 2
    assert report["similarity_metrics"]["query_count"] == 2
    rendered = json.dumps(report)
    assert "PRIVATE_SYMBOL" not in rendered
    assert "kline_data" not in rendered


def test_annotations_require_review_and_catalog_candidates(tmp_path: Path) -> None:
    experience_dir = _experience_library(tmp_path)
    template = export_annotation_template(experience_dir, salt=_SALT)

    with pytest.raises(ValueError, match="reviewed"):
        evaluate_annotated_experience(experience_dir, template, salt=_SALT)

    reviewed = _review_all(template)
    reviewed["cases"][0]["relevant_ids"] = ["case-not-in-catalog"]
    with pytest.raises(ValueError, match="candidate_ids"):
        evaluate_annotated_experience(experience_dir, reviewed, salt=_SALT)


def test_export_rejects_missing_symbol_and_short_salt(tmp_path: Path) -> None:
    experience_dir = tmp_path / "experience"
    case_path = (
        experience_dir / "micro_channel" / "success_cases" / "2026-01-01_09-00-00_missing.json"
    )
    case_path.parent.mkdir(parents=True)
    case_path.write_text(
        json.dumps(
            {
                "timeframe": "5m",
                "direction": "bullish",
                "detected_patterns": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="salt"):
        export_annotation_template(experience_dir, salt="short")
    with pytest.raises(ValueError, match="symbol"):
        export_annotation_template(experience_dir, salt=_SALT)

    case_path.write_text(
        json.dumps(
            {
                "symbol": "PRIVATE_SYMBOL",
                "timeframe": "5m",
                "direction": "bullish",
                "detected_patterns": [],
            }
        ),
        encoding="utf-8",
    )
    renamed = case_path.with_name("missing-timestamp.json")
    case_path.rename(renamed)
    with pytest.raises(ValueError, match="filename"):
        export_annotation_template(experience_dir, salt=_SALT)


def test_cli_uses_environment_salt_and_writes_sanitized_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    experience_dir = _experience_library(tmp_path)
    labels_path = tmp_path / "artifacts" / "labels.json"
    output_dir = tmp_path / "artifacts" / "report"
    monkeypatch.setenv(SALT_ENV, _SALT)

    assert (
        main(
            [
                "export-labels",
                "--experience-dir",
                str(experience_dir),
                "--output",
                str(labels_path),
            ]
        )
        == 0
    )
    labels = _review_all(json.loads(labels_path.read_text(encoding="utf-8")))
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    assert (
        main(
            [
                "evaluate",
                "--experience-dir",
                str(experience_dir),
                "--annotations",
                str(labels_path),
                "--output-dir",
                str(output_dir),
                "--evaluation-fraction",
                "0.5",
                "--k",
                "2",
            ]
        )
        == 0
    )

    assert {path.name for path in output_dir.iterdir()} == {
        "dataset.json",
        "split.json",
        "report.json",
    }
    stdout = capsys.readouterr().out
    assert "PRIVATE_SYMBOL" not in stdout
    assert _SALT not in stdout
