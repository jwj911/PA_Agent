"""Tests for stable Prompt identity rendering in the GUI debug panel."""

from __future__ import annotations

from pa_agent.ai.prompting import TEMPLATE_CATALOG, prompt_ids
from pa_agent.gui.prompt_files_panel import PromptFilesPanel


def test_panel_resolves_legacy_filename_to_display_name_and_id(qtbot) -> None:
    panel = PromptFilesPanel()
    qtbot.addWidget(panel)
    spec = TEMPLATE_CATALOG.spec(prompt_ids.MARKET_DIAGNOSIS)

    panel.set_stage1_files([spec.legacy_filename])

    item = panel._stage1_list.item(0)
    assert item.text() == f"1. {spec.display_name} [{spec.prompt_id}]"
    assert spec.source_path not in item.text()
    assert item.toolTip().splitlines() == [
        f"prompt_id: {spec.prompt_id}",
        f"source_path: {spec.source_path}",
        f"legacy_filename: {spec.legacy_filename}",
        f"version: {spec.version}",
    ]


def test_panel_accepts_prompt_ids_without_filename_identity(qtbot) -> None:
    panel = PromptFilesPanel()
    qtbot.addWidget(panel)
    prompt_id = prompt_ids.BULLISH_CHANNEL_STRATEGY
    spec = TEMPLATE_CATALOG.spec(prompt_id)

    panel.set_stage2_prompt_ids([prompt_id])

    item = panel._stage2_list.item(0)
    assert item.text() == f"1. {spec.display_name} [{prompt_id}]"
    assert f"source_path: {spec.source_path}" in item.toolTip()


def test_panel_preserves_unknown_legacy_value_as_unresolved(qtbot) -> None:
    panel = PromptFilesPanel()
    qtbot.addWidget(panel)

    panel.set_stage2_files(["private-strategy-path"])

    item = panel._stage2_list.item(0)
    assert item.text() == "1. private-strategy-path [unresolved]"
    assert item.toolTip() == ("legacy_filename: private-strategy-path\n" "status: unresolved")
