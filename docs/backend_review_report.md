# PA Agent 后端全面审查报告

> 初始审查日期：2026-07-12
> 审查范围：`pa_agent/` 后端核心代码（`ai/`、`data/`、`orchestrator/`、`records/`、`config/`、`util/`、`security/`、`notify/`），以及 `tests/`、`pyproject.toml`、`.githooks/`、`.github/workflows/ci.yml` 等支撑文件。  
> 审查方法：只读代码审查，结合多维度静态分析，未运行测试与 lint。  
> 说明：GUI 层的 `main_window.py` 也在部分章节被提及，因为其中包含了部分业务逻辑与主线程交互，但本报告重点仍是后端。

> 状态更新：2026-07-21。R1-R8、M1-M10 及 L1-L6 的实际进度以
> [`docs/architecture_roadmap.md`](./architecture_roadmap.md) 和
> [`docs/iteration_plan.md`](./iteration_plan.md) 为准；本报告保留初始审查发现，
> 不再作为已完成项的唯一状态来源。

---

## 1. 总体结论

PA Agent 的后端已经具备一个生产级桌面应用的核心骨架：

- **模块职责划分清晰**：`ai/`（AI 层）、`data/`（数据层）、`orchestrator/`（业务编排）、`records/`（持久化）、`config/`（配置）、`util/`（通用工具）边界基本合理。
- **数据流闭环完整**：K 线数据 → 特征工程 → 两阶段 AI 分析 → JSON 校验/归一化 → 策略路由 → 交易决策 → 持久化/日志，流程明确。
- **并发与取消机制成熟**：网络/AI 调用均下放到后台线程，GUI 主线程基本不被阻塞；`CancelToken` 贯穿数据刷新、AI 流式请求、编排器、追问等链路。
- **测试与安全意识较好**：测试分 unit / integration / property / e2e / live 五层；API Key 在日志、持久化、GUI 中均有脱敏机制；`.gitignore` 与 pre-commit hook 覆盖敏感文件。

**但当前最大的技术债务集中在三个方面**：

1. **`ai/` 层内部高耦合与超大文件**：循环依赖、运行时延迟导入、3000+ 行的 `decision_nodes.py`、近 2000 行的 `prompt_assembler.py` 等，长期维护成本高。
2. **编排器/启动器职责泛化**：`AppContext.bootstrap()` 与 `TwoStageOrchestrator` 承担了 provider 同步、设置保存、日志更新等本应由专门服务负责的职责。
3. **安全实现与文档承诺不一致**：README / config/README 称 API Key "本地加密存储"，但实际 `settings.json` 仍为明文；`pa_agent/security/` 包为空占位。

整体而言，PA Agent 后端已经"可用"，但要达到"易维护、易扩展、长期稳定"，建议优先进行**模块化拆分、职责下沉、循环依赖治理**，再逐步补齐安全加密与性能优化。

### 1.1 当前进度校正（2026-07-19）

- L1 数据源/Provider 注册表已完成第二阶段基础，未知数据源配置已安全回退并持久化规范化值；
  第 236 轮又补齐了规范化 key、replace/unregister、priority 稳定性、并发读写和 lazy-import
  测试；仍待插件发现与正式扩展契约。
- L2 已完成 prompt 文件顺序、阶段边界和 Spike/Climax 硬约束的合同化基线；第 230 轮新增
  29 个模板的 manifest、`TemplateStore` 和 UTF-8 golden digest，第 231-233 轮完成共享 system、
  Stage 1、Stage 2/continuation、`TemplateContext` 和严格变量渲染迁移，并保留严格失败回退；
  当前进入旧 loader/helper 的兼容观察期。
- L3 第 238 轮已新增 PyQt-free `orchestrator/pipeline/` 状态/步骤协议、显式终态和
  `LegacySubmitStep` compatibility adapter；`TwoStageOrchestrator.submit()` 默认行为保持不变，
  真实 Stage 1/route/Stage 2/persist 步骤化和完整终态等价仍待完成。
