"""Pydantic v2 data models for PA Agent records persistence.

Defines the canonical schema for analysis records, followup turns,
alarm payloads, validation errors, and experience entries.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _prompt_ids_for_legacy_files(filenames: list[str]) -> list[str] | None:
    """Resolve a complete legacy list, preserving unknown old records unchanged."""
    from pa_agent.ai.prompting import TEMPLATE_CATALOG, PromptCatalogError

    try:
        return [str(TEMPLATE_CATALOG.resolve_legacy_filename(filename)) for filename in filenames]
    except PromptCatalogError:
        return None


def _legacy_files_for_prompt_ids(prompt_ids: list[str]) -> list[str]:
    """Project stable Prompt IDs to immutable legacy filenames."""
    from pa_agent.ai.prompting import TEMPLATE_CATALOG, PromptId

    return [TEMPLATE_CATALOG.legacy_filename(PromptId(prompt_id)) for prompt_id in prompt_ids]


def _synchronize_strategy_prompt_identity(
    *,
    prompt_ids: list[str],
    filenames: list[str],
) -> tuple[list[str], list[str]]:
    """Normalize the stable and legacy strategy identities as one contract."""
    if prompt_ids:
        projected = _legacy_files_for_prompt_ids(prompt_ids)
        if filenames and filenames != projected:
            raise ValueError("Record strategy Prompt IDs and files do not match")
        return prompt_ids, projected
    if filenames:
        resolved = _prompt_ids_for_legacy_files(filenames)
        if resolved is not None:
            return resolved, _legacy_files_for_prompt_ids(resolved)
        return [], filenames
    return [], []


class RecordMeta(BaseModel):
    """Metadata captured at the moment of analysis submission."""

    model_config = ConfigDict(extra="forbid")

    timestamp_local_iso: str  # Local time ISO string, used for filename
    timestamp_local_ms: int  # Local time in milliseconds
    symbol: str
    timeframe: str
    bar_count: int
    ai_provider: dict  # Sanitized provider config snapshot (no plaintext API key)
    decision_stance: str = (
        "conservative"  # conservative | balanced | aggressive | extreme_aggressive
    )


class AnalysisRecord(BaseModel):
    """Full record of a two-stage AI analysis run."""

    model_config = ConfigDict(extra="forbid")

    meta: RecordMeta
    kline_data: list[dict]  # Same data as sent to AI
    htf_text: str
    stage1_messages: list[dict]
    stage1_response: dict | None  # Raw response (includes reasoning_content)
    stage1_diagnosis: dict | None
    stage2_messages: list[dict]
    stage2_response: dict | None
    stage2_decision: dict | None
    strategy_files_used: list[str]
    strategy_prompt_ids_used: list[str] = Field(default_factory=list)
    experience_loaded: list[dict]
    exception: dict | None  # If error occurred: category + debug info
    usage_total: dict  # Cumulative usage for audit

    @model_validator(mode="after")
    def _synchronize_strategy_prompt_identity(self) -> "AnalysisRecord":
        """Keep new Prompt IDs and the legacy filename field mutually consistent."""
        prompt_ids, filenames = _synchronize_strategy_prompt_identity(
            prompt_ids=self.strategy_prompt_ids_used,
            filenames=self.strategy_files_used,
        )
        self.strategy_prompt_ids_used = prompt_ids
        self.strategy_files_used = filenames
        return self

    def model_copy(
        self,
        *,
        update: dict | None = None,
        deep: bool = False,
    ) -> "AnalysisRecord":
        """Copy a record while preserving the Prompt ID/filename dual contract."""
        normalized_update = dict(update or {})
        if {
            "strategy_prompt_ids_used",
            "strategy_files_used",
        } & normalized_update.keys():
            prompt_ids, filenames = _synchronize_strategy_prompt_identity(
                prompt_ids=list(normalized_update.get("strategy_prompt_ids_used") or []),
                filenames=list(normalized_update.get("strategy_files_used") or []),
            )
            normalized_update["strategy_prompt_ids_used"] = prompt_ids
            normalized_update["strategy_files_used"] = filenames
        return super().model_copy(update=normalized_update, deep=deep)


class FollowupTurn(BaseModel):
    """A single turn in the post-analysis free-chat session."""

    model_config = ConfigDict(extra="forbid")

    turn: int
    ts_ms: int
    user: str
    ai_content: str
    ai_reasoning: str | None
    usage: dict
    cancelled: bool = False


class AlarmPayload(BaseModel):
    """Payload emitted when a JSON validation alarm is triggered (R8.6)."""

    model_config = ConfigDict(extra="forbid")

    category: str  # 'a'..'e'
    stage: str  # '阶段一-诊断' or '阶段二-决策'
    timestamp_local_iso: str
    raw_text: str
    parse_position: str | None
    missing_fields: list[str]
    invalid_fields: list[str]
    consecutive_count: int
    history_excerpt: list[dict]


class ValidationError(BaseModel):
    """Structured validation error produced by JsonValidator.

    Note: this is a Pydantic model, not the built-in exception class.
    """

    model_config = ConfigDict(extra="forbid")

    category: str  # 'a', 'b', 'c', or 'd'
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    raw_text: str
    parse_position: str | None = None
    allowed_values: dict = {}


class ExperienceEntry(BaseModel):
    """A single entry loaded from the experience library."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    case_type: str  # 'success' or 'failure'
    cycle_position: str
    timestamp_ms: int
    content: dict  # Parsed JSON content of the experience file
