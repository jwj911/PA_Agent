"""PyQt-free state values for the incremental pipeline migration."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from numbers import Real
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pa_agent.records.schema import AnalysisRecord
from pa_agent.util.threading import CancelToken, OrchestratorEvent


class TerminalStatus(StrEnum):
    """Explicit terminal status for one pipeline execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INSUFFICIENT_DATA = "insufficient_data"
    STAGE1_FAILED = "stage1_failed"
    STAGE2_FAILED = "stage2_failed"
    ROUTE_FAILED = "route_failed"
    # Keep the longer spelling available to callers that use "routing".
    ROUTING_FAILED = "route_failed"
    PERSIST_FAILED = "persist_failed"
    # Keep the longer spelling available to callers that use "persistence".
    PERSISTENCE_FAILED = "persist_failed"
    FAILED = "failed"


class PersistenceIntent(StrEnum):
    """Requested persistence action for the current pipeline state."""

    NONE = "none"
    FULL = "full"
    PARTIAL = "partial"


_FAILURE_STAGE_TO_STATUS = {
    "route": TerminalStatus.ROUTE_FAILED,
    "routing": TerminalStatus.ROUTE_FAILED,
    "persist": TerminalStatus.PERSIST_FAILED,
    "persistence": TerminalStatus.PERSIST_FAILED,
}
_FAILURE_TYPE_TO_STATUS = {
    "route_error": TerminalStatus.ROUTE_FAILED,
    "route_failure": TerminalStatus.ROUTE_FAILED,
    "route_failed": TerminalStatus.ROUTE_FAILED,
    "routing_error": TerminalStatus.ROUTE_FAILED,
    "routing_failure": TerminalStatus.ROUTE_FAILED,
    "persist_error": TerminalStatus.PERSIST_FAILED,
    "persist_failure": TerminalStatus.PERSIST_FAILED,
    "persist_failed": TerminalStatus.PERSIST_FAILED,
    "persistence_error": TerminalStatus.PERSIST_FAILED,
    "persistence_failure": TerminalStatus.PERSIST_FAILED,
    "persistence_failed": TerminalStatus.PERSIST_FAILED,
    "save_error": TerminalStatus.PERSIST_FAILED,
}
_USAGE_FIELDS = (
    "prompt_tokens",
    "cached_prompt_tokens",
    "completion_tokens",
    "total_tokens",
)
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "callback",
    "client",
    "prompt",
    "message",
    "content",
    "response",
    "reply",
    "raw",
    "frame",
    "kline",
    "market",
    "quote",
    "price",
)
_SAFE_STRING_KEYS = frozenset(
    {
        "analysis_mode",
        "base_url",
        "decision_stance",
        "model",
        "mode",
        "name",
        "normalization_mode",
        "reasoning_effort",
        "route",
        "status",
        "version",
    }
)
_SAFE_NUMERIC_KEYS = frozenset(
    {
        "context_window",
        "experience_max_chars_per_entry",
        "experience_max_entries",
        "incremental_new_bar_count",
        "retry_max",
        "structure_flip_cooldown_bars",
    }
)
_SAFE_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,79}$", re.IGNORECASE)
_SAFE_REASON_RE = re.compile(
    r"^(?:"
    r"user_cancelled|insufficient_data|network_error|disk_error|"
    r"provider_error|validation_error|cancelled|"
    r"stage[12](?:_failed|_[a-e])|"
    r"(?:route|routing)_(?:failed|error)|"
    r"(?:persist|persistence)_(?:failed|error)"
    r")$",
    re.IGNORECASE,
)


def _is_sensitive_key(key: str) -> bool:
    """Return whether a metadata key can carry data excluded from summaries."""
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _safe_metadata(value: Any, *, key: str = "") -> Any:
    """Copy only scalar, allowlisted runtime metadata.

    Pipeline state can contain arbitrary adapter objects, so summary creation
    must be allowlist-based. In particular, this function never falls back to
    ``repr(value)`` or serializes unknown objects.
    """
    if key and _is_sensitive_key(key):
        return None
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, Real):
        if key not in _SAFE_NUMERIC_KEYS:
            return None
        number = float(value)
        if not math.isfinite(number):
            return None
        if isinstance(value, int):
            return value
        return number
    if isinstance(value, str):
        if key not in _SAFE_STRING_KEYS:
            return None
        if len(value) > 128:
            return None
        if key == "base_url":
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                return None
            # A provider may encode credentials or tenant data in its path.
            # Keep only the origin in a summary.
            return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        if not _SAFE_LABEL_RE.fullmatch(value):
            return None
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for child_key, child_value in value.items():
            if not isinstance(child_key, str) or _is_sensitive_key(child_key):
                continue
            safe_value = _safe_metadata(child_value, key=child_key)
            if safe_value is not None:
                result[child_key] = safe_value
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            safe_item = _safe_metadata(item, key=key)
            if safe_item is not None:
                result.append(safe_item)
        return result
    return None


