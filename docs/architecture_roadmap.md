# L1-L6 架构升级路线图

> 状态：规划基线
> 更新时间：2026-07-23
> 适用分支：`main`
> 关联路线：[`docs/backend_review_report.md`](./backend_review_report.md)
> 短中期执行计划：[`docs/iteration_plan.md`](./iteration_plan.md)

本文档把长期路线图 L1-L6 细化为可分批迁移的架构计划。目标是降低模块之间的隐式耦合，
让 GUI、无 GUI 运行、测试和未来的服务端入口共享同一套应用核心，同时保持当前两阶段分析
的输出、提示词字节稳定性、记录格式和 Provider 路由行为。

本文档是迁移顺序和边界的主参考。具体实现仍需遵循每轮原子提交、同步更新
`AGENTS.md`/`CHANGELOG.md`、聚焦测试和 Ruff 基线的项目规则。
后续若干轮的建议交付物、验收顺序、依赖关系和风险边界见
[`docs/iteration_plan.md`](./iteration_plan.md)；若两者发生冲突，长期路线图事实以本文档为准。

## 1. 当前基线

| 路线 | 当前状态 | 已有基础 | 主要剩余工作 |
|---|---|---|---|
| L1 Provider/数据源注册表 | 扩展兼容观察与下线策略/CI 门禁已收口；legacy registrar 按政策 retain | registry、entry point、v1 registrar、失败隔离、并发/lazy-import 和固定样例观察已完成；`compatibility_policy.json` 强制保留未声明版本 callable | 观察真实安装扩展；最早 0.3.0 且具备 v0.2.0 tag、inventory 和迁移报告后才评估删除 |
| L2 Prompt 模板引擎 | 5 轮等价观察与下线策略/CI 门禁已收口；旧 loader/fallback 按政策 retain | TemplateStore、TemplateContext、29 个 manifest、system/Stage 1/Stage 2/continuation、golden snapshot 和回退观察已完成 | 最早 0.3.0 且具备 v0.2.0 tag、fallback 零命中和 golden 报告后才评估删除 |
| L3 Pipeline Builder | 受控 fixture rollout、显式 live legacy/Pipeline 入口和成对 artifact 比较合同已建立，默认 legacy，真实观察周期未收口 | 新增完整四步 Pipeline、默认关闭的 rollout flag、Task 10 终态矩阵、5 场景×3 轮对照、live harness opt-in 和 `compare_live_observations.py` | 在有凭据环境取得至少一个 `valid=true` 的 legacy/Pipeline pair 并完成稳定观察；满足后才评估启用默认 flag |
| L4 性能优化 | v2 hosted baseline 与同环境 10% p95 对照已收口，进入每日持续观察 | HTTP client 复用、forming-bar 判定复用、K 线几何 O(n) 化、记录缓存和并发锁；`pa-agent.performance.v1` 报告、`l4.synthetic.v2` 批量折算采样、p50/p95、100/500/5000 bars 基准、版本隔离 baseline cache 和 artifact；run `29975410917`/`29975592352` 完成建基线与 restore 对照 | 维护每日 schedule；runner image、benchmark version 或采样合同变化时重建 baseline |
| L5 经验库升级 | 评估合同、固定切分、opaque 导出/人工标注/报告管道已交付，真实数据评估未收口 | 全量相关性排序 + K 线相似度；版本化 dataset/split/report；HMAC opaque catalog、标签门禁和 leave-one-out legacy/similarity 对照；不改变线上排序 | 按 `docs/experience_evaluation_runbook.md` 导入真实案例、人工标注并生成指标报告；证据充分后才评估权重 |
| L6 无 GUI 运行 | mock 全链路等价、跨进程 replay、显式 live harness、单体/成对 artifact validator 已建立，真实环境观察未收口 | `AppEvent`/`EventSink`、严格 correlation replay、共享 core/gui bootstrap、`HeadlessAnalysisAdapter`、PyQt-free CLI、`run_live_headless_observation.py`、`validate_live_observation.py` 和 `compare_live_observations.py`；GUI/headless 已有全终态 fixture 对照 | 按 `docs/live_observation_runbook.md` 在有凭据环境取得真实 record/event pair 和稳定观察证据 |

当前经验目录主要是空目录占位，因而 L5 的 scorer 目前只能由合成 fixture 验证，不能据此
判断真实交易结构的检索质量；本轮只交付数据合同和指标实现，不改变线上权重。L5 后续工作
必须以脱敏数据集和离线指标为前置条件。

### 1.1 当前收尾判定

L1/L2 的实现、固定观察和下线策略门禁已收口，兼容入口按 `retain` 政策保留；L4 hosted
baseline/10% 对照已收口并进入每日观察。当前尚未满足外部证据条件的顺序为：

1. **L6**：在有凭据环境生成真实 legacy/Pipeline record/event pair；
2. **L3**：使用该 pair 完成真实 rollout 观察，再评估默认 flag；
3. **L5**：在有真实案例后完成人工标注和固定 split 指标报告。

其中 L1 已具备第二阶段注册表基础，未知数据源配置回退、生命周期/并发证据和 entry point 扩展契约
已完成，不再阻塞 L6；后续只观察外部扩展兼容性。L6 的 mock/fixed-fixture record 等价、
`pa-agent.event.v1` envelope 和严格跨进程 correlation replay 契约已建立，但仍需真实 Provider
runner 环境验证、真实运行 record/事件证据和 record/event 完整等价。单次 artifact 可由
`validate_live_observation.py` 审计，legacy/Pipeline pair 可由 `compare_live_observations.py`
比较终态、事件和 shape-only record 合同；两次独立模型正文不作为等价条件。L3 已建立
`orchestrator/pipeline/` 状态/步骤
协议并完成 Task 5 的 state foundation；Task 6 已交付 `Stage1Step`，Task 7 已交付 `RouteStep`，
Task 8 已交付 `Stage2Step`，Task 9 已交付 `PersistStep` 和 opt-in 等价证据；PersistStep
现在集中 full/partial record assembly/write，前置终态通过 `persistence_pending` 交给唯一一次
PersistStep 写入，成功后才发出 `RecordSaved`，磁盘失败由 `last_write_succeeded` 反馈并映射为
持久化失败。本轮已用 5 个终态场景、每场景 3 轮固定 fixture 完成 flag-off/flag-on
record、事件、prompt、流式内容、策略文件和写入边界对照；Pipeline feature flag、真实稳定
观察周期和 GUI/headless 真实运行全链路等价仍未收口。L6 的 mock/fixed-fixture 等价证据已
单独完成。
L5 在真实数据和人工指标建立前不得调整线上权重；L4 只在持续基准证明回退时修改热路径。

