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
| 加解密         | cryptography（WorkBuddy DPAPI 解密等）；`ctypes`+`crypt32` DPAPI（API Key 至静态加密） |

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
│   ├── security/        # 安全包：secret_store.py（API Key 至静态加密，Windows DPAPI，非 Windows 优雅降级）
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
   - 通过 `ProviderSyncService` 同步特殊 provider（QClaw / WorkBuddy / Cursor）配置；
   - 配置日志（API Key 脱敏）；
   - 创建 `EventBus`、数据源、AI 客户端；
   - 创建 `PromptAssembler`、`JsonValidator`、记录写入器、经验库读取器等。

### 3.2 关键子包职责

- **`pa_agent/ai/`**：项目核心算法层。
  - `client_factory.py`：根据模型选择客户端（DeepSeekClient / CursorSdkClient）。
  - `deepseek_client.py`：OpenAI 兼容通用客户端，支持流式、reasoning\_content、KV cache，并内置 MiMo、QClaw、WorkBuddy、PackyAPI、KKAI、MiniMax 等网关适配逻辑。按 `(base_url, api_key)` 缓存 `_OpenAI` 实例（`_get_client()`），`chat`/`stream_chat` 复用连接池；`update_provider()` 会失效缓存。
  - `provider_sync_service.py`：**ProviderSyncService provider 同步服务**（M5）。`ProviderSyncService(save_path=...).sync_on_load(settings)` 按 QClaw → WorkBuddy → Cursor 顺序调用既有 connector 的 `sync_*_provider_on_load()` 并透传 `save_path`；服务本身不判断 route、不 mutate provider、不写 settings，只集中启动期编排。`finish_provider_fallback(...)` 负责自动降级 apply 成功后的共享尾部：`err` 处理、`client.update_provider(settings.provider)`、best-effort `save_settings` + `update_api_key`、`pending_writer.set_api_key` 同步脱敏 key、切换日志。`app_context.bootstrap()` 现只调用 `sync_providers_on_load(...)`，`two_stage._finish_provider_fallback()` 现只作为兼容 wrapper 委托服务；per-provider guard 与 connector `apply_*` 仍留在 `two_stage` 的三个 `_try_*_fallback` 包装器里，以保持 patch 点与尝试顺序。
  - `cursor_sdk_client.py` / `cursor_connector.py`：Cursor SDK 路由。
  - `qclaw_connector.py` / `qclaw_relay.py` / `qclaw_relay_manager.py`：QClaw 本地网关。
  - `workbuddy_connector.py`：WorkBuddy / CodeBuddy 环境检测与 DPAPI 解密取 token。
  - `mimo_compat.py`：MiMo 模型适配。
  - `prompt_assembler.py`：阶段一/阶段二 prompt 组装（超大文件，含中文术语表与 schema 示例）。进程级 `_SYSTEM_PROMPT_CACHE` 由 `_SYSTEM_PROMPT_LOCK` 双检锁保护（构建放锁外，保证跨 worker 拿到同一 byte-identical 前缀）。正按报告 §5.2 M1 逐步拆分：**第一刀**已将 K 线表渲染器簇（`KlineTableRenderer` 产出——`_render_kline_table`/`_render_kline_feature_table` 两个渲染器 + `_fmt_feature` 辅助 + `_KLINE_INDICATOR_NOTE` 常量）拆出至 PyQt6-free 叶子模块 `kline_table_renderer.py`，并在 `PromptAssembler` 类体内以 2 行 `_render_kline_table = staticmethod(render_kline_table)` / `_render_kline_feature_table = staticmethod(render_kline_feature_table)` **重绑定**，使 `PromptAssembler._render_kline_table(...)`（`main_window.py` 类名调用）、`assembler._render_kline_feature_table(...)`（测试实例调用）等既有站点逐字节兼容；文件从 1963 行降至 1902 行。**第二刀**已将经验库渲染器（`ExperienceRenderer` 产出——`_render_experience`）拆出至 stdlib-only 叶子模块 `experience_renderer.py`，并在类体内以 1 行 `_render_experience = staticmethod(render_experience)` **重绑定**，使 `build_stage2` 链内 `self._render_experience(...)` 逐字节兼容；文件从 1902 行降至 1880 行。**第三刀**已将阶段二指导渲染器簇（`_render_trend_conflict_guidance`/`_render_transition_guidance`/`_parse_level_midpoint`/`_render_planned_limit_hint`）拆出至 PyQt6-free 叶子模块 `stage2_guidance.py`，并在类体内以 4 行 `_render_x = staticmethod(render_x)` **重绑定**，使 `_build_stage2_user_prompt` 链内 `self._render_*_guidance(...)`/`self._render_planned_limit_hint(...)` 逐字节兼容；随簇迁出后 `math.` 在本文件内已无引用，`import math` 一并删除；文件从 1880 行降至 1736 行。**第四刀**已将跨阶段 carryover 上下文构建器簇（`_normalize_prev_stage1_assistant_for_incremental`/`_render_previous_prediction`/`_normalize_stage1_assistant_for_chain`/`_compact_stage1_for_stage2`）拆出至 PyQt6-free 叶子模块 `chain_context.py`，并在类体内以 4 行 `_x = staticmethod(y)` **重绑定**，使 `build_incremental_stage1`/`_build_stage2_user_prompt`/`build_stage2_continuation` 链内 `self._normalize_prev_stage1_assistant_for_incremental(...)`/`self._render_previous_prediction(...)`/`self._normalize_stage1_assistant_for_chain(...)`/`self._compact_stage1_for_stage2(...)` 逐字节兼容；文件从 1736 行降至 1652 行。**第五刀**已将程序预填充节点提示渲染器（`_render_program_prefill_hint`）拆出至 PyQt6-free 叶子模块 `program_prefill_hint.py`，并在类体内以 1 行 `_render_program_prefill_hint = staticmethod(render_program_prefill_hint)` **重绑定**，使 `_build_stage1_user_prompt`/`_build_incremental_stage1_user_prompt`/`_build_incremental_stage1_continuation_user_prompt` 三处 `self._render_program_prefill_hint(frame)` 逐字节兼容；文件从 1652 行降至 1571 行。market-feature 包装方法（`_render_simple_market_features_block`/`_inject_market_features_block`）因依赖 `market_features`（经 `util/__init__`→`event_bus`→PyQt6 触链）**暂留**本文件，待后续切 `Stage1PromptBuilder`/`Stage2PromptBuilder` 时一并处理。
  - `prompt_assembler.py`（R41 更新 / M1 Stage1PromptBuilder）：Stage 1 user prompt 三个大方法（全量阶段一、增量阶段一、增量 continuation）与 market-feature 包装已下沉到 `stage1_prompt_builder.py`；本文件继续保留 `build_stage1()` / `build_incremental_stage1()` 对外 API、系统 prompt 缓存、Stage 2 prompt 构建、以及 `_build_stage1_user_prompt` / `_build_incremental_stage1_user_prompt` / `_build_incremental_stage1_continuation_user_prompt` / `_render_simple_market_features_block` / `_inject_market_features_block` 兼容性薄包装。`PromptAssembler` 类体从 675 行降至 507 行，文件从 1570 行降至 1398 行。后续 M1 剩余重点为 `Stage2PromptBuilder`（`build_stage2` / `build_stage2_continuation` / `_build_stage2_user_prompt` / `stage2_system_prompt_only`）。
  - `stage1_prompt_builder.py`：**Stage 1 user prompt builder 模块**（M1 第六刀）。含 `Stage1PromptBuilder`，负责 `build_stage1_user_prompt()`、`build_incremental_stage1_user_prompt()`、`build_incremental_stage1_continuation_user_prompt()` 三类 Stage 1 user turn；同时承接 `render_simple_market_features_block()` / `inject_market_features_block()` 两个 market-feature 包装函数。新 builder 通过构造参数接收 `load`、prompt settings、Stage 1 txt 文件列表、输出提醒函数、尾部提醒/增量硬规则/market-feature authority note，以及 K 线表/预填提示渲染 callable，不 import `prompt_assembler.py`，避免循环依赖；`pattern_routing` 与 `market_features` 依赖在本模块内收束。
  - `prompt_assembler.py`（R42 更新 / M1 Stage2PromptBuilder）：Stage 2 prompt 构建主体已下沉到 `stage2_prompt_builder.py`；本文件继续保留 `build_stage2()` / `build_stage2_continuation()` / `stage2_system_prompt_only()` 对外 API、系统 prompt 缓存、以及 `_build_stage2_user_prompt` 兼容性薄包装。Stage 2 user prompt 中的 stance/continuity/guidance/experience/next-bar/next-cycle/prefix-chain/kline-block/breakout-tick/previous-prediction/compact-stage1 逻辑均由 `Stage2PromptBuilder` 负责。文件从 1398 行降至 1275 行，`PromptAssembler` 类体从 507 行降至 385 行。至此 M1 点名的 `Stage1PromptBuilder` / `Stage2PromptBuilder` / `KlineTableRenderer` / `ExperienceRenderer` 均已落位。
  - `stage2_prompt_builder.py`：**Stage 2 prompt builder 模块**（M1 第七刀）。含 `Stage2PromptBuilder`，负责 `build_stage2()`、`build_stage2_continuation()`、`build_stage2_user_prompt()` 三类 Stage 2 构建职责；通过构造参数接收 system prompt 构建函数、txt 加载函数、完整策略库开关、Stage 2 txt 文件列表函数、预测说明/输出契约常量，以及 trend guidance / experience / carryover / market-feature / K 线表渲染 callable，不 import `prompt_assembler.py`，避免循环依赖。`supports_kv_prefix_chain`、`decision_continuity`、`format_breakout_tick_hint` 等 Stage 2 专属依赖均在本模块内收束。
  - `kline_table_renderer.py`：**K 线表渲染器簇模块**（`KlineTableRenderer` 产出，M1 第一刀，PyQt6-free 叶子——仅 `from __future__ import annotations` + `math` + 3 个 PyQt6-free 叶子 import：`kline_features`（`bar_candle_direction_label`/`compute_kline_geometry_features`）/`data.base`（`KlineFrame`）/`data.datetime_ts`（`format_epoch_for_display`），无其他 import 期项目依赖、无副作用）。含 `_KLINE_INDICATOR_NOTE` 中文说明常量、`_fmt_feature`（`None→"N/A"`，否则 `f"{value:.3f}"`）辅助，以及两个把结构化 K 线落地成模型逐字节对齐文本表的确定性渲染器：`render_kline_table`（价量指标表，含 EMA20/ATR14 的 `math.isnan→"N/A"` warm-up 分支、`bar_candle_direction_label` 阳阴列）、`render_kline_feature_table`（单棒几何特征表，逐字段 `_fmt_feature` 格式化、`compute_kline_geometry_features` 驱动）。这两个渲染器原为 `PromptAssembler` 的 `@staticmethod _render_kline_table`/`_render_kline_feature_table`，迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `prompt_assembler.py` 在类体内以 `_render_kline_table = staticmethod(render_kline_table)` / `_render_kline_feature_table = staticmethod(render_kline_feature_table)` **重绑定**，使 `PromptAssembler._render_kline_table(...)`（`main_window.py` 类名调用）、`assembler._render_kline_feature_table(...)`（`test_prompt_assembler.py` 实例调用）逐字节兼容。因全为 PyQt6-free 叶子依赖，本模块可独立 import 并做真实 runtime 等价验证（区别于经 `market_features`→PyQt6 触链的 market-feature 包装方法）；表格布局/列宽/中文表头/`_KLINE_INDICATOR_NOTE` 说明常量须逐字节一致（模型按此表形对齐）。
  - `experience_renderer.py`：**经验库渲染器模块**（`ExperienceRenderer` 产出，M1 第二刀，stdlib-only 叶子——仅 `from __future__ import annotations` + `json` + `typing.Any`，无其他 import 期项目依赖、无副作用）。含单个确定性渲染器 `render_experience(entries, *, max_chars_per_entry=400)`：把「阶段二 user 消息」折叠的最近经验库案例落地成「## 经验库(最近案例,供参考)」纯文本块——块头附「以下案例仅作对照…不得因相似就改变独立判断」中文告诫，逐条按 `isinstance(dict)`→`json.dumps(indent=2)` / `hasattr("content")`→取 `content` 序列化 / 否则 `str(entry)` 三分支序列化，超 `max_chars_per_entry` 时截断为 `blob[: max_chars_per_entry - 3] + "..."`，每条包 `\n### 案例 {i}\n```json\n{blob}\n```` markdown 围栏。该渲染器原为 `PromptAssembler` 的 `@staticmethod _render_experience`（`build_stage2`→`stage2_system_prompt_only` 链唯一内部调用点），迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `prompt_assembler.py` 在类体内以 `_render_experience = staticmethod(render_experience)` **重绑定**，使 `self._render_experience(...)` 逐字节兼容。因纯 stdlib（仅 `json`），本模块可独立 import 并做真实 runtime 等价验证（同 kline_table_renderer 一样绕开 `market_features`→PyQt6 触链）；块头/中文告诫串/每条 markdown 围栏/截断省略号须逐字节一致（模型按此块形对齐）。
  - `stage2_guidance.py`：**阶段二指导渲染器簇模块**（M1 第三刀，PyQt6-free 叶子——仅 `from __future__ import annotations` + `math` + `from pa_agent.data.base import KlineFrame`，无其他 import 期项目依赖、无副作用）。含四个把阶段一诊断字段派生成 Stage 2 user 消息确定性指导块的渲染器/辅助：`render_trend_conflict_guidance`（新旧趋势冲突指导，Brooks 并列原则，块头「## 新旧趋势冲突指导（Brooks 并列原则）」，含 recent_spike 分支）、`render_transition_guidance`（状态转换期风险指导，块头「## 状态转换期风险指导」，按 `transition_risk` 高/中/低给信号把握与入场选择三分支）、`parse_level_midpoint`（支撑/阻力位字符串→数值中点，处理 `-` 区间与单值，`render_planned_limit_hint` 专用辅助）、`render_planned_limit_hint`（通道/区间结构下的 §9.0/§9.0P 计划型限价提示，块头「## §9.0 / §9.0P 计划型限价提示…」，含 cycle 白名单过滤、ATR 邻近度 `max(atr * 0.35, abs(close) * 0.0008)`、近支撑/阻力遍历、`math.isnan` warm-up 分支、direction=neutral 分支；内部调用模块内 `parse_level_midpoint(lv)`）。这四者原为 `PromptAssembler` 的 `@staticmethod _render_trend_conflict_guidance`/`_render_transition_guidance`/`_parse_level_midpoint`/`_render_planned_limit_hint`（三渲染器仅在 `_build_stage2_user_prompt` 经 `self._render_*` 调用，`_parse_level_midpoint` 仅被 `_render_planned_limit_hint` 内部调用），迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `prompt_assembler.py` 在类体内以 4 行 `_render_trend_conflict_guidance = staticmethod(render_trend_conflict_guidance)` / `_render_transition_guidance = staticmethod(render_transition_guidance)` / `_parse_level_midpoint = staticmethod(parse_level_midpoint)` / `_render_planned_limit_hint = staticmethod(render_planned_limit_hint)` **重绑定**，使 `self._render_*_guidance(...)`/`self._render_planned_limit_hint(...)` 逐字节兼容。因仅依赖 stdlib `math` + PyQt6-free 的 `KlineFrame` 叶子（不触 `market_features`→PyQt6 触链），本模块可独立 import 并做真实 runtime 等价验证（同 kline_table_renderer/experience_renderer）；块头/中文指导串/`transition_risk` 三分支文案/`{...:.4f}` 数值格式化/`max(atr * 0.35, ...)` 邻近度算术须逐字节一致（模型按此块形对齐）。
  - `chain_context.py`：**跨阶段 carryover 上下文构建器簇模块**（M1 第四刀，PyQt6-free 叶子——仅 `from __future__ import annotations` + `json` + `logging` + `typing`（`TYPE_CHECKING`/`Any`），`AnalysisRecord` 仅注解用途置于 `TYPE_CHECKING` 块，无 import 期项目依赖、无副作用）。含四个把**上一阶段/上一轮结果**序列化成**下游 prompt 片段**的确定性构建器：`normalize_prev_stage1_assistant_for_incremental`（增量模式下复用上一轮已校验的阶段一诊断 JSON 而非其散文/markdown 回复作 assistant 轮，降级时 `logger.warning`）、`render_previous_prediction`（把上一轮「下一根K线预测」渲染成「## 上一轮下一根K线预测」参考块，含 unpredictable 分支与 `阳/阴/中性 %` 概率格式化，R5.2）、`normalize_stage1_assistant_for_chain`（前缀链模式下压缩刚校验的阶段一 JSON 作 assistant 轮）、`compact_stage1_for_stage2`（把阶段一诊断投影到阶段二所需的 20 字段白名单子集，降噪减 token）。唯一项目触点 `format_model_json_for_context`（来自 `json_validator`）沿用原有的**函数体内 call-time import**（避开 `market_features`→PyQt6 触链、破环）。这四者原为 `PromptAssembler` 的 `@staticmethod _normalize_prev_stage1_assistant_for_incremental`/`_render_previous_prediction`/`_normalize_stage1_assistant_for_chain`/`_compact_stage1_for_stage2`（分别仅在 `build_incremental_stage1`/`_build_stage2_user_prompt`/`build_stage2_continuation` 经 `self._x` 调用），迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `prompt_assembler.py` 在类体内以 4 行 `_x = staticmethod(y)` **重绑定**，使 `self._normalize_prev_stage1_assistant_for_incremental(...)`/`self._render_previous_prediction(...)`/`self._normalize_stage1_assistant_for_chain(...)`/`self._compact_stage1_for_stage2(...)` 逐字节兼容。因近乎 stdlib（`json`/`logging`/`typing`，项目触点 call-time import），本模块可独立 import 并做真实 runtime 等价验证（同 kline_table_renderer/experience_renderer/stage2_guidance）；块头/中文参考串/方向概率格式化/阶段二 20 字段白名单/`json.dumps(indent=2)` 序列化须逐字节一致（模型按这些片段形对齐、前缀 KV 缓存对压缩 JSON 敏感）。
  - `program_prefill_hint.py`：**程序预填充节点提示渲染器模块**（M1 第五刀，PyQt6-free 叶子——模块级仅 `from __future__ import annotations` + `logging` + `typing`（`TYPE_CHECKING`），`KlineFrame` 仅注解用途置于 `TYPE_CHECKING` 块，无 import 期项目依赖、无副作用）。含单个确定性渲染器 `render_program_prefill_hint(frame)`：在**阶段一 user prompt** 里注入一个紧凑块，把确定性引擎对 §1.1（数据是否足够）/§2.3（当前方向，五信号投票）/§2.4（是否 Always In，三闸门）的预填充判定与依据摊开给 AI 参考（结果将写入 gate_trace，AI 可在理解依据后经 `node_overrides` 提交有充分理由的覆盖）——块头「## 程序预填充节点判断依据（§1.1 / §2.3 / §2.4，供 AI 参考）」，逐段 append §1.1 数据充分性、§2.3 方向（含 `render_three_window_summary` 三窗口摘要 + §2.2「长程背景 vs 近期方向」摘要行 + 冲突分支「；**冲突时不否决近期、不自动减半仓位**」）、§2.4 Always In、override 门槛三条 `•` 项，`except Exception`→`logger.warning`→返回空串兜底。唯一项目触点——`decision_nodes` 的三个 judge（`judge_data_sufficiency`/`judge_direction`/`judge_always_in`）与 `trend_context` 的两个摘要辅助（`build_trend_context`/`render_three_window_summary`）——沿用原有的**函数体内 call-time import**（避开 `market_features`→PyQt6 触链、并打破 `prompt_assembler` ↔ `decision_nodes`/`trend_context` 循环依赖）。该渲染器原为 `PromptAssembler` 的 `@staticmethod _render_program_prefill_hint`（`_build_stage1_user_prompt`/`_build_incremental_stage1_user_prompt`/`_build_incremental_stage1_continuation_user_prompt` 三处经 `self._render_program_prefill_hint(frame)` 调用），迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `prompt_assembler.py` 在类体内以 1 行 `_render_program_prefill_hint = staticmethod(render_program_prefill_hint)` **重绑定**，使三处 `self._render_program_prefill_hint(frame)` 逐字节兼容。因模块级近乎 stdlib（`logging`/`typing`，项目触点 call-time import），本模块可独立 import 并做真实 runtime 等价验证（同 kline_table_renderer/experience_renderer/stage2_guidance/chain_context，用 `sys.modules` stub 注入 `decision_nodes`/`trend_context` 绕开 PyQt6）；块头/§1.1/§2.3/§2.4 中文依据串/§2.2 背景摘要行/冲突分支文案/override 门槛三条须逐字节一致（阶段一前缀 KV 缓存敏感、模型按块形对齐）。
  - `strategy_files.py`：策略/提示 `.txt` 文件名的**单一事实来源**（模块级常量注册表）。`router.py` 与 `prompt_assembler.py` 共同引用，新增/重命名策略文件只改此处。纯数据模块（仅 `from __future__ import annotations`，无第三方依赖）；取值须与既有文件名逐字节一致（阶段二前缀 KV 缓存敏感）。`pattern_routing.py` 因文件名嵌在 KV 敏感 prompt 散文中，**不**纳入注册表。
  - `json_validator.py`：阶段一/阶段二 JSON 校验与错误分类（category a-e）。原为 1023 行大文件，正按报告 §5.2 M2 逐步拆分：第一刀已将纯 JSON 文本提取/修复函数区拆出至 `json_repair.py`，并从 `json_repair` **重导出**这些修复函数（`# noqa: E402, F401`）；**第二刀**已将「阶段二业务规则跨字段校验层」——`_EXPLICIT_S9_TRADABLE_TOKENS` 令牌元组、7 个 `_check_*` 校验器与 3 个模块级辅助（`_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons`）拆出至 `business_rules.py`（`BusinessRuleValidator` 簇），本文件从 `business_rules` **重导出** token 元组与 3 个辅助（`# noqa: E402, F401`），并在 `JsonValidator` 类体内以 7 行 `_check_x = staticmethod(business_rules.check_x)` **重绑定**，使 `validate` 内 `self._check_x(...)` 与测试 `JsonValidator._check_x(...)` 类名调用逐字节兼容。本文件现仅保留 `JsonValidator` 类（`normalize_parsed`/`validate` 编排层）与 `Ok`/`ValidationError`/`Result` 结果类型，从 821 行降至 415 行；两组重导出块须按 isort 字母序（`business_rules` 在 `json_repair` 之前）排列，使既有 `from pa_agent.ai.json_validator import ...` 站点逐字节兼容。
  - `json_validator.py`（R40 更新 / M2 第三刀）：JSON Schema 结构校验层已拆出至 `schema_validator.py`。`JsonValidator.validate()` 现把 normalizer 之后、显式跨字段检查之前的 `jsonschema.Draft7Validator(schema).iter_errors(obj)` 与 missing/invalid/allowed 分类委托给 `collect_schema_errors(obj, schema)`；本文件继续保留 `Ok`/`ValidationError`/`Result` 结果类型、`normalize_parsed`、Stage 1/Stage 2 coherence/trace 语义检查、`business_rules` 调用以及最终 category/message 组装，避免 `schema_validator.py` 反向 import `json_validator.py` 造成循环依赖。文件从 415 行降至 405 行；schema 校验缺失 `jsonschema` 时仍按原行为 warning 后 `Ok(obj=obj)`。
  - `json_repair.py`：JSON 提取与修复的**纯函数模块**（stdlib-only，仅依赖 `json`/`logging`/`re`，零依赖 `JsonValidator` 及任何项目模块）。含去 markdown fence（`_strip_fences`）、修不转义引号（`_repair_unescaped_quotes`）、修分号分隔符、补截断括号（`_balance_json_brackets`）、注入 stage1 缺失尾部、闭合未完结字符串、语法修复（`_try_repair_json_syntax`）等，以及 `coalesce_model_json_text` / `format_model_json_for_context`。被 `validation_retry.py`、`prompt_assembler.py`、`tools/debug_stage2_json.py`、测试等跨模块 import；新增/修改修复逻辑改此处，`json_validator.py` 的重导出块须同步名单。
  - `business_rules.py`：阶段二**业务规则跨字段校验器簇模块**（`BusinessRuleValidator`，M2 第二刀，near-stdlib：仅 `from __future__ import annotations` + `re` + `typing.Any`，无 import 期项目依赖、无副作用）。含 `_EXPLICIT_S9_TRADABLE_TOKENS` 令牌元组、7 个确定性 `check_*` 校验器（`check_no_order_invariant` 不下单↔null 铁律、`check_breakout_order_basis` 突破单绑定 K 线极值、`check_trade_metrics` RR/交易者方程、`check_breakout_price_extreme` 突破入场价数值校验、`check_next_cycle_prediction` 周期预测 sum/argmax/null 规则、`check_next_bar_prediction` 下一棒预测 sum/argmax/null 规则、`check_signal_chain` 下单决策须以 §9 信号事实为依据）与 3 个模块级辅助（`_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons`）。两个项目触点均走**函数体内 call-time import** 以避 PyQt6/破环：`check_trade_metrics` 内 `from pa_agent.util.trade_metrics import validate_order_trade_metrics`（经 `util/__init__`→`event_bus`→PyQt6），`check_next_cycle_prediction` 内 `from pa_agent.ai.cycle_enums import CYCLE_ENUM, CYCLE_ORDER`（干净）。这些 `check_*` 原为 `JsonValidator` 的 `@staticmethod _check_*`，迁出为模块函数（去前导下划线、去 `@staticmethod`）后由 `json_validator.py` 在类体内以 `_check_x = staticmethod(business_rules.check_x)` **重绑定**，token 元组与 3 个辅助则由 `json_validator.py` 从本模块重导出，使 `JsonValidator._check_x(...)` 与 `from pa_agent.ai.json_validator import _EXPLICIT_S9_TRADABLE_TOKENS/_parse_k_seq/...` 逐字节兼容；行为/中文 reason 串/`_planned_limit_boundary_patterns` 白名单须与原文逐字节一致。
  - `schema_validator.py`：JSON Schema **结构校验器模块**（M2 第三刀，near-stdlib：模块级仅 `from __future__ import annotations` + `logging` + `dataclasses` + `typing.Any`；`jsonschema` 为函数体内 call-time import）。含 `SchemaValidationResult` 与 `collect_schema_errors(obj, schema)`：运行 Draft 7 schema 校验并分类 `missing_fields`、`invalid_fields`、`allowed_values`、`first_validator`、`first_message`、`error_count`；若 `jsonschema` 不可用则 warning 后返回 `None`，由 `JsonValidator.validate()` 保持原有跳过 schema 校验语义。该模块不 import `json_validator.py`，避免 `ValidationError` 结果类型反向依赖造成循环；最终 category 判定与 `ValidationError` 组装仍在 `JsonValidator` 内完成。
  - `stage1_normalizer.py` / `stage2_normalizer.py` / `trace_normalize.py`：LLM 输出归一化。
  - `decision_tree.py` / `decision_nodes.py` / `decision_stance.py`：决策树、立场、节点逻辑。`decision_nodes.py` 为 AI 层最大单文件，正按报告 §5.2 M3 逐步拆分：头部 28 个调参常量与节点权限集已拆出至 `decision_thresholds.py`，3 个纯 K 线几何原语（`_count_trend_bars`/`_mean_overlap_ratio`/`_find_swings`）已拆出至 `bar_geometry.py`（此两组名字在本文件函数体内确有引用，属**正常 import**，无 `# noqa`）；前置数据质量闸门（`PreflightResult`/`check_preflight_data`/`_check_preflight_data_inner`）已拆出至 `preflight.py`，因这两个外露名在本文件内不再被其他函数引用，顶部 import 组以 `# noqa: F401` 做**纯重导出**（与 M2 的 `json_repair` 重导出同理）；所有 section-judge 共享的「结果层」（`NodeFill` 结果 dataclass、`_coerce_dict`/`_coerce_trace_list` 归一、`build_program_trace_node` trace 构建，及无引用点的私有 `_node_label`）已拆出至 `trace_nodes.py`（前四者在本文件函数体内确有引用，属**正常 import**，无 `# noqa`；`_node_label` 全仓库无 import 点，随簇迁入不再暴露）；**首个被剥离的 section-judge 簇**——§9「信号棒」四判定器（`judge_signal_bar_closed`/`judge_signal_bar_direction`/`judge_signal_bar_length`/`judge_follow_through` 及 §9.2 的 4 个 bar-type 常量）已拆出至 `signal_bar_judges.py`（四 judge 在 `apply_stage2` 的 §9 填充链中确有引用，属**正常 import**，无 `# noqa`；随其迁出后 `SIGNAL_BAR_LONG_ATR_RATIO` 在本文件内已无引用、仅供测试从本命名空间取用，故其 `decision_thresholds` import 行补 `# noqa: F401` 转为纯重导出）；**第二个被剥离的 section-judge**——§2.3「方向」判定器 `judge_direction`（五信号投票+中窗口确认）已拆出至 `direction_judge.py`（在 `apply_stage2` 链 `direction, fill_23 = judge_direction(frame)` 确有引用，属**正常 import**，无 `# noqa`；随其迁出后 7 个 `DIRECTION_*`/`OVERLAP_*` 阈值常量在本文件内已无引用、且全仓库无站点从本命名空间取用，故直接从 import 块剪除、不做重导出，而 `EMA_SLOPE_LOOKBACK`/`TREND_BAR_DOMINANCE_RATIO` 因仍被 `judge_market_chaos` 等引用而保留）；**第三个被剥离的 section-judge 簇**——§1「市场诊断」两判定器 `judge_data_sufficiency`（§1.1 数据充分性，恒 `是`）/`judge_market_chaos`（§1.3 极端混乱，恒 `否`+三项客观混乱信号计数）已拆出至 `diagnostic_judges.py`（两 judge 在 `apply_stage1` 链 `fill_11 = judge_data_sufficiency(frame)`/`fill_13 = judge_market_chaos(frame)` 确有引用，属**正常 import**，无 `# noqa`；随其迁出后 3 个 `CHAOS_*` 与 `TREND_BAR_DOMINANCE_RATIO` 在本文件内已无引用、且全仓库无站点从本命名空间取用，故直接从 import 块剪除、不做重导出，而 `BAR_COUNT_THRESHOLD` 迁出后本文件内亦无引用但仍被 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py` 从本命名空间取用，故其 `decision_thresholds` import 行补 `# noqa: F401` 转为纯重导出；`ALWAYS_IN_WINDOW`/`EMA_SLOPE_LOOKBACK` 因仍被 AlwaysIn/Momentum 引用而保留）；**第四个被剥离的 section-judge 簇**——§2「趋势状态」两判定器 `judge_always_in`（§2.4 Always-In 状态，近端 K8-K1 主判+背景 K20-K1 参考双窗口 Brooks 对齐）/`judge_momentum_strength`（§2.5 动量强度，双窗口三近端信号：趋势棒占优、K 线重叠、回撤深度）已拆出至 `always_in_judges.py`（两 judge 在 `apply_stage2` 链 `fill_24 = judge_always_in(frame)`/`fill_25 = judge_momentum_strength(frame, direction=direction)` 确有引用，属**正常 import**，无 `# noqa`；因这两个 judge 共享私有辅助 `_max_pullback_atr`，故连同 §2.4 专属的 `_weighted_ema_side_weights`/`_eval_always_in_gates` 一并整簇迁出，避免共享辅助被跨模块拆散；随其迁出后 `bar_geometry` 三几何原语整块 import 与 `import math` 在本文件内已无引用而剪除、9 个 `ALWAYS_IN_*`/`MOMENTUM_*`/`EMA_SLOPE_LOOKBACK` 阈值常量在本文件内已无引用且全仓库无站点从本命名空间取用故直接剪除、不做重导出，而 `ALWAYS_IN_SAME_SIDE_RATIO` 迁出后本文件内亦无引用但仍被 `test_decision_nodes_judges.py` 从本命名空间取用，故其 `decision_thresholds` import 行补 `# noqa: F401` 转为纯重导出；至此 `decision_nodes.py` 内已无任何 section-judge 定义，仅余 SignalBarJudge 辅助、OrderMethodRouter、OverrideArbiter 与 `DecisionNodeEngine` 编排层）；**第五个被剥离的簇**——非 section-judge 的**受控 override 裁决层** OverrideArbiter（4 公开 `merge_program_nodes`/`merge_program_nodes_head`/`apply_overrides`/`write_override_trace` + 5 私有 `_conservativeness_rank`/`_node_id_sort_key`/`_validate_dir_override`/`_sync_always_in_from_24_override`/`_sync_order_type_from_11_override`）已拆出至 `override_arbiter.py`（`apply_overrides`/`merge_program_nodes`/`merge_program_nodes_head` 在 `DecisionNodeEngine.apply_stage1`/`apply_stage2` 链确有引用，属**正常 import**，无 `# noqa`；`write_override_trace` 迁出后本文件内已无引用但仍被 `test_decision_nodes_judges.py` 从本命名空间取用，故补 `# noqa: F401` 转纯重导出；随其迁出后 5 个 override 权限集常量 `AI_PRIMARY_NODES`/`AI_PRIMARY_SUPPLEMENT_NODES`/`LOCKED_NODES`/`OVERRIDABLE_NODES`/`SAFETY_GATE_NODES` 在本文件内已无引用且全仓库无站点从本命名空间取用故直接剪除、不做重导出，唯一的 `TRACE_ANSWERS`（来自 `decision_tree`）走 `apply_overrides` 函数体内 call-time import 打破环；至此 `decision_nodes.py` 仅余 SignalBarJudge 辅助、OrderMethodRouter 与 `DecisionNodeEngine` 编排层）；**第六个被剥离的簇**——§11「下单方式路由」层 OrderMethodRouter（单个大函数 `route_order_method` + 模块级 `_CYCLE_ORDER_METHOD` 路由表，内嵌 `_trace_answer`/`_sec14_violated`/`_has_trade_prices` 辅助随函数整体迁出、`_METHOD_NODE`/`_node_reasons` 为函数内局部表）已拆出至 `order_method_router.py`（`route_order_method` 在 `DecisionNodeEngine.apply_stage2` 链 `sec11_fills = route_order_method(stage1_json, decision, decision_trace)` 确有引用，属**正常 import**，无 `# noqa`；该簇只依赖唯一叶子模块 `trace_nodes`（`_coerce_dict`/`_coerce_trace_list`/`NodeFill`）、不引用任何 judge/override、不回依赖 `decision_nodes`，故 `order_method_router` ← `decision_nodes` 无环；至此 `decision_nodes.py` 仅余 SignalBarJudge 辅助与 `DecisionNodeEngine` 编排层，大文件拆分接近尾声）；**第七个被剥离的簇**——§9「信号棒/限价单上下文」辅助（`_get_signal_seq` 定位信号棒序号、`has_background_limit_path` §9.0P 背景限价路径检测、`is_planned_limit_order` 计划型限价单判定）已拆出至 `signal_context.py`（三者在 `DecisionNodeEngine.apply_stage2` 链 `sig = _get_signal_seq(...)`/`_planned_limit = is_planned_limit_order(out)`/`has_background_limit_path(out)` 确有引用，属**正常 import**，无 `# noqa`；该簇近乎 stdlib-only（`logging`/`typing.Any`），唯一项目触点 `parse_k_seq`（来自 `util/price_tick`，仅 import stdlib）走 `_get_signal_seq` 函数体内 call-time import 打破环、不引用任何 judge/override/router、不回依赖 `decision_nodes`，故 `signal_context` ← `decision_nodes` 无环；至此 `decision_nodes.py` 仅余 `DecisionNodeEngine` 编排层——大文件拆分 M3 收官在即）。因 `from pa_agent.ai.decision_nodes import <名字>` 站点仍能从 `decision_nodes` 命名空间取到同一对象，跨模块 import 逐字节兼容。
  - `decision_node_engine.py`：**DecisionNodeEngine 编排层模块**（M3 收官刀）。承接原 `decision_nodes.py` 内最后的 `DecisionNodeEngine` 类，负责 `apply_stage1()` / `apply_stage2()` 两个确定性编排入口：串联 diagnostic/direction/always-in/signal-bar/order-method/override/trace 等已拆出的叶子模块，写回 `gate_trace` / `decision_trace` / `trend_context` / `bar_analysis.always_in`。`decision_nodes.py` 现已缩为 兼容 facade，仅重导出历史 import 路径所需的 judges、helpers、thresholds 与 `DecisionNodeEngine`，不再承载实现逻辑；M3 拆分目标完成。
  - `decision_thresholds.py`：决策节点引擎的**调参常量与节点权限集纯数据模块**（仅 `from __future__ import annotations`，无 import、无副作用）。含 §1.1 数据充分性阈值（`BAR_COUNT_THRESHOLD`）、§2.3 方向投票窗口/阈值、§2.4 Always-In 窗口/占比、§2.5 动量强度阈值、§1.3 极端混沌阈值，以及 override 权限集（`LOCKED_NODES`/`OVERRIDABLE_NODES`/`AI_PRIMARY_NODES`/`SAFETY_GATE_NODES` 等）。由 `decision_nodes.py`、`trend_context.py` 与 `preflight.py`（取 `BAR_COUNT_THRESHOLD`）共同引用，是后续把各 section-judge 拆成独立子模块的无环依赖前提；取值须与原文逐字节一致（编码经调优的 Brooks 价格行为阈值与闸门/override 策略）。
  - `bar_geometry.py`：**纯 K 线几何原语模块**（stdlib-only，仅 `from __future__ import annotations` + `typing.Any`，无项目 import、无副作用）。含 `_count_trend_bars`（趋势棒计数：body/close-position 阈值分类）、`_mean_overlap_ratio`（相邻棒重叠比均值）、`_find_swings`（左右各 2 根枢轴的波段高低点检测）。与 `decision_thresholds.py` 同为 `decision_nodes.py`/`trend_context.py` 的共享底层依赖；行为须与原文一致（section-judge 依赖这些分类阈值）。
  - `preflight.py`：**Stage1 前置数据质量闸门模块**（near-stdlib：`logging`/`math`/`dataclass`/`typing.Any`，仅从 `decision_thresholds` 取 `BAR_COUNT_THRESHOLD`，无其他项目依赖、无副作用）。含 `PreflightResult`（frozen dataclass 结果类型）与纯函数 `check_preflight_data`（对外入口，异常保护）/`_check_preflight_data_inner`（内部实现）：依次校验「frame/bars 非空且 OHLC 合法 → 已收盘 K 线数 ≥ `BAR_COUNT_THRESHOLD`(20) → EMA20/ATR14 非全 NaN」，任一不满足即保守返回 `ok=False` 及三类 `failed_check` 令牌（`bars_empty_or_bad_ohlc`/`bar_count_lt_20`/`indicators_all_nan`）。由 `orchestrator/two_stage.py`（`submit()` Step 2.5 前置闸门）与 `test_decision_nodes_preflight.py` 经 `decision_nodes` 命名空间重导出调用；三类令牌与中文 reason 串被下游消费，行为须与原文逐字节一致。
  - `trace_nodes.py`：**决策 trace 结果层模块**（near-stdlib：`logging`/`dataclass`/`typing.Any`，对 `decision_tree` 的 `node_label` 走 call-time import，无 import 期项目依赖、无副作用）。含 `NodeFill`（frozen dataclass——每个 section-judge 的返回类型）、`_coerce_dict`/`_coerce_trace_list`（把松散 AI JSON 防御性归一为 dict/trace 列表）、`_node_label`/`build_program_trace_node`（把 `NodeFill` 转成合法决策 trace dict，问题文本惰性解析）。是**每个 judge 都会 return/消费的公共结果层**——先抽成无环叶子模块（`trace_nodes` ← `decision_nodes`），后续把 `DirectionJudge`/`AlwaysInJudge`/`MomentumJudge`/`SignalBarJudge` 等各自拆成独立子模块时才能各自 `from pa_agent.ai.trace_nodes import NodeFill` 而不与 `decision_nodes` 形成 import 循环。`decision_nodes.py` 从本模块正常 import 前四者（函数体内确有引用，无 `# noqa`）；`_node_label` 全仓库无 import 点，随簇迁入本模块、`decision_nodes` 不再暴露；trace dict 键序与惰性 `node_label` 回退须与原文逐字节一致。
  - `signal_bar_judges.py`：**§9「信号棒」判定器簇模块**（stdlib-only 依赖：仅 `from __future__ import annotations` + `typing.Any`，加两个叶子模块 import——`SIGNAL_BAR_LONG_ATR_RATIO`（来自 `decision_thresholds`）与 `NodeFill`（来自 `trace_nodes`），无其他项目依赖、无副作用）。含 4 个确定性 judge——`judge_signal_bar_closed`（§9.1 信号棒恒已收盘）、`judge_signal_bar_direction`（§9.2 bar_type 与下单方向一致性，外包棒降级为「弱」集合并告警）、`judge_signal_bar_length`（§9.3 过长棒判定，对比 `SIGNAL_BAR_LONG_ATR_RATIO`）、`judge_follow_through`（§9.5 follow_through_1_2 映射）——及 §9.2 的 4 个私有 bar-type 常量（`_LONG_BAR_TYPES`/`_SHORT_BAR_TYPES`/`_LONG_BAR_TYPES_WEAK`/`_SHORT_BAR_TYPES_WEAK`）。是 M3 拆分中**首个被剥离的 section-judge 簇**（前四刀先抽常量/几何/闸门/`NodeFill` 结果层等共享底层，本刀才拆 judge 本身）：因该簇只依赖上述两个叶子模块、不引用任何其他 judge、不回依赖 `decision_nodes`，故 `signal_bar_judges` ← `decision_nodes` 无环，可干净剥离。由 `decision_nodes.py`（`apply_stage2` 的 §9 填充链）正常 import 四 judge，并从 `decision_nodes` 命名空间重导出供 `test_decision_nodes_judges.py` 调用；`answer`/中文 reason 串/`bar_range` 取值须与原文逐字节一致。
  - `direction_judge.py`：**§2.3「方向」判定器模块**（near-stdlib 依赖：仅 `from __future__ import annotations` + `math` + `typing.Any`，加三个叶子模块 import——几何原语 `_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio`（来自 `bar_geometry`）、9 个方向/重叠/斜率/趋势棒阈值常量（来自 `decision_thresholds`）与 `NodeFill`（来自 `trace_nodes`），无其他项目依赖、无副作用）。含单个自足函数 `judge_direction(frame) -> (direction, NodeFill)`：五信号投票（S1 EMA 斜率、S2 加权收盘重心、S3 波段结构 HH/HL vs LL/LH、S4 趋势棒占优、S5 K 线重叠比）+ 中窗口确认过滤，分类市场方向并填充 §2.3 节点（内嵌 `_weighted_avg`/`_weighted_avg_med` 辅助随函数整体迁出，不与其他 judge 共享）。是 M3 拆分中**第二个被剥离的 section-judge**：因它是单函数、无跨 judge 共享的私有辅助、依赖全为叶子模块、不引用任何其他 judge、不回依赖 `decision_nodes`，故 `direction_judge` ← `decision_nodes` 无环，可一刀干净剥离。由 `decision_nodes.py`（`apply_stage2` 链 `direction, fill_23 = judge_direction(frame)`）正常 import，并从 `decision_nodes` 命名空间重导出供 `test_decision_nodes_judges.py`/`test_trend_context.py`/`prompt_assembler.py` 调用；`direction`/`answer`/中文 reason 串/`score` 算术/`bar_range` 取值须与原文逐字节一致。
  - `diagnostic_judges.py`：**§1「市场诊断」判定器簇模块**（near-stdlib 依赖：仅 `from __future__ import annotations` + `math` + `typing.Any`，加三个叶子模块 import——几何原语 `_count_trend_bars`/`_mean_overlap_ratio`（来自 `bar_geometry`）、7 个诊断/窗口/斜率/趋势棒阈值常量（来自 `decision_thresholds`）与 `NodeFill`（来自 `trace_nodes`），无其他项目依赖、无副作用）。含 2 个确定性 judge——`judge_data_sufficiency`（§1.1 数据充分性：前置闸门已通过，恒 `是`，reason 记录已收盘 K 线数）与 `judge_market_chaos`（§1.3 极端混乱：extreme_tr 需 AI 综合判断、不设硬性程序门槛，故恒 `否`，但 reason 内嵌三项客观混乱信号计数——EMA 斜率平坦、K 线重叠高、无方向共识——供 AI 决定是否提交 §1.3=是 覆盖）。是 M3 拆分中**第三个被剥离的 section-judge 簇**：因该簇只依赖上述三个叶子模块、不引用任何其他 judge、不回依赖 `decision_nodes`，故 `diagnostic_judges` ← `decision_nodes` 无环，可干净剥离。由 `decision_nodes.py`（`apply_stage1` 链 `fill_11`/`fill_13`）正常 import，并从 `decision_nodes` 命名空间重导出供 `test_decision_nodes_judges.py`/`prompt_assembler.py` 调用；`answer`/中文 reason 串/`chaos_score` 算术/`bar_range` 取值须与原文逐字节一致。
  - `always_in_judges.py`：**§2「趋势状态」判定器簇模块**（near-stdlib 依赖：仅 `from __future__ import annotations` + `math` + `typing.Any`，加三个叶子模块 import——几何原语 `_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio`（来自 `bar_geometry`）、10 个 Always-In/动量/斜率阈值常量（来自 `decision_thresholds`）与 `NodeFill`（来自 `trace_nodes`），无其他项目依赖、无副作用）。含 2 个确定性 judge——`judge_always_in`（§2.4 Always-In 状态：近端 K8-K1 为主判窗口捕捉当前惯性/spike、背景 K20-K1 仅作参考不否决，三闸门 AIL/AIS——加权同侧占比、EMA 斜率确认、波段结构+浅回撤——按 Brooks 并列原则输出 `是`/`否`+`AIL`/`AIS` branch）与 `judge_momentum_strength`（§2.5 动量强度：双窗口三近端信号 M1 趋势棒占优/M2 K 线重叠/M3 回撤深度，`strong_count≥2→是`/`==1→中性 broad_channel`/`==0→否`）——及 3 个私有辅助 `_weighted_ema_side_weights`（EMA 上下侧线性衰减加权计数）/`_eval_always_in_gates`（AIL/AIS 三闸门束评估）/`_max_pullback_atr`（窗口内最大回撤深度/ATR，**§2.4/§2.5 共享辅助**）。是 M3 拆分中**第四个被剥离的 section-judge 簇**：因这两个 judge 共享私有辅助 `_max_pullback_atr`（`_eval_always_in_gates` 与 `judge_momentum_strength` 均调用），故连同 §2.4 专属的 `_weighted_ema_side_weights`/`_eval_always_in_gates` 一并整簇迁出，避免共享辅助被跨模块拆散；又因该簇只依赖上述三个叶子模块、不引用任何其他 judge、不回依赖 `decision_nodes`，故 `always_in_judges` ← `decision_nodes` 无环，可干净剥离。由 `decision_nodes.py`（`apply_stage2` 链 `fill_24 = judge_always_in(frame)`/`fill_25 = judge_momentum_strength(frame, direction=direction)`）正常 import，并从 `decision_nodes` 命名空间重导出供 `test_decision_nodes_judges.py`/`test_trend_context.py`/`prompt_assembler.py` 调用；`answer`/`branch`/中文 reason 串/双窗口 gate/评分算术/`bar_range` 取值须与原文逐字节一致。
  - `override_arbiter.py`：**受控 override 裁决簇模块**（near-stdlib 依赖：仅 `from __future__ import annotations` + `logging` + `typing.Any`，加两个叶子模块 import——5 个 override 权限集常量 `AI_PRIMARY_NODES`/`AI_PRIMARY_SUPPLEMENT_NODES`/`LOCKED_NODES`/`OVERRIDABLE_NODES`/`SAFETY_GATE_NODES`（来自 `decision_thresholds`）与 `_coerce_trace_list`（来自 `trace_nodes`），唯一的 `TRACE_ANSWERS`（来自 `decision_tree`）走 `apply_overrides` 函数体内 **call-time import** 打破环，无其他 import 期项目依赖、无副作用）。含 4 个公开函数——`merge_program_nodes`（把程序算出的决策节点按 `node_id` 并入 AI trace：默认 PROGRAM-AUTHORITATIVE 程序结果替换 AI 节点，AI-PRIMARY 集（§1.3/§2.5）保留 AI 版本，新节点按 `node_id` 数字序插入）、`merge_program_nodes_head`（gate_result=wait/unknown 时把新节点前置到 head，AI 终止节点留末尾）、`apply_overrides`（对 AI 提交的 `node_overrides` 按 7 条规则裁决：非 list 忽略/无效跳过/locked 忽略/缺 override_reason 拒绝/safety gate 激进方向拒绝/§2.3 方向一致性/OVERRIDABLE 接受并 §11 sync order_type + §2.4 sync always_in）、`write_override_trace`（在节点上记录 program 原值与 AI override）——及 5 个私有辅助 `_conservativeness_rank`（安全闸门保守度排序）/`_node_id_sort_key`（'1.1'→(1,1,'1.1') 数字排序键）/`_validate_dir_override`（§2.3 answer/branch 一致性）/`_sync_always_in_from_24_override`（§2.4 override 后同步 bar_analysis.always_in）/`_sync_order_type_from_11_override`（§11 override 后同步 decision.order_type，突破单无 basis 回退限价单）。是 M3 拆分中**第五个被剥离的簇**（前八刀先抽共享底层与全部 section-judge，本刀转向决策合并与受控 override 裁决层）：因该簇高内聚自足、只依赖上述两个叶子模块（`TRACE_ANSWERS` 走 call-time import）、不被任何其他 judge 引用、不回依赖 `decision_nodes`，故 `override_arbiter` ← `decision_nodes` 无环，可干净剥离。由 `decision_nodes.py`（`DecisionNodeEngine.apply_stage1`/`apply_stage2`）正常 import `apply_overrides`/`merge_program_nodes`/`merge_program_nodes_head`，并从 `decision_nodes` 命名空间重导出 `write_override_trace` 供 `test_decision_nodes_judges.py` 调用；合并模式、override 规则顺序、中文日志/reason 串、节点键写入须与原文逐字节一致。
  - `order_method_router.py`：**§11「下单方式路由」簇模块**（stdlib-only 依赖：仅 `from __future__ import annotations` + `typing.Any`，加唯一叶子模块 import——`_coerce_dict`/`_coerce_trace_list`/`NodeFill`（来自 `trace_nodes`），无其他项目依赖、无副作用、无 `logger`（本簇原本不记日志））。含单个自足大函数 `route_order_method(stage1_json, decision, decision_trace)`：把阶段一 `cycle_position`（及模型自身的 order_type / entry_basis 提示）经 `_CYCLE_ORDER_METHOD` 路由表映射为最终下单方式（市价单/突破单/限价单/不下单），在 §10.3=否 / §14 违规安全闸门下短路返回、处理 spike_ending/breakout_fallback 例外分支、就地改写 `decision.order_type` 并生成 §11 trace 节点（内嵌 `_trace_answer`/`_sec14_violated`/`_has_trade_prices` 辅助随函数整体迁出，`_METHOD_NODE`/`_node_reasons` 为函数内局部表）。`_has_trade_prices()` 只要求 `entry_price` / `stop_loss_price` / 主 `take_profit_price` 三个核心价格，`take_profit_price_2` 是可选分批止盈，不能阻止 broad_channel 下带完整 `entry_basis_bar/extreme` 的模型突破单被保留。是 M3 拆分中**第六个被剥离的簇**（前五刀先抽共享底层、全部 section-judge 与 override 裁决层，本刀转向 §11 下单方式路由层）：因该簇高内聚自足、只依赖唯一叶子模块 `trace_nodes`、不引用任何 judge/override、不回依赖 `decision_nodes`，故 `order_method_router` ← `decision_nodes` 无环，可一刀干净剥离。由 `decision_nodes.py`（`apply_stage2` 链 `sec11_fills = route_order_method(stage1_json, decision, decision_trace)`）正常 import，并从 `decision_nodes` 命名空间重导出供 `test_order_method_router.py` 调用；路由表、安全闸门短路、spike/breakout 例外、中文 reason 串、§11 节点 answer 取值须与原文逐字节一致。
  - `signal_context.py`：**§9 信号棒/限价单上下文辅助簇模块**（near-stdlib 依赖：仅 `from __future__ import annotations` + `logging` + `typing.Any`，唯一项目触点 `parse_k_seq`（来自 `util/price_tick`，该模块仅 import stdlib `re`/`typing`）走 `_get_signal_seq` 函数体内 **call-time import** 打破环，无其他 import 期项目依赖、无副作用）。含 3 个确定性辅助——`_get_signal_seq`（定位信号棒序号：优先 `bar_analysis.signal_bar.bar` 经 `parse_k_seq` 解析，否则默认 K1）、`has_background_limit_path`（§9.0P=是 背景驱动限价路径检测）、`is_planned_limit_order`（计划型限价单判定：限价单 + 背景路径/pending 入场棒 + 弱信号棒 pattern 白名单，内部调用 `has_background_limit_path`）。是 M3 拆分中**第七个被剥离的簇**（前六刀先抽共享底层、全部 section-judge、override 裁决层与 §11 下单方式路由层，本刀转向 `apply_stage2` 依赖的最后一组独立辅助）：因该簇高内聚自足、近乎 stdlib-only（`parse_k_seq` 走 call-time import）、不引用任何 judge/override/router、不回依赖 `decision_nodes`，故 `signal_context` ← `decision_nodes` 无环，可一刀干净剥离。由 `decision_nodes.py`（`apply_stage2` 链 `sig = _get_signal_seq(...)`/`_planned_limit = is_planned_limit_order(out)`/`has_background_limit_path(out)`）正常 import，并从 `decision_nodes` 命名空间重导出供 `stage2_normalizer.py`（两处 call-time import）/`test_decision_nodes_judges.py` 调用；§9.0P 检测、pending/白名单判定分支、默认 K1 兜底、中文 reason 串须与原文逐字节一致。至此 `decision_nodes.py` 仅余 `DecisionNodeEngine` 编排层（`apply_stage1`/`apply_stage2`），M3 大文件拆分收官在即。
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
  - `factory.py`：数据源工厂，返回 MT5 / TradingView / AkShare / EastMoney / Tushare / YFinance 源。`create_data_source(kind, settings=None)` 为纯构造器；仅 Tushare 分支需 `settings`（取 API token）。调用方（`app_context.bootstrap`、`main_window._switch_data_source`）已持有 `Settings`，应**注入**而非让工厂读盘；`settings` 省略时 Tushare 分支才惰性 `load_settings(SETTINGS_JSON_PATH)` 兜底（向后兼容独立/脚本化构造与既有单测）。`Settings` 仅注解用途，置于 `TYPE_CHECKING` 块导入。
  - `mt5.py`：MetaTrader5 连接。
  - `tradingview.py` / `tradingview_connectivity.py`：TradingView WebSocket/HTTP 数据。
  - `akshare_source.py` / `eastmoney_source.py` / `tushare_source.py` / `yfinance_source.py`：A 股/期货数据源。
  - `base.py`：通用数据模型 `KlineFrame`、`KlineBar`、`IndicatorBundle` 与 `DataSource` ABC。M7 已新增默认 `DataSource.has_forming_bar_at_head(...)`，统一 forming-bar 语义入口：默认实现委托 `bar_close_wait.has_forming_bar_at_head()`，并在未显式传 `now_ms` 时通过 `reference_now_ms(data_source=self)` 优先使用数据源可提供的 broker/server time；具体数据源可 override 以承接交易所/session 特例。当前 `EastMoneySource` 已 override 为 `_ashare_head_bar_live(timeframe)` 语义（日线午休仍 live），`AkShareSource` 已 override 为 `_ashare_session_open()` 语义（仅连续交易时段 live），`TradingViewSource` 已 override 为 `seconds_until_bar_closes()` 倒计时语义（保留 TradingView 时间戳固定偏移取模行为），`YFinanceSource.latest_snapshot()` 与 `MT5Source.latest_snapshot()` 复用 ABC 默认判定写回头部 `closed` 标记；MT5 默认判定会通过 `server_time_ms()` 优先使用 broker tick 时间。
  - `snapshot.py` / `bar_close_wait.py` / `refresh_loop.py`：实时刷新、K 线收盘等待与快照构建。`snapshot.py` 内部通过 `_head_is_forming(...)` 优先调用 `DataSource.has_forming_bar_at_head(...)`，无 `data_source` 时回退原 helper，保持纯函数测试与旧调用兼容；`MainWindow._build_chart_frame_from_bars()` 已把当前 `ctx.data_source` 传入 `build_live_frame()` / `build_display_frame()`，使 GUI 图表与分析快照进入统一入口。
  - `kline_adjust.py` / `market_defaults.py`：复权调整与市场默认值。
