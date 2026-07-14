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

## [Unreleased] — 2026-07-14（第九轮：类型现代化 R4）

本轮落实后端审查报告（`docs/backend_review_report.md`）路线图 §5.1 的 **R4**：清理散落在后端各处的旧式 `typing` 注解，统一到 Python 3.11+（PEP 585/604）风格。项目已在 `pyproject.toml` 声明 `target-version = "py311"`，却仍有 36 处 ruff 现代化告警——`Optional[X]`（UP045）、`typing.List`/`typing.Callable` 的过时导入（UP035）、`List[...]`（UP006）。**原则：只换注解写法、不改任何运行时行为与类型语义**——`Optional[X]` 与 `X | None` 完全等价，`list` 与 `typing.List` 同义，仅让代码风格与工具链目标版本一致、消除告警噪音。

### 代码清理

- **`Optional[X]` → `X | None`（UP045，32 处）**：覆盖 `records/schema.py`（8 处 Pydantic 字段）、`records/experience_reader.py`（4 处）、`records/pending_writer.py`（2 处）、`orchestrator/two_stage.py`（2 处）、`orchestrator/free_chat.py`（2 处）、`gui/ai_sidebar.py`（2 处）、`gui/ai_stream_window.py`（5 处）、`gui/conversation_widget.py`（7 处）。其中 8 个模块本就 `from __future__ import annotations`（注解为惰性字符串，零运行期成本）；顺带把这些文件里原本被引号包裹的前置声明（如 `Optional["Settings"]`）解引号为 `Settings | None`，一并消除 12 处 UP037 引号注解告警。
- **过时 `typing` 导入清理（UP035，3 处）**：`util/logging.py` 删除 `from typing import List`；`orchestrator/two_stage.py`、`orchestrator/free_chat.py` 把 `Callable` 从 `typing` 迁到 `collections.abc`（放入各自的 `if TYPE_CHECKING:` 块，因两文件均已启用延迟注解、`Callable` 仅用于注解）。
- **`List[...]` → `list[...]`（UP006，1 处）**：`util/logging.py` 的 `_active_formatters: list[MaskingFormatter]`（PEP 585 内置泛型；该文件已启用延迟注解，运行期不求值）。

### 明确不改（保持原样）

- **`schema.py` 未加 `from __future__ import annotations`**：Pydantic v2 需在类定义时**求值**字段注解以构建模型，惰性注解会干扰其 schema 生成，故此文件保留即时注解；`X | None` 在 Python ≥3.11 可直接运行期求值，无需 `__future__`。
- **`Any`、`Literal`、`TYPE_CHECKING` 等仍来自 `typing`**：这些并非过时符号（无 UP 告警），保持从 `typing` 导入。
- **其余既有告警**（RUF001 中文标点、E402、RUF100、I001、SIM 等）：属全仓既有噪音，不在 R4 范围内，未改动。

### 验证

- `py_compile` 通过（全部 9 个改动文件）。
- **运行时验证**：`schema.py` 为 Pydantic 即时求值风险点——`python -c` 实测 `ValidationError(category='a', raw_text='x').parse_position is None`、`FollowupTurn(..., ai_reasoning=None)` 构造成功，证明 `X | None` 字段在运行期正确建模；其余 8 个文件因 `from __future__ import annotations` 注解不求值，仅需语法正确。含 PyQt6 依赖的模块（经 `util/__init__`→`event_bus`）与既往各轮一致无法本机导入，非本次改动引入。
- `ruff check` 对比基线（9 个文件）：改动前 **211** 条 → 改动后 **163** 条，减少的 48 条全部为目标类别——UP045 32→0、UP037 31→19（解引号）、UP035 3→0、UP006 1→0；其余类别（RUF001:110、E402:11、RUF100:11、I001:5、SIM108:2、UP017:2、F821:1、RUF002:1、SIM114:1）与改动前**逐项一致，零新增**。
- `git diff` 密钥扫描（`sk-...` / `api_key=...`）0 命中。
- 改动为纯注解现代化、类型语义不变，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归记录序列化与两阶段编排相关用例（`test_schema_*`、`test_pending_writer_*`、`test_experience_reader_*`）。

---

## [Unreleased] — 2026-07-14（第八轮：类型完善 R5）

