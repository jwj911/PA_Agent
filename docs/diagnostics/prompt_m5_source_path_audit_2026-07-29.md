# M5 Prompt Source Path 诊断报告

> 诊断 ID：`PA-M5-SOURCE-PATH-001`
>
> 日期：2026-07-29
>
> 状态：M5.0 修复、本地质量门禁与远端验收均已完成

## 问题

M4.3 已证明模型合同可进入 M5，但物理迁移前审计发现两条读取路径仍把不可变
`legacy_filename` 当作磁盘路径：

1. `PromptAssembler._load()` 的显式关闭/失败回退路径直接读取
   `prompt_dir / legacy_filename`。
2. `load_decision_tree()` 默认直接读取 `PROMPT_DIR / "二元决策.txt"`。

若直接把运行时模板 `git mv` 为 `.prompt.md` 并只修改 manifest `source_path`，上述路径会失效。
保留同名 `.txt` 复制文件又会违反 M5 “不得保留重复实体”的约束。

## 根因

核心 `TemplateStore` 已按 Prompt ID 解析 `source_path`，但两个兼容/辅助入口早于 ID 迁移，
仍绕过 Catalog。现有测试还断言 legacy `.txt` 名对应真实实体文件，因而没有覆盖
`legacy_filename != source_path` 的迁移状态。

## 修复

- `PromptCatalog` 新增 `source_path_for_legacy_filename()`，先精确解析兼容名称为 Prompt ID，
  再返回当前 `source_path`。
- `PromptAssembler._load()` 保留 legacy filename 输入和缓存键，但磁盘读取改走上述投影；
  未知 legacy 名称继续失败关闭并返回原兼容错误占位。
- `load_decision_tree()` 默认改用 `TemplateStore.load_id(pa.binary_decision)`；显式传入 `path`
  的测试/工具入口保持原行为，返回的 `source` 继续是不可变 legacy filename。
- 测试 fixture 按 Catalog 当前 `source_path` 创建文件；新增 `.prompt.md` 物理路径下
  legacy API 仍可读取、决策树默认经 Prompt ID 加载和未知 legacy 名称失败关闭的覆盖。

## 不变量

- 本切片不移动或修改任何运行时 Prompt 文件。
- 29 个 Prompt ID、`legacy_filename`、manifest 版本和模板正文 SHA-256 不变。
- shared system、Stage 1、Stage 2 standalone/continuation 的 assembled digest 不变。
- `route_strategy_files()`、记录字段和 GUI 仍输出 legacy `.txt` 投影。
- `_reference/*.md` 不进入运行时 manifest。

## 验证

- Prompt/Catalog/Store/Assembler/DecisionTree、GUI/记录、L2 兼容观察与 M4 报告可复现
  扩展回归：134 项通过。
- CI targeted 177 个目标与完整 `not e2e and not live` 回归通过，coverage 56.83%。
- Ruff 0.15.13 baseline：3,712 条已批准诊断，集合不变。
- 293 个 focused Ruff 目标、363 个 focused Black 文件与 `py_compile` 通过。
- 运行时读取检索只保留：
  - `TemplateStore` 按 `source_path` 读取；
  - assembler 经 Catalog 投影读取；
  - decision tree 显式调用方提供的 `path`。

- 实现提交：`ac549d0`。
- GitHub Actions run `30471807472`：Windows/Python 3.11 与 3.12 均为 `success`。

## 后续

M5 第一批只迁移一个低耦合模板组。每批必须使用 `git mv`，只修改对应 manifest
`source_path`，并重新验证模板内容 SHA-256、assembled Prompt digest、legacy API 和旧记录解析。

M5.1 已按该边界选择 `pa.persona` 单模板执行首批迁移；双口径正文摘要、四种组装摘要和
legacy filename 合同均保持不变。批次证据见
[`PA-M5-PERSONA-001`](./prompt_m5_persona_migration_2026-07-29.md)。
