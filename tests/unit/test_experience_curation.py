"""Tests for explicit record-to-experience curation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pa_agent.records.experience_curation import (
    CURATED_EXPERIENCE_CASE_SCHEMA,
    EXPERIENCE_CURATION_REVIEW_SCHEMA,
    EXPERIENCE_CURATION_SCAN_SCHEMA,
    EXPERIENCE_CURATION_SCHEMA,
    curate_record,
    curate_record_by_id,
    export_record_review_catalog,
    scan_record_directory,
)
from pa_agent.records.experience_eval_pipeline import export_annotation_template
from tools import curate_experience_record as curation_cli

_SECRET = "PRIVATE_API_KEY_VALUE"
_SYMBOL = "PRIVATE_INSTRUMENT"
_SALT = "fixed-curation-test-salt"


def _record_payload() -> dict[str, object]:
    return {
        "meta": {
            "timestamp_local_iso": "2026-07-24T08:30:00+08:00",
            "timestamp_local_ms": 1_753_314_600_000,
            "symbol": _SYMBOL,
            "timeframe": "15m",
            "bar_count": 4,
            "ai_provider": {"model": "provider-model", "api_key": "****"},
            "decision_stance": "balanced",
        },
        "kline_data": [
            {
                "seq": index,
                "open": 100.0 + index,
                "high": 101.0 + index,
                "low": 99.0 + index,
                "close": 100.5 + index,
            }
            for index in range(4)
        ],
        "htf_text": "private higher-timeframe context",
        "stage1_messages": [{"role": "user", "content": "private prompt"}],
        "stage1_response": {"content": "private provider response"},
        "stage1_diagnosis": {
            "cycle_position": "normal_channel",
            "direction": "bullish",
            "detected_patterns": ["wedge", "wedge"],
            "risk_warning": f"masked before persistence: {_SECRET}",
        },
        "stage2_messages": [{"role": "user", "content": "private stage2 prompt"}],
        "stage2_response": {"content": "private stage2 provider response"},
        "stage2_decision": {
            "decision": {
                "order_type": "不下单",
                "reasoning": f"structured decision {_SECRET}",
            }
        },
        "strategy_files_used": ["private-strategy-path"],
        "experience_loaded": [],
        "exception": None,
        "usage_total": {"total_tokens": 123},
    }


def _write_record(path: Path, payload: dict[str, object] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload or _record_payload(), ensure_ascii=False),
        encoding="utf-8",
    )


def test_scan_reports_only_shape_and_rejection_reasons(tmp_path: Path) -> None:
    records_dir = tmp_path / "records"
    _write_record(records_dir / f"completed_{_SYMBOL}.json")
    partial = _record_payload()
    partial["_partial_reason"] = "network_error"
    partial["exception"] = {"type": "TimeoutError"}
    _write_record(records_dir / f"partial_{_SYMBOL}.json", partial)
    (records_dir / f"broken_{_SYMBOL}.json").write_text("{", encoding="utf-8")

    result = scan_record_directory(records_dir)
    rendered = json.dumps(result)

    assert result == {
        "schema": EXPERIENCE_CURATION_SCAN_SCHEMA,
        "record_count": 3,
        "eligible_count": 1,
        "reason_counts": {
            "eligible": 1,
            "invalid_json": 1,
            "partial_record": 1,
        },
        "cycle_position_counts": {"normal_channel": 1},
    }
    assert _SYMBOL not in rendered
    assert _SECRET not in rendered
    assert str(records_dir) not in rendered


def test_review_catalog_is_sanitized_and_supports_record_id_import(
    tmp_path: Path,
) -> None:
    records_dir = tmp_path / "records"
    record_path = records_dir / f"completed_{_SYMBOL}.json"
    experience_dir = tmp_path / "experience"
    _write_record(record_path)
    partial = _record_payload()
    partial["_partial_reason"] = "network_error"
    _write_record(records_dir / f"partial_{_SYMBOL}.json", partial)

    catalog = export_record_review_catalog(records_dir)
    rendered = json.dumps(catalog)
    review_case = catalog["cases"][0]

    assert catalog["schema"] == EXPERIENCE_CURATION_REVIEW_SCHEMA
    assert catalog["record_count"] == 2
    assert catalog["eligible_count"] == 1
    assert catalog["reason_counts"] == {
        "eligible": 1,
        "partial_record": 1,
    }
    assert len(catalog["catalog_digest"]) == 64
    assert set(review_case) == {
        "record_id",
        "timestamp_local_ms",
        "timeframe",
        "cycle_position",
        "direction",
        "detected_pattern_count",
    }
    assert review_case["record_id"].startswith("record-")
    assert review_case["detected_pattern_count"] == 1
    for private_value in (
        _SYMBOL,
        _SECRET,
        str(records_dir),
        record_path.name,
        "100.0",
        "private prompt",
        "private provider response",
    ):
        assert private_value not in rendered

    renamed = record_path.with_name("renamed.json")
    record_path.rename(renamed)
    repeated = export_record_review_catalog(records_dir)
    assert repeated == catalog

    result = curate_record_by_id(
        records_dir,
        experience_dir,
        record_id=review_case["record_id"],
        outcome="success",
        sensitive_values=(_SECRET,),
    )
    assert result["review_record_id"] == review_case["record_id"]
    assert result["imported"] is True
    assert len(list(experience_dir.rglob("*.json"))) == 1

    with pytest.raises(ValueError, match="review record id not found"):
        curate_record_by_id(
            records_dir,
            experience_dir,
            record_id="record-not-present",
            outcome="success",
        )


def test_curate_record_is_minimal_sanitized_and_idempotent(tmp_path: Path) -> None:
    record_path = tmp_path / "records" / f"source_{_SYMBOL}.json"
    experience_dir = tmp_path / "experience"
    _write_record(record_path)

    first = curate_record(
        record_path,
        experience_dir,
        outcome="success",
        sensitive_values=(_SECRET,),
    )
    second = curate_record(
        record_path,
        experience_dir,
        outcome="success",
        sensitive_values=(_SECRET,),
    )

    assert first["schema"] == EXPERIENCE_CURATION_SCHEMA
    assert first["imported"] is True
    assert second == {**first, "imported": False}
    paths = list(experience_dir.rglob("*.json"))
    assert len(paths) == 1
    assert _SYMBOL not in paths[0].name

    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    rendered = json.dumps(payload)
    assert payload["schema"] == CURATED_EXPERIENCE_CASE_SCHEMA
    assert set(payload) == {
        "schema",
        "meta",
        "cycle_position",
        "direction",
        "detected_patterns",
        "outcome",
        "kline_data",
        "stage1_diagnosis",
        "stage2_decision",
    }
    assert payload["detected_patterns"] == ["wedge"]
    assert _SECRET not in rendered
    assert "private prompt" not in rendered
    assert "private provider response" not in rendered
    assert "total_tokens" not in rendered
    assert str(record_path) not in rendered

    template = export_annotation_template(experience_dir, salt=_SALT)
    assert len(template["cases"]) == 1
    assert _SYMBOL not in json.dumps(template)

    with pytest.raises(ValueError, match="conflicting metadata"):
        curate_record(
            record_path,
            experience_dir,
            outcome="failure",
            sensitive_values=(_SECRET,),
        )


def test_curate_record_requires_explicit_outcome_and_completed_record(
    tmp_path: Path,
) -> None:
    record_path = tmp_path / "record.json"
    _write_record(record_path)

    with pytest.raises(ValueError, match="success or failure"):
        curate_record(record_path, tmp_path / "experience", outcome="unknown")

    partial = _record_payload()
    partial["exception"] = {"type": "ProviderError"}
    _write_record(record_path, partial)
    with pytest.raises(ValueError, match="partial_record"):
        curate_record(record_path, tmp_path / "experience", outcome="failure")


def test_cli_scan_and_import_outputs_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    records_dir = tmp_path / "records"
    record_path = records_dir / f"source_{_SYMBOL}.json"
    experience_dir = tmp_path / "experience"
    review_path = tmp_path / "artifacts" / "review.json"
    _write_record(record_path)
    monkeypatch.setattr(
        curation_cli,
        "load_settings",
        lambda: SimpleNamespace(provider=SimpleNamespace(api_key=_SECRET)),
    )

    assert (
        curation_cli.main(
            [
                "scan",
                "--records-dir",
                str(records_dir),
            ]
        )
        == 0
    )
    assert (
        curation_cli.main(
            [
                "export-review",
                "--records-dir",
                str(records_dir),
                "--output",
                str(review_path),
            ]
        )
        == 0
    )
    catalog = json.loads(review_path.read_text(encoding="utf-8"))
    record_id = catalog["cases"][0]["record_id"]
    assert (
        curation_cli.main(
            [
                "import-record",
                "--record-id",
                record_id,
                "--records-dir",
                str(records_dir),
                "--experience-dir",
                str(experience_dir),
                "--outcome",
                "success",
            ]
        )
        == 0
    )
    assert (
        curation_cli.main(
            [
                "import-record",
                "--record",
                str(record_path),
                "--experience-dir",
                str(experience_dir),
                "--outcome",
                "success",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert EXPERIENCE_CURATION_SCAN_SCHEMA in output
    assert EXPERIENCE_CURATION_REVIEW_SCHEMA in output
    assert EXPERIENCE_CURATION_SCHEMA in output
    assert _SYMBOL not in output
    assert _SECRET not in output
    assert str(record_path) not in output
    assert _SYMBOL not in review_path.read_text(encoding="utf-8")
    assert len(list(experience_dir.rglob("*.json"))) == 1
