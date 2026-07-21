"""Compatibility helpers for incremental PromptAssembler template migration."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from pa_agent.ai.prompting.template_store import TemplateStore, TemplateStoreError

logger = logging.getLogger(__name__)


def prepare_template_store(
    root: Path,
    store: Any | None,
    enabled: bool,
) -> tuple[dict[str, str], Any, bool]:
    """Prepare assembler cache state without changing its public constructor."""
    return {}, store if store is not None else TemplateStore(root), enabled


def load_shared_system_templates(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    names: Sequence[str],
    *,
    warning_logger: logging.Logger | None = None,
) -> tuple[str, ...]:
    """Load shared system templates and explicitly fall back to the legacy loader."""
    if enabled:
        try:
            return tuple(store.load_many(names, stage="stage1"))
        except TemplateStoreError as exc:
            (warning_logger or logger).warning(
                "TemplateStore system prompt load failed; falling back to legacy loader: %s",
                exc,
            )
    return tuple(legacy_load(name) for name in names)


def _make_template_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    names: Sequence[str],
    *,
    stage: Literal["stage1", "stage2"],
    stage_label: str,
    warning_logger: logging.Logger | None = None,
) -> Callable[[str], str]:
    """Build an atomic stage loader with a legacy fallback."""
    templates: dict[str, str] | None = None
    if enabled:
        try:
            loaded = store.load_many(names, stage=stage)
            templates = dict(zip(names, loaded, strict=True))
        except TemplateStoreError as exc:
            (warning_logger or logger).warning(
                "TemplateStore %s prompt load failed; falling back to legacy loader: %s",
                stage_label,
                exc,
            )

    if templates is None:
        return legacy_load

    def _load(name: str) -> str:
        if name in templates:
            return templates[name]
        return legacy_load(name)

    return _load


def make_stage1_template_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    names: Sequence[str],
    *,
    warning_logger: logging.Logger | None = None,
) -> Callable[[str], str]:
    """Build a Stage 1 loader that switches atomically or falls back as a group."""
    return _make_template_loader(
        store,
        enabled,
        legacy_load,
        names,
        stage="stage1",
        stage_label="Stage 1",
        warning_logger=warning_logger,
    )


def make_stage2_template_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    names: Sequence[str],
    *,
    warning_logger: logging.Logger | None = None,
) -> Callable[[str], str]:
    """Build a Stage 2 loader that switches atomically or falls back as a group."""
    return _make_template_loader(
        store,
        enabled,
        legacy_load,
        names,
        stage="stage2",
        stage_label="Stage 2",
        warning_logger=warning_logger,
    )
