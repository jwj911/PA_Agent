"""Explicit, JSON-serializable context for prompt template orchestration.

The context intentionally contains only prompt inputs and primitive metadata.
It must not carry ``Settings``, Qt objects, network clients, or filesystem
handles.  Runtime-only objects such as ``KlineFrame`` and ``AnalysisRecord``
are reduced to safe snapshots at the boundary.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pa_agent.ai.prompting.prompt_ids import PromptId
from pa_agent.ai.prompting.template_manifest import TEMPLATE_CATALOG

if TYPE_CHECKING:
    from pa_agent.data.base import KlineFrame

TemplateContextStage = Literal["stage1", "stage2"]


def _jsonable(value: Any) -> Any:
    """Convert common project values into deterministic JSON-compatible data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _jsonable(model_dump())
    if dataclasses.is_dataclass(value):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    return str(value)


def _prompt_id_key(value: Any) -> str:
    """Normalize a Prompt ID or legacy filename to the stable ID string."""
    candidate = PromptId(str(value))
    if candidate in TEMPLATE_CATALOG.by_id:
        return str(candidate)
    return str(TEMPLATE_CATALOG.resolve_legacy_filename(str(value)))


@dataclass(frozen=True, slots=True)
class TemplateContext:
    """Immutable prompt inputs safe to serialize or snapshot."""

    stage: TemplateContextStage
    symbol: str
    timeframe: str
    bar_count: int
    stage1_diagnosis: dict[str, Any] = field(default_factory=dict)
    strategy_prompt_ids: tuple[PromptId, ...] = ()
    strategy_files: tuple[str, ...] = ()
    experience_entries: tuple[Any, ...] = ()
    decision_stance: str = "conservative"
    previous_record: Any | None = None
    feature_flags: dict[str, bool] = field(default_factory=dict)
    template_versions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stage not in ("stage1", "stage2"):
            raise ValueError(f"Unknown template context stage: {self.stage!r}")
        if self.bar_count < 0:
            raise ValueError("Template context bar_count must not be negative")
        object.__setattr__(self, "symbol", str(self.symbol))
        object.__setattr__(self, "timeframe", str(self.timeframe))
        object.__setattr__(
            self,
            "stage1_diagnosis",
            _jsonable(self.stage1_diagnosis),
        )
        prompt_ids = tuple(PromptId(str(prompt_id)) for prompt_id in self.strategy_prompt_ids)
        legacy_files = tuple(str(name) for name in self.strategy_files)
        if prompt_ids:
            projected_files = TEMPLATE_CATALOG.legacy_filenames(prompt_ids)
            if legacy_files and legacy_files != projected_files:
                raise ValueError("Template context strategy IDs and files do not match")
            legacy_files = projected_files
        elif legacy_files:
            prompt_ids = tuple(
                TEMPLATE_CATALOG.resolve_legacy_filename(name) for name in legacy_files
            )
        object.__setattr__(self, "strategy_prompt_ids", prompt_ids)
        object.__setattr__(self, "strategy_files", legacy_files)
        object.__setattr__(
            self,
            "experience_entries",
            tuple(_jsonable(entry) for entry in self.experience_entries),
        )
        object.__setattr__(self, "decision_stance", str(self.decision_stance))
        object.__setattr__(self, "previous_record", _jsonable(self.previous_record))
        object.__setattr__(
            self,
            "feature_flags",
            {
                str(name): bool(value)
                for name, value in sorted(self.feature_flags.items(), key=lambda pair: str(pair[0]))
            },
        )
        object.__setattr__(
            self,
            "template_versions",
            {
                _prompt_id_key(name): str(version)
                for name, version in sorted(
                    self.template_versions.items(),
                    key=lambda pair: str(pair[0]),
                )
            },
        )

    @classmethod
    def from_stage2_inputs(
        cls,
        frame: KlineFrame,
        stage1_diagnosis: Mapping[str, Any],
        strategy_files: Sequence[str],
        experience_entries: Sequence[Any],
        *,
        decision_stance: str,
        previous_record: Any | None = None,
        feature_flags: Mapping[str, bool] | None = None,
        template_versions: Mapping[str, str] | None = None,
    ) -> TemplateContext:
        """Build a Stage 2 context from legacy strategy filenames."""
        strategy_prompt_ids = tuple(
            TEMPLATE_CATALOG.resolve_legacy_filename(name) for name in strategy_files
        )
        return cls.from_stage2_prompt_ids(
            frame,
            stage1_diagnosis,
            strategy_prompt_ids,
            experience_entries,
            decision_stance=decision_stance,
            previous_record=previous_record,
            feature_flags=feature_flags,
            template_versions=template_versions,
        )

    @classmethod
    def from_stage2_prompt_ids(
        cls,
        frame: KlineFrame,
        stage1_diagnosis: Mapping[str, Any],
        strategy_prompt_ids: Sequence[PromptId],
        experience_entries: Sequence[Any],
        *,
        decision_stance: str,
        previous_record: Any | None = None,
        feature_flags: Mapping[str, bool] | None = None,
        template_versions: Mapping[str, str] | None = None,
    ) -> TemplateContext:
        """Build a Stage 2 context from stable IDs without retaining services."""
        ordered_ids = tuple(strategy_prompt_ids)
        return cls(
            stage="stage2",
            symbol=frame.symbol,
            timeframe=frame.timeframe,
            bar_count=len(frame.bars),
            stage1_diagnosis=dict(stage1_diagnosis),
            strategy_prompt_ids=ordered_ids,
            strategy_files=TEMPLATE_CATALOG.legacy_filenames(ordered_ids),
            experience_entries=tuple(experience_entries),
            decision_stance=decision_stance,
            previous_record=previous_record,
            feature_flags=dict(feature_flags or {}),
            template_versions=dict(template_versions or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""
        return {
            "stage": self.stage,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_count": self.bar_count,
            "stage1_diagnosis": _jsonable(self.stage1_diagnosis),
            "strategy_prompt_ids": list(self.strategy_prompt_ids),
            "strategy_files": list(self.strategy_files),
            "experience_entries": _jsonable(self.experience_entries),
            "decision_stance": self.decision_stance,
            "previous_record": _jsonable(self.previous_record),
            "feature_flags": _jsonable(self.feature_flags),
            "template_versions": _jsonable(self.template_versions),
        }
