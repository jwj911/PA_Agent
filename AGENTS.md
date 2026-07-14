<!-- From: d:\Code\price_action_agent\AGENTS.md -->

# PA Agent — AI 编码代理须知

> 本文件面向不熟悉本项目的 AI 编码代理。阅读本文件后，你应该对项目目标、技术栈、模块划分、构建/测试流程、安全约束有清晰了解，再开始修改代码。

***

## 1. 项目概述

**PA Agent** 是一款面向主观交易者的 **价格行为（Price Action）AI 辅助决策桌面程序**。

- 从 **MT5 / TradingView / AkShare / 东方财富 / Tushare / yfinance** 等数据源读取 K 线；
- 将结构化 K 线数据与预计算特征送入大模型，执行 **两阶段分析**：
  1. **阶段一**：市场诊断（周期位置、方向、关键信号、策略文件路由）；
  2. **阶段二**：交易决策（是否下单、限价/突破/市价、入场/止损/止盈、决策树 trace）。
- 支持**增量分析**、**持续跟踪**、**自由追问**、**决策树可视化**、**下一根 K 线预测**；
- **不连接券商、不执行真实下单**，仅作为分析辅助工具输出建议。

项目主要文档语言为**简体中文**；代码内部的技术术语、模块/类/函数名、类型注解以英文为主，但大量注释、日志、用户提示、prompt 为中文。

- 用户操作文档：[`PA_Agent使用文档.md`](./PA_Agent使用文档.md)
- 配置字段说明：[`config/README.md`](./config/README.md)
- 贡献指南：[`CONTRIBUTING.md`](./CONTRIBUTING.md)
- 安全策略：[`SECURITY.md`](./SECURITY.md)
- 迭代记录：[`docs/CHANGELOG.md`](./docs/CHANGELOG.md)

***

## 2. 技术栈与运行环境

| 项目          | 说明                                                    |
| ----------- | ----------------------------------------------------- |
| 语言          | Python >= 3.11                                        |
| 主操作系统       | Windows 10 / 11（MT5 数据源仅 Windows）                     |
| GUI 框架      | PyQt6 + pyqtgraph                                     |
| 数据处理        | numpy、pandas                                          |
| LLM 客户端     | openai（OpenAI 兼容协议）+ cursor-sdk                       |
| 配置校验        | Pydantic v2                                           |
| JSON Schema | jsonschema                                            |
| Token 计数    | tiktoken                                              |
| A 股数据源      | akshare、baostock、tushare、东方财富客户端                      |
| 国际市场        | MetaTrader5（Windows）、TradingView（tvdatafeed）、yfinance |
| 通知          | 飞书机器人、PushPlus                                        |
| 加解密         | cryptography（仅用于 WorkBuddy DPAPI 解密等少数场景）             |

完整依赖见 [`pyproject.toml`](./pyproject.toml)。

***

## 3. 项目结构与模块划分

项目根目录下主要目录：

