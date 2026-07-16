"""Tests for the records package exports."""
from __future__ import annotations

from pa_agent import records
from pa_agent.records.experience_reader import ExperienceReader
from pa_agent.records.schema import (
    AlarmPayload,
    AnalysisRecord,
    ExperienceEntry,
    FollowupTurn,
    RecordMeta,
    ValidationError,
)


def test_records_package_exports_expected_public_names() -> None:
    assert records.__all__ == [
        "AlarmPayload",
        "AnalysisRecord",
        "ExperienceEntry",
        "ExperienceReader",
        "FollowupTurn",
        "RecordMeta",
        "ValidationError",
    ]


def test_records_public_names_are_bound_to_records_classes() -> None:
    assert records.AlarmPayload is AlarmPayload
    assert records.AnalysisRecord is AnalysisRecord
    assert records.ExperienceEntry is ExperienceEntry
    assert records.ExperienceReader is ExperienceReader
    assert records.FollowupTurn is FollowupTurn
    assert records.RecordMeta is RecordMeta
    assert records.ValidationError is ValidationError