## 2. 目标架构

### 2.1 分层

```text
┌───────────────────────────────────────────────────────────┐
│ Entry points: GUI / CLI / future service                  │
└──────────────────────────────┬────────────────────────────┘
                               │ application ports
┌──────────────────────────────▼────────────────────────────┐
│ Application core: AppContext / Pipeline / use cases       │
│ - analysis request                                        │
│ - cancellation / progress                                 │
│ - records / experience policy                             │
└──────────────┬───────────────────────┬────────────────────┘
               │ ports                 │ ports
┌──────────────▼─────────────┐ ┌───────▼───────────────────┐
│ Domain / pure components    │ │ Adapters / infrastructure │
│ prompt context, validators, │ │ PyQt EventBus, data feeds,│
│ normalizers, decision rules │ │ OpenAI/Cursor, filesystem │
└────────────────────────────┘ └───────────────────────────┘
```

### 2.2 边界规则

1. **入口层不承载业务规则**：GUI 和 CLI 只负责收集参数、订阅事件和呈现结果。
2. **应用核心不导入 PyQt6**：Headless 模式必须能在无 Qt 环境中 import、构建和测试。
3. **注册表只做发现与构造**：Provider/data source registry 不负责 token 同步、网络探测、
   配置保存或 fallback 副作用。
4. **Prompt builder 不直接读全局配置文件**：配置由 `AppContext` 或显式 context 注入。
5. **持久化是边界适配器**：Pipeline 只调用记录端口，不直接拼接文件名或操作目录。
6. **决策规则保持纯函数优先**：技术指标、几何判断、业务规则不依赖 GUI、网络和磁盘。
7. **全局可变注册表和缓存必须线程安全**：锁只保护字典/缓存元数据，实际 IO、网络和构造放锁外。
8. **兼容优先于清理**：旧函数、旧记录和旧 prompt 输出在迁移期间继续可用，删除入口必须有
   明确的 deprecation 周期。

## 3. 迁移总原则

### 3.1 Strangler migration

每个大模块采用“新边界包裹旧实现”的方式迁移：

1. 先定义接口和适配器；
2. 新入口默认调用旧实现；
3. 为新旧路径建立等价性测试；
4. 按功能簇逐步切换；
5. 稳定一个完整周期后，才删除旧分支。

不允许一次性重写 `PromptAssembler`、`TwoStageOrchestrator` 或 `MainWindow`。

### 3.2 双路径与 feature flag

对有行为风险的阶段保留显式开关：

- `prompt.template_engine_enabled`
- `orchestrator.pipeline_builder_enabled`
- `runtime.headless_mode`

默认值在迁移完成前保持关闭或兼容模式；当前 `orchestrator.pipeline_builder_enabled` 的默认值
为 `false`，旧配置缺少 `orchestrator` section 时也回退到 legacy 默认。开关必须记录在诊断
日志和分析记录元数据中，便于比较新旧路径。

### 3.3 等价性证据

每个迁移切片至少提供一种证据：

- 旧/新函数相同输入的字节级输出比较；
- JSON/Pydantic 结构深度相等比较；
- 相同 fixture 下的事件序列比较；
- 相同记录目录下的读取结果排序比较；
- 性能基准在目标预算内无回退。

## 4. L1：Provider/数据源注册表收口

### 4.1 已完成

- `pa_agent/data/registry.py`
  - `DataSourceSpec`
  - `DataSourceRegistry`
  - 线程安全读写和延迟 builder
- `pa_agent/data/factory.py`
  - 内置六类数据源注册
  - `register_data_source()` / `unregister_data_source()`
  - 动态可见选项
- `pa_agent/ai/provider_registry.py`
  - `AIClientSpec`
  - matcher + priority + lazy builder
  - Cursor SDK 高优先级、OpenAI-compatible 低优先级兜底
- 现有 QClaw、WorkBuddy、Cursor 同步仍由连接器和
  `provider_sync_service.py` 负责。

### 4.2 目标边界

```text
Registry:
  kind/model matcher -> spec -> builder(settings, logger)

ProviderSyncService:
  detect environment -> resolve token/url -> mutate settings -> persist/fallback

Client/DataSource:
  connect/build -> runtime operations
```

注册表不得调用 `detect_qclaw()`、DPAPI、网络健康检查或 `save_settings()`。

### 4.3 后续收口

1. **插件发现**：已采用 Python entry points；本轮以外部风格样例观察
   `pa-agent.registry-extension.v1` 与旧 callable registrar 的兼容性，继续禁止扫描任意目录执行代码。
2. **配置持久化**：自定义 kind/model 只作为字符串保存；加载时由注册表校验，未知值安全回退并记录 warning。
3. **扩展契约**：已在 `pa_agent/extensions.py` 和项目文档中固定 registrar、builder、matcher、
   settings 注入、线程安全和注销时机边界。
4. **生命周期测试**：验证重复注册、replace、注销、并发读取以及 builder 不在锁内执行。

第 236 轮已完成第 2、4 项的第一批代码证据，前轮补齐已安装 entry point 发现、扩展失败隔离、
正式 registrar 契约和 builder 锁外执行证据；本轮又以 5 轮外部风格样例确认 versioned/legacy
registrar、settings 注入、matcher 和 builder 的兼容边界；运行时注册入口仍
不需要修改 `create_*` 条件分支。
下线策略由 `config/compatibility_policy.json` 和 `scripts/check_compatibility_policy.py`
强制执行：当前 `retain`，最早 `0.3.0` 且具备 `v0.2.0` 弃用 tag、安装扩展 inventory 和迁移
报告后才可评估删除 legacy callable。

### 4.4 验收标准

