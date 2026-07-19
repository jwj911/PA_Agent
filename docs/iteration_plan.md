# L1-L6 后续迭代执行计划

> 状态：短中期执行计划
> 更新时间：2026-07-19
> 适用范围：后续若干轮原子迭代
> 长期边界：以 [`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为准

本文档用于把长期架构路线图拆成短中期可执行轮次，明确下一批交付物、验收标准、
依赖关系和风险边界。长期模块边界、迁移原则、完成定义仍以
[`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为主参考；本文件不改写长期事实，
只帮助代理在已批准方向下选择下一轮工作。

## 1. 当前完成情况

| 路线 | 当前状态 | 已完成基础 | 主要剩余工作 |
|---|---|---|---|
| L1 Provider/数据源注册表 | 第二阶段完成 | 数据源注册表、AI Provider 注册表、优先级 matcher、延迟 builder、运行时注册 API | 插件发现、配置持久化、扩展契约、生命周期和并发测试 |
| L2 Prompt 模板引擎 | 未启动 | `Stage1PromptBuilder`、`Stage2PromptBuilder` 和多个 PyQt-free renderer 已拆出 | `TemplateStore`、manifest、严格变量检查、golden snapshots 和兼容 adapter |
| L3 Pipeline Builder | 部分准备 | `TwoStageOrchestrator.submit()` 已拆出 Stage 1、Stage 2、路由和持久化辅助方法 | 显式 state/step、terminal status、事件序列和旧/新路径等价测试 |
| L4 性能预算 | 主要优化完成 | HTTP client 复用、forming 判定复用、K 线几何 O(n) 化、记录缓存和并发锁 | 固定基准、预算阈值、p50/p95 报告和持续回归监控 |
| L5 经验库升级 | 第二阶段完成 | 全量相关性排序和 K 线几何相似度已接入 | 脱敏数据集、离线评估、特征版本化和权重校准 |
| L6 Headless/编排 | CLI 最小切片完成 | `AppEvent`、`EventSink`、`bootstrap_headless()`、共享 `_build_core()`、`bootstrap_gui()`、兼容 `bootstrap()`、PyQt-free `pa-agent headless` | 真实 Provider 分析 runner、最终 record 等价测试、JSONL 事件 sink/replay、公开 adapter 契约 |

L6 的当前约束必须继续保持：`bootstrap_gui()` 负责 Qt `EventBus`、数据源连接和订阅；
`bootstrap_headless()` 复用 core helper，但不导入或创建 Qt `EventBus`，不连接数据源，默认使用
`NullEventSink`。

## 2. 后续迭代顺序

本轮已完成 **L6 headless runner / CLI 最小入口与同 snapshot core 等价测试**。下一轮主线转入
**L2 Prompt TemplateStore / manifest / golden snapshots**；L6 剩余的真实 Provider runner、最终
record 等价测试和事件重放继续作为后续 L6 收口项，不能把当前 dry-run 误标为完整无 GUI 分析。

推荐顺序如下：

1. **L2：Prompt TemplateStore / manifest / golden snapshots**。
2. **L6：真实 Provider 分析 runner、JSONL 事件 sink 与最终 record 等价测试**。
3. **L3：Pipeline state/step 化和旧/新路径等价验证**。
4. **L5：脱敏经验数据集与离线评估基线**。
5. **L4：性能预算和持续基准**。
6. **L1 收口治理** 可以在主线空档穿插推进，但不得绕过 L6 的 headless 边界和 L2/L3 等价证据。

## 2.1 当前未收敛问题

以下问题已确认存在，但不在本轮 CLI 最小切片中伪装成“已完成”：

1. `pa-agent headless analyze` 当前只做 snapshot 校验和 Stage 1 prompt dry-run，不调用真实
   Provider，也不写入 `AnalysisRecord`；真实两阶段分析仍由 GUI/`TwoStageOrchestrator` 执行。
2. `CollectingEventSink` 已可收集应用事件，但尚未提供稳定的 JSONL sink、事件重放协议和跨进程
   correlation id 约束。
3. headless 与 GUI 当前已验证共享 core 的 Stage 1 prompt 对同一 snapshot 字节等价；Stage 1/2
   最终 record、partial record、取消和失败事件的全链路等价证据尚未建立。
4. `AppContext._build_core()` 仍是私有 helper；`build_core` 与 `build_gui_adapters` 是否公开，
   需要等 CLI/GUI adapter 契约稳定后再决定。
5. L2 的 TemplateStore、manifest、严格变量检查和 golden snapshot 尚未实现；Prompt 字节稳定性
   目前由既有 builder 与合同测试保证。
6. L1 插件发现/配置回退、L5 脱敏数据集与离线指标、L4 p50/p95 性能预算仍缺少真实数据或固定
   benchmark，不能仅依据合成 fixture 宣称收敛。

## 3. 每轮建议交付物

### 3.1 L6 headless runner / CLI 最小入口

本轮已交付：

- 新增 PyQt-free `pa_agent/cli.py`，接入 `pa-agent headless` 和 `python -m pa_agent.main headless`。
- `validate-config` 严格解析 settings JSON，stdout 只输出结构化结果，密钥只报告是否配置。
- `snapshot --input` 规范化 `bars`/`kline_data` 为 `pa-agent.snapshot.v1`，并把非有限指标值
  序列化为 JSON `null`。
- `analyze --input` 运行 provider-free Stage 1 prompt dry-run，明确 `dry_run=true`、
  `provider_called=false`，不执行真实网络请求或下单。
- 新增 CLI 单测、入口无 Qt 分发测试，以及 GUI/headless 共享 core 对同一 snapshot 的 Stage 1
  prompt 等价测试；CLI 测试已进入 targeted pytest 和 focused Ruff 清单。

仍需交付：

- 明确真实 Provider 分析的显式开关、配置/网络错误映射和 record 输出目录契约。
- 新增同一 snapshot 下 GUI/headless Stage 1/Stage 2 record、partial record 和事件序列等价测试，
  使用 mock provider 或固定 fixture，避免 live 网络依赖。
- 新增 JSONL event sink 与事件快照/重放检查，确认 headless sink 输出可被复现和比对。
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

建议交付物：

- 为当前 `PromptAssembler`、Stage 1/Stage 2 builder 和关键 renderer 建立 UTF-8 golden snapshots。
- 新增 `TemplateStore` 和模板 manifest，先读取现有 `.txt` 与已拆出的 renderer，不大规模改写中文
  prompt 文本。
- 定义模板上下文的显式字段，避免模板直接访问 `Settings`、Qt 对象、网络客户端或文件系统。
- 如引入模板引擎，必须使用严格缺变量失败策略，并保留旧 `PromptAssembler` 兼容 adapter。

验收标准：

- 同一 fixture 下旧/新 prompt 字节相等；若确需变化，snapshot diff 必须可审查并说明原因。
- system prompt 前缀和 KV cache key 不漂移。
- 模板缺变量、编码错误和文件缺失都能给出明确诊断，不静默生成不完整 prompt。
- feature flag 关闭时旧路径行为不变。

依赖关系：

- 建议依赖 L6 headless harness 提供无 GUI prompt 组装与记录对照能力。
- 依赖当前 PyQt-free renderer 保持叶子模块边界。

风险边界：

- 不在第一轮模板化中重写全部策略文本。
- 不允许模板执行任意 Python。
- 不用一次提交同时迁移 system、Stage 1、Stage 2 和 continuation。

### 3.3 L3 Pipeline state/step 化

建议交付物：

- 新增 PyQt-free `PipelineState`、`TerminalStatus`、`StepResult` 和 `PipelineStep` 协议。
- 将现有 `_run_stage1`、`_route_and_load_experience`、`_run_stage2`、`_persist_result` 等辅助方法
  逐步适配为步骤。
- 保留 `TwoStageOrchestrator.submit()` 作为兼容 facade，并通过 feature flag 控制新路径。
- 增加 happy path、取消、网络错误、Stage 1/2 校验失败、gate short-circuit 和 partial record
  的旧/新路径等价测试。

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
  -> L2 golden snapshots / TemplateStore
  -> L3 Pipeline state / steps
  -> L5 离线评估和 L4 性能预算

L1 插件契约治理
  -> 可穿插推进，但不得阻塞 L6 -> L2 -> L3 主链路
```

关键依赖说明：

- L6 先行，是因为后续 prompt、pipeline、经验评估和性能预算都需要无 GUI harness 产生可重复证据。
- L2 早于 L3，是为了在 Pipeline 改造前固定 prompt 字节和 JSON 校验输入。
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
