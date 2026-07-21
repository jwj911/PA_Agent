# L1-L6 后续迭代执行计划

> 状态：短中期执行计划
> 更新时间：2026-07-21
> 适用范围：后续若干轮原子迭代
> 长期边界：以 [`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为准

本文档用于把长期架构路线图拆成短中期可执行轮次，明确下一批交付物、验收标准、
依赖关系和风险边界。长期模块边界、迁移原则、完成定义仍以
[`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为主参考；本文件不改写长期事实，
只帮助代理在已批准方向下选择下一轮工作。

## 1. 当前完成情况

| 路线 | 当前状态 | 已完成基础 | 主要剩余工作 |
|---|---|---|---|
| L1 Provider/数据源注册表 | 基础完成，治理切片已交付 | 数据源注册表、AI Provider 注册表、优先级 matcher、延迟 builder、运行时注册 API、未知数据源配置安全回退；本轮补齐规范化、replace/unregister、并发和懒导入证据 | 插件发现方案、正式扩展契约文档、builder 锁外执行证据 |
| L2 Prompt 模板引擎 | 实现完成，兼容观察期 | `TemplateStore`、29 个模板 manifest、system/Stage 1/Stage 2/continuation 迁移、`TemplateContext`、严格变量渲染、golden snapshots 和整组回退 | 观察一个稳定周期后评估移除重复 helper、兼容开关和旧 loader |
| L3 Pipeline Builder | 第一切片已交付，默认旧路径 | 新增 PyQt-free `PipelineState`、`TerminalStatus`、`PipelineStep`、`StepResult`、`PipelineBuilder`；`run_pipeline()`/`submit_pipeline()` 作为 opt-in compatibility adapter，旧 `submit()` 保持不变 | 将 legacy wrapper 拆为 Stage 1/route/Stage 2/persist steps，并完成全终态与 GUI/headless 等价验证 |
| L4 性能预算 | 代码优化完成，预算未收口 | HTTP client 复用、forming 判定复用、K 线几何 O(n) 化、记录缓存和并发锁 | 固定 synthetic benchmark、预算阈值、p50/p95 报告和持续回归监控 |
| L5 经验库升级 | 排序实现完成，数据评估未收口 | 全量相关性排序和 K 线几何相似度已接入 | 脱敏数据集、固定评估集、离线指标、特征版本化和权重校准 |
| L6 Headless/编排 | runner 第一切片已交付，等价契约未收口 | `AppEvent`、`EventSink`、`JsonlEventSink`、`replay_jsonl`、`bootstrap_headless()`、共享 `_build_core()`、`bootstrap_gui()`、兼容 `bootstrap()`、PyQt-free `pa-agent headless`；`analyze --run/--execute` 已接入两阶段 orchestrator、record 持久化和 JSONL 事件 | GUI/headless 最终/partial/cancel/failure record 等价、公开 adapter 契约和真实 Provider 环境验证 |

L6 的当前约束必须继续保持：`bootstrap_gui()` 负责 Qt `EventBus`、数据源连接和订阅；
`bootstrap_headless()` 复用 core helper，但不导入或创建 Qt `EventBus`，不连接数据源，默认使用
`NullEventSink`。

## 1.1 当前未收尾清单

以下条目是基于当前代码目录、测试入口和路线图的收尾审计；“基础完成”不等于路线已完成。

| 优先级 | 路线 | 当前阻塞项 | 收尾证据 |
|---|---|---|---|
| P0 | L6 | `headless analyze --run` 已接入真实两阶段 runner，但 GUI/headless 全链路等价和公开 adapter 契约仍缺 | mock Provider 下的 final/partial/cancel/failure record、事件重放与 GUI 对照；真实 Provider 只允许显式执行 |
| P1 | L3 | state/step 协议和 legacy wrapper 已存在，但尚未拆出真实阶段步骤，默认路径仍未切换 | Stage 1/route/Stage 2/persist 步骤化、全终态等价和 feature flag 观察周期 |
| P1 | L5 | 没有脱敏经验数据集和固定离线评估基线 | 可重复的 `Recall@K`、`NDCG@K`、fallback rate、稳定性报告 |
| P1 | L4 | 没有固定 benchmark、预算阈值和 p50/p95 报告 | 固定 fixture 基线、回归阈值和 CI/夜间任务报告 |
| P2 | L1 | registry 基础、未知数据源配置回退和第一批生命周期/并发证据已完成；插件发现与正式扩展契约仍未收口 | 不改核心条件分支的扩展样例、entry points/显式注册方案、matcher/builder/settings 注入契约 |
| P2 | L2 | 实现已完成，但 `use_template_store` 与旧 loader 尚处兼容观察期 | 稳定周期内新旧路径持续等价，并形成兼容入口下线计划 |

当前主链路为 **L6 → L3 → L5/L4**；L2 已完成实现并进入兼容观察期，L1 可独立并行治理，
但不得成为 L6/L3 主线的隐式前置条件。

## 2. 后续迭代顺序

第 232 轮已完成 **L2 Stage 1 user prompt 迁移**，第 233 轮已完成 Stage 2/continuation
和 `TemplateContext` 收尾实现。第 234 轮已完成 L6 JSONL event sink/replay 切片，第 237 轮
已交付显式执行的 headless 两阶段 runner，第 238 轮已交付 L3 state/step compatibility
adapter；当前主线继续推进 L3 阶段步骤化和 GUI/headless 最终 record 等价。

推荐顺序如下：

1. **L3：Pipeline 阶段步骤化和旧/新路径等价验证**。
2. **L6：GUI/headless 最终/partial/cancel/failure record 等价和公开 adapter 契约**。
3. **L5：脱敏经验数据集与离线评估基线**。
4. **L4：性能预算和持续基准**。
5. **L1 收口治理** 可以在主线空档穿插推进，但不得绕过 L6/L3 的等价证据。
6. **L2 兼容观察**：记录新旧路径运行结果，稳定一个周期后再单独评估旧 loader/helper 的下线。
7. **L1 治理观察**：第 236 轮已完成 registry 生命周期、replace/unregister、并发和 lazy-import 测试；下一切片聚焦插件发现方案与正式扩展契约。

第 233 轮已经完成；当前不再重复改写 L2 prompt 文本，后续只保留兼容观察和回滚能力。

## 2.1 当前未收敛问题

以下问题已确认存在，但不在本轮 CLI 最小切片中伪装成“已完成”：

1. `pa-agent headless analyze` 默认仍只做 snapshot 校验和 Stage 1 prompt dry-run；只有显式
   `--run/--execute` 才装配真实 client 并执行两阶段 `TwoStageOrchestrator`，写入 final/partial
   `AnalysisRecord`。
2. `JsonlEventSink` / `replay_jsonl` 已提供本地 JSONL 事件写入和重放；跨进程 correlation id
   约束和与真实 Provider record 的完整等价协议仍待建立。
3. headless 与 GUI 当前已验证共享 core 的 Stage 1 prompt 对同一 snapshot 字节等价；runner 已有
   mock Provider 的 final/partial record 和 JSONL 事件测试，但 Stage 1/2 最终 record、取消和失败
   事件的 GUI/headless 全链路等价证据尚未建立。
4. `AppContext._build_core()` 仍是私有 helper；当前通过 `bootstrap_headless(client=...)` 提供
   测试注入点，`build_core` 与 `build_gui_adapters` 是否公开，需要等 CLI/GUI adapter 契约稳定后再决定。
5. L2 system、Stage 1、Stage 2/continuation、TemplateContext 和严格变量渲染已实现并保留严格
   失败回退；当前只剩旧 loader/helper 的兼容观察期。
6. L3 阶段步骤化与完整终态等价、L1 插件发现方案与正式扩展契约、L5 脱敏数据集与离线指标、L4 p50/p95 性能预算仍缺少
   固定证据，不能仅依据当前测试宣称收敛；L2 只剩兼容观察期。

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

本轮不实现 Python entry points、任意目录扫描、Provider token 同步或 registry 并发策略；
下一 L1 切片再处理扩展契约和生命周期/并发测试。

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

仍需交付：

- 新增同一 snapshot 下 GUI/headless Stage 1/Stage 2 record、partial record 和事件序列等价测试，
  覆盖取消和失败终态，使用 mock provider 或固定 fixture，避免 live 网络依赖。
- 固化公开 headless adapter 契约，明确 CLI 参数、record 摘要和事件 envelope 的版本边界。
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

第 238 轮已交付协议和 legacy compatibility adapter，后续交付物：

- 将现有 `_run_stage1`、`_route_and_load_experience`、`_run_stage2`、`_persist_result` 等辅助方法
  逐步适配为步骤。
- 保留 `TwoStageOrchestrator.submit()` 作为兼容 facade，通过显式 adapter/feature flag 控制新路径。
- 增加网络错误、Stage 1/2 校验失败、gate short-circuit、增量分析和 partial record 的旧/新路径等价测试。

验收标准：

- 每个终止状态都由显式 `TerminalStatus` 表示，不能再依赖局部变量是否存在推断进度。
- 新旧路径在相同 fixture 下最终记录、partial record 和事件序列可比对。
- Pipeline 模块不导入 PyQt6。
- feature flag 关闭时旧 `submit()` 行为保持不变。

依赖关系：

- 依赖 L6 headless harness 作为跨层等价验证入口。
- 依赖 L2 prompt snapshot 稳定，避免 Pipeline 改造时混入 prompt 字节变化。

风险边界：

- 不一次性重写 `TwoStageOrchestrator`。
- 不改变 JSON schema、normalizer、retry 和记录格式，除非单独开新任务并提供迁移证据。
- 不删除旧路径，直到新路径经过至少一个完整稳定周期。

### 3.4 L5 脱敏数据集与离线评估

建议交付物：

- 定义经验案例 schema version、feature extraction version 和脱敏导出格式。
- 建立固定 train/evaluation 切分，保留 symbol、timeframe、cycle、direction、patterns、
  success/failure 等必要元数据。
- 新增离线 scorer，输出 `Recall@K`、`NDCG@K`、legacy fallback rate、score distribution 和
  ranking stability。
- 生成旧排序规则和候选新规则的并排报告。

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

建议交付物：

- 为 prompt build、snapshot 构建、K 线几何、records 读取、Pipeline dry-run 等路径建立固定
  synthetic benchmark。
- 输出 p50/p95、样本数量、解释器版本、操作系统和关键配置。
- 设定保守预算阈值，并决定进入 CI、夜间任务或手工报告的范围。
- 将超过 10% 的回退定义为需要先分析后优化的事件。

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