- 新增一个测试数据源或 AI client route 不需要修改 `create_*` 的条件分支；
- 内置路由与第 221 轮之前的实例类型、日志和错误行为一致；
- 可选依赖不会因 import registry 而提前加载；
- 注册表并发读写无数据竞争；
- 未知配置值不导致 GUI 启动崩溃。

## 5. L2：Prompt 模板引擎化

### 5.1 当前边界

`PromptAssembler` 目前同时承担：

- 公共 system prompt 拼装；
- `.txt` 文件读取和缓存；
- Stage 1/Stage 2 user prompt 调度；
- K 线表、经验库、市场特征和指导块的绑定；
- 增量分析和 continuation chain 兼容。

已经存在的 `Stage1PromptBuilder`、`Stage2PromptBuilder`、`kline_table_renderer`、
`experience_renderer`、`stage2_guidance` 是迁移的叶子边界，不应重新合并。

当前已建立 prompt engineering 合同化基线：`test_prompt_txt_files.py` 固定策略文件注册、
真实 `.txt` 存在性和 Stage 1 / Stage 2 组装顺序；`test_prompt_assembler.py` 固定阶段一/阶段二
边界、Stage 2 关键输出契约、禁止逆势三价、禁止 SCS/追高潮、禁止仓位管理、不依赖成交量以及
Spike/Climax 文本约束。第 230 轮新增 `ai/prompting/template_manifest.py`、
`ai/prompting/template_store.py` 和 `tests/fixtures/prompt_golden.json`：覆盖 29 个模板的
阶段/角色/版本/依赖元数据、严格 UTF-8 加载、缓存失效和 SHA-256 字节快照。第 231 轮将
共享 system prompt 的 `PERSONA`/`BINARY_DECISION` 读取切换到 TemplateStore，并以 golden
digest 和旧 `_load()` 直接对照证明字节相等。第 232 轮又迁移 Stage 1 的
`MARKET_DIAGNOSIS`/`KLINE_SIGNAL` 任务模板：全量、增量和 continuation 共用同一批量 loader，
任一严格加载失败则整组回退旧 `_load()`；第 233 轮又迁移 Stage 2 user prompt 和 continuation，
并新增 `TemplateContext` 与严格变量渲染。

### 5.2 目标模块

```text
ai/prompting/
├── template_store.py       # 文件读取、版本、缓存、严格变量检查
├── template_manifest.py    # 阶段、模板名、依赖和输出契约
├── template_context.py     # 显式、可序列化的渲染上下文
├── stage1_renderer.py      # Stage 1 模板编排
├── stage2_renderer.py      # Stage 2 模板编排
└── compatibility.py        # 旧 PromptAssembler API adapter
```

第 230 轮先引入结构化 `TemplateStore` 和 manifest；第 231-233 轮依次迁移共享 system、
Stage 1、Stage 2 和 continuation，不替换任何中文策略文本。TemplateStore 失败时可 warning
回退旧 `_load()`，也可通过 `use_template_store=False` 显式回滚。当前严格变量渲染使用标准库
`string.Template`，不引入 Jinja2 或任意代码执行能力：

- `Template.substitute` 或等价的缺变量失败策略；
- 禁止模板执行任意 Python；
- 模板加载失败时返回明确的诊断错误，不静默生成不完整 prompt；
- 系统 prompt 和 Stage 1→Stage 2 共享前缀继续走进程级缓存；
- 模板渲染结果支持 UTF-8 字节快照；
- render/render_many 记录模板名、阶段、context 键名、占位符、长度和失败原因等安全元数据，
  不记录变量值、完整 prompt 或密钥。

### 5.3 Context 设计

`TemplateContext` 只包含显式输入：

- `frame` 的 symbol/timeframe/bar_count 元数据；K 线表和程序特征仍由 builder 显式传入；
- `stage1_diagnosis`；
- `strategy_files`；
- `experience_entries`；
- `decision_stance`；
- `previous_record` / continuation 信息；
- `feature_flags` 和模板版本。

模板不直接访问 `Settings`、Qt 对象、网络客户端或文件系统。

### 5.4 迁移步骤

1. 已为 29 个 `.txt` 和共享 system prompt 建立 UTF-8 golden digest。
2. 已引入 `TemplateStore`，先只读取现有 `.txt`，旧 builder 继续作为默认 adapter。
3. 已迁移公共 system prompt，比较 Stage 1/Stage 2 字节前缀和 KV cache key，并保留旧路径回退。
4. 已迁移 Stage 1 user prompt 的两个静态任务模板，并覆盖全量/增量/continuation 复用和整组回退。
5. 已迁移 Stage 2 user prompt 和 continuation prompt，并覆盖 standalone/prefix-chain 两条路径。
6. 已新增 `TemplateContext`、严格变量渲染和 Stage 2 golden snapshots；旧 helper、旧 loader
   和兼容开关进入观察期，暂不删除。
7. 本轮新增 5 轮固定 fixture 兼容观察，重复验证 system、Stage 1、Stage 2 standalone、
   continuation standalone/prefix-chain 与旧 loader 字节相等；`use_template_store=False` 继续
   作为显式回滚路径。

### 5.5 验收/回滚

- 同一 fixture 下旧/新 prompt 完全相等，或差异被显式列入 snapshot 更新；
- 所有 JSON schema、normalizer、retry 和 continuation 测试通过；
- KV prefix 测试确认 system 前缀不漂移；
- 任一迁移阶段出现差异时，关闭对应的 `use_template_store`/feature flag 即可回退旧 assembler；
- 模板目录损坏不会影响旧路径启动；
- 兼容观察期内旧/新 loader 可按固定 fixture 重放并回滚；本轮已完成 5 轮观察，尚未达到
  删除旧入口的发布/回滚条件。
- 下线策略当前为 `retain`；最早 `0.3.0` 且具备 `v0.2.0` tag、fallback 零命中和 Prompt
  golden 等价报告后才可评估删除，CI 会阻止提前移除。

## 6. L3：Pipeline Builder / State Machine

### 6.1 当前问题

