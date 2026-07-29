# M5 Persona 模板迁移诊断报告

> 诊断 ID：`PA-M5-PERSONA-001`
>
> 日期：2026-07-29
>
> 状态：M5.1 本地全部质量门禁已通过，远端验收待完成

## 目标

M5.0 已消除 legacy filename 到物理路径的剩余耦合。M5.1 选择无模板依赖的
`pa.persona` 作为首个物理迁移样本，验证仅改变 manifest `source_path` 和文件路径时，
ID、兼容名称、正文和组装合同是否保持稳定。

## 变更

- 使用 `git mv` 将
  `prompt_engineering/提示词大纲_人设与思维方式.txt`
  移动为
  `prompt_engineering/提示词大纲_人设与思维方式.prompt.md`。
- `TemplateSpec.prompt_id` 保持 `pa.persona`。
- manifest 只把 `source_path` 更新为新 `.prompt.md` 路径。
- `legacy_filename` 继续固定为 `提示词大纲_人设与思维方式.txt`。
- 不保留同名 `.txt` 重复实体，不修改 Prompt 正文、版本、角色、阶段或依赖。

## 摘要证据

文件移动前后摘要逐项相同：

| 口径 | 字节数 | SHA-256 |
|---|---:|---|
| 磁盘原始字节 | 5,702 | `6a8b31bf6686a086092dfbe00b8a772aca5d8159ac39c74b1e3e983214553fb0` |
| `TemplateStore` UTF-8/LF 正文 | 5,604 | `1bb0b0ccc326ef6170624dc8d64f1dc0509abaa4f14538c14153c4b5b14f853b` |

原始字节与 `TemplateStore` 摘要不同是 Python 文本读取规范化 CRLF 的既有结果；迁移前后
两种口径分别保持一致，没有更新 golden 掩盖漂移。

固定 fixture 下，以 UTF-8、非 ASCII 转义关闭、紧凑 JSON 序列化后的消息列表计算摘要：

| 组装路径 | SHA-256 |
|---|---|
| Stage 1 | `d7ffebc4a68c431d42f4efe231a8af4937c5d4121b91e347d9c66617d9862577` |
| Stage 2 standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation standalone | `6aec0599a2f0ffdf2474d890b2d3af03a8ec9e5d6f3de345b5fd56f3465844fd` |
| Stage 2 continuation prefix | `9b5ba6b4a27d99f34444aea324e08074118396277ae11f4551ce3c4d0748a90c` |

四项摘要与迁移前冻结值完全相同。M4 评估器生成的 candidate Prompt metrics 也逐对象相等。

## 兼容结论

- `TemplateStore.load_id(pa.persona)` 按新 `source_path` 读取。
- legacy `TemplateStore.load("提示词大纲_人设与思维方式.txt")` 仍解析到同一 Prompt ID。
- assembler fallback 经 Catalog 投影读取新物理路径。
- route、record、Pipeline 和 GUI 的 legacy filename 投影保持 `.txt`。
- 新 `.prompt.md` 实体存在，旧 `.txt` 实体不存在。

## 验证

- Prompt Catalog、Store、Assembler、DecisionTree、记录兼容和 L2 集成聚焦回归：
  114 项通过。
- Persona 专属合同测试固定新 `source_path`、旧 `legacy_filename`、实体唯一性和旧文件缺失。
- CI targeted 177 个目标全部通过，coverage 56.83%。
- 完整 `not e2e and not live` 回归通过。
- Ruff 0.15.13 baseline 精确保持 3,712 条批准诊断。
- 293 个 focused Ruff 目标与展开后的 363 个 focused Black 文件通过。
- CI 清单自检、兼容政策、`git diff --check` 和 M4 最终报告逐字节复现通过。

## 后续

完整本地门禁与 GitHub Actions Python 3.11/3.12 双矩阵通过后，M5.1 才能收口。后续模板
必须继续按独立批次使用 `git mv`，不得把 Prompt 文本优化、多 Agent 或无关配置改动混入迁移。
