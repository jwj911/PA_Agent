# 更新日志（CHANGELOG）

本文件记录 PA Agent 的迭代与修复历史，供维护者与 AI 编码代理追溯每一次变更。

## 维护规范（重要）

- **每次代码更新/迭代都必须在本文件追加或更新对应条目**，不得只改代码而不记录。
- 新的一轮迭代在文件顶部“未发布 / Unreleased”或对应日期小节下新增条目；发布版本时把 Unreleased 内容归档到带版本号的小节。
- 每条记录尽量包含：**问题/动机** → **修复/改动** → **涉及文件** → **验证方式**。
- 条目按类别归类：`崩溃修复` / `安全加固` / `性能优化` / `代码清理` / `功能` / `文档`。
- 用户可见文案、日志、提示使用简体中文；代码标识符使用英文，与项目既有风格保持一致。
- 遵守安全边界：不得记录任何真实 API Key、明文密钥或敏感配置内容。

---

## [Unreleased] — 2026-07-14（第四轮：异常可观测性）

本轮聚焦排障能力，落实后端审查报告（`docs/backend_review_report.md`）路线图中的 **R6**：把散落在基础设施、数据源、GUI 与决策逻辑里、被裸 `except Exception:` 直接 `pass`/`return` 静默吞掉的失败，统一补上 `logger.debug(..., exc_info=True)` 诊断日志。**原则：只加日志、不改控制流**——保留原有兜底行为（返回默认值 / 跳过 / 继续），仅让失败在需要排障时可见（DEBUG 级，不污染正常运行输出）。

### 代码清理 / 可观测性

- **裸 `except Exception` 静默吞异常，出问题无从排查（R6）**：审查报告 §4.1.5 点名多处基础设施/初始化/信号连接/IO 失败被无声吞掉（如 MT5 订阅、TradingView socket 清理、cursor-sdk patch 初始化、WorkBuddy DPAPI 解密、分析记录读取等），失败时既无日志也无异常，线上排障只能靠猜。为 34 处此类站点补上带堆栈的 DEBUG 日志：
  - **数据源**：`mt5.py`（订阅/取数前 `symbol_select` 失败 ×2）、`tradingview.py`（socket 引用重置、探测回调失败 ×2）、`eastmoney_baostock.py`（force reset 时 socket close 失败）。
  - **AI 网关/客户端**：`cursor_sdk_client.py`（4 处 patch import guard 失败）、`workbuddy_connector.py`（token 文件读取、base64 解码、token 候选解析 ×3）、`qclaw_relay_manager.py`（relay 健康探测失败）。
  - **AI 逻辑**：`decision_nodes.py`（node_label 查询、signal bar seq 解析、K 线几何特征计算 ×3）、`pattern_routing.py`（barbwire 特征计算）、`retry_feedback.py`（K 线几何摘要构建）。
  - **记录**：`analysis_history.py`（损坏/不兼容记录读取）、`pending_writer.py`（save_full/save_partial 后缓存失效 ×2）。
  - **GUI**：`main_window.py`（信号连接、设置读写、TradingView socket 关闭、save_partial、支撑阻力渲染、增量分析探测等 10 处）、`chart_widget.py`（支撑阻力标签定位）、`widgets/overlay_lines.py`（信号断连、viewRange 读取 ×2）。
  - 其中 5 个此前无模块级 logger 的文件（`analysis_history.py`、`pattern_routing.py`、`retry_feedback.py`、`chart_widget.py`、`overlay_lines.py`）补充了 `import logging` 与 `logger = logging.getLogger(__name__)`。
  - **明确排除**（保持原样，加日志纯属噪音）：热循环里的窄类型数值兜底（`except (TypeError, ValueError)`）、Qt 信号断连 idiom（`except (TypeError, RuntimeError)`）、可选依赖 `ImportError` 探测、以及已返回错误文本的连通性探测。

### 验证

- `py_compile` 全部 14 个改动文件通过。
- `ruff check` 对比基线：改动前 800 条既有告警（全为全仓既有的 RUF001 中文标点/UP037/SIM 等噪音），改动后降至 791 条（消除 9 条原 `except: pass` 的 SIM105 候选），**未新增任何告警**。
- 未实机运行（环境无 PyQt6）；改动为纯日志增补、不改控制流，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归。

---

## [Unreleased] — 2026-07-14（第三轮：安全一致性）

本轮聚焦安全边界的"文档—代码一致性"与文件名安全，落实后端审查报告（`docs/backend_review_report.md`）路线图中的 R7、M10。

### 安全加固