`TwoStageOrchestrator.submit()` 已拆出部分方法，但仍有大量跨阶段局部变量、流式闭包、取消检查、校验重试和 partial record early return。当前状态隐含在方法栈中，
不利于 headless、重放、插桩和恢复。第 238 轮已建立显式 state/step 契约和 legacy wrapper，
Task 5 又补齐了阶段 payload、route 输出、持久化意图、route/persist 终态映射和安全摘要；
Task 6 已将 Stage 1 拆为真实 `Stage1Step`，Task 7 又将路由和经验加载拆为真实 `RouteStep`；
Task 8 已将 Stage 2 准备/执行拆为真实 `Stage2Step`，Task 9 已将 record 组装与写入拆为真实
`PersistStep`；Task 10 已接入默认关闭的 rollout flag、完整终态矩阵和 Qt-free adapter
equivalence 测试。四个步骤仍只在 flag-on/opt-in pipeline 使用，默认 `submit()` 路径保持 legacy。

### 6.2 目标对象

已新增 PyQt6-free 模块：

```text
orchestrator/pipeline/
├── state.py       # PipelineState、TerminalStatus、StageUsage
├── step.py        # PipelineStep Protocol 和 StepResult
├── steps.py       # preflight/stage1/route/stage2/validate/persist
├── events.py      # 应用级 pipeline event DTO
└── builder.py     # PipelineBuilder 和默认步骤装配
```

当前切片实际包含 `state.py`、`step.py`、`steps.py`、`builder.py` 和包导出；`events.py`
仍留待后续切片。`Stage1Step`、`RouteStep`、`Stage2Step` 和 `PersistStep` 已是真实步骤，其中
RouteStep 负责复用 router/经验读取并写入 route state，Stage2Step 负责 continuation、flags、
gate、Provider 调用、流式、retry、失败和取消边界，PersistStep 负责 terminal record assembly、
full/partial write、磁盘失败映射和 `RecordSaved` ordering。`LegacyPersistStep` 仅作为兼容名称
保留，不是当前 opt-in sequence 的步骤。

`PipelineState` 当前显式包含：

- `frame`、`settings`、`cancel_token` 和 legacy callbacks（仅运行时，不进入摘要）；
- Stage 1/Stage 2 messages、reply/raw response 引用、normalized JSON、usage 和 usage calls；
- strategy files、experience entries、route outputs；
- `partial_reason`、`PersistenceIntent`、`persistence_pending`、record、events、step history
  和 terminal status；
- settings/feature metadata（仅通过 allowlist 摘要暴露），以及后续兼容所需的增量上下文。

`safe_summary()`/`to_safe_json()` 不保留 callbacks、Provider client、prompt/reply 正文、
normalized JSON 值、frame bars、行情数据或密钥；mapping/object usage 只提取 token counters，
`base_url` 只保留 `http`/`https` origin，移除凭据、path、query 和 fragment。

Pipeline enabled 生命周期日志使用同一 `trace_id` 关联一次执行，事件名为
`pipeline.lifecycle`、`pipeline.event`、`pipeline.step` 和 `pipeline.timing`，字段通过 allowlist 限制为
步骤/阶段、结果或终态分类、异常类型分类、耗时、跳过原因、写入状态和 `safe_summary`。
诊断时可按 `trace_id` 聚合，或按四个事件名过滤，再按 `pipeline_step` 查询
`Preflight -> Stage1 -> Route -> Stage2 -> Persist`。禁止写入原始行情、股票/合约代码、
价格、prompt/Provider 原文、API Key、Provider Token、callbacks 或 client 对象。`pipeline.timing`
在 Stage 2 启动前记录 `stage1_to_stage2` 边界及 Stage 1/Route 已完成耗时。
Task 11 已同步生命周期日志业务代码、聚焦测试和项目文档/规格，并已纳入原子提交/推送。

步骤协议建议：

```text
step.run(state, services) -> Continue(state) | Complete(record) | Fail(record)
```

取消、网络错误、校验失败和 gate short-circuit 都必须转换为明确的 terminal status，
不能通过“某个局部变量是否存在”推断阶段进度。

### 6.3 迁移步骤

1. **已完成**：定义状态/终态/步骤协议，以 `LegacySubmitStep` 包装现有 `submit()`，并证明
   happy path、事件序列和取消终态等价。
2. **已完成 Task 5 foundation**：扩展阶段 payload、usage、route outputs、`PersistenceIntent`
   和 partial reason；补充 `route_failed`/`persist_failed` 映射，且不改变 `AnalysisRecord` schema。
3. **已完成 Task 5 安全边界**：提供 shape-only safe summary/JSON，mapping/object usage 仅保留
   token counters，allowlist metadata 只保留安全标签和 URL origin。
4. **已完成 Task 6**：把现有 Stage 1 helper 适配为真实 `Stage1Step`；Stage 1 集成测试覆盖
   happy/retry/network/validation/cancel/incremental，且验证最终 record 与事件等价。
5. **已完成 Task 7**：把 `_route_and_load_experience` 适配为真实 `RouteStep`，并在 opt-in
   pipeline 中按 `Stage1Step -> RouteStep -> ...` 执行；保持 callable/object router、策略文件
   顺序、经验数量/字符限制、`current_bars`、空经验库和 Stage 2 前取消边界，route exception
   映射为 `route_failed` partial terminal。
6. **已完成 Task 8**：把 Stage 2 continuation 构建、settings flags、gate short-circuit、
   Provider 调用、流式、retry、network、validation 和 cancel 边界适配为真实 `Stage2Step`；
   opt-in sequence 进入 `Stage2Step -> PersistStep` 尾部，并通过 `persist=False` 把 record
   组装与写入边界分开。
7. **已完成 Task 9**：新增真实 `PersistStep`，集中 full/partial record assembly、partial
   reason、保留 `PendingWriter` 脱敏、磁盘错误和 `RecordSaved` 契约；前置终态通过
   `persistence_pending` 交给 PersistStep，Builder 不会重复执行写入。full 写入成功后先清除
   pending，再发 `RecordSaved`，最后标记 completed；partial 写入和磁盘失败均不发出成功事件。
8. 保留 `submit()` 作为 compatibility facade，flag-off 默认调用旧路径，flag-on 委托完整四步
   Pipeline。
