"""Tests for JSON Schema structural error classification."""

from __future__ import annotations

from pa_agent.ai.schema_validator import SchemaValidationResult, collect_schema_errors


def test_schema_validation_result_has_errors_reflects_error_count() -> None:
    assert not SchemaValidationResult(error_count=0).has_errors
    assert SchemaValidationResult(error_count=1).has_errors


def test_collect_schema_errors_returns_empty_result_for_valid_object() -> None:
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    result = collect_schema_errors({"name": "alpha"}, schema)

    assert result is not None
    assert result.error_count == 0
    assert not result.has_errors
    assert result.first_validator is None
    assert result.first_message == "custom validation failed"
    assert result.missing_fields == []
    assert result.invalid_fields == []
    assert result.allowed_values == {}


def test_collect_schema_errors_classifies_required_fields() -> None:
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    result = collect_schema_errors({}, schema)

    assert result is not None
    assert result.error_count == 1
    assert result.first_validator == "required"
    assert "name" in result.first_message
    assert result.missing_fields == ["name"]
    assert result.invalid_fields == []
    assert result.allowed_values == {}


def test_collect_schema_errors_classifies_enum_allowed_values() -> None:
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["ok", "fail"]}},
        "required": ["status"],
    }

    result = collect_schema_errors({"status": "unknown"}, schema)

    assert result is not None
    assert result.error_count == 1
    assert result.first_validator == "enum"
    assert result.missing_fields == []
    assert result.invalid_fields == ["status"]
    assert result.allowed_values == {"status": ["ok", "fail"]}
