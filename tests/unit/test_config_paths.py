"""Tests for centralised path constants."""

from __future__ import annotations

from pa_agent.config import paths


def test_project_root_points_to_repository_root() -> None:
    assert paths.PROJECT_ROOT == paths.PA_AGENT_DIR
    assert paths.PROJECT_ROOT.name == "price_action_agent"
    assert paths.PROJECT_ROOT.resolve() == paths.PROJECT_ROOT


def test_runtime_directories_are_rooted_at_project_root() -> None:
    assert paths.PROMPT_DIR == paths.PROJECT_ROOT / "prompt_engineering"
    assert paths.RECORDS_PENDING_DIR == paths.PROJECT_ROOT / "records" / "pending"
    assert paths.EXPERIENCE_DIR == paths.PROJECT_ROOT / "experience"
    assert paths.CONFIG_DIR == paths.PROJECT_ROOT / "config"
    assert paths.LOGS_DIR == paths.PROJECT_ROOT / "logs"


def test_file_paths_are_derived_from_runtime_directories() -> None:
    assert paths.FEISHU_JSON_LEGACY_PATH == paths.CONFIG_DIR / "feishu.json"
    assert paths.SETTINGS_JSON_PATH == paths.CONFIG_DIR / "settings.json"
    assert paths.LOG_FILE_PATH == paths.LOGS_DIR / "pa_agent.log"
    assert paths.CRASH_LOG_PATH == paths.LOGS_DIR / "crash.log"