9. **已完成 Task 10 rollout 准备**：新增
   `orchestrator.pipeline_builder_enabled`（默认 `false`），为 Settings round-trip 和缺少
   `orchestrator` section 的旧配置补充 legacy 默认，接入 flag 路由，建立完整终态矩阵及
   Qt-free headless/GUI adapter equivalence 测试，并将测试/config module 纳入 CI targets。
10. **已完成受控 fixture rollout 观察**：在默认 flag 仍关闭的前提下，以 5 个终态场景、
    每场景 3 轮比较 flag-off/flag-on 的 record、事件、prompt、流式内容、策略文件和写入边界；
    下一步仍需真实 Provider 稳定观察周期和 GUI/headless 真实运行 final/partial/cancel/failure
    evidence。
11. 只有上述观察和 evidence 无未解释偏差后，才评估启用默认 flag；随后再评估删除旧
    `submit()` 内部实现，只保留 facade。

### 6.4 事件与取消契约

Pipeline 只能发出应用级事件，例如：

- `AnalysisStarted`
- `StageStarted`
- `StageProgress`
- `ValidationRetried`
- `RecordSaved`
- `AnalysisCancelled`
- `AnalysisFailed`

Qt signal、CLI stdout 和日志分别由入口 adapter 映射。取消令牌必须在每个可等待步骤前后
检查；步骤不得阻塞在无法取消的长 sleep 或网络重试上。

### 6.5 验收/回滚

- `Stage1Step` 的 happy、retry、network、validation、cancel、incremental 路径以及最终 record/
  event equivalence 已有 opt-in 测试证据；`RouteStep` 已有 callable/object router、策略顺序、
  experience limit、empty library、`current_bars`、取消和 `route_failed` 测试；`Stage2Step` 已有
  continuation/flags、流式、gate short-circuit、retry、network、validation、cancel 和 partial
  record 等价测试；`PersistStep` 已有 full/partial/insufficient-data、`RecordSaved` ordering、
  磁盘失败和 `persistence_pending` 防重复保存测试；Task 10 另有完整终态矩阵、
  `submit()` flag-off/flag-on 路由、Settings round-trip/旧配置 legacy 默认以及 Qt-free
  headless/GUI adapter equivalence 测试；
- route failure 已产生稳定的 `route_failed`；Stage2 failure 已有显式终态；PersistStep 已收口
  full/partial assembly/write、partial reason、`PendingWriter.last_write_succeeded` 和
  persist failure；
  且摘要不会暴露
  callbacks、Provider client、prompt/reply 正文、行情数据、密钥或 URL path/query/fragment；
- 事件顺序和事件 payload 可快照比较；
- Pipeline 不导入 PyQt6；
- feature flag 关闭时旧 `submit()` 行为不变；
- 四个真实步骤与 Pipeline feature flag 接线已齐；受控 fixture rollout 已覆盖 5 个终态场景
  × 3 轮且默认 flag 仍为 `false`，至少一个真实稳定观察周期和 GUI/headless 真实运行
  final/partial/cancel/failure 全链路等价仍待完成；
- 任一阶段出现差异可按 symbol/timeframe 或配置开关回退。
- 生命周期日志仅证明 opt-in 路径可观测，不代表默认 flag 可以开启；在真实稳定观察周期和
  GUI/headless final、partial、cancel、failure 全链路 evidence 无未解释偏差前，必须保持
  `orchestrator.pipeline_builder_enabled=false`。

## 7. L4：性能预算与持续验证

L4 的主要代码优化已经完成，本路线不建议继续凭感觉修改热路径。后续工作从“优化实现”
转为“建立预算和证据”：

| 热点 | 已完成 | 后续验证 |
|---|---|---|
| API client | 连接池复用 | Stage 1→2 latency、连接重建次数 |
| snapshot | forming 判定复用 | refresh tick p50/p95、forming/closed 分支 |
| K 线几何 | EMA gap O(n) | 100/500/5000 bars benchmark |
| records | latest record cache + 文件名预过滤 | pending 文件数量增长时读取预算 |
| prompt | system prompt 进程缓存 | prompt build 时间和 KV prefix 命中率 |
| 全局状态 | 多处锁 | 锁等待时间和无死锁测试 |

性能基准要求：

- 使用固定 synthetic fixture，避免网络噪声；
- 报告 p50/p95，而不是单次最好成绩；
- 任何新增锁、序列化或模板步骤都必须有基线对比；
- 性能回退超过 10% 时先分析，再决定是否改变实现。

`pa_agent.perf.benchmark` 和 `tools/run_l4_benchmark.py` 的固定 suite 覆盖 snapshot build、
indicator 和 K-line geometry 的 100/500/5000 bars。v1 hosted run `29930306551` 与
`29974597115` 均恢复首次 baseline 并被 10% 门禁阻断，但失败项分别落在不同亚毫秒操作；
三次 runner image 完全相同，确认逐次计时受调度抖动放大。`l4.synthetic.v2` 因此按操作成本
批量执行后折算单次耗时，报告增加 `sample_repeats`，10% 回归阈值和绝对预算保持不变；
本地报告为 `docs/benchmarks/l4_synthetic_v2_2026-07-23.json`。workflow 使用独立
`l4-baseline-v2-*` cache，避免混用 v1 baseline。run `29975410917` 已建立 v2 hosted baseline，
run `29975592352` 成功恢复对应 cache 并完成九项 p95 对照；最大正回退为 `+5.12%`，低于
10% 门禁。L4 进入每日持续观察，runner image、benchmark version 或采样合同变化时重建 baseline。

## 8. L5：经验库评估与版本化

### 8.1 当前实现

`ExperienceReader.read_for_stage2()` 当前顺序为：

1. 全量加载指定 cycle position 的可读案例；
2. direction 匹配和 pattern overlap 评分；
3. 用 `experience_similarity.py` 的最近 K 线几何分数打破同分；
4. timestamp 作为稳定兜底；
5. 截断到 `max_entries`。

旧案例没有 `kline_data` 时不参与相似度评分，但继续参与旧的相关性排序。