- **`pa_agent/gui/`**：PyQt6 GUI。
  - `main_window.py`：主窗口（近 200KB，功能高度集中）。
  - `settings_dialog.py` / `ai_model_settings_dialog.py` / `general_settings_dialog.py` / `feishu_settings_dialog.py`：设置对话框。
  - `decision_flow_viz.py` / `decision_panel.py` / `decision_tree_panel.py`：决策可视化。
  - `chart_widget.py` / `widgets/`：K 线图表与自定义 widgets。
  - `theme/`：QSS 主题与 token。
  - `ai_stream_window.py` / `conversation_widget.py`：实时推理流与会话管理。
- **`pa_agent/orchestrator/`**：业务编排。
  - `two_stage.py`：两阶段分析主流程。Stage1/Stage2 的校验错误富化由单一 `_enrich_validation_message(err, reply, *, stage)` 完成（`stage="stage1"|"stage2"` 仅切换少量中文提示串，输出与原分函数逐字节一致）。网络降级链（`_stream_chat_resilient` 内 WorkBuddy→Cursor→QClaw）的三个 `_try_*_fallback` 是薄包装器（各自 call-time 导入连接器 `apply_*`/`is_openclaw_*_model` 以保持测试可 patch、守卫、调用 `apply_*`），相同尾部（`update_provider`+`save_settings`+`update_api_key`+**`pending_writer.set_api_key`**+切换日志）合并到共享 `_finish_provider_fallback(provider_name, err)`；返回语义与日志文本与拆分前一致。降级切换 provider（新 key）时，尾部除刷新日志脱敏 formatter（`update_api_key`）外，还须 `set_api_key` 刷新记录写入器的脱敏 key（`hasattr` 守卫），否则同一 `submit()` 内降级后落盘的记录会用旧 key 脱敏、泄漏新 key 明文——与 GUI「AI 模型」设置保存路径的脱敏语义一致。巨型方法 `TwoStageOrchestrator.submit()`（约 647 行、跨 Stage1→路由/经验→Stage2→落盘六段、含多处 `nonlocal` 闭包与 early-return）正按报告 §5.2 M4 逐步拆为阶段方法（roadmap 目标 `_run_stage1`/`_run_stage2`/`_route_and_load_experience`/`_persist_result`）。与 M1/M2/M3 的**叶子模块提取**不同，M4 是**同类内的方法级拆分**——子方法共享 `self` 与跨阶段可变局部状态，无法用纯函数等价脚本验证，须靠既有 mock-based 集成测试套件（`tests/integration/test_two_stage_*.py` + `test_gate_shortcircuit.py` + `tests/unit/test_decision_nodes_orchestrator.py`）做 baseline 对比（happy_path/gate/stage1_syntax/stage1_missing/stage2_invalid/network/cancel）。**第一刀**已将 Steps 10-11（§路由策略文件 + 加载经验条目）拆出为实例方法 `_route_and_load_experience(self, stage1_json) -> tuple[list[str], list[Any]]`——它是 `submit()` 中唯一零闭包、零 early-return、零副作用的自足片段（只读 `stage1_json` 与 `self._router`/`self._settings`/`self._exp_reader`，中间局部 `cycle_position`/`direction`/`patterns` 经核查仅在块内引用、Step 12+ 只用 `strategy_files`/`experience_entries`，故可完整封装），`submit()` 内替换为单行解包 `strategy_files, experience_entries = self._route_and_load_experience(stage1_json)`；router 分支/经验加载三分支/中间局部提取须与原文逐字节一致（行为等价，靠集成测试基线守护）。**第二刀**已将 Steps 19.5-24（预测日志 + 构建 final record + `save_full` + `RecordSaved` 事件 + return）拆出为实例方法 `_persist_result(self, *, record, on_event, stage1_json, messages_s1, reply_s1, messages_s2, reply_s2, stage2_json, strategy_files, experience_entries, s1_usage_calls, s2_usage_calls, _enable_next_bar) -> AnalysisRecord`——它是 `_route_and_load_experience` 之后 `submit()` 中最自足的一段（纯只读聚合已算好的状态 + 单次落盘，无 early-return 回流、无 `nonlocal` 闭包，是 happy-path 的唯一终点：所有中途失败/取消 early-return 都在本段之前），保留 next_bar/next_cycle 预测日志分支、`usage_total` 双层 `_accumulate_usage_calls`、11 字段 `record.model_copy`、`save_full`、`RecordSaved`、`return record`，`submit()` 内替换为单次 `return self._persist_result(...)` 关键字实参调用；`submit()` 降至 575 行。router 分支/预测日志/落盘逻辑须与原文逐字节一致（行为等价，靠集成测试基线守护）。**第三刀**已将 Step 13 的闸门短路终局（`gate_result ∈ {wait, unknown}` 时本地合成阶段二结果、不调模型、落盘返回）拆出为守卫方法 `_try_gate_short_circuit(self, *, record, on_event, on_stage_prompt, on_stage2_content, stage1_json, messages_s1, reply_s1, strategy_files, experience_entries) -> AnalysisRecord | None`——因 `_run_stage2`（Steps 12-19）经核查内含五处 `return record` early-return 与两组 `nonlocal` 流式闭包（`_on_s2_reasoning`/`_on_s2_content`/`_call_s2_retry`），整块外提须引入新控制流信号类型、违背原子提交且风险高，故先切其中最自足的单出口分支（计算→`save_full`→`RecordSaved`→return，无闭包/`nonlocal`，与 `_persist_result` 同构），返回 `None` 表示放行、`submit()` 内 `if _gate_record is not None: return _gate_record` 后继续 Step 14；`submit()` 降至 552 行，靠 `test_gate_shortcircuit` 专项守护。**第四刀**已将 Step 14（阶段二 prompt 组装）拆出为纯实例方法 `_build_stage2_messages(self, *, frame, messages_s1, reply_s1, stage1_json, strategy_files, experience_entries, record, previous_record) -> tuple[list[dict], bool, int]`——结构与第一刀 `_route_and_load_experience` 同构（无闭包/无 early-return/无副作用）：解析 `self._settings.general` 的 `enable_next_bar_prediction`/`structure_flip_cooldown_bars` 两标志（带 `getattr` 兜底）+ `build_stage2_continuation` 组装 `messages_s2`；因两标志在后续校验（Step 17 `validate_kwargs`）、Step 18（`pop next_bar_prediction`）、Step 19.5（`_persist_result` 预测日志）复用，返回 `(messages_s2, enable_next_bar, flip_cooldown)` 三元组，`submit()` 内三元解包接收；`submit()` 降至 538 行。**第五刀**已将 Steps 15-24（Stage 2 调用/校验/落盘核心）拆出为实例方法 `_run_stage2(self, *, record, on_event, on_stage_prompt, on_stage2_reasoning, on_stage2_content, cancel_token, frame, messages_s1, reply_s1, stage1_json, strategy_files, experience_entries, messages_s2, previous_record, _enable_next_bar, _flip_cooldown, _thinking, _effort, s1_usage_calls) -> AnalysisRecord`，**收官 Stage 2 拆解**——第三刀曾判此块「须引入新控制流信号类型、风险高」，但第二刀 `_persist_result` 外提后其**四条路径全部返回 `AnalysisRecord`**（网络错误/调用后取消/校验失败三终局 + happy-path 委托 `_persist_result`），故整块干净外提、`submit()` 尾部 `return self._run_stage2(...)` 尾调、无需新类型；两组 `nonlocal` 流式闭包（`_on_s2_reasoning`/`_on_s2_content` 共享 `s2_streamed_*`、retry 闭包 `_call_s2_retry`）随方法整体搬迁、捕获关系不变，in-body 形参名与原局部逐字一致（`_enable_next_bar`/`_flip_cooldown`/`_thinking`/`_effort`）保证方法体逐字节等价，靠 `test_two_stage_stage2_invalid_value`/`_network_timeout`/`_user_cancel` 三终局专项守护；`submit()` 降至 334 行。M4 剩余目标：仅余 `_run_stage1`（Steps 3-9，含 Stage 1 自身的两组 `nonlocal` 流式闭包 `s1_streamed_*`/`_call_s1_retry` + 语法/缺字段/网络/取消终局，须逐场景比对），收官后 `submit()` 降为薄编排层（Steps 1-2 + 四个阶段方法的顺序调用）。
  - `two_stage.py`（R39 更新 / M4 收官）：第六刀已将 Steps 3-9（Stage 1 prompt 组装、模型调用、调用后取消检查、校验与 retry、`Stage1Done`）拆出为实例方法 `_run_stage1(...) -> AnalysisRecord | tuple[dict, list[dict], Any, list[Any], bool, str]`。因 Stage 1 的 happy path 仍需继续进入 Steps 10-24，`_run_stage1` 与 `_run_stage2` 不同：网络错误、调用后取消、校验失败三条终局路径返回 partial `AnalysisRecord`，校验通过路径返回 `(stage1_json, messages_s1, reply_s1, s1_usage_calls, _thinking, _effort)` 成功元组；`submit()` 以 `isinstance(_s1, AnalysisRecord)` 分派，终局即返回，否则解包后继续路由/经验加载与 Stage 2。两组 Stage 1 `nonlocal` 流式闭包（`_on_s1_reasoning`/`_on_s1_content` 共享 `s1_streamed_*`、retry 闭包 `_call_s1_retry`）随方法整体搬迁，Steps 3-9 主体经 anchored block 对比确认逐字节一致；`submit()` 已降至 151 行。至此报告 §5.2 M4 的四个目标 `_route_and_load_experience` / `_persist_result` / `_run_stage2` / `_run_stage1` 全部完成，后续迭代转入 M2 的 `SchemaValidator` 拆分与 M1 的 `Stage1PromptBuilder` / `Stage2PromptBuilder` 拆分。
  - `two_stage.py`（R44 更新 / M5 fallback 尾部下沉）：`_finish_provider_fallback(provider_name, err)` 已改为薄 wrapper，委托 `ProviderSyncService(save_path=SETTINGS_JSON_PATH).finish_provider_fallback(...)` 执行共享尾部；三个 `_try_qclaw_fallback` / `_try_cursor_fallback` / `_try_workbuddy_fallback` 仍保留 connector call-time import、模型 guard、`apply_*_provider_to_settings` 调用和返回语义，确保测试 patch 点与 WorkBuddy → Cursor → QClaw 尝试顺序不变。
  - `free_chat.py`：分析后自由追问与会话管理。
  - `validation_retry.py`：校验失败后的重试策略。