- L5 已接入 K 线几何相似度，但真实脱敏数据集和离线指标尚未具备，不应调整线上权重。
- L6 已完成 `AppEvent`/`EventSink`、`bootstrap_headless()`、共享 core/GUI bootstrap 边界，
  第 229 轮新增 PyQt-free CLI 最小切片，第 234 轮新增 JSONL event sink/replay，第 237 轮又
  通过显式 `--run/--execute` 接入两阶段 runner、final/partial record 持久化、退出码映射和
  correlation 事件输出；GUI/headless 全链路 record 等价、真实 Provider 环境验证和公开
  adapter 契约仍未收敛。
- L7 已具备 Python 矩阵、targeted pytest、Ruff baseline、focused Ruff/Black 和覆盖率门槛；
  全仓历史诊断仍通过基线治理，不能把 focused 门禁等同于全仓零告警。

---

## 2. 后端架构评估

### 2.1 分层架构

```
┌─────────────────────────────────────────┐
│  GUI (PyQt6) / CLI / E2E Tests          │
├─────────────────────────────────────────┤
│  Orchestrator: two_stage.py             │  ← 两阶段流水线、追问、校验重试
│  free_chat.py / validation_retry.py     │
├─────────────────────────────────────────┤
│  AI Layer: ai/                          │  ← 客户端、prompt 组装、JSON 校验、
│  client_factory / deepseek_client       │     归一化、策略路由、决策树/节点
│  prompt_assembler / router              │
│  json_validator / normalizers           │
│  decision_tree / decision_nodes         │
├─────────────────────────────────────────┤
│  Data Layer: data/                      │  ← MT5 / TradingView / AkShare /
│  base.py / factory.py / mt5.py          │     EastMoney / Tushare / yfinance
│  refresh_loop.py                        │
├─────────────────────────────────────────┤
│  Records & Config: records/ / config/   │  ← 持久化、经验库、配置模型
│  util/                                  │  ← 日志、事件总线、掩码、线程工具
└─────────────────────────────────────────┘
```

**优点**：分层基本符合关注点分离；`AppContext` 以依赖注入容器方式装配组件，避免了全局单例。

**风险**：
- `AppContext` 字段类型全为 `Any`（`app_context.py:13-27`），失去了静态类型检查价值。
- `AppContext.bootstrap()` 集中了 17+ 个运行时导入，并直接负责 QClaw/WorkBuddy/Cursor 的 provider 同步与 `settings.json` 回写，属于启动期副作用。
- `TwoStageOrchestrator` 除了编排两阶段分析，还承担了 provider fallback 保存、API key 更新、日志脱敏同步、usage 累加等职责。

### 2.2 依赖关系与循环依赖

后端存在若干循环依赖/强耦合链，当前主要通过**函数内延迟导入**硬解：

| 循环/强耦合 | 涉及文件 | 说明 |
|---|---|---|
| qclaw ↔ workbuddy | `ai/qclaw_connector.py` / `ai/workbuddy_connector.py` | 互相导入对方别名函数 |
| decision_tree ↔ trace_normalize | `ai/decision_tree.py:237` / `ai/trace_normalize.py:10` | 互相导入 |
| decision_nodes ↔ trend_context | `ai/decision_nodes.py:2871` / `ai/trend_context.py` | 互相导入 |
| decision_nodes ↔ decision_tree | `ai/decision_nodes.py:391,409` / `ai/decision_tree.py` | 节点使用 tree 的 `node_label`，tree 又依赖 trace_normalize，trace_normalize 依赖 tree |
| json_validator ↔ normalizer ↔ decision_nodes | `ai/json_validator.py` / `stage1_normalizer.py` / `stage2_normalizer.py` / `decision_nodes.py` | 校验器调用归一化器，归一化器调用决策节点引擎 |
| prompt_assembler ↔ decision_nodes/trend_context | `ai/prompt_assembler.py:1199-1213` | prompt 组装直接读取决策节点结果 |
| data/factory → config/settings | `pa_agent/data/factory.py:88-92` | 工厂内部读取 `settings.json` |