本轮新增 `pa_agent.records.experience_eval`，定义
`pa-agent.experience-eval.v1` dataset envelope 和 `kline-geometry.v1` feature version。
评估输入只保留 opaque instrument id、周期/方向/形态、候选数量和人工标注的相关案例 id；
不携带价格、K 线原文、截图路径、密钥或本地绝对路径。新增
`pa-agent.experience-split.v1` / `instrument-hash.v1`，按 opaque instrument group 做稳定
hash split，并以 dataset digest 防止 split 错用于其他数据集；`evaluate_rankings()` 输出宏平均
`Recall@K`、`NDCG@K`、similarity fallback rate、top-K ranking stability 和 score distribution。
`pa_agent.records.experience_eval_pipeline` 与 `tools/run_experience_evaluation.py` 又补齐真实
经验目录到 evaluator 的安全入口：使用环境变量 salt 生成 HMAC opaque case/instrument ID，
导出不可篡改的人工标注模板，校验全量 reviewed 标签，并以 leave-one-out 旧/新排序生成固定
split 报告。产物只允许写入 Git 忽略的 `artifacts/`，流程见
`docs/experience_evaluation_runbook.md`；当前目录无真实 JSON 案例，因此仍不能给出质量结论。

### 8.2 下一阶段前置条件

在真实经验案例不足前，不调整 body/direction/range 权重。数据合同已建立，仍需：

- 案例 schema 版本字段；
- feature extraction version；
- `success`/`failure`、symbol、timeframe、cycle、direction、patterns 的完整元数据；
- 脱敏后可用于离线测试的案例导出；
- 使用 `build_fixed_split()` 生成固定 train/evaluation 切分，避免同一 instrument group
  泄漏到评估集；真实数据仍需人工检查更高层结构泄漏。

### 8.3 离线指标

至少记录：

- `Recall@K`：人工标注的相关案例是否进入前 K；
- `NDCG@K`：相关性排序质量；
- legacy fallback rate：没有可比 K 线的案例比例；
- score distribution：不同 cycle、方向和成功/失败类别的分布；
- ranking stability：新增一条案例后旧候选排序的扰动范围。

### 8.4 迁移策略

1. 先只写离线 scorer，不改变线上排序；
2. 生成旧规则与新规则的并排报告；
3. 通过最小样本门槛和人工抽样评审后，再开启新权重；
4. 将权重、特征版本和窗口写入检索诊断信息；
5. 线上保留旧规则 fallback 和 `similarity_enabled` 开关。

L5 的下一轮应是“数据集/基准迭代”，不是直接修改线上公式。

## 9. L6：无 GUI 运行支持

### 9.1 当前边界

`EventBus` 仍是 Qt adapter，直接继承 `QObject` 并继续暴露旧 signals。第 223 轮已新增
PyQt-free `AppEvent` / `EventSink` / `CollectingEventSink`，并让 `EventBus.publish()` 能把应用
事件转发到旧 Qt signals。第 224 轮新增 `AppContext.bootstrap_headless()`，可在不创建 Qt
`EventBus`、不连接数据源的情况下装配核心组件。

第 225 轮完成 `AppContext` core/gui bootstrap 边界拆分：共享 `_build_core()` 负责 settings、
AI client、Prompt、Validator、记录、经验库和 ledger 等核心服务；`bootstrap_gui()` 负责 Qt
`EventBus`、数据源连接和默认订阅，并让 `event_sink` 指向 `EventBus`；旧 `bootstrap()` 保持
兼容 facade 并委托 GUI 路径。`bootstrap_headless()` 复用同一 core helper，继续保持无 Qt
`EventBus` import、无数据源连接。第 229 轮已新增 PyQt-free CLI 最小入口和同 snapshot 的
Stage 1 prompt 等价测试，第 234 轮已新增 PyQt-free JSONL event sink/replay，第 237 轮新增
显式 `--run/--execute` 的两阶段 runner、final/partial record 持久化和 correlation 事件输出；
本轮新增公开 `HeadlessAnalysisAdapter` 的阶段回调合同、GUI `_AnalysisWorker` 与 headless
adapter 的 final/partial/cancel/failure fixture 对照测试，以及 `pa-agent.event.v1` JSONL
envelope 版本校验；真实 Provider 环境验证、真实运行 record/事件证据和跨进程 correlation
重放仍未建立。

### 9.2 目标端口

新增 PyQt6-free 应用事件模型：

```text
util/events.py
  AppEvent(type, timestamp_ms, correlation_id, payload)

JSONL envelope:
  {"schema": "pa-agent.event.v1", "type": ..., "timestamp_ms": ...,
   "correlation_id": ..., "payload": ...}

util/event_sink.py
  EventSink Protocol
  NullEventSink
  CollectingEventSink

util/event_bus.py
  EventBus(EventSink)
```

兼容期间保留现有 `EventBus` 名称，由它实现 `publish(AppEvent)` 并继续暴露 Qt signals。
headless 使用 `CollectingEventSink` 或后续 JSONL sink，不创建 `QApplication`。

### 9.3 AppContext 迁移

`AppContext` 现在已拆成：

```text
AppContext._resolve_settings(...)
AppContext._build_core(...)
AppContext.bootstrap_gui()
AppContext.bootstrap_headless()
AppContext.bootstrap() -> bootstrap_gui()
```

`AppContext.build_core(...)` 已作为公开 PyQt-free 共享服务构造入口，GUI/headless 两条路径均
通过它装配；`_build_core(...)` 仅保留兼容委托。GUI adapter 继续由 `bootstrap_gui()` 负责，
不额外公开会触发数据源连接的 `build_gui_adapters()`。

两者共享 settings、client、assembler、validator、records、experience reader 和
pipeline services；只有 GUI 入口装配 Qt `EventBus`、数据源连接/订阅、MainWindow 和 Qt widgets。

### 9.4 CLI 形态

第一阶段的 CLI 已支持无网络副作用的分析辅助命令，并提供显式执行入口：

```text
pa-agent headless validate-config
pa-agent headless snapshot --input snapshot.json --output normalized.json
pa-agent headless analyze --input snapshot.json --output dry-run.json
pa-agent headless analyze --input snapshot.json --run --records-dir records/ --events events.jsonl
```