- **`pa_agent/records/`**：持久化。
  - `pending_writer.py`：分析记录写入（会自动对明文 API Key 脱敏——用构造时传入的 `api_key` 递归掩码；运行时改 key 后须调 `set_api_key` 同步，否则记录仍用旧 key 脱敏。当前所有运行时改 key 路径均已配套：GUI「AI 模型」保存（`main_window._open_ai_model_settings_dialog`）与 orchestrator provider 降级（`two_stage._finish_provider_fallback`）都在 `update_api_key` 后调 `pending_writer.set_api_key`）。记录/分片/followup 侧车的文件名 stem 由**单一事实来源** `build_record_basename(record)` 统一生成，格式 `{YYYY-MM-DD_HH-mm-ss}_{symbol}_{timeframe}`（`strftime("%Y-%m-%d_%H-%M-%S")`，`%M` 为分钟；`symbol`/`timeframe` 经 `sanitize_filename_component` 过滤）。`orchestrator/free_chat.py` 的 `_derive_record_id` 必须委托本函数（call-time 导入），保证 followup `.followups.jsonl` 侧车与记录同名。
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
- **`pa_agent/security/`**：本地安全。
  - `secret_store.py`：API Key **至静态加密**（encryption at rest）。`encrypt_secret`/`decrypt_secret`/`is_encryption_available`/`looks_encrypted`。Windows 经 DPAPI（`ctypes` 直调 `crypt32` 的 `CryptProtectData`/`CryptUnprotectData`）加密为自描述令牌 `dpapi:v1:<base64>`，绑定当前 Windows 账户；非 Windows/DPAPI 不可用时 `encrypt_secret` 返回 `None`，`config/settings.py` 回退明文至静态。仅改磁盘表示——内存态 `provider.api_key` 恒为明文，`save_settings`/`load_settings` 分别在落盘/加载时调 `_encrypt_provider_key_for_disk`/`_decrypt_provider_key_in_place`。与运行时脱敏（`util/`）正交。

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
- CI（`.github/workflows/ci.yml`）目前在 Windows + Python 3.11 下执行安装/import 验证，并运行一组形成中 K 线/数据源、刷新循环 warmup、刷新策略 helper、K-line 复权偏好 helper、A 股涨跌停 helper、East Money quote page URL helper、East Money field enum helper、East Money quote API constants、East Money low-level client helpers、bar geometry primitives、trace node result helpers、signal context helpers、token counter helper、retry policy helper、validation message formatter、strategy filename registry、business-rule validators、schema structural validator、experience library renderer、QClaw relay helper、A 股/Tushare 无网络数据源、East Money quote 解析与 Baostock fallback helper、TradingView socket/error/connectivity/symbol lookup、market defaults、MT5 symbol availability、QClaw/Cursor route、CursorSdkClient bridge patch 合同、property invariants、non-live integration / non-e2e gate、provider override by model、KV prefix cache provider 判定、PushPlus mock 通知、API key configured helper、时间戳转换、timefmt epoch ms helper、CancelToken/OrchestratorEvent 基础线程工具、KlineBar 归一化、收盘等待/快照 warmup、ATR true range、K 线方向/几何特征、price tick/breakout entry 归一化、order opportunity alert helper、market features、Stage 1 支撑/阻力刷新、Stage 1 pattern routing、Stage 1/Stage 2 normalizer、Stage 1 策略文件别名、decision stance、decision panel UI 合同、decision tree helpers、decision continuity、PreflightDataGate / decision node judges property tests、支撑/阻力图表线与 overlay 价格精度、chart decision continuity overlay、chart fit view、chart skip-redraw、chart no-lines when not trading、DebugWidget key masking、token indicator thresholds、free chat reasoning resend、DeepSeekClient provider 参数合同、trade metrics / trade metrics validation、限价单 K1 新鲜度、cycle 枚举、响应提取、trace semantic/normalize checks、coherence validators、JSON repair/validator、lenient validation auto-fixes、MiMo 兼容、prompt txt 文件清单/prompt assembler、AI client factory 路由、SessionTokenLedger、provider quota/402 检测、validation retry/retry policy、分析历史增量定位、demo record/replay、§11 路由、决策编排、provider fallback、安全加密、settings round-trip 与 PendingWriter 脱敏/文件名安全相关的目标测试；目标 pytest 会通过 `pytest-cov` 输出 `pa_agent` 覆盖率报告但暂不设阈值，并额外运行 `pytest -m "not e2e and not live"` 作为非 live 非 e2e 回归门禁。Ruff 门禁覆盖应用入口与包入口文件组、notify 包入口、forming-bar/data-source、收盘等待/快照 warmup 测试、数据源工厂、A 股共享工具、AkShare/Tushare source、East Money client/source/Baostock fallback/quote API 常量/解析、数据层小文件组、刷新循环、A 股涨跌停辅助、TradingView source/connectivity、`tv_symbol_lookup`、`market_defaults`、`datetime_ts`、`kline_adjust`、`kline_features`、AI 基础叶子模块、AI schema/routing 辅助文件、AI token/signal 辅助文件、AI validation messages、AI experience renderer、AI business rules、AI decision node compatibility facade、QClaw relay 脚本、配置路径常量、验证重试编排、util 包入口/EventBus/日志/崩溃诊断、`structure_levels`、`chart_decision_overlay`、`ai_sidebar`、`stage2_payload`、`validation_debug_dialog`、util 小工具组、`trade_metrics`、`ai/prompts`、`cycle_enums`、`response_extract`、`mimo_compat`、`client_factory`、`session_ledger`、`cursor_sdk_client`、`provider_errors`、`retry_policy`、`records`、`demo`、`ProviderSyncService`、`security`、`indicators`、`gui/theme`、测试包入口与子包入口、目标测试文件、`tests/property`、`tests/integration`、`tests/e2e` 及 `tests/fixtures`。尚未启用 live/e2e、全仓 Ruff、Black 或覆盖率阈值门禁。
- 提交前建议至少运行与改动相关的目标测试；较大改动应继续补跑 `pytest -m "not e2e"`。
- 第一百三十七轮 L7 补充：focused Ruff 新增 `pa_agent/gui/prediction_format.py`，覆盖未来走势预期面板共享显示 helper；本轮不修改 prediction probability 格式化、dominant direction 判定或任何用户可见显示文本。
- 第一百三十八轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/status_bar.py`，仅清理 status bar widget 的 docstring 标点；本轮不修改消息显示、进度条、颜色切换、TPS 显示或样式逻辑。
- 第一百三十九轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/model_selector.py`，覆盖模型选择下拉 widget；本轮不修改模型分组、下拉定位、选中态刷新、信号发射、按钮文案或样式逻辑。
- 第一百四十轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/flow_bar.py`，仅按 Ruff/isort 拆分 `PyQt6.QtWidgets` import；本轮不修改 FlowBar 步骤名称、默认 caption、状态颜色或更新/reset 行为。
- 第一百四十一轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/toast.py`，仅按 Ruff/isort 调整 `PyQt6.QtCore` import 顺序；本轮不修改 toast 消息显示、自动关闭、布局定位、尺寸计算或样式逻辑。
- 第一百四十二轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/overlay_lines.py`，仅移除 `PlotItem` quoted annotations 与 stale `BLE001` noqa；本轮不修改 entry/TP/SL 线绘制、label 精确价格存储、view range 更新连接或异常日志兜底。
- 第一百四十三轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/summary_strip.py`，仅移除 `resizeEvent()` 上 stale `N802` noqa；本轮不修改 summary card 标题、默认值、metric 更新、reset 或响应式 relayout 行为。
- 第一百四十四轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/candle_item.py`，仅移除 `KlineBar` quoted annotations；本轮不修改蜡烛绘制、forming bar 样式、body/wick 几何计算、颜色、bounding rect 或增量 `update_bar()` 行为。
- 第一百四十五轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/seq_label_item.py`，仅把 forming/non-forming 两侧相同的序号文本条件表达式简化为单一赋值；本轮不修改序号文本格式、forming 颜色、默认颜色、字体、anchor 或位置。
- 第一百四十六轮 L7 补充：focused Ruff 新增 `pa_agent/gui/widgets/__init__.py`，覆盖 widgets 包入口导出；本轮不修改包导出、公开类名、widget 初始化路径或任何运行代码。
- 第一百四十七轮 L7 补充：focused Ruff 新增 `pa_agent/gui/__init__.py`，仅按 Ruff/isort 排序 GUI 包入口 import 与 `__all__`；本轮不修改 GUI 包公开类集合、导出名称、初始化路径或任何运行代码。
- 第一百四十八轮 L7 补充：focused Ruff 新增 `pa_agent/gui/snapshot_worker.py`，仅移除 stale `BLE001` noqa；本轮不修改后台 snapshot 拉取、`bars_ready`/`failed` signal、异常捕获范围、warning 日志或失败消息传播。
- 第一百四十九轮 L7 补充：focused Ruff 新增 `pa_agent/gui/stage2_payload.py`，覆盖 Stage 2 UI payload 合并 helper；本轮不修改 `decision` 合并、`next_bar_prediction`/`next_cycle_prediction` 透传、deepcopy 归一化或 `skip_next_bar` 行为。
- 第一百五十轮 L7 补充：focused Ruff 新增 `pa_agent/gui/validation_debug_dialog.py`，覆盖验证失败调试弹窗 helper；本轮不修改弹窗标题/摘要/正文传入、复制到剪贴板、关闭按钮、尺寸或 modal `exec()` 行为。
- 第一百五十一轮 L7 补充：focused Ruff 新增 `pa_agent/gui/ai_sidebar.py`，仅按 Ruff/isort 排序 sidebar 导入；本轮不修改 tab 顺序、tab 标题、widget 初始化、settings 绑定或 tab change refit 行为。
- 第一百五十二轮 L7 补充：focused Ruff 新增 `pa_agent/ai/decision_nodes.py`，覆盖决策节点兼容导出 facade；本轮不修改 `__all__` 公开导出、judge/helper re-export、threshold 常量引用或任何底层判定逻辑。
- 第一百五十三轮 L7 补充：focused Ruff 新增 `pa_agent/notify/__init__.py`，仅覆盖通知包入口注释；本轮不修改 Feishu/PushPlus 通知实现、webhook 签名、消息文案、图片上传或发送重试逻辑。
- 第一百五十四轮 L7 补充：focused Ruff 新增 `pa_agent/ai/experience_renderer.py`，仅对经验库中文 caveat 行添加窄范围 `# noqa: RUF001`；本轮不修改经验库 block header、中文提示、markdown fence、JSON 序列化、截断省略号或 PromptAssembler 绑定路径。
- 第一百五十五轮 L7 补充：focused Ruff 新增 `tests/__init__.py` 与 `tests/unit/__init__.py`，覆盖测试包入口；本轮不修改测试选择、fixture、断言、marker 或任何运行代码。
- 第一百五十六轮 L7 补充：focused Ruff 新增 `tests/integration/__init__.py`、`tests/property/__init__.py`、`tests/fixtures/__init__.py` 与 `tests/e2e/__init__.py`，覆盖测试子包入口；本轮不修改测试选择、fixture、断言、marker、live/e2e 默认执行策略或任何运行代码。
- 第一百五十七轮 L7 补充：新增 `tests/unit/test_timefmt.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `pa_agent/util/timefmt.py:now_local_ms()` 的 epoch 毫秒转换；本轮不修改真实时间读取逻辑、时区语义或 util/timefmt 运行代码。
- 第一百五十八轮 L7 补充：新增 `tests/unit/test_threading_utils.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `CancelToken` 的 set/clear/wait 语义和 `OrchestratorEvent` 成员顺序；本轮不修改线程工具实现、事件枚举值或编排器运行代码。
- 第一百五十九轮 L7 补充：新增 `tests/unit/test_refresh_policy.py` 并纳入目标 pytest 与 focused Ruff，覆盖 HTTP 轮询源刷新间隔 clamp、日线刷新下限、snapshot cache TTL 与 zombie join timeout；本轮不修改刷新策略常量、数据源判定或刷新循环运行代码。
- 第一百六十轮 L7 补充：新增 `tests/unit/test_kline_adjust.py` 并纳入目标 pytest 与 focused Ruff，覆盖 K-line 复权偏好设置、非法值回退、settings 读取与 `None` 默认重置；本轮不修改复权模式取值、锁保护或数据源调用逻辑。
- 第一百六十一轮 L7 补充：新增 `tests/unit/test_ashare_limits.py` 并纳入目标 pytest 与 focused Ruff，覆盖 A 股代码归一化、涨跌停比例/价格、API pct_chg 优先级、一字涨跌停标签与跨交易日标签；本轮不修改涨跌停判定、缓存或交易日日期逻辑。
- 第一百六十二轮 L7 补充：新增 `tests/unit/test_eastmoney_urls.py` 并纳入目标 pytest 与 focused Ruff，覆盖 East Money quote page URL 的沪深/指数/空 symbol fallback、timeframe klt 映射、未知周期默认日线与 simple URL；本轮不修改 URL 构造、A 股 symbol 归一化或指数前缀规则。
- 第一百六十三轮 L7 补充：新增 `tests/unit/test_eastmoney_field_enums.py` 并纳入目标 pytest 与 focused Ruff，覆盖 East Money field enum 的 fields 参数去重/顺序、未知 enum 核心字段兜底、L2 深度字段与 `FIELDS_TEN_DEPTH` 合同；本轮不修改逆向 enum 映射、十档字段或 quote API 常量。
- 第一百六十四轮 L7 补充：新增 `tests/unit/test_eastmoney_quote_api.py` 并纳入目标 pytest 与 focused Ruff，覆盖 East Money quote API hosts/path、五档/十档盘口字段顺序、逐笔字段和 `TEN_DEPTH_FIELDS` 绑定；本轮不修改 HTTP/SSE 常量、盘口解析或采集逻辑。
- 第一百六十五轮 L7 补充：新增 `tests/unit/test_bar_geometry.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `_count_trend_bars()`、`_mean_overlap_ratio()` 与 `_find_swings()` 的趋势棒阈值、重叠率和 2-bar pivot 行为；本轮不修改几何阈值、判定逻辑或调用站点。
- 第一百六十六轮 L7 补充：新增 `tests/unit/test_trace_nodes.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `_coerce_dict()`、`_coerce_trace_list()`、`NodeFill` frozen 语义、`build_program_trace_node()` 键/可选元数据和 `node_label` 异常回退；本轮不修改 trace 构建、决策树 label 解析或任何运行代码。
- 第一百六十七轮 L7 补充：新增 `tests/unit/test_signal_context.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `_get_signal_seq()` 的 signal bar 序号解析/回退、`has_background_limit_path()` 的 §9.0P 检测和 `is_planned_limit_order()` 的背景限价、pending entry 与 weak structural pattern 分支；本轮不修改信号棒定位、计划型限价判定或 Stage 2 调用路径。
- 第一百六十八轮 L7 补充：新增 `tests/unit/test_token_counter.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `estimate_tokens()` 的 fake `tiktoken` 编码路径、字符串字段计数、模型 hint 透传、char/4 fallback 和最小返回 1；本轮不修改 token 估算公式、日志或真实 `tiktoken` 调用路径。
- 第一百六十九轮 L7 补充：新增 `tests/unit/test_retry_policy.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `max_retries_for_category()`、`should_retry()` attempt 上限/语义拒绝前缀、`detect_cheat()` 的 Stage 2 diagnosis summary 不可变保护与反馈豁免，以及 `extract_feedback_targets()` 字段映射；本轮不修改重试策略、作弊检测或验证重试编排。
- 第一百七十轮 L7 补充：新增 `tests/unit/test_validation_messages.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `format_validation_errors()` 的缺失字段前置、invalid 条目截断/额外计数、空输入，以及 `_label_one()` 的 prefix/embedded-prefix 匹配与 fallback；本轮不修改验证错误中文标签、摘要拼接或 retry feedback 调用路径。
- 第一百七十一轮 L7 补充：新增 `tests/unit/test_strategy_files.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `strategy_files.py` 注册表唯一性/`.txt` 后缀、router `_ALL_VALID_FILES` 从注册表派生，以及 prompt assembler 阶段文件列表绑定；本轮不修改策略文件名、路由逻辑、prompt 组装顺序或生产代码。
- 第一百七十二轮 L7 补充：新增 `tests/unit/test_business_rules.py` 并纳入目标 pytest 与 focused Ruff，直接覆盖 `business_rules.py` 的不下单铁律、突破单 basis/价格极值校验、K 序号/frame/reason helper 和 weak signal reasoning token 分支；本轮不修改业务规则、JsonValidator 重绑定、trade metrics 调用或生产代码。
- 第一百七十三轮 L7 补充：新增 `tests/unit/test_schema_validator.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `SchemaValidationResult.has_errors`、`collect_schema_errors()` 的 valid 空结果、required missing 分类和 enum allowed-values 分类；本轮不修改 JSON Schema 结构校验、JsonValidator category 组装或业务规则链。
- 第一百七十四轮 L7 补充：新增 `tests/unit/test_experience_renderer.py` 并纳入目标 pytest 与 focused Ruff，覆盖 `render_experience()` 的块头/caveat、dict JSON block、`content` 属性序列化和长条目截断省略号；本轮不修改经验库渲染、PromptAssembler staticmethod 重绑定或 prompt 文案。
- 第一百七十五轮 L7 补充：新增 `tests/unit/test_qclaw_relay.py` 并纳入目标 pytest 与 focused Ruff，覆盖 QClaw relay `_find_free_port()` 跳过占用端口、`/health` 服务元数据响应和 `/v1/models` 模型列表响应；本轮不修改 relay 转发、上游调用、自测线程或真实 QClaw 集成路径。
- 第一百七十六轮 L7 补充：新增 `tests/unit/test_eastmoney_client.py` 并纳入目标 pytest 与 focused Ruff，覆盖 East Money low-level client 的 market/secid helper、K 线字符串解析、clist 行解析和日线参数生成；本轮不修改 HTTP 请求、CDN host retry、真实 East Money 网络调用或数据源集成路径。