- **记录/交易日志文件名未过滤，存在路径遍历风险（M10）**：`pending_writer.py` 与 `trade_logger.py` 直接把 `symbol`/`timeframe` 拼进文件名，`trade_logger` 仅替换 `/`、`\`，未处理 `..`、`:`、Windows 保留名（CON/NUL/COM1…）等；恶意或异常的品种名可能导致写入越界或非法文件名。新增独立无依赖工具 `pa_agent/util/safe_filename.py`（`sanitize_filename_component`）：替换非法字符/路径分隔符为 `-`、剥离首尾 `. -`（阻断 `..` 遍历）、为 Windows 保留名加 `_` 前缀、空值回退 `fallback`；并在两处文件名构造点应用。
  - 涉及：`pa_agent/util/safe_filename.py`（新增）、`pa_agent/records/pending_writer.py`（`_build_basename`）、`pa_agent/records/trade_logger.py`（CSV/PNG 路径）。

### 文档

- **多处文档虚假宣称"API Key 加密存储"，与实际明文存储矛盾（R7）**：`README.md`、`config/README.md`、`PA_Agent使用文档.md` 声称 API Key "本地加密存储"/"Windows DPAPI 加密"/"加密写入 `api_key_encrypted`"，甚至引用了并不存在的 `pa_agent.security.secret_store.SecretStore` 类（`pa_agent/security/` 实为空占位）。这与 `AGENTS.md` §7.1 描述的明文存储事实矛盾，会误导用户。统一改为如实说明：**明文**存储于被 `.gitignore` 忽略的 `settings.json`，安全依赖 `.gitignore` 隔离 + `.githooks/pre-commit` 拦截 + 日志/记录运行时脱敏三重防护；`api_key_encrypted` 标注为未实现的历史遗留字段。
  - 涉及：`README.md`（特性列表）、`config/README.md`（首次使用步骤、字段表 `api_key`/`api_key_encrypted`）、`PA_Agent使用文档.md`（首次运行第 4 步、设置表 API Key 行、§19 安全与密钥管理）。

### 验证

- `py_compile` 通过（`safe_filename.py`、`pending_writer.py`、`trade_logger.py`）。
- 用 importlib 隔离测试 `sanitize_filename_component` 边界：`../../etc/passwd`→`etc-passwd`、`XAU/USD`→`XAU-USD`、`CON`→`_CON`、`nul.csv`→`_nul.csv`、`..`→`unknown`（fallback）、`15m`→`15m`（正常值不变）。
- 全仓 grep 复核：除 `AGENTS.md`/审查报告中如实记录的"未实现加密"说明外，已无残留的"加密存储"误导性文案。
- 未实机运行（环境无 PyQt6）；建议在项目 venv 运行 `pytest -m "not e2e" -q`，重点回归 `test_pending_writer_*` 与交易日志相关用例。

---

## [Unreleased] — 2026-07-13（第二轮：并发与 UI 响应性）

继续对数据层与 GUI 主线程做审查，修复两处会导致界面卡顿 / 线程无法及时退出的真实缺陷。

### 崩溃 / 卡顿修复

- **「获取数据」按钮阻塞 GUI 线程 1.5 秒**：TradingView 连通性探测后用 `time.sleep(1.5)` 等待 WebSocket 断开，该调用运行在 GUI 线程上，导致界面冻结 1.5 秒。改为 `QTimer.singleShot(1500, ...)` 异步延迟重启刷新循环，并在等待期间显示「正在连接 TradingView，请稍候…」状态提示；将重启逻辑抽出为 `_restart_refresh_loop_fresh()`。
  - 涉及：`pa_agent/gui/main_window.py`（`_on_fetch_data_clicked`、新增 `_restart_refresh_loop_fresh`）。
- **RefreshLoop 退避 sleep 不响应取消，导致停止时最长阻塞 10 秒**：后台刷新线程在指数退避（最长 10s）与间隔等待期间使用 `time.sleep`，不检查取消令牌，`_stop_refresh_loop` 只能把线程标记为 zombie 稍后回收。新增 `_sleep_cancellable()`（按 0.1s 粒度轮询取消令牌）与 `_cancelled()` 辅助，替换所有 `time.sleep`，使线程在取消后 ~0.1s 内退出。
  - 涉及：`pa_agent/data/refresh_loop.py`（`run`、新增 `_cancelled`/`_sleep_cancellable`）。

### 验证

- `py_compile` 通过；`ruff --select F,B` 全部通过（改动文件仅剩全文件既有的 SIM105/UP037 风格噪音，非本次引入）。
- 未实机运行（环境无 PyQt6）；建议在项目 venv 运行 `pytest -m "not e2e" -q`，并手动验证：切换到 TradingView 数据源点击「获取数据」时界面不再冻结、频繁切换标的/时间框时刷新线程能及时停止。

---

## [Unreleased] — 2026-07-13

本轮基于 [`AGENTS.md`](../AGENTS.md) 对前端 GUI 与后端进行代码审查，修复崩溃类缺陷、加固安全、清理死代码并优化图表渲染。

### 崩溃修复

- **EventBus 磁盘错误静默 / 崩溃**：`disk_error` 通知链路存在死代码，磁盘/IO 异常无法上抛到界面。新增 `disk_error` 信号与 `emit_disk_error`，由主窗口状态栏捕获提示。
  - 涉及：`pa_agent/util/event_bus.py`、`pa_agent/gui/main_window.py`（`_on_disk_error`）、`pa_agent/records/pending_writer.py`（`_handle_disk_error`）。
- **主窗口关闭崩溃（QThread destroyed while running）**：`closeEvent` 未等待分析线程退出。改为调用 `_cancel_analysis_worker` 并带 `join_ms` 超时等待。
  - 涉及：`pa_agent/gui/main_window.py`（`closeEvent`）。
- **子面板关窗崩溃**：`AIStreamPanel`、`ConversationWidget` 等子 widget 不会自动触发 `closeEvent`，后台 worker 未清理。新增显式 `shutdown()`（断信号、停 worker、`deleteLater`），由主窗口关闭时调用。
  - 涉及：`pa_agent/gui/ai_stream_window.py`、`pa_agent/gui/conversation_widget.py`、`pa_agent/gui/main_window.py`（`closeEvent` 调用 `stream.shutdown()`）。

### 安全加固

- **API Key 默认明文显示**：所有 API Key 输入框改为 Password 隐藏模式。
  - 涉及：`pa_agent/gui/ai_model_settings_dialog.py`、`pa_agent/gui/settings_dialog.py`、`pa_agent/gui/general_settings_dialog.py`。
- **调试导出未脱敏**：调试面板 JSON 导出/校验统一经过 `_mask` 脱敏处理。
  - 涉及：`pa_agent/gui/debug_widget.py`。
- **保存设置无异常处理**：`save_settings` 增加 `try/except`，写盘失败不再静默或崩溃。
  - 涉及：设置相关对话框的保存逻辑。
- **PendingWriter Key 运行时同步**：在 AI 模型设置对话框保存后，调用 `pending_writer.set_api_key(key)` 同步最新 Key，保证记录脱敏基准与实际使用一致。
  - 涉及：`pa_agent/records/pending_writer.py`（`set_api_key`）、`pa_agent/gui/main_window.py`（`_open_ai_model_settings_dialog`）。

### 决策流可视化（decision_flow_viz.py）

- **全局动画相位互相干扰**：删除模块级 `_ANIM_PHASE`，改为 `_FlowScene` 实例属性 `anim_phase`，新增 `_item_anim_phase(item)` 辅助读取，避免多实例干扰。
- **全屏弹窗内存泄漏**：`_open_fullscreen` 的 `QDialog` 设置 `WA_DeleteOnClose`。
- **隐藏标签页仍重绘浪费资源**：新增 `hideEvent` 停止 fx 定时器与播放，`showEvent` 恢复 fx 定时器。
  - 涉及：`pa_agent/gui/decision_flow_viz.py`。

### 性能优化

- **图表增量渲染**：实时 tick 下原先每帧全量清空并重建所有蜡烛/标签/EMA。现新增“仅最新 forming bar 变化”快路径：当所有已收盘 bar、数量、seq 标签、已收盘段 EMA 均不变，只对最新一根蜡烛做原地 `update_bar` 并刷新 EMA 线；结构性变化（新增收盘 bar、数量变化、forming→closed、字号变更）仍走全量重建。
  - 涉及：`pa_agent/gui/widgets/candle_item.py`（新增 `update_bar`）、`pa_agent/gui/chart_widget.py`（`_render_frame` 快路径、`_try_forming_only_update`、`_forming_only_change`、`_rendered_frame`/`_needs_full_render` 状态、`reset` 复位、`set_seq_label_font_pt` 置全量重建标记）。

### 代码清理

- **清理真实死代码**：删除多处无副作用、计算后未被消费的死变量/被遮蔽的死导入（`pa_agent` 下 F841/F811 清零）。
  - 涉及：`pa_agent/ai/stage1_normalizer.py`、`pa_agent/app_context.py`、`pa_agent/data/eastmoney_source.py`、`pa_agent/ai/coherence_checks.py`、`pa_agent/ai/json_validator.py`、`pa_agent/data/market_defaults.py`、`pa_agent/records/trade_logger.py`、`pa_agent/gui/main_window.py`。
- **F401 未用导入清理**：`pa_agent` 目录（不含 tests）批量移除 34 处未用导入，`compileall` 全量通过；已核实被删名字未被其他模块 re-import。

### 说明

- 当前环境未安装 PyQt6 / hypothesis，GUI 与 property 测试无法本地运行；改动均以 `py_compile` / `compileall` 做语法级验证（BOM 安全）。
- **建议在装有 PyQt6 的项目 venv 中运行 `pytest -m "not e2e" -q` 做完整回归。**
- ruff `--statistics` 中约 3787 项为中文全角标点噪音（RUF001/002/003），属误报，为保留中文界面**不予处理**；本轮只精修 F401/F841/F811 等真实信号。