def _safe_usage(value: Any) -> dict[str, int]:
    """Extract token counters without serializing arbitrary usage objects."""
    result: dict[str, int] = {}
    for name in _USAGE_FIELDS:
        raw = value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)
        if isinstance(raw, bool) or not isinstance(raw, Real):
            continue
        number = float(raw)
        if math.isfinite(number):
            result[name] = max(0, int(number))
    return result


def _safe_partial_reason(reason: str | None) -> str | None:
    """Keep stable machine labels while replacing free-form error text."""
    if reason is None:
        return None
    if _SAFE_REASON_RE.fullmatch(reason):
        return reason
    return "redacted"


def _reply_summary(reply: Any) -> dict[str, Any]:
    """Return reply presence and usage metadata, never reply text or raw data."""
    if reply is None:
        return {"present": False, "usage": {}}
    usage = reply.get("usage") if isinstance(reply, Mapping) else getattr(reply, "usage", None)
    return {
        "present": True,
        "usage": _safe_usage(usage),
    }


def _stage_summary(
    messages: Sequence[Any],
    reply: Any,
    normalized_json: Any,
    usage: Any,
    usage_calls: Sequence[Any],
) -> dict[str, Any]:
    """Summarize one stage without copying message or response contents."""
    roles = []
    for message in messages:
        role = message.get("role") if isinstance(message, Mapping) else None
        roles.append(role if role in {"system", "user", "assistant", "tool"} else "other")
    return {
        "message_count": len(messages),
        "message_roles": roles,
        "reply": _reply_summary(reply),
        "normalized_json_present": normalized_json is not None,
        "usage": _safe_usage(usage),
        "usage_call_count": len(usage_calls),
    }


def _route_summary(
    route_outputs: Mapping[str, Any],
    strategy_files: Sequence[str],
    experience_entries: Sequence[Any],
) -> dict[str, Any]:
    """Summarize route cardinalities without exposing route payloads."""
    files = route_outputs.get("strategy_files", strategy_files)
    entries = route_outputs.get("experience_entries", experience_entries)
    file_count = len(files) if isinstance(files, Sequence) and not isinstance(files, str) else 0
    entry_count = (
        len(entries) if isinstance(entries, Sequence) and not isinstance(entries, str) else 0
    )
    return {
        "output_present": bool(route_outputs or strategy_files or experience_entries),
        "strategy_file_count": file_count,
        "experience_entry_count": entry_count,
    }


def _exception_value(record: AnalysisRecord | None, name: str) -> str:
    if record is None:
        return ""
    exception = getattr(record, "exception", None)
    if not isinstance(exception, Mapping):
        return ""
    value = exception.get(name)
    return value.strip().lower() if isinstance(value, str) else ""


def terminal_status_for(
    record: AnalysisRecord | None,
    events: Sequence[OrchestratorEvent],
    *,
    partial_reason: str | None = None,
) -> TerminalStatus:
    """Map legacy record/events to the explicit pipeline terminal status."""
    event_set = set(events)
    if OrchestratorEvent.Cancelled in event_set:
        return TerminalStatus.CANCELLED
    if OrchestratorEvent.InsufficientData in event_set:
        return TerminalStatus.INSUFFICIENT_DATA
    if OrchestratorEvent.Stage1Failed in event_set:
        return TerminalStatus.STAGE1_FAILED
    if OrchestratorEvent.Stage2Failed in event_set:
        return TerminalStatus.STAGE2_FAILED
    failure_stage = _exception_value(record, "stage")
    if failure_stage in _FAILURE_STAGE_TO_STATUS:
        return _FAILURE_STAGE_TO_STATUS[failure_stage]
    failure_type = _exception_value(record, "type")
    if failure_type in _FAILURE_TYPE_TO_STATUS:
        return _FAILURE_TYPE_TO_STATUS[failure_type]
    reason = (partial_reason or "").strip().lower()
    if reason in _FAILURE_TYPE_TO_STATUS:
        return _FAILURE_TYPE_TO_STATUS[reason]
    if record is not None and record.exception is None:
        return TerminalStatus.COMPLETED
    return TerminalStatus.FAILED