本轮落实后端审查报告（`docs/backend_review_report.md`）§2.1 与路线图 §5.1 的 **R5**：给依赖注入容器 `AppContext` 的字段补全真实类型。此前 10 个字段（`settings`/`event_bus`/`data_source`/`client`/`assembler`/`router`/`validator`/`pending_writer`/`exp_reader`/`ledger`）全部标注为 `Any`，仅靠行尾注释（如 `# DeepSeekClient`）说明实际类型，静态类型检查与 IDE 补全完全失效。**原则：只补类型、不改运行时行为**——`AppContext` 仍是 `@dataclass(slots=True)`，字段默认值、构造签名、`bootstrap()` 装配逻辑一律不变。

### 代码清理

- **`app_context.py:AppContext` 字段全为 `Any`（审查 §2.1）**：改用 `from __future__ import annotations` 已启用的**延迟注解**，在 `if TYPE_CHECKING:` 块内导入真实类型（`Settings`、`EventBus`、`DataSource`、`DeepSeekClient`/`CursorSdkClient`、`PromptAssembler`、`JsonValidator`、`PendingWriter`、`ExperienceReader`、`SessionTokenLedger`），把各字段标注为对应的 `T | None`（`router` 标注为 `Callable[[dict[str, Any]], list[str]] | None`，对应 `route_strategy_files`）。因注解在运行期为字符串、导入仅在类型检查期发生，**不引入任何运行时导入开销，也不会触发 `util/__init__`→PyQt6 的循环导入**。删除了原有的行尾类型注释（已由注解本身表达）。
  - 涉及：`pa_agent/app_context.py`（`TYPE_CHECKING` 导入块 + 10 个字段注解）。

### 明确不改（保持原样）

- **`bootstrap()` 内的 17+ 处运行时延迟导入**：属审查报告列出的「启动期副作用」中期项（M5 ProviderSyncService 抽取），本轮只做零风险的字段类型补全，不动装配流程。
- **`logger` 字段**：本就是具体类型 `logging.Logger`（带 `default_factory`），保持不变。

### 验证

- `py_compile pa_agent/app_context.py` 通过。
- **运行时导入验证**：`python -c "import pa_agent.app_context"` 成功（`TYPE_CHECKING` 块内导入不在运行期执行，规避了本机无 PyQt6 的限制）；`dataclasses.fields(AppContext)` 仍为 **11** 个字段，`AppContext()` 默认构造成功、`logger.name == "pa_agent"`，证明字段默认值与 slots 行为未变。
- `ruff check` 对比基线：改动前后同为 **4** 条既有告警（I001:2、RUF100:1、UP037:1，均为全仓既有噪音），新增的 `TYPE_CHECKING` 导入块排序合规，**零新增**。
- 改动为纯类型注解、运行期行为不变，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归启动装配相关用例。

---

## [Unreleased] — 2026-07-14（第七轮：代码去重 R2）

本轮落实后端审查报告（`docs/backend_review_report.md`）§4.3 与路线图 §5.1 的 **R2**：合并 `orchestrator/two_stage.py` 中两个高度重复的校验错误富化函数。`_enrich_stage1_validation_message` 与 `_enrich_stage2_validation_message` 逐行几乎一致（配额短路、`format_validation_errors` 明细、`_json_truncation_hint` 截断提示、content 空 / 仅思考区分支判断完全相同），仅**两处**中文提示串不同：思考截断成因（阶段一「思考占满输出额度…检查网关输出上限」vs 阶段二「思考在输出阶段二 JSON 前被截断…检查 Packy 分组限额」）与「阶段一/阶段二」标签。**原则：只去重、不改任何输出**——合并后两个 stage 产出的错误文案与原实现逐字节一致。

### 代码清理

- **合并为单一 `_enrich_validation_message(err, reply, *, stage)`**：把 stage 相关的差异收敛到一个 `stage` 关键字参数（`"stage1"`/`"stage2"`）。函数内仅在「仅思考区、正文为空」分支按 `stage` 选择对应的 `truncation_cause` 文案，并用 `stage_label` 变量渲染「阶段一/阶段二」标签；其余逻辑（配额短路、截断提示、明细拼接、分支顺序）完全共享。两处调用点（Stage 1 第 534 行、Stage 2 第 844 行）改为传入对应 `stage`。净减少约 45 行重复代码。

