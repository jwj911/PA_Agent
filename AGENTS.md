<!-- AGENTS.md for PA Agent -->

# PA Agent — AI 编码代理须知

> 本文件面向不熟悉本项目的 AI 编码代理。阅读后，你应该对项目目标、技术栈、模块划分、构建/测试流程、安全约束有清晰了解，再开始修改代码。

---

## 1. 项目概述

**PA Agent** 是一款面向主观交易者的 **价格行为（Price Action）AI 辅助决策桌面程序**。

- 从 **MT5 / TradingView / AkShare / 东方财富 / Tushare / yfinance** 等数据源读取 K 线；
- 将结构化 K 线数据与预计算特征送入大模型，执行 **两阶段分析**：
  1. **阶段一**：市场诊断（周期位置、方向、关键信号、策略文件路由）；
  2. **阶段二**：交易决策（是否下单、限价/突破/市价、入场/止损/止盈、决策树 trace）。
- 支持 **增量分析**、**持续跟踪**、**自由追问**、**决策树可视化**、**下一根 K 线预测**；
- **不连接券商、不执行真实下单**，仅作为分析辅助工具输出建议。

项目主要文档语言为 **简体中文**；代码内部的技术术语、模块/类/函数名、类型注解以英文为主，但大量注释、日志、用户提示、prompt 为中文。

相关文档：

- 用户操作文档：[`PA_Agent使用文档.md`](./PA_Agent使用文档.md)
- 配置字段说明：[`config/README.md`](./config/README.md)
- 贡献指南：[`CONTRIBUTING.md`](./CONTRIBUTING.md)
- 安全策略：[`SECURITY.md`](./SECURITY.md)
- 迭代记录：[`docs/CHANGELOG.md`](./docs/CHANGELOG.md)
- 架构升级路线图：[`docs/architecture_roadmap.md`](./docs/architecture_roadmap.md)
- 短中期执行计划：[`docs/iteration_plan.md`](./docs/iteration_plan.md)，在长期边界以
  `architecture_roadmap` 为准的前提下，拆解后续若干轮交付物、验收标准和依赖顺序。

---

## 2. 技术栈与运行环境

| 项目          | 说明                                                    |
| ------------- | ------------------------------------------------------- |
| 语言          | Python >= 3.11                                          |
| 主操作系统    | Windows 10 / 11（MT5 数据源仅 Windows）                 |
| GUI 框架      | PyQt6 + pyqtgraph                                       |
| 数据处理      | numpy、pandas                                           |
| LLM 客户端    | openai（OpenAI 兼容协议）+ cursor-sdk                   |
| 配置校验      | Pydantic v2                                             |
| JSON Schema   | jsonschema                                              |
| Token 计数    | tiktoken                                                |
| A 股数据源    | akshare、baostock、tushare、东方财富客户端              |
| 国际市场      | MetaTrader5（Windows）、TradingView（tvdatafeed）、yfinance |
| 通知          | 飞书机器人、PushPlus                                    |
| 加解密        | cryptography；Windows DPAPI（`ctypes` + `crypt32`）     |

完整依赖与构建配置见 [`pyproject.toml`](./pyproject.toml)。

---

## 3. 项目结构与模块划分

```
price_action_agent/
├── pa_agent/            # 主程序包
│   ├── cli.py           # PyQt-free headless CLI adapter
│   ├── main.py          # 应用入口
│   ├── app_context.py   # 依赖容器与启动装配
│   ├── ai/              # LLM 客户端、prompt 组装、JSON 校验、归一化、策略路由
│   ├── config/          # 路径常量、Pydantic 配置模型和 rollout 开关
│   ├── data/            # 数据源抽象与实现
│   ├── demo/            # 记录加载器与回放器
│   ├── gui/             # PyQt6 主窗口、对话框、widgets、主题
│   ├── indicators/      # EMA、ATR 等技术指标
│   ├── notify/          # 飞书、PushPlus 通知
│   ├── orchestrator/    # 两阶段分析流水线、Pipeline state/step、自由追问、校验重试
│   ├── records/         # 分析记录持久化、经验库读取、交易日志
│   ├── security/        # API Key 至静态加密（Windows DPAPI）
│   └── util/            # 日志脱敏、事件总线、崩溃诊断、线程、时间格式化等
├── config/              # 本地配置模板（运行时配置被 gitignore 忽略）
├── docs/                # 项目文档
├── experience/          # 经验库案例目录（被 gitignore 忽略）
├── logs/                # 日志（被 gitignore 忽略）
├── prompt_engineering/  # 阶段一/阶段二策略 prompt 文本与参考资料
├── records/             # 分析记录落盘（被 gitignore 忽略）
├── scripts/             # 审计/工具脚本
├── tests/               # 测试（unit / integration / property / e2e）
├── tools/               # 诊断、调试、网关探测脚本
├── trade_records/       # 交易 CSV/截图日志（被 gitignore 忽略）
├── pyproject.toml       # 项目配置与依赖
├── Makefile             # 常用命令封装
├── run.py               # 推荐直接双击/终端启动脚本
└── README.md
```