**影响**：代码可读性下降，静态分析受限，新增功能时容易踩到 import 顺序陷阱。

---

## 3. 优点

### 3.1 架构与设计

1. **依赖注入优于全局单例**：`AppContext` 显式声明共享依赖并注入 GUI 与编排器，便于测试与替换。
2. **数据抽象合理**：`DataSource` ABC + `KlineFrame` / `KlineBar` / `IndicatorBundle` 不可变数据快照，降低多线程共享状态风险。
3. **事件驱动解耦**：`OrchestratorEvent` + Qt signal/slot 让编排器与 GUI 解耦。
4. **配置模型规范**：Pydantic v2 + 字段范围校验 + 旧字段迁移，对配置错误有较好防御。

### 3.2 AI 输出治理

1. **校验闭环完整**：JSON schema 校验 → fence 剥离/截断修复/控制字符转义 → 业务一致性检查 → 错误分类 retry。
2. **归一化宽容度高**：`stage1_normalizer.py` / `stage2_normalizer.py` 对模型常见输出错误做自动修正。
3. **决策节点减少幻觉**：`decision_nodes.py` 用确定性逻辑填充 §1.1、§1.3、§2.3、§2.4、§9、§11 等节点。
4. **Prompt 工程有性能意识**：`_SYSTEM_PROMPT_CACHE` 进程级缓存、FreeChat stable prefix 缓存、增量分析 prefix cache hit 设计。

### 3.3 并发与资源

1. **GUI 主线程基本不被阻塞**：`RefreshLoop`、快照 Worker、分析 Worker、聊天 Worker 均在后台 QThread。
2. **取消链路完整**：`CancelToken` 贯穿数据刷新、AI 流式、编排、追问。
3. **资源回收有意识**：disconnect signal → wait timeout → zombie reap → `deleteLater()` 形成闭环。
4. **TradingView WebSocket 泄漏有修复**：`tradingview.py:134-162` 手动关闭 ws 并置空引用。

### 3.4 安全与测试

1. **密钥脱敏体系化**：`mask_secret.py` + `MaskingFormatter` + `PendingWriter._sanitize()` + GUI `DebugWidget` 均围绕脱敏实现，并有对应测试守护。
2. **敏感文件隔离**：`.gitignore` 正确忽略 `config/settings.json`、日志、记录；`.githooks/pre-commit` 阻止提交敏感文件并扫描 diff。
3. **测试分层完整**：unit / integration / property / e2e / live 五层；真实网络/API 测试被正确标记为 `live`。
4. **文档诚实准确**：`AGENTS.md` 主动指出 `api_key_encrypted` 未实现、settings.json 明文存储等已知问题。

---

## 4. 问题与风险

### 4.1 高优先级

#### 1）`ai/` 层内部高耦合与超大文件

| 文件 | 行数 | 问题 |
|---|---|---|
| `pa_agent/ai/decision_nodes.py` | ~3071 | 包含 `PreflightDataGate`、`DecisionNodeEngine`、`OverrideArbiter`、大量阈值与 judge 函数 |
| `pa_agent/ai/prompt_assembler.py` | ~1953 | 超大类（1063 行），硬编码约 84 KB 中文 prompt，承担 Stage1/Stage2/增量/追问/表格渲染等多重职责 |
| `pa_agent/ai/stage2_normalizer.py` | ~1800 | 与 `trade_metrics`、`decision_continuity`、中文字符串规则深度耦合 |
| `pa_agent/ai/json_validator.py` | ~1165 | schema 校验 + JSON 修复 + 业务一致性检查 + retry 反馈准备混在一起 |
| `pa_agent/orchestrator/two_stage.py` | ~1217 | `submit()` 函数约 646 行，完成 20+ 步骤 |

**风险**：单文件职责过重，单元测试困难，错误定位困难，新功能改动容易牵一发而动全身。

#### 2）循环依赖与延迟导入

