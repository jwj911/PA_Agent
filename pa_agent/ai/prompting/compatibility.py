"""Compatibility helpers for incremental PromptAssembler template migration."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from pa_agent.ai.prompting.prompt_ids import PromptId
from pa_agent.ai.prompting.template_store import TemplateStore, TemplateStoreError

logger = logging.getLogger(__name__)


def _legacy_names_for_prompt_ids(
    store: Any,
    prompt_ids: Sequence[PromptId],
) -> tuple[str, ...]:
    """Resolve legacy names for real stores and pre-M1 injected store doubles."""
    catalog = getattr(store, "catalog", None)
    if catalog is None:
        from pa_agent.ai.prompting.template_manifest import TEMPLATE_CATALOG

        catalog = TEMPLATE_CATALOG
    return tuple(catalog.legacy_filenames(tuple(prompt_ids)))


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


def load_shared_system_prompt_ids(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    prompt_ids: Sequence[PromptId],
    *,
    warning_logger: logging.Logger | None = None,
) -> tuple[str, ...]:
    """Load shared system templates by ID with explicit legacy fallback."""
    ordered_ids = tuple(prompt_ids)
    legacy_names = _legacy_names_for_prompt_ids(store, ordered_ids)
    if enabled:
        try:
            load_many_ids = getattr(store, "load_many_ids", None)
            if callable(load_many_ids):
                return tuple(load_many_ids(ordered_ids, stage="stage1"))
            return tuple(store.load_many(legacy_names, stage="stage1"))
        except TemplateStoreError as exc:
            (warning_logger or logger).warning(
                "TemplateStore system prompt load failed; falling back to legacy loader: %s",
                exc,
            )
    return tuple(legacy_load(name) for name in legacy_names)


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


def _make_prompt_id_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    prompt_ids: Sequence[PromptId],
    *,
    stage: Literal["stage1", "stage2"],
    stage_label: str,
    warning_logger: logging.Logger | None = None,
) -> Callable[[PromptId], str]:
    """Build an atomic Prompt ID loader with a legacy filename fallback."""
    ordered_ids = tuple(prompt_ids)
    legacy_names = _legacy_names_for_prompt_ids(store, ordered_ids)
    legacy_by_id = dict(zip(ordered_ids, legacy_names, strict=True))
    templates: dict[PromptId, str] | None = None
    if enabled:
        try:
            load_many_ids = getattr(store, "load_many_ids", None)
            if callable(load_many_ids):
                loaded = load_many_ids(ordered_ids, stage=stage)
            else:
                loaded = store.load_many(legacy_names, stage=stage)
            templates = dict(zip(ordered_ids, loaded, strict=True))
        except TemplateStoreError as exc:
            (warning_logger or logger).warning(
                "TemplateStore %s prompt load failed; falling back to legacy loader: %s",
                stage_label,
                exc,
            )

    def _legacy_load(prompt_id: PromptId) -> str:
        legacy_name = legacy_by_id.get(prompt_id)
        if legacy_name is None:
            legacy_name = _legacy_names_for_prompt_ids(store, (prompt_id,))[0]
        return legacy_load(legacy_name)

    if templates is None:
        return _legacy_load

    def _load(prompt_id: PromptId) -> str:
        if prompt_id in templates:
            return templates[prompt_id]
        return _legacy_load(prompt_id)

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


def make_stage1_prompt_id_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    prompt_ids: Sequence[PromptId],
    *,
    warning_logger: logging.Logger | None = None,
) -> Callable[[PromptId], str]:
    """Build a Stage 1 ID loader that switches atomically or falls back as a group."""
    return _make_prompt_id_loader(
        store,
        enabled,
        legacy_load,
        prompt_ids,
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


def make_stage2_prompt_id_loader(
    store: Any,
    enabled: bool,
    legacy_load: Callable[[str], str],
    prompt_ids: Sequence[PromptId],
    *,
    warning_logger: logging.Logger | None = None,
) -> Callable[[PromptId], str]:
    """Build a Stage 2 ID loader that switches atomically or falls back as a group."""
    return _make_prompt_id_loader(
        store,
        enabled,
        legacy_load,
        prompt_ids,
        stage="stage2",
        stage_label="Stage 2",
        warning_logger=warning_logger,
    )
