"""Sidebar panel for stable Prompt identities used by the latest analysis."""

from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pa_agent.ai.prompting import TEMPLATE_CATALOG, PromptCatalogError, PromptId


def _prompt_display(prompt_id: PromptId) -> tuple[str, str]:
    spec = TEMPLATE_CATALOG.spec(prompt_id)
    return (
        f"{spec.display_name} [{spec.prompt_id}]",
        "\n".join(
            (
                f"prompt_id: {spec.prompt_id}",
                f"source_path: {spec.source_path}",
                f"legacy_filename: {spec.legacy_filename}",
                f"version: {spec.version}",
            )
        ),
    )


def _prompt_displays_from_ids(prompt_ids: Sequence[PromptId]) -> list[tuple[str, str]]:
    return [_prompt_display(PromptId(str(prompt_id))) for prompt_id in prompt_ids]


def _prompt_displays_from_legacy(filenames: Sequence[str]) -> list[tuple[str, str]]:
    displays: list[tuple[str, str]] = []
    for filename in filenames:
        legacy_filename = str(filename)
        try:
            prompt_id = TEMPLATE_CATALOG.resolve_legacy_filename(legacy_filename)
        except PromptCatalogError:
            displays.append(
                (
                    f"{legacy_filename} [unresolved]",
                    f"legacy_filename: {legacy_filename}\nstatus: unresolved",
                )
            )
            continue
        displays.append(_prompt_display(prompt_id))
    return displays


def _fill_list(
    widget: QListWidget,
    displays: Sequence[tuple[str, str]],
    *,
    empty_hint: str,
) -> None:
    widget.clear()
    if not displays:
        item = QListWidgetItem(empty_hint)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        widget.addItem(item)
        return
    for i, (text, tooltip) in enumerate(displays, 1):
        item = QListWidgetItem(f"{i}. {text}")
        item.setToolTip(tooltip)
        widget.addItem(item)


class PromptFilesPanel(QWidget):
    """Show ordered Prompt display names and stable IDs for the latest analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        hint = QLabel(
            "本次分析使用的 Prompt 模板（显示名称 + 稳定 ID；悬停查看存储路径）"  # noqa: RUF001
        )
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        s1_title = QLabel("阶段一 · 市场诊断")
        s1_title.setStyleSheet("font-weight: bold; color: #a371f7;")
        layout.addWidget(s1_title)

        self._stage1_list = QListWidget()
        self._stage1_list.setObjectName("promptFileList")
        layout.addWidget(self._stage1_list, stretch=1)

        s2_title = QLabel("阶段二 · 交易决策")
        s2_title.setStyleSheet("font-weight: bold; color: #58a6ff;")
        layout.addWidget(s2_title)

        self._stage2_list = QListWidget()
        self._stage2_list.setObjectName("promptFileList")
        layout.addWidget(self._stage2_list, stretch=1)

        self._extra_label = QLabel("")
        self._extra_label.setObjectName("mutedLabel")
        self._extra_label.setWordWrap(True)
        layout.addWidget(self._extra_label)

        self.clear()

    def set_stage1_files(self, files: list[str]) -> None:
        _fill_list(
            self._stage1_list,
            _prompt_displays_from_legacy(files),
            empty_hint="（尚未开始阶段一）",  # noqa: RUF001
        )

    def set_stage2_files(self, files: list[str]) -> None:
        _fill_list(
            self._stage2_list,
            _prompt_displays_from_legacy(files),
            empty_hint="（阶段二尚未开始）",  # noqa: RUF001
        )

    def set_stage1_prompt_ids(self, prompt_ids: Sequence[PromptId]) -> None:
        _fill_list(
            self._stage1_list,
            _prompt_displays_from_ids(prompt_ids),
            empty_hint="（尚未开始阶段一）",  # noqa: RUF001
        )

    def set_stage2_prompt_ids(self, prompt_ids: Sequence[PromptId]) -> None:
        _fill_list(
            self._stage2_list,
            _prompt_displays_from_ids(prompt_ids),
            empty_hint="（阶段二尚未开始）",  # noqa: RUF001
        )

    def set_extras(
        self,
        *,
        stage1_builtin: bool = True,
        stage2_builtin: bool = False,
        experience_count: int = 0,
    ) -> None:
        parts: list[str] = []
        if stage1_builtin:
            parts.append("阶段一另含内置 JSON 输出格式说明（非 Prompt 模板）")  # noqa: RUF001
        if stage2_builtin:
            parts.append("阶段二另含内置 JSON 决策契约（非 Prompt 模板）")  # noqa: RUF001
        if experience_count > 0:
            parts.append(
                f"阶段二另注入经验库 {experience_count} 条（非 Prompt 模板）"  # noqa: RUF001
            )
        self._extra_label.setText(" · ".join(parts))

    def clear(self) -> None:
        self.set_stage1_files([])
        self.set_stage2_files([])
        self.set_extras(stage1_builtin=False, stage2_builtin=False, experience_count=0)

    def set_latest_run(
        self,
        stage1_files: list[str],
        stage2_files: list[str],
        *,
        experience_count: int = 0,
    ) -> None:
        self.set_stage1_files(stage1_files)
        self.set_stage2_files(stage2_files)
        self.set_extras(
            stage1_builtin=bool(stage1_files),
            stage2_builtin=bool(stage2_files),
            experience_count=experience_count,
        )

    def set_latest_run_prompt_ids(
        self,
        stage1_prompt_ids: Sequence[PromptId],
        stage2_prompt_ids: Sequence[PromptId],
        *,
        experience_count: int = 0,
    ) -> None:
        self.set_stage1_prompt_ids(stage1_prompt_ids)
        self.set_stage2_prompt_ids(stage2_prompt_ids)
        self.set_extras(
            stage1_builtin=bool(stage1_prompt_ids),
            stage2_builtin=bool(stage2_prompt_ids),
            experience_count=experience_count,
        )
