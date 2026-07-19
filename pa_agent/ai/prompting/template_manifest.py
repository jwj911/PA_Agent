"""Manifest for the existing prompt-engineering text templates.

The manifest is intentionally metadata-only. It does not alter the ordered
lists consumed by ``PromptAssembler``; it gives the next template-engineering
slice an explicit, validated description of stage ownership and contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pa_agent.ai import strategy_files as sf

StageName = Literal["stage1", "stage2"]
TemplateRole = Literal["system", "task", "base", "strategy"]
MANIFEST_VERSION = "v1"
_VALID_STAGES = frozenset(("stage1", "stage2"))
_VALID_ROLES = frozenset(("system", "task", "base", "strategy"))


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    """Static metadata for one prompt-engineering text file."""

    name: str
    stages: tuple[StageName, ...]
    role: TemplateRole
    output_contract: str | None = None
    dependencies: tuple[str, ...] = ()
    version: str = MANIFEST_VERSION


def _spec(
    name: str,
    stages: tuple[StageName, ...],
    role: TemplateRole,
    *,
    output_contract: str | None = None,
    dependencies: tuple[str, ...] = (),
) -> TemplateSpec:
    return TemplateSpec(
        name=name,
        stages=stages,
        role=role,
        output_contract=output_contract,
        dependencies=dependencies,
    )


TEMPLATE_MANIFEST: tuple[TemplateSpec, ...] = (
    _spec(sf.PERSONA, ("stage1", "stage2"), "system"),
    _spec(
        sf.BINARY_DECISION,
        ("stage1", "stage2"),
        "system",
        output_contract="stage1_diagnosis",
    ),
    _spec(
        sf.MARKET_DIAGNOSIS,
        ("stage1",),
        "task",
        output_contract="stage1_diagnosis",
        dependencies=(sf.BINARY_DECISION,),
    ),
    _spec(
        sf.KLINE_SIGNAL,
        ("stage1", "stage2"),
        "base",
        output_contract="stage1_diagnosis|stage2_decision",
        dependencies=(sf.BINARY_DECISION,),
    ),
    _spec(
        sf.BAR_CHECKLIST,
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(sf.BINARY_DECISION,),
    ),
    _spec(
        sf.STOP_TARGET_POSITION,
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(sf.BINARY_DECISION,),
    ),
    _spec(
        sf.MEASURED_MOVE,
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(sf.BINARY_DECISION,),
    ),
    _spec(
        sf.BULLISH_CHANNEL_ID,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        sf.BULLISH_CHANNEL_STRATEGY,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(sf.BULLISH_CHANNEL_ID,),
    ),
    _spec(
        sf.BEARISH_CHANNEL_ID,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        sf.BEARISH_CHANNEL_STRATEGY,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(sf.BEARISH_CHANNEL_ID,),
    ),
    _spec(
        sf.BULLISH_SPIKE_ID,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        sf.BULLISH_SPIKE_STRATEGY,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(sf.BULLISH_SPIKE_ID,),
    ),
    _spec(
        sf.BEARISH_SPIKE_ID,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        sf.BEARISH_SPIKE_STRATEGY,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(sf.BEARISH_SPIKE_ID,),
    ),
    _spec(sf.RANGE_ID, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(
        sf.RANGE_STRATEGY,
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(sf.RANGE_ID,),
    ),
    _spec(sf.CHANNEL_WIDTH, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.WEDGE, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.REVERSAL, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.BREAKOUT_FAILURE, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.H1H2, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.ALWAYS_IN, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.BARBWIRE, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.MAGNET, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.FINAL_FLAG, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.MTR, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.TRIANGLE, ("stage2",), "strategy", output_contract="stage2_decision"),
    _spec(sf.DOUBLE_TOP_BOTTOM, ("stage2",), "strategy", output_contract="stage2_decision"),
)


def validate_template_manifest(
    manifest: tuple[TemplateSpec, ...] = TEMPLATE_MANIFEST,
) -> dict[str, TemplateSpec]:
    """Validate and index a manifest, failing closed on contract mistakes."""
    indexed: dict[str, TemplateSpec] = {}
    for spec in manifest:
        template_path = Path(spec.name)
        if (
            not spec.name
            or spec.name != spec.name.strip()
            or template_path.name != spec.name
            or template_path.suffix.lower() != ".txt"
        ):
            raise ValueError(f"Invalid template name: {spec.name!r}")
        if spec.name in indexed:
            raise ValueError(f"Duplicate template name: {spec.name}")
        if not spec.stages or any(stage not in _VALID_STAGES for stage in spec.stages):
            raise ValueError(f"Invalid stages for template {spec.name}: {spec.stages!r}")
        if spec.role not in _VALID_ROLES:
            raise ValueError(f"Invalid role for template {spec.name}: {spec.role!r}")
        if not spec.version:
            raise ValueError(f"Missing version for template {spec.name}")
        indexed[spec.name] = spec

    for spec in manifest:
        missing_dependencies = sorted(
            dependency for dependency in spec.dependencies if dependency not in indexed
        )
        if missing_dependencies:
            raise ValueError(
                f"Unknown dependencies for template {spec.name}: {missing_dependencies}"
            )
    return indexed


TEMPLATE_MANIFEST_BY_NAME = validate_template_manifest()


def template_files_for_stage(stage: StageName) -> tuple[str, ...]:
    """Return manifest-ordered template names assigned to *stage*."""
    if stage not in _VALID_STAGES:
        raise ValueError(f"Unknown template stage: {stage!r}")
    return tuple(spec.name for spec in TEMPLATE_MANIFEST if stage in spec.stages)
