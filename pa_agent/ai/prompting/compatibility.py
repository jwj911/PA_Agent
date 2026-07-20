"""Compatibility helpers for incremental PromptAssembler template migration."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

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


def make_stage1_template_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    names: Sequence[str],
    *,
    warning_logger: logging.Logger | None = None,
) -> Callable[[str], str]:
    """Build a Stage 1 loader that switches atomically or falls back as a group."""
    templates: dict[str, str] | None = None
    if enabled:
        try:
            loaded = store.load_many(names, stage="stage1")
            templates = dict(zip(names, loaded, strict=True))
        except TemplateStoreError as exc:
            (warning_logger or logger).warning(
                "TemplateStore Stage 1 prompt load failed; falling back to legacy loader: %s",
                exc,
            )

    if templates is None:
        return legacy_load

    def _load(name: str) -> str:
        if name in templates:
            return templates[name]
        return legacy_load(name)

    return _load