多个模块通过函数内延迟导入避免死锁，但架构上呈现"意大利面条式"依赖。新增功能或重构时容易触发 import 错误。

#### 3）编排器/启动器职责泛化

- `AppContext.bootstrap()` 直接负责 QClaw/WorkBuddy/Cursor provider 同步并回写 `settings.json`。
- `TwoStageOrchestrator` 承担 provider fallback 保存、API key 更新、日志脱敏同步、usage 累加等。

**风险**：核心流程代码被基础设施代码淹没，单测难度大，启动期副作用失败时仅打印日志，配置可能处于半同步状态。

#### 4）API Key 明文存储与文档不一致

- `config/settings.json` 中 `provider.api_key` 以明文写入（`pa_agent/config/settings.py:271-280`）。
- `README.md:22`、`config/README.md:15-18` 称 "API Key 加密写入 `api_key_encrypted`"，但 `pa_agent/security/` 为空，无任何加解密逻辑。
- Tushare Token、Feishu Secret、PushPlus Token 同样明文存储。
- WorkBuddy DPAPI 解密取出的 token 也被明文写回 `settings.json`（`workbuddy_connector.py:697-700`）。

**风险**：文档误导用户；`settings.json` 泄漏即密钥泄漏；从 DPAPI 保护的存储中取出再明文落盘，削弱了原存储的安全意义。

#### 5）大量裸 `except Exception: pass` 静默吞异常

| 位置 | 影响 |
|---|---|
| `pa_agent/gui/main_window.py:329,474,574,781` 等 | UI 设置/信号连接出错时完全静默 |
| `pa_agent/data/tradingview.py:161` | ws 清理失败无日志 |
| `pa_agent/data/mt5.py:148,214` | MT5 订阅/初始化失败被吞，用户可能以为成功 |
| `pa_agent/ai/cursor_sdk_client.py:79,94,120,163` | cursor-sdk patch 初始化失败直接 `return`，排障困难 |
| `pa_agent/ai/workbuddy_connector.py:272,351` | DPAPI 解密失败直接 `return`/`pass` |
| `pa_agent/records/analysis_history.py:45` | JSON 损坏或 schema 不兼容被吞掉 |

**风险**：真实 Bug 被长期掩盖，线上问题难以定位。

### 4.2 中优先级

#### 6）全局可变状态无线程保护

| 状态 | 位置 | 风险 |
|---|---|---|
| `_SYSTEM_PROMPT_CACHE` | `ai/prompt_assembler.py:759` | 进程级 dict，多 QThread 并发读写可能 race |
| `_LATEST_RECORD_CACHE` | `records/analysis_history.py:85` | 后台线程使用，无锁 |
| `_COMPACT_CTX_CACHE` | `data/eastmoney_extended.py:706` | 全局可变 dict 无锁 |
| `_active_formatters`、`_configured` | `util/logging.py:21-22` | 全局状态无锁 |
| `_ANIM_PHASE` | `gui/decision_flow_viz.py` | 模块级全局，多实例共享动画相位 |
| `_current` 复权模式 | `data/kline_adjust.py:9` | 全局 mutable，设置与数据源并发读写存在竞态 |
| cursor patch flag | `ai/cursor_sdk_client.py:25-28` | 非线程安全初始化 |

#### 7）部分 I/O 无超时/无重试

- `data/mt5.py`：`copy_rates_from_pos()` / `mt5.initialize()` 无超时，若终端僵死会永久阻塞调用线程。
- `data/tushare_source.py`：无显式 timeout/retry，依赖 `tushare` 库内部行为。
- `data/akshare_source.py`：有 4 次重试但缺少单次调用 timeout。
- `ai/cursor_sdk_client.py`：`run.events()` 没有超时保护，bridge 异常时可能无限阻塞。
- `ai/deepseek_client.py`：无请求级重试，仅依赖 orchestrator 的 provider fallback。

#### 8）性能热点

