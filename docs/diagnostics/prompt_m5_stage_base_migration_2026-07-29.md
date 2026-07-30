# M5 Stage 1/Base 模板迁移诊断报告

> 诊断 ID：`PA-M5-STAGE-BASE-001`
>
> 日期：2026-07-29
>
> 状态：M5.3 本地全部质量门禁已通过，远端验收待完成

## 目标

M5.2 已单独迁移共享依赖 `pa.binary_decision`。M5.3 在该依赖稳定后迁移直接依赖它的
Stage 1/Base 模板：一个 Stage 1 task、一个跨 Stage base 和三个 Stage 2 base。五者共享
组装验证面，且不包含 router 动态策略对，适合作为一个原子批次。

## 变更

本批使用 `git mv` 将以下物理文件迁移为同名 `.prompt.md`：

- `pa.market_diagnosis`；
- `pa.kline_signal`；
- `pa.bar_checklist`；
- `pa.stop_target_position`；
- `pa.measured_move`。

manifest 只更新对应 `source_path`。稳定 Prompt ID、不可变 `.txt` `legacy_filename`、
manifest `v2`、阶段、角色、输出合同和 `pa.binary_decision` 依赖保持不变；不保留重复
`.txt` 实体。迁移合同参数表同步扩展到全部 7 个已迁移模板。

## 摘要证据

文件移动前后摘要逐项相同：

| Prompt ID | raw bytes / SHA-256 | `TemplateStore` bytes / SHA-256 |
|---|---|---|
| `pa.market_diagnosis` | 86,801 / `7a2d20fd88416969ccc5466606382484f619a67a944c9e6ea52edcc79f25f435` | 85,359 / `d2144886a1b17a779df822fe0ce22075366104c733a67570999e5b15e3ff6147` |
| `pa.kline_signal` | 21,437 / `a24f8c950174d154010bc30ee06dbd95faa61beda6a0e5c16ca9516d428f7eb2` | 20,995 / `9b61ac25b6d6d235ae282164d4e9e3eefcf6b46cd20bdb972d8bc4a6fb40728e` |
| `pa.bar_checklist` | 2,364 / `b6240348455b62b3c3656551d0f05ba2f99910e958190f8d24ecbbd07ccaf3d6` | 2,304 / `4e867202df9cba4dcb5a74a6c122bb112880534f9cfeeb24e6ca25df8ab996ea` |
| `pa.stop_target_position` | 4,068 / `8fa680896c5555452c4b34d102e1b979b3de196f212f71e8845f98b791d659a9` | 3,979 / `e953072fccb182bd391511132fa924ca5b2c5711292051348446df1da7b2a805` |
| `pa.measured_move` | 5,479 / `70ce6479d41a3e47c7d89a9ce619d19b2f62baa00950fb407ed6573c967f6779` | 5,371 / `07dbc646c2764230f580e91473ce5e7721283f0cc04366491500cef99ccc4f35` |

## 组装合同

四种组装摘要与迁移前冻结值逐项相同：

| 组装路径 | SHA-256 |
|---|---|
| Stage 1 | `d7ffebc4a68c431d42f4efe231a8af4937c5d4121b91e347d9c66617d9862577` |
| Stage 2 standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation prefix | `9b5ba6b4a27d99f34444aea324e08074118396277ae11f4551ce3c4d0748a90c` |

M4 最终退出报告 SHA-256 保持
`ce8b9555c8b947cce70046f415e3715f7db09d8f759eb4db808d440cc0e2c79a`，
`m4_exit_gate_passed=true`。

## 验证

- Prompt Catalog、Store、Assembler、DecisionTree、记录、GUI 和 L2 集成聚焦回归：
  123 项通过。
- 五个新 `.prompt.md` 实体存在，对应旧 `.txt` 实体均不存在。
- CI targeted 177 个目标全部通过，coverage 56.83%。
- 完整 `not e2e and not live` 回归通过。
- Ruff 0.15.13 baseline 精确保持 3,712 条批准诊断。
- 293 个 focused Ruff 目标与展开后的 363 个 focused Black 文件通过。
- CI 清单自检、兼容政策、`git diff --check` 和 M4 最终报告逐字节复现通过。

## 后续

完整本地门禁与 GitHub Actions Python 3.11/3.12 双矩阵通过后，M5.3 才能收口。剩余
22 个模板按 router 语义对和独立 pattern 组继续分批迁移。
