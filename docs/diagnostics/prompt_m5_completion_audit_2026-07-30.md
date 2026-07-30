# M5 Prompt 物理迁移完成审计报告

> 诊断 ID：`PA-M5-COMPLETE-001`
>
> 日期：2026-07-30
>
> 状态：M5 29/29 完成审计通过

## 审计范围

本报告审计 M5.0 Source Path 准备之后的全部物理迁移：

- 基线提交：`ac549d0a8c3483b38855f15265649090bd6de74b`；
- 最终实现提交：`a9ecb76141d5d4c7bc713e7f002dfebe54376116`；
- 运行时模板：29 个；
- 迁移批次：M5.1 Persona、M5.2 Binary Decision、M5.3 Stage 1/Base、M5.4 Router
  语义对、M5.5 Pattern/Context。

`prompt_engineering/_reference/` 是非运行时参考层，不计入 29 个 manifest 模板，也未参与
本轮物理迁移。

## 要求与权威证据

| 要求 | 权威证据 | 结论 |
|---|---|---|
| 29 个稳定 Prompt ID 保持唯一 | `TEMPLATE_MANIFEST` 与 `ALL_PROMPT_IDS` 均为 29，集合完全相等 | 通过 |
| 全部物理路径迁移为 `.prompt.md` | 29 个 manifest `source_path` 均以 `.prompt.md` 结尾且实体存在 | 通过 |
| 不保留重复 `.txt` 实体 | 顶层运行时目录为 29 个 `.prompt.md`、0 个 `.txt` | 通过 |
| `.txt` 兼容身份保持不变 | 29 个 `legacy_filename` 均以 `.txt` 结尾 | 通过 |
| 旧 API 与 ID API 内容等价 | 对全部 29 个模板逐项比较 `TemplateStore.load(legacy)` 与 `load_id(id)` | 通过 |
| 迁移不改变模板内容 | M5.0 基线的 29 个 legacy 路径 Git blob 与当前 29 个 `source_path` blob 逐 ID 相同 | 通过 |
| 迁移合同覆盖全部模板 | `MIGRATED_PROMPT_SOURCES` 为 29 项，ID/legacy/source 三元组与 manifest 完全相等 | 通过 |
| 路由与组装不变 | M5.4 五组语义对、M5.5 十组 pattern/context 路由与组装摘要迁移前后相同 | 通过 |
| M4 合同不回退 | 最终报告 SHA-256 为 `ce8b9555…2c79a`，offline/live/final gate 均为 `true` | 通过 |
| 本地质量门禁完整 | targeted 177 目标、完整非 live 回归、Ruff baseline、focused Ruff/Black 全部通过 | 通过 |
| Windows 支持矩阵通过 | M5.5 实现 run `30509955576` 的 Python 3.11/3.12 job 均为 `success` | 通过 |

## 全量内容证据

对 29 个模板使用 `prompt_id + Git blob OID` 构造的身份摘要为：

`6f96b2f9f9380ba3946865f5bbddcc9f8e3fc8e81019f3bb2f09a425b14dd54f`

该摘要中的每个 blob OID 都已逐项证明等于 M5.0 基线对应 legacy `.txt` 文件的 blob OID。
当前 `TemplateStore` 规范化正文以 `prompt_id + bytes + SHA-256` 构造的全量摘要为：

`565ca22d59cd83d92ef2bcd3020a73d12b3482da0b3a8174e4f3382df76202b3`

各批次 raw/规范化正文、路由与组装细节见：

- [`PA-M5-PERSONA-001`](./prompt_m5_persona_migration_2026-07-29.md)；
- [`PA-M5-BINARY-001`](./prompt_m5_binary_decision_migration_2026-07-29.md)；
- [`PA-M5-STAGE-BASE-001`](./prompt_m5_stage_base_migration_2026-07-29.md)；
- [`PA-M5-ROUTER-PAIRS-001`](./prompt_m5_router_pairs_migration_2026-07-30.md)；
- [`PA-M5-PATTERN-CONTEXT-001`](./prompt_m5_pattern_context_migration_2026-07-30.md)。

## M5.5 远端证据

- 实现提交：`a9ecb76`；
- GitHub Actions run：`30509955576`；
- Windows/Python 3.11 job `90767663880`：`success`；
- Windows/Python 3.12 job `90767663920`：`success`。

## 收口结论

M5 的 29 个运行时模板已全部完成 `.txt` 到 `.prompt.md` 的物理迁移。稳定 Prompt ID、
legacy filename、正文、路由、组装、记录兼容和 M4 合同均有直接证据证明保持不变；M5
完成定义满足。

兼容入口不随 M5 删除。`TemplateStore` legacy loader、filename 路由投影和旧记录字段继续受
`compatibility_policy.json` 约束；未满足版本、fallback 零命中和迁移报告条件前继续保留。

下一迭代只评估可选语义审查 Agent 的收益、边界和成本，不直接引入多 Agent，也不与 Prompt
正文优化或经验库权重调整混合提交。
