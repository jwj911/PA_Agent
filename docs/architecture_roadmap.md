# L1-L6 架构升级路线图

> 状态：规划基线
> 更新时间：2026-07-19
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
| L1 Provider/数据源注册表 | 第二阶段完成 | `data/registry.py`、`ai/provider_registry.py` 已支持规格、优先级、延迟 builder 和运行时注册 | 插件发现、配置持久化和扩展契约仍需在后续治理中固化 |
| L2 Prompt 模板引擎 | 存储/合同基线完成，默认 assembler 尚未迁移 | `Stage1PromptBuilder`、`Stage2PromptBuilder`、多个 PyQt-free renderer、29 个模板 manifest、`TemplateStore` 和 UTF-8 golden digest；prompt 文件顺序、阶段边界、硬禁令和 Spike/Climax 约束已有合同测试 | 引入 TemplateContext/严格变量渲染，按 system → Stage 1 → Stage 2 → continuation 迁移并保留兼容 adapter |
| L3 Pipeline Builder | 部分准备 | `TwoStageOrchestrator.submit()` 已拆出 `_run_stage1`、`_run_stage2`、路由和持久化方法 | 用显式状态和步骤协议替代方法内隐式局部状态与 early return |
| L4 性能优化 | 主要目标完成 | HTTP client 复用、forming-bar 判定复用、K 线几何 O(n) 化、记录缓存和并发锁 | 增加基准、预算和回归监控，不再无证据地继续优化 |
| L5 经验库升级 | 第二阶段完成 | 全量相关性排序 + K 线几何相似度 | 等待真实经验样本后做离线评估、特征版本化和权重校准 |
| L6 无 GUI 运行 | CLI 最小切片完成 | `AppEvent`、`EventSink`、`CollectingEventSink`、共享 `_build_core()`、`bootstrap_gui()`/`bootstrap_headless()`、兼容 `bootstrap()`，以及 PyQt-free `pa-agent headless` 已可用 | 真实 Provider runner、Stage 1/2 最终 record 等价测试、JSONL 事件重放和公开 adapter 契约 |

当前经验目录主要是空目录占位，因而 L5 的分数函数目前只能由合成 fixture 验证，不能据此
判断真实交易结构的检索质量。L5 后续工作必须以数据集和离线指标为前置条件。

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

默认值在迁移完成前保持关闭或兼容模式。开关必须记录在诊断日志和分析记录元数据中，
便于比较新旧路径。

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

1. **插件发现**：评估 Python entry points 或显式 bootstrap registration，禁止扫描任意目录执行代码。
2. **配置持久化**：自定义 kind/model 只作为字符串保存；加载时由注册表校验，未知值安全回退并记录 warning。
3. **扩展契约**：补充 builder、matcher、settings 注入、线程安全和注销时机的开发者文档。
4. **生命周期测试**：验证重复注册、replace、注销、并发读取以及 builder 不在锁内执行。

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
阶段/角色/版本/依赖元数据、严格 UTF-8 加载、缓存失效和 SHA-256 字节快照；旧
`PromptAssembler._load()` 仍是默认路径，TemplateStore 只作为兼容旁路和合同层。

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

第 230 轮已先引入结构化 `TemplateStore` 和 manifest，不替换任何中文策略文本，也不改变
`PromptAssembler` 默认路径。下一步只迁移一个边界（优先共享 system prompt 或 Stage 1 user
prompt），完成旧/新字节等价后再继续。
模板引擎可选 Jinja2，但必须满足：

- `StrictUndefined` 或等价的缺变量失败策略；
- 禁止模板执行任意 Python；
- 模板加载失败时返回明确的诊断错误，不静默生成不完整 prompt；
- 系统 prompt 和 Stage 1→Stage 2 共享前缀继续走进程级缓存；
- 模板渲染结果支持 UTF-8 字节快照。

### 5.3 Context 设计

`TemplateContext` 只包含显式输入：

- `frame` / K 线表和程序特征；
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
3. 迁移公共 system prompt，比较 Stage 1/Stage 2 字节前缀和 KV cache key。
4. 迁移 Stage 1 user prompt。
5. 迁移 Stage 2 user prompt 和 continuation prompt。
6. 最后删除重复的 `PromptAssembler` 静态 helper，保留兼容重导出。