***

## 7. 安全配置与密钥处理

### 7.1 实际行为（请务必注意）

- `config/settings.json` 中的 API Key 采用**至静态加密（encryption at rest）**，实现见 `pa_agent/security/secret_store.py`：
  - **Windows**：保存时经 **DPAPI**（`CryptProtectData`/`CryptUnprotectData`，`ctypes` 直调 `crypt32`）把明文加密为自描述令牌 `dpapi:v1:<base64(blob)>` 写入 `provider.api_key_encrypted`，磁盘上的 `provider.api_key` 置空；加载时 `load_settings` 解密回内存态 `provider.api_key` 并清空内存中的 `api_key_encrypted`。DPAPI 密文**绑定当前 Windows 用户账户**，他机/他账户无法解密。
  - **非 Windows / DPAPI 不可用**：`encrypt_secret` 返回 `None`，优雅降级为**明文至静态**（`provider.api_key` 明文写盘），行为与加密引入前一致。
  - **向后兼容**：磁盘上的**旧明文 key** 照常加载，并在**下次保存时自动加密**（无缝迁移）。
  - **加密仅改磁盘表示**：内存态 `provider.api_key` 始终为明文，所有调用方（客户端、脱敏、降级同步）零改动，仍统一读明文。
- 加密与脱敏是两个正交层：**至静态加密**（secret_store，只改磁盘密文）vs **运行时脱敏**（下方三层，处理内存明文进入日志/记录的路径）。
- `pa_agent/security/` 包现含 `secret_store.py`（本地密钥加密），不再是空占位。