### 明确不改（保持原样）

- **两个 stage 的错误文案**：合并后逐字节保持与原双函数一致（含全角标点、`completion_tokens≈` 记法、成因指引措辞），不改变任何用户可见输出与日志内容。
- **调用时机与控制流**：仅替换函数名与新增 `stage` 关键字参数，`err_message` 的赋值位置、后续 `logger.warning` 与 `record.model_copy` 均不变。

### 验证

- `py_compile pa_agent/orchestrator/two_stage.py` 通过。
- `ruff check` 对比基线：改动前 **56** 条既有告警 → 改动后 **47** 条，减少的 9 条全部为 **RUF001**（去掉重复中文串带来的模糊 Unicode 标点告警）；其余类别（E402:11、UP037:7、RUF100:3、UP045:2、I001:1、UP035:1）与改动前**逐项一致，零新增**。
- 全仓 `grep` 确认旧函数名 `_enrich_stage1_validation_message`/`_enrich_stage2_validation_message` 已无残留引用，新函数 `_enrich_validation_message` 定义 1 处 + 调用 2 处。
- 该函数无独立单元测试直接覆盖（仅 `two_stage.py` 内部引用）；改动为纯重构、输出不变，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归两阶段编排相关用例。

---

## [Unreleased] — 2026-07-14（第六轮：并发安全 R8）

本轮落实后端审查报告（`docs/backend_review_report.md`）§4.2「中优先级」#6 与路线图 §5.1 的 **R8**：给若干**进程级可变状态**补上线程锁。项目大量使用后台 QThread（RefreshLoop tick、快照/分析/聊天 worker、数据源并发拉取），这些全局缓存/开关此前无锁保护，多线程并发读写存在 race（`dict` 并发写、复权模式读写撕裂、日志 handler 重装竞态、cursor-sdk monkeypatch 标志重复打补丁）。**原则：只加锁、不改语义与外部行为**——缓存命中/未命中结果、复权取值、日志输出、补丁幂等性均与原实现一致，耗时的文件 IO / prompt 构建放在锁外。

### 并发安全

- **`records/analysis_history.py:_LATEST_RECORD_CACHE` 无锁（审查 §4.2#6）**：后台增量分析线程读、保存后失效线程写，`dict` 并发读写可能 race。新增 `_LATEST_RECORD_LOCK`：`find_latest_successful_record` 的缓存读与缓存写各自在锁内完成，中间**耗时的 `records/pending/*.json` 扫描与解析放在锁外**（不长时间持锁）；`invalidate_latest_record_cache` 的 `clear()` 也纳入锁。缓存命中/未命中语义不变。
- **`ai/prompt_assembler.py:_SYSTEM_PROMPT_CACHE` 无锁**：多个 `PromptAssembler` 实例（不同 worker）并发首建同一 prompt_dir 的共享系统提示时会重复构建并互相覆盖。新增 `_SYSTEM_PROMPT_LOCK` + **双检锁**：先加锁读缓存，未命中则**在锁外构建**（避免长时间持锁做大字符串拼接），再加锁写入；若期间已有其他线程写入则复用既有条目，保证所有调用方拿到**同一份 byte-identical 前缀**（DeepSeek KV cache 命中依赖此不变式）。
- **`data/eastmoney_extended.py:_COMPACT_CTX_CACHE` 无锁**：A 股 F10/资金上下文的 TTL 缓存被并发数据拉取读写。新增 `_COMPACT_CTX_LOCK`：缓存读、写、`clear`/`pop` 均在锁内；实际的 `_build_compact_stock_context` 网络拉取放在锁外。TTL 与返回副本（`dict(...)`）语义不变。
- **`util/logging.py:_active_formatters/_configured` 无锁**：`configure_logging` 可能被重复调用（含 handler 重装），`update_api_key` 从设置对话框线程调用，二者对全局状态无保护。新增可重入 `_STATE_LOCK`（RLock，因 `configure_logging` 持锁期间会调用 `update_api_key`）：`configure_logging` 主体与 `update_api_key` 全程在锁内；仅把末尾的 diagnostics info 日志移出锁外，避免在持锁时触发日志链路。
- **`data/kline_adjust.py:_current` 无锁**：全局复权模式被设置动作与数据源并发读写。新增 `_LOCK`：`set_kline_adjust` 写、`get_kline_adjust` 读均在锁内，消除读写撕裂。取值归一化（`qfq/hfq/none` 白名单、非法回退默认）语义不变。
- **`ai/cursor_sdk_client.py` 四个 `_PATCHED_*` 开关无锁**：`_ensure_cursor_sdk_patches()` 除 import 期外，还从分析 worker 线程调用，多个 patch 函数的「check-then-set」标志非线程安全，可能重复打补丁或补丁半完成。新增 `_PATCH_LOCK` 串行化 `_ensure_cursor_sdk_patches()` 全过程，保证四个补丁整体幂等。