### 5.5 验收/回滚

- 同一 fixture 下旧/新 prompt 完全相等，或差异被显式列入 snapshot 更新；
- 所有 JSON schema、normalizer、retry 和 continuation 测试通过；
- KV prefix 测试确认 system 前缀不漂移；
- 任一迁移阶段出现差异时，关闭新路径即可回退旧 assembler；
- 模板目录损坏不会影响旧路径启动。

## 6. L3：Pipeline Builder / State Machine

### 6.1 当前问题

`TwoStageOrchestrator.submit()` 已拆出部分方法，但仍有大量跨阶段局部变量、
流式闭包、取消检查、校验重试和 partial record early return。当前状态隐含在方法栈中，
不利于 headless、重放、插桩和恢复。

### 6.2 目标对象

建议新增 PyQt6-free 模块：

```text
orchestrator/pipeline/
├── state.py       # PipelineState、TerminalStatus、StageUsage
├── step.py        # PipelineStep Protocol 和 StepResult
├── steps.py       # preflight/stage1/route/stage2/validate/persist
├── events.py      # 应用级 pipeline event DTO
└── builder.py     # PipelineBuilder 和默认步骤装配
```

`PipelineState` 至少包含：

- `frame`、`settings`、`cancel_token`；
- Stage 1/Stage 2 messages、raw response、normalized JSON；
- strategy files、experience entries；
- usage、attempts、exception、terminal status；
- feature flags 和 correlation id。

步骤协议建议：

```text
step.run(state, services) -> Continue(state) | Complete(record) | Fail(record)
```

取消、网络错误、校验失败和 gate short-circuit 都必须转换为明确的 terminal status，
不能通过“某个局部变量是否存在”推断阶段进度。

### 6.3 迁移步骤

1. 把现有 `_build_empty_record` 和 usage helper 包装为 state factory。
2. 把已拆出的 `_run_stage1`、`_route_and_load_experience`、`_try_gate_short_circuit`、
   `_run_stage2`、`_persist_result` 分别适配为步骤。
3. 保留 `submit()` 作为 compatibility facade，默认调用旧路径。
4. 新旧路径执行相同 fixture，比较事件序列、partial record 和最终 record。
5. 开启 Pipeline feature flag，观察至少一个完整发布周期。
6. 删除旧 submit 内部实现，只保留 facade。

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

- happy path、取消、网络错误、Stage 1/2 校验失败、gate short-circuit 和增量分析的
  最终记录与旧路径等价；
- 事件顺序和事件 payload 可快照比较；
- Pipeline 不导入 PyQt6；
- feature flag 关闭时旧 `submit()` 行为不变；
- 任一阶段出现差异可按 symbol/timeframe 或配置开关回退。

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

## 8. L5：经验库评估与版本化

### 8.1 当前实现

`ExperienceReader.read_for_stage2()` 当前顺序为：

1. 全量加载指定 cycle position 的可读案例；
2. direction 匹配和 pattern overlap 评分；
3. 用 `experience_similarity.py` 的最近 K 线几何分数打破同分；
4. timestamp 作为稳定兜底；
5. 截断到 `max_entries`。

旧案例没有 `kline_data` 时不参与相似度评分，但继续参与旧的相关性排序。

### 8.2 下一阶段前置条件

在真实经验案例不足前，不调整 body/direction/range 权重。先完成：

- 案例 schema 版本字段；
- feature extraction version；
- `success`/`failure`、symbol、timeframe、cycle、direction、patterns 的完整元数据；
- 脱敏后可用于离线测试的案例导出；
- 固定 train/evaluation 切分，避免同一结构泄漏到评估集。

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
Stage 1 prompt 等价测试，但真实两阶段 Provider runner、最终 record 等价测试和 JSONL 事件
重放仍未建立。

### 9.2 目标端口

新增 PyQt6-free 应用事件模型：