因此，项目的密钥安全依赖以下多层：

1. **至静态加密**：Windows 下 `provider.api_key` 经 DPAPI 加密存盘（见上）；非 Windows 回退明文。
2. **Git 忽略**：`config/settings.json` 等敏感文件已被 `.gitignore` 排除；
3. **pre-commit 拦截**：`.githooks/pre-commit` 阻止提交 `settings.json`、`.env`、日志、分析记录，并扫描 diff 中的 `api_key` / `api_key_encrypted` / `sk-...` 模式（DPAPI 令牌命中既有 `api_key_encrypted` 大 base64 规则）；
4. **运行时脱敏**（内存明文进入外部载体前替换）：
   - `pa_agent/util/mask_secret.py` 提供掩码函数（保留最后 4 位，其余替换为 `*`）；
   - `pa_agent/util/logging.py` 的 `MaskingFormatter` 在日志输出前替换明文 API Key；
   - `pa_agent/records/pending_writer.py` 在序列化记录前递归扫描并替换明文 API Key；
   - 多处测试（`test_secret_store.py`、`test_settings_round_trip.py`、`test_pending_writer_no_plaintext_key.py` 等）确保加密与脱敏有效。

### 7.2 开发者必须遵守的安全规范

- **绝不**将 `config/settings.json`、`config/exception_state.json`、`.env`、密钥文件加入 Git。
- **绝不**在测试、日志、错误信息中硬编码真实 API Key。
- 修改涉及密钥读取/保存的代码时，确保：
  - 保存到文件前仍经过脱敏或保持在 gitignored 文件中；
  - 日志和持久化记录中不出现明文 key；
  - **密钥落盘统一走 `save_settings`**（内部对 `provider.api_key` 施加至静态加密），不要绕过它直接写 `settings.json`；
  - 如需新增密钥字段，同步更新 `.gitignore` 与 `.githooks/pre-commit`，并考虑纳入 `secret_store` 的至静态加密。
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
- CI（`.github/workflows/ci.yml`）已开始执行安装/import 验证、目标测试、目标覆盖率报告、非 live 非 e2e 回归与聚焦 Ruff 检查；目标测试现覆盖 forming-bar/data-source、刷新循环 warmup、刷新策略 helper、K-line 复权偏好 helper、A 股涨跌停 helper、East Money quote page URL helper、East Money field enum helper、East Money quote API constants、bar geometry primitives、A 股/Tushare 无网络数据源、East Money quote 解析与 Baostock fallback helper、TradingView socket/error/connectivity/symbol lookup、market defaults、MT5 symbol availability、QClaw/Cursor route、CursorSdkClient bridge patch 合同、property invariants、non-live integration / non-e2e gate、provider override by model、KV prefix cache provider 判定、PushPlus mock 通知、API key configured helper、时间戳转换、KlineBar 归一化、收盘等待/快照 warmup、ATR true range、K 线方向/几何特征、price tick/breakout entry 归一化、order opportunity alert helper、market features、Stage 1 支撑/阻力刷新、Stage 1 pattern routing、Stage 1/Stage 2 normalizer、Stage 1 策略文件别名、decision stance、decision panel UI 合同、decision tree helpers、decision continuity、PreflightDataGate / decision node judges property tests、支撑/阻力图表线与 overlay 价格精度、chart decision continuity overlay、chart fit view、chart skip-redraw、chart no-lines when not trading、DebugWidget key masking、token indicator thresholds、free chat reasoning resend、DeepSeekClient provider 参数合同、trade metrics / trade metrics validation、限价单 K1 新鲜度、cycle 枚举、响应提取、trace semantic/normalize checks、coherence validators、JSON repair/validator、lenient validation auto-fixes、MiMo 兼容、prompt txt 文件清单/prompt assembler、AI client factory 路由、SessionTokenLedger、provider quota/402 检测、validation retry/retry policy、分析历史增量定位、demo record/replay、§11 路由、决策编排、provider fallback、安全加密、settings round-trip 与 PendingWriter 脱敏/文件名安全，Ruff 门禁同步覆盖对应测试文件、`tests/property`、`tests/integration`、`tests/e2e`、`tests/fixtures`、应用入口与包入口文件组、`indicators`、`gui/theme`、`records`、`demo`、util 小工具组、util 包入口/EventBus/日志/崩溃诊断、数据源工厂、A 股共享工具、AkShare/Tushare source、East Money client/source/Baostock fallback/quote API 常量/解析、数据层小文件组、收盘等待/快照 warmup 测试、刷新循环、A 股涨跌停辅助、TradingView source/connectivity、`tv_symbol_lookup`、`market_defaults`、`datetime_ts`、`kline_adjust`、`kline_features`、`structure_levels`、`chart_decision_overlay`、`cycle_enums`、`response_extract`、`mimo_compat`、`client_factory`、`session_ledger`、`cursor_sdk_client`、`provider_errors`、`retry_policy`、`ProviderSyncService` 与 `security`，live/e2e、Black 与覆盖率阈值仍属于 L7 后续增强。
- `tools/` 目录包含大量一次性诊断脚本（网关探测、stage2 JSON 调试、MT5 时钟偏移检测等），不属于正式发布流程。