### 3.1 核心启动流程

1. `run.py` 检测是否在 Spyder/Jupyter IPython 内核中；若是，启动独立子进程避免 `kernel died`；
2. `pa_agent.main:main()`：
   - 启用崩溃诊断与文件日志；
   - 创建 `QApplication` 并应用主题；
   - 调用 `AppContext.bootstrap()`（兼容 facade，当前委托 `AppContext.bootstrap_gui()`）装配 GUI 运行路径；
   - 创建 `MainWindow(ctx)` 并显示。
3. `AppContext.bootstrap_gui()`（`pa_agent/app_context.py`）：
   - 加载 `config/settings.json`；
   - 通过 `provider_sync_service` 同步特殊 provider（QClaw / WorkBuddy / Cursor）配置；
   - 配置日志（API Key 脱敏）；
   - 创建 Qt `EventBus`，并把 `event_sink` 指向该 `EventBus`；
   - 创建数据源，执行连接和默认 symbol/timeframe 订阅；
   - 复用共享 core helper 创建 AI 客户端、`PromptAssembler`、`JsonValidator`、记录写入器、经验库读取器等。
4. `AppContext.bootstrap()` 保持旧 GUI 入口兼容，公开签名不变，委托到 `bootstrap_gui()`。
5. `AppContext.bootstrap_headless()` 提供无 GUI 核心装配：
   - 复用同一共享 core helper；
   - 不导入或创建 Qt `EventBus`，使用显式 `EventSink` 或默认 `NullEventSink`；
   - 不连接数据源；
   - 创建 AI 客户端、Prompt、Validator、PendingWriter、ExperienceReader、SessionLedger 等核心组件。
6. `pa-agent headless ...` / `python -m pa_agent.main headless ...` 进入 `pa_agent.cli`：
   - 不导入或创建 Qt `EventBus`；
   - `validate-config` 严格校验 settings JSON；
   - `snapshot` 规范化显式输入的 K 线 JSON；
   - `analyze` 当前仅执行 provider-free Stage 1 prompt dry-run，不调用 Provider、不写入真实分析记录。

### 3.2 关键子包职责

- **`pa_agent/ai/`**：项目核心算法层。
  - `client_factory.py`：根据模型选择客户端（DeepSeekClient / CursorSdkClient）。
  - `provider_registry.py`：AI 客户端 Provider 规格注册表与优先级 matcher。
  - `deepseek_client.py`：OpenAI 兼容通用客户端，支持流式、reasoning_content、KV cache，内置 MiMo、QClaw、WorkBuddy、PackyAPI、KKAI、MiniMax 等网关适配。
  - `provider_sync_service.py`：provider 同步服务，集中启动期编排 QClaw → WorkBuddy → Cursor 的同步与降级尾部处理。
  - `cursor_sdk_client.py` / `cursor_connector.py`：Cursor SDK 路由。
  - `qclaw_connector.py` / `qclaw_relay.py` / `qclaw_relay_manager.py`：QClaw 本地网关。
  - `workbuddy_connector.py`：WorkBuddy / CodeBuddy 环境检测与 DPAPI 解密取 token。
  - `prompt_assembler.py`：阶段一/阶段二 prompt 组装总入口。
  - `prompting/template_manifest.py` / `prompting/template_store.py` / `prompting/template_context.py` /
    `prompting/compatibility.py`：PyQt-free 模板元数据、显式 JSON 可序列化上下文、严格 UTF-8 加载、
    缓存和 golden snapshot 契约；共享 system、Stage 1 user prompt、Stage 2/continuation 均支持
    TemplateStore 整组加载、旧路径回退和 `use_template_store=False` 回滚。关键 render 路径只记录
    模板/阶段/键名/占位符/长度等安全元数据，不记录变量值或完整 prompt。
  - `stage1_prompt_builder.py` / `stage2_prompt_builder.py`：阶段一/阶段二 user prompt 构建器。
  - `kline_table_renderer.py` / `experience_renderer.py` / `stage2_guidance.py` / `chain_context.py` / `program_prefill_hint.py`：prompt 渲染子模块（PyQt6-free 叶子模块）。
  - `json_validator.py` / `json_repair.py` / `business_rules.py` / `schema_validator.py`：阶段一/阶段二 JSON 校验、修复、业务规则与 schema 校验。
  - `stage1_normalizer.py` / `stage2_normalizer.py` / `trace_normalize.py`：LLM 输出归一化。
  - `decision_node_engine.py` / `decision_nodes.py` / `decision_tree.py` / `decision_stance.py`：决策树、立场、节点逻辑。
  - `decision_thresholds.py` / `bar_geometry.py` / `trace_nodes.py` / `preflight.py` / `signal_bar_judges.py` / `direction_judge.py` / `diagnostic_judges.py` / `always_in_judges.py` / `override_arbiter.py` / `order_method_router.py` / `signal_context.py`：决策节点拆分后的叶子模块。
  - `strategy_files.py`：策略/提示 `.txt` 文件名的单一事实来源。
  - `prompts/schemas.py`：JSON schema 定义。
  - `session_ledger.py`：Token 用量与上下文窗口追踪。