### 明确不改（保持原样）

- **`gui/decision_flow_viz.py` 动画相位**：审查 §4.2#6 曾列出模块级 `_ANIM_PHASE`，但已在第一轮（`7387943`）改为 `_FlowScene` 实例属性 `anim_phase`，仅 GUI 线程访问，无需加锁。
- **`ai/deepseek_client.py:_client` 连接池缓存（L4 新增）**：`DeepSeekClient` 实例通常由单一编排线程串行使用（Stage1→Stage2），`_get_client()` 的 check-then-build 不在跨线程共享路径上；加锁收益不抵复杂度，保持不动。

### 验证

- `py_compile` 通过（全部 6 个改动文件）。
- `ruff check` 对比基线：6 个文件改动前后同为 **1529** 条既有告警（全为全仓既有的 RUF001/002/003 中文标点、UP035、SIM 等噪音），**未新增任何告警**。
- 功能验证：`kline_adjust` set/get（含非法值回退、None 回退）逐项通过；`eastmoney_extended` 导入、`_COMPACT_CTX_LOCK` 为 `Lock`、`clear_compact_stock_context_cache()` 正常；`analysis_history` 的 `_LATEST_RECORD_LOCK` 存在、预置缓存后 `invalidate_latest_record_cache()` 清空生效。
- `cursor_sdk_client`、`prompt_assembler` 因本机无 PyQt6（`util/__init__`→`event_bus`→PyQt6 导入链）无法运行时导入，与既往各轮一致；改动为纯加锁、不改控制流与输出，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归，重点 `test_prompt_assembler_*`、`test_analysis_history_*`、`test_logs_have_no_plaintext_key`、`test_eastmoney_*`。

---

## [Unreleased] — 2026-07-14（第五轮：性能优化 L4）

本轮落实后端审查报告（`docs/backend_review_report.md`）路线图中的 **L4 性能优化**，针对 §8「性能热点」清单里在**热路径**（每次 RefreshLoop tick / 每次分析 / 每次 API 调用）重复付出的开销做减法。**原则：只降开销、不改语义与外部行为**——每处改动都保持输出与原实现逐位一致，仅避免重复计算或提前短路。

### 性能优化

- **每次 API 调用都新建 OpenAI 客户端，连接池无法复用（热点 `ai/deepseek_client.py:466`）**：`chat()` 与 `stream_chat()` 每次都 `_OpenAI(base_url=..., api_key=...)` 新建实例，Stage 1/Stage 2 两次调用各开一次全新 HTTP 会话。改为按 `(base_url, api_key)` 缓存客户端：新增 `DeepSeekClient._get_client()`，仅当 base_url/api_key 变化时重建；`update_provider()`（QClaw 自动 fallback 后切换 provider）时主动失效缓存。同一 provider 下 Stage 1→Stage 2 复用同一连接池，减少握手开销。
  - 涉及：`pa_agent/ai/deepseek_client.py`（`__init__` 新增 `_client`/`_client_key`、新增 `_get_client()`、`update_provider` 失效缓存、`chat`/`stream_chat` 两处改用 `_get_client()`）。
- **Stage 1/2 无条件把完整 prompt 逐条写 DEBUG 日志（热点 `orchestrator/two_stage.py:423-430,715-721`）**：即便日志级别高于 DEBUG，仍会执行 `for msg in messages:` 循环、`role.upper()` 与大段 prompt 字符串拼接，只是最终被丢弃。用 `if logger.isEnabledFor(logging.DEBUG):` 包裹两处循环，DEBUG 关闭时直接跳过，省去每次分析的无用字符串处理。
  - 涉及：`pa_agent/orchestrator/two_stage.py`（Stage 1、Stage 2 两处 prompt DEBUG 日志块）。