@dataclass(slots=True)
class PipelineState:
    """Mutable execution state carried between pipeline steps.

    Runtime callbacks and service objects are intentionally kept at the
    adapter boundary. They are not serialized or exposed as record payload.
    """

    frame: Any = field(repr=False)
    cancel_token: CancelToken = field(repr=False)
    on_event: Callable[[OrchestratorEvent], None] = field(
        default=lambda _event: None,
        repr=False,
    )
    on_stage1_reasoning: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage1_content: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage2_reasoning: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage2_content: Callable[[str], None] | None = field(default=None, repr=False)
    on_stage_prompt: Callable[[str, str, str], None] | None = field(default=None, repr=False)
    on_stage2_files: Callable[[list[str]], None] | None = field(default=None, repr=False)
    previous_record: AnalysisRecord | None = field(default=None, repr=False)
    incremental_new_bar_count: int | None = None
    record: AnalysisRecord | None = field(default=None, repr=False)

    # Stage snapshots are deliberately kept separate from AnalysisRecord.
    # The real steps will populate these fields in later migration slices.
    stage1_messages: list[dict[str, Any]] = field(default_factory=list, repr=False)
    stage1_reply: Any = field(default=None, repr=False)
    stage1_normalized_json: dict[str, Any] | None = field(default=None, repr=False)
    stage1_usage: dict[str, Any] = field(default_factory=dict, repr=False)
    stage1_usage_calls: list[Any] = field(default_factory=list, repr=False)
    stage1_thinking: bool = field(default=True, repr=False)
    stage1_reasoning_effort: str = field(default="high", repr=False)
    stage2_messages: list[dict[str, Any]] = field(default_factory=list, repr=False)
    stage2_reply: Any = field(default=None, repr=False)
    stage2_normalized_json: dict[str, Any] | None = field(default=None, repr=False)
    stage2_usage: dict[str, Any] = field(default_factory=dict, repr=False)
    stage2_usage_calls: list[Any] = field(default_factory=list, repr=False)
    strategy_files: list[str] = field(default_factory=list, repr=False)
    experience_entries: list[Any] = field(default_factory=list, repr=False)
    route_outputs: dict[str, Any] = field(default_factory=dict, repr=False)
    partial_reason: str | None = field(default=None, repr=False)
    persistence_intent: PersistenceIntent = PersistenceIntent.NONE
    settings_metadata: dict[str, Any] = field(default_factory=dict, repr=False)
    feature_metadata: dict[str, Any] = field(default_factory=dict, repr=False)
    usage_total: dict[str, Any] = field(default_factory=dict, repr=False)
    terminal_status: TerminalStatus = TerminalStatus.RUNNING
    events: list[OrchestratorEvent] = field(default_factory=list)
    step_history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize enum inputs passed by compatibility callers."""
        self.persistence_intent = PersistenceIntent(self.persistence_intent)
        self.terminal_status = TerminalStatus(self.terminal_status)

    def emit(self, event: OrchestratorEvent) -> None:
        """Record and forward one legacy orchestrator event."""
        self.events.append(event)
        self.on_event(event)

    def mark_terminal(self, status: TerminalStatus | str) -> None:
        """Set a terminal status while preventing accidental rewrites."""
        status = TerminalStatus(status)
        if status is TerminalStatus.RUNNING:
            raise ValueError("Pipeline terminal status cannot be running")
        if (
            self.terminal_status is not TerminalStatus.RUNNING
            and self.terminal_status is not status
        ):
            raise ValueError(
                f"Pipeline already terminated with {self.terminal_status.value}"
            )
        self.terminal_status = status
        if status is TerminalStatus.COMPLETED:
            if self.persistence_intent is PersistenceIntent.NONE:
                self.set_persistence_intent(PersistenceIntent.FULL)
        elif self.persistence_intent is PersistenceIntent.NONE:
            self.set_persistence_intent(PersistenceIntent.PARTIAL)
            if self.partial_reason is None:
                self.partial_reason = {
                    TerminalStatus.CANCELLED: "user_cancelled",
                    TerminalStatus.INSUFFICIENT_DATA: "insufficient_data",
                    TerminalStatus.STAGE1_FAILED: "stage1_failed",
                    TerminalStatus.STAGE2_FAILED: "stage2_failed",
                    TerminalStatus.ROUTE_FAILED: "route_failed",
                    TerminalStatus.PERSIST_FAILED: "persist_failed",
                }.get(status)

    def set_persistence_intent(self, intent: PersistenceIntent | str) -> None:
        """Set the planned record write without touching the record schema."""
        self.persistence_intent = PersistenceIntent(intent)

    def set_route_outputs(
        self,
        *,
        strategy_files: Sequence[str] = (),
        experience_entries: Sequence[Any] = (),
        **outputs: Any,
    ) -> None:
        """Store route results for later steps and keep common outputs explicit."""
        self.strategy_files = list(strategy_files)
        self.experience_entries = list(experience_entries)
        self.route_outputs = {
            **outputs,
            "strategy_files": list(self.strategy_files),
            "experience_entries": list(self.experience_entries),
        }

    @property
    def stage1_response(self) -> Any:
        """Compatibility alias for the Stage-1 reply snapshot."""
        return self.stage1_reply

    @stage1_response.setter
    def stage1_response(self, value: Any) -> None:
        self.stage1_reply = value

    @property
    def stage2_response(self) -> Any:
        """Compatibility alias for the Stage-2 reply snapshot."""
        return self.stage2_reply

    @stage2_response.setter
    def stage2_response(self, value: Any) -> None:
        self.stage2_reply = value

    @property
    def stage1_json(self) -> dict[str, Any] | None:
        """Short alias for the normalized Stage-1 JSON."""
        return self.stage1_normalized_json

    @stage1_json.setter
    def stage1_json(self, value: dict[str, Any] | None) -> None:
        self.stage1_normalized_json = value

    @property
    def stage2_json(self) -> dict[str, Any] | None:
        """Short alias for the normalized Stage-2 JSON."""
        return self.stage2_normalized_json

    @stage2_json.setter
    def stage2_json(self, value: dict[str, Any] | None) -> None:
        self.stage2_normalized_json = value

    @property
    def route_output(self) -> dict[str, Any]:
        """Singular alias for the route output mapping."""
        return self.route_outputs

    @route_output.setter
    def route_output(self, value: Mapping[str, Any]) -> None:
        self.route_outputs = dict(value)

    def update_terminal_metadata(self, record: AnalysisRecord | None = None) -> None:
        """Infer partial/persistence metadata after a compatibility submission."""
        if record is not None:
            self.record = record
        status = terminal_status_for(
            self.record,
            self.events,
            partial_reason=self.partial_reason,
        )
        if status is TerminalStatus.COMPLETED:
            self.set_persistence_intent(PersistenceIntent.FULL)
            self.partial_reason = None
        else:
            self.set_persistence_intent(PersistenceIntent.PARTIAL)
            if self.partial_reason is None:
                if status is TerminalStatus.CANCELLED:
                    self.partial_reason = "user_cancelled"
                elif status is TerminalStatus.INSUFFICIENT_DATA:
                    self.partial_reason = "insufficient_data"
                elif status is TerminalStatus.ROUTE_FAILED:
                    self.partial_reason = "route_failed"
                elif status is TerminalStatus.PERSIST_FAILED:
                    self.partial_reason = "persist_failed"
                elif status is TerminalStatus.STAGE1_FAILED:
                    self.partial_reason = "stage1_failed"
                elif status is TerminalStatus.STAGE2_FAILED:
                    self.partial_reason = "stage2_failed"

    @property
    def event_names(self) -> tuple[str, ...]:
        """Return stable event names for snapshots and adapter output."""
        return tuple(event.name for event in self.events)

    def safe_summary(self) -> dict[str, Any]:
        """Return a JSON-safe execution summary without sensitive payloads.

        This is intentionally a shape summary: stage message bodies, reply
        content/raw responses, normalized JSON values, frame bars, records,
        callbacks, cancellation tokens, settings secrets, and service clients
        are excluded.
        """
        return {
            "terminal_status": self.terminal_status.value,
            "events": list(self.event_names),
            "step_history": list(self.step_history),
            "stage1": _stage_summary(
                self.stage1_messages,
                self.stage1_reply,
                self.stage1_normalized_json,
                self.stage1_usage,
                self.stage1_usage_calls,
            ),
            "stage2": _stage_summary(
                self.stage2_messages,
                self.stage2_reply,
                self.stage2_normalized_json,
                self.stage2_usage,
                self.stage2_usage_calls,
            ),
            "route": _route_summary(
                self.route_outputs,
                self.strategy_files,
                self.experience_entries,
            ),
            "partial_reason": _safe_partial_reason(self.partial_reason),
            "persistence_intent": self._safe_persistence_intent(),
            "settings": _safe_metadata(self.settings_metadata),
            "features": _safe_metadata(self.feature_metadata),
            "usage_total": _safe_usage(self.usage_total),
        }

    def _safe_persistence_intent(self) -> str:
        try:
            return PersistenceIntent(self.persistence_intent).value
        except (TypeError, ValueError):
            return "unknown"

    def to_safe_dict(self) -> dict[str, Any]:
        """Alias for :meth:`safe_summary` for serializer-oriented callers."""
        return self.safe_summary()

    def to_safe_json(self) -> str:
        """Serialize :meth:`safe_summary` with stable keys and no raw payloads."""
        return json.dumps(
            self.safe_summary(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def serialize(self) -> str:
        """Compatibility alias for :meth:`to_safe_json`."""
        return self.to_safe_json()