- **`pa_agent/config/`**：配置与路径。
  - `settings.py`：Pydantic v2 配置模型与读写；支持旧字段迁移。
  - `orchestrator.py`：PyQt-free Pipeline rollout 配置；`orchestrator.pipeline_builder_enabled`
    默认 `false`，旧配置缺少该 section 时保持 legacy 默认。
  - `paths.py`：集中管理项目根目录、配置、日志、记录、prompt 目录等路径常量。

- **`pa_agent/data/`**：市场数据层。
  - `factory.py`：数据源注册表 facade 与兼容工厂，返回 MT5 / TradingView / AkShare / EastMoney / Tushare / YFinance 源。
  - `registry.py`：数据源规格注册表与延迟 builder，支持运行时注册/注销自定义数据源。
  - `base.py`：通用数据模型 `KlineFrame`、`KlineBar`、`IndicatorBundle` 与 `DataSource` ABC。
  - `mt5.py` / `tradingview.py` / `tradingview_connectivity.py` / `akshare_source.py` / `eastmoney_source.py` / `tushare_source.py` / `yfinance_source.py`：各数据源实现。
  - `snapshot.py` / `bar_close_wait.py` / `refresh_loop.py`：实时刷新、K 线收盘等待与快照构建。
  - `kline_adjust.py` / `market_defaults.py`：复权调整与市场默认值。

- **`pa_agent/gui/`**：PyQt6 GUI。
  - `main_window.py`：主窗口（功能高度集中，约 4000+ 行）。
  - `settings_dialog.py` / `ai_model_settings_dialog.py` / `general_settings_dialog.py` / `feishu_settings_dialog.py`：设置对话框。
  - `decision_flow_viz.py` / `decision_panel.py` / `decision_tree_panel.py`：决策可视化。
  - `chart_widget.py` / `widgets/`：K 线图表与自定义 widgets。
  - `theme/`：QSS 主题与 token。
  - `ai_stream_window.py` / `conversation_widget.py`：实时推理流与会话管理。

- **`pa_agent/orchestrator/`**：业务编排。
  - `two_stage.py`：两阶段分析主流程。
  - `pipeline/`：PyQt-free `PipelineState`、`TerminalStatus`、`PersistenceIntent`、
    `PipelineStep`、`StepResult`、`PipelineBuilder`、`Stage1Step`、`RouteStep`、`Stage2Step`
    和 `PersistStep`。当前 state 显式承载 Stage 1/Stage 2 payload、usage、route 输出、
    Stage 2 flags、partial reason、持久化意图和 `persistence_pending`，并提供不暴露运行时
    payload 的 safe summary；opt-in sequence 为
    `Stage1Step -> RouteStep -> Stage2Step -> PersistStep`。PersistStep 负责 full/partial
    record assembly/write、磁盘失败映射和 `RecordSaved` ordering；`LegacyPersistStep` 仅保留
    兼容名称，默认 `submit()` 路径保持兼容。
  - `free_chat.py`：分析后自由追问与会话管理。
  - `validation_retry.py`：校验失败后的重试策略。

- **`pa_agent/records/`**：持久化。
  - `pending_writer.py`：分析记录写入（自动对明文 API Key 脱敏）。
  - `experience_reader.py`：经验库读取。
  - `experience_similarity.py`：基于最近 K 线几何的可选经验案例相似度评分。
  - `trade_logger.py`：交易 CSV/截图日志。
  - `analysis_history.py`：历史记录管理。
  - `schema.py`：记录数据结构定义。