***

## 10. 给 AI 代理的实用提示

1. **先读配置再改代码**：很多行为由 `config/settings.json` 与 `pa_agent/config/settings.py` 中的 Pydantic 模型控制。新增配置字段时，同步更新 example 文件、GUI 设置对话框、相关测试。
2. **Prompt 文本在** **`prompt_engineering/`**：策略路由、阶段一/阶段二的 prompt 片段多为中文 `.txt` 文件。修改这些文件可能改变模型输出格式，需要同步更新 `tests/` 中的 JSON fixture 与校验用例。
3. **JSON schema 在** **`pa_agent/ai/prompts/schemas.py`**：阶段一/阶段二的输出结构严格受 schema 约束，改动需同步更新 `json_validator.py` 与 normalizer。
4. **MainWindow 是巨型文件**：`pa_agent/gui/main_window.py` 接近 200KB、4000+ 行。做小改动时优先定位到具体方法；做大重构时建议与维护者沟通。
5. **API Key 至静态加密，但内存态是明文**：磁盘上（Windows）经 DPAPI 加密为 `dpapi:v1:` 令牌存于 `api_key_encrypted`（见 §7.1、`security/secret_store.py`），非 Windows 回退明文；但**内存态 `provider.api_key` 始终为明文**，所有读取方零改动。任何涉及密钥持久化的新功能都要统一走 `save_settings`（自动加密），任何日志/记录落盘仍须经运行时脱敏——两层正交，不可混淆。
6. **优先用测试验证**：本项目测试覆盖较全，改动后请运行相关分层测试；涉及 LLM 输出解析的改动建议同时跑 `unit` 与 `integration`。
7. **保持中文用户界面**：新增用户可见字符串、日志、提示信息时，默认使用简体中文，与项目现有风格保持一致。
8. **每次迭代必须更新变更日志**：任何代码更新/修复/优化完成后，都要在 [`docs/CHANGELOG.md`](./docs/CHANGELOG.md) 追加或更新对应条目（问题/动机 → 修复/改动 → 涉及文件 → 验证方式），不得只改代码而不记录。
9. **新增文件/字段时注意更新本文件**：如果你新增了模块、数据源、AI 提供商、安全机制、构建流程等，请同步更新本 `AGENTS.md` 中的对应章节，保持文档与代码一致。
10. **热路径注意性能，但不牺牲语义**：`data/snapshot.py`（RefreshLoop tick）、`ai/kline_features.py`（逐棒特征）、`records/analysis_history.py`（增量分析找上次记录）、`ai/deepseek_client.py`（每次 API 调用）等属于高频路径，改动时避免重复计算、无谓遍历与无条件构造大字符串（如把 prompt DEBUG 日志用 `logger.isEnabledFor(logging.DEBUG)` 守卫）。任何性能优化都必须保持输出与原实现一致，替换算法时应给出等价性验证；性能热点清单见 `docs/backend_review_report.md` §8。
11. **进程级缓存/全局状态需线程安全**：后台 QThread（刷新、快照、分析、聊天）会并发访问模块级缓存。`ai/prompt_assembler.py:_SYSTEM_PROMPT_CACHE`、`records/analysis_history.py:_LATEST_RECORD_CACHE`、`data/eastmoney_extended.py:_COMPACT_CTX_CACHE`、`util/logging.py`（`_configured`/`_active_formatters`）、`data/kline_adjust.py:_current`、`ai/cursor_sdk_client.py` 的 patch 标志均已加锁保护。新增此类全局可变状态时，应配套加锁（耗时构建/IO 放锁外，用双检锁），保持输出与语义不变。

***

*本文件基于项目当前实际代码生成。若后续引入本地加密、新增数据源/提供商、调整构建或测试流程，请同步更新本文件。*
