"""Strict UTF-8 storage for manifest-backed prompt templates."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

from pa_agent.ai.prompting.template_manifest import (
    TEMPLATE_MANIFEST,
    StageName,
    TemplateSpec,
    validate_template_manifest,
)


class TemplateStoreError(RuntimeError):
    """Raised when a manifest-backed template cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class TemplateSnapshot:
    """Byte-level identity information for one UTF-8 template."""

    name: str
    version: str
    byte_length: int
    sha256: str


class TemplateStore:
    """Load only known prompt templates and cache their decoded UTF-8 text.

    The store deliberately does not render templates or execute code. A caller
    must opt into a manifest-backed name, and all file errors are raised
    instead of being replaced with an incomplete prompt.
    """

    def __init__(
        self,
        root: Path,
        *,
        manifest: Sequence[TemplateSpec] = TEMPLATE_MANIFEST,
    ) -> None:
        self._root = root
        self._manifest = tuple(manifest)
        self._specs = validate_template_manifest(self._manifest)
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    @property
    def root(self) -> Path:
        """Return the template root directory."""
        return self._root

    @property
    def manifest(self) -> tuple[TemplateSpec, ...]:
        """Return the immutable manifest used by this store."""
        return self._manifest

    def spec(self, name: str) -> TemplateSpec:
        """Return metadata for *name* or raise a strict store error."""
        try:
            return self._specs[name]
        except KeyError as exc:
            raise TemplateStoreError(f"Unknown prompt template: {name}") from exc

    def load(self, name: str, *, stage: StageName | None = None) -> str:
        """Load one manifest-backed UTF-8 template."""
        spec = self.spec(name)
        self._validate_stage(spec, stage)
        with self._lock:
            cached = self._cache.get(name)
        if cached is not None:
            return cached

        path = self._root / spec.name
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise TemplateStoreError(f"Prompt template not found: {path}") from exc
        except UnicodeDecodeError as exc:
            raise TemplateStoreError(f"Prompt template is not valid UTF-8: {path}") from exc
        except OSError as exc:
            raise TemplateStoreError(f"Prompt template cannot be read: {path}: {exc}") from exc
        if not text:
            raise TemplateStoreError(f"Prompt template is empty: {path}")

        with self._lock:
            existing = self._cache.get(name)
            if existing is not None:
                return existing
            self._cache[name] = text
        return text

    def load_many(
        self,
        names: Sequence[str],
        *,
        stage: StageName | None = None,
    ) -> tuple[str, ...]:
        """Load templates in exactly the caller-provided order."""
        return tuple(self.load(name, stage=stage) for name in names)

    def render(
        self,
        name: str,
        context: Mapping[str, Any] | Any,
        *,
        stage: StageName | None = None,
    ) -> str:
        """Render a template with strict, non-executable variable substitution.

        Templates use standard-library ``$name`` / ``${name}`` placeholders.
        Missing variables and malformed placeholders fail explicitly instead of
        producing a partial prompt.
        """
        text = self.load(name, stage=stage)
        values = context.to_dict() if hasattr(context, "to_dict") else context
        if not isinstance(values, Mapping):
            raise TemplateStoreError("Template render context must be a mapping")
        try:
            return Template(text).substitute({str(key): value for key, value in values.items()})
        except KeyError as exc:
            raise TemplateStoreError(
                f"Missing template variable {exc.args[0]!r} for {name}"
            ) from exc
        except ValueError as exc:
            raise TemplateStoreError(f"Invalid template syntax for {name}: {exc}") from exc

    def render_many(
        self,
        names: Sequence[str],
        context: Mapping[str, Any] | Any,
        *,
        stage: StageName | None = None,
    ) -> tuple[str, ...]:
        """Render templates in caller order using one explicit context."""
        return tuple(self.render(name, context, stage=stage) for name in names)

    def snapshot(self, name: str, *, stage: StageName | None = None) -> TemplateSnapshot:
        """Return the UTF-8 byte digest of one loaded template."""
        text = self.load(name, stage=stage)
        encoded = text.encode("utf-8")
        return TemplateSnapshot(
            name=name,
            version=self.spec(name).version,
            byte_length=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
        )

    def snapshots(
        self,
        names: Sequence[str],
        *,
        stage: StageName | None = None,
    ) -> tuple[TemplateSnapshot, ...]:
        """Return ordered byte snapshots for *names*."""
        return tuple(self.snapshot(name, stage=stage) for name in names)

    def clear_cache(self, name: str | None = None) -> None:
        """Clear one cached template or the entire store cache."""
        with self._lock:
            if name is None:
                self._cache.clear()
                return
            self.spec(name)
            self._cache.pop(name, None)

    @staticmethod
    def _validate_stage(spec: TemplateSpec, stage: StageName | None) -> None:
        if stage is not None and stage not in spec.stages:
            raise TemplateStoreError(f"Template {spec.name} is not assigned to stage {stage!r}")