- **`pa_agent/security/`**：本地安全。
  - `secret_store.py`：API Key **至静态加密**（Windows DPAPI，非 Windows 优雅降级）。

- **`pa_agent/util/`**：通用工具。
  - `logging.py`：日志配置与 API Key 掩码格式化。
  - `mask_secret.py`：密钥掩码函数。
  - `safe_filename.py`：安全文件名组件。
  - `events.py` / `event_sink.py`：PyQt-free 应用事件对象与 headless 事件端口。
  - `event_bus.py`：Qt 事件总线，兼容旧 signal，并可发布 `AppEvent`。
  - `crash_diagnostics.py`：崩溃诊断与启动信息记录。
  - `threading.py`：取消令牌、worker 事件等并发原语。
- **`pa_agent/cli.py`**：PyQt-free headless 命令适配器；只接收显式 JSON/settings 输入，
    stdout 输出结构化 JSON，诊断写 stderr；`analyze` 默认 dry-run，只有显式 `--run/--execute`
    才调用 Provider 并写入 final/partial record，不能在此层加入真实下单或隐式数据源连接。

---

## 4. 构建与运行命令

项目使用标准 Python 打包工具 setuptools，安装命令：

```cmd
# 基础安装
pip install -e .

# 开发安装（包含 pytest、pytest-qt、hypothesis、ruff、black）
pip install -e ".[dev]"
```

启动方式（任选其一）：

```cmd
# 推荐：直接双击 run.py，或终端执行
python run.py

# 作为模块运行
python -m pa_agent.main

# 若已 pip install，使用入口脚本
pa-agent

# Makefile 封装
make run
```

> 注意：`run.py` 针对 Spyder/Jupyter 内核做了特殊处理，避免 `The kernel died`。在普通终端直接执行即可。

### 4.1 常用 Makefile 命令

| 命令               | 作用                                         |
| ------------------ | -------------------------------------------- |
| `make run`         | 启动 GUI                                     |
| `make test`        | 运行全部测试（`pytest -q`）                  |
| `make lint`        | 代码检查（`ruff check . && black --check .`）|
| `make setup-secrets` | 启用 pre-commit 钩子                       |

---

## 5. 代码风格规范

- **Python 版本**：>= 3.11。
- **格式化**：Black，行宽 100（`pyproject.toml` 配置）。
- **Lint**：Ruff，启用规则 `E, F, I, UP, B, SIM, RUF`，忽略 `E501`。
- **导入排序**：由 Ruff `I` rule 管理，通常不需要手动调整。
- **类型注解**：全面使用，文件开头通常写 `from __future__ import annotations`。统一采用 Python 3.11+ 风格：`X | None`、内置泛型 `list[...]`/`dict[...]`、`Callable` 从 `collections.abc` 导入（仅注解用途可置于 `TYPE_CHECKING` 块）。例外：`records/schema.py` 因 Pydantic v2 需即时求值字段注解，不加 `from __future__ import annotations`。
- **命名**：模块/函数/变量使用小写下划线；类使用 CamelCase。
- **注释/文档字符串**：模块级和重要函数多为英文注释；用户可见字符串、日志、prompt、GUI 标签大量使用中文。
- **异常处理**：常见 `except Exception` 并标注 `# noqa: BLE001`。
- **字符串引号**：代码字符串优先双引号，与 Black 默认一致。

常用命令：

```cmd
# 代码检查
make lint
# 等价于
ruff check . && black --check .

# 自动格式化
black .
ruff check --fix .
```

---

## 6. 测试策略与运行方式

测试位于 `tests/`，分为四层：

| 目录                | 说明                                           | 标记            |
| ------------------- | ---------------------------------------------- | --------------- |
| `tests/unit/`       | 单元测试，覆盖数据源、AI 组件、GUI widgets、校验器、记录器等 | `unit`          |
| `tests/integration/`| 两阶段流水线集成测试，使用共享 `conftest.py`   | `integration`   |
| `tests/property/`   | 基于 Hypothesis 的属性测试                     | `property`      |
| `tests/e2e/`        | 使用 `pytest-qt` 驱动真实 `MainWindow` 的冒烟测试 | `e2e`           |

特殊标记：

- `live`：需要真实网络或 API Key（如 `test_akshare_live.py`、`test_kkai_thinking_live.py`），**绝不读取 `config/settings.json`**，仅通过环境变量获取密钥。

