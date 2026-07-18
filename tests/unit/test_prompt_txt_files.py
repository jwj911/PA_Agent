"""Tests for stage prompt .txt file list helpers."""

from __future__ import annotations

from pathlib import Path

from pa_agent.ai import strategy_files as sf
from pa_agent.ai.prompt_assembler import (
    COMMON_SYSTEM_STAGE1_TXT_FILES,
    COMMON_SYSTEM_STAGE2_TXT_FILES,
    STAGE1_TASK_PROMPT_TXT_FILES,
    STAGE2_BASE_PROMPT_TXT_FILES,
    STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES,
    stage1_prompt_txt_files,
    stage2_prompt_txt_files,
    stage2_user_task_txt_files,
)

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt_engineering"
DEPRECATED_STAGE1_GATE_FILE = "二元决策_闸门.txt"


def _strategy_registry_values() -> set[str]:
    return {
        value
        for name, value in vars(sf).items()
        if name.isupper() and isinstance(value, str)
    }


def test_stage1_txt_files() -> None:
    files = stage1_prompt_txt_files()
    assert files == [*COMMON_SYSTEM_STAGE1_TXT_FILES, *STAGE1_TASK_PROMPT_TXT_FILES]
    # Stage 1 now uses the full binary tree (same as Stage 2) for prefix caching
    assert "二元决策.txt" in files
    assert DEPRECATED_STAGE1_GATE_FILE not in files
    assert "文件13-窄通道与宽通道策略.txt" not in files


def test_stage_prompt_file_lists_match_audited_order() -> None:
    assert COMMON_SYSTEM_STAGE1_TXT_FILES == (
        "提示词大纲_人设与思维方式.txt",
        "二元决策.txt",
    )
    assert STAGE1_TASK_PROMPT_TXT_FILES == (
        "市场诊断框架.txt",
        "文件16-K线信号识别.txt",
    )
    assert COMMON_SYSTEM_STAGE2_TXT_FILES == (
        "提示词大纲_人设与思维方式.txt",
        "二元决策.txt",
    )
    assert STAGE2_BASE_PROMPT_TXT_FILES == (
        "逐棒分析检查单.txt",
        "文件16-K线信号识别.txt",
        "文件17-止损和止盈与仓位管理.txt",
        "文件23-MeasuredMove与结构目标.txt",
    )

    routed = ["极速上涨分析识别.txt", "极速上涨交易策略.txt"]
    assert stage2_prompt_txt_files(routed, direction="bullish") == [
        *COMMON_SYSTEM_STAGE2_TXT_FILES,
        *routed,
        *STAGE2_BASE_PROMPT_TXT_FILES,
    ]


def test_prompt_file_helpers_reference_existing_real_txt_files() -> None:
    helper_files = {
        *stage1_prompt_txt_files(),
        *stage2_prompt_txt_files(
            list(STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES),
            load_full_strategy_library=True,
        ),
        *stage2_user_task_txt_files(
            ["极速上涨分析识别.txt", "极速上涨交易策略.txt"],
            direction="bullish",
        ),
    }

    assert DEPRECATED_STAGE1_GATE_FILE not in helper_files
    assert all(name.endswith(".txt") for name in helper_files)

    expected_files = helper_files | _strategy_registry_values()
    missing = sorted(name for name in expected_files if not (PROMPT_DIR / name).is_file())
    assert missing == []


def test_stage2_routed_only_bullish() -> None:
    routed = ["震荡区间交易策略.txt", "上涨通道分析识别.txt"]
    files = stage2_user_task_txt_files(routed, direction="bullish")
    assert "上涨通道分析识别.txt" in files
    assert "下跌通道分析识别.txt" not in files
    assert "下跌通道交易策略.txt" not in files
    assert "文件17-止损和止盈与仓位管理.txt" in files
    for name in STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES:
        if name.startswith("下跌") or name.startswith("极速下跌"):
            assert name not in files


def test_stage2_full_library_flag() -> None:
    routed = ["震荡区间交易策略.txt"]
    files = stage2_user_task_txt_files(
        routed,
        direction="bullish",
        load_full_strategy_library=True,
    )
    for name in STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES:
        assert name in files


def test_stage2_txt_files_order() -> None:
    routed = ["震荡区间交易策略.txt", "震荡区间分析识别.txt"]
    files = stage2_prompt_txt_files(routed, direction="neutral")
    expected_user = stage2_user_task_txt_files(routed, direction="neutral")
    assert files == [*COMMON_SYSTEM_STAGE2_TXT_FILES, *expected_user]
    assert files[:2] == list(COMMON_SYSTEM_STAGE2_TXT_FILES)
    assert files[-4:] == list(STAGE2_BASE_PROMPT_TXT_FILES)
    assert routed[0] in files
