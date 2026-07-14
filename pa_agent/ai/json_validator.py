"""JSON validator for Stage 1 and Stage 2 AI outputs.

Categories:
  a — syntax error (invalid JSON)
  b — missing required field
  c — illegal value (enum violation, type mismatch, 不下单 price non-null, etc.)
  d — plain text (no JSON structure at all)
  e — provider error (quota/billing; non-retryable)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class Ok:
    """Successful validation result."""
    obj: dict[str, Any]


@dataclass
class ValidationError:
    """Failed validation result."""
    category: Literal["a", "b", "c", "d", "e"]
    stage: str                          # "stage1" or "stage2"
    raw_text: str
    parse_position: str | None = None   # "line:col" if available
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    allowed_values: dict[str, list] = field(default_factory=dict)
    message: str = ""


Result = Ok | ValidationError

# ── Business-rule validators ──────────────────────────────────────────────────
# Extracted to pa_agent.ai.business_rules (report §5.2 M2). The module-level
# helpers + token tuple are re-exported here so existing
# ``from pa_agent.ai.json_validator import ...`` sites keep working byte-for-byte;
# the ``check_x`` functions are re-bound as ``JsonValidator._check_x``
# staticmethods below so ``JsonValidator._check_x(...)`` call sites still work.
from pa_agent.ai import business_rules  # noqa: E402
from pa_agent.ai.business_rules import (  # noqa: E402, F401
    _EXPLICIT_S9_TRADABLE_TOKENS,
    _all_stage2_reasons,
    _bar_by_seq,
    _parse_k_seq,
)

# ── JSON extraction / repair helpers ──────────────────────────────────────────
# Extracted to pa_agent.ai.json_repair (report §5.2 M2). Re-exported here so
# existing ``from pa_agent.ai.json_validator import ...`` sites keep working
# byte-for-byte (F401: these are intentional re-exports, used by other modules).
from pa_agent.ai.json_repair import (  # noqa: E402, F401
    _FENCE_RE,
    _LEADING_FENCE_RE,
    _STRING_END_CHARS,
    _TRAILING_FENCE_RE,
    _balance_json_brackets,
    _escape_control_chars_in_json_strings,
    _extract_outer_json_object,
    _inject_stage1_missing_tail,
    _repair_semicolon_separator,
    _repair_unclosed_string_before_brace,
    _repair_unescaped_quotes,
    _strip_fences,
    _try_repair_json_syntax,
    coalesce_model_json_text,
    format_model_json_for_context,
)

# ── JsonValidator ─────────────────────────────────────────────────────────────

class JsonValidator:
    """Validates raw AI text against Stage 1 or Stage 2 JSON schemas."""

    def __init__(self, validation: Any = None) -> None:
        from pa_agent.ai.prompts.schemas import STAGE1_SCHEMA, STAGE2_SCHEMA
        from pa_agent.config.settings import ValidationSettings

        if validation is None:
            self._validation = ValidationSettings()
        elif hasattr(validation, "validation"):
            self._validation = validation.validation
        else:
            self._validation = validation

        self._schemas = {
            "stage1": STAGE1_SCHEMA,
            "stage2": STAGE2_SCHEMA,
        }

    def normalize_parsed(
        self,
        stage: Literal["stage1", "stage2"],
        obj: dict[str, Any],
        *,
        decision_stance: str | None = None,
        kline_frame: Any = None,
        stage1_json: dict[str, Any] | None = None,
        incremental_new_bar_count: int = 0,
        incremental_previous_stage1: dict[str, Any] | None = None,
        skip_next_bar: bool = False,
        previous_record: Any | None = None,
        structure_flip_cooldown_bars: int = 3,
    ) -> dict[str, Any]:
        """Apply the same post-parse normalization as :meth:`validate`."""
        norm_mode = getattr(self._validation, "normalization_mode", "strict")
        if stage == "stage1":
            from pa_agent.ai.stage1_normalizer import normalize_stage1

            return normalize_stage1(
                obj,
                normalization_mode=norm_mode,
                kline_frame=kline_frame,
                incremental_new_bar_count=int(incremental_new_bar_count or 0),
                incremental_previous_stage1=incremental_previous_stage1
                if incremental_new_bar_count > 0
                else None,
            )
        from pa_agent.ai.stage2_normalizer import normalize_stage2

        # Always satisfy STAGE2_SCHEMA.required during validation; orchestrator
        # strips next_bar_prediction before save when the feature is disabled.
        return normalize_stage2(
            obj,
            normalization_mode=norm_mode,
            kline_frame=kline_frame,
            decision_stance=decision_stance,
            stage1_json=stage1_json,
            skip_next_bar=False,
            previous_record=previous_record,
            structure_flip_cooldown_bars=structure_flip_cooldown_bars,
        )

    def validate(
        self,
        stage: Literal["stage1", "stage2"],
        raw_text: str,
        *,
        decision_stance: str | None = None,
        kline_frame: Any = None,
        stage1_json: dict[str, Any] | None = None,
        incremental_new_bar_count: int = 0,
        incremental_previous_stage1: dict[str, Any] | None = None,
        skip_next_bar: bool = False,
        previous_record: Any | None = None,
        structure_flip_cooldown_bars: int = 3,
    ) -> Result:
        """Validate *raw_text* against the schema for *stage*.

        Returns Ok(obj) on success, ValidationError on any failure.
        """
        schema = self._schemas[stage]

        # ── Category d / e: plain text (no JSON at all) ───────────────────────
        stripped = _strip_fences(raw_text)
        if not stripped.startswith("{") and not stripped.startswith("["):
            from pa_agent.ai.provider_errors import (
                PROVIDER_QUOTA_USER_MESSAGE,
                is_provider_quota_exhausted,
            )

            if is_provider_quota_exhausted(stripped):
                return ValidationError(
                    category="e",
                    stage=stage,
                    raw_text=raw_text,
                    message=PROVIDER_QUOTA_USER_MESSAGE,
                    invalid_fields=["provider:quota_exhausted"],
                )
            return ValidationError(
                category="d",
                stage=stage,
                raw_text=raw_text,
                message="Response is plain text, not JSON",
            )

        # ── Category a: syntax error ──────────────────────────────────────────
        obj: dict | list | None = None
        parse_exc: json.JSONDecodeError | None = None
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            parse_exc = exc
            escaped = _escape_control_chars_in_json_strings(stripped)
            if escaped != stripped:
                try:
                    obj = json.loads(escaped)
                    logger.debug("Parsed JSON after escaping control chars in strings")
                    stripped = escaped
                    parse_exc = None
                except json.JSONDecodeError as exc2:
                    parse_exc = exc2
            if obj is None and parse_exc is not None:
                exc = parse_exc
                allow_inject = (
                    stage == "stage1"
                    and not getattr(self._validation, "disable_truncation_repair", True)
                )
                repaired = _try_repair_json_syntax(
                    stripped, stage, allow_tail_inject=allow_inject
                )
                if repaired is not None:
                    try:
                        obj = json.loads(repaired)
                        logger.warning(
                            "Repaired truncated %s JSON (%d -> %d chars)",
                            stage,
                            len(stripped),
                            len(repaired),
                        )
                    except json.JSONDecodeError:
                        repaired = None
                if repaired is None:
                    pos = f"{exc.lineno}:{exc.colno}"
                    return ValidationError(
                        category="a",
                        stage=stage,
                        raw_text=raw_text,
                        parse_position=pos,
                        message=f"JSON syntax error at {pos}: {exc.msg}",
                    )

        if not isinstance(obj, dict):
            return ValidationError(
                category="a",
                stage=stage,
                raw_text=raw_text,
                message="Top-level JSON value is not an object",
            )

        obj = self.normalize_parsed(
            stage,
            obj,
            decision_stance=decision_stance,
            kline_frame=kline_frame,
            stage1_json=stage1_json,
            incremental_new_bar_count=incremental_new_bar_count,
            incremental_previous_stage1=incremental_previous_stage1,
            skip_next_bar=False if stage == "stage2" else skip_next_bar,
            previous_record=previous_record,
            structure_flip_cooldown_bars=structure_flip_cooldown_bars,
        )
        norm_mode = getattr(self._validation, "normalization_mode", "strict")

        # ── Schema validation (b and c) ───────────────────────────────────────
        try:
            import jsonschema  # type: ignore[import]
        except ImportError:
            logger.warning("jsonschema not installed; skipping schema validation")
            return Ok(obj=obj)

        errors = list(jsonschema.Draft7Validator(schema).iter_errors(obj))

        # Classify errors
        missing: list[str] = []
        invalid: list[str] = []
        allowed: dict[str, list] = {}

        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or err.schema_path[-1]
            if err.validator == "required":
                # Extract the missing property name from the message
                missing.append(err.message.split("'")[1] if "'" in err.message else str(path))
            else:
                invalid.append(str(path) or err.message[:80])
                if "enum" in err.schema:
                    allowed[str(path)] = err.schema["enum"]

        # ── Explicit cross-field checks ───────────────────────────────────────
        if stage == "stage1":
            from pa_agent.ai.coherence_checks import auto_fix_bar_by_bar_types

            # Auto-correct contradicting bar_type values before validation so
            # minor model slips (writing trend_bull when program says trend_bear)
            # don't cause the whole analysis to fail.
            for msg in auto_fix_bar_by_bar_types(obj, kline_frame=kline_frame):
                import logging as _logging
                _logging.getLogger(__name__).info("stage1 %s", msg)

            if getattr(self._validation, "stage1_coherence_checks", False):
                from pa_agent.ai.decision_tree import validate_gate_result_consistency
                from pa_agent.ai.coherence_checks import (
                    validate_incremental_stage1_coherence,
                    validate_stage1_coherence,
                )

                for msg in validate_gate_result_consistency(obj):
                    invalid.append(f"gate:{msg}")
                for msg in validate_stage1_coherence(
                    obj,
                    kline_frame=kline_frame,
                    strict_bar_features=getattr(
                        self._validation, "strict_bar_by_bar_features", False
                    ),
                ):
                    invalid.append(f"s1:{msg}")
                if incremental_new_bar_count > 0:
                    for msg in validate_incremental_stage1_coherence(
                        obj,
                        new_bar_count=incremental_new_bar_count,
                        previous_stage1=incremental_previous_stage1,
                    ):
                        invalid.append(f"s1:{msg}")
            if getattr(self._validation, "trace_semantic_checks", False):
                from pa_agent.ai.trace_semantic_checks import validate_trace_semantics

                gate_trace = obj.get("gate_trace")
                if isinstance(gate_trace, list):
                    for msg in validate_trace_semantics(
                        gate_trace,
                        path_prefix="gate_trace",
                        stage="stage1",
                        gate_result=str(obj.get("gate_result", "")),
                    ):
                        invalid.append(f"trace_semantic:{msg}")

        if stage == "stage2":
            no_order_err = self._check_no_order_invariant(obj)
            if no_order_err:
                invalid.extend(no_order_err["fields"])
                allowed.update(no_order_err["allowed"])

            breakout_err = self._check_breakout_order_basis(obj)
            if breakout_err:
                invalid.extend(breakout_err["fields"])
                allowed.update(breakout_err["allowed"])

            for msg in self._check_breakout_price_extreme(obj, kline_frame):
                invalid.append(f"breakout_price:{msg}")

            for msg in self._check_signal_chain(
                obj,
                kline_frame,
                lenient=norm_mode == "lenient",
            ):
                invalid.append(f"signal_chain:{msg}")

            for msg in self._check_next_bar_prediction(obj):
                invalid.append(msg)

            for msg in self._check_next_cycle_prediction(obj):
                invalid.append(msg)

            for msg in self._check_trade_metrics(
                obj,
                decision_stance=decision_stance,
                kline_frame=kline_frame,
            ):
                invalid.append(f"metrics:{msg}")

            if getattr(self._validation, "stage2_coherence_checks", False):
                from pa_agent.ai.decision_tree import validate_stage2_trace_consistency
                from pa_agent.ai.coherence_checks import validate_stage2_coherence

                for msg in validate_stage2_trace_consistency(obj):
                    invalid.append(f"trace:{msg}")
                if isinstance(stage1_json, dict):
                    for msg in validate_stage2_coherence(
                        obj, stage1_json, kline_frame=kline_frame
                    ):
                        invalid.append(f"s2:{msg}")
            if getattr(self._validation, "trace_semantic_checks", False):
                from pa_agent.ai.trace_semantic_checks import (
                    validate_stage2_order_trace_semantics,
                    validate_trace_semantics,
                )

                decision_trace = obj.get("decision_trace")
                if isinstance(decision_trace, list):
                    for msg in validate_trace_semantics(
                        decision_trace,
                        path_prefix="decision_trace",
                        stage="stage2",
                    ):
                        invalid.append(f"trace_semantic:{msg}")
                for msg in validate_stage2_order_trace_semantics(obj):
                    invalid.append(f"trace_semantic:{msg}")

        if not errors and not missing and not invalid:
            return Ok(obj=obj)

        # Determine category: b if only missing fields, c otherwise
        if invalid or (missing and errors[0].validator not in ("required",)):
            category: Literal["b", "c"] = "c"
        elif missing:
            category = "b"
        else:
            category = "c"

        first_message = errors[0].message[:120] if errors else (invalid[0] if invalid else "custom validation failed")
        return ValidationError(
            category=category,
            stage=stage,
            raw_text=raw_text,
            missing_fields=missing,
            invalid_fields=invalid,
            allowed_values=allowed,
            message=f"{len(errors)} schema error(s): {first_message}",
        )

    _check_no_order_invariant = staticmethod(business_rules.check_no_order_invariant)
    _check_breakout_order_basis = staticmethod(business_rules.check_breakout_order_basis)
    _check_trade_metrics = staticmethod(business_rules.check_trade_metrics)
    _check_breakout_price_extreme = staticmethod(business_rules.check_breakout_price_extreme)
    _check_next_cycle_prediction = staticmethod(business_rules.check_next_cycle_prediction)
    _check_next_bar_prediction = staticmethod(business_rules.check_next_bar_prediction)
    _check_signal_chain = staticmethod(business_rules.check_signal_chain)
