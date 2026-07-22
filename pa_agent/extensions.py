"""Installed extension discovery for registry-backed adapters.

Extensions are opt-in package entry points.  Discovery never scans arbitrary
directories and never owns provider synchronization, persistence, or network
health checks.  Each entry point must load a callable registrar accepting the
target registry.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Protocol

from pa_agent.ai.provider_registry import AIClientRegistry
from pa_agent.data.registry import DataSourceRegistry

DATA_SOURCE_ENTRY_POINT_GROUP = "pa_agent.data_sources"
AI_CLIENT_ENTRY_POINT_GROUP = "pa_agent.ai_clients"

logger = logging.getLogger(__name__)


class RegistryRegistrar(Protocol):
    """Callable contract implemented by one installed registry extension."""

    def __call__(self, registry: DataSourceRegistry | AIClientRegistry) -> None:
        """Register one or more specs into the supplied registry."""


@dataclass(frozen=True, slots=True)
class ExtensionLoadResult:
    """Safe outcome metadata for one discovered extension."""

    group: str
    name: str
    loaded: bool
    error_type: str | None = None


def discover_data_source_extensions(
    registry: DataSourceRegistry,
    *,
    entry_points_fn: Callable[..., Any] = entry_points,
    warning_logger: logging.Logger | None = None,
) -> tuple[ExtensionLoadResult, ...]:
    """Load installed data-source registrars into *registry*."""
    return discover_registry_extensions(
        registry,
        group=DATA_SOURCE_ENTRY_POINT_GROUP,
        entry_points_fn=entry_points_fn,
        warning_logger=warning_logger,
    )


def discover_ai_client_extensions(
    registry: AIClientRegistry,
    *,
    entry_points_fn: Callable[..., Any] = entry_points,
    warning_logger: logging.Logger | None = None,
) -> tuple[ExtensionLoadResult, ...]:
    """Load installed AI-client registrars into *registry*."""
    return discover_registry_extensions(
        registry,
        group=AI_CLIENT_ENTRY_POINT_GROUP,
        entry_points_fn=entry_points_fn,
        warning_logger=warning_logger,
    )


def discover_registry_extensions(
    registry: DataSourceRegistry | AIClientRegistry,
    *,
    group: str,
    entry_points_fn: Callable[..., Any] = entry_points,
    warning_logger: logging.Logger | None = None,
) -> tuple[ExtensionLoadResult, ...]:
    """Discover and invoke entry-point registrars without holding registry locks.

    Discovery and plugin execution happen outside registry internals.  A
    broken optional extension is isolated and cannot prevent built-in
    providers or data sources from loading.
    """
    log = warning_logger or logger
    try:
        discovered = _select_entry_points(entry_points_fn, group)
    except Exception as exc:
        log.warning(
            "Registry extension discovery failed group=%s error_type=%s",
            _safe_label(group),
            type(exc).__name__,
        )
        return ()

    results: list[ExtensionLoadResult] = []
    for extension in sorted(discovered, key=_entry_point_sort_key):
        name = _safe_label(getattr(extension, "name", "unknown"))
        try:
            registrar = extension.load()
            if not callable(registrar):
                raise TypeError("entry point must load a callable registrar")
            registrar(registry)
        except Exception as exc:
            log.warning(
                "Registry extension load failed group=%s name=%s error_type=%s",
                _safe_label(group),
                name,
                type(exc).__name__,
            )
            results.append(
                ExtensionLoadResult(
                    group=group,
                    name=name,
                    loaded=False,
                    error_type=type(exc).__name__,
                )
            )
        else:
            log.info(
                "Registry extension loaded group=%s name=%s",
                _safe_label(group),
                name,
            )
            results.append(ExtensionLoadResult(group=group, name=name, loaded=True))
    return tuple(results)


def _select_entry_points(
    entry_points_fn: Callable[..., Any],
    group: str,
) -> tuple[EntryPoint, ...]:
    """Normalize supported ``importlib.metadata`` entry-point APIs."""
    selected = entry_points_fn(group=group)
    if hasattr(selected, "select"):
        selected = selected.select(group=group)
    return tuple(selected)


def _entry_point_sort_key(extension: EntryPoint) -> tuple[str, str]:
    return (
        _safe_label(getattr(extension, "name", "unknown")),
        _safe_label(getattr(extension, "value", "")),
    )


def _safe_label(value: Any) -> str:
    """Keep diagnostic labels bounded and free of newline/control characters."""
    text = str(value or "").replace("\r", "?").replace("\n", "?")
    return text[:120] or "unknown"


__all__ = [
    "AI_CLIENT_ENTRY_POINT_GROUP",
    "DATA_SOURCE_ENTRY_POINT_GROUP",
    "ExtensionLoadResult",
    "RegistryRegistrar",
    "discover_ai_client_extensions",
    "discover_data_source_extensions",
    "discover_registry_extensions",
]