运行方式：

```cmd
# 运行全部测试
pytest -q
make test

# 按分层运行
pytest -m unit
pytest -m integration
pytest -m property
pytest -m e2e

# 跳过 E2E（贡献者推荐）
pytest -m "not e2e"

# 仅运行真实网络/API 测试（谨慎）
pytest -m live
```

**测试约定**：

- 修改 JSON schema、提示词、策略路由、决策节点时，请补充或更新对应测试用例。
- CI（`.github/workflows/ci.yml`）在 Windows + Python 3.11/3.12 矩阵下执行安装/import 验证、
  CI 目标清单检查、`QT_QPA_PLATFORM=offscreen` 目标测试（带覆盖率）、非 live 非 e2e 回归、
  Ruff baseline、focused Ruff 和 focused Black 检查。
- 提交前建议至少运行与改动相关的目标测试；较大改动应补跑 `pytest -m "not e2e"`。

---

## 7. 安全配置与密钥处理

### 7.1 实际行为

- `config/settings.json` 中的 API Key 采用 **至静态加密（encryption at rest）**，实现见 `pa_agent/security/secret_store.py`：
  - **Windows**：保存时经 **DPAPI**（`CryptProtectData`/`CryptUnprotectData`，`ctypes` 直调 `crypt32`）把明文加密为自描述令牌 `dpapi:v1:<base64(blob)>` 写入 `provider.api_key_encrypted`，磁盘上的 `provider.api_key` 置空；加载时 `load_settings` 解密回内存态 `provider.api_key`。
  - **非 Windows / DPAPI 不可用**：`encrypt_secret` 返回 `None`，优雅降级为**明文至静态**。
  - **向后兼容**：磁盘上的旧明文 key 照常加载，并在下次保存时自动加密。
  - **加密仅改磁盘表示**：内存态 `provider.api_key` 始终为明文，所有调用方零改动。

密钥安全依赖多层防护：

1. **至静态加密**：Windows 下 DPAPI 加密存盘（见上）；非 Windows 回退明文。
2. **Git 忽略**：`config/settings.json` 等敏感文件已被 `.gitignore` 排除。
3. **pre-commit 拦截**：`.githooks/pre-commit` 阻止提交 `settings.json`、`.env`、日志、分析记录，并扫描 diff 中的 `api_key` / `api_key_encrypted` / `sk-...` 模式。
4. **运行时脱敏**：
   - `pa_agent/util/mask_secret.py`：掩码函数（保留最后 4 位，其余替换为 `*`）。
   - `pa_agent/util/logging.py`：`MaskingFormatter` 在日志输出前替换明文 API Key。
   - `pa_agent/records/pending_writer.py`：序列化记录前递归扫描并替换明文 API Key。

### 7.2 开发者必须遵守的安全规范

- **绝不**将 `config/settings.json`、`config/exception_state.json`、`.env`、密钥文件加入 Git。
- **绝不**在测试、日志、错误信息中硬编码真实 API Key。
- 修改涉及密钥读取/保存的代码时，确保：
  - 保存到文件前仍经过脱敏或保持在 gitignored 文件中；
  - 日志和持久化记录中不出现明文 key；
  - **密钥落盘统一走 `save_settings`**（内部对 `provider.api_key` 施加至静态加密），不要绕过它直接写 `settings.json`；
  - 如需新增密钥字段，同步更新 `.gitignore` 与 `.githooks/pre-commit`。
- 建议新贡献者运行：

```cmd
powershell -ExecutionPolicy Bypass -File tools\setup_git_secrets.ps1
```

### 7.3 安全文件名

- `pa_agent/util/safe_filename.py` 提供 `sanitize_filename_component`，用于把 `symbol`/`timeframe` 等用户输入转换为安全的文件路径组件，防止路径遍历与 Windows 保留名问题。
- 任何把用户输入拼入文件名的场景，都应优先使用该工具。

---

## 8. 外部集成

### 8.1 AI 提供商

支持多种 OpenAI 兼容网关与专用 SDK：

- **DeepSeek**：原生 OpenAI 兼容，支持 thinking / reasoning_effort / KV cache。
- **QClaw**：本地网关（`~/.qclaw/openclaw.json`），模型别名 `openclaw` / `openclaw/*`。
- **Cursor**：`cursor-sdk`，模型别名 `openclaw_cs` / `openclaw_cs/*`。
- **WorkBuddy / CodeBuddy**：`copilot.tencent.com/v2`，模型别名 `openclaw_wb`。
- **PackyAPI**、**KKAI**、**MiniMax**、**MiMo** 等网关适配见 `deepseek_client.py` / `mimo_compat.py`。

