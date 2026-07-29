"""Tests for stable Prompt IDs and their physical-path catalog."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from pa_agent.ai import strategy_files as sf
from pa_agent.ai.prompting import (
    TEMPLATE_CATALOG,
    TEMPLATE_MANIFEST,
    PromptCatalog,
    PromptCatalogError,
    PromptId,
    TemplateSpec,
    TemplateStore,
    prompt_ids,
)


def _spec(
    prompt_id: str,
    source_path: str = "fixture.txt",
    *,
    legacy_filename: str | None = None,
    legacy_aliases: Sequence[str] = (),
    dependencies: Sequence[str] = (),
) -> TemplateSpec:
    return TemplateSpec(
        prompt_id=PromptId(prompt_id),
        source_path=source_path,
        legacy_filename=source_path if legacy_filename is None else legacy_filename,
        display_name="测试模板",
        stages=("stage1",),
        role="task",
        dependencies=tuple(PromptId(value) for value in dependencies),
        legacy_aliases=tuple(legacy_aliases),
    )


def test_runtime_catalog_covers_all_prompt_ids_and_legacy_filenames() -> None:
    expected_filenames = {
        value for name, value in vars(sf).items() if name.isupper() and isinstance(value, str)
    }

    assert len(TEMPLATE_MANIFEST) == 29
    assert len(prompt_ids.ALL_PROMPT_IDS) == len(set(prompt_ids.ALL_PROMPT_IDS)) == 29
    assert set(TEMPLATE_CATALOG.by_id) == set(prompt_ids.ALL_PROMPT_IDS)
    assert set(TEMPLATE_CATALOG.by_legacy_filename) == expected_filenames
    source_paths = {
        TEMPLATE_CATALOG.source_path(prompt_id) for prompt_id in prompt_ids.ALL_PROMPT_IDS
    }
    assert len(source_paths) == 29
    assert all(path.endswith((".txt", ".prompt.md")) for path in source_paths)
    assert all(TEMPLATE_CATALOG.display_name(prompt_id) for prompt_id in prompt_ids.ALL_PROMPT_IDS)


def test_catalog_separates_id_source_path_and_legacy_filename(tmp_path) -> None:
    source_path = "runtime/fixture.prompt.md"
    legacy_filename = "fixture.txt"
    alias = "old-fixture.txt"
    prompt_id = PromptId("test.fixture")
    template_path = tmp_path / "runtime" / "fixture.prompt.md"
    template_path.parent.mkdir()
    template_path.write_text("stable content", encoding="utf-8")
    spec = _spec(
        str(prompt_id),
        source_path,
        legacy_filename=legacy_filename,
        legacy_aliases=(alias,),
    )
    catalog = PromptCatalog((spec,))
    store = TemplateStore(tmp_path, manifest=(spec,))

    assert catalog.source_path(prompt_id) == source_path
    assert catalog.legacy_filename(prompt_id) == legacy_filename
    assert catalog.resolve_legacy_filename(legacy_filename) == prompt_id
    assert catalog.resolve_legacy_filename(alias) == prompt_id
    assert catalog.source_path_for_legacy_filename(legacy_filename) == source_path
    assert catalog.source_path_for_legacy_filename(alias) == source_path
    assert store.load_id(prompt_id) == "stable content"
    assert store.load(legacy_filename) == "stable content"
    assert store.load(alias) == "stable content"


@pytest.mark.parametrize(
    "prompt_id",
    [
        "",
        "PA.Persona",
        "pa-persona",
        "pa..persona",
        "pa.persona.v1!",
        "1.pa",
    ],
)
def test_catalog_rejects_invalid_prompt_ids(prompt_id: str) -> None:
    with pytest.raises(PromptCatalogError, match="Invalid prompt ID"):
        PromptCatalog((_spec(prompt_id),))


@pytest.mark.parametrize(
    "source_path",
    [
        "",
        "../escape.txt",
        "/absolute.txt",
        "C:/absolute.txt",
        r"nested\fixture.txt",
        "./fixture.txt",
        "nested//fixture.txt",
        "fixture.md",
        "fixture\x00.txt",
    ],
)
def test_catalog_rejects_unsafe_or_unregistered_source_paths(source_path: str) -> None:
    with pytest.raises(PromptCatalogError, match="Invalid prompt source path"):
        PromptCatalog(
            (
                _spec(
                    "test.fixture",
                    source_path,
                    legacy_filename="fixture.txt",
                ),
            )
        )


@pytest.mark.parametrize(
    "legacy_filename",
    [
        "",
        " nested.txt",
        "nested/fixture.txt",
        r"nested\fixture.txt",
        "C:fixture.txt",
        "fixture.prompt.md",
        "fixture\x00.txt",
    ],
)
def test_catalog_rejects_invalid_legacy_filenames(legacy_filename: str) -> None:
    with pytest.raises(PromptCatalogError, match="Invalid legacy prompt filename"):
        PromptCatalog(
            (
                _spec(
                    "test.fixture",
                    "fixture.txt",
                    legacy_filename=legacy_filename,
                ),
            )
        )


def test_catalog_rejects_duplicate_ids_paths_and_compatibility_names() -> None:
    with pytest.raises(PromptCatalogError, match="Duplicate prompt ID"):
        PromptCatalog(
            (
                _spec("test.fixture", "first.txt"),
                _spec("test.fixture", "second.txt"),
            )
        )

    with pytest.raises(PromptCatalogError, match="Duplicate prompt source path"):
        PromptCatalog(
            (
                _spec("test.first", "same.prompt.md", legacy_filename="first.txt"),
                _spec("test.second", "same.prompt.md", legacy_filename="second.txt"),
            )
        )

    with pytest.raises(PromptCatalogError, match="Duplicate legacy prompt filename"):
        PromptCatalog(
            (
                _spec("test.first", "first.txt", legacy_aliases=("shared.txt",)),
                _spec("test.second", "second.txt", legacy_aliases=("shared.txt",)),
            )
        )

    with pytest.raises(PromptCatalogError, match="conflicts with another legacy filename"):
        PromptCatalog(
            (
                _spec(
                    "test.first",
                    "runtime/first.prompt.md",
                    legacy_filename="shared.txt",
                ),
                _spec("test.second", "shared.txt", legacy_filename="second.txt"),
            )
        )


def test_catalog_rejects_unknown_dependencies_and_lookups() -> None:
    with pytest.raises(PromptCatalogError, match="Unknown dependencies"):
        PromptCatalog((_spec("test.fixture", dependencies=("test.missing",)),))

    with pytest.raises(PromptCatalogError, match="Unknown prompt ID"):
        TEMPLATE_CATALOG.spec(PromptId("pa.unknown"))
    with pytest.raises(PromptCatalogError, match="Unknown legacy prompt filename"):
        TEMPLATE_CATALOG.resolve_legacy_filename("unknown.txt")
    with pytest.raises(PromptCatalogError, match="Unknown legacy prompt filename"):
        TEMPLATE_CATALOG.source_path_for_legacy_filename("unknown.txt")
