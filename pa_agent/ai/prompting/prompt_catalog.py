"""Validated Prompt ID catalog independent of physical template paths."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING

from pa_agent.ai.prompting.prompt_ids import PromptId

if TYPE_CHECKING:
    from pa_agent.ai.prompting.template_manifest import StageName, TemplateSpec

_PROMPT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$")
_VALID_STAGES = frozenset(("stage1", "stage2"))
_VALID_ROLES = frozenset(("system", "task", "base", "strategy"))


class PromptCatalogError(ValueError):
    """Raised when Prompt ID metadata or a catalog lookup is invalid."""


class PromptCatalog:
    """Index immutable template metadata by ID and legacy filename."""

    def __init__(self, manifest: Sequence[TemplateSpec]) -> None:
        self._manifest = tuple(manifest)
        by_id: dict[PromptId, TemplateSpec] = {}
        by_legacy_filename: dict[str, TemplateSpec] = {}
        source_path_owners: dict[str, PromptId] = {}
        compatibility_name_owners: dict[str, PromptId] = {}

        for spec in self._manifest:
            prompt_id = PromptId(str(spec.prompt_id))
            source_path = str(spec.source_path)
            legacy_filename = str(spec.legacy_filename)

            self._validate_prompt_id(prompt_id)
            self._validate_source_path(source_path)
            self._validate_legacy_filename(legacy_filename)
            self._validate_spec_metadata(spec)

            if prompt_id in by_id:
                raise PromptCatalogError(f"Duplicate prompt ID: {prompt_id}")
            if source_path in source_path_owners:
                raise PromptCatalogError(f"Duplicate prompt source path: {source_path}")

            by_id[prompt_id] = spec
            source_path_owners[source_path] = prompt_id
            self._register_compatibility_name(
                legacy_filename,
                prompt_id,
                spec,
                by_legacy_filename,
                compatibility_name_owners,
            )
            for alias in spec.legacy_aliases:
                alias_value = str(alias)
                self._validate_legacy_filename(alias_value)
                self._register_compatibility_name(
                    alias_value,
                    prompt_id,
                    spec,
                    by_legacy_filename,
                    compatibility_name_owners,
                )

        for source_path, prompt_id in source_path_owners.items():
            compatibility_owner = compatibility_name_owners.get(source_path)
            if compatibility_owner is not None and compatibility_owner != prompt_id:
                raise PromptCatalogError(
                    f"Prompt source path conflicts with another legacy filename: {source_path}"
                )

        for spec in self._manifest:
            missing_dependencies = sorted(
                str(dependency)
                for dependency in spec.dependencies
                if PromptId(str(dependency)) not in by_id
            )
            if missing_dependencies:
                raise PromptCatalogError(
                    f"Unknown dependencies for prompt {spec.prompt_id}: {missing_dependencies}"
                )

        self._by_id: Mapping[PromptId, TemplateSpec] = MappingProxyType(by_id)
        self._by_legacy_filename: Mapping[str, TemplateSpec] = MappingProxyType(by_legacy_filename)

    @property
    def manifest(self) -> tuple[TemplateSpec, ...]:
        """Return the manifest in its declared order."""
        return self._manifest

    @property
    def by_id(self) -> Mapping[PromptId, TemplateSpec]:
        """Return the read-only Prompt ID index."""
        return self._by_id

    @property
    def by_legacy_filename(self) -> Mapping[str, TemplateSpec]:
        """Return the read-only current-name and legacy-alias index."""
        return self._by_legacy_filename

    def spec(self, prompt_id: PromptId) -> TemplateSpec:
        """Return metadata for a stable Prompt ID."""
        normalized = PromptId(str(prompt_id))
        try:
            return self._by_id[normalized]
        except KeyError as exc:
            raise PromptCatalogError(f"Unknown prompt ID: {prompt_id}") from exc

    def source_path(self, prompt_id: PromptId) -> str:
        """Return the physical source path for a Prompt ID."""
        return self.spec(prompt_id).source_path

    def source_path_for_legacy_filename(self, filename: str) -> str:
        """Resolve a compatibility filename to its current physical path."""
        return self.source_path(self.resolve_legacy_filename(filename))

    def legacy_filename(self, prompt_id: PromptId) -> str:
        """Return the immutable legacy filename projection for a Prompt ID."""
        return self.spec(prompt_id).legacy_filename

    def legacy_filenames(self, prompt_ids: Sequence[PromptId]) -> tuple[str, ...]:
        """Project Prompt IDs to immutable legacy filenames in caller order."""
        return tuple(self.legacy_filename(prompt_id) for prompt_id in prompt_ids)

    def display_name(self, prompt_id: PromptId) -> str:
        """Return the user-facing display name for a Prompt ID."""
        return self.spec(prompt_id).display_name

    def resolve_legacy_filename(self, filename: str) -> PromptId:
        """Resolve an exact current legacy filename or registered alias."""
        try:
            return self._by_legacy_filename[str(filename)].prompt_id
        except KeyError as exc:
            raise PromptCatalogError(f"Unknown legacy prompt filename: {filename}") from exc

    def prompt_ids_for_stage(self, stage: StageName) -> tuple[PromptId, ...]:
        """Return manifest-ordered Prompt IDs assigned to a stage."""
        if stage not in _VALID_STAGES:
            raise PromptCatalogError(f"Unknown template stage: {stage!r}")
        return tuple(spec.prompt_id for spec in self._manifest if stage in spec.stages)

    @staticmethod
    def _validate_prompt_id(prompt_id: PromptId) -> None:
        value = str(prompt_id)
        if not _PROMPT_ID_PATTERN.fullmatch(value):
            raise PromptCatalogError(f"Invalid prompt ID: {value!r}")

    @staticmethod
    def _validate_source_path(source_path: str) -> None:
        path = PurePosixPath(source_path)
        if (
            not source_path
            or source_path != source_path.strip()
            or "\\" in source_path
            or ":" in source_path
            or "\x00" in source_path
            or path.is_absolute()
            or path.as_posix() != source_path
            or any(part in ("", ".", "..") for part in path.parts)
            or not (source_path.endswith(".txt") or source_path.endswith(".prompt.md"))
        ):
            raise PromptCatalogError(f"Invalid prompt source path: {source_path!r}")

    @staticmethod
    def _validate_legacy_filename(filename: str) -> None:
        path = PurePosixPath(filename)
        if (
            not filename
            or filename != filename.strip()
            or "\\" in filename
            or ":" in filename
            or "\x00" in filename
            or path.name != filename
            or path.suffix.lower() != ".txt"
        ):
            raise PromptCatalogError(f"Invalid legacy prompt filename: {filename!r}")

    @staticmethod
    def _validate_spec_metadata(spec: TemplateSpec) -> None:
        if not spec.display_name or spec.display_name != spec.display_name.strip():
            raise PromptCatalogError(
                f"Invalid display name for prompt {spec.prompt_id}: {spec.display_name!r}"
            )
        if not spec.stages or any(stage not in _VALID_STAGES for stage in spec.stages):
            raise PromptCatalogError(f"Invalid stages for prompt {spec.prompt_id}: {spec.stages!r}")
        if spec.role not in _VALID_ROLES:
            raise PromptCatalogError(f"Invalid role for prompt {spec.prompt_id}: {spec.role!r}")
        if not spec.version:
            raise PromptCatalogError(f"Missing version for prompt {spec.prompt_id}")

    @staticmethod
    def _register_compatibility_name(
        filename: str,
        prompt_id: PromptId,
        spec: TemplateSpec,
        by_legacy_filename: dict[str, TemplateSpec],
        owners: dict[str, PromptId],
    ) -> None:
        if filename in owners:
            raise PromptCatalogError(f"Duplicate legacy prompt filename or alias: {filename}")
        owners[filename] = prompt_id
        by_legacy_filename[filename] = spec


__all__ = ["PromptCatalog", "PromptCatalogError"]
