"""Tests for the prompt strategy filename registry."""

from __future__ import annotations

from pa_agent.ai import prompt_assembler, router, strategy_files


def _registry_values() -> set[str]:
    return {
        value
        for name, value in vars(strategy_files).items()
        if name.isupper() and isinstance(value, str)
    }


def test_strategy_file_registry_values_are_unique_txt_names() -> None:
    names = [
        name
        for name, value in vars(strategy_files).items()
        if name.isupper() and isinstance(value, str)
    ]
    values = [getattr(strategy_files, name) for name in names]

    assert len(values) == len(set(values))
    assert all(value.endswith(".txt") for value in values)


def test_router_valid_files_are_derived_from_strategy_registry() -> None:
    registry = _registry_values()
    router_excluded = {
        strategy_files.BINARY_DECISION,
        strategy_files.BAR_CHECKLIST,
    }

    assert frozenset(registry - router_excluded) == router._ALL_VALID_FILES
    assert router._BULLISH_CHANNEL_FILES == [
        strategy_files.BULLISH_CHANNEL_ID,
        strategy_files.BULLISH_CHANNEL_STRATEGY,
    ]
    assert router._BEARISH_SPIKE_FILES == [
        strategy_files.BEARISH_SPIKE_ID,
        strategy_files.BEARISH_SPIKE_STRATEGY,
    ]


def test_prompt_assembler_file_lists_use_strategy_registry_values() -> None:
    registry = _registry_values()

    assert prompt_assembler.COMMON_SYSTEM_PROMPT_TXT_FILES is (
        prompt_assembler.COMMON_SYSTEM_STAGE2_TXT_FILES
    )
    assert set(prompt_assembler.COMMON_SYSTEM_STAGE1_TXT_FILES) <= registry
    assert set(prompt_assembler.COMMON_SYSTEM_STAGE2_TXT_FILES) <= registry
    assert set(prompt_assembler.STAGE1_TASK_PROMPT_TXT_FILES) <= registry
    assert set(prompt_assembler.STAGE2_BASE_PROMPT_TXT_FILES) <= registry
    assert set(prompt_assembler.STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES) <= registry


def test_prompt_assembler_stage1_list_preserves_common_then_task_order() -> None:
    assert prompt_assembler.stage1_prompt_txt_files() == [
        *prompt_assembler.COMMON_SYSTEM_STAGE1_TXT_FILES,
        *prompt_assembler.STAGE1_TASK_PROMPT_TXT_FILES,
    ]