### 8.2 数据源

- **MT5**（`MetaTrader5`）：Windows 主数据源。
- **TradingView**：通过 `tvdatafeed` 库。
- **AkShare**：A 股数据。
- **EastMoney**：A 股（东方财富）。
- **Tushare**：A 股（需 token）。
- **Baostock**：部分场景作为 fallback。
- **YFinance**：期货/加密货币。

### 8.3 通知

- **飞书（Feishu）**：自定义机器人 webhook，支持签名、tenant_access_token、图片上传、交互卡片。
- **PushPlus**：简单 HTTP 推送。

---

## 9. 部署与发布

- 当前项目 **没有** 构建独立可执行文件（如 PyInstaller / Nuitka / cx_Freeze）的流程。
- 部署方式以源码运行或 `pip install -e .` 为主：
  - Windows 用户：直接双击 `run.py` 或在终端执行 `python run.py`。
  - 开发者：`pip install -e ".[dev]"` 后使用 `make run` / `python -m pa_agent.main`。
- CI（`.github/workflows/ci.yml`）在 `push` / `pull_request` 到 `main` 时触发，运行于
  `windows-latest` + Python 3.11/3.12：
  - 安装依赖并验证 `import pa_agent`；
  - 检查 `scripts/check_ci_workflow_targets.py` 目标清单；
  - 在 `QT_QPA_PLATFORM=offscreen` 下运行 targeted pytest（含覆盖率门槛）；
  - 运行非 live 非 e2e 测试；
  - 运行 `scripts/check_ruff_baseline.py`、focused Ruff 和 focused Black。
- `tools/` 目录包含大量一次性诊断脚本（网关探测、stage2 JSON 调试、MT5 时钟偏移检测等），不属于正式发布流程。

---

## 10. 给 AI 代理的实用提示

1. **先读配置再改代码**：很多行为由 `config/settings.json` 与 `pa_agent/config/settings.py` 中的 Pydantic 模型控制。新增配置字段时，同步更新 example 文件、GUI 设置对话框、相关测试。
2. **Prompt 文本在 `prompt_engineering/`**：策略路由、阶段一/阶段二的 prompt 片段多为中文 `.txt` 文件。修改这些文件可能改变模型输出格式，需要同步更新 `tests/` 中的 JSON fixture 与校验用例；涉及文件顺序、阶段边界、Spike/Climax 或硬禁令时，至少运行 `tests/unit/test_prompt_txt_files.py`、`tests/unit/test_prompt_assembler.py` 和 `tests/unit/test_template_store.py`，并复核 `tests/fixtures/prompt_golden.json`。确保阶段一不输出三价、阶段二保留 Stage 1 JSON/`decision_trace`/`terminal`/不下单空值规则，并继续满足禁止逆势三价、禁止 SCS/追高潮、禁止仓位管理和不依赖成交量的合同。
3. **JSON schema 在 `pa_agent/ai/prompts/schemas.py`**：阶段一/阶段二的输出结构严格受 schema 约束，改动需同步更新 `json_validator.py` 与 normalizer。
4. **MainWindow 是巨型文件**：`pa_agent/gui/main_window.py` 接近 4000+ 行。做小改动时优先定位到具体方法；做大重构时建议与维护者沟通。
5. **API Key 至静态加密，但内存态是明文**：磁盘上（Windows）经 DPAPI 加密为 `dpapi:v1:` 令牌存于 `api_key_encrypted`，非 Windows 回退明文；但**内存态 `provider.api_key` 始终为明文**。任何涉及密钥持久化的新功能都要统一走 `save_settings`（自动加密），任何日志/记录落盘仍须经运行时脱敏。
6. **优先用测试验证**：本项目测试覆盖较全，改动后请运行相关分层测试；涉及 LLM 输出解析的改动建议同时跑 `unit` 与 `integration`。
7. **保持中文用户界面**：新增用户可见字符串、日志、提示信息时，默认使用简体中文。
8. **每次迭代必须更新变更日志**：任何代码更新/修复/优化完成后，都要在 [`docs/CHANGELOG.md`](./docs/CHANGELOG.md) 追加或更新对应条目，不得只改代码而不记录。
9. **新增文件/字段时注意更新本文件**：如果你新增了模块、数据源、AI 提供商、安全机制、构建流程等，请同步更新本 `AGENTS.md` 中的对应章节。
10. **热路径注意性能**：`data/snapshot.py`、`ai/kline_features.py`、`records/analysis_history.py`、`ai/deepseek_client.py` 等属于高频路径，改动时避免重复计算与无条件构造大字符串。
11. **进程级缓存/全局状态需线程安全**：后台 QThread 会并发访问模块级缓存。新增全局可变状态时，应配套加锁（耗时构建/IO 放锁外，用双检锁），保持输出与语义不变。
12. **L1 当前进度**：数据源注册表和 AI Provider 注册表已完成第二阶段基础与第一批治理测试，
    支持规格、优先级 matcher、延迟 builder、运行时注册，以及规范化 key、replace/unregister、
    并发读写、lazy-import 和 entry point 扩展发现证据；必须保留 `openclaw_cs` → Cursor SDK 的专用路由，以及其余
    模型 → OpenAI-compatible client 的兼容行为。Provider 同步仍由 `ProviderSyncService`
    负责，不得重复搬入 registry 或 client factory。未知数据源配置已在 settings 加载时安全回退到
    `mt5` 并持久化规范化值；扩展 registrar 通过 `pa_agent.extensions` 的
    `pa_agent.data_sources`/`pa_agent.ai_clients` entry point group 注册，失败隔离且不扫描任意目录；
    外部扩展兼容观察和版本化契约策略仍待收口。