- **`build_analysis_frame` 重复计算 forming-bar 判定（热点 `data/snapshot.py`）**：函数先调用一次 `has_forming_bar_at_head` 求 `forming`，随后 `_newest_closed_slice` 内部又独立算了一遍（含 A 股日线交易时段判断等分支）。为 `_newest_closed_slice` 增加可选参数 `forming`，由调用方把已算好的结果传入，消除每次分析帧构建时的重复判定；参数缺省时行为不变（其他潜在调用方安全）。
  - 涉及：`pa_agent/data/snapshot.py`（`_newest_closed_slice` 新增 `forming` 参数、`build_analysis_frame` 复用 `forming`）。
- **几何特征 `_ema_gap_count` 为 O(n²)（热点 `ai/kline_features.py:250`）**：原实现对每根 K 线都从当前位置向老方向扫到「同侧 EMA 缺口」中断，逐棒 O(n) → 整帧 O(n²)。改为单次反向传递的 O(n) 批量函数 `_ema_gap_counts`：先算每根的缺口侧，再从最老一根反向累加（同侧则 `run[idx]=1+run[idx+1]`，否则重置），一次填满全部计数。缺口侧计算与 EMA 无效（越界 / NaN）作为「中断」的语义与原实现完全一致，已用 400 组随机数据（含空数组、NaN、短 EMA 序列）逐位比对验证等价。
  - 涉及：`pa_agent/ai/kline_features.py`（删除 `_ema_gap_count`、新增 `_ema_gap_counts`；`compute_kline_geometry_features` 预计算后按 idx 取值、`_feature_for_bar` 改收 `ema_gap_count` 参数）。
- **查找上次成功记录时全量加载 pending 目录（热点 `records/analysis_history.py:49-82`）**：`find_latest_successful_record` 在缓存未命中时会 `load_record()` 解析 `records/pending/*.json` 里**每一个**文件（含 JSON parse + Pydantic 校验），再按 symbol/timeframe 过滤。由于记录文件名格式固定为 `{时间戳}_{symbol}_{timeframe}.json`（见 `PendingWriter._build_basename`），改为先按 basename 中 `sanitize_filename_component(symbol)` / `sanitize_filename_component(timeframe)` 两个子串预过滤，只解析候选文件；`record.meta.symbol/timeframe` 的精确比对仍保留为最终权威判断，预过滤只做「安全收窄」不改变结果。
  - 涉及：`pa_agent/records/analysis_history.py`（`find_latest_successful_record` 增加文件名预过滤）。

### 明确不改（保持原样）

- **`records/pending_writer.py:133-154` 递归遍历做 API key 替换**：`_sanitize` 已有 `if not api_key: return data` 快速返回，且掩码是安全正确性所必需，遍历范围就是待落盘记录本身；改成增量/浅层替换会带来密钥泄漏风险，收益不抵风险，保持不动。
- **`records/trade_logger.py:607-624` 每次全量重写 CSV**：该「读入全部行→追加→带统一表头重写」是**刻意的 schema 迁移设计**（旧记录自动补齐新列）；改成纯追加会破坏历史 CSV 的列迁移能力。交易记录写入频率低（仅在产生订单时），全量重写开销可接受，保持不动。

### 验证

- `py_compile` 通过（全部 5 个改动文件）。
- `ruff check` 对比基线：改动前后同为 74 条既有告警（全为全仓既有的 I001 导入排序 / RUF002 中文标点 / UP035 等噪音），**未新增任何告警**。
- `_ema_gap_counts` 等价性：400 组随机 K 线（覆盖空数组、NaN EMA、短 EMA 序列）与原 O(n²) 实现逐 idx 比对，0 处不一致。
- `pa_agent.ai.kline_features` 可独立导入（无 PyQt6 依赖）；`git diff` 密钥扫描（`sk-...` / `api_key=...`）0 命中。
- 未实机运行完整 GUI 测试（本机所有 Python 解释器均无 PyQt6/hypothesis）；改动为纯性能优化、不改语义，建议在项目 venv 运行 `pytest -m "not e2e" -q` 回归，重点 `test_deepseek_client`、`test_build_analysis_frame`、`test_snapshot_*`、`test_kline_features`、`test_qclaw_auto_fallback`。

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
