"""JSON Schema validation helpers for :mod:`pa_agent.ai.json_validator`.

This module owns only the structural jsonschema pass: run Draft 7 validation
and classify schema errors into missing fields, invalid fields, allowed enum
values, and first-error metadata. Semantic / business-rule checks remain in
``JsonValidator`` and ``business_rules``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SchemaValidationResult:
    """Classified output from the jsonschema validation pass."""

    error_count: int
    first_validator: str | None = None
    first_message: str = "custom validation failed"
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    allowed_values: dict[str, list] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0


def collect_schema_errors(
    obj: dict[str, Any], schema: dict[str, Any]
) -> SchemaValidationResult | None:
    """Return classified Draft 7 schema errors, or ``None`` if jsonschema is absent."""

    try:
        import jsonschema  # type: ignore[import]
    except ImportError:
        logger.warning("jsonschema not installed; skipping schema validation")
        return None

    errors = list(jsonschema.Draft7Validator(schema).iter_errors(obj))
    result = SchemaValidationResult(error_count=len(errors))

    if errors:
        result.first_validator = str(errors[0].validator)
        result.first_message = errors[0].message[:120]

    for err in errors:
        path = ".".join(str(p) for p in err.absolute_path) or err.schema_path[-1]
        if err.validator == "required":
            # Extract the missing property name from the message
            result.missing_fields.append(
                err.message.split("'")[1] if "'" in err.message else str(path)
            )
        else:
            result.invalid_fields.append(str(path) or err.message[:80])
            if "enum" in err.schema:
                result.allowed_values[str(path)] = err.schema["enum"]

    return result