```text
util/events.py
  AppEvent(type, timestamp_ms, correlation_id, payload)

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

当前 `_build_core` 仍是私有 helper，供 GUI/headless 两条路径复用。后续建议继续公开或收口：

- `build_core(...)`
- `build_gui_adapters(...)`

两者共享 settings、client、assembler、validator、records、experience reader 和
pipeline services；只有 GUI 入口装配 Qt `EventBus`、数据源连接/订阅、MainWindow 和 Qt widgets。

### 9.4 CLI 形态

第一阶段的 CLI 已支持无网络副作用的分析辅助命令：

```text
pa-agent headless validate-config
pa-agent headless snapshot --input snapshot.json --output normalized.json
pa-agent headless analyze --input snapshot.json --output dry-run.json
```

约束：

- 默认输出结构化 JSON，不把诊断文本混入 stdout；
- 日志写 stderr 或指定日志文件；
- 当前 `analyze` 明确是 provider-free dry-run：只校验 snapshot 并构建 Stage 1 prompt 统计，
  不调用 Provider、不写入 `AnalysisRecord`，真实两阶段 runner 仍待后续切片；
- 不执行真实下单；
- 网络、API key、文件路径都从显式参数或 settings 注入；
- 退出码区分配置错误、数据错误、Provider 错误、校验错误和用户取消。

### 9.5 验收/回滚

- 在未安装 PyQt6 的 Python 环境中可以 import headless core；
- headless 与 GUI 对同一 snapshot 产生相同 Stage 1/Stage 2 record；
- 事件可以 JSON 序列化并重放；
- GUI 继续使用现有 signal 语义；
- `bootstrap_gui()` 出现问题时不影响 `bootstrap_headless()` 的单元测试。

## 10. 推荐实施顺序

### Phase 0：本规划

- 固化边界、接口、依赖和验收标准；
- 不改变业务运行路径。

### Phase 1：L1 收口

- 完成插件发现和 settings 字符串校验设计；
- 增加 registry 并发、replace、注销和 lazy import 测试；
- 不引入动态代码扫描。

### Phase 2：L6 Headless core

- 已抽象应用事件和 `EventSink`；
- 已拆分 `AppContext` core/gui bootstrap；
- 已新增 `pa_agent/cli.py` 和 `pa-agent headless` 最小 dry-run 入口；
- 已用固定 snapshot 验证 GUI/headless 共享 core 的 Stage 1 prompt 等价；
- 下一步补真实 Provider runner、最终 record 等价、JSONL sink/replay 和公开 adapter 契约。

### Phase 3：L2 Prompt engine

- 先做 TemplateStore、manifest 和 golden snapshots；
- 逐步迁移 system、Stage 1、Stage 2、continuation；
- 保持旧 PromptAssembler facade。

### Phase 4：L3 Pipeline

- 将现有方法拆分结果转成显式 state/step；
- 用 headless harness 做新旧事件和记录等价性验证；
- 最后切换默认路径。

### Phase 5：L5 数据评估

- 导出脱敏经验数据；
- 建立离线 benchmark；
- 仅在指标改善且稳定性可接受时调整线上权重。

### Phase 6：L4 预算收口

- 将基准加入 CI 或夜间任务；
- 只对有数据证明的热点继续优化；
- 形成性能回归报告。

L1、L4、L5 的收口工作可以并行，但 L6 应先于 L3；L2 可以与 L6 后半段并行，
不建议在 Pipeline 状态模型尚未稳定时进行大规模 Prompt 重写。

## 11. 测试和质量门禁

### 单元测试

- registry：匹配优先级、重复注册、replace、注销、线程安全、lazy import；
- TemplateStore：变量缺失、编码、版本、snapshot、缓存失效；
- Pipeline：每个 terminal status、取消、重试、事件序列；
- EventSink：Qt adapter、collecting sink、JSONL sink；
- L5：数据集切分、指标计算、legacy fallback。

### 集成测试

- GUI 与 headless 对同一 snapshot 的 record 等价；
- Provider/data source registry 与 AppContext 装配；
- Prompt → validator → Pipeline 的完整链路；
- 记录写入、重新加载和经验读取闭环。

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

第 229 轮已完成 L6 headless runner 的最小入口和第一条等价证据；下一轮建议转入
**L2 TemplateStore / manifest / golden snapshots**，同时保留 L6 真实 runner、最终 record 等价
和事件重放为明确的未收敛项，而不是立即调整 L5 相似度权重。
