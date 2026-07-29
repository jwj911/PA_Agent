# M5 Binary Decision 模板迁移诊断报告

> 诊断 ID：`PA-M5-BINARY-001`
>
> 日期：2026-07-29
>
> 状态：M5.2 本地全部质量门禁已通过，远端验收待完成

## 目标

M5.1 已用 `pa.persona` 证明单模板物理迁移路径可行。M5.2 选择高耦合共享系统模板
`pa.binary_decision` 单独迁移：它同时进入 Stage 1/Stage 2，是 5 个基础模板的 manifest
依赖，并由决策树 UI 独立解析。单独切片可将任何组装或解析偏差精确归因。

## 变更

- 使用 `git mv` 将 `prompt_engineering/二元决策.txt` 移动为
  `prompt_engineering/二元决策.prompt.md`。
- `TemplateSpec.prompt_id` 保持 `pa.binary_decision`。
- manifest 只把 `source_path` 更新为新 `.prompt.md` 路径。
- `legacy_filename` 继续固定为 `二元决策.txt`。
- 不保留同名 `.txt` 重复实体，不修改 Prompt 正文、版本、角色、阶段、输出合同或依赖。
- 迁移实体合同测试改为参数表，同时覆盖已迁移的 Persona 与 Binary Decision，供后续批次扩展。

## 摘要证据

文件移动前后摘要逐项相同：

| 口径 | 字节数 | SHA-256 |
|---|---:|---|
| 磁盘原始字节 | 43,260 | `7a67b6bee0425279fbdad1880f265c1feb796897418792f667a19d5c537c9c13` |
| `TemplateStore` UTF-8/LF 正文 | 42,164 | `723111253fa41d732e123943ab12dc94e2c459988978f2fad807699ff704525c` |

固定 fixture 下，以 UTF-8、非 ASCII 转义关闭、紧凑 JSON 序列化后的消息列表计算摘要：

| 组装路径 | SHA-256 |
|---|---|
| Stage 1 | `d7ffebc4a68c431d42f4efe231a8af4937c5d4121b91e347d9c66617d9862577` |
| Stage 2 standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation prefix | `9b5ba6b4a27d99f34444aea324e08074118396277ae11f4551ce3c4d0748a90c` |

M4 评估器生成的 candidate Prompt metrics 与最终退出报告均逐对象、逐字节相等，
`m4_exit_gate_passed=true`。

## 决策树合同

默认 `load_decision_tree()` 仍通过 `pa.binary_decision` 加载，并继续向兼容调用方返回
`source="二元决策.txt"`。迁移前后解析结果均为：

- 14 个 sections；
- 54 个索引节点；
- 规范 JSON SHA-256：
  `cb9b2f7982126bc4995394a8dc81067b0b5d2119a70c36f74aad3a47fb017c91`。

## 验证

- Prompt Catalog、Store、Assembler、DecisionTree、记录、GUI 和 L2 集成聚焦回归：
  118 项通过。
- 新 `.prompt.md` 实体存在，旧 `.txt` 实体不存在。
- CI targeted 177 个目标全部通过，coverage 56.83%。
- 完整 `not e2e and not live` 回归通过。
- Ruff 0.15.13 baseline 精确保持 3,712 条批准诊断。
- 293 个 focused Ruff 目标与展开后的 363 个 focused Black 文件通过。
- CI 清单自检、兼容政策、`git diff --check` 和 M4 最终报告逐字节复现通过。

## 后续

完整本地门禁与 GitHub Actions Python 3.11/3.12 双矩阵通过后，M5.2 才能收口。剩余
27 个模板继续按依赖边界分批迁移。