约束：

- 默认输出结构化 JSON，不把诊断文本混入 stdout；
- 日志写 stderr 或指定日志文件；
- 当前 `analyze` 默认仍是 provider-free dry-run：只校验 snapshot 并构建 Stage 1 prompt 统计；
  只有显式 `--run/--execute` 才调用 Provider、执行两阶段 orchestrator 并写入 final/partial
  `AnalysisRecord`；
- `--events` 输出带 correlation id 的 orchestrator milestone JSONL，`--records-dir` 沿用现有
  `PendingWriter` 记录目录；runner 错误映射到稳定退出码，stdout 不输出 `raw_text`；
- 不执行真实下单；
- 网络、API key、文件路径都从显式参数或 settings 注入；
- 退出码区分配置错误、数据错误、Provider 错误、校验错误和用户取消。

### 9.5 验收/回滚

- 在未安装 PyQt6 的 Python 环境中可以 import headless core；
- headless 与 GUI 对同一 snapshot 在固定 fixture 下产生相同 Stage 1/Stage 2 final/partial/
  cancel/failure record 和 milestone 序列；
- 新事件使用 `pa-agent.event.v1` JSON envelope，事件可以序列化并重放，旧缺失 schema 的
  envelope 保持兼容；
- GUI 继续使用现有 signal 语义；
- `bootstrap_gui()` 出现问题时不影响 `bootstrap_headless()` 的单元测试。

## 10. 推荐实施顺序

### Phase 0：本规划

- 固化边界、接口、依赖和验收标准；
- 不改变业务运行路径。

### Phase 1：L1 收口

- 已完成 settings 字符串安全回退，以及 registry 并发、replace、注销和 lazy import 测试；
- 已完成 entry point 插件发现和 settings/扩展契约设计，后续观察外部扩展兼容性；
- 不引入动态代码扫描。

### Phase 2：L6 Headless core

- 已抽象应用事件和 `EventSink`；
- 已拆分 `AppContext` core/gui bootstrap；
- 已新增 `pa_agent/cli.py` 和 `pa-agent headless` 最小 dry-run 入口；
- 已用固定 snapshot 验证 GUI/headless 共享 core 的 Stage 1 prompt 等价；
- 已新增显式 `--run/--execute` 两阶段 runner、final/partial record 持久化、退出码映射和
  correlation JSONL 事件；严格 replay 可按 `expected_correlation_id` 校验整条跨进程流并在
  发布前拒绝混流或缺失 ID；
- 公开 `HeadlessAnalysisAdapter` 已交付；已补 GUI `_AnalysisWorker` 与 headless adapter 的
  final/partial/cancel/failure fixture 等价、阶段回调对照、`pa-agent.event.v1` envelope 和
  跨进程 replay contract；新增显式 `tools/run_live_headless_observation.py`，只读环境变量
  凭据并输出脱敏 summary；`tools/validate_live_observation.py` 可离线核对 summary/event/
  record 自洽性；`tools/compare_live_observations.py` 可对 legacy/Pipeline 两次产物做控制流和
  记录结构比较。完整执行顺序见 `docs/live_observation_runbook.md`；下一步在有授权凭据环境
  取得至少一个真实 `valid=true` pair 并进行稳定观察。

### Phase 3：L2 Prompt engine

- 已完成 TemplateStore、manifest、system、Stage 1、Stage 2、continuation 和 golden snapshots；
- 已完成显式 `TemplateContext` 与严格变量渲染；
- 当前处于旧 loader/helper 和 feature flag 的兼容观察期；
- 保持旧 PromptAssembler facade。

### Phase 4：L3 Pipeline

- 已建立显式 `PipelineState`/`TerminalStatus`/`PersistenceIntent`/`PipelineStep`/`StepResult`
  协议和 legacy wrapper；
- 已完成 Task 5 的阶段 payload、route/persistence intent、route/persist 终态映射和安全摘要；
- 已完成 Task 6 的 `Stage1Step`、Task 7 的 `RouteStep`、Task 8 的 `Stage2Step` 和 Task 9
  的 `PersistStep` 真实步骤；Task 10 已完成默认关闭的 flag 接线、完整终态矩阵和 Qt-free
  adapter equivalence 测试；flag-on sequence 为
  `Stage1Step -> RouteStep -> Stage2Step -> PersistStep`；
- `PersistStep` 集中 full/partial record assembly/write，前置终态通过
  `persistence_pending` 防止重复保存，`PendingWriter.last_write_succeeded` 反馈磁盘写入结果；
  full 写入成功后才发 `RecordSaved`，partial 或 disk failure 不发成功事件；
- 继续用 headless harness 做新旧事件和记录等价性验证，补齐 GUI/headless final/partial/cancel/
  failure 全链路 evidence；
- 显式 `tools/run_live_headless_observation.py --pipeline-builder-enabled` 只对本次有授权运行
  打开 Pipeline，未传参数保持 legacy；
- 默认 flag 仍关闭；后续先进行受控 flag-on rollout 并观察至少一个真实稳定周期，待 GUI/headless
  全链路 evidence 无未解释偏差后，再评估默认路径切换和旧路径下线。

### Phase 5：L5 数据评估

- 已建立版本化脱敏评估合同和离线 scorer；
- 已建立 `pa-agent.experience-split.v1` instrument-grouped 固定切分和 dataset digest；
- 已建立真实经验 HMAC opaque 导出、人工标注门禁、leave-one-out 旧/新排序和版本化报告管道；
- 下一步按 runbook 导入真实案例、人工标注并建立固定 train/evaluation benchmark；
- 仅在指标改善且稳定性可接受时调整线上权重。

### Phase 6：L4 预算收口

- 已建立固定 synthetic benchmark、p50/p95 报告和 10% regression 判定；v2 对短操作使用
  批量执行后折算单次耗时，且报告记录 `sample_repeats`；
- 已新增 `.github/workflows/l4-benchmark.yml`，接入手动/夜间预算门禁和报告 artifact；
- v1 首次 run `29923921295` 已保存 hosted baseline；run `29930306551`/`29974597115`
  均恢复该 baseline 并正确阻断，失败未覆盖成功 baseline，且 runner image 保持一致；