| 位置 | 问题 |
|---|---|
| `data/snapshot.py:104-127` | 每次 RefreshLoop tick 全量重算 EMA20/ATR14，O(n) 重复计算 |
| `ai/kline_features.py:250` | 几何特征计算存在 O(n²) 嵌套循环 |
| `records/analysis_history.py:49-82` | 每次增量分析全量扫描 `records/pending/*.json` 并按 mtime 排序 |
| `records/pending_writer.py:133-154` | 每次保存递归遍历整个 `AnalysisRecord` 做 API key 替换 |
| `records/trade_logger.py:607-624` | 每次写 CSV 全量重写文件 |
| `ai/deepseek_client.py:466` | 每次调用新建 `_OpenAI(...)` 实例，不复用 HTTP client |
| `orchestrator/two_stage.py:423-430,715-721` | 每次 Stage 1/2 把完整 prompt 每条消息写入 DEBUG 日志 |

#### 9）数据层实现一致性不足

- `DataSource` ABC 未定义统一的 "forming bar" 语义，各实现自行判断：
  - MT5：默认 position 0 为 `closed=False`
  - TradingView：通过 `seconds_until_bar_closes` 计算
  - AkShare/EastMoney：依赖 A 股交易时段
  - Tushare/yfinance：所有 bar 直接 `closed=True`
- 缓存策略不一致：EastMoney/Tushare 有缓存，AkShare/MT5/yfinance 没有。
- 错误处理、重试策略差异大。
- `factory.py` 对 Tushare 直接读取 `settings.json`，让数据层反向依赖配置层。

#### 10）代码重复

- 策略文件名列表在 `ai/router.py`、`ai/prompt_assembler.py`、`ai/pattern_routing.py` 中多处硬编码。
- `_enrich_stage1_validation_message` 与 `_enrich_stage2_validation_message` 在 `two_stage.py` 中高度重复。
- QClaw/Cursor/WorkBuddy provider fallback 三部曲结构重复。
- MiMo assistant message 构建逻辑在 `validation_retry.py` 与 `prompt_assembler.py` 中重复。
- 价格区间解析函数在 `prompt_assembler.py` 与 `gui/main_window.py` 中重复。

### 4.3 低优先级

#### 11）类型注解遗留问题

- `AppContext` 字段全为 `Any`。
- `records/schema.py`、`util/logging.py` 仍使用 `Optional`、`List` 等旧 typing。
- `ai/pattern_routing.py`、`orchestrator/two_stage.py`、`prompt_assembler.py` 中部分参数为 `Any`。
- `main_window.py` 中 34 处 `Any` 使用。

#### 12）测试与 CI

- `.github/workflows/ci.yml` 仅做安装验证与 import 检查，**不运行 pytest，不跑 ruff/black**。
- pre-commit hook 是手写 shell，Windows 需执行 `tools/setup_git_secrets.ps1` 才会生效。

#### 13）路径/文件名安全

