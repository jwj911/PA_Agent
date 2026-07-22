# L1-L6 后续迭代执行计划

> 状态：短中期执行计划
> 更新时间：2026-07-22
> 适用范围：后续若干轮原子迭代
> 长期边界：以 [`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为准

本文档用于把长期架构路线图拆成短中期可执行轮次，明确下一批交付物、验收标准、
依赖关系和风险边界。长期模块边界、迁移原则、完成定义仍以
[`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为主参考；本文件不改写长期事实，
只帮助代理在已批准方向下选择下一轮工作。

## 1. 当前完成情况

| 路线 | 当前状态 | 已完成基础 | 主要剩余工作 |
|---|---|---|---|
| L1 Provider/数据源注册表 | 外部扩展兼容观察已通过，仍保留 legacy registrar | 数据源注册表、AI Provider 注册表、优先级 matcher、延迟 builder、运行时注册 API、未知数据源配置安全回退；本轮补齐 entry point 发现、registrar 契约、失败隔离、规范化、replace/unregister、并发、懒导入和 `pa-agent.registry-extension.v1` 版本观察证据 | 继续观察已安装扩展并形成 legacy registrar/版本合同的长期兼容与下线策略 |
| L2 Prompt 模板引擎 | 5 轮固定 fixture 兼容观察已通过，仍保留回滚路径 | `TemplateStore`、29 个模板 manifest、system/Stage 1/Stage 2/continuation 迁移、`TemplateContext`、严格变量渲染、golden snapshots 和整组回退；本轮重复比较 TemplateStore/旧 loader 的 system、Stage 1、Stage 2 和 continuation 输出 | 继续记录稳定周期后评估移除重复 helper、兼容开关和旧 loader |
| L3 Pipeline Builder | 受控 fixture rollout 和显式 live legacy/Pipeline 入口已建立，默认 legacy，真实观察周期未收口 | 新增 PyQt-free `PipelineState`、`TerminalStatus`、`PersistenceIntent`、`PipelineStep`、`StepResult`、`PipelineBuilder`、`Stage1Step`、`RouteStep`、`Stage2Step` 和 `PersistStep`；新增 `orchestrator.pipeline_builder_enabled`（默认 `false`）及 `pa_agent/config/orchestrator.py`；`submit()` flag-off 走原 legacy 实现，flag-on 委托完整 `Stage1Step -> RouteStep -> Stage2Step -> PersistStep` Pipeline；Task 10 终态矩阵、本轮 5 场景×3 轮对照和 live harness opt-in 均通过 | 在有凭据环境分别运行 legacy/Pipeline，完成真实稳定周期和 GUI/headless final/partial/cancel/failure evidence，之后才评估默认 flag |
| L4 性能预算 | synthetic benchmark 已接入手动/夜间预算门禁和 hosted runner baseline cache，首轮缓存仍待运行 | HTTP client 复用、forming 判定复用、K 线几何 O(n) 化、记录缓存和并发锁；新增 `pa-agent.performance.v1` runner、p50/p95 报告、100/500/5000 bars 基准、`.github/workflows/l4-benchmark.yml` 和按 iterations/warmups 分区的成功 baseline cache | 运行首轮成功 baseline，持续审核 runner image 变化并维护超过 10% 回退告警 |
| L5 经验库升级 | 评估合同、scorer 和 instrument-grouped 固定切分已交付，真实数据评估未收口 | 全量相关性排序和 K 线几何相似度已接入；新增 `pa-agent.experience-eval.v1`、`pa-agent.experience-split.v1`、`instrument-hash.v1`、dataset digest、`Recall@K`/`NDCG@K`/fallback/stability scorer，不改变线上排序 | 真实脱敏数据集、人工标注、指标报告和权重校准 |
| L6 Headless/编排 | mock 全链路等价、跨进程 replay、显式 live harness 和 artifact validator 已建立，真实环境观察未收口 | `AppEvent`、`EventSink`、`JsonlEventSink`、`replay_jsonl`、严格 `expected_correlation_id` replay、`bootstrap_headless()`、共享 `_build_core()`、`bootstrap_gui()`、兼容 `bootstrap()`、`HeadlessAnalysisAdapter`、PyQt-free `pa-agent headless`、`tools/run_live_headless_observation.py`、`tools/validate_live_observation.py`；`analyze --run/--execute` 已接入两阶段 orchestrator、record 持久化和 JSONL 事件；GUI `_AnalysisWorker` 与 headless adapter 已覆盖 final/partial/cancel/failure fixture | 在有凭据环境运行真实 Provider 稳定周期，使用 validator 审计并收集 record/event 完整等价证据 |

L6 的当前约束必须继续保持：`bootstrap_gui()` 负责 Qt `EventBus`、数据源连接和订阅；
`bootstrap_headless()` 复用 core helper，但不导入或创建 Qt `EventBus`，不连接数据源，默认使用
`NullEventSink`。

## 1.1 当前未收尾清单

以下条目是基于当前代码目录、测试入口和路线图的收尾审计；“基础完成”不等于路线已完成。

| 优先级 | 路线 | 当前阻塞项 | 收尾证据 |
|---|---|---|---|
| P0 | L6 | mock Provider/fixed fixture 下 GUI/headless final/partial/cancel/failure 等价、`pa-agent.event.v1` envelope、严格跨进程 replay、显式 live harness 和 artifact validator 已交付 | 真实 Provider 只允许显式执行；需在有凭据环境补真实运行 record/事件证据、稳定观察和 record/event 完整等价 |
| P1 | L3 | `Stage1Step`、`RouteStep`、`Stage2Step`、`PersistStep` 已拆出并由 `orchestrator.pipeline_builder_enabled` 控制；默认 `false`，flag-off 仍走 legacy；显式 live harness 可切换本次运行 | Task 10 终态矩阵及本轮 5 场景×3 轮 flag-off/flag-on 对照均通过；仍需在有凭据环境完成真实 Provider 稳定观察及 GUI/headless 真实运行 final/partial/cancel/failure evidence，之后才评估启用默认 flag |
| P1 | L5 | scorer、数据合同和 instrument-grouped 固定切分已建立，但经验目录仍无真实案例 | 真实脱敏数据集、人工标注、可重复的 `Recall@K`、`NDCG@K`、fallback rate、稳定性报告和权重校准 |
| P1 | L4 | benchmark、预算、手动/夜间 workflow 和 hosted runner baseline cache 已建立；首轮成功 baseline 尚未产生 | 运行首轮成功 baseline，审核 runner image 变化并保持同环境回归阈值和超过 10% 回退告警 |
| P2 | L1 | registry 基础、未知数据源配置回退、生命周期/并发证据、entry point 扩展契约和 5 轮外部风格样例观察已完成 | 继续观察已安装扩展并形成 legacy registrar/版本合同的长期兼容与下线策略 |
| P2 | L2 | 5 轮固定 fixture 新旧路径等价已通过，但 `use_template_store` 与旧 loader 仍需保留 | 继续稳定周期内重放并形成兼容入口下线计划 |

当前主链路为 **L6 → L3 → L5/L4**；L2 已完成实现并进入兼容观察期，L1 可独立并行治理，
但不得成为 L6/L3 主线的隐式前置条件。

## 2. 后续迭代顺序

第 232 轮已完成 **L2 Stage 1 user prompt 迁移**，第 233 轮已完成 Stage 2/continuation
和 `TemplateContext` 收尾实现。第 234 轮已完成 L6 JSONL event sink/replay 切片，第 237 轮
已交付显式执行的 headless 两阶段 runner，第 238 轮已交付 L3 state/step compatibility
adapter，Task 5 已完成 PipelineState foundation，Task 6 已完成 `Stage1Step`，Task 7 已完成
`RouteStep`，Task 8 已完成 `Stage2Step`，Task 9 已完成 `PersistStep` 真实步骤，Task 10 已完成
Pipeline flag 接线、终态矩阵和 Qt-free adapter 对照测试；本轮又完成 5 个终态场景×3 轮的
flag-off/flag-on 受控 fixture rollout 观察。默认 flag 仍关闭，后续必须完成真实 Provider
稳定观察周期和 GUI/headless 真实运行全链路最终 record 等价。

推荐顺序如下：

1. **L6：真实 Provider 环境观察、GUI/headless 运行证据和事件重放契约**。
2. **L3：Pipeline rollout 观察、旧/新路径等价验证和默认开关评估**。
3. **L5：脱敏经验数据集与离线评估基线**。
4. **L4：性能预算和持续基准**。
5. **L1 收口治理** 可以在主线空档穿插推进，但不得绕过 L6/L3 的等价证据。
6. **L2 兼容观察**：记录新旧路径运行结果，稳定一个周期后再单独评估旧 loader/helper 的下线。
7. **L1 治理观察**：registry 生命周期、replace/unregister、并发、lazy-import、entry point
   扩展契约和 5 轮外部风格样例观察已交付；后续只观察已安装扩展兼容性和 legacy registrar/
   版本合同的长期策略。

第 233 轮已经完成；当前不再重复改写 L2 prompt 文本，后续只保留兼容观察和回滚能力。

## 2.1 当前未收敛问题

以下问题已确认存在，但不在本轮 CLI 最小切片中伪装成“已完成”：

1. `pa-agent headless analyze` 默认仍只做 snapshot 校验和 Stage 1 prompt dry-run；只有显式
   `--run/--execute` 才装配真实 client 并执行两阶段 `TwoStageOrchestrator`，写入 final/partial
   `AnalysisRecord`。
2. `JsonlEventSink` / `replay_jsonl` 已提供本地 JSONL 事件写入和重放；新事件使用
   `pa-agent.event.v1` envelope，未知 schema 会拒绝，旧缺失 schema 的事件保持回放兼容；
   严格 replay 可要求整条跨进程流使用同一个 `expected_correlation_id`，并在发布前完成原子校验；
   与真实 Provider record 的完整等价协议仍待建立。
3. headless 与 GUI 已通过真实 `_AnalysisWorker`/`HeadlessAnalysisAdapter` 和固定 fixture
   验证 Stage 1/2 final、partial、cancel、failure record、milestone、prompt、流式内容和
   策略文件回调等价；真实 Provider 运行证据和稳定观察周期仍未建立。
4. `AppContext._build_core()` 仍是私有 helper；当前通过 `bootstrap_headless(client=...)` 提供
   测试注入点，`build_core` 与 `build_gui_adapters` 是否公开，需要等 CLI/GUI adapter 契约稳定后再决定。
5. L2 system、Stage 1、Stage 2/continuation、TemplateContext 和严格变量渲染已实现并保留严格
   失败回退；当前只剩旧 loader/helper 的兼容观察期。
6. L3 的四个真实步骤已具备 opt-in 等价与失败路径证据：`PersistStep` 集中 full/partial
   record assembly/write，使用 `persistence_pending` 防重复保存，成功写入后才发出 `RecordSaved`，
   并通过 `PendingWriter.last_write_succeeded` 识别磁盘失败；Task 10 已新增默认关闭的
   `orchestrator.pipeline_builder_enabled`、flag 路由、完整终态矩阵和 Qt-free adapter 对照测试，
   但真实稳定观察周期和 GUI/headless 真实运行 final/partial/cancel/failure 等价仍未收口；L6 的
   mock/fixed-fixture 等价证据已单独完成。L1 插件
   发现方案与正式扩展契约、L5 脱敏评估合同/scorer/固定切分已建立；L4 已有 p50/p95 budget gate，
   但同环境 baseline/10% regression 仍未收口，不能仅依据当前测试宣称全部收敛；L2 只剩兼容
   观察期。

## 2.2 第 233 轮完成结果（L2 Stage 2/continuation 与 TemplateContext）

### 目标与结果

在不重写中文策略文本、不改变路由和 JSON 输出契约的前提下，Stage 2 user prompt 和
continuation 的静态 `.txt` 模板读取已切换到现有 `TemplateStore` compatibility adapter；
L1 已完成第二阶段基础，未作为本轮前置条件。

### 已交付

1. 扩展 `pa_agent/ai/prompting/compatibility.py`，为 Stage 2 模板提供按组严格加载、
   `stage="stage2"` 校验和整组 legacy fallback，禁止新旧模板部分混用。
2. 将 loader 注入 `Stage2PromptBuilder` / `PromptAssembler`，覆盖 standalone Stage 2
   和 prefix-chain continuation 两条路径。
3. 为 system、Stage 2 user prompt 和 continuation 建立固定 fixture 的旧/新字节等价快照；
   保留 `use_template_store=False` 显式回滚。
4. 补齐缺失文件、空文件、非法 UTF-8、错误阶段和加载异常的 warning/fallback 测试，
   并复核 Stage 1 已有路径不回退。
5. 新增 `TemplateContext` 和严格 `$name`/`${name}` 变量渲染；缺变量、语法错误和非 mapping
   context 均显式失败，不执行任意 Python。
6. 同步 `docs/CHANGELOG.md`、`AGENTS.md`、CI 目标清单和本执行计划，完成目标 pytest、
   focused Ruff、py_compile 和 golden snapshot 检查。

### 明确不做

- 本轮不引入 Jinja2；使用标准库严格替换已满足当前静态 prompt 的变量合同，未来如需更复杂
  模板语法必须另开迁移切片。
- 不修改 prompt 中文内容、策略文件顺序、Provider 路由、JSON schema、normalizer 或
  `TwoStageOrchestrator`。
- 不在同一提交实现 L1 插件发现、动态代码扫描或 Provider token 同步迁移。

### 验收标准

- 固定 fixture 下 `use_template_store=True/False` 的 Stage 2 system/user/continuation
  messages 字节完全一致；任何差异必须有可审查的 snapshot diff。
- 任一 Stage 2 模板组加载失败时，整组回退旧 `_load()`，并留下明确 warning；显式关闭
  feature flag 时完全走旧路径。
- Stage 1、KV prefix、策略路由和输出契约回归测试通过；模板模块保持 PyQt-free。
- 本轮完成后，下一主线转入 L6 真实 Provider runner、JSONL event sink/replay 和最终
  record 等价测试。

### L2 收尾状态

L2 的实现切片已完成，`use_template_store=False` 和旧 loader 继续保留作为兼容回滚路径。
在稳定周期结束前，不删除重复 helper、不改变 prompt 中文文本，也不关闭 feature flag。
L1 的 matcher/builder/settings 注入/线程安全/注销时机契约和 registry 生命周期测试可在独立
提交中并行推进。

## 2.3 第 234 轮完成结果（L6 JSONL event sink/replay）

### 已交付

1. 新增 PyQt-free `JsonlEventSink`，按一行一个 JSON event 写入并在每次 publish 后 flush。
2. 新增 `event_to_dict` / `event_from_dict` 和 `replay_jsonl`，对事件 envelope、时间戳、
   correlation id、payload 类型和坏行提供明确校验错误。
3. 支持 `require_correlation_id=True`，为后续跨进程 runner 契约保留严格模式；默认不改变
   既有 `AppEvent` 可选 correlation id 行为。
4. 补充写入、重放、关闭 sink、缺失 correlation id 和损坏 JSONL 行测试，并保持 PyQt-free。

### 收尾边界

本轮只建立事件持久化/重放端口，不调用 Provider、不改变 GUI signal 语义，也不宣称 headless
两阶段分析已完成。下一轮继续实现真实 Provider runner，并使用本轮 JSONL 端口验证最终/partial
record、取消和失败事件等价。

## 2.4 第 235 轮完成结果（L1 未知配置安全回退）

### 已交付

1. `GeneralSettings.last_data_source` 对未知、空值和非字符串配置安全回退到 `mt5`；
   既有 `yfinance`、`adata`、`a_share` 兼容迁移保持不变。
2. 回退时记录不含密钥或行情数据的 warning，并在 `load_settings()` 后持久化规范化值，
   避免每次启动重复遇到同一未知配置。
3. 新增 settings round-trip 回归测试，验证未知值不会阻塞配置加载且磁盘值被规范化。

### 收尾边界

本轮不引入任意目录扫描、Provider token 同步或网络探测；entry point registrar 只负责向目标
registry 注册规格，registry 并发和 builder 锁外执行边界保持不变。

## 2.5 第 236 轮完成结果（L1 注册表治理）

### 已交付

1. `DataSourceRegistry` 与 `AIClientRegistry` 的 key/name 规范化行为已集中覆盖：注册、查询、
   注销均按去除首尾空白后的 canonical key 工作，保持大小写和既有路由语义不变。
2. 补充重复注册拒绝、`replace=True` 替换、注销返回值和幂等行为测试，覆盖数据源工厂与 AI
   client factory 的运行时扩展入口。
3. 补充 AI route priority 与同优先级稳定顺序测试、数据源 registry 并发注册/读取/注销测试，
   以及 concrete client 不因 import registry 而提前加载的 lazy-import 检查。

### 收尾边界

本轮不引入 Python entry points、任意目录扫描、动态代码执行、Provider token 同步或网络探测；
builder 仍由现有 factory 在 registry 锁外调用。下一 L1 切片聚焦插件发现方案和 matcher、
builder、settings 注入、线程安全及注销时机的正式开发者契约。

### 验证

- `tests/unit/test_registry.py`、`tests/unit/test_data_source_factory.py`、
  `tests/unit/test_client_factory.py` → **21 passed**。
- 受影响模块 focused Ruff、`scripts/check_ci_workflow_targets.py`、
  `scripts/check_ruff_baseline.py` 和 `git diff --check` → **通过**。

## 2.5.1 本轮完成结果（L1 扩展契约与 entry point 发现）

1. 新增 `pa_agent/extensions.py`，固定 `pa_agent.data_sources` 和 `pa_agent.ai_clients`
   两个 entry point group，以及 callable registrar contract。
2. 数据源与 AI client factory 在内置规格之后执行确定性排序的 entry point discovery；外部
   扩展失败只产生分类日志和结果，不阻断内置规格。
3. discovery、registrar 和 builder 均在 registry 锁外执行；不扫描任意目录，不负责 token
   同步、网络探测、`save_settings()` 或运行时连接。
4. 新增 entry point 排序、失败隔离、metadata API 兼容和安全日志测试，纳入 targeted pytest
   与 focused Ruff。

验证：extension/registry/factory focused tests **24 passed**；Ruff、`py_compile` 和
`git diff --check` 通过。L1 进入外部扩展兼容观察期。

## 2.5.2 本轮完成结果（L1 外部扩展兼容观察）

### 已交付

1. `pa_agent.extensions` 固定 `EXTENSION_CONTRACT_VERSION =
   "pa-agent.registry-extension.v1"` 和可选的
   `__pa_agent_extension_version__` registrar 声明；未声明版本的旧 callable 继续兼容。
2. 不匹配的显式版本在当前扩展边界内抛出 `ExtensionContractError` 并被 discovery 隔离；
   其他扩展、内置 registry 和原有 entry point group 不受影响。
3. 新增外部风格 data source/AI client registrar 5 轮重复观察，覆盖 versioned/legacy
   registrar、settings 注入、matcher、builder 和结果合同版本。
4. 将 `tests/integration/test_l1_extension_compatibility_observation.py` 纳入 CI targeted
   pytest，继续禁止任意目录扫描、网络探测、token 同步和真实 Provider 调用。

### 收尾边界

本轮证明固定无敏感数据样例下的 versioned/legacy 扩展兼容，不删除旧 registrar 入口；仍需
在真实已安装扩展集合上观察发布版本策略，再决定 legacy registrar 和版本合同的长期下线计划。

### 验证

- L1 extension 单测和兼容观察 → **通过**。
- Ruff、Ruff format、`py_compile`、CI target 和 `git diff --check` → **通过**。

## 2.6 第 237 轮完成结果（L6 headless 两阶段 runner）

### 已交付

1. `pa-agent headless analyze` 保持默认 provider-free dry-run；新增显式 `--run/--execute` 开关，
   避免脚本或误调用隐式触发网络请求。
2. `AppContext.bootstrap_headless(client=...)` 支持 fake client 注入，runner 复用现有
   `TwoStageOrchestrator`、校验重试、gate short-circuit 和 `PendingWriter`，不创建 Qt `EventBus`
   或连接数据源。
3. `--records-dir` 持久化 final/partial record，按现有记录 schema 写入；network、validation、
   insufficient-data、cancelled 等终态映射到稳定 CLI 退出码，stdout 只输出结构化摘要并排除
   `raw_text`。
4. `--events` 将 orchestrator milestone 以带 correlation id 的 `AppEvent` 写入 JSONL；事件端口
   仍可通过既有 `replay_jsonl` 重放。
5. 新增 fake Provider final/partial 测试、headless client 注入测试和事件/record 输出断言，不依赖
   live network。

### 收尾边界

本轮只提供显式执行的 headless adapter 第一切片；未宣称 GUI/headless 最终、partial、取消和失败
记录的全链路等价，也未将 CLI adapter 提升为稳定公共 API。真实 Provider 运行仍需用户明确传入
`--run`，测试与 CI 继续使用 fake client。

### 验证

- `tests/unit/test_cli.py`、`tests/unit/test_event_sink.py`、`tests/unit/test_app_context_headless.py`
  → **21 passed**。
- 受影响模块 focused Ruff、`scripts/check_ci_workflow_targets.py`、
  `scripts/check_ruff_baseline.py` 和 `git diff --check` → **通过**。

## 2.7 第 238 轮完成结果（L3 Pipeline state/step 第一切片）

### 已交付

1. 新增 PyQt-free `orchestrator/pipeline/` 包，定义 `PipelineState`、`TerminalStatus`、
   `PipelineStep`、`StepOutcome`、`StepResult` 和 `PipelineBuilder`。
2. `terminal_status_for()` 将 legacy `OrchestratorEvent`/`AnalysisRecord.exception` 映射为
   `completed`、`cancelled`、`insufficient_data`、`stage1_failed`、`stage2_failed` 和 `failed`
   等显式终态。
3. `TwoStageOrchestrator.run_pipeline()` 以 `LegacySubmitStep` 包装当前稳定的 `submit()`；
   `submit_pipeline()` 返回兼容的 `AnalysisRecord`。默认 GUI/headless 仍调用旧 `submit()`。
4. 新增 Pipeline builder 单测，以及 legacy/opt-in path 的 final record、事件序列和取消终态等价测试。
5. 新增 Pipeline 模块和测试到 CI targeted pytest/focused Ruff 清单，保持模块不导入 PyQt6。

### 收尾边界

本轮只建立显式状态/步骤协议和兼容适配器，没有拆动 Stage 1、route、Stage 2、persist 的内部实现，
也没有切换默认路径。下一切片再将现有辅助方法逐步替换为真实步骤，并补全网络错误、校验失败、
gate short-circuit、增量分析和 GUI/headless 等价证据。

### 验证

- L3 协议、等价和既有终态测试 → **15 passed**。
- Pipeline focused Ruff、py_compile、CI workflow target、Ruff baseline 和 `git diff --check` → **通过**。

## 2.8 本轮完成结果（L3 Task 5：PipelineState foundation）

### 已交付

1. 扩展 PyQt-free `PipelineState`，显式承载 Stage 1/Stage 2 messages、reply/raw response
   引用、normalized JSON、usage/usage calls、strategy files、experience entries 和 route
   outputs；`LegacySubmitStep` 会在未改变的 legacy `submit()` 返回后回填这些状态。
2. 新增 `PersistenceIntent`（`none`/`full`/`partial`）和 `partial_reason`，让完成与非完成
   终态分别表达 full/partial 持久化意图；不修改 `AnalysisRecord` schema。
3. 扩展 `terminal_status_for()` 的 mapping：兼容 `route`/`routing` 与 `persist`/`persistence`
   stage/type/reason，并输出稳定的 `route_failed`、`persist_failed` 终态。
4. 增加 `safe_summary()`/`to_safe_json()`：只保留阶段形状、消息角色、route 数量、usage
   计数、稳定终态和 allowlist metadata；不序列化 callbacks、Provider client、prompt/reply
   正文、normalized JSON 值、行情数据或密钥。usage 支持 mapping/对象读取；`base_url` 只保留
   `http`/`https` origin，移除凭据、path、query 和 fragment。
5. 保持 `TwoStageOrchestrator.submit()` 及 GUI/headless 默认调用路径不变；Pipeline adapter
   仍为 opt-in，兼容 facade 和安全边界继续有效。

### 明确未实现

- Stage 1、Route、Stage 2、Persist 的真实 `PipelineStep` 尚未从 legacy wrapper 中拆出；
- 对应的 retry、网络/校验失败、gate short-circuit、取消、增量分析和 final/partial 记录的
  完整旧/新事件与记录等价尚未收口；
- Pipeline feature flag 尚未切换，默认路径仍是旧 `submit()`。

### 证据与边界

- `tests/unit/test_pipeline.py` 已补充阶段/route/persistence state、route/persist 终态映射、
  safe summary、Provider client/callback/prompt/行情数据/密钥排除和 URL path 脱敏覆盖。
- 本轮只扩展状态承载和摘要边界，不改变 prompt 文本、JSON schema、normalizer、retry 语义、
  `AnalysisRecord` schema 或持久化实现。

## 2.9 本轮完成结果（L3 Task 6：Stage1Step 真实步骤）

### 已交付

1. 新增真实 PyQt-free `Stage1Step`，复用现有 Stage 1 构建、Provider 调用、校验/重试和
   preflight 语义，并把 Stage 1 messages、reply、normalized JSON、usage、usage calls、
   thinking 和 reasoning effort 回填到 `PipelineState`。
2. `run_pipeline()` 的 opt-in sequence 固定为
   `Stage1Step -> legacy_post_stage1`；`legacy_post_stage1` 在迁移完成前继续承接
   Route、Stage 2 和 Persist 兼容尾步骤。
3. 保留 `TwoStageOrchestrator.submit()` 及 GUI/headless 默认调用路径；本轮没有切换
   Pipeline feature flag，也没有改变默认旧 `submit()` 路径。
4. 新增 `tests/integration/test_stage1_pipeline_step.py`，覆盖 happy、retry、network、
   validation、cancel 和 incremental 路径；更新 `test_two_stage_pipeline_equivalence.py`
   验证旧/新最终 record、事件序列和步骤顺序等价。
5. 将 Stage 1 集成测试加入 CI targeted pytest 与 focused Ruff 目标清单，继续保持
   Pipeline 模块不导入 PyQt6。

### 明确未实现

- Route、Stage 2、Persist 尚未拆为独立真实 `PipelineStep`，仍由 `legacy_post_stage1`
  兼容尾步骤执行。
- Pipeline 默认路径、`submit()` facade、`AnalysisRecord` schema、prompt 文本、normalizer
  和既有 retry 语义均未切换或改写。
- L3 的完整终态、GUI/headless 全链路 record 等价和 feature flag 观察周期仍待收口。

### 证据与边界

- Stage 1 集成测试覆盖状态快照、回调、usage、校验重试、网络失败、校验失败、取消、增量
  prompt context，以及旧/新最终 record 和事件等价。
- 本轮只推进 Stage 1 步骤化，不将 Route/Stage 2/Persist 兼容尾步骤误标为真实步骤。

## 2.10 本轮完成结果（L3 Task 7：RouteStep 真实步骤）

### 已交付

1. 新增真实 PyQt-free `RouteStep`，复用现有 `_route_and_load_experience` 的路由和经验加载
   语义，把 `strategy_files`、`experience_entries` 和 route outputs 写入 `PipelineState`。
2. `run_pipeline()` 的 opt-in sequence 固定为
   `Stage1Step -> RouteStep -> legacy_stage2_persist`；`legacy_stage2_persist` 仍由兼容尾步骤
   承接 Stage 2 和 Persist，默认 `submit()` 路径不变。
3. RouteStep 保持 callable router 与带 `.route()` 的 object router，保留策略文件返回顺序；
   经验加载继续使用 settings 中的数量/字符限制，透传 `current_bars`，空经验库保持为空。
4. 保持 Stage 2 前取消边界：route 返回后若已取消则只保存 `user_cancelled` partial record，
   发出 `Cancelled`，不发出 `Stage2Started`，也不调用 Stage 2 Provider。
5. Route/experience 异常映射为 `TerminalStatus.ROUTE_FAILED`、`partial_reason="route_failed"`、
   `PersistenceIntent.PARTIAL`，保存 `route_failed` partial record，并在 record exception 中保留
   `route_error` 的稳定 stage/type/message 结构。
6. 新增 `tests/integration/test_route_pipeline_step.py`，覆盖 callable/object router、策略文件
   顺序、经验数量/字符限制、`current_bars`、空经验库、Stage 2 前取消和 `route_failed`；
   更新 `tests/integration/test_two_stage_pipeline_equivalence.py`，断言新旧最终 record/事件
   等价及 `["stage1", "route", "legacy_stage2_persist"]` 步骤顺序。
7. 将 `test_route_pipeline_step.py` 同步加入 CI targeted pytest 与 focused Ruff/Black 目标清单；
   Pipeline 目录继续保持 PyQt-free。

### 明确未实现

- Stage 2、Persist 尚未拆为独立真实 `PipelineStep`，仍由 `legacy_stage2_persist` 执行。
- Pipeline 默认路径、`submit()` facade、`AnalysisRecord` schema、prompt 文本、normalizer 和
  既有 retry 语义均未切换或改写。
- L3 完整终态、GUI/headless 全链路 record 等价和 feature flag 观察周期仍待收口。

### 证据与边界

- RouteStep 只推进 Stage 1 后的路由/经验边界，不改变 Stage 2 prompt、JSON schema、normalizer、
  Persist 实现或默认旧路径。
- Route failure 只对 opt-in RouteStep 增加显式 `route_failed` partial 映射；旧 `submit()` 仍
  直接保持既有调用语义。

## 2.11 本轮完成结果（L3 Task 8：Stage2Step 真实步骤）

### 已交付

1. 新增真实 PyQt-free `Stage2Step`，复用既有 continuation message 构建、Stage 2 Provider 调用、
   流式回调、校验/retry 和终态映射；Stage 2 payload、usage/usage calls 和归一化 JSON 写入
   `PipelineState`。
2. `run_pipeline()` 的 opt-in sequence 固定为
   `Stage1Step -> RouteStep -> Stage2Step -> legacy_persist`；`Stage2Step` 通过
   `persist=False` 只组装结果，`legacy_persist` 再承接写入边界。
3. settings 派生的 `enable_next_bar_prediction` 与 `structure_flip_cooldown_bars` 写入 state
   和安全 feature metadata；continuation prompt 的旧/新调用参数与 UTF-8 字节内容保持等价。
4. 保持 `Stage2Started`、gate short-circuit、reasoning/content 流式回调、retry、network failure、
   validation failure 和 post-call cancel 语义；Stage 2 partial 分支不进入 full persist。
5. 新增 `tests/integration/test_stage2_pipeline_step.py`，覆盖 continuation/flags、事件顺序和
   state payload、流式回调、gate short-circuit、retry、network failure、validation failure、
   post-call cancel，以及 partial record 与 legacy `submit()` 的等价；更新最终 record/event
   equivalence 的步骤顺序断言。
6. 将 Stage 2 集成测试加入 CI targeted pytest、focused Ruff 和 focused Black 目标清单；
   Pipeline 模块继续保持 PyQt-free。

### 明确未实现

- `PersistStep` 尚未实现。当前 `legacy_persist` 只承接已经由 Stage 2/既有 helper 组装完成的
  full/partial 写入边界：成功结果走 `save_full`，Stage 2 网络/校验/取消等 partial 分支仍由
  现有 legacy helper 处理 `save_partial`；它不负责独立的 record 组装、partial reason 策略、
  磁盘错误处理或新的持久化契约。
- Pipeline 默认路径、`submit()` facade、`AnalysisRecord` schema、prompt 文本、normalizer 和
  既有 retry 语义均未切换或改写；feature flag 仍处于观察前状态。
- 完整 Persist 终态矩阵、GUI/headless 全链路 record 等价和 feature flag 观察周期仍待 Task 9/10。

### 证据与边界

- Stage 2 只推进准备/执行边界，不把 `legacy_persist` 宣称为真实 `PersistStep`，也不改变
  JSON schema、normalizer、记录格式或默认旧 `submit()` 路径。
- 本轮文档同步只运行 `git diff --check`；未运行 pytest，代码测试清单以工作区测试和 CI 配置为准。

## 2.12 本轮完成结果（L3 Task 9：PersistStep 真实步骤）

### 已交付

1. 新增真实 PyQt-free `PersistStep`，由 opt-in pipeline 独立负责终态 record assembly 与
   `PendingWriter` 写入；不修改 `AnalysisRecord` schema 或旧 `submit()` facade。
2. `run_pipeline()` 的 opt-in sequence 固定为
   `Stage1Step -> RouteStep -> Stage2Step -> PersistStep`。Stage 1/Route/Stage 2 的失败、
   取消和 insufficient-data 终态设置 `persistence_pending`，`PipelineBuilder` 仍会执行一次
   PersistStep，避免前置步骤直接保存后再次写入。
3. full record assembly 从 `PipelineState` 汇总 Stage 1/Stage 2 messages、raw response、
   normalized JSON、strategy files、experience entries 和 usage；成功写入后先清除 pending，
   再发出 `RecordSaved`，最后标记 completed。
4. partial record assembly 保留已有 `partial_reason` 和已完成阶段 payload，统一调用
   `save_partial`；partial 写入不发出 `RecordSaved`。full 写入异常或
   `PendingWriter.last_write_succeeded` 为 false 时映射为 `persist_failed`/`disk_error`；
   partial 写入失败则保留原终态并设置 `persistence_error`，两者都不伪造成功事件。
5. `PendingWriter` 的 `_write_json()` 返回写入结果，并暴露 `last_write_succeeded`，保持磁盘
   错误日志和事件通知仍由 writer 负责；旧 writer/fake writer 未提供该属性时保留兼容回退。
6. 新增 PersistStep 集成覆盖，验证 full/partial/insufficient-data、`RecordSaved` 顺序、磁盘
   失败、`persistence_pending` 防重复保存，以及与旧路径的记录/事件边界。

### 收尾边界

- 四个真实步骤已经齐备，但 Pipeline feature flag 仍未切换，尚未完成至少一个完整稳定观察周期。
- GUI/headless final、partial、cancel、failure 的全链路等价仍未收口；默认
  `TwoStageOrchestrator.submit()` 和 GUI/headless 默认调用路径继续保持旧兼容行为。

## 2.13 本轮完成结果（L3 Task 10：rollout 观察与切换准备）

### 已交付

1. 新增 PyQt-free `pa_agent/config/orchestrator.py`，定义
   `orchestrator.pipeline_builder_enabled`；默认值为 `false`。
2. `Settings` round-trip 已覆盖 flag 持久化；没有 `orchestrator` section 的旧配置自动采用
   `false`，继续走 legacy 路径。
3. `TwoStageOrchestrator.submit()` 保持原 facade：flag-off 委托原 legacy `submit()` 实现，
   flag-on 委托 `submit_pipeline()`，执行完整
   `Stage1Step -> RouteStep -> Stage2Step -> PersistStep` Pipeline。
4. 新增完整终态矩阵测试，覆盖 happy/completed、preflight insufficient-data、cancel、
   Stage 1 network/validation failure、Route failure/Route cancel、Stage 2 gate/network/
   validation/cancel，以及 full/partial persist disk failure；每个 fixture 都断言终态、
   partial reason、step history、事件序列和唯一一次 PersistStep 写入边界。
5. 新增 Qt-free headless/GUI adapter equivalence 测试，比较 flag-off legacy、flag-on adapter
   和 direct Pipeline 的规范化 record、events、stage prompts、流式 content，并确认完整四步
   顺序；不导入或创建 Qt。
6. 将 `tests/integration/test_task10_pipeline_rollout.py` 加入 CI targeted pytest，将
   `pa_agent/config/orchestrator.py` 加入 focused Ruff/config target。

### 明确边界

- 本轮只完成 rollout 观察与默认切换准备；`pipeline_builder_enabled` 默认仍为 `false`，
  不宣称已完成默认路径切换。
- 现有测试提供 mock/fixture 下的矩阵和 Qt-free adapter 证据；后续仍需真实稳定观察周期，
  以及 GUI/headless final、partial、cancel、failure 全链路 evidence，确认无未解释偏差后才
  评估启用默认 flag。
- 不修改 prompt 文本、JSON schema、normalizer、retry 语义、`AnalysisRecord` schema 或
  `.trae/specs` 状态。

### 本轮验证边界

- 本轮代理操作只更新项目文档，不修改业务代码或 `.trae/specs` 状态，不提交、不推送；
  仅运行 `git diff --check`，未运行 pytest。

## 2.14 本轮完成结果（L3 Task 11：Pipeline enabled lifecycle logging）

### 日志字段与查询

Pipeline enabled 路径使用同一 `trace_id` 关联一次执行，事件名分为
`pipeline.lifecycle`（builder 生命周期）、`pipeline.event`（编排事件）和
`pipeline.step`（步骤结果）。结构化字段包括 `trace_id`、`pipeline_event`、
`pipeline_step`、终态/结果分类、异常类型分类、耗时、跳过原因、写入类型/状态和
`safe_summary`；可按 `trace_id` 聚合，也可按 `pipeline.lifecycle`、`pipeline.event`、
`pipeline.step` 过滤，再按 `pipeline_step` 重建
`Preflight -> Stage1 -> Route -> Stage2 -> Persist` 顺序。

### 已交付与边界

- Pipeline enabled 时记录各阶段开始、结果、跳过、终态、结束及编排事件；retry、网络错误、
  校验失败、gate short-circuit、取消和持久化失败使用稳定的事件/状态/异常类型分类。
- 日志字段使用显式 allowlist 和 `PipelineState.safe_summary()`；不记录原始行情、股票/合约
  代码、价格、prompt 或 Provider 原文、API Key、Provider Token、callbacks 或 client 对象。
- `orchestrator.pipeline_builder_enabled` 默认仍为 `false`；flag-off 继续走 legacy
  `submit()`，事件顺序、retry/cancel 语义和 final/partial record 不变。
- 当前日志只提供 opt-in 诊断证据，不等同于生产稳定观察。启用默认 flag 前仍需真实稳定观察
  周期，以及 GUI/headless final、partial、cancel、failure 全链路 evidence。

### 验证

- 生命周期/日志安全聚焦测试 → **80 passed**；Ruff、受影响模块 `py_compile` 和
  `git diff --check` → **通过**。
- 本轮已同步 Pipeline logging 业务代码、聚焦测试和项目文档/规格；验证通过并按流程纳入原子提交/推送。

## 2.15 本目标四条任务的收口审计

本目标要求的四条实现主线已分别完成其“实现切片”：

1. **L1 注册表治理**：registry 生命周期治理、entry point discovery、registrar 契约、失败
   隔离和锁外执行均已有代码与测试证据；进入外部扩展兼容观察期。
2. **L2 模板迁移实现**：TemplateStore、TemplateContext、严格渲染、system/Stage 1/Stage 2/
   continuation 迁移和 golden snapshot 已通过兼容回归；旧 loader 和 `use_template_store=False`
   继续作为观察期回滚路径。
3. **L6 headless 第一切片**：`bootstrap_headless()`、显式 runner、JSONL sink/replay 和公开
   `HeadlessAnalysisAdapter` 已交付；全链路 GUI/headless 等价和真实 Provider 验证仍是 L6 后续收口。
4. **L3 Pipeline**：Stage1/Route/Stage2/Persist 四个真实 steps、rollout flag、终态矩阵和
   lifecycle logging 已交付；默认 flag 仍关闭，真实稳定观察周期和全链路等价仍是 L3 后续收口。

本节的“收口”仅表示四条实现切片完成，不把尚未取得真实环境证据的观察项标记为完成。

### 本目标验证

- L1 extension/registry/factory focused tests：`24 passed`
- L2 TemplateStore/TemplateContext/PromptAssembler/golden tests：`59 passed`
- L6 headless/AppContext/CLI/event tests：`30 passed`
- L3 Pipeline/终态/生命周期日志 tests：`68 passed`
- 受影响模块 Ruff、py_compile、CI target、Ruff baseline 和 git diff 检查通过

## 2.16 本轮完成结果（L3 Pipeline 阶段边界耗时统计）

Pipeline enabled 路径新增 `pipeline.timing` 事件：

- 每个 `stage1`、`route`、`stage2`、`persist` 步骤记录
  `pipeline_step_elapsed_ms`、`pipeline_stage_elapsed_ms`、累计
  `pipeline_elapsed_ms` 和完成步骤数；
- Stage 2 开始前记录 `stage1_to_stage2` 边界，并携带 Stage 1 与 Route 已完成耗时；
- 所有时间来自 `time.monotonic()`，与 `trace_id` 关联，日志字段不包含 prompt、reply、行情
  或 Provider 原文；
- 该日志用于观察 full/partial/cancel/failure 的时序和 adapter 等价性，不代表真实生产
  稳定观察已经完成，默认 Pipeline flag 继续关闭。

验证：Pipeline focused tests **69 passed**；Ruff、`py_compile`、Ruff baseline、CI target 和
`git diff --check` 通过。

## 2.17 本轮完成结果（L6：GUI/headless 全链路等价证据与事件 envelope v1）

本轮在不调用真实 Provider、不开启 Pipeline 默认开关的前提下，补齐 L6 的固定 fixture
全链路证据：

- 扩展公开 `HeadlessAnalysisAdapter.run()` 的可选回调边界，使其与 GUI `_AnalysisWorker`
  对齐 Stage 1/Stage 2 prompt、reasoning、content 和策略文件观察；
- 新增真实 GUI worker 与 headless adapter 对照测试，覆盖 final、partial、cancel、failure
  四类终态，并比较 record、milestone/status、prompt、流式内容、策略文件和 partial persistence；
- JSONL 新事件写入 `schema: "pa-agent.event.v1"`；未知 schema 明确拒绝，历史缺失 schema
  的 envelope 保持回放兼容；
- 将等价测试加入 CI targeted pytest。

验证：L6/既有 Pipeline focused pytest 通过；受影响模块 Ruff、`py_compile`、Ruff baseline、
CI target 和 `git diff --check` 通过。

收尾边界：真实 Provider 环境稳定观察、真实运行 record/事件证据和跨进程 correlation 重放
仍未完成；在不冒充真实环境证据的前提下，后续先进入 L3 受控 rollout，L6 真实环境观察
作为独立收口项保留。

## 2.18 本轮完成结果（L3：flag-off/flag-on 受控 rollout 观察）

本轮在默认 `orchestrator.pipeline_builder_enabled=false` 保持不变的前提下，建立可重复的
受控 rollout 观察：

- 新增 `tests/integration/test_l3_rollout_observation.py`；
- 使用 final、Stage 1 network failure、Stage 2 network failure、cancel、Stage 1 validation
  五个终态场景；
- 每个场景重复 3 轮，分别执行 flag-off legacy `submit()` 和 flag-on 四步 Pipeline；
- 对照最终 record、`OrchestratorEvent` 顺序、Stage prompt、reasoning/content、策略文件和
  full/partial writer 边界；
- 将观察测试纳入 CI targeted pytest，作为后续真实 Provider rollout 的固定回归基线。

验证：5 个场景 × 3 轮全部通过；Ruff、`py_compile`、CI target 和 `git diff --check` 通过。

收尾边界：本轮只证明固定 fixture 下的受控稳定性，不等价于真实 Provider 生产观察；真实
稳定周期、GUI/headless 真实运行终态证据和默认 flag 切换仍未完成。

## 2.19 本轮完成结果（L5：脱敏经验评估合同与离线 scorer）

本轮只建立离线评估能力，不读取当前空经验目录中的真实案例，也不修改线上排序权重：

- 新增 `pa_agent.records.experience_eval`，定义 `pa-agent.experience-eval.v1` dataset envelope
  和 `kline-geometry.v1` feature version；
- 评估案例只允许 opaque instrument id、timeframe、cycle、direction、patterns、候选数量和
  人工标注的相关案例 id，不包含价格、K 线原文、截图路径、密钥或本地绝对路径；
- 新增 `dump_dataset()` / `load_dataset()` 的 schema 校验和
  `evaluate_rankings()`，输出宏平均 `Recall@K`、`NDCG@K`、similarity fallback rate、
  top-K ranking stability 和 score distribution；
- 新增固定脱敏 fixture 单测，验证 dataset round-trip、未知 schema 拒绝、指标计算和空集边界。

验证：`test_experience_eval.py` 与既有 `test_experience_reader.py` 全部通过；Ruff 和
`py_compile` 通过。

收尾边界：经验目录仍只有占位文件，当前指标只能证明 scorer 正确性；真实脱敏数据集、
固定 train/evaluation 切分、人工标注和权重校准仍未完成。

## 2.20 本轮完成结果（L4：固定 synthetic benchmark 与 p50/p95 预算）

本轮不修改热路径实现，只建立可重复的性能证据：

- 新增 `pa_agent.perf.benchmark`，定义 `pa-agent.performance.v1` report、p50/p95 计算、
  p95 budget 和 baseline regression（超过 10% 判定失败）；
- 新增 `tools/run_l4_benchmark.py`，固定 snapshot build、indicator 和 K-line geometry 的
  100/500/5000 bars synthetic suite，支持 `--iterations`、`--warmups`、`--output` 和
  `--baseline`；
- 当前报告写入 `docs/benchmarks/l4_synthetic_2026-07-22.json`，9 个基准在 30 次采样、
  5 次预热下全部通过 p95 预算；
- 新增 benchmark contract 单测，纳入 CI targeted pytest 和 focused Ruff/format targets。

验证：benchmark 单测、经验库相关回归、Ruff、Ruff format、`py_compile`、CI target 和
`git diff --check` 通过。当前本机 Black 26.5 单文件检查无输出挂起，已由 Ruff format 作为
本地格式证据；CI 锁定依赖仍需由 GitHub Actions 验证。

收尾边界：当前报告是固定环境基线，不代表跨机器性能结论；CI/夜间持续回归和同环境基线维护
仍未完成。

## 2.21 本轮完成结果（L2：TemplateStore/旧 loader 兼容观察）

本轮不修改任何中文 Prompt 文本和模板 manifest，只重复验证迁移回滚边界：

- 新增 `tests/integration/test_l2_template_compatibility_observation.py`；
- 固定 `prompt_golden.json` Stage 2 fixture，连续 5 轮比较 TemplateStore 开启与
  `use_template_store=False` 旧 loader；
- 覆盖 shared system、Stage 1、Stage 2 standalone、continuation standalone 和
  prefix-chain，并额外比较 conservative/balanced decision stance；
- 将兼容观察测试纳入 CI targeted pytest，旧 loader 继续作为显式回滚路径。

验证：L2 兼容观察、TemplateStore、TemplateContext 测试全部通过；Ruff、`py_compile`、CI
target 和 `git diff --check` 通过。

收尾边界：本轮只证明固定 fixture 下 5 轮稳定等价，不代表旧 helper/loader 可以立即删除；
仍需完整稳定周期和兼容入口下线计划。

## 2.22 本轮完成结果（L6：跨进程 correlation replay 契约）

本轮不调用真实 Provider，只收口 JSONL event stream 的跨进程重放边界：

- `replay_jsonl()` 新增可选 `expected_correlation_id` 和 `require_correlation_id` 严格模式；
- 严格模式先完成 schema、类型、非空 correlation 和期望 ID 全文件校验，再向 sink 发布；
- 新增 `tests/integration/test_l6_event_replay_contract.py`，由独立 Python 子进程读取父进程
  写入的 `pa-agent.event.v1` stream，比较 event 顺序和 correlation id；
- 默认 replay 仍兼容历史缺失 schema/缺失 correlation id 事件，并将测试纳入 CI targeted
  pytest/focused Ruff。

验证：event sink、CLI、headless 和跨进程 replay 测试共 **22 passed**；Ruff、Ruff format、
`py_compile`、CI target 和 `git diff --check` 通过。

收尾边界：本轮证明 event replay contract，不代表真实 Provider record/事件落盘和稳定运行
观察已经完成。

## 2.23 本轮完成结果（L4：synthetic benchmark 持续回归接线）

本轮不修改性能热路径，只把既有固定 suite 接入可重复的 GitHub Actions 预算门禁：

- 新增 `.github/workflows/l4-benchmark.yml`，支持 `workflow_dispatch` 和每日 schedule；
- 固定 Windows/Python 3.12.9，运行 snapshot、indicator、K-line geometry 的 100/500/5000 bars
  suite；p95 超过预算时 workflow 失败；
- 无论成功或失败上传 `pa-agent.performance.v1` JSON 报告 artifact，保留 30 天；
- 手动运行可覆盖 iterations/warmups；`--baseline` 仍保留给同环境 baseline 维护后的回退比较。

验证：benchmark contract、L4 runner、CI target 和 workflow 目标路径检查通过。

收尾边界：本轮完成持续预算门禁和报告留存，不把本机报告当作 hosted runner baseline；
固定 runner baseline 和超过 10% regression 告警仍待下一轮维护。

## 2.24 本轮完成结果（L5：脱敏经验数据固定切分合同）

本轮不读取或生成真实经验案例，只收口离线评估的切分和数据泄漏边界：

- 新增 `pa-agent.experience-split.v1` / `instrument-hash.v1`；
- `build_fixed_split()` 按 opaque `instrument_id` 分组，以稳定 hash 选择 evaluation groups；
- `apply_fixed_split()` 校验 dataset digest、case 覆盖和 group 不交叉；
- `dump_split()` / `load_split()` 支持版本化 split envelope，case 顺序变化不改变 digest；
- 单 instrument 数据集显式拒绝，避免产生没有独立 evaluation group 的伪基准。

验证：experience evaluator/reader 测试 **11 passed**；Ruff、Ruff format、`py_compile` 和
`git diff --check` 通过。

收尾边界：经验目录仍无真实案例，本轮不宣称检索质量改善；仍需脱敏导出、人工标签、固定
split 报告和线上权重校准。

## 2.25 本轮完成结果（L6：显式 live headless observation harness）

本轮不执行真实 Provider，只提供受控、可审计的真实观察入口：

- 新增 `tools/run_live_headless_observation.py`，必须显式 `--confirm-live`，并只读取
  `PA_AGENT_LIVE_API_KEY`、可选 `PA_AGENT_LIVE_BASE_URL`/`PA_AGENT_LIVE_MODEL`；
- 通过 `HeadlessAnalysisAdapter` 写入 event/record，随后使用严格
  `expected_correlation_id` replay；
- 输出 `pa-agent.live-observation.v1` 脱敏 summary，不包含 key、prompt、回复、行情、价格或
  绝对路径；
- 未确认或缺少 key 时立即退出，安全守卫测试进入 CI targeted pytest/focused Ruff；普通和
  夜间 CI 不调用 live harness。

验证：live harness 安全守卫测试通过；Ruff、Ruff format、`py_compile`、CI target 和
`git diff --check` 通过。

收尾边界：当前环境没有 Provider 凭据，真实运行结果、稳定周期和 GUI/headless record/event
完整等价仍待在有授权凭据的环境中执行。

## 2.26 本轮完成结果（L3：live harness Pipeline opt-in）

本轮不改变默认 rollout 开关，只扩展显式 live observation：

- `tools/run_live_headless_observation.py` 新增 `--pipeline-builder-enabled`；
- 不传参数保持 legacy，传入后仅本次运行使用 Pipeline；
- summary 记录开关状态、终态、事件序列、record 写入和严格 replay 结果，不写入敏感原文；
- 普通/夜间 CI 仍不会触发 Provider。

验证：live harness 安全守卫测试、Ruff、`py_compile` 和 `git diff --check` 通过。

收尾边界：当前环境没有 Provider 凭据，本轮未运行真实 legacy/Pipeline，不能宣称真实等价或
稳定周期完成。

## 2.27 本轮完成结果（L4：hosted runner baseline cache）

本轮不修改性能热路径，把 L4 workflow 的 baseline 维护接到同一 hosted runner 缓存：

- workflow 按 Windows/Python、iterations、warmups 分区恢复最近一次成功 `l4-baseline.json`；
- 有 baseline 时自动执行 `--baseline`，超过 10% p95 regression 或预算失败则当前运行失败；
- 失败运行不会覆盖旧 baseline，首次无缓存运行只做预算门禁；
- 成功运行保存新 baseline，并继续上传当前 JSON artifact。

验证：benchmark CLI、L4 contract tests、CI target、Ruff baseline 和 workflow 文本检查通过。

收尾边界：当前环境无法直接执行 GitHub Actions；首轮成功 hosted baseline 和 runner image 变更
审核仍需由 Actions 运行产生。

## 2.28 本轮完成结果（L6：live observation artifact validator）

本轮不调用 Provider，只增加真实观察 artifact 的离线审计：

- 新增 `tools/validate_live_observation.py`；
- 校验 `pa-agent.live-observation.v1` summary、event_file、event schema、correlation、事件
  序列/数量和 record 文件是否存在且未越出 records 目录；
- 输出 `pa-agent.live-observation-validation.v1`，可分别审计 legacy/Pipeline 两次运行；
- 新增无网络 validator 单测并纳入 CI targeted pytest/focused Ruff。

验证：live harness/validator 测试、Ruff、`py_compile`、CI target 和 `git diff --check` 通过。

收尾边界：validator 只证明 artifact 自洽，不能替代真实 Provider 稳定周期或 GUI/headless
完整等价证据。

## 2.29 下一轮待执行（L4：workflow dispatch 权限与 hosted baseline 验收）

本轮只记录外部执行步骤，不把权限配置或 hosted runner 结果误标为已完成：

- 仓库 `jwj911/PA_Agent` 的 workflow 文件为 `.github/workflows/l4-benchmark.yml`，分支为
  `main`，已声明 `workflow_dispatch` 和每日 schedule；
- 网页手动运行要求账号拥有仓库 Write 权限；CLI/API 触发建议使用仅授权
  `PA_Agent` 的 Fine-grained PAT，并只授予 Repository `Actions: Read and write`；
- 不把 PAT、Provider key 或其输出写入仓库、日志或聊天；workflow 内现有
  `permissions: contents: read` 不因“触发 workflow”而扩大为全局写权限；
- 首次以 `iterations=30`、`warmups=5` 运行，只验证预算门禁并建立 hosted baseline；
- 第二次使用相同参数运行，验证最近成功 baseline restore、`--baseline` p95 比较和超过 10%
  regression 门禁；同时下载并审核 `pa-agent.performance.v1` JSON artifact；
- 只有 Actions 成功运行、artifact 存在、runner/Python 环境记录清晰且第二次比较证据完整后，
  才能把 L4 hosted baseline 标记为收口。

推荐执行入口：

```powershell
gh workflow run l4-benchmark.yml `
  --repo jwj911/PA_Agent `
  --ref main `
  -f iterations=30 `
  -f warmups=5
gh run list --repo jwj911/PA_Agent --workflow l4-benchmark.yml --limit 5
```

收尾边界：当前工作区没有 GitHub Actions 触发凭据，且尚无 hosted run；本节仅作为后续
授权环境的执行清单，不替代真实 runner 证据。

## 3. 每轮建议交付物

### 3.1 L6 headless runner / CLI 最小入口

本轮已交付：

- 新增 PyQt-free `pa_agent/cli.py`，接入 `pa-agent headless` 和 `python -m pa_agent.main headless`。
- `validate-config` 严格解析 settings JSON，stdout 只输出结构化结果，密钥只报告是否配置。
- `snapshot --input` 规范化 `bars`/`kline_data` 为 `pa-agent.snapshot.v1`，并把非有限指标值
  序列化为 JSON `null`。
- `analyze --input` 默认运行 provider-free Stage 1 prompt dry-run，明确 `dry_run=true`、
  `provider_called=false`，不执行真实网络请求或下单；`--run/--execute` 显式启用两阶段
  Provider runner。
- `--records-dir`、`--events` 和 `--correlation-id` 提供 record 输出、orchestrator JSONL
  事件及稳定退出码映射；final/partial record 复用既有 `PendingWriter`。
- 新增 CLI 单测、入口无 Qt 分发测试，以及 GUI/headless 共享 core 对同一 snapshot 的 Stage 1
  prompt 等价测试；CLI 测试已进入 targeted pytest 和 focused Ruff 清单。

已完成：

- 同一固定 fixture 下 GUI/headless Stage 1/Stage 2 final、partial、cancel、failure record 和
  milestone/status 等价测试，覆盖 prompt、流式内容、策略文件回调和 partial persistence；
- 固化 `pa-agent.event.v1` JSONL envelope，新增 schema 校验、未知版本拒绝和旧 envelope 回放
  兼容。
- 新增显式 `tools/run_live_headless_observation.py`：使用环境变量凭据、严格 correlation replay
  和脱敏 summary；未确认或缺少凭据时不触网。
- 新增 `tools/validate_live_observation.py`：离线核对 summary、event、correlation 和 record
  文件自洽性，不替代真实运行证据。

仍需交付：

- 在有授权凭据的环境执行真实 Provider 观察、record/事件落盘证据和稳定周期；
- 对真实运行结果补充 GUI/headless record/event 完整等价复核；
- 保留 `AppContext.bootstrap()` 兼容 facade，并确认 `bootstrap_gui()` 的 Qt/data source adapter
  语义不变。

验收标准：

- 未安装 PyQt6 的环境可以 import headless core 和运行相关单测。
- headless 路径不导入 `pa_agent.util.event_bus`，不创建 Qt `EventBus`，不连接数据源。
- GUI/headless 对同一 snapshot 的核心记录字段深度相等；任何允许差异必须在测试中显式声明。
- stdout 只输出结构化结果，诊断日志不污染 JSON 输出。
- 旧 GUI 启动入口签名和行为保持兼容。

依赖关系：

- 已依赖第 223 至 225 轮完成的 `AppEvent` / `EventSink`、`bootstrap_headless()`、
  `_build_core()` 和 `bootstrap_gui()`。
- 需要固定 snapshot fixture、fake AI client 或 mock 响应，避免真实 Provider 和数据源。

风险边界：

- 本轮不实现完整服务端、后台 daemon 或真实交易能力。
- 不把数据源连接逻辑搬进 headless bootstrap。
- 不在测试中读取真实 `config/settings.json` 的密钥，也不依赖 live API。

### 3.2 L2 TemplateStore / manifest / golden snapshots

本轮已交付：

- 新增 PyQt-free `pa_agent/ai/prompting/template_manifest.py`，覆盖现有 29 个 `.txt` 模板的
  阶段、角色、版本、输出契约和依赖。
- 新增 `TemplateStore`，提供 manifest 限制的 UTF-8 读取、显式缓存失效、错误诊断和 SHA-256
  `TemplateSnapshot`。
- 新增 `tests/fixtures/prompt_golden.json`，固定全部模板和 `PromptAssembler` 共享 system prompt
  的 UTF-8 字节长度/摘要，以及 Stage 2 standalone/prefix-chain continuation 的消息快照。
- 共享 system prompt、Stage 1 user prompt、Stage 2 user prompt 和 continuation 已通过同一
  compatibility adapter 迁移；Stage 1/Stage 2 模板组整组严格加载，失败时 warning 回退旧 `_load()`。
- 新增 `pa_agent/ai/prompting/template_context.py`：上下文不可变、显式且 JSON 可序列化，
  不携带 `Settings`、Qt 对象或网络客户端。
- `TemplateStore.render()` / `render_many()` 使用标准库严格变量替换；缺变量、语法错误和
  非 mapping context 均明确失败，不执行任意 Python。
- 关键渲染路径增加安全诊断日志，只记录模板名、阶段、context 键名、占位符、长度和失败原因，
  不记录变量值、完整 prompt 或密钥。

兼容观察项：

- 稳定一个完整周期后，再评估删除重复的 `PromptAssembler` loader/helper。
- 在兼容观察期内继续保留 `use_template_store=False`、旧 `_load()` 和 prompt golden snapshots。
- 不把 Jinja2 或其他可执行模板引擎作为本轮隐含依赖。

验收标准：

- 同一 fixture 下旧/新 prompt 字节相等；若确需变化，snapshot diff 必须可审查并说明原因。
- system prompt 前缀和 KV cache key 不漂移。
- 模板缺变量、编码错误和文件缺失都能给出明确诊断，不静默生成不完整 prompt。
- feature flag 关闭时旧路径行为不变。
- 旧 loader 与 TemplateStore 路径在兼容观察期内保持可按 fixture 重放和回滚。

依赖关系：

- 已依赖 L6 headless harness 提供无 GUI prompt 组装与记录对照能力。
- 依赖当前 PyQt-free renderer 保持叶子模块边界。

风险边界：

- 不在第一轮模板化中重写全部策略文本。
- 不允许模板执行任意 Python。
- 不在后续观察期顺手重写中文策略文本或改变文件顺序。

### 3.3 L3 Pipeline state/step 化

第 238 轮已交付协议和 legacy compatibility adapter，Task 5 已完成 PipelineState
foundation，Task 6 已完成 `Stage1Step`，Task 7 已完成 `RouteStep`，Task 8 已完成 `Stage2Step`，
Task 9 已完成 `PersistStep` 真实步骤，Task 10 已完成 rollout flag 接线、完整终态矩阵和 Qt-free
adapter 对照测试；后续交付物：

- 保持 state 对 Stage 1/Stage 2 payload、usage、route 输出、partial reason、persistence intent
  、terminal status 和 `persistence_pending` 的显式承载。
- 继续验证真实 `PersistStep` 的 full/partial record assembly/write、partial reason、脱敏、
  磁盘失败和 writer 写入结果边界；`PendingWriter.last_write_succeeded` 为底层写入结果提供
  可观测信号。
- 在 opt-in pipeline 中保持 `Stage1Step -> RouteStep -> Stage2Step -> PersistStep` 顺序；
  `LegacyPersistStep` 仅保留兼容名称，不再作为当前 opt-in 步骤描述。
- 保留 `TwoStageOrchestrator.submit()` 作为兼容 facade，通过默认关闭的
  `orchestrator.pipeline_builder_enabled` 控制新路径；flag-off 走 legacy，flag-on 委托完整四步
  Pipeline。
- 继续增加 Persist 的 final/partial、磁盘错误、partial reason 和 GUI/headless 等价测试，并
  保持 Task 10 完整终态矩阵；四个真实步骤和切换准备已齐，但真实稳定观察周期与 GUI/headless
  全链路 evidence 仍未收口。

验收标准：

- 每个终止状态都由显式 `TerminalStatus` 表示，不能再依赖局部变量是否存在推断进度。
- Route failure 已映射到稳定的 `route_failed`；Stage2Step 已覆盖 Stage 2 失败终态；真实
  PersistStep 已收口 full/partial 写入、`RecordSaved` 顺序和磁盘失败；
  状态摘要不得泄露
  callbacks、Provider client、prompt/reply 正文、行情数据、密钥或 URL path/query/fragment。
- 新旧路径在相同 fixture 下最终记录、partial record 和事件序列可比对。
- Pipeline 模块不导入 PyQt6。
- feature flag 关闭时旧 `submit()` 行为保持不变。
- 四个真实步骤和 rollout 测试已齐不等于 L3 完成；默认 flag 仍须关闭，仍需真实稳定观察周期和
  GUI/headless final/partial/cancel/failure 全链路等价 evidence。

依赖关系：

- 依赖 L6 headless harness 作为跨层等价验证入口。
- 依赖 L2 prompt snapshot 稳定，避免 Pipeline 改造时混入 prompt 字节变化。

风险边界：

- 不一次性重写 `TwoStageOrchestrator`。
- 不改变 JSON schema、normalizer、retry 和记录格式，除非单独开新任务并提供迁移证据。
- 不删除旧路径，直到新路径经过至少一个完整稳定周期。

### 3.4 L5 脱敏数据集与离线评估

已交付：

- `pa-agent.experience-eval.v1` dataset envelope、`kline-geometry.v1` feature version 和
  opaque instrument id 等脱敏字段合同；
- `pa-agent.experience-split.v1` / `instrument-hash.v1` instrument-grouped 固定切分、dataset
  digest 和 split round-trip/泄漏门禁；
- 离线 scorer，输出 `Recall@K`、`NDCG@K`、legacy fallback rate、score distribution 和
  ranking stability；
- scorer 及 dataset round-trip 的固定单测。

仍需交付：

- 导出满足合同的真实脱敏经验案例，并补齐 opaque instrument id、timeframe、cycle、direction、
  patterns、success/failure 等必要元数据和人工相关性标签。
- 生成固定 split 下的真实指标报告，并在证据充分后评估线上权重。
- 生成旧排序规则和候选新规则的并排报告，并进行人工抽样评审。

验收标准：

- 离线评估可重复运行，输入 fixture 不含真实 API Key 或敏感配置。
- 在真实样本不足前不调整线上相似度权重。
- 若未来启用新权重，必须记录特征版本、窗口和 fallback 诊断信息。

依赖关系：

- 依赖现有 L5 相关性排序和 K 线相似度实现。
- 建议借助 L6/L3 的 headless harness 批量生成或重放评估输入。

风险边界：

- 不用合成样本结论替代真实经验数据结论。
- 不把失败样本、截图路径、密钥或本地绝对路径泄漏到可提交 fixture。
- 不在无指标改善证据时修改线上排序公式。

### 3.5 L4 性能预算和持续基准

已交付：

- `pa-agent.performance.v1` benchmark/report contract、p50/p95 和 10% regression 判定；
- `tools/run_l4_benchmark.py` 的 100/500/5000 bars snapshot/indicator/geometry synthetic suite；
- 当前固定环境报告 `docs/benchmarks/l4_synthetic_2026-07-22.json` 和 contract 单测。
- `.github/workflows/l4-benchmark.yml` 的手动/夜间预算门禁和 30 天 artifact 留存。

仍需交付：

- 在固定 runner 环境维护 baseline，并启用同环境 10% regression 比较；
- 评估 prompt build、records 读取、Pipeline dry-run 等剩余热点是否需要纳入 suite。

验收标准：

- 基准输入固定，避免网络、live Provider 和本机 GUI 状态噪声。
- 每个预算都有当前基线和维护说明。
- 预算检查不会显著拖慢常规 CI。

依赖关系：

- 建议等待 L6 harness、L2 prompt snapshot 和 L3 Pipeline 状态模型初步稳定后收口。

风险边界：

- 不凭单次最好成绩判断性能。
- 不在没有基准证据的情况下继续重写热路径。
- 不为了性能预算缩小功能测试或安全检查范围。

### 3.6 L1 插件和扩展契约收口

建议交付物：

- 补充数据源和 AI Provider 扩展契约文档，说明 matcher、builder、settings 注入、线程安全和注销时机。
- 增加 registry 生命周期测试，覆盖重复注册、replace、注销、并发读取和 builder 不在锁内执行。
- 设计配置持久化规则：自定义 kind/model 只保存字符串，加载时由注册表校验，未知值安全回退并记录 warning。
- 评估 Python entry points 或显式 bootstrap registration，避免扫描任意目录执行代码。

验收标准：

- 新增测试数据源或 AI client route 不需要修改核心 `create_*` 条件分支。
- 内置路由、日志和错误行为与既有版本一致。
- import registry 不提前加载可选依赖。
- 未知配置值不导致 GUI 启动崩溃。

依赖关系：

- 依赖 L1 第二阶段已完成的数据源注册表和 AI Provider 注册表。
- 可与 L6 真实 runner/事件重放收口并行，但不应绕过 L2/L3 的等价性证据。

风险边界：

- 注册表不负责 token 同步、网络探测、DPAPI 解密或 `save_settings()`。
- 不引入任意目录扫描和动态执行。
- 不把外部插件失败升级为内置 Provider/data source 启动失败。

## 4. 依赖关系总览

```text
L6 headless runner / 等价测试
  -> L3 Pipeline state / steps
  -> L5 离线评估和 L4 性能预算

L2 TemplateStore / Context
  -> 已完成实现，进入兼容观察期

L1 插件契约治理
  -> 可穿插推进，但不得阻塞 L6 -> L3 主链路
```

关键依赖说明：

- L6 先行，是因为后续 prompt、pipeline、经验评估和性能预算都需要无 GUI harness 产生可重复证据。
- L2 已通过 golden snapshot 固定 prompt 字节和 JSON 校验输入，L3 可直接复用其稳定合同。
- L3 早于 L5/L4，是为了让批量评估和性能基准能复用显式状态和事件模型。
- L5 的线上权重调整必须等待脱敏数据集和离线指标，不作为近期第一优先级。

## 5. 通用验收标准

每轮完成时至少满足：

- 公开契约或兼容 facade 明确，旧入口在迁移周期内保持可用。
- 有单元、集成或失败路径测试覆盖本轮改动风险。
- GUI/headless 或旧/新路径提供等价证据。
- 线程安全、日志脱敏、配置持久化、文件名安全和密钥处理约束不回退。
- 文档、`docs/CHANGELOG.md`、`AGENTS.md`、路线图和 CI 清单按需同步。
- 不把 live 网络、真实 API Key 或本地敏感配置作为测试前提。
- 每轮改动保持原子化，避免把 prompt、pipeline、GUI 和记录格式迁移混在同一提交中。

## 6. 风险边界

- **Prompt 字节漂移**：必须通过 golden snapshot 或显式 diff 审查控制，不能顺手改文案。
- **Qt 依赖泄漏**：headless 相关模块必须保持 PyQt-free，import boundary 需要测试兜住。
- **Pipeline 行为漂移**：取消、校验失败、partial record 和 gate short-circuit 必须有等价证据。
- **Registry 副作用扩散**：注册表只做发现和构造，不做网络、密钥、配置保存或 fallback 编排。
- **经验库过拟合**：真实样本不足时只做数据和评估，不调线上公式。
- **性能目标失真**：性能预算使用固定 fixture 和 p50/p95，避免用单次运行或 live 网络结果下结论。
- **文档和事实漂移**：短中期执行顺序以本文件为准，长期边界和完成定义仍以
  [`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为准；两者冲突时先更新路线图事实，
  再同步本执行计划。