```
price_action_agent/
├── pa_agent/            # 主程序包
│   ├── main.py          # 应用入口
│   ├── app_context.py   # 依赖容器与启动装配（AppContext 字段已用 TYPE_CHECKING 补全真实类型）
│   ├── ai/              # LLM 客户端、prompt 组装、JSON 校验、归一化、策略路由
│   ├── config/          # 路径常量、Pydantic 配置模型
│   ├── data/            # 数据源抽象与实现
│   ├── demo/            # 记录加载器与回放器
│   ├── gui/             # PyQt6 主窗口、对话框、widgets、主题
│   ├── indicators/      # EMA、ATR 等技术指标
│   ├── notify/          # 飞书、PushPlus 通知
│   ├── orchestrator/    # 两阶段分析流水线、自由追问、校验重试
│   ├── records/         # 分析记录持久化、经验库读取、交易日志
│   ├── security/        # 安全包（当前为空占位，实际密钥处理在 util/ 与 git hooks）
│   └── util/            # 日志脱敏、事件总线、崩溃诊断、线程、时间格式化、安全文件名等
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
   - 调用 `AppContext.bootstrap()` 装配所有组件；
   - 创建 `MainWindow(ctx)` 并显示。
3. `AppContext.bootstrap()`（见 `pa_agent/app_context.py`）：
   - 加载 `config/settings.json`；
   - 同步特殊 provider（QClaw / WorkBuddy / Cursor）配置；
   - 配置日志（API Key 脱敏）；
   - 创建 `EventBus`、数据源、AI 客户端；
   - 创建 `PromptAssembler`、`JsonValidator`、记录写入器、经验库读取器等。

### 3.2 关键子包职责

- **`pa_agent/ai/`**：项目核心算法层。
  - `client_factory.py`：根据模型选择客户端（DeepSeekClient / CursorSdkClient）。
  - `deepseek_client.py`：OpenAI 兼容通用客户端，支持流式、reasoning\_content、KV cache，并内置 MiMo、QClaw、WorkBuddy、PackyAPI、KKAI、MiniMax 等网关适配逻辑。按 `(base_url, api_key)` 缓存 `_OpenAI` 实例（`_get_client()`），`chat`/`stream_chat` 复用连接池；`update_provider()` 会失效缓存。
  - `cursor_sdk_client.py` / `cursor_connector.py`：Cursor SDK 路由。
  - `qclaw_connector.py` / `qclaw_relay.py` / `qclaw_relay_manager.py`：QClaw 本地网关。
  - `workbuddy_connector.py`：WorkBuddy / CodeBuddy 环境检测与 DPAPI 解密取 token。
  - `mimo_compat.py`：MiMo 模型适配。
  - `prompt_assembler.py`：阶段一/阶段二 prompt 组装（超大文件，含中文术语表与 schema 示例）。进程级 `_SYSTEM_PROMPT_CACHE` 由 `_SYSTEM_PROMPT_LOCK` 双检锁保护（构建放锁外，保证跨 worker 拿到同一 byte-identical 前缀）。
  - `router.py`：根据阶段一诊断路由策略 `.txt` 文件。文件名字面量统一引用 `ai/strategy_files.py` 注册表（`strategy_files as sf`），常量名/聚合结构/输出顺序不变。
  - `strategy_files.py`：策略/提示 `.txt` 文件名的**单一事实来源**（27 个模块级常量）。`router.py` 与 `prompt_assembler.py` 共同引用，新增/重命名策略文件只改此处。纯数据模块（仅 `from __future__ import annotations`，无第三方依赖）；取值须与既有文件名逐字节一致（阶段二前缀 KV 缓存敏感）。`pattern_routing.py` 因文件名嵌在 KV 敏感 prompt 散文中，**不**纳入注册表。
  - `json_validator.py`：阶段一/阶段二 JSON 校验与错误分类（category a-e）。
  - `stage1_normalizer.py` / `stage2_normalizer.py` / `trace_normalize.py`：LLM 输出归一化。
  - `decision_tree.py` / `decision_nodes.py` / `decision_stance.py`：决策树、立场、节点逻辑。
  - `session_ledger.py`：Token 用量与上下文窗口追踪。
  - `prompts/schemas.py`：JSON schema 定义。
  - `coherence_checks.py` / `trace_semantic_checks.py`：阶段一/阶段二一致性检查。
  - `kline_features.py` / `market_features.py`：K 线几何特征与市场特征预计算。EMA 缺口计数用 `_ema_gap_counts` 单次反向传递（O(n)）批量算好后按 idx 取用，避免逐棒 O(n²) 扫描。
  - `pattern_routing.py`：模式识别与路由辅助。
  - `structure_levels.py`：结构位管理。
  - `response_extract.py` / `retry_feedback.py` / `retry_policy.py`：响应提取与重试策略。
- **`pa_agent/config/`**：配置与路径。
  - `settings.py`：Pydantic v2 配置模型与读写；支持旧字段迁移。
  - `paths.py`：集中管理项目根目录、配置、日志、记录、prompt 目录等路径常量。
- **`pa_agent/data/`**：市场数据层。
  - `factory.py`：数据源工厂，返回 MT5 / TradingView / AkShare / EastMoney / Tushare / YFinance 源。
  - `mt5.py`：MetaTrader5 连接。
  - `tradingview.py` / `tradingview_connectivity.py`：TradingView WebSocket/HTTP 数据。
  - `akshare_source.py` / `eastmoney_source.py` / `tushare_source.py` / `yfinance_source.py`：A 股/期货数据源。
  - `base.py`：通用数据模型 `KlineFrame`、`KlineBar`、`IndicatorBundle`。
  - `refresh_loop.py` / `bar_close_wait.py`：实时刷新与 K 线收盘等待。
  - `kline_adjust.py` / `market_defaults.py`：复权调整与市场默认值。
- **`pa_agent/gui/`**：PyQt6 GUI。
  - `main_window.py`：主窗口（近 200KB，功能高度集中）。
  - `settings_dialog.py` / `ai_model_settings_dialog.py` / `general_settings_dialog.py` / `feishu_settings_dialog.py`：设置对话框。
  - `decision_flow_viz.py` / `decision_panel.py` / `decision_tree_panel.py`：决策可视化。
  - `chart_widget.py` / `widgets/`：K 线图表与自定义 widgets。
  - `theme/`：QSS 主题与 token。
  - `ai_stream_window.py` / `conversation_widget.py`：实时推理流与会话管理。
- **`pa_agent/orchestrator/`**：业务编排。
  - `two_stage.py`：两阶段分析主流程。Stage1/Stage2 的校验错误富化由单一 `_enrich_validation_message(err, reply, *, stage)` 完成（`stage="stage1"|"stage2"` 仅切换少量中文提示串，输出与原分函数逐字节一致）。网络降级链（`_stream_chat_resilient` 内 WorkBuddy→Cursor→QClaw）的三个 `_try_*_fallback` 是薄包装器（各自 call-time 导入连接器 `apply_*`/`is_openclaw_*_model` 以保持测试可 patch、守卫、调用 `apply_*`），相同尾部（`update_provider`+`save_settings`+`update_api_key`+切换日志）合并到共享 `_finish_provider_fallback(provider_name, err)`；返回语义与日志文本与拆分前一致。
  - `free_chat.py`：分析后自由追问与会话管理。
  - `validation_retry.py`：校验失败后的重试策略。
- **`pa_agent/records/`**：持久化。
  - `pending_writer.py`：分析记录写入（会自动对明文 API Key 脱敏）。记录/分片/followup 侧车的文件名 stem 由**单一事实来源** `build_record_basename(record)` 统一生成，格式 `{YYYY-MM-DD_HH-mm-ss}_{symbol}_{timeframe}`（`strftime("%Y-%m-%d_%H-%M-%S")`，`%M` 为分钟；`symbol`/`timeframe` 经 `sanitize_filename_component` 过滤）。`orchestrator/free_chat.py` 的 `_derive_record_id` 必须委托本函数（call-time 导入），保证 followup `.followups.jsonl` 侧车与记录同名。
  - `experience_reader.py`：经验库读取。
  - `trade_logger.py`：交易 CSV/截图日志。
  - `analysis_history.py`：历史记录管理。`find_latest_successful_record` 带 `_LATEST_RECORD_CACHE`（按 dir mtime 失效，`_LATEST_RECORD_LOCK` 保护并发读写），缓存未命中时按 basename 的 `symbol`/`timeframe` 子串预过滤，只解析候选文件。
  - `schema.py`：记录数据结构定义。
- **`pa_agent/util/`**：通用工具。
  - `logging.py`：日志配置与 API Key 掩码格式化。全局 `_configured`/`_active_formatters` 由可重入 `_STATE_LOCK` 保护（`configure_logging`/`update_api_key` 线程安全）。
  - `mask_secret.py`：密钥掩码函数。
  - `safe_filename.py`：安全文件名组件（防止路径遍历与 Windows 保留名）。
  - `event_bus.py`：应用内事件总线。
  - `crash_diagnostics.py`：崩溃诊断与启动信息记录。
  - `threading.py`：取消令牌、worker 事件等并发原语。

***

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

| 命令                   | 作用                                      |
| -------------------- | --------------------------------------- |
| `make run`           | 启动 GUI                                  |
| `make test`          | 运行全部测试（`pytest -q`）                     |
| `make lint`          | 代码检查（`ruff check . && black --check .`） |
| `make setup-secrets` | 启用 pre-commit 钩子                        |

***

## 5. 代码风格规范

- **Python 版本**：>= 3.11。
- **格式化**：Black，行宽 100（`pyproject.toml` 配置）。
- **Lint**：Ruff，启用规则 `E, F, I, UP, B, SIM, RUF`，忽略 `E501`。
- **导入排序**：由 Ruff `I` rule 管理，通常不需要手动调整。
- **类型注解**：全面使用，文件开头通常写 `from __future__ import annotations`。统一采用 Python 3.11+（PEP 585/604）风格：用 `X | None` 而非 `Optional[X]`、内置泛型 `list[...]`/`dict[...]` 而非 `typing.List`/`Dict`、`Callable` 从 `collections.abc` 导入（仅注解用途可置于 `TYPE_CHECKING` 块）。例外：`records/schema.py` 因 Pydantic v2 需即时求值字段注解，不加 `from __future__ import annotations`，但仍用 `X | None`。
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

***

## 6. 测试策略与运行方式

测试位于 `tests/`，分为四层：

| 目录                   | 说明                                        | 标记            |
| -------------------- | ----------------------------------------- | ------------- |
| `tests/unit/`        | 80+ 单元测试，覆盖数据源、AI 组件、GUI widgets、校验器、记录器等 | `unit`        |
| `tests/integration/` | 两阶段流水线集成测试，使用共享 `conftest.py`             | `integration` |
| `tests/property/`    | 基于 Hypothesis 的属性测试                       | `property`    |
| `tests/e2e/`         | 使用 `pytest-qt` 驱动真实 `MainWindow` 的冒烟测试    | `e2e`         |

特殊标记：

- `live`：需要真实网络或 API Key（如 `test_akshare_live.py`、`test_kkai_thinking_live.py`），**绝不读取** **`config/settings.json`**，仅通过环境变量获取密钥。

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
- CI（`.github/workflows/ci.yml`）目前只在 Windows + Python 3.11 下做安装验证，不运行完整测试套件。
- 提交前建议至少运行 `pytest -m "not e2e"`。

***

## 7. 安全配置与密钥处理

### 7.1 实际行为（请务必注意）

- `config/settings.json` 中的 `provider.api_key` **以明文形式存储**。
- 字段 `provider.api_key_encrypted` 在模型中存在，但当前代码**未实现本地加密存储逻辑**；保存设置时直接把内存中的 `api_key` 明文写入 `settings.json`。
- `pa_agent/security/` 包目前为空占位，未承担实际加密职责。

因此，项目的密钥安全主要依赖：

1. **Git 忽略**：`config/settings.json` 等敏感文件已被 `.gitignore` 排除；
2. **pre-commit 拦截**：`.githooks/pre-commit` 阻止提交 `settings.json`、`.env`、日志、分析记录，并扫描 diff 中的 `api_key` / `sk-...` 模式；
3. **运行时脱敏**：
   - `pa_agent/util/mask_secret.py` 提供掩码函数（保留最后 4 位，其余替换为 `*`）；
   - `pa_agent/util/logging.py` 的 `MaskingFormatter` 在日志输出前替换明文 API Key；
   - `pa_agent/records/pending_writer.py` 在序列化记录前递归扫描并替换明文 API Key；
   - 多处测试（`test_logs_have_no_plaintext_key.py`、`test_pending_writer_no_plaintext_key.py` 等）确保脱敏有效。

### 7.2 开发者必须遵守的安全规范

- **绝不**将 `config/settings.json`、`config/exception_state.json`、`.env`、密钥文件加入 Git。
- **绝不**在测试、日志、错误信息中硬编码真实 API Key。
- 修改涉及密钥读取/保存的代码时，确保：
  - 保存到文件前仍经过脱敏或保持在 gitignored 文件中；
  - 日志和持久化记录中不出现明文 key；
  - 如需新增密钥字段，同步更新 `.gitignore` 与 `.githooks/pre-commit`。
- 建议新贡献者运行：

```cmd
powershell -ExecutionPolicy Bypass -File tools\setup_git_secrets.ps1
```

该脚本会设置 `core.hooksPath` 并验证敏感路径是否被忽略。

### 7.3 安全文件名

- `pa_agent/util/safe_filename.py` 提供 `sanitize_filename_component`，用于把 `symbol`/`timeframe` 等用户输入转换为安全的文件路径组件，防止路径遍历与 Windows 保留名问题。
- 任何把用户输入拼入文件名的场景，都应优先使用该工具，而不是直接 `replace('/', '-')`。

***

## 8. 外部集成

### 8.1 AI 提供商

支持多种 OpenAI 兼容网关与专用 SDK：

- **DeepSeek**：原生 OpenAI 兼容（`api.deepseek.com`），支持 thinking / reasoning\_effort / KV cache。
- **QClaw**：本地网关（`~/.qclaw/openclaw.json`），模型别名 `openclaw` / `openclaw/*`。
- **Cursor**：`cursor-sdk`，模型别名 `openclaw_cs` / `openclaw_cs/*`。
- **WorkBuddy / CodeBuddy**：`copilot.tencent.com/v2`，模型别名 `openclaw_wb`，支持从 Windows DPAPI 解密 Electron Local Storage 取 token。
- **PackyAPI**（`packyapi.com`）：支持 Claude 官方路由与 thinking budget。
- **KKAI**（`api.kkone.vip`）：Claude 代理。
- **MiniMax**（`api.minimax.io`）：OpenAI 兼容。
- **MiMo**：`mimo_compat.py` 专门适配。

### 8.2 数据源

- **MT5**（`MetaTrader5`）：Windows 主数据源。
- **TradingView**：通过 `tvdatafeed` 库。
- **AkShare**：A 股数据。
- **EastMoney**：A 股（东方财富），见 `eastmoney_client.py` / `eastmoney_source.py`。
- **Tushare**：A 股（需 token）。
- **Baostock**：部分场景作为 fallback。
- **YFinance**：期货/加密货币。

### 8.3 通知

- **飞书（Feishu）**：自定义机器人 webhook，支持签名、tenant\_access\_token、图片上传、交互卡片。
- **PushPlus**：简单 HTTP 推送。

***

## 9. 部署与发布

- 当前项目**没有**构建独立可执行文件（如 PyInstaller / Nuitka / cx\_Freeze）的流程。
- 部署方式以源码运行或 `pip install -e .` 为主：
  - Windows 用户：直接双击 `run.py` 或在终端执行 `python run.py`。
  - 开发者：`pip install -e ".[dev]"` 后使用 `make run` / `python -m pa_agent.main`。
- CI（`.github/workflows/ci.yml`）仅做安装与 import 验证，不运行完整测试套件。
- `tools/` 目录包含大量一次性诊断脚本（网关探测、stage2 JSON 调试、MT5 时钟偏移检测等），不属于正式发布流程。

***

## 10. 给 AI 代理的实用提示

1. **先读配置再改代码**：很多行为由 `config/settings.json` 与 `pa_agent/config/settings.py` 中的 Pydantic 模型控制。新增配置字段时，同步更新 example 文件、GUI 设置对话框、相关测试。
2. **Prompt 文本在** **`prompt_engineering/`**：策略路由、阶段一/阶段二的 prompt 片段多为中文 `.txt` 文件。修改这些文件可能改变模型输出格式，需要同步更新 `tests/` 中的 JSON fixture 与校验用例。
3. **JSON schema 在** **`pa_agent/ai/prompts/schemas.py`**：阶段一/阶段二的输出结构严格受 schema 约束，改动需同步更新 `json_validator.py` 与 normalizer。
4. **MainWindow 是巨型文件**：`pa_agent/gui/main_window.py` 接近 200KB、4000+ 行。做小改动时优先定位到具体方法；做大重构时建议与维护者沟通。
5. **不要假设 API Key 已加密**：当前实现为明文存储在 gitignored 的 `settings.json` 中。任何涉及密钥持久化的新功能都要保持这一安全边界（或明确引入加密方案并更新本文件）。
6. **优先用测试验证**：本项目测试覆盖较全，改动后请运行相关分层测试；涉及 LLM 输出解析的改动建议同时跑 `unit` 与 `integration`。
7. **保持中文用户界面**：新增用户可见字符串、日志、提示信息时，默认使用简体中文，与项目现有风格保持一致。
8. **每次迭代必须更新变更日志**：任何代码更新/修复/优化完成后，都要在 [`docs/CHANGELOG.md`](./docs/CHANGELOG.md) 追加或更新对应条目（问题/动机 → 修复/改动 → 涉及文件 → 验证方式），不得只改代码而不记录。
9. **新增文件/字段时注意更新本文件**：如果你新增了模块、数据源、AI 提供商、安全机制、构建流程等，请同步更新本 `AGENTS.md` 中的对应章节，保持文档与代码一致。
10. **热路径注意性能，但不牺牲语义**：`data/snapshot.py`（RefreshLoop tick）、`ai/kline_features.py`（逐棒特征）、`records/analysis_history.py`（增量分析找上次记录）、`ai/deepseek_client.py`（每次 API 调用）等属于高频路径，改动时避免重复计算、无谓遍历与无条件构造大字符串（如把 prompt DEBUG 日志用 `logger.isEnabledFor(logging.DEBUG)` 守卫）。任何性能优化都必须保持输出与原实现一致，替换算法时应给出等价性验证；性能热点清单见 `docs/backend_review_report.md` §8。
11. **进程级缓存/全局状态需线程安全**：后台 QThread（刷新、快照、分析、聊天）会并发访问模块级缓存。`ai/prompt_assembler.py:_SYSTEM_PROMPT_CACHE`、`records/analysis_history.py:_LATEST_RECORD_CACHE`、`data/eastmoney_extended.py:_COMPACT_CTX_CACHE`、`util/logging.py`（`_configured`/`_active_formatters`）、`data/kline_adjust.py:_current`、`ai/cursor_sdk_client.py` 的 patch 标志均已加锁保护。新增此类全局可变状态时，应配套加锁（耗时构建/IO 放锁外，用双检锁），保持输出与语义不变。

***

*本文件基于项目当前实际代码生成。若后续引入本地加密、新增数据源/提供商、调整构建或测试流程，请同步更新本文件。*