- `pending_writer.py:30-36` 文件名直接拼接 `symbol` 和 `timeframe`，未过滤 `/`、 `\`、`:`、`..`。
- `trade_logger.py:489-494` 仅替换 `/` 和 `\`，未处理 `..`、Windows 保留名。

#### 14）util 命名与全局日志状态

- `pa_agent/util/logging.py` 与 Python 标准库 `logging` 同名，易误导。
- `configure_logging()` 使用全局 `_configured` 状态，重复调用时先移除所有 handler，多线程/测试环境可能竞态。

---

## 5. 迭代路线图

### 5.1 近期（1-2 周，低风险、高回报）

| 编号 | 任务 | 目标文件 | 预期收益 |
|---|---|---|---|
| R1 | 提取策略文件注册表 | `ai/router.py`、`ai/prompt_assembler.py`、`ai/pattern_routing.py` | 消除重复，新增策略只需改一处 |
| R2 | 合并 Stage1/Stage2 校验错误富化函数 | `orchestrator/two_stage.py` | 减少 ~80 行重复代码 |
| R3 | 统一 provider fallback | `orchestrator/two_stage.py` | 抽象 QClaw/Cursor/WorkBuddy fallback |
| R4 | 清理旧 typing | `records/schema.py`、`util/logging.py` 等 | 匹配 Python 3.11+ 风格 |
| R5 | 给 `AppContext` 字段补全类型 | `app_context.py` | 恢复依赖注入的类型检查价值 |
| R6 | 替换裸 `except Exception: pass` | 全后端 | 至少记录 `logger.debug(..., exc_info=True)`，提升排障能力 |
| R7 | 修正 README / config/README 中 "API Key 加密" 的不实描述 | `README.md`、`config/README.md` | 避免误导用户 |
| R8 | 对全局可变状态加锁 | `prompt_assembler.py`、`analysis_history.py`、`eastmoney_extended.py`、`logging.py`、`decision_flow_viz.py` | 消除多线程 race |

### 5.2 中期（1-2 个月，需要一定重构）

| 编号 | 任务 | 目标文件 | 预期收益 |
|---|---|---|---|
| M1 | 拆分 `PromptAssembler` | `ai/prompt_assembler.py` | `Stage1PromptBuilder`、`Stage2PromptBuilder`、`KlineTableRenderer`、`ExperienceRenderer` |
| M2 | 拆分 `JsonValidator` | `ai/json_validator.py` | `SchemaValidator`、`BusinessRuleValidator`、`RetryFeedbackBuilder` |
| M3 | 拆分 `decision_nodes.py` | `ai/decision_nodes.py` | 按 §1/§2/§9/§11/preflight/risk 拆分子模块 |
| M4 | 拆分 `TwoStageOrchestrator.submit()` | `orchestrator/two_stage.py` | `_run_stage1`、`_run_stage2`、`_route_and_load_experience`、`_persist_result` |
| M5 | 提取 `ProviderSyncService` | `app_context.py`、`orchestrator/two_stage.py` | 将 QClaw/WorkBuddy/Cursor 同步与持久化抽出 |
| M6 | 统一数据源配置注入 | `data/factory.py`、`data/tushare_source.py` | 移除工厂对 `settings.json` 的直接读取 |
| M7 | 统一 forming bar 判定 | `data/base.py` + 各数据源 | 在 ABC 提供默认实现，允许子类覆盖 |
| M8 | 实现真正的本地 API Key 加密 | `pa_agent/security/`、`config/settings.py` | Windows DPAPI / macOS Keychain / Linux keyring |
| M9 | 修复 `PendingWriter` 动态 key 脱敏失效 | `app_context.py`、`gui/settings_dialog.py` | key 修改后同步更新 writer |
| M10 | 修复 `PendingWriter` 文件名 sanitization | `records/pending_writer.py`、`records/trade_logger.py` | 防止路径遍历与非法文件名 |

### 5.3 长期（3-6 个月，架构升级）

| 编号 | 任务 | 目标文件 | 预期收益 |
|---|---|---|---|
| L1 | 引入 Provider/数据源注册表（第二阶段治理切片完成） | `ai/client_factory.py`、`ai/provider_registry.py`、`data/factory.py`、`data/registry.py`、`tests/unit/test_registry.py` | AI client 与数据源支持规格注册、优先级/延迟 builder、运行时扩展及第一批生命周期/并发/lazy-import 证据；插件发现和正式扩展契约仍待完成，Provider 同步仍由现有 service 负责 |
| L2 | Prompt 模板引擎化 | `prompt_engineering/`、`ai/prompt_assembler.py` | 使用 Jinja2 或结构化模板，支持热更新 |
| L3 | 引入 Pipeline Builder（第一切片完成） | `orchestrator/pipeline/`、`orchestrator/two_stage.py` | 已有 state/step/terminal status 协议和 legacy wrapper；后续用真实阶段步骤逐步替代巨型 `submit()`，并验证旧/新事件与记录等价 |
| L4 | 性能优化 | `data/snapshot.py`、`ai/kline_features.py`、`records/analysis_history.py`、`records/pending_writer.py`、`ai/deepseek_client.py` | 增量指标、索引、追加写、复用 HTTP client |
| L5 | 经验库升级（第二阶段完成） | `records/experience_reader.py`、`records/experience_similarity.py` | Stage 2 先按全量案例的 pattern + direction 排序，再以最近 K 线几何相似度打破同分并列；无 K 线字段的旧案例保持兼容 |
| L6 | 无 GUI 运行支持（headless runner 第一切片完成） | `util/events.py`、`util/event_sink.py`、`util/event_bus.py`、`app_context.py`、`cli.py`、`records/pending_writer.py` | 默认 dry-run 保持无网络；显式 `--run/--execute` 已复用 `TwoStageOrchestrator` 写入 final/partial record，并输出 correlation JSONL 事件；后续 GUI/headless 等价、真实 Provider 验证和公开 adapter 契约 |
| L7 | CI 增强 | `.github/workflows/ci.yml` | 运行 `pytest -m "not e2e"`、ruff、black、覆盖率 |

---

## 6. 关键文件索引

| 文件 | 行数 | 主要职责 | 当前主要问题 |
|---|---|---|---|
| `pa_agent/gui/main_window.py` | ~4386 | GUI 主窗口、部分业务逻辑 | God Object，220+ 方法 |
| `pa_agent/ai/decision_nodes.py` | ~3071 | 决策节点引擎 | 超大模块，循环依赖 |
| `pa_agent/ai/prompt_assembler.py` | ~1953 | Prompt 组装 | 超大类，84 KB 硬编码 prompt |
| `pa_agent/ai/stage2_normalizer.py` | ~1800 | Stage 2 输出归一化 | 高耦合，中文字符串规则 |
| `pa_agent/orchestrator/two_stage.py` | ~1217 | 两阶段编排 | `submit()` 646 行，职责过重 |
| `pa_agent/ai/json_validator.py` | ~1165 | JSON 校验与修复 | 职责过多 |
| `pa_agent/app_context.py` | ~143 | 依赖装配 | 字段全 `Any`，启动期副作用 |
| `pa_agent/config/settings.py` | ~280 | 配置模型 | API Key 明文存储 |
| `pa_agent/data/factory.py` | ~103 | 数据源工厂 | 硬编码 if/elif，反向依赖 settings |
| `pa_agent/records/pending_writer.py` | ~154 | 记录写入 | 递归 sanitize、文件名未过滤 |
| `pa_agent/records/trade_logger.py` | ~624 | 交易 CSV/截图日志 | 全量重写 CSV |
| `pa_agent/ai/deepseek_client.py` | ~600+ | OpenAI 兼容客户端 | 每次新建 client，无重试 |
| `pa_agent/data/mt5.py` | ~263 | MT5 数据源 | 无超时 |
| `pa_agent/util/logging.py` | ~153 | 日志配置 | 全局状态无锁 |

---

## 7. 下一步建议

L1-L6 的详细边界、依赖顺序、迁移开关、验收标准和回滚策略以
[`docs/architecture_roadmap.md`](./architecture_roadmap.md) 为准；本节保留审查报告的高层优先级。

建议按以下顺序开始后续迭代：

1. **先推进 L6/L3 等价 harness**：真实 Provider runner、JSONL 事件重放、Pipeline state/step
   与旧 `submit()` 的 record/事件等价。
2. **等待数据后推进 L5 离线评估**：固定 train/evaluation 切分、Recall/NDCG 和 ranking stability。
3. **收口 L4 性能预算与 L1 扩展治理**：使用固定 fixture 的 p50/p95 基准，不凭感觉修改热路径。
4. **观察 L2 兼容周期**：持续记录新旧 prompt 等价结果，稳定后再评估旧 loader/helper 和 feature
   flag 的下线。

---

*本报告基于当前代码实际状态生成，后续若引入加密、新增数据源/提供商、调整构建或测试流程，应同步更新 `AGENTS.md` 与本报告。*
