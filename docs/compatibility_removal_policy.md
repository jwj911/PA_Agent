# L1/L2 兼容入口下线策略

本文定义 L1 legacy registrar 与 L2 legacy Prompt loader 的保留、弃用和删除门禁。当前项目版本
为 `0.1.0`，没有发布 tag；固定 fixture 观察通过不等于可以立即删除兼容入口。

机器可读事实位于 `config/compatibility_policy.json`，CI 执行
`scripts/check_compatibility_policy.py`。文档与策略文件冲突时，先修正文档和策略，再单独推进
版本/兼容迁移，不允许直接删除源码绕过门禁。

## 1. 状态机

每个兼容 surface 只能处于：

- `retain`：继续支持，不得设置 `deprecated_since`；CI 检查兼容源码和观察测试仍存在。
- `deprecated`：仍继续支持；必须设置达到最低弃用版本的 `deprecated_since`，并在用户/扩展
  文档中给出迁移方式。
- `remove`：允许删除兼容源码；必须同时满足最早移除版本、弃用发布 tag 和全部证据文件。

当前两个 surface 都是 `retain`：

| Surface | 当前状态 | 最低弃用版本 | 最早移除版本 |
|---|---|---:|---:|
| `l1_legacy_registrar` | retain | 0.2.0 | 0.3.0 |
| `l2_legacy_prompt_loader` | retain | 0.2.0 | 0.3.0 |

`0.3.0` 是最早允许评估删除的版本，不是自动删除承诺。只要证据不完整，就继续保留。

## 2. L1 Legacy Registrar

保留面：

- 未声明 `__pa_agent_extension_version__` 的 callable registrar 继续加载；
- versioned registrar 必须声明 `pa-agent.registry-extension.v1`；
- 未知显式版本继续隔离当前扩展，不阻断内置 registry 或其他扩展。

进入 `deprecated` 前必须：

1. 发布扩展开发文档，要求新扩展声明 v1；
2. 对维护者实际安装的扩展集合做 inventory；
3. 在至少一个发布 tag 中保留 legacy 支持并发出不含敏感内容的分类弃用诊断。

进入 `remove` 前，`docs/compatibility_evidence/l1_legacy_registrar/` 必须存在：

- `installed-extension-inventory.json`
- `deprecation-release-tag.json`
- `versioned-registrar-migration-report.json`

同时项目版本至少为 `0.3.0`，仓库存在 `v0.2.0` tag。

## 3. L2 Legacy Prompt Loader

保留面：

- `PromptAssembler(..., use_template_store=False)` 显式回滚；
- `PromptAssembler._load()` 旧 UTF-8 loader；
- TemplateStore 严格加载失败时整组回退 legacy loader；
- L2 新旧路径固定 fixture 字节等价观察。

进入 `deprecated` 前必须：

1. 至少一个发布周期记录 TemplateStore fallback 命中；
2. fallback 零命中且 golden snapshot、Stage 1/Stage 2/continuation 对照无偏差；
3. 提供模板文件损坏时的新恢复方案，不能通过删除 fallback 降低可恢复性。

进入 `remove` 前，`docs/compatibility_evidence/l2_legacy_prompt_loader/` 必须存在：

- `deprecation-release-tag.json`
- `template-fallback-zero-hit-report.json`
- `prompt-golden-equivalence-report.json`

同时项目版本至少为 `0.3.0`，仓库存在 `v0.2.0` tag。

## 4. 执行与变更规则

本地检查：

```powershell
py -3.12 scripts/check_compatibility_policy.py
py -3.12 -m pytest tests/unit/test_compatibility_policy.py `
  tests/integration/test_l1_extension_compatibility_observation.py `
  tests/integration/test_l2_template_compatibility_observation.py -q
```

兼容状态变化必须是独立原子迭代，并同步：

- `config/compatibility_policy.json`
- `AGENTS.md`
- `docs/CHANGELOG.md`
- `docs/architecture_roadmap.md`
- `docs/iteration_plan.md`
- 对应迁移文档、证据 JSON、测试和 CI 清单

禁止通过删除策略文件、CI 步骤、required symbol 或观察测试来绕过门禁。删除兼容入口后仍须保留
历史记录读取、Prompt schema、Provider/data source 内置路由和安全脱敏行为。