- 由于 v1 的失败项在不同亚毫秒操作间漂移，workflow 已切换独立 v2 cache；run
  `29975410917`/`29975592352` 已完成 v2 建基线与同参数 restore 对照，九项全部通过；
- v2 两轮均由具备仓库 Write 权限的账号手动触发，使用 `iterations=30`、`warmups=5`；
  后续网页入口不需本地 token，CLI/API 入口继续使用仅限 `PA_Agent` 且 Repository
  `Actions: Read and write` 的 Fine-grained PAT；
- v1 证据证明 restore、10% 阻断、失败 artifact 和失败不覆盖 baseline 均有效，但不把受
  亚毫秒抖动影响的结果作为 v2 性能结论；
- PAT、Provider key 和 benchmark 原始敏感配置不得写入仓库或日志；触发权限配置不等于扩大
  workflow 内的 `GITHUB_TOKEN` 权限，当前 `contents: read` 保持最小范围；
- 只对有数据证明的热点继续优化；
- 每日 schedule 持续观察；runner image、benchmark version 或采样合同变化时重建 baseline。

L1、L4、L5 的收口工作可以并行，但 L6 应先于 L3；L2 可以与 L6 后半段并行，
不建议在 Pipeline 状态模型尚未稳定时进行大规模 Prompt 重写。

## 11. 测试和质量门禁

### 单元测试

- registry：匹配优先级、重复注册、replace、注销、线程安全、lazy import；
- TemplateStore：变量缺失、编码、版本、snapshot、缓存失效；
- Pipeline：每个 terminal status、`Stage1Step` 的 happy/retry/network/validation/cancel/incremental
  路径、`RouteStep` 的 callable/object router、策略顺序、经验限制、空经验库、`current_bars`、
  取消和 `route_failed`、`Stage2Step` 的失败与取消、`PersistStep` 的 full/partial assembly/write、
  `RecordSaved` ordering、磁盘失败、`persistence_pending` 防重复保存和最终 record equivalence；
- EventSink：Qt adapter、collecting sink、JSONL sink；
- L5：数据集切分、指标计算、legacy fallback。

### 集成测试

- GUI 与 headless 对同一 snapshot 的 record 等价；
- Provider/data source registry 与 AppContext 装配；
- Prompt → validator → Pipeline 的完整链路；
- 记录写入、重新加载和经验读取闭环。

Stage 1 集成测试 `tests/integration/test_stage1_pipeline_step.py`、Route 集成测试
`tests/integration/test_route_pipeline_step.py`、Stage 2 集成测试
`tests/integration/test_stage2_pipeline_step.py` 和 Persist 集成测试
`tests/integration/test_persist_pipeline_step.py`，以及 Task 10 集成测试
`tests/integration/test_task10_pipeline_rollout.py` 同时纳入 CI targeted pytest；其中
`pa_agent/config/orchestrator.py` 纳入 focused Ruff/config target。GUI/headless 全链路等价仍待补齐。

### 每轮最低门禁

```text
py_compile 受影响模块
目标 pytest
pytest -m "not e2e and not live"
ruff check 受影响模块
ruff format --check 受影响模块
scripts/check_ci_workflow_targets.py
scripts/check_ruff_baseline.py
```

涉及 prompt、schema、pipeline 或 headless 的轮次必须补充 golden fixture 或事件快照，
不能只依赖 import/py_compile。

## 12. 风险与回滚

| 风险 | 影响 | 预防 | 回滚 |
|---|---|---|---|
| Prompt 字节变化 | KV cache、模型输出和校验行为变化 | golden snapshot、前缀比较、feature flag | 关闭模板引擎 |
| Pipeline 状态遗漏 | partial record/取消语义变化 | terminal status 全覆盖、旧新路径对照 | 关闭 Pipeline flag |
| Qt 依赖泄漏 | headless 无法启动 | import boundary 检查、无 Qt 环境 CI job | 使用旧 GUI bootstrap |
| Registry matcher 冲突 | 错误 Provider/data source | priority、重复名拒绝、路由诊断 | 注销扩展、恢复内置规格 |
| L5 过拟合 | 经验检索质量下降 | 固定评估集、人工抽样、legacy fallback | `similarity_enabled=false` |
| 配置迁移失败 | 启动失败或选项丢失 | 字符串兼容、未知值回退、备份写入 | 读取旧 settings schema |
| 大文件重构范围失控 | 合并冲突和回归 | 一轮一个边界、禁止无关格式化 | 保留 compatibility facade |

## 13. 完成定义

L1-L6 只有同时满足以下条件，才标记为完成：

1. 新边界有明确模块和公开契约；
2. 旧入口在迁移周期内保持可用；
3. 有单元、集成和失败路径测试；
4. GUI/headless 或旧/新路径结果有等价性证据；
5. 线程安全、日志脱敏、配置和文件安全约束未回退；
6. 文档、CHANGELOG、AGENTS、路线图和 CI 清单同步；
7. 至少一个真实或脱敏 fixture 覆盖主路径；
8. 提交可独立回滚，且 feature flag/兼容 facade 已有明确下线计划。

第 229 轮已完成 L6 headless runner 的最小入口，第 230-233 轮已完成 L2 TemplateStore
基线、共享 system、Stage 1、Stage 2、continuation、`TemplateContext` 和严格变量渲染。
第 238 轮已完成 L3 state/step compatibility adapter，Task 5 完成 PipelineState foundation，
Task 6 完成 `Stage1Step`，Task 7 完成 `RouteStep`，Task 8 完成 `Stage2Step`，Task 9 完成
`PersistStep`，Task 10 完成 rollout flag 接线、终态矩阵和 Qt-free adapter equivalence；
L6 已补齐 mock/fixed-fixture GUI/headless 全终态等价和 `pa-agent.event.v1` envelope 版本契约；
`AppContext.build_core()` 公共入口和 legacy/Pipeline 成对 artifact 合同也已交付。当前下一步
只剩真实 Provider 环境观察；L3 默认 flag 仍关闭，后续需真实稳定周期。L5 等待真实经验数据；
L1/L2 按兼容策略 retain，L4 每日观察。