13. **L6 当前进度**：`AppContext` 已拆出共享 core helper 和 `bootstrap_gui()`；`bootstrap()`
    委托 GUI 路径。headless 复用 core helper，必须继续保持无 Qt `EventBus` import、无数据源连接；
    GUI adapter 继续负责 `EventBus`、数据源连接/订阅，且 `event_sink` 指向 `EventBus`。第 229 轮已
    新增 `pa_agent.cli` 和 `pa-agent headless` 最小入口，第 234 轮已新增 PyQt-free JSONL
    `JsonlEventSink`/`replay_jsonl`，第 237 轮新增显式 `analyze --run/--execute` 两阶段 runner、
    final/partial record 持久化、稳定退出码和 correlation 事件输出；公开
    `pa_agent.headless.HeadlessAnalysisAdapter` 统一 headless 执行边界。本轮已扩展其阶段回调
    合同，并用真实 GUI `_AnalysisWorker` 对照固定 fixture 的 final/partial/cancel/failure
    record、milestone/status、prompt 和流式内容；JSONL 新事件必须写入
    `schema="pa-agent.event.v1"`，未知 schema 拒绝，旧缺失 schema 事件继续可回放。默认
    `analyze` 仍必须保持 provider-free dry-run；真实 Provider 环境观察、真实运行 record/事件
    证据和跨进程 correlation 重放仍未收敛。
14. **架构任务先读两份计划**：长期模块边界、迁移原则和完成定义以
    [`docs/architecture_roadmap.md`](./docs/architecture_roadmap.md) 为准；短中期优先级、每轮建议
    交付物、验收标准和依赖顺序见 [`docs/iteration_plan.md`](./docs/iteration_plan.md)。
15. **L2 当前进度**：第 230 轮建立 `TemplateStore`、29 个模板 manifest 和 UTF-8 golden
    digest；第 231 轮迁移共享 system prompt，第 232 轮迁移 Stage 1 user prompt，第 233 轮迁移
    Stage 2/continuation 并新增 `TemplateContext`。所有迁移均保留 `use_template_store=False`、
    严格失败 warning 回退和固定 fixture 字节等价证据；后续不得顺手重写中文策略文本。
16. **L3 当前进度**：第 238 轮新增 PyQt-free `orchestrator/pipeline/`，定义
    `PipelineState`、`TerminalStatus`、`PipelineStep`、`StepResult` 和 `PipelineBuilder`，
    并通过 `TwoStageOrchestrator.run_pipeline()` / `submit_pipeline()` 提供 opt-in
    compatibility adapter。Task 5 扩展 `PipelineState` 承载 Stage 1/Stage 2 messages、
    reply/raw response 引用、normalized JSON、usage、route outputs、`PersistenceIntent`、
    partial reason 和 `persistence_pending`，补充 `route_failed`/`persist_failed` 映射，以及
    callbacks、Provider client、prompt/reply 正文、行情数据、密钥和 URL path/query/fragment
    不进入的安全摘要。Task 6 已交付真实 `Stage1Step`，Task 7 已交付真实 `RouteStep`，Task 8
    已交付真实 `Stage2Step`，Task 9 已交付真实 `PersistStep`；Task 10 新增
    `orchestrator.pipeline_builder_enabled`（默认 `false`）和 Settings round-trip/旧配置
    legacy 默认测试。`submit()` flag-off 走 legacy，flag-on 委托完整
    `Stage1Step -> RouteStep -> Stage2Step -> PersistStep` Pipeline。Task 10 还补充完整终态
    矩阵、Qt-free headless/GUI adapter equivalence 测试，并将
    `tests/integration/test_task10_pipeline_rollout.py` 纳入 CI targeted pytest、
    `pa_agent/config/orchestrator.py` 纳入 focused Ruff/config target。PersistStep 集中
    full/partial record assembly/write，前置终态通过 `persistence_pending` 防止重复保存，使用
    `PendingWriter.last_write_succeeded` 识别磁盘失败，full 写入成功后才发出 `RecordSaved`，
    partial 或磁盘失败不发成功事件。默认 `submit()` 和 GUI/headless 调用路径仍保持 legacy；
    本轮已用 5 个终态场景 × 3 轮固定 fixture 完成 flag-off/flag-on 的 record、事件、prompt、
    流式内容、策略文件和写入边界对照；这只是受控 rollout evidence，不是生产稳定观察。
    后续需真实 Provider 稳定观察周期和 GUI/headless 真实运行 final/partial/cancel/failure
    evidence 后才评估启用默认 flag。
17. **L3 Pipeline 生命周期日志**：Pipeline enabled 路径以同一 `trace_id` 关联一次执行，
    使用 `pipeline.lifecycle`、`pipeline.event`、`pipeline.step` 和 `pipeline.timing` 四类结构化事件；主要字段
    为 `pipeline_step`、结果/终态分类、异常类型分类、耗时、跳过原因、写入状态和
    `PipelineState.safe_summary()`。查询时可按 `trace_id` 聚合，按上述事件名过滤，再按
    `pipeline_step` 重建 `Preflight -> Stage1 -> Route -> Stage2 -> Persist`；
    `pipeline.timing` 在 Stage 2 启动前记录 Stage 1/Route 边界耗时。日志只允许
    allowlist 安全字段，不得写入原始行情、股票/合约代码、价格、prompt/Provider 原文、
    API Key、Provider Token、callbacks 或 client。`orchestrator.pipeline_builder_enabled`
    默认仍为 `false`，flag-off 必须保持 legacy `submit()`、事件顺序、retry/cancel 语义和
    final/partial record 不变；真实稳定观察周期及 GUI/headless final/partial/cancel/failure
    全链路 evidence 完成前，不得启用默认 flag。本轮已同步业务代码、聚焦测试和项目文档/
    规格，并已纳入原子提交/推送。
18. **L5 经验库评估当前进度**：经验目录当前只有占位文件，禁止把合成 fixture 的指标当作
    真实检索质量结论。`pa_agent.records.experience_eval` 提供
    `pa-agent.experience-eval.v1` dataset envelope、`kline-geometry.v1` feature version、
    opaque instrument id 数据合同和离线 `Recall@K`/`NDCG@K`/fallback/stability scorer；
    评估数据不得包含价格、K 线原文、截图路径、密钥或本地绝对路径。真实脱敏数据集、
    固定切分、人工标注和线上权重校准仍待完成，不得顺手修改 `ExperienceReader` 线上排序。
19. **L4 性能基准当前进度**：`pa_agent.perf.benchmark` 和
    `tools/run_l4_benchmark.py` 提供 `pa-agent.performance.v1` 报告、p50/p95、p95 budget
    和超过 10% baseline regression 判定；固定 suite 覆盖 snapshot build、indicator、
    K-line geometry 的 100/500/5000 bars，报告只保留耗时、平台和预算状态，不写行情原文。
    当前基线见 `docs/benchmarks/l4_synthetic_2026-07-22.json`；CI/夜间持续回归和同环境
    baseline 维护完成前，不得据单次 benchmark 修改热路径。
20. **L2 Prompt 兼容观察当前进度**：TemplateStore、TemplateContext、严格变量渲染和
    29 个模板 golden snapshot 已完成；本轮用固定 `prompt_golden.json` 连续 5 轮比较
    TemplateStore/旧 loader 的 shared system、Stage 1、Stage 2 standalone、continuation
    standalone/prefix-chain，并覆盖 conservative/balanced stance，结果保持字节等价。
    `use_template_store=False`、旧 `_load()` 和兼容回滚路径在完整稳定周期结束前不得删除，
    不得顺手重写 `prompt_engineering/` 中文文本。
