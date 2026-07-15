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

## [Unreleased] — 2026-07-15（第七十三轮：继续 L7，扩展 CI 到 stance/别名与轻量图表辅助测试）

本轮继续推进 **L7：CI 增强**。第七十二轮已把 market features 测试纳入目标 CI；本轮继续筛选稳定的小型测试文件。`test_decision_stance.py` 覆盖决策立场归一化和不同激进度的指导文案；`test_stage1_normalizer_strategy_aliases.py` 覆盖 Stage 1 策略文件别名归一化；`test_overlay_lines.py` 与 `test_support_resistance_chart.py` 覆盖 overlay 价格精度和支撑/阻力图表线选择。这些测试稳定且不启动 GUI 事件循环。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_decision_stance.py`、`tests/unit/test_stage1_normalizer_strategy_aliases.py`、`tests/unit/test_overlay_lines.py` 与 `tests/unit/test_support_resistance_chart.py`。目标测试数量从 **242** 扩展到 **252**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增上述 4 个测试文件。
- **清理目标测试 lint**：`test_decision_stance.py` 为需保留的胜率区间 `30–44` 添加行级 `# noqa: RUF001`；`test_support_resistance_chart.py` 将生成器变量 `l` 改为 `level`，消除 `E741`。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 decision stance、Stage 1 策略文件别名、支撑/阻力图表线与 overlay 价格精度。

### 验证

- `py -3.12 -m pytest tests/unit/test_decision_stance.py tests/unit/test_stage1_normalizer_strategy_aliases.py tests/unit/test_overlay_lines.py tests/unit/test_support_resistance_chart.py --tb=line -q -p no:cacheprovider` → **10 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_overlay_lines.py tests/unit/test_support_resistance_chart.py tests/unit/test_data_source_factory.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_market_features.py tests/unit/test_structure_levels.py tests/unit/test_stage1_normalizer_strategy_aliases.py tests/unit/test_decision_stance.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **252 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_overlay_lines.py tests/unit/test_support_resistance_chart.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_market_features.py tests/unit/test_structure_levels.py tests/unit/test_stage1_normalizer_strategy_aliases.py tests/unit/test_decision_stance.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_decision_stance.py tests\unit\test_stage1_normalizer_strategy_aliases.py tests\unit\test_overlay_lines.py tests\unit\test_support_resistance_chart.py` → 通过。

---

## [Unreleased] — 2026-07-15（第七十二轮：继续 L7，扩展 CI 到 market features 测试）

本轮继续推进 **L7：CI 增强**。第七十一轮已把 KV prefix 与刷新 warmup 测试纳入目标 CI；本轮继续筛选低依赖的后端特征测试。`test_market_features.py` 覆盖简单市场特征计算与渲染输出，测试稳定且不访问 GUI/网络，适合进入目标 CI。对应源文件 `pa_agent/ai/market_features.py` 仍包含面向 prompt 的中文文案 Ruff 历史基线，本轮暂不把源文件纳入 focused Ruff。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_market_features.py`。目标测试数量从 **235** 扩展到 **242**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_market_features.py`。
- **清理目标测试 lint**：整理 `test_market_features.py` 的 import 换行，消除 Ruff `I001`；测试逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 market features。

### 验证

- `py -3.12 -m pytest tests/unit/test_market_features.py --tb=line -q -p no:cacheprovider` → **7 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_market_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **242 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_market_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_market_features.py` → 通过。

---

## [Unreleased] — 2026-07-15（第七十一轮：继续 L7，扩展 CI 到 KV prefix 与刷新 warmup 测试）

本轮继续推进 **L7：CI 增强**。第七十轮已把 QClaw/Cursor route 测试纳入目标 CI；本轮继续筛选纯后端、低依赖的小测试。`test_kv_prefix_cache.py` 覆盖 DeepSeek native 与 OpenClaw/QClaw/WorkBuddy/Cursor route 的 KV prefix-chain 开关判定；`test_refresh_loop_warmup.py` 通过 AST 验证刷新循环向数据源请求额外 warmup bars，测试稳定且不访问 GUI/网络。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_kv_prefix_cache.py` 与 `tests/unit/test_refresh_loop_warmup.py`。目标测试数量从 **230** 扩展到 **235**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_kv_prefix_cache.py` 与 `tests/unit/test_refresh_loop_warmup.py`。
- **保持运行逻辑不变**：本轮只扩展 CI 清单，不修改运行代码。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 KV prefix cache provider 判定与 refresh loop indicator warmup 取数结构。

### 验证

- `py -3.12 -m pytest tests/unit/test_kv_prefix_cache.py tests/unit/test_refresh_loop_warmup.py --tb=line -q -p no:cacheprovider` → **5 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **235 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_refresh_loop_warmup.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_kv_prefix_cache.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_kv_prefix_cache.py tests\unit\test_refresh_loop_warmup.py` → 通过。

---

## [Unreleased] — 2026-07-15（第七十轮：继续 L7，扩展 CI 到 QClaw/Cursor route 测试）

本轮继续推进 **L7：CI 增强**。第六十九轮已把 A 股/Tushare 无网络数据源测试纳入目标 CI；本轮继续筛选 provider route 相关的 mock-only 测试。`test_qclaw_agent_route.py` 与 `test_cursor_agent_route.py` 覆盖 OpenClaw/QClaw、WorkBuddy、Cursor subscription route 的模型别名、stale base_url 防串线和启动同步保护，测试稳定且不启动真实 relay/SDK。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_qclaw_agent_route.py` 与 `tests/unit/test_cursor_agent_route.py`。目标测试数量从 **212** 扩展到 **230**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_qclaw_agent_route.py` 与 `tests/unit/test_cursor_agent_route.py`。
- **清理目标测试 lint**：把多处嵌套 `with patch(...)` 合并为单个 `with` 语句，保留 OpenClaw 网关中文 mode 样例并用行级 `# noqa: RUF001` 标注；运行逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 QClaw/Cursor route。

### 验证

- `py -3.12 -m pytest tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py --tb=line -q -p no:cacheprovider` → **18 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **230 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_qclaw_agent_route.py tests/unit/test_cursor_agent_route.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_qclaw_agent_route.py tests\unit\test_cursor_agent_route.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十九轮：继续 L7，扩展 CI 到 A 股/Tushare 无网络数据源测试）

本轮继续推进 **L7：CI 增强**。第六十八轮已把 prompt txt 文件清单测试纳入目标 CI；本轮继续筛选数据源层的无网络小测试。`test_akshare_source.py` 覆盖 A 股 symbol 归一化、指数识别和 60m→4h 聚合；`test_tushare_source.py` 通过 fake `tushare` 模块覆盖 token 优先级、日线/分钟线抓取、缓存和限频错误提示，测试稳定且不访问真实网络。对应源文件仍有用户可见中文错误提示 Ruff `RUF001/RUF003` 历史基线，本轮暂不把源文件纳入 focused Ruff。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_akshare_source.py` 与 `tests/unit/test_tushare_source.py`。目标测试数量从 **197** 扩展到 **212**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_akshare_source.py` 与 `tests/unit/test_tushare_source.py`。
- **保留真实中文限频样例**：`test_tushare_source.py` 中的 Tushare 限频响应样例保留中文原文，并用行级 `# noqa: RUF001` 标注。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 A 股/Tushare 无网络数据源路径。

### 验证

- `py -3.12 -m pytest tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py --tb=line -q -p no:cacheprovider` → **15 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **212 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_akshare_source.py tests/unit/test_tushare_source.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_akshare_source.py tests\unit\test_tushare_source.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十八轮：继续 L7，扩展 CI 到 prompt txt 文件清单测试）

本轮继续推进 **L7：CI 增强**。第六十七轮已把限价单 K1 新鲜度纳入目标 CI；本轮继续筛选不依赖 GUI、网络或外部 SDK 的小型测试。`test_prompt_txt_files.py` 覆盖 Stage 1 / Stage 2 prompt `.txt` 文件清单、方向过滤与 full library 开关，测试稳定且测试文件 Ruff 干净，适合进入目标 CI。对应源文件 `prompt_assembler.py` 仍有大量用户可见中文 prompt 文案 Ruff `RUF001/RUF003` 历史基线，本轮暂不把该源文件纳入 focused Ruff。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_prompt_txt_files.py`。目标测试数量从 **193** 扩展到 **197**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_prompt_txt_files.py`。
- **保持运行逻辑不变**：本轮只扩展 CI 清单，不修改运行代码。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 prompt txt 文件清单。

### 验证

- `py -3.12 -m pytest tests/unit/test_prompt_txt_files.py --tb=line -q -p no:cacheprovider` → **4 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **197 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_prompt_txt_files.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_prompt_txt_files.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十七轮：继续 L7，扩展 CI 到限价单 K1 新鲜度测试）

本轮继续推进 **L7：CI 增强**。第六十六轮已把 Stage 1 支撑/阻力刷新纳入目标 CI；本轮继续筛选交易规则相关的小型稳定测试。`test_limit_order_k1_freshness.py` 覆盖限价单在最新 K1 已越过入场/止损后的失效判定，以及 lenient 校验下将过期限价单转为不下单的路径；对应核心源文件 `pa_agent/util/trade_metrics.py` 已在既有 Ruff 门禁中覆盖，适合以测试文件为主扩展 CI。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_limit_order_k1_freshness.py`。目标测试数量从 **190** 扩展到 **193**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_limit_order_k1_freshness.py`；`pa_agent/util/trade_metrics.py` 已在既有 focused Ruff 门禁中覆盖。
- **清理目标 lint**：整理 `test_limit_order_k1_freshness.py` 的 import 分组，消除 Ruff `I001`；测试逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖限价单 K1 新鲜度。

### 验证

- `py -3.12 -m pytest tests/unit/test_limit_order_k1_freshness.py --tb=line -q -p no:cacheprovider` → **3 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **193 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_limit_order_k1_freshness.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_limit_order_k1_freshness.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十六轮：继续 L7，扩展 CI 到 Stage 1 支撑/阻力刷新测试）

本轮继续推进 **L7：CI 增强**。第六十五轮已把 trade metrics helper 纳入目标 CI；本轮继续筛选非 GUI、非网络、低 Ruff 噪声的小模块。`test_structure_levels.py` 覆盖 Stage 1 支撑/阻力位刷新、破位过滤、swing pivot 回填与近远排序，测试稳定且 lint 清理范围小，适合进入目标 CI。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_structure_levels.py`。目标测试数量从 **185** 扩展到 **190**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/structure_levels.py` 与 `tests/unit/test_structure_levels.py`。
- **清理目标 lint**：移除 `structure_levels.py` 中冗余的 `int(round(...))` 包装，将未使用解包变量改为 `_lo` / `_hi`，并把 swing high/low 判断中的尾部条件改为等价布尔返回；运行逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 Stage 1 支撑/阻力刷新。

### 验证

- `py -3.12 -m pytest tests/unit/test_structure_levels.py --tb=line -q -p no:cacheprovider` → **5 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **190 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/structure_levels.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_structure_levels.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\ai\structure_levels.py tests\unit\test_structure_levels.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十五轮：继续 L7，扩展 CI 到 trade metrics helper 测试）

本轮继续推进 **L7：CI 增强**。第六十四轮已把 AI client factory 与 SessionTokenLedger 纳入目标 CI；本轮继续评估交易指标相关测试。`test_trade_metrics.py` 稳定且 Ruff 清理量小，适合先纳入目标 CI；`test_trade_metrics_validation.py` 虽然测试通过，但包含大量中文决策 trace 样例 Ruff 噪声，暂不纳入本轮门禁。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_trade_metrics.py`。目标测试数量从 **178** 扩展到 **185**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/util/trade_metrics.py` 与 `tests/unit/test_trade_metrics.py`。
- **清理目标 lint**：将 `trade_metrics.py` 中英文 docstring/error 的 en dash 与乘号替换为 ASCII 标点，并把测试样例中一处中文逗号替换为 ASCII 逗号；运行逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 trade metrics helper。

### 验证

- `py -3.12 -m pytest tests/unit/test_trade_metrics.py --tb=line -q -p no:cacheprovider` → **7 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **185 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/util/trade_metrics.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_trade_metrics.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\util\trade_metrics.py tests\unit\test_trade_metrics.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十四轮：继续 L7，扩展 CI 到 AI client factory 与 SessionTokenLedger 测试）

本轮继续推进 **L7：CI 增强**。第六十三轮已把 MT5 symbol availability 纳入目标 CI；本轮继续筛选 AI 层小模块。`client_factory` 路由测试和 `SessionTokenLedger` 阈值测试稳定，且清理后 Ruff 噪声可控，适合进入目标 CI。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_client_factory.py` 与 `tests/unit/test_cost_and_ledger.py`。目标测试数量从 **171** 扩展到 **178**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/client_factory.py`、`pa_agent/ai/session_ledger.py` 以及上述两组测试文件。
- **清理目标 lint**：将 `session_ledger.py` 的 PyQt import 移到模块 import 区，并把 `parent` 参数注解从字符串改为 `QObject | None`；删除 `test_cost_and_ledger.py` 未使用的 `pytest` import。运行逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 AI client factory 路由与 SessionTokenLedger。

### 验证

- `py -3.12 -m pytest tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py --tb=line -q -p no:cacheprovider` → **7 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **178 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/ai/client_factory.py pa_agent/ai/session_ledger.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_client_factory.py tests/unit/test_cost_and_ledger.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\ai\client_factory.py pa_agent\ai\session_ledger.py tests\unit\test_client_factory.py tests\unit\test_cost_and_ledger.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十三轮：继续 L7，扩展 CI 到 MT5 symbol availability 测试）

本轮继续推进 **L7：CI 增强**。第六十二轮已把分析历史与 demo record/replay 纳入目标 CI；本轮继续筛选数据源相关的小型稳定测试。候选集中 TradingView connectivity 依赖本机缺失的 `tvDatafeed`，TradingView 错误提示/别名模块和 provider connector 模块仍有大量用户可见中文文案 Ruff 噪声；因此本轮收窄到稳定且低噪声的 MT5 symbol availability 测试。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_mt5_symbol_available.py`。目标测试数量从 **169** 扩展到 **171**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `tests/unit/test_mt5_symbol_available.py`；对应源文件 `pa_agent/data/mt5.py` 已在既有 focused Ruff 门禁中覆盖。
- **保持运行逻辑不变**：本轮只扩展 CI 清单，无运行代码修改。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 MT5 symbol availability。

### 验证

- `py -3.12 -m pytest tests/unit/test_mt5_symbol_available.py --tb=line -q -p no:cacheprovider` → **2 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **171 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_mt5_symbol_available.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile tests\unit\test_mt5_symbol_available.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十二轮：继续 L7，扩展 CI 到分析历史与 demo 记录回放测试）

本轮继续推进 **L7：CI 增强**。第六十一轮已把 validation retry/retry policy 纳入目标 CI；本轮继续筛选非网络、低噪声的记录读取路径。`analysis_history` 与 demo record/replay 相关测试稳定，覆盖增量分析历史定位、demo 记录加载、损坏记录跳过与响应 reasoning 提取，适合进入目标 CI。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_analysis_history.py`、`test_demo_record_loader.py`、`test_demo_replayer.py`。目标测试数量从 **158** 扩展到 **169**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/records/analysis_history.py`、`pa_agent/demo/record_loader.py`、`pa_agent/demo/replayer.py` 以及上述三组测试文件。
- **清理目标 lint**：移除 `record_loader.py` 中当前 Ruff 配置下冗余的 `# noqa: BLE001`；整理 `analysis_history.py` import 顺序；把 `replayer.py` 中响应提取 import 移到模块 import 区，消除 E402。运行逻辑保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖分析历史增量定位与 demo record/replay。

### 验证

- `py -3.12 -m pytest tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **11 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py --tb=line -q -p no:cacheprovider` → **169 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py pa_agent/records/analysis_history.py pa_agent/demo/record_loader.py pa_agent/demo/replayer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py tests/unit/test_analysis_history.py tests/unit/test_demo_record_loader.py tests/unit/test_demo_replayer.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\records\analysis_history.py pa_agent\demo\record_loader.py pa_agent\demo\replayer.py tests\unit\test_analysis_history.py tests\unit\test_demo_record_loader.py tests\unit\test_demo_replayer.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十一轮：继续 L7，扩展 CI 到 validation retry 策略测试）

本轮继续推进 **L7：CI 增强**。第六十轮已把 provider quota/402 检测纳入目标 CI；本轮继续评估校验/重试链。候选集中 `test_json_validator.py` 仍依赖缺失的 `tools/stage2_raw_sample.txt` 样本，`test_validation_lenient_fixes.py` 存在既有断言失败，`retry_feedback.py` 与 `stage2_normalizer.py` 仍有大量 prompt/中文文案 Ruff 噪声；因此本轮收窄到稳定的 `retry_policy.py` 与 `test_validation_retry.py`。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_validation_retry.py`。目标测试数量从 **146** 扩展到 **158**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/retry_policy.py` 与 `tests/unit/test_validation_retry.py`，使 retry policy 的 category 重试决策、cheat 检测和 validation retry 反馈契约进入 lint 门禁。
- **清理目标 lint**：将 `retry_policy.detect_cheat()` 中 gate_result raw weakening 检测的嵌套 `if` 改为等价组合条件，消除 SIM102；不改变 normalizer 修复 wait/unknown→proceed 时的跳过逻辑。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 validation retry/retry policy。

### 验证

- `py -3.12 -m pytest tests/unit/test_validation_retry.py --tb=line -q -p no:cacheprovider` → **12 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py --tb=line -q -p no:cacheprovider` → **158 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/ai/retry_policy.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py tests/unit/test_validation_retry.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\ai\retry_policy.py tests\unit\test_validation_retry.py` → 通过。

---

## [Unreleased] — 2026-07-15（第六十轮：继续 L7，扩展 CI 到 provider quota 检测）

本轮继续推进 **L7：CI 增强**。第五十九轮已把 K 线几何特征测试纳入目标 CI；本轮继续评估 provider 与连续性相关小模块。候选集中 `decision_continuity.py` 仍有既有测试失败和大量 prompt 文案 Ruff 噪声，`provider_override_by_model` 受 connector/环境状态影响仍不适合直接纳入 CI；因此本轮收窄到稳定的 provider quota/402 检测路径。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_provider_errors.py`。目标测试数量从 **141** 扩展到 **146**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/provider_errors.py` 与 `tests/unit/test_provider_errors.py`，使 provider quota/402 识别与 category e 非重试路径进入 lint 门禁。
- **保留网关原文与用户提示语义**：`PROVIDER_QUOTA_USER_MESSAGE` 和测试里的 OpenClaw 402 中文响应样例需要保留真实中文标点，本轮用行级 `# noqa: RUF001` 标注保留原因，而不是改写用户可见文案或网关样例。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 provider quota/402 检测。

### 验证

- `py -3.12 -m pytest tests/unit/test_provider_errors.py --tb=line -q -p no:cacheprovider` → **5 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py --tb=line -q -p no:cacheprovider` → **146 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/ai/provider_errors.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py tests/unit/test_provider_errors.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\ai\provider_errors.py tests\unit\test_provider_errors.py` → 通过。

---

## [Unreleased] — 2026-07-15（第五十九轮：继续 L7，扩展 CI 到 K 线几何特征测试）

本轮继续推进 **L7：CI 增强**。第五十八轮已把 AI 小模块纯函数测试纳入目标 CI；本轮继续评估后端特征计算测试。候选集中 `market_features.py` 仍有大量面向 prompt 的中文文案 RUF001 历史噪声，不适合直接纳入 Ruff 门禁；因此本轮收窄到稳定且可清理的 ATR true range、K 线方向标签与 `kline_features` 几何特征测试。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_atr_true_range.py`、`test_kline_candle_direction.py`、`test_kline_features.py`。目标测试数量从 **131** 扩展到 **141**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/kline_features.py` 以及上述三组测试文件，使 K 线几何特征路径进入 lint 门禁。
- **清理目标注释 lint**：将 `kline_features.py` 与 `test_kline_features.py` 中少量注释/docstring 的中文全角标点改为 ASCII 标点；不改运行时代码、不改 prompt 文案、不改变 follow-through 判定语义。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 ATR true range、K 线方向与 K 线几何特征。

### 验证

- `py -3.12 -m pytest tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py --tb=line -q -p no:cacheprovider` → **10 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py --tb=line -q -p no:cacheprovider` → **141 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/ai/kline_features.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_atr_true_range.py tests/unit/test_kline_candle_direction.py tests/unit/test_kline_features.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent\ai\kline_features.py tests\unit\test_atr_true_range.py tests\unit\test_kline_candle_direction.py tests\unit\test_kline_features.py` → 通过。

---

## [Unreleased] — 2026-07-15（第五十八轮：继续 L7，扩展 CI 到 AI 小模块纯函数测试）

本轮继续推进 **L7：CI 增强**。第五十七轮已把时间戳与 KlineBar 归一化工具测试纳入目标 CI；本轮继续评估 AI 层小模块测试。候选集中 `decision_stance.py` 与 `session_ledger.py` 仍有大量历史 Ruff 噪声，不适合直接纳入 lint 门禁；因此本轮收窄到稳定且 Ruff 干净的 `cycle_enums`、`response_extract` 与 `mimo_compat` 三组纯函数/兼容性测试。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_cycle_enums.py`、`test_response_extract.py`、`test_mimo_compat.py`。目标测试数量从 **118** 扩展到 **131**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/ai/cycle_enums.py`、`pa_agent/ai/response_extract.py`、`pa_agent/ai/mimo_compat.py` 以及对应三组测试文件。
- **保留历史噪声边界**：`decision_stance.py` 主要是中文 prompt/指导文案中的 RUF001 标点噪声，`session_ledger.py` 仍有 E402/UP037 历史风格问题；本轮不把这些文件加入 CI Ruff，避免 L7 门禁被非本轮治理目标卡死。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖 cycle 枚举、响应提取与 MiMo 兼容模块。

### 验证

- `py -3.12 -m pytest tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py --tb=line -q -p no:cacheprovider` → **13 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py --tb=line -q -p no:cacheprovider` → **131 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent/ai/cycle_enums.py pa_agent/ai/response_extract.py pa_agent/ai/mimo_compat.py tests/unit/test_cycle_enums.py tests/unit/test_response_extract.py tests/unit/test_mimo_compat.py` → 通过。

---

## [Unreleased] — 2026-07-15（第五十七轮：继续 L7，扩展 CI 到时间戳与 KlineBar 工具测试）

本轮继续推进 **L7：CI 增强**。第五十六轮已把安全/配置/记录写入路径纳入目标 CI；本轮继续评估纯后端工具测试。候选集中 `price_tick` 与 `market_defaults` 暴露既有测试失败，`trade_metrics` / `price_tick` 相关文件仍有大量中文标点 Ruff 基线噪声，因此本轮收窄到稳定且低噪声的时间戳与 KlineBar 归一化工具测试。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_datetime_ts.py` 与 `tests/unit/test_kline_bar_normalize.py`。目标测试数量从 **105** 扩展到 **118**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/data/datetime_ts.py` 与上述两个测试文件；`pa_agent/data/base.py` 已在既有门禁中覆盖，继续守护 `KlineBar` normalize 路径。
- **清理 `datetime_ts` 目标 lint**：`pa_agent/data/datetime_ts.py` 和 `test_datetime_ts.py` 改用 `datetime.UTC`，并把 pandas `Timestamp` 的 UTC 归一分支收敛为等价三元表达式；同时修正测试中一处错位注释缩进。时间戳语义保持不变：naive datetime 仍按 UTC wall clock，`naive_local_to_utc()` 仍按主机本地 offset 转 UTC。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖时间戳转换与 KlineBar 归一化。

### 验证

- `py -3.12 -m pytest tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py --tb=line -q -p no:cacheprovider` → **13 passed**。
- 扩展后目标集：`py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py --tb=line -q -p no:cacheprovider` → **118 passed**。
- 扩展后 Ruff：`py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/data/datetime_ts.py pa_agent/ai/provider_sync_service.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent/data/datetime_ts.py tests/unit/test_datetime_ts.py tests/unit/test_kline_bar_normalize.py` → 通过。

---

## [Unreleased] — 2026-07-15（第五十六轮：继续 L7，扩展 CI 到安全配置与记录写入目标测试）

本轮继续推进 **L7：CI 增强**。第五十五轮已为现有目标测试增加覆盖率报告；本轮继续扩大目标 pytest 的业务覆盖面，纳入此前已稳定的安全/配置/记录写入路径：API Key 至静态加密、settings load/save round-trip、PendingWriter 递归脱敏和记录文件名安全。这些路径与项目安全边界直接相关，且测试稳定，不依赖 GUI 或真实网络，适合纳入 CI 目标集。

### 工程治理

- **CI 目标 pytest 扩容**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 新增 `tests/unit/test_secret_store.py`、`test_settings_round_trip.py`、`test_pending_writer_sanitize.py`、`test_pending_writer_no_plaintext_key.py`。目标测试数量从 **60** 扩展到 **105**，继续通过 `pytest-cov` 输出覆盖率报告。
- **CI Ruff 门禁扩容**：聚焦 Ruff 新增 `pa_agent/security/secret_store.py`、`pa_agent/records/pending_writer.py` 以及上述四个测试文件，使新增 CI 目标路径同时具备 lint 门禁。
- **清理目标文件 lint**：`pending_writer.py` 改用 `datetime.UTC` 替代 `timezone.utc`，并移除当前 Ruff 配置下冗余的 `# noqa: BLE001`；相关测试文件删除未使用 import，并按 Ruff 整理 import 块。`PendingWriter` 的异常处理语义和 `logger.debug(..., exc_info=True)` 可观测性保持不变。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已覆盖安全加密、settings round-trip 与 PendingWriter 脱敏/文件名安全。

### 验证

- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py --tb=line -q -p no:cacheprovider` → **105 passed**。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/ai/provider_sync_service.py pa_agent/security/secret_store.py pa_agent/records/pending_writer.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent/records/pending_writer.py tests/unit/test_settings_round_trip.py tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py` → 通过。

---

## [Unreleased] — 2026-07-15（第五十五轮：继续 L7，给 CI 目标测试增加覆盖率报告）

本轮继续推进 **L7：CI 增强**，切入上一轮尚未覆盖的“覆盖率”项。当前 CI 已具备安装/import、目标 pytest 与聚焦 Ruff；但 `pyproject.toml` 的 dev 依赖没有 `pytest-cov`，CI 也没有任何覆盖率输出。本轮先建立低风险覆盖率基线：让现有目标测试输出 `pa_agent` 的终端覆盖率报告，但暂不设置 `--cov-fail-under`，避免把当前 11% 的目标子集覆盖率误变成阻塞门禁。

### 工程治理

- **新增 dev 依赖 `pytest-cov>=5`**：加入 `pyproject.toml` 的 `[project.optional-dependencies].dev`，使 CI 的 `pip install -e ".[dev]"` 能安装 coverage 插件。
- **CI 目标 pytest 增加 coverage 输出**：`.github/workflows/ci.yml` 的 `Run targeted unit tests` 步骤新增 `-p pytest_cov --cov=pa_agent --cov-report=term-missing:skip-covered`。这会在现有 60 项目标测试通过后输出 `pa_agent` 覆盖率报告，先提供可观测基线，不生成持久报告文件，也不设失败阈值。
- **保持现有测试/Ruff 门禁不变**：目标 pytest 范围、聚焦 Ruff 文件集合不扩大，避免本轮同时引入测试范围变化与覆盖率工具链变化。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确 CI 已输出目标覆盖率报告，但完整测试、Black 与覆盖率阈值仍属于 L7 后续增强。

### 验证

- 本机通过仓库临时 target 安装 `pytest-cov>=5` 后，使用 `PYTHONPATH=.tmp_pytest_cov` 显式加载插件验证 coverage 命令：目标 pytest **60 passed**，输出 `pa_agent` 终端覆盖率报告，总覆盖率 **11%**（目标子集基线）。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/ai/provider_sync_service.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py` → **All checks passed**。
- `py -3.12 -c "import pathlib, tomllib; data=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); print(data['project']['optional-dependencies']['dev'])"` → 成功解析并包含 `pytest-cov>=5`。
- coverage 验证产生的 `.coverage` 与 `.tmp_pytest_cov/` 临时目录已删除，未进入提交。

---

## [Unreleased] — 2026-07-15（第五十四轮：继续 L7，扩大 Ruff 门禁并清理目标测试 lint）

本轮继续推进 **L7：CI 增强**。第五十三轮留下的直接问题是 Black 门禁尚未启用，因为本机 `black --check` 会卡住。本轮先复核 Black 工具链：当前全局 `black 26.5.1` 连 `--version` 都无法稳定返回；把 `black>=24.4,<26` 安装到仓库临时 target 后，隔离的 `black 25.12.0` 同样在 `--version` / `--check` 卡住。因此本轮不再强行推进 Black CI，而是选择可验证的 L7 切片：把上一轮新增到 CI 的 M3/M5 目标测试和 `ProviderSyncService` 纳入 Ruff 门禁，并清理这些文件中的真实 lint。

### 工程治理

- **CI Ruff 门禁扩容**：`.github/workflows/ci.yml` 的 `Run focused Ruff checks` 新增 `pa_agent/ai/provider_sync_service.py`、`tests/unit/test_order_method_router.py`、`test_trend_context.py`、`test_decision_nodes_orchestrator.py`、`test_provider_sync_service.py`、`test_qclaw_auto_fallback.py`。CI 现在不仅测试这些路径，也对对应测试/服务文件执行 lint。
- **清理目标测试 lint**：删除 `test_decision_nodes_orchestrator.py` 中未使用的 `call` import，把未使用的解包变量改为 `_assembler` / `_writer` / `_client`；删除 `test_trend_context.py` 中未使用的 `compute_background_direction` import；把 `test_qclaw_auto_fallback.py` 中预期的 `APIConnectionError` 吞掉逻辑改为 `contextlib.suppress(...)`，并按 Ruff 建议合并 `with` 语句。
- **清理 `ProviderSyncService` 冗余 noqa**：当前 Ruff 配置未启用 `BLE001`，`# noqa: BLE001` 会触发 RUF100；移除 `finish_provider_fallback()` 保存失败兜底分支上的冗余 noqa，保留原有 `except Exception as save_exc` 行为和 warning 日志。
- **暂不纳入决策源文件 Ruff**：`order_method_router.py` 与 `decision_node_engine.py` 仍有随中文 reason 串存在的历史 RUF001 标点告警，本轮不把这些源文件加入 CI Ruff，避免 L7 门禁被历史中文文案噪声卡死。

### 验证

- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py --tb=line -q -p no:cacheprovider` → **60 passed**。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py pa_agent/ai/provider_sync_service.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent/ai/provider_sync_service.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_qclaw_auto_fallback.py tests/unit/test_trend_context.py` → 通过。
- Black 复核：全局 `black 26.5.1` 与临时 target 的 `black 25.12.0` 均会在 `--version` / `--check` 场景无输出卡住，已手动中断；本轮未启用 Black CI。

---

## [Unreleased] — 2026-07-15（第五十三轮：继续 L7，扩大 CI 目标测试并整理 Black 前置格式）

本轮继续推进 **L7：CI 增强**。第五十二轮已让 CI 从“安装 + import”升级为“目标 pytest + 聚焦 Ruff”；本轮在不触碰全仓历史基线的前提下，继续扩大目标 pytest 覆盖，把最近几轮已稳定的 M3/M5 核心路径纳入 CI。同时对上一轮 CI lint 文件集合执行 Black 机械格式化，作为后续启用 Black 门禁前的前置清理；但由于本机 `black --check` 对单文件与多文件均出现无输出卡住，本轮暂不把 Black 写入 CI。

### 工程治理

- **CI 目标 pytest 扩容**：在原 forming-bar/data-source 测试集基础上，新增 `tests/unit/test_order_method_router.py`、`test_trend_context.py`、`test_decision_nodes_orchestrator.py`、`test_provider_sync_service.py`、`test_qclaw_auto_fallback.py`。CI 现在覆盖 M7 forming-bar 统一入口、M3 决策编排 facade、§11 broad_channel 突破单路由修复，以及 M5 provider fallback 服务尾部。
- **目标文件 Black 机械格式化**：对 `pa_agent/data/base.py`、`snapshot.py`、`mt5.py`、`yfinance_source.py`、`tests/unit/test_data_source_forming_bar.py`、`tests/unit/test_mt5_clock_skew.py` 执行 Black 格式化。改动仅为 import/docstring 空行、对齐空格、长列表/字典/字符串换行等机械排版，不改变 forming-bar 行为。
- **暂缓 Black CI 门禁**：本机 `py -3.12 -m black --check ...` 对同一候选文件集合和逐文件执行均无输出卡住，只能手动中断；因此本轮不把 `black --check` 写入 CI，避免引入未经验证的必过门禁。后续 L7 可先固定 Black 版本或进一步定位本机卡顿原因，再启用 Black。
- **同步 `AGENTS.md`**：更新 CI 状态说明，明确目标测试已从 forming-bar/data-source 扩展到 §11 路由、决策编排和 provider fallback。

### 验证

- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py tests/unit/test_order_method_router.py tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py --tb=line -q -p no:cacheprovider` → **60 passed**。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py` → **All checks passed**。
- `py -3.12 -m py_compile pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py` → 通过。
- `py -3.12 -m black --check ...` 与逐文件 `black --check` 均超过 30 秒无输出，已手动中断；本轮仅保留机械格式化结果，不启用 CI Black 门禁。

---

## [Unreleased] — 2026-07-15（第五十二轮：启动 L7，给 CI 增加目标测试与聚焦 Ruff 门禁）

本轮根据后端审查报告 §5.3 的 **L7：CI 增强** 开始收窄 CI 缺口。此前 `.github/workflows/ci.yml` 只在 Windows + Python 3.11 下安装依赖并 import `pa_agent`，没有运行任何 pytest、ruff、black 或覆盖率检查。考虑到全仓仍存在大量历史 Ruff 中文标点告警，且当前 Python 文件尚未整体 black 格式化，本轮先落地低风险第一片：把近期 M7 forming-bar/data-source 相关的稳定目标单测和同范围 Ruff 检查纳入 CI。

### 工程治理

- **CI 新增目标单测步骤**：安装与 import 验证之后，运行 `tests/unit/test_data_source_forming_bar.py`、`test_bar_close_wait.py`、`test_snapshot_closed_only_buffer.py`、`test_build_analysis_frame.py`、`test_snapshot_indicator_warmup.py`、`test_data_source_factory.py`、`test_mt5_clock_skew.py`。该子集覆盖 `DataSource.has_forming_bar_at_head(...)` 统一入口、snapshot closed-only 逻辑、各数据源 forming 判定复用，以及 MT5 clock skew 的无本地终端测试路径。
- **CI 新增聚焦 Ruff 步骤**：对 `pa_agent/data/base.py`、`snapshot.py`、`mt5.py`、`yfinance_source.py` 以及对应 forming/MT5 单测运行 `python -m ruff check`。这些文件在本轮前已确认可全量通过 Ruff，适合作为第一批 CI lint 门禁。
- **暂不启用 Black / 全仓 Ruff / 全量 pytest**：本机验证显示候选文件 `black --check` 仍会触发格式化请求，若本轮直接启用 Black 会把 CI 增强扩大为大面积格式化任务；全仓 Ruff 也仍受历史中文标点基线影响。Black、覆盖率、完整 `pytest -m "not e2e"` 继续作为 L7 后续增量推进。
- **同步 `AGENTS.md`**：更新测试策略与发布章节中的 CI 描述，避免继续声称 CI 仅做安装与 import。

### 验证

- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py --tb=line -q -p no:cacheprovider` → **41 passed**。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py pa_agent/data/mt5.py pa_agent/data/yfinance_source.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py` → **All checks passed**。
- `py -3.12 -m black --check ...` 对同一候选文件返回 **6 files would be reformatted**，确认为本轮暂缓 Black CI 门禁的基线证据。

---

## [Unreleased] — 2026-07-15（第五十一轮：修复 §11 broad_channel 突破单被错误降级为限价单）

本轮处理第五十轮 M3 收官验证中暴露出的既有失败：`test_order_method_router.py::test_model_breakout_preserved_for_broad_channel`。该用例描述的是 **broad_channel 默认偏限价，但模型若给出完整突破单依据（`entry_basis_bar` + `entry_basis_extreme`）且 §10.3 已通过，应保留模型明确的突破单选择**。实际代码中已写了保留分支，但 `_has_trade_prices()` 错把可选的 `take_profit_price_2` 当成必填价格，导致只有主止盈价的有效突破单未进入保留分支，随后被 broad_channel 默认路线改成 `限价单`。

### 修复

- **修正 `order_method_router._has_trade_prices()`**：核心交易价格只要求 `entry_price`、`stop_loss_price`、主 `take_profit_price` 三项非空；`take_profit_price_2` 是可选分批止盈，不再作为保留模型显式 `限价单` / `市价单` / `突破单` 选择的必要条件。
- **保留既有安全边界**：突破单仍必须有 `entry_basis_bar` + `entry_basis_extreme`，否则继续走 `breakout_fallback_to_limit` 回退为限价单；§10.3=否 / §14 违规短路逻辑不变。

### 验证

- `py_compile` 通过（`order_method_router.py`、`test_order_method_router.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_order_method_router.py --tb=line -q -p no:cacheprovider` → **3 passed**。
- 直接调用 `order_method_router.route_order_method()` 复核 broad_channel + 完整做空突破依据：输出 `decision["order_type"] == "突破单"`，最终节点 `11.2`，`answer="是"`。
- `git diff --check` 通过。
- `py -3.12 -m ruff check pa_agent/ai/order_method_router.py tests/unit/test_order_method_router.py` 仍只报 `order_method_router.py` 既有 RUF001 中文标点告警（随中文 reason 串存在），本轮未新增新的 ruff 类别。

---

## [Unreleased] — 2026-07-15（第五十轮：完成 M3，提取 DecisionNodeEngine 编排层）

本轮回到后端审查报告 §5.2 的 **M3：拆分 `decision_nodes.py`** 做收官。此前 M3 已陆续拆出阈值常量、几何原语、preflight、trace 结果层、全部 section-judge、override 裁决、§11 下单方式路由、§9 信号棒/限价单上下文辅助；`decision_nodes.py` 中仅剩最后的 `DecisionNodeEngine` 编排类。为完成 M3，本轮把 `DecisionNodeEngine.apply_stage1()` / `apply_stage2()` 移入独立模块 `decision_node_engine.py`，让 `decision_nodes.py` 退化为兼容 facade，继续稳定旧 import 路径。

### 代码清理

- **新增 `pa_agent/ai/decision_node_engine.py`**：承接原 `DecisionNodeEngine` 类，保留 `apply_stage1()` / `apply_stage2()` 的编排职责：调用 diagnostic / direction / always-in / signal-bar / order-method / override / trace 等已拆出的模块，写回 `gate_trace`、`decision_trace`、`trend_context` 和 `bar_analysis.always_in`。除格式收敛与安全等价的 `program_nodes = [node_91, node_92, node_93, node_95, *sec11_nodes]` 外，不改变决策语义和中文 reason 串。
- **`decision_nodes.py` 缩为兼容 facade**：删除内联 `DecisionNodeEngine` 实现，改为从 `decision_node_engine.py` 导入并重导出；同时继续重导出历史调用点依赖的 `judge_*`、`route_order_method`、`is_planned_limit_order`、`check_preflight_data`、`NodeFill`、三个阈值常量等名字。旧的 `from pa_agent.ai.decision_nodes import ...` 路径保持可用。
- **补充 `__all__`**：显式列出 facade 的兼容导出面，降低后续清理时误删历史 import 名字的风险。

### 验证

- `py_compile` 通过（`decision_nodes.py`、`decision_node_engine.py`、`stage1_normalizer.py`、`stage2_normalizer.py`、`program_prefill_hint.py`，EXIT=0）。
- import 核验通过：从 `pa_agent.ai.decision_nodes` 导入 `DecisionNodeEngine`、所有历史 judges/helpers/thresholds，并确认 `DecisionNodeEngine is pa_agent.ai.decision_node_engine.DecisionNodeEngine`。
- `py -3.12 -m pytest tests/unit/test_trend_context.py tests/unit/test_decision_nodes_orchestrator.py --tb=line -q -p no:cacheprovider` → **8 passed**。
- `py -3.12 -m pytest tests/unit/test_order_method_router.py -k "not model_breakout_preserved_for_broad_channel" --tb=line -q -p no:cacheprovider` → **2 passed / 1 deselected**。
- 未运行完整 `test_decision_nodes_judges.py` / `test_decision_nodes_preflight.py`：当前 Python 3.12 环境缺少 `hypothesis`，测试收集阶段报 `ModuleNotFoundError: No module named 'hypothesis'`。
- `test_order_method_router.py::test_model_breakout_preserved_for_broad_channel` 仍失败（期望 `突破单`，当前 `order_method_router.route_order_method()` 直接调用也输出 `限价单`），确认为既有路由行为/测试期望不一致，非本轮 facade 提取引入。
- `py -3.12 -m ruff check pa_agent/ai/decision_nodes.py pa_agent/ai/decision_node_engine.py` 当前仅剩 **8×RUF001**，均为随原中文 reason 串迁入 `decision_node_engine.py` 的全角标点告警；原 `decision_nodes.py` 已从 400 行降至 71 行，新模块 259 行。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十九轮：继续 M7，让 MT5 复用 DataSource 默认 forming 判定）

本轮继续推进 **M7：统一 forming bar 判定**。第四十八轮已让 YFinance 源内构建复用 ABC 默认入口；继续核查剩余显式硬编码后，`MT5Source.latest_snapshot()` 仍把头部 bar 固定视为 forming（`is_forming=True`），再依赖下游 snapshot 复判。MT5 已提供 `server_time_ms()`，而 ABC 默认 `has_forming_bar_at_head(...)` 会通过 `reference_now_ms(data_source=self)` 优先使用 broker tick 时间，因此应把 MT5 源内构建也接入统一入口，让过期/停盘头部在源内就可写回 closed。

### 代码清理

- **`MT5Source.latest_snapshot()` 复用 `DataSource.has_forming_bar_at_head(...)`**：构造每根 `KlineBar` 后，头部 bar 仍先按 MT5 position 0 语义临时 `closed=False`，随后调用 `self.has_forming_bar_at_head([bar], self._timeframe)`，按返回值写回最终 `closed=not is_forming`。非头部 bar 仍保持 `closed=True`，`copy_rates_from_pos()`、成交量兜底、OHLCV/seq/normalize 流程不变。
- **保持 MT5 使用 ABC 默认语义**：不新增 `MT5Source` override；默认入口会优先调用 `MT5Source.server_time_ms()` 取 broker/server tick 时间，仍保留 `is_bar_still_forming()` 对 daily/weekly stale broker time 的安全网。
- **扩展 `tests/unit/test_data_source_forming_bar.py`**：新增无真实 MT5 终端测试，stub `MetaTrader5` 模块与 `copy_rates_from_pos()`，验证 `latest_snapshot()` 会调用数据源 forming 入口，并按 override 返回值写回头部 `closed`。
- **修复 `tests/unit/test_mt5_clock_skew.py` 的环境依赖**：原测试直接 `patch("MetaTrader5.symbol_info_tick")`，在未安装 MetaTrader5 的解释器中会 `ModuleNotFoundError`。改为通过 `monkeypatch.setitem(sys.modules, "MetaTrader5", ...)` 注入假模块，使测试不依赖本机安装 MT5 包。
- **清理 `mt5.py` 既有失效 noqa**：当前 ruff 配置未启用 `BLE001`，`# noqa: BLE001` 会触发 RUF100；本轮移除这些失效注释，使 `pa_agent/data/mt5.py` 全文件 ruff 通过。

### 验证

- `py_compile` 通过（`mt5.py`、`test_data_source_forming_bar.py`、`test_mt5_clock_skew.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py tests/unit/test_mt5_clock_skew.py --tb=line -q -p no:cacheprovider` → **41 passed**。
- `py -3.12 -m ruff check pa_agent/data/mt5.py tests/unit/test_data_source_forming_bar.py tests/unit/test_mt5_clock_skew.py` → **All checks passed**。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十八轮：继续 M7，让 YFinance 复用 DataSource 默认 forming 判定）

本轮继续推进 **M7：统一 forming bar 判定**。前几轮已建立 `DataSource.has_forming_bar_at_head(...)` 入口，并将 A 股源与 TradingView 的特殊语义下沉。继续核查剩余数据源后，`YFinanceSource.latest_snapshot()` 仍硬编码 `closed=(i != 0)`：头部永远先标为未收盘，再依赖 snapshot 层复判。YFinance 没有 broker/server time，也没有 TradingView 的固定偏移取模需求，因此无需新增专门 override；直接复用 ABC 默认判定即可让源内构建与 snapshot 共享同一入口。

### 代码清理

- **`YFinanceSource.latest_snapshot()` 复用 `DataSource.has_forming_bar_at_head(...)`**：构造每根 `KlineBar` 后，头部 bar 仍先按旧规则临时 `closed=False`，随后调用 `self.has_forming_bar_at_head([bar], self._timeframe)`，按返回值写回最终 `closed=not is_forming`。非头部 bar 仍保持 `closed=True`，OHLCV/seq/normalize 流程不变。
- **保持 YFinance 使用 ABC 默认语义**：不新增 `YFinanceSource` override；默认入口会用本地时间和 timeframe 判断头部周期是否已结束，能把 stale `closed=False` 头部在周期结束后视为已收盘。
- **顺手清理同函数既有 SIM108**：把 `period` 的 intraday/daily 分支改为等价三元表达式，使 `pa_agent/data/yfinance_source.py` 全文件 ruff 通过。
- **扩展 `tests/unit/test_data_source_forming_bar.py`**：新增无网络 YFinance 测试，stub `yfinance.Ticker.history()`，验证 `latest_snapshot()` 会调用数据源 forming 入口，并按 override 返回值写回头部 `closed`。

### 验证

- `py_compile` 通过（`yfinance_source.py`、`test_data_source_forming_bar.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py --tb=line -q -p no:cacheprovider` → **36 passed**。
- `py -3.12 -m ruff check pa_agent/data/yfinance_source.py tests/unit/test_data_source_forming_bar.py` → **All checks passed**。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十七轮：继续 M7，下沉 TradingView forming 倒计时判定）

本轮继续推进 **M7：统一 forming bar 判定**。第四十五轮建立了 `DataSource.has_forming_bar_at_head(...)` 统一入口，第四十六轮已把 A 股源的 session 差异下沉为 override。本轮转向 `TradingViewSource`：它此前仍在 `latest_snapshot()` 内直接 import `seconds_until_bar_closes()` 并计算头部 bar 是否仍在形成。该逻辑属于 TradingView 数据源自身的时间戳语义（尤其是固定 exchange/broker offset 下的取模倒计时），应放到数据源 override 中，由 snapshot 和源内构建共享。

### 代码清理

- **`TradingViewSource.has_forming_bar_at_head(...)` override**：新增数据源级 forming 判定。空列表返回 `False`；缺少 timeframe 时回退 `not head.closed`；有 timeframe 时继续使用既有 `seconds_until_bar_closes(int(head.ts_open), timeframe, now_ms=...)`，`secs_left > 0` 即 forming。该实现保留原 `latest_snapshot()` 内联逻辑的取模倒计时语义，不改 TradingView 固定时间偏移处理。
- **`latest_snapshot()` 复用统一入口**：`_latest_snapshot_inner()` 构造头部临时 `KlineBar(closed=True)` 后，不再内联 import/调用 `seconds_until_bar_closes()`，而是调用 `self.has_forming_bar_at_head([bar], self._timeframe)`，再按返回值写回 `closed=not still_forming`。输出 `KlineBar` 结构与既有行为保持一致。
- **扩展 `tests/unit/test_data_source_forming_bar.py`**：新增 TradingView active head / boundary closed 两条 override 单测，以及一条 `_latest_snapshot_inner()` 无网络测试（stub `tvDatafeed.Interval` 和 `_fetch_hist_with_retry()`），证明 snapshot 构建链路确实复用 override，并把 override 返回的 forming 状态写回头部 `closed`。

### 验证

- `py_compile` 通过（`tradingview.py`、`test_data_source_forming_bar.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py tests/unit/test_data_source_factory.py --tb=line -q -p no:cacheprovider` → **35 passed**。
- `py -3.12 -m ruff check tests/unit/test_data_source_forming_bar.py` → **All checks passed**。
- `tradingview.py` 全文件 ruff 仍存在既有 RUF/I001 基线告警（中文标点、旧 `noqa`、旧 import 排序等），本轮未做大文件顺手清理；新增 override 与调用迁移已通过编译和目标测试覆盖。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十六轮：继续 M7，下沉 A 股数据源 forming 判定 override）

本轮继续推进 **M7：统一 forming bar 判定**。第四十五轮已在 `DataSource` ABC 上建立默认 `has_forming_bar_at_head(...)` 入口，并让 snapshot 构建优先调用数据源方法。本轮核查各数据源后，发现 A 股源存在一个必须由数据源自身表达的语义差异：`EastMoneySource` 的日线头部在 A 股交易日午休期间仍应视为 live/forming（`ashare_head_bar_live("1d")` 使用 09:30-15:00 trading day），而 `AkShareSource` 现有 `latest_snapshot()` 只在连续交易时段把头部标为未收盘（午休不 live）。通用 helper 无法同时表达这两个差异，因此本轮把两者各自的 live-head 规则下沉为 override。

### 代码清理

- **`EastMoneySource.has_forming_bar_at_head(...)` override**：空列表或头部 `closed=True` 直接返回 `False`；否则把 `now_ms` 转为 Asia/Shanghai 时间，并调用 `_ashare_head_bar_live(timeframe or self._timeframe, now)`。这保留 EastMoney 日线在午休期间仍 live 的既有 `latest_snapshot()` 语义，避免第四十五轮 GUI 传入 `data_source` 后被通用 A 股 helper 误判为 closed。
- **`AkShareSource.has_forming_bar_at_head(...)` override**：空列表或头部 `closed=True` 直接返回 `False`；否则按 `_ashare_session_open(now)` 判定。该规则与 AkShare 当前 `latest_snapshot()` 中 `row["closed"] = not (i == 0 and _ashare_session_open())` 保持一致，不把午休日线视为 live。
- **扩展 `tests/unit/test_data_source_forming_bar.py`**：新增 EastMoney 日线午休仍 forming、AkShare 日线午休不 forming 两个确定性测试，显式锁住两个数据源的 session 语义差异。

### 验证

- `py_compile` 通过（`eastmoney_source.py`、`akshare_source.py`、`test_data_source_forming_bar.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py --tb=line -q -p no:cacheprovider` → **24 passed**。
- `py -3.12 -m ruff check tests/unit/test_data_source_forming_bar.py` → **All checks passed**。
- `akshare_source.py` / `eastmoney_source.py` 全文件 ruff 仍存在既有 RUF/SIM/I001 基线告警（中文标点、旧 import 排序、旧 SIM 分支等），本轮未做大文件顺手清理；新增 override 行未触发新的源文件告警。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十五轮：启动 M7，统一 forming bar 判定入口）

本轮启动后端审查报告 §5.2 的 **M7：统一 forming bar 判定**。此前 `DataSource` ABC 只约定 `latest_snapshot()` 返回 newest-first K 线，forming-bar 是否存在由各数据源自行设置 `KlineBar.closed`，而 `snapshot.py` 直接散用 `bar_close_wait.has_forming_bar_at_head()`。这让后续为特定交易所/数据源处理 session、server time、停牌或周末 stale tick 时缺少统一覆写点。本轮第一刀不改变 `KlineBar.closed` 含义，也不改各数据源产出；先在 ABC 上提供默认判定入口，并把 GUI snapshot 构建迁移到该入口。

### 代码清理

- **`DataSource` ABC 新增 `has_forming_bar_at_head(...) -> bool` 默认方法**：参数接收 newest-first bars、`timeframe`、`now_ms`、`symbol`，默认委托 `bar_close_wait.has_forming_bar_at_head()`。当调用方未显式传入 `now_ms` 时，通过 `reference_now_ms(data_source=self)` 优先复用数据源可提供的 broker/server time，继续保留 stale `closed=False` bar 在周期结束后视为已收盘的既有语义。各具体数据源以后可 override 该方法承接交易所/session 特例。
- **`snapshot.py` 统一 forming-bar 调用入口**：新增内部 `_head_is_forming(...)`，优先调用传入 `data_source.has_forming_bar_at_head(...)`，缺省时回退原 helper；`take_snapshot_from_bars()`、`build_display_frame()`、`build_live_frame()`、`build_analysis_frame()` 和 `_newest_closed_slice()` 均新增兼容性可选参数 `data_source`，旧调用不受影响。
- **GUI 图表/分析快照传入当前数据源**：`MainWindow._build_chart_frame_from_bars()` 在已有 `now_ms = self._reference_now_ms()` 的基础上，把 `self._ctx.data_source` 传给 `build_live_frame()` / `build_display_frame()`，使实时图和分析图都进入 ABC 统一判定入口。
- **新增 `tests/unit/test_data_source_forming_bar.py`**：覆盖 ABC 默认方法与共享 helper 的等价性、活动 intraday bar 仍判定为 forming、以及 `build_analysis_frame(..., data_source=...)` 会尊重子类 override。

### 验证

- `py_compile` 通过（`base.py`、`snapshot.py`、`main_window.py`、`test_data_source_forming_bar.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_data_source_forming_bar.py tests/unit/test_bar_close_wait.py tests/unit/test_snapshot_closed_only_buffer.py tests/unit/test_build_analysis_frame.py tests/unit/test_snapshot_indicator_warmup.py --tb=line -q -p no:cacheprovider` → **22 passed**。
- `py -3.12 -m ruff check pa_agent/data/base.py pa_agent/data/snapshot.py tests/unit/test_data_source_forming_bar.py` → **All checks passed**。
- `pa_agent/gui/main_window.py` 全文件 ruff 基线仍存在大量既有 RUF/SIM/I001 告警，本轮未做大文件顺手清理；本轮对该文件仅新增 `data_source` 变量并作为关键字参数传入 snapshot 构建函数，已通过 `py_compile` 与目标测试覆盖。
- `git diff --check` 通过；仅提示 Windows 工作树 LF/CRLF 规范化 warning，无 whitespace error。

---

## [Unreleased] — 2026-07-15（第四十四轮：继续 M5，下沉 provider fallback 共享尾部到 ProviderSyncService）

本轮继续推进 **M5：提取 `ProviderSyncService`**。第四十三轮已把启动期 QClaw / WorkBuddy / Cursor provider 同步编排从 `AppContext.bootstrap()` 下沉到 `ProviderSyncService.sync_on_load()`；本轮处理 M5 的另一半职责——`TwoStageOrchestrator._finish_provider_fallback()` 中的 provider fallback 共享尾部。三个 per-provider 包装器（`_try_workbuddy_fallback` / `_try_cursor_fallback` / `_try_qclaw_fallback`）继续保留 call-time connector import、route guard 与 `apply_*_provider_to_settings()` 调用，确保测试 patch 点与尝试顺序不变；成功 apply 之后的通用副作用（`update_provider`、`save_settings`、`update_api_key`、`pending_writer.set_api_key`、切换日志）统一委托服务层执行。

### 代码清理

- **`ProviderSyncService` 新增 `finish_provider_fallback(...) -> bool`**：参数接收 `provider_name`、`err`、`settings`、`client`、`pending_writer`、`logger`，按原 `_finish_provider_fallback` 顺序执行：`err` 非空时 warning 并返回 `False`；否则 `client.update_provider(settings.provider)`；读取新 `settings.provider.api_key`；best-effort `save_settings(settings, save_path)` + `update_api_key(new_key)`；保存失败时 warning 但继续；若 writer 有 `set_api_key` 则同步新 key；最后记录 `"%s auto-fallback: model=%s base_url=%s"` 并返回 `True`。服务保持不负责 connector guard/apply，避免破坏现有 fallback patch 点。
- **`TwoStageOrchestrator._finish_provider_fallback()` 改为兼容 wrapper**：方法签名和三个 `_try_*_fallback` 调用点保持不变，仅构造 `ProviderSyncService(save_path=SETTINGS_JSON_PATH).finish_provider_fallback(...)` 并传入 `self._settings`、`self._client`、`self._pending_writer` 与模块 logger。`_stream_chat_resilient` 的 WorkBuddy → Cursor → QClaw 尝试顺序、`tried_*` 标志、网络错误判定均不变。
- **扩展 `tests/unit/test_provider_sync_service.py`**：在原启动同步顺序测试之外，新增 fallback 尾部成功路径、`err` 提前返回、保存失败仍同步 writer、writer 无 `set_api_key` 四类测试。

### 验证

- `py_compile` 通过（`provider_sync_service.py`、`two_stage.py`、`test_provider_sync_service.py`，EXIT=0）。
- `py -3.12 -m pytest tests/unit/test_provider_sync_service.py tests/unit/test_qclaw_auto_fallback.py --tb=line -q -p no:cacheprovider` → **8 passed**。
- ruff 对比基线：HEAD 的 `provider_sync_service.py` + `two_stage.py` + 既有测试，与拆分后三文件均为 `E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`，逐类别 Counter 完全一致，**零净新增告警**。
- diff 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）仅命中 `api_key` / `set_api_key` / `update_api_key` 标识符与测试假值 `new-key`，无真实明文密钥。

---

## [Unreleased] — 2026-07-15（第四十三轮：启动 M5，提取 ProviderSyncService 启动期 provider 同步）

本轮启动后端审查报告 §5.2 的 **M5：提取 `ProviderSyncService`**。M5 目标是把 QClaw / WorkBuddy / Cursor provider 同步与持久化职责从 `AppContext.bootstrap()` 与 `TwoStageOrchestrator` 中下沉。第一刀先切启动期路径：`AppContext.bootstrap()` 原本直接 import 并顺序调用 `sync_qclaw_agent_provider_on_load()`、`sync_workbuddy_provider_on_load()`、`sync_cursor_provider_on_load()`，这让依赖容器承担了特殊 provider 同步编排职责。本轮新增薄服务集中这段顺序编排；各 connector 仍保留自身的 route 检测、provider mutation、`save_settings` 持久化与日志逻辑，避免一次性触碰自动降级 fallback 尾部。

### 代码清理

- **新增 `pa_agent/ai/provider_sync_service.py`**：提供 `ProviderSyncService(save_path=...)` 与便利函数 `sync_providers_on_load(settings, save_path=...)`。`sync_on_load()` 内以既有顺序调用 QClaw → WorkBuddy → Cursor 三个 connector 的 `sync_*_provider_on_load()`，并透传同一个 `save_path`。服务本身不判断 route、不写 settings、不更新日志，只负责把启动期特殊 provider 同步编排从 AppContext 中抽离。
- **`pa_agent/app_context.py` 简化启动期 provider 同步**：删除 `bootstrap()` 内三个 connector 直接 import 与三次调用，替换为 `from pa_agent.ai.provider_sync_service import sync_providers_on_load` + `sync_providers_on_load(settings, save_path=SETTINGS_JSON_PATH)`。设置加载、后续 `configure_logging(api_key=settings.provider.api_key)`、AI client 创建、PendingWriter 初始 `api_key` 注入等逻辑保持不变。
- **新增 `tests/unit/test_provider_sync_service.py`**：用 monkeypatch 验证 `ProviderSyncService.sync_on_load()` 按 QClaw → WorkBuddy → Cursor 顺序调用，并向三者传入同一 `settings` 对象与 `save_path`。

### 验证

- `py_compile` 通过（`provider_sync_service.py`、`app_context.py`、`test_provider_sync_service.py`，EXIT=0）。
- import 核验通过：`ProviderSyncService`、`sync_providers_on_load`、`AppContext` 均可正常 import。
- `pytest tests/unit/test_provider_sync_service.py --tb=line -q -p no:cacheprovider` → **1 passed**。
- 新增文件 ruff 通过：`ruff check pa_agent/ai/provider_sync_service.py tests/unit/test_provider_sync_service.py` → **All checks passed**。
- app_context 相关 ruff 对比：HEAD `app_context.py` 为 `I001:2, RUF100:1, UP037:1`；拆分后 `app_context.py` + 新服务 + 新测试为 `I001:1, RUF100:1, UP037:1`，**零净新增告警**，并减少 1 条既有 I001。
- staged diff 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）仅命中 `configure_logging(api_key=settings.provider.api_key)` 标识符引用，无明文密钥。

---

## [Unreleased] — 2026-07-15（第四十二轮：继续拆分 PromptAssembler，提取 Stage2PromptBuilder）

本轮继续推进后端审查报告 §5.2 的 **M1：拆分 `PromptAssembler`**。第四十一轮已提取 `Stage1PromptBuilder`，本轮切剩余的 Stage 2 builder 主体：独立阶段二请求、前缀链 continuation 请求、以及 Stage 2 user prompt 渲染。`PromptAssembler` 继续保留对外 `build_stage2()` / `build_stage2_continuation()` / `stage2_system_prompt_only()` API、进程级系统 prompt 缓存、以及既有私有 wrapper 名称，避免影响 orchestrator、测试和工具调用点。新模块通过构造参数接收 system prompt 构建函数、txt 加载函数、策略文件列表函数、预测说明/输出契约常量、Stage 2 guidance/experience/carryover/market-feature/K 线表渲染 callable，避免反向 import `prompt_assembler.py` 形成循环依赖。

### 代码清理

- **新增 `pa_agent/ai/stage2_prompt_builder.py`**：提供 `Stage2PromptBuilder`，负责 `build_stage2()`、`build_stage2_continuation()`、`build_stage2_user_prompt()` 三类 Stage 2 构建职责。原 `_build_stage2_user_prompt()` 中的 stance guidance、continuity block、trend conflict/transition/planned-limit guidance、strategy txt 加载、experience 渲染、next-bar/next-cycle 指令、prefix-chain kline 省略逻辑、breakout tick hint、previous prediction block、compact Stage 1 JSON、Stage 2 tail reminder 均整体迁入。
- **`pa_agent/ai/prompt_assembler.py` 改为 Stage 2 薄包装**：新增 `_stage2_prompt_builder()` 工厂，`build_stage2()` / `build_stage2_continuation()` / `_build_stage2_user_prompt()` 仅委托 `Stage2PromptBuilder`；`stage2_system_prompt_only()` 保持原实现，继续返回共享 system prompt。随依赖下沉，`prompt_assembler.py` 不再直接 import `json`、`build_decision_stance_guidance`、`normalize_stance`，Stage 2 相关复杂依赖收束到新模块。`prompt_assembler.py` 从 1398 行降至 1275 行，`PromptAssembler` 类体从 507 行降至 385 行，新模块 293 行。

### 验证

- `py_compile` 通过（`prompt_assembler.py`、`stage2_prompt_builder.py`，EXIT=0）。
- import 核验通过：`PromptAssembler` 与 `Stage2PromptBuilder` 均可正常 import。
- AST 结构核验：`prompt_assembler.py` 现 1275 行，`PromptAssembler` 跨 890-1275 行（385 行）；`stage2_prompt_builder.py` 现 293 行，含 `Stage2PromptBuilder`（20-293）。
- `pytest tests/unit/test_prompt_assembler.py --tb=line -q -p no:cacheprovider` → **31 passed**。
- `ruff check` 对比基线：HEAD 的 `prompt_assembler.py` + `stage1_prompt_builder.py` 与拆分后三文件（再加 `stage2_prompt_builder.py`）均为 `RUF001:1270, RUF003:2, RUF100:1`，逐类别 Counter 完全一致，**零净新增告警**。
- staged diff 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中。

---

## [Unreleased] — 2026-07-15（第四十一轮：继续拆分 PromptAssembler，提取 Stage1PromptBuilder）

本轮转入后端审查报告 §5.2 的 **M1：拆分 `PromptAssembler`** 后续阶段。此前 M1 已完成 KlineTableRenderer、ExperienceRenderer、Stage 2 guidance、chain context、program prefill hint 五个叶子簇；`prompt_assembler.py` 中仍保留 Stage 1 user prompt 三个大方法（全量阶段一、增量阶段一、增量 continuation）以及 market-features 包装。R41 将这些 Stage 1 user-turn 构建职责下沉到新模块 `stage1_prompt_builder.py`，`PromptAssembler` 继续保留对外 `build_stage1()` / `build_incremental_stage1()` API、系统 prompt 缓存、Stage 2 构建与兼容性薄包装。此切口避免一次性改动 Stage 2 大 prompt，同时兑现 AGENTS 中“market-feature 包装待切 Stage1/Stage2PromptBuilder 时处理”的约定。

### 代码清理

- **新增 `pa_agent/ai/stage1_prompt_builder.py`**：提供 `Stage1PromptBuilder`，负责构建三类 Stage 1 user prompt：`build_stage1_user_prompt()`、`build_incremental_stage1_user_prompt()`、`build_incremental_stage1_continuation_user_prompt()`；同时迁入 `render_simple_market_features_block()` / `inject_market_features_block()` 两个 market-feature 包装函数。新 builder 通过构造参数接收 `load`、prompt settings、Stage 1 txt 文件列表、输出提醒函数、尾部提醒/增量硬规则/market-feature authority note 以及 K 线表/预填提示渲染 callable，避免新模块 import `prompt_assembler.py` 造成循环依赖。
- **`pa_agent/ai/prompt_assembler.py` 改为薄包装调用**：移除 Stage 1 user prompt 三个大方法体和直接 `pattern_routing` / `market_features` import，新增 `_stage1_prompt_builder()` 工厂；`_build_stage1_user_prompt()`、`_build_incremental_stage1_user_prompt()`、`_build_incremental_stage1_continuation_user_prompt()` 仅委托 `Stage1PromptBuilder`。`_render_simple_market_features_block` / `_inject_market_features_block` 继续以 staticmethod 形式绑定到 `PromptAssembler` 类体，保持私有兼容入口；`build_incremental_stage1()` 的四消息链编排逻辑暂留 `PromptAssembler`。`prompt_assembler.py` 从 1570 行降至 1398 行，新模块 288 行。

### 验证

- `py_compile` 通过（`prompt_assembler.py`、`stage1_prompt_builder.py`，EXIT=0）。
- import 核验通过：`PromptAssembler` 与 `Stage1PromptBuilder` 均可正常 import。
- AST 结构核验：`PromptAssembler` 类体从 675 行降至 507 行；`stage1_prompt_builder.py` 含 2 个模块函数与 `Stage1PromptBuilder`（52-288）。
- `pytest tests/unit/test_prompt_assembler.py --tb=line -q -p no:cacheprovider` → **31 passed**。
- `ruff check` 对比基线：HEAD 单文件 `prompt_assembler.py` 为 `I001:1, RUF001:1270, RUF003:2, RUF100:1`；拆分后 `prompt_assembler.py` + `stage1_prompt_builder.py` 为 `RUF001:1270, RUF003:2, RUF100:1`，**零净新增告警**，并随 import 清理减少 1 条既有 I001。
- staged diff 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中。

---

## [Unreleased] — 2026-07-15（第四十轮：继续拆分 JsonValidator，提取 schema_validator 结构校验器）

本轮回到后端审查报告 §5.2 的 **M2：拆分 `JsonValidator`**。此前第十六轮已将 JSON 文本提取/修复函数拆出至 `json_repair.py`，第二十八轮已将 Stage 2 业务规则跨字段校验簇拆出至 `business_rules.py`；本轮继续切第三块——**JSON Schema 结构校验层**。该层位于 `JsonValidator.validate()` 的 normalizer 之后、显式跨字段检查之前，职责是调用 `jsonschema.Draft7Validator(schema).iter_errors(obj)`，并把 schema 错误归类为 `missing_fields`、`invalid_fields`、`allowed_values`、首个 validator 与首条错误消息。为避免新模块反向 import `json_validator.py` 产生循环依赖，本轮不把 `ValidationError` 结果类型迁出，而是新建轻量结果 `SchemaValidationResult`；`JsonValidator` 继续负责最终 category 判定和 `ValidationError` 组装，业务一致性检查、normalizer 与 `business_rules` 调用保持原位。

### 代码清理

- **新增 `pa_agent/ai/schema_validator.py`**：提供 `SchemaValidationResult` dataclass 与 `collect_schema_errors(obj, schema) -> SchemaValidationResult | None`。新模块仅依赖 stdlib `logging`/`dataclasses`/`typing`，`jsonschema` 仍为函数体内 import；若本地未安装 `jsonschema`，保持原行为 `logger.warning("jsonschema not installed; skipping schema validation")` 并返回 `None`，由 `JsonValidator.validate()` 继续 `return Ok(obj=obj)`。
- **`pa_agent/ai/json_validator.py` 改为委托 schema 结构校验**：删除 `validate()` 内直接 import `jsonschema`、收集 `errors`、分类 missing/invalid/allowed 的内联代码，替换为 `schema_result = collect_schema_errors(obj, schema)`；随后复制 `schema_result.missing_fields` / `invalid_fields` / `allowed_values` 供后续 Stage 1/Stage 2 显式检查继续追加。最终 `Ok` 判定、category 判定与 `ValidationError(message=f"{schema_result.error_count} schema error(s): ...")` 语义保持一致。`json_validator.py` 从 415 行降至 405 行，新模块 61 行。

### 验证

- `py_compile` 通过（`schema_validator.py`、`json_validator.py`，EXIT=0）。
- import 核验通过：`collect_schema_errors` 可调用，`JsonValidator.validate` 仍存在。
- AST 结构核验：`json_validator.py` 现 405 行，`JsonValidator` 跨 81-405 行；`schema_validator.py` 现 61 行，含 `SchemaValidationResult`（18-30）与 `collect_schema_errors`（33-61）。
- `ruff check` 对比基线：HEAD 单文件 `json_validator.py` 与拆分后 `json_validator.py` + `schema_validator.py` 均为 **2 条 I001**，逐类别 Counter 完全一致，**零净新增告警**。
- schema 分类直接断言通过：required 缺失 + enum 非法样例输出 `missing=['a']`、`invalid=['b']`、`allowed={'b': ['x', 'y']}`、`error_count=2`。
- focused 单测通过：`pytest tests/unit/test_json_validator.py -k "next_bar_prediction or invalid_fields_prefix"` → **5 passed**。
- `tests/property/test_json_validator_categories.py` 仍为 **3 failed**；经 `git stash` 回到 HEAD 复跑确认三项失败完全一致，均为既有基线（`test_no_order_with_non_null_price_is_category_c` 与两项截断 Stage 1 修复断言），非本轮引入。
- staged diff 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中。

---

## [Unreleased] — 2026-07-15（第三十九轮：完成 TwoStageOrchestrator.submit() 第六刀，提取 _run_stage1 收官 M4）

本轮为**大文件拆分 M4 的第六刀 / 收官刀**（第三十八轮第五刀已切 `_run_stage2`，`submit()` 从 538 行降至 334 行），完成 roadmap §5.2 中 `TwoStageOrchestrator.submit()` 的四个目标拆分：`_route_and_load_experience`、`_persist_result`、`_run_stage2`、`_run_stage1` 均已落位。与 `_run_stage2` 不同，Stage 1 的 happy path 不能直接返回最终记录，而必须继续进入 Steps 10-24；因此 `_run_stage1` 设计为返回 **终局 `AnalysisRecord` 或成功元组**：网络错误、调用后取消、校验失败三条终局路径返回 partial record；校验通过路径返回 `(stage1_json, messages_s1, reply_s1, s1_usage_calls, _thinking, _effort)`，由 `submit()` 判断 `isinstance(_s1, AnalysisRecord)` 后继续解包。Stage 1 两组 `nonlocal` 流式闭包（`_on_s1_reasoning`/`_on_s1_content` 与 retry 闭包 `_call_s1_retry`）随方法整体搬迁，Steps 3-9 主体经 anchored block 对比确认与拆分前逐字节一致。至此 `submit()` 已从 M4 起点约 647 行降至 151 行，保留 Steps 1-2 / 2.5 的入口守卫和后续阶段方法编排。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增实例方法 `_run_stage1(self, *, record, on_event, on_stage_prompt, on_stage1_reasoning, on_stage1_content, cancel_token, frame, previous_record, incremental_new_bar_count) -> AnalysisRecord | tuple[dict, list[dict], Any, list[Any], bool, str]`**：把 `submit()` 内 Steps 3-9（Stage 1 started、analysis mode 解析、Stage 1 prompt 组装、Stage 1 模型调用、调用后取消检查、Stage 1 校验与 retry、Stage1Done 事件）整体搬迁为独立方法。网络错误终局仍执行 `save_partial(record, "network_error")` + `Stage1Failed`；调用后取消终局仍执行 `save_partial(record, "user_cancelled")` + `Cancelled`；校验失败终局仍执行 `save_partial(record, f"stage1_{err.category}")` + `Stage1Failed`；happy path 返回 Stage 2 所需的 Stage 1 成功上下文。
- **`submit()` 内 Steps 3-9 替换为 `_run_stage1` 调用与分派**：`_s1 = self._run_stage1(...)` 后，若 `_s1` 是 `AnalysisRecord` 则直接返回；否则解包出 `stage1_json, messages_s1, reply_s1, s1_usage_calls, _thinking, _effort` 继续 Step 10-24。`submit()` 从 334 行降至 151 行，M4 收官后成为薄编排层。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `TwoStageOrchestrator` 类体已含 `_run_stage1` 方法，`_run_stage1` 跨 805-1027 行（222 行），`submit()` 现跨 1031-1182 行（151 行）。
- **逐字节搬迁核验**：从 HEAD（第三十八轮文档同步后）提取 `submit()` 内 Steps 3-9 的 198 行主体，与工作区 `_run_stage1` 内对应主体 anchored block 对比，结果 `BYTE-IDENTICAL: True`。
- **集成测试基线对比**：核心 submit-path 套件（`test_gate_shortcircuit` + `test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`（**Stage 1 语法失败终局专项**）/`_stage1_missing_field`（**Stage 1 缺字段终局专项**）/`_stage2_invalid_value`/`_network_timeout`（覆盖 Stage 1/2 网络错误终局）/`_user_cancel`（覆盖取消终局）+ `test_decision_nodes_orchestrator`）**13 passed / 1 failed**，进度串 `..F...........`。唯一失败 `test_no_order_with_non_null_price_fails_stage2` 仍为**既有失败**（该测试用不含业务规则的 `schema_test_validator()`，与第三十四~三十八轮记录一致）。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**，逐类别 Counter 完全一致（`E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无真实密钥命中——仅 `cancel_token` / token 计数字段等代码标识符。

---

## [Unreleased] — 2026-07-15（第三十八轮：完成 TwoStageOrchestrator.submit() 第五刀，提取 _run_stage2 收官 Stage 2 拆解）

本轮为**大文件拆分 M4 的第五刀**（第三十七轮第四刀已切纯函数 `_build_stage2_messages`，`submit()` 从 552 行降至 538 行），**完成 Stage 2 区的整体拆解**。前四刀已把 Stage 2 的**闸门短路终局**（第三刀 `_try_gate_short_circuit`）与**纯函数 prompt 组装**（第四刀 `_build_stage2_messages`）分别外提，Stage 2 区仅余最难的**含闭包调用/校验核心**（Steps 15-24）。第三十六轮曾评估此块「须引入新控制流信号类型、风险过高」而暂缓；但第三十五轮 `_persist_result` 外提后，该结论已**不再成立**——Steps 15-24 的**全部四条路径都返回 `AnalysisRecord`**（网络错误终局、调用后取消终局、校验失败终局三终局 + happy-path 委托 `_persist_result`），故整块可干净外提为 `_run_stage2 -> AnalysisRecord`，`submit()` 尾部以 `return self._run_stage2(...)` **尾调**，**无需任何新类型**。两组 `nonlocal` 流式闭包（`_on_s2_reasoning`/`_on_s2_content` 共享 `s2_streamed_*` 标志、retry 闭包 `_call_s2_retry`）随方法**整体搬迁**、闭包捕获关系不变；in-body 形参名保持与原局部逐字一致（`_enable_next_bar`/`_flip_cooldown`/`_thinking`/`_effort`），使方法体逐字节等价。至此 `submit()` 仅余 Steps 1-14（Stage 1 全流程 + 路由/经验加载 + 闸门守卫 + Stage 2 prompt 组装），Stage 2 调用/校验/落盘已全部下沉。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增实例方法 `_run_stage2(self, *, record, on_event, on_stage_prompt, on_stage2_reasoning, on_stage2_content, cancel_token, frame, messages_s1, reply_s1, stage1_json, strategy_files, experience_entries, messages_s2, previous_record, _enable_next_bar, _flip_cooldown, _thinking, _effort, s1_usage_calls) -> AnalysisRecord`**：把 `submit()` 内 Steps 15-24（`# ── Step 15: Call AI for Stage 2`→happy-path `return self._persist_result(...)`）**逐字节搬迁**为独立方法，放在 `_build_stage2_messages` 之后、`# ── Public API ──` 分隔线之前。逻辑完全不变：Stage 2 prompt DEBUG 日志与 `on_stage_prompt("stage2", ...)` 通知、两组 `nonlocal` 流式闭包 `_on_s2_reasoning`/`_on_s2_content`（共享 `s2_streamed_reasoning`/`s2_streamed_content`）、`self._stream_chat_resilient(...)` 弹性调用、网络错误终局（`_is_network_error`→`model_copy`→`save_partial("network_error")`→`Stage2Failed`→`return record`）、buffered-stream 兜底、Step 16 调用后取消终局（`model_copy`→`save_partial("user_cancelled")`→`Cancelled`→`return record`）、Step 17 校验（Stage 2 响应 DEBUG 日志、`_call_s2_retry` retry 闭包 + `s2_usage_calls` 累积、`validate_with_retry(...)`、校验失败终局 `model_copy`→`save_partial(f"stage2_{err.category}")`→`Stage2Failed`→`return record`）、`assert isinstance(result_s2, Ok)` 后 `stage2_json` 取值与 `not _enable_next_bar` 时 `deepcopy`+`pop("next_bar_prediction")`、Step 19 `Stage2Done` 事件，末尾 happy-path `return self._persist_result(...)`。
- **`submit()` 内 Steps 15-24 替换为单次尾调**：`return self._run_stage2(record=..., on_event=..., on_stage_prompt=..., on_stage2_reasoning=..., on_stage2_content=..., cancel_token=..., frame=..., messages_s1=..., reply_s1=..., stage1_json=..., strategy_files=..., experience_entries=..., messages_s2=..., previous_record=..., _enable_next_bar=..., _flip_cooldown=..., _thinking=..., _effort=..., s1_usage_calls=...)`，紧跟 Step 14 `_build_stage2_messages` 三元解包之后。`submit()` 从 538 行降至 334 行。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `TwoStageOrchestrator` 类体已含 `_run_stage2` 方法，`_run_stage2` 跨 545-803 行（258 行），`submit()` 现跨 807-1141 行（334 行）。
- **集成测试基线对比**：核心 submit-path 套件（`test_gate_shortcircuit` + `test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`/`_stage1_missing_field`/`_stage2_invalid_value`（**校验失败终局专项，本刀关键守护**）/`_network_timeout`（**网络错误终局专项**）/`_user_cancel`（**取消终局专项**）+ `test_decision_nodes_orchestrator`）**13 passed / 1 failed**，进度串 `..F...........`——三条 Stage 2 终局用例全过，验证网络错误/取消/校验失败三路径逐字节等价；唯一失败 `test_no_order_with_non_null_price_fails_stage2` 为**既有失败**（该测试用不含业务规则的 `schema_test_validator()`，与第三十四~三十七轮记录一致）。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**，逐类别 Counter 完全一致（`E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中——纯结构搬迁。

---

## [Unreleased] — 2026-07-15（第三十七轮：继续拆分 TwoStageOrchestrator.submit() 第四刀，提取 _build_stage2_messages 阶段二 prompt 组装）

本轮为**大文件拆分 M4 的第四刀**（第三十六轮第三刀已切 `_try_gate_short_circuit`，`submit()` 从 575 行降至 552 行）。M4 剩余的 `_run_stage2` 主体（Steps 14-19）内，闸门短路终局已于上一轮外提；本轮继续剥离其中**纯函数片段** Step 14（阶段二 prompt 组装）。该段结构与第一刀 `_route_and_load_experience` 同构——**无闭包、无 early-return、无副作用**：先从 `self._settings.general` 解析两个 settings 标志（`enable_next_bar_prediction` → `_enable_next_bar`、`structure_flip_cooldown_bars` → `_flip_cooldown`，均带 `getattr` 兜底），再调 `self._assembler.build_stage2_continuation(...)` 组装 `messages_s2`。因 `_enable_next_bar`/`_flip_cooldown` 在后续 Step 17（校验 `validate_kwargs`）、Step 18（`stage2_json.pop("next_bar_prediction")`）、Step 19.5（`_persist_result` 的预测日志）均被复用，方法返回 `(messages_s2, enable_next_bar, flip_cooldown)` 三元组，`submit()` 内以三元解包接收。剥离本段后，Stage 2 区仅余不可再分的**含闭包调用/校验核心**（Steps 15-18 的两组 `nonlocal` 流式闭包 `_on_s2_reasoning`/`_on_s2_content`/`_call_s2_retry` + 网络错误/取消/校验失败三终局），留待后续轮次处理。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增纯实例方法 `_build_stage2_messages(self, *, frame, messages_s1, reply_s1, stage1_json, strategy_files, experience_entries, record, previous_record) -> tuple[list[dict], bool, int]`**：把 `submit()` 内 Step 14（`_enable_next_bar`/`_flip_cooldown` 两 settings 标志解析 + `build_stage2_continuation` 组装）**逐字节搬迁**为独立方法，放在 `_try_gate_short_circuit` 之后、`# ── Public API ──` 分隔线之前。逻辑完全不变：`bool(getattr(getattr(self._settings, "general", None), "enable_next_bar_prediction", False))`、`int(getattr(..., "structure_flip_cooldown_bars", 3) or 3)`、`build_stage2_continuation(frame/stage1_messages/stage1_reply_content/stage1_json/strategy_files/experience_entries/decision_stance/previous_record/enable_next_bar_prediction/provider_settings/structure_flip_cooldown_bars=...)`，末尾 `return messages_s2, enable_next_bar, flip_cooldown`。
- **`submit()` 内 Step 14 块替换为三元解包调用**：`messages_s2, _enable_next_bar, _flip_cooldown = self._build_stage2_messages(frame=..., messages_s1=..., reply_s1=..., stage1_json=..., strategy_files=..., experience_entries=..., record=..., previous_record=...)`，紧跟 Step 13 闸门守卫之后。`submit()` 从 552 行降至 538 行。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `TwoStageOrchestrator` 类体已含 `_build_stage2_messages` 方法，`submit()` 现跨 547-1084 行（538 行）。
- **集成测试基线对比**：核心 submit-path 套件（`test_gate_shortcircuit` + `test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`/`_stage1_missing_field`/`_stage2_invalid_value`/`_network_timeout`/`_user_cancel` + `test_decision_nodes_orchestrator`）**13 passed / 1 failed**，进度串 `..F...........`——唯一失败 `test_no_order_with_non_null_price_fails_stage2` 为**既有失败**（该测试用不含业务规则的 `schema_test_validator()`，与第三十四/三十五/三十六轮记录一致），拆分前后行为逐字节一致。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**，逐类别 Counter 完全一致（`E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中——纯结构搬迁。

---

## [Unreleased] — 2026-07-15（第三十六轮：继续拆分 TwoStageOrchestrator.submit() 第三刀，提取 _try_gate_short_circuit 闸门短路终局）

本轮为**大文件拆分 M4 的第三刀**（第三十五轮第二刀已切 `_persist_result`，`submit()` 从约 601 行降至 575 行）。roadmap（`docs/backend_review_report.md` §5 L262）M4 剩余目标原列为 `_run_stage1`（Steps 3-9）与 `_run_stage2`（Steps 12-19）两大块。核查 `submit()` 现状后**细化了拆分粒度**：`_run_stage2`（Steps 12-19）经通读发现内含**五处 `return record` early-return 终局**（Step 12 取消检查、Step 13 闸门短路、Step 15 网络错误、Step 16 取消检查、Step 17 校验失败）与**两组 `nonlocal` 流式闭包**（`_on_s2_reasoning`/`_on_s2_content` 及 retry 内的 `_call_s2_retry`），整块一次性外提约 284 行、且须引入新的控制流信号类型，违背用户的**原子提交**偏好、风险过高。因此本轮改切其中**最自足的单一终局分支**——Step 13 的闸门短路块（`gate_result ∈ {wait, unknown}` 时程序本地合成阶段二结果、不调模型、落盘返回）：它是「计算 → `save_full` → `RecordSaved` → `return record`」的单出口块，**无闭包、无 `nonlocal`**，结构与第二刀 `_persist_result` 同构。外提为返回 `AnalysisRecord | None` 的守卫方法（返回 `None` 表示闸门放行、`submit()` 继续 Step 14 正常流程），**不引入任何新类型**，保持提交原子、低风险。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增实例方法 `_try_gate_short_circuit(self, *, record, on_event, on_stage_prompt, on_stage2_content, stage1_json, messages_s1, reply_s1, strategy_files, experience_entries) -> AnalysisRecord | None`**：把 `submit()` 内 Step 13 的 `gate_result in ("wait", "unknown")` 分支**逐字节搬迁**为独立方法，放在 `_persist_result` 之后、`# ── Public API ──` 分隔线之前。逻辑完全不变：`gate_result` 小写归一化后若不属于 `{wait, unknown}` 则 `return None`（放行）；否则局部 import `build_stage2_gate_wait_response`、`on_stage_prompt("stage2", "", "（阶段一闸门未通过…）")`、`_emit_buffered_stream(short_msg, on_stage2_content)`、`build_stage2_gate_wait_response(stage1_json)`、`Stage2Done` 事件、gate 短路专用 next_bar_prediction 日志、`_accumulate_usage(record.usage_total, reply_s1.usage)`、`record.model_copy(update={...含 stage2_messages=[]/stage2_response=None...})`、`save_full`、`RecordSaved`、`return record`。
- **`submit()` 内 Step 13 闸门块替换为守卫调用**：`Stage2Started` 事件 + `on_stage2_files` 回调之后，改为 `_gate_record = self._try_gate_short_circuit(record=..., on_event=..., on_stage_prompt=..., on_stage2_content=..., stage1_json=..., messages_s1=..., reply_s1=..., strategy_files=..., experience_entries=...)`，随后 `if _gate_record is not None: return _gate_record`。`submit()` 从 575 行降至 552 行。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `TwoStageOrchestrator` 类体已含 `_try_gate_short_circuit` 方法，`submit()` 现跨 499-1050 行（552 行）。
- **集成测试基线对比**：核心 submit-path 套件（`test_gate_shortcircuit`（**闸门短路专项，本刀关键守护**）+ `test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`/`_stage1_missing_field`/`_stage2_invalid_value`/`_network_timeout`/`_user_cancel` + `test_decision_nodes_orchestrator`）**13 passed / 1 failed**，进度串 `..F...........`——`test_gate_shortcircuit` 两条用例（居首 `..`）全过，验证闸门短路行为逐字节等价；唯一失败 `test_no_order_with_non_null_price_fails_stage2` 为**既有失败**（该测试用不含业务规则的 `schema_test_validator()`，与第三十四/三十五轮记录一致）。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**，逐类别 Counter 完全一致（`E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中——纯结构搬迁。

---

## [Unreleased] — 2026-07-15（第三十五轮：继续拆分 TwoStageOrchestrator.submit() 第二刀，提取 _persist_result 落盘尾段）

本轮为**大文件拆分 M4 的第二刀**（第三十四轮首刀已切 `_route_and_load_experience`，`submit()` 从约 647 行降至约 601 行）。与 M1/M2/M3 的**叶子模块提取**不同，M4 是**同类内的方法级拆分**：子方法共享 `self` 与跨阶段可变局部状态，无法用纯函数等价脚本验证，须靠既有 mock-based 集成测试套件做 baseline 对比。roadmap（`docs/backend_review_report.md` §5 L262）将 M4 目标拆为 `_run_stage1`/`_run_stage2`/`_route_and_load_experience`/`_persist_result`。本刀切**尾段** Steps 19.5-24（预测日志 + 构建 final record + `save_full` + `RecordSaved` 事件 + return）。选它作为 M4 第二刀的关键动机：① 它是 `_route_and_load_experience` 之后 `submit()` 中**最自足的一段**——纯只读聚合（读 `stage2_json`/`record`/两组 `usage_calls` 等已算好的状态）+ 单次落盘，**无 early-return 回流、无 `nonlocal` 闭包**（`submit()` 的所有中途失败/取消 early-return 都在本段之前，本段是 happy-path 的唯一终点）；② 它只被 `submit()` 尾部唯一调用点触达，`stage2_json`/`usage_total` 等中间局部只在段内与段末 return 使用，可完整封装；③ 因用 `self.*` 与 `on_event` 回调，自然拆为实例方法而非模块函数，`submit()` 内替换为单次 `return self._persist_result(...)` 关键字实参调用，行为逐字节一致。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增实例方法 `_persist_result(self, *, record, on_event, stage1_json, messages_s1, reply_s1, messages_s2, reply_s2, stage2_json, strategy_files, experience_entries, s1_usage_calls, s2_usage_calls, _enable_next_bar) -> AnalysisRecord`**：把 `submit()` 内 Steps 19.5-24（`# ── Step 19.5: Log next_bar_prediction`→`# ── Step 24: Return` 五块）**逐字节搬迁**为独立方法，放在 `_route_and_load_experience` 之后、`# ── Public API ──` 分隔线之前的辅助方法区。逻辑完全不变：next_bar_prediction 日志（feature 关闭/unpredictable/概率三分支/absent 兜底）、next_cycle_prediction 日志（unpredictable/正常/absent 三分支）、`usage_total` 双层 `_accumulate_usage_calls(s1_usage_calls)` 再叠 `s2_usage_calls`、`record.model_copy(update={...11 字段含 experience_loaded 的 model_dump/dict 分支...})`、`self._pending_writer.save_full(record)`、`on_event(OrchestratorEvent.RecordSaved)`、末尾 `return record`。全部经关键字实参传入，被搬迁的所有局部（`_pred`/`_nb_pred`/`_probs`/`_nc_pred`/`usage_total`）仍为方法内局部。
- **`submit()` 内 Steps 19.5-24 替换为单次调用**：`return self._persist_result(record=record, on_event=on_event, stage1_json=stage1_json, messages_s1=messages_s1, reply_s1=reply_s1, messages_s2=messages_s2, reply_s2=reply_s2, stage2_json=stage2_json, strategy_files=strategy_files, experience_entries=experience_entries, s1_usage_calls=s1_usage_calls, s2_usage_calls=s2_usage_calls, _enable_next_bar=_enable_next_bar)`，紧跟 `# ── Step 19: Stage 2 done`→`on_event(OrchestratorEvent.Stage2Done)` 之后。`submit()` 从约 601 行降至 575 行。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `TwoStageOrchestrator` 类体已含 `_persist_result` 与 `_route_and_load_experience` 两个方法，`submit()` 现跨 439-1013 行（575 行）。
- **集成测试基线对比**：核心 submit-path 套件（`test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`/`_stage1_missing_field`/`_stage2_invalid_value`/`_network_timeout`/`_user_cancel` + `test_gate_shortcircuit` + `test_decision_nodes_orchestrator`）**13 passed / 1 failed**，唯一失败 `test_no_order_with_non_null_price_fails_stage2` 经 `git stash` 回退 HEAD 复跑确认为**既有失败**（该测试用 `schema_test_validator()`，不含业务规则校验，故 order_type=不下单+entry_price=0 走到 happy path 而非 Stage2Failed，与第三十四轮记录一致）——拆分前后行为逐字节一致。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**，逐类别 Counter 完全一致（`E402:11, I001:1, RUF001:22, RUF100:1, UP037:5`），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`Bearer`/`password`/`token`）无命中——纯结构搬迁，无密钥泄漏。

---

## [Unreleased] — 2026-07-15（第三十四轮：启动 M4 里程碑，拆分 TwoStageOrchestrator.submit() 第一刀，提取 _route_and_load_experience）

本轮**开启大文件拆分 M4 里程碑**（M1 已完成对 `prompt_assembler.py` 的五刀叶子提取，1963→1571 行；本轮转向 `orchestrator/two_stage.py` 的巨型方法 `TwoStageOrchestrator.submit()`——约 647 行、跨阶段流转、含多处 `nonlocal` 闭包与 early-return）。与 M1/M2/M3 的**叶子模块提取**本质不同，M4 是**同类内的方法级拆分**：子方法共享 `self` 与大量跨阶段流转的可变局部状态，无法用纯函数等价脚本验证，必须靠既有 mock-based 集成测试套件做 baseline 对比。roadmap（`docs/backend_review_report.md` §5 L262）将 M4 目标拆为 `_run_stage1`/`_run_stage2`/`_route_and_load_experience`/`_persist_result`。本刀先切最干净的一块——Steps 10-11（路由策略文件 + 加载经验条目）。选它作为 M4 第一刀的关键动机：① 它是 `submit()` 中**唯一零闭包、零 early-return、零副作用的自足片段**——只读 `stage1_json` 与 `self._router`/`self._settings`/`self._exp_reader`，输出 `(strategy_files, experience_entries)`；② 其中间局部变量 `cycle_position`/`direction`/`patterns` 经核查**只在该块内被引用**（Step 12+ 仅用 `strategy_files`/`experience_entries`），故可完整封装、不外泄；③ 因用 `self.*`，自然拆为实例方法而非模块函数，`submit()` 内替换为单行解包调用，行为逐字节一致。

### 代码清理

- **`pa_agent/orchestrator/two_stage.py` 新增实例方法 `_route_and_load_experience(self, stage1_json: dict) -> tuple[list[str], list[Any]]`**：把 `submit()` 内 Steps 10-11（`# ── Step 10: Route strategy files`+`# ── Step 11: Load experience entries` 两块，共 27 行）**逐字节搬迁**为独立方法，放在 `_validation_settings` 之后、`# ── Public API ──` 分隔线之前的辅助方法区。逻辑完全不变：router 分支（`callable(self._router) and not hasattr(self._router, "route")` → `self._router(stage1_json)`，否则 `self._router.route(stage1_json)`）、`cycle_position`/`direction`/`patterns` 提取、`prompt_cfg`/`max_exp`/`max_chars` 读取、经验加载三分支（`max_exp<=0`→`[]` / 有 `read_for_stage2`→`read_for_stage2(...)` / 否则 `read_top5(cycle_position)[:max_exp]`），末尾 `return strategy_files, experience_entries`。
- **`submit()` 内 Steps 10-11 替换为单行调用**：`strategy_files, experience_entries = self._route_and_load_experience(stage1_json)`，保留 `strategy_files`/`experience_entries` 两个局部变量供后续 Step 12+（pre-Stage-2 cancel、Stage2 gate 短路、final record）使用。`submit()` 净减约 26 行。

### 验证

- `py_compile` 通过（`two_stage.py`，EXIT=0）。
- **集成测试基线对比**（本会话已 `pip install PyQt6`，打通 `two_stage` 集成测试收集）：核心 submit-path 套件（`test_two_stage_happy_path`/`_no_order_with_prices`/`_stage1_syntax`/`_stage1_missing_field`/`_stage2_invalid_value`/`_network_timeout`/`_user_cancel` + `test_gate_shortcircuit` + `test_decision_nodes_orchestrator` + `test_qclaw_auto_fallback`）**16 passed / 1 failed**，唯一失败 `test_no_order_with_non_null_price_fails_stage2` 经 `git stash` 回退 HEAD 复跑确认为**既有失败**（该测试用 `schema_test_validator()`，不含业务规则校验，故 order_type=不下单+entry_price=0 走到 happy path 而非 Stage2Failed），与本刀无关——拆分前后行为逐字节一致。
- `ruff check` 对比基线：`git show HEAD:two_stage.py` 与拆分后同为 **40 条**（全为既有 E402/RUF001/UP037/RUF100 类别，皆因该文件历史风格），**零净新增告警**。
- `git diff` 密钥扫描（`api_key`/`sk-`/`secret`/`token`/`password`/`Bearer`）仅命中无关的 `cancel_token` 既有变量名，无密钥泄漏——纯结构搬迁。

---

## [Unreleased] — 2026-07-15（第三十三轮：继续拆分 PromptAssembler，提取 program_prefill_hint 程序预填充节点提示渲染器 R-M1-5）

本轮为**大文件拆分 M1 的第五刀**（第二十九轮切 `kline_table_renderer.py`、第三十轮切 `experience_renderer.py`、第三十一轮切 `stage2_guidance.py`、第三十二轮切 `chain_context.py`，`prompt_assembler.py` 从 1963→1902→1880→1736→1652 行）。前四刀分别切走 KlineTableRenderer、ExperienceRenderer、阶段二指导渲染器簇与跨阶段 carryover 上下文构建器簇；本刀转向阶段一 user 消息里**把确定性引擎（§1.1/§2.3/§2.4）预填充判定摊开给 AI 参考**的那个渲染器——`_render_program_prefill_hint`。它在阶段一 user prompt 里注入一个紧凑块，展示程序对「数据是否足够」「当前方向（多/空/中性，五信号投票）」「是否 Always In（三闸门）」的确定性判定与依据，让 AI 在做自己的判断前先看到程序算了什么（并可经 `node_overrides` 覆盖）。选它作为 M1 第五刀的关键动机：① 它是一个**自足的单函数渲染器**——`@staticmethod`、无实例状态，仅在 `_build_stage1_user_prompt`/`_build_incremental_stage1_user_prompt`/`_build_incremental_stage1_continuation_user_prompt` 三处经 `self._render_program_prefill_hint(frame)` 调用，不被其他逻辑纠缠；② 依赖近乎 stdlib——模块级仅 `logging`+`typing`（`KlineFrame` 仅注解用途置于 `TYPE_CHECKING` 块），唯一的项目触点（`decision_nodes` 的三个 judge 与 `trend_context` 的两个摘要辅助）沿用原有的**函数体内 call-time import**（这也正是打破 `prompt_assembler` ↔ `decision_nodes`/`trend_context` 循环依赖的既有手法），故新模块可**独立 import**；③ `program_prefill_hint` ← `prompt_assembler` **无环**（新模块不回依赖 `prompt_assembler`）。

### 代码清理

- **新增 `pa_agent/ai/program_prefill_hint.py`（程序预填充节点提示渲染器模块，PyQt6-free 叶子）**：把 `_render_program_prefill_hint`（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `render_program_prefill_hint`）**逐字节搬迁**至新模块（保留块头「## 程序预填充节点判断依据（§1.1 / §2.3 / §2.4，供 AI 参考）」、§1.1/§2.3/§2.4 三节的中文依据串、§2.2「长程背景 vs 近期方向」摘要行与 `背景方向（K{n}-K41）≈ … 关系={…}` 格式化、冲突分支「；**冲突时不否决近期、不自动减半仓位**」、override 门槛的三条 `•` 项与 `except Exception` 兜底返回空串+`logger.warning` 文案）。import 仅 `from __future__ import annotations` + `logging` + `typing`（`TYPE_CHECKING`），`KlineFrame` 仅注解用途置于 `TYPE_CHECKING` 块，`decision_nodes`（`judge_data_sufficiency`/`judge_direction`/`judge_always_in`）与 `trend_context`（`build_trend_context`/`render_three_window_summary`）保持函数体内 call-time import，无其他 import 期项目依赖、无副作用。模块 docstring 说明其定位、PyQt6-free 叶子依赖、`PromptAssembler` staticmethod 重绑定约束、以及「块头/中文提示串/§2.2 摘要/override 门槛文案须逐字节一致（阶段一前缀 KV 缓存敏感、模型按块形对齐）」的约束。
- **`prompt_assembler.py` 改为从 `program_prefill_hint` 导入并重绑定 staticmethod**：删除方法体（含 `@staticmethod` 装饰）；在顶部 import 组 `market_features` 之后新增 `from pa_agent.ai.program_prefill_hint import render_program_prefill_hint`；在 `_stage1_pattern_supplement` 之后以 1 行 `_render_program_prefill_hint = staticmethod(render_program_prefill_hint)` **重绑定**，使 `_build_stage1_user_prompt`/`_build_incremental_stage1_user_prompt`/`_build_incremental_stage1_continuation_user_prompt` 三处 `self._render_program_prefill_hint(frame)` 调用**逐字节兼容**。文件从 1652 行降至 1571 行。
- **调用站点零改动**：`PromptAssembler` 内 3 处 `self._render_program_prefill_hint(frame)` 调用因 staticmethod 重绑定仍从 `PromptAssembler` 命名空间取到同一函数。

### 验证

- `py_compile` 通过（`program_prefill_hint.py`、`prompt_assembler.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `prompt_assembler.py` 中已无 `_render_program_prefill_hint` 的函数定义残留（`RESIDUAL_DEFS []`，全部迁出，仅余 1 行 staticmethod 重绑定）。
- **真实 runtime 等价对比**（新模块模块级 PyQt6-free 可独立 import）：从 `git show HEAD:prompt_assembler.py` 用 AST 提取拆分前的 `@staticmethod` 方法体、`exec` 重建为 `old_render`，与新模块 `render_program_prefill_hint` 在多组用例上逐例对比返回值——因两者的项目依赖均为**函数体内 call-time import**，用 `sys.modules` 注入 `decision_nodes`/`trend_context` 的 stub（避开 `market_features`→PyQt6 触链）使新旧走同一 stub——normal（含 §1.1/§2.3/§2.4 齐全，566 字符）、conflict_neutral（方向中性 + 背景冲突分支，546 字符）、raises（judge 抛异常触发 `except` 兜底，返回空串）三场景逐例相等——`PREFILL_HINT_EQ` **True**。
- `ruff check` 对比基线：拆分前 HEAD `prompt_assembler.py` 为 **1307** 条、Counter `{I001:2, RUF001:1301, RUF003:2, RUF100:2}`；拆分后 `prompt_assembler.py` 降至 1274、新模块 `program_prefill_hint.py` 携 33 条（`{I001:1, RUF001:31, RUF100:1}`——31×RUF001 全角标点随中文提示串迁入、`I001` 为 call-time import 块排序、`RUF100` 为 `# noqa: BLE001` 未启用规则，三者均随方法体整体迁移的既有类别），合计 **1307**，**逐类别 Counter 完全一致、零净新增告警**（`I001`/`RUF100` 均从 `prompt_assembler` 的 2→1 转移到新模块的 0→1，总量守恒）。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- **既有失败甄别**：`test_prompt_assembler.py` 因 import `PromptAssembler` 经 `market_features`→`util/__init__`→`event_bus`→PyQt6 在本机无法收集，属**既有环境缺口**（本机缺 PyQt6），与本轮纯结构搬迁无关；本轮迁出的渲染器已由 PyQt6-free 的 runtime 等价脚本（stub 注入）独立验证。

---

## [Unreleased] — 2026-07-15（第三十二轮：继续拆分 PromptAssembler，提取 chain_context 跨阶段 carryover 上下文构建器簇 R-M1-4）

本轮为**大文件拆分 M1 的第四刀**（第二十九轮切 `kline_table_renderer.py`、第三十轮切 `experience_renderer.py`、第三十一轮切 `stage2_guidance.py`，`prompt_assembler.py` 从 1963→1902→1880→1736 行）。前三刀分别切走 KlineTableRenderer、ExperienceRenderer 与阶段二指导渲染器簇；本刀转向散落在类体中、把**上一阶段/上一轮结果**序列化成**下游 prompt 片段**的一组确定性辅助——把它们抽成独立叶子模块。这一簇由四个 `@staticmethod` 组成：`_normalize_prev_stage1_assistant_for_incremental`（增量模式下复用上一轮已校验的阶段一诊断 JSON 而非其散文/markdown 回复作为 assistant 轮）、`_render_previous_prediction`（把上一轮「下一根K线预测」渲染成紧凑参考块，R5.2）、`_normalize_stage1_assistant_for_chain`（前缀链模式下压缩刚校验的阶段一 JSON 作 assistant 轮）、`_compact_stage1_for_stage2`（把阶段一诊断投影到阶段二实际所需字段子集，降噪减 token）。选它作为 M1 第四刀的关键动机：① 它是一个**主题高内聚簇**——四者语义都是「跨阶段/跨轮结果 → 下游上下文」的确定性序列化，且每个都只有类内 `self._x(...)` 调用点（`_normalize_prev_stage1_assistant_for_incremental` 于 `build_incremental_stage1`、`_render_previous_prediction`/`_compact_stage1_for_stage2` 于 `_build_stage2_user_prompt`、`_normalize_stage1_assistant_for_chain` 于 `build_stage2_continuation`），不被其他逻辑纠缠；② 依赖**近乎 stdlib**——仅 `json`/`logging`/`typing.Any` + `TYPE_CHECKING` 下的 `AnalysisRecord` 注解 import，唯一项目触点 `format_model_json_for_context` 沿用原有的**函数体内 call-time import**（避开 `market_features`→PyQt6 触链、破环），故新模块可**独立 import 并运行真实 runtime 等价验证**；③ `chain_context` ← `prompt_assembler` **无环**（新模块不回依赖 `prompt_assembler`）。

### 代码清理

- **新增 `pa_agent/ai/chain_context.py`（跨阶段 carryover 上下文构建器簇模块，PyQt6-free 叶子）**：把四个方法（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `normalize_prev_stage1_assistant_for_incremental`/`render_previous_prediction`/`normalize_stage1_assistant_for_chain`/`compact_stage1_for_stage2`）**逐字节搬迁**至新模块（保留全部块头「## 上一轮下一根K线预测」、`unpredictable` 分支文案、`{"bullish": "阳线", ...}` 方向映射、`阳 {bull}% / 阴 {bear}% / 中性 {neut}%` 概率格式化、20 字段 `_compact_stage1_for_stage2` 白名单元组、`json.dumps(indent=2)` 序列化、增量降级的 `logger.warning` 文案）。import 仅 `from __future__ import annotations` + `json` + `logging` + `typing`（`TYPE_CHECKING`/`Any`），`AnalysisRecord` 仅注解用途置于 `TYPE_CHECKING` 块，`format_model_json_for_context` 保持两处函数体内 call-time import，无其他 import 期项目依赖、无副作用。模块 docstring 说明其定位、PyQt6-free 叶子依赖、`PromptAssembler` staticmethod 重绑定约束、以及「块头/中文参考串/方向概率格式化/阶段二字段白名单须逐字节一致（模型按这些片段形对齐、前缀 KV 缓存对压缩 JSON 敏感）」的约束。
- **`prompt_assembler.py` 改为从 `chain_context` 导入并重绑定 staticmethod**：删除四个方法体（含 `@staticmethod` 装饰）；在顶部 import 组新增 `from pa_agent.ai.chain_context import (compact_stage1_for_stage2, normalize_prev_stage1_assistant_for_incremental, normalize_stage1_assistant_for_chain, render_previous_prediction)`；在 `PromptAssembler` 类体新增「Cross-stage carryover context」区以 4 行 `_normalize_prev_stage1_assistant_for_incremental = staticmethod(normalize_prev_stage1_assistant_for_incremental)` / `_render_previous_prediction = staticmethod(render_previous_prediction)` / `_normalize_stage1_assistant_for_chain = staticmethod(normalize_stage1_assistant_for_chain)` / `_compact_stage1_for_stage2 = staticmethod(compact_stage1_for_stage2)` **重绑定**，使 `build_incremental_stage1`/`_build_stage2_user_prompt`/`build_stage2_continuation` 链内 `self._normalize_prev_stage1_assistant_for_incremental(...)`/`self._render_previous_prediction(...)`/`self._normalize_stage1_assistant_for_chain(...)`/`self._compact_stage1_for_stage2(...)` 调用**逐字节兼容**。文件从 1736 行降至 1652 行。
- **调用站点零改动**：`PromptAssembler` 内 4 处 `self._normalize_prev_stage1_assistant_for_incremental`/`self._render_previous_prediction`/`self._normalize_stage1_assistant_for_chain`/`self._compact_stage1_for_stage2` 调用因 staticmethod 重绑定仍从 `PromptAssembler` 命名空间取到同一函数。

### 验证

- `py_compile` 通过（`chain_context.py`、`prompt_assembler.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `prompt_assembler.py` 中已无这四个构建器的函数定义残留（`RESIDUAL_DEFS []`，全部迁出，仅余 4 行 staticmethod 重绑定）。
- **真实 runtime 等价对比**（新模块 PyQt6-free 可独立 import）：从 `git show HEAD:prompt_assembler.py` 用 AST 提取拆分前四个 `@staticmethod` 方法体、`exec` 重建为 `old_*`，与新模块 `normalize_prev_stage1_assistant_for_incremental`/`render_previous_prediction`/`normalize_stage1_assistant_for_chain`/`compact_stage1_for_stage2` 在多组用例上逐例对比返回值——prev_inc 4 例（有诊断/空诊断+可修复JSON/None+纯文本/空）、prev_pred 7 例（None/无预测/unpredictable/多头概率/空概率/dict形态/未知方向）、chain 4 例（有JSON/空+可修复/无JSON/空）、compact 4 例（含垃圾键/空/部分字段/全白名单）——`CHAIN_CONTEXT_EQ` **True**。
- `ruff check` 对比基线：拆分前 HEAD `prompt_assembler.py` 为 **1312** 条、Counter `{I001:2, RUF001:1306, RUF003:2, RUF100:2}`；拆分后 `prompt_assembler.py` 降至 1307、新模块 `chain_context.py` 携 5 条（5×RUF001 全角标点，随参考串迁入的既有类别），合计 **1312**，**逐类别 Counter 完全一致、零净新增告警**（`I001` 两条均为既有——顶部块 `pattern_routing` 早于 `kline_table_renderer` 的历史排序 + `_render_program_prefill_hint` 内 call-time import 块，均自第二十九轮沿袭，本轮 `chain_context` 插入相对邻居排序正确、零新增）。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- **既有失败甄别**：`test_prompt_assembler.py` 因 import `PromptAssembler` 经 `market_features`→`util/__init__`→`event_bus`→PyQt6 在本机无法收集，属**既有环境缺口**（本机缺 PyQt6），与本轮纯结构搬迁无关；本轮迁出的构建器已由 PyQt6-free 的 runtime 等价脚本独立验证。

---

## [Unreleased] — 2026-07-14（第三十一轮：继续拆分 PromptAssembler，提取 stage2_guidance 阶段二指导渲染器簇 R-M1-3）

本轮为**大文件拆分 M1 的第三刀**（第二十九轮已切 `kline_table_renderer.py`、第三十轮已切 `experience_renderer.py`，`prompt_assembler.py` 从 1963→1902→1880 行）。前两刀分别切走报告 §5.2 M1 点名的 KlineTableRenderer 与 ExperienceRenderer 产出；本刀转向 Stage 2 user 消息里一组**由阶段一诊断字段派生的确定性指导块渲染器**——把它们抽成独立叶子模块。这一簇由四个 `@staticmethod` 组成：`_render_trend_conflict_guidance`（新旧趋势冲突指导，Brooks 并列原则）、`_render_transition_guidance`（状态转换期风险指导，按 transition_risk 高/中/低给信号把握与入场选择）、`_parse_level_midpoint`（支撑/阻力位字符串解析为数值中点，`_render_planned_limit_hint` 专用辅助）、`_render_planned_limit_hint`（通道/区间结构下的 §9.0/§9.0P 计划型限价提示，含 ATR 邻近度与近支撑/阻力定价）。选它作为 M1 第三刀的关键动机：① 它是一个**高内聚自足簇**——三个指导渲染器 + 一个私有解析辅助逻辑闭环，`_parse_level_midpoint` 仅被 `_render_planned_limit_hint` 内部调用，三个渲染器仅在 `_build_stage2_user_prompt`（L1575-1577）经 `self._render_*` 调用，不被其他逻辑纠缠；② 依赖**仅 stdlib `math` + PyQt6-free 的 `KlineFrame` 叶子**——不触 `market_features`→PyQt6 链，故新模块可**独立 import 并运行真实 runtime 等价验证**；③ 迁出后 `math.` 在 `prompt_assembler.py` 内**仅剩** `_render_planned_limit_hint` 一处引用，随簇迁出后 `import math` 成为孤儿可一并删除；④ `stage2_guidance` ← `prompt_assembler` **无环**（新模块不回依赖 `prompt_assembler`）。

### 代码清理

- **新增 `pa_agent/ai/stage2_guidance.py`（阶段二指导渲染器簇模块，PyQt6-free 叶子）**：把四个方法（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `render_trend_conflict_guidance`/`render_transition_guidance`/`parse_level_midpoint`/`render_planned_limit_hint`）**逐字节搬迁**至新模块（保留全部块头「## 新旧趋势冲突指导（Brooks 并列原则）」/「## 状态转换期风险指导」/「## §9.0 / §9.0P 计划型限价提示…」、中文指导串、`transition_risk` 高/中/低三分支文案、`{...:.4f}` 数值格式化、`max(atr * 0.35, ...)` 邻近度算术、`math.isnan` warm-up 分支；`_render_planned_limit_hint` 内两处 `PromptAssembler._parse_level_midpoint(lv)` 调用改为模块内 `parse_level_midpoint(lv)`）。import 仅 `from __future__ import annotations` + `math` + `from pa_agent.data.base import KlineFrame`，无其他 import 期项目依赖、无副作用。模块 docstring 说明其定位、PyQt6-free 叶子依赖、`PromptAssembler` staticmethod 重绑定约束、以及「块头/中文指导串/数值格式化须逐字节一致（模型按此块形对齐）」的约束。
- **`prompt_assembler.py` 改为从 `stage2_guidance` 导入并重绑定 staticmethod**：删除四个方法体（含 `@staticmethod` 装饰，共约 154 行）；在顶部 import 组新增 `from pa_agent.ai.stage2_guidance import (parse_level_midpoint, render_planned_limit_hint, render_transition_guidance, render_trend_conflict_guidance)`；在 `PromptAssembler` 类体新增「Stage-2 contextual guidance rendering」区以 4 行 `_render_trend_conflict_guidance = staticmethod(render_trend_conflict_guidance)` / `_render_transition_guidance = staticmethod(render_transition_guidance)` / `_parse_level_midpoint = staticmethod(parse_level_midpoint)` / `_render_planned_limit_hint = staticmethod(render_planned_limit_hint)` **重绑定**，使 `_build_stage2_user_prompt` 链内 `self._render_trend_conflict_guidance(...)`/`self._render_transition_guidance(...)`/`self._render_planned_limit_hint(...)` 调用**逐字节兼容**；删除已成孤儿的 `import math`（迁出后本文件内 `math.` 已无引用）。文件从 1880 行降至 1736 行。
- **调用站点零改动**：`PromptAssembler` 内 3 处 `self._render_*_guidance`/`self._render_planned_limit_hint`（`_build_stage2_user_prompt`）调用因 staticmethod 重绑定仍从 `PromptAssembler` 命名空间取到同一函数。

### 验证

- `py_compile` 通过（`stage2_guidance.py`、`prompt_assembler.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `prompt_assembler.py` 中已无这四个渲染器/辅助的函数定义残留（`RESIDUAL_DEFS []`，全部迁出，仅余 4 行 staticmethod 重绑定）。
- **真实 runtime 等价对比**（新模块 PyQt6-free 可独立 import）：从 `git show HEAD:prompt_assembler.py` 用 AST 提取拆分前四个 `@staticmethod` 方法体、`exec` 重建为 `old_*`，与新模块 `render_*`/`parse_level_midpoint` 在多组用例上逐例对比返回值——trend_conflict 6 例（无 trend_context/非 dict/无 conflict/含 spike 等）、transition 7 例（stable/transitioning×高中低/未知 risk）、parse_level_midpoint 12 例（None/空/纯数/区间/非法/多段）、planned_limit_hint 7 例（非目标周期/空 bars/近支撑/近阻力/NaN ATR/非法 levels/neutral 方向）——`STAGE2_GUIDANCE_EQ` **True**。
- `ruff check` 对比基线：拆分前 HEAD `prompt_assembler.py` 为 **1372** 条、Counter `{I001:2, RUF001:1364, RUF003:2, RUF100:2, SIM102:2}`；拆分后 `prompt_assembler.py` 降至 1312、新模块 `stage2_guidance.py` 携 60 条（58×RUF001 全角标点 + 2×SIM102 嵌套 if，均随 hint 逻辑迁入的既有类别），合计 **1372**，**逐类别 Counter 完全一致、零净新增告警**。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- **既有失败甄别**：`test_prompt_assembler.py` 因 import `PromptAssembler` 经 `market_features`→`util/__init__`→`event_bus`→PyQt6 在本机无法收集，属**既有环境缺口**（本机缺 PyQt6），与本轮纯结构搬迁无关；本轮迁出的渲染器已由 PyQt6-free 的 runtime 等价脚本独立验证。

---

## [Unreleased] — 2026-07-14（第三十轮：继续拆分 PromptAssembler，提取 experience_renderer 经验库渲染器 R-M1-2）

本轮为**大文件拆分 M1 的第二刀**（第二十九轮 `kline_table_renderer.py` 已把 K 线表渲染器簇拆出，`prompt_assembler.py` 从 1963 行降至 1902 行）。首刀切走了 **KlineTableRenderer 产出**，本刀转向报告 §5.2 M1 点名的另一产出——**ExperienceRenderer**，即把「阶段二 user 消息」中折叠最近经验库案例的纯文本块渲染器 `_render_experience` 抽成独立叶子模块。它是把经验库条目（dict / 带 `content` 属性对象 / 纯字符串）落地成「## 经验库(最近案例,供参考)」文本块的确定性生成器：逐条 `json.dumps(indent=2)` 序列化、超 `max_chars_per_entry`（默认 400）截断加省略号、每条包 markdown ```json 围栏。选它作为 M1 第二刀的关键动机：① 它是一个**极简自足单元**——单个 `@staticmethod`，除 `build_stage2`/`stage2_system_prompt_only` 链的唯一内部调用点（`self._render_experience(...)`）外不被其他逻辑纠缠；② 依赖**纯 stdlib**——只 `json`（无任何项目 import），故新模块可**独立 import 并运行真实 runtime 等价验证**（同 KlineTableRenderer 一样绕开 `market_features`→PyQt6 触链）；③ `experience_renderer` ← `prompt_assembler` **无环**（新模块不回依赖 `prompt_assembler`）。

### 代码清理

- **新增 `pa_agent/ai/experience_renderer.py`（经验库渲染器模块，stdlib-only 叶子）**：把 `_render_experience`（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `render_experience`）**逐字节搬迁**至新模块（保留「## 经验库(最近案例,供参考)」块头、「以下案例仅作对照…」中文告诫串、`isinstance(dict)`/`hasattr("content")`/`str(entry)` 三分支序列化、`max_chars_per_entry - 3` 截断加 `"..."`、每条 `\n### 案例 {i}\n```json\n{blob}\n```` 围栏）。import 仅 `from __future__ import annotations` + `json` + `typing.Any`，无其他 import 期项目依赖、无副作用。模块 docstring 说明其「ExperienceRenderer」定位、stdlib-only 叶子依赖、`PromptAssembler` staticmethod 重绑定约束、以及「块头/中文告诫/围栏/截断省略号须逐字节一致（模型按此块形对齐）」的约束。
- **`prompt_assembler.py` 改为从 `experience_renderer` 导入并重绑定 staticmethod**：删除原 `_render_experience` 方法体（含 `@staticmethod` 装饰，共约 25 行）；在顶部 import 组新增 `from pa_agent.ai.experience_renderer import render_experience`（字母序排在 `decision_stance` 之后、`pattern_routing` 之前）；在 `PromptAssembler` 类体末尾「Experience library rendering」区以 1 行 `_render_experience = staticmethod(render_experience)` **重绑定**，使 `build_stage2` 链内 `self._render_experience(entries)` 调用**逐字节兼容**。`import json` 保留（`_compact_stage1_json` 等多处仍用）。文件从 1902 行降至 1880 行。
- **调用站点零改动**：`PromptAssembler._render_experience`（`build_stage2` → `stage2_system_prompt_only` 链的唯一内部调用点）因 staticmethod 重绑定仍从 `PromptAssembler` 命名空间取到同一函数。

### 验证

- `py_compile` 通过（`experience_renderer.py`、`prompt_assembler.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `prompt_assembler.py` 中已无 `render_experience`/`_render_experience` 函数定义残留（渲染器已全部迁出，仅余 1 行 staticmethod 重绑定）。
- **真实 runtime 等价对比**（新模块 stdlib-only 可独立 import）：从 `git show HEAD:prompt_assembler.py` 用正则提取拆分前的 `_render_experience` 方法 `exec` 重建为 `old_render_exp`，与新模块 `render_experience` 在 **7 组条目用例**（空列表、单/多 dict、带 `content` 属性对象、纯字符串、超长触发截断、四类混排）× **4 种 `max_chars_per_entry`**（50/400/1000/默认）上逐例对比返回值——`EXPERIENCE_EQ` **True**（含 dict/content-attr/str 三分支与截断路径全覆盖）。
- `ruff check` 对比基线：拆分前后总数 **1373** 保持不变；逐错误码 Counter 对比——新模块 `experience_renderer.py` 携 **1** 条（1×RUF001 全角逗号，随「## 经验库(最近案例,供参考)」块头迁入），`prompt_assembler.py` 从 1373 降至 1372，合计 1373，**逐类别一致、零净新增告警**。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- **既有失败甄别**：`test_prompt_assembler.py` 因 import `PromptAssembler` 经 `market_features`→`util/__init__`→`event_bus`→PyQt6 在本机无法收集，属**既有环境缺口**（本机缺 PyQt6），与本轮纯结构搬迁无关；本轮迁出的渲染器已由 stdlib-only 的 runtime 等价脚本独立验证。

---

## [Unreleased] — 2026-07-14（第二十九轮：拆分 PromptAssembler，提取 kline_table_renderer K 线表渲染器簇 R-M1-1）

本轮为**大文件拆分 M1 的第一刀**（对应后端审查报告 §5.2 M1「拆分 `PromptAssembler`，产出 `Stage1PromptBuilder`/`Stage2PromptBuilder`/`KlineTableRenderer`/`ExperienceRenderer`」）。`prompt_assembler.py` 是 AI 层超大文件（1963 行，CRLF），此前 M2/M3 各轮未触碰。本刀先切报告明确点名的 **KlineTableRenderer 产出**——即把喂给模型「阶段一/阶段二 user 消息」的两张纯文本 K 线表渲染器抽成独立叶子模块。它们是把结构化 K 线「落地成模型逐字节对齐的 OHLC/EMA20/ATR14 表 + 单棒几何特征表」的确定性文本生成器：`_render_kline_table`（价量指标表，含 EMA/ATR 的 `N/A` warm-up 分支）、`_render_kline_feature_table`（几何特征表，逐字段用 `_fmt_feature` 格式化），配套 `_fmt_feature` 辅助与 `_KLINE_INDICATOR_NOTE` 中文说明常量。选它作为 M1 第一刀的关键动机：① 它是一个**高内聚自足簇**——两个渲染器 + 一个格式化辅助 + 一个常量逻辑闭环，除 `PromptAssembler` 内部调用与测试外不被其他逻辑纠缠；② 依赖**全为 PyQt6-free 叶子模块**——`kline_features`（`bar_candle_direction_label`/`compute_kline_geometry_features`）、`data.base`（`KlineFrame`）、`data.datetime_ts`（`format_epoch_for_display`）均验证 `import` 期不触 PyQt6，故新模块可**独立 import 并运行真实 runtime 等价验证**（区别于经 `market_features`→`util/__init__`→`event_bus`→PyQt6 触链的 market-feature 包装方法——那两个方法本刀**暂留** `prompt_assembler.py`，待后续切 Stage1/Stage2PromptBuilder 时一并处理）；③ `kline_table_renderer` ← `prompt_assembler` **无环**（新模块不回依赖 `prompt_assembler`）。

### 代码清理

- **新增 `pa_agent/ai/kline_table_renderer.py`（K 线表渲染器簇模块，PyQt6-free 叶子）**：把 `_KLINE_INDICATOR_NOTE` 常量、`_fmt_feature` 辅助、`_render_kline_table`/`_render_kline_feature_table` 两个渲染器（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `render_kline_table`/`render_kline_feature_table`）**逐字节搬迁**至新模块（保留全部表头列宽、中文列名、`f"{...:<4}"` 对齐格式、`Render方案 A` 混排 docstring、`math.isnan(...)→"N/A"` warm-up 分支、`str(feat.ioi_pattern)` 渲染）。import 仅 `from __future__ import annotations` + `math` + 3 个 PyQt6-free 叶子 import，无其他 import 期项目依赖、无副作用。模块 docstring 说明其「K 线表渲染器」定位、PyQt6-free 叶子依赖、`PromptAssembler` staticmethod 重绑定约束、以及「表格布局/列宽/中文表头/说明常量须逐字节一致（模型按此表形对齐）」的约束。
- **`prompt_assembler.py` 改为从 `kline_table_renderer` 导入并重绑定 staticmethod**：删除原 `_KLINE_INDICATOR_NOTE` 常量、`_fmt_feature` 模块函数、两个渲染器方法体（共约 60 行）；把顶部 `from pa_agent.ai.kline_features import ...`（两名只被渲染器用）替换为 `from pa_agent.ai.kline_table_renderer import render_kline_feature_table, render_kline_table`，并删除已成孤儿的 `from pa_agent.data.datetime_ts import format_epoch_for_display`；在 `PromptAssembler` 类体「K-line table rendering」区以 2 行 `_render_kline_table = staticmethod(render_kline_table)` / `_render_kline_feature_table = staticmethod(render_kline_feature_table)` **重绑定**，使 `PromptAssembler._render_kline_table(...)`（`main_window.py` 类名调用）、`assembler._render_kline_feature_table(...)`（`test_prompt_assembler.py` 实例调用）等既有站点**逐字节兼容**。`import math` 保留（market-feature 分支仍用）。文件从 1963 行降至 1902 行。
- **调用站点零改动**：`PromptAssembler` 内 8 处 `self._render_kline_table(...)` / `self._render_kline_feature_table(...)` 调用、`main_window.py` 的 `PromptAssembler._render_kline_table(export_frame)`、`test_prompt_assembler.py`/`test_kline_candle_direction.py` 的类名/实例调用因 staticmethod 重绑定仍从 `PromptAssembler` 命名空间取到同一函数。

### 验证

- `py_compile` 通过（`kline_table_renderer.py`、`prompt_assembler.py`，EXIT=0）。
- **AST 结构核验**：`ast.walk` 确认 `prompt_assembler.py` 中已无 `render_kline*`/`_fmt_feature` 函数定义残留（渲染器已全部迁出，仅余 2 行 staticmethod 重绑定）。
- **真实 runtime 等价对比**（新模块 PyQt6-free 可独立 import）：从 `git show HEAD:prompt_assembler.py` 用正则提取拆分前的常量/`_fmt_feature`/两个渲染器方法 `exec` 重建为 `old_*`，与新模块 `render_*` 在真实 `KlineFrame`（含 nan EMA/ATR 触发 `N/A` 路径）上对比 **4 组返回值**——full 表、limited×2（`limit=2`）——`TABLE_EQ`/`FEAT_EQ`/`TABLE_LIM_EQ`/`FEAT_LIM_EQ` **全部 True**。
- `ruff check` 对比基线：拆分前后总数 **1384** 保持不变；逐错误码 Counter 对比——新模块 `kline_table_renderer.py` 携 **11** 条（10×RUF001 全角逗号 + 1×RUF010，均随 feature table 迁入的既有类别），`prompt_assembler.py` 从 1384 降至 1373，合计 1384，**逐类别一致、零净新增告警**。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- **既有失败甄别**：`test_prompt_assembler.py` 因 import `PromptAssembler` 经 `market_features`→`util/__init__`→`event_bus`→PyQt6 在本机无法收集，属**既有环境缺口**（本机缺 PyQt6），与本轮纯结构搬迁无关；本轮迁出的渲染器已由 PyQt6-free 的 runtime 等价脚本独立验证。

---

## [Unreleased] — 2026-07-14（第二十八轮：继续拆分 JsonValidator，提取 business_rules §9/§11 业务规则校验器簇 R-M2-2）

本轮为**大文件拆分 M2 的第二刀**（第十六轮 `json_repair.py` 已把纯 JSON 文本提取/修复函数区拆出，`json_validator.py` 从 1023 行降至约 660 行；随 M3 各轮迭代该文件保持不变）。首刀抽走了「JSON 语法层（去 fence / 修引号 / 补括号 / 语法修复）」，本刀转向 `JsonValidator` 内**阶段二业务规则跨字段校验层**——`BusinessRuleValidator` 簇（对应后端审查报告 §5.2 M2 规划产出）。它是 `JsonValidator.validate` 在 schema 校验之后、对 stage2 输出施加的 7 个确定性 §9/§11 下单决策校验：`_check_no_order_invariant`（不下单↔null 铁律）、`_check_breakout_order_basis`（突破单必须绑定 K 线极值）、`_check_trade_metrics`（RR/交易者方程）、`_check_breakout_price_extreme`（突破入场价数值校验）、`_check_next_cycle_prediction`（周期预测 sum/argmax/null 规则）、`_check_next_bar_prediction`（下一棒预测 sum/argmax/null 规则）、`_check_signal_chain`（下单决策须以 §9 信号事实为依据）。选它作为下一刀的关键动机：① 它是一个**高内聚自足簇**——7 个 `_check_*` 校验器 + 3 个模块级辅助（`_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons`）+ `_EXPLICIT_S9_TRADABLE_TOKENS` 令牌元组逻辑闭环、互相配合，除 `validate` 主方法与测试外**不被其他模块引用**；② 依赖近乎全为 stdlib——只 `re`/`typing.Any`，两个项目触点（`validate_order_trade_metrics` 来自 `pa_agent.util.trade_metrics`——经 `util/__init__`→`event_bus`→PyQt6，`CYCLE_ENUM`/`CYCLE_ORDER` 来自 `pa_agent.ai.cycle_enums`）均走**函数体内 call-time import**，故新模块 import 期**不触 PyQt6、不引入循环导入**（`business_rules` ← `json_validator` 无环）；③ `json_validator.py` 的 import 链本身**不经 PyQt6**，故本刀可运行**真实 pytest** 验证（区别于 M3 各轮只能靠运行时对比脚本）。

### 代码清理

- **新增 `pa_agent/ai/business_rules.py`（§9/§11 业务规则校验器簇模块）**：把 `_EXPLICIT_S9_TRADABLE_TOKENS` 令牌元组、7 个 `_check_*` 校验器（去掉 `@staticmethod` 装饰降为模块函数、更名去掉前导下划线为 `check_*`，即 `check_no_order_invariant`/`check_breakout_order_basis`/`check_trade_metrics`/`check_breakout_price_extreme`/`check_next_cycle_prediction`/`check_next_bar_prediction`/`check_signal_chain`）与 3 个模块级辅助（`_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons`）**逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、`_planned_limit_boundary_patterns` 白名单、R2.3/R3.2/R3.3/R5.1 注释、`_check_trade_metrics` 的 `validate_order_trade_metrics` call-time import 原位、`_check_next_cycle_prediction` 的 `cycle_enums` call-time import 原位）。import 仅 `from __future__ import annotations` + `re` + `typing.Any`，无其他 import 期项目依赖、无副作用。模块 docstring 说明其「business-rule 校验器簇」定位、call-time import 打破 PyQt6/环、以及「`JsonValidator` 以 staticmethod 重绑定保持 `JsonValidator._check_x(...)` 逐字节兼容」的约束。
- **`json_validator.py` 改为从 `business_rules` 重导出并重绑定 staticmethod**：删除原 `_EXPLICIT_S9_TRADABLE_TOKENS`（L20-40）、7 个 `_check_*` 方法体（L418-793）与 3 个模块辅助（L796-821），移除已无用的 `import re`；在顶部 import 组新增 `from pa_agent.ai import business_rules` + `from pa_agent.ai.business_rules import (_EXPLICIT_S9_TRADABLE_TOKENS, _all_stage2_reasons, _bar_by_seq, _parse_k_seq)`（`# noqa: E402, F401` 纯重导出，字母序排在 `json_repair` 之前满足 isort）；在 `JsonValidator` 类体内以 7 行 `_check_x = staticmethod(business_rules.check_x)` **重绑定**，使 `validate` 内 `self._check_x(...)` 与测试 `JsonValidator._check_x(...)` 类名调用**逐字节兼容**。文件从 821 行降至 415 行。
- **调用站点零改动**：`JsonValidator._check_next_bar_prediction`（`test_json_validator.py`/`test_next_bar_prediction.py`）、`JsonValidator._check_breakout_price_extreme`（`test_price_tick.py`）等测试站点因 staticmethod 重绑定仍从 `JsonValidator` 命名空间取到同一函数；`from pa_agent.ai.json_validator import _EXPLICIT_S9_TRADABLE_TOKENS/_parse_k_seq/...` 等既有站点因重导出仍可取到同一对象。

### 验证

- `py_compile` 通过（`business_rules.py`、`json_validator.py`，EXIT=0）。
- **import 与重绑定等价性**：`python -c` 断言 `import pa_agent.ai.json_validator`（**不触 PyQt6**）成功；`_EXPLICIT_S9_TRADABLE_TOKENS` 长度=18、`_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons` 可调用；`JsonValidator._check_no_order_invariant`/`_check_next_bar_prediction`/`_check_signal_chain`/`_check_breakout_price_extreme` 经类名调用返回值与原实现一致（不下单+非 null 价 → 命中 `entry_price`；空 obj → `[]`）。
- **真实 pytest**（`json_validator` import 不经 PyQt6，本轮可运行真实测试）：`pytest tests/unit/test_json_validator.py -k "next_bar_prediction"` → **5 passed**（覆盖 absent/unpredictable-null/sum-tolerance/direction-mismatch/prefix 全部 T6 用例）。
- **运行时行为对比**：以真实 `KlineFrame` 构造突破单用例，断言 `_check_breakout_price_extreme` 对「做多突破单 entry 低于 K1.high」返回中文报错串、对「entry 高于 K1.high」返回 `[]`，与拆分前一致。
- `ruff check` 对比基线：从 `git show HEAD:` 取拆分前 `json_validator.py` 写 UTF-8 临时文件后逐错误码 Counter 对比——基线单文件 **3** 条（2×I001、1×RUF005）→ 拆分后 `json_validator.py`（2×I001）+ 新增 `business_rules.py`（1×RUF005，随 `check_next_cycle_prediction` 的 `errors + [...]` 迁入）合计 **3**，**逐类别完全一致、零净新增告警**（新增的 business_rules import 块曾触发 1 条 I001，已手工把 `business_rules` 重导出块置于 `json_repair` 之前恢复 isort 顺序、收敛为零净新增）。
- **既有失败甄别**：`test_json_validator.py` 内 5 个失败经 `git stash` 还原至 HEAD 复现，确认均为**既有环境缺口**、非本轮引入——2 个 `FileNotFoundError`（缺 `tools/stage2_raw_sample.txt` 样本）、3 个 `ModuleNotFoundError: PyQt6`（`validate` 内 `normalize_parsed`→`stage2_normalizer`→`util/__init__`→`event_bus`→PyQt6）。这些失败均不触及本轮迁出的 `_check_*` 方法。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十七轮：继续拆分 decision_nodes，提取 signal_context §9 信号棒/限价单上下文辅助 R-M3-11）

本轮为**大文件拆分 M3 的第十一刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇、第二十二轮 `direction_judge.py` §2.3 方向判定器、第二十三轮 `diagnostic_judges.py` §1 诊断判定器簇、第二十四轮 `always_in_judges.py` §2.4/§2.5 判定器簇、第二十五轮 `override_arbiter.py` 受控 override 裁决簇、第二十六轮 `order_method_router.py` §11 下单方式路由簇）。前十刀先后抽走了「共享底层（常量/几何/闸门/结果层）」「全部 section-judge 簇」「override 裁决层」与「§11 下单方式路由层」，本刀转向 `DecisionNodeEngine.apply_stage2` 依赖的最后一组独立辅助——**§9 信号棒/限价单上下文辅助**（SignalBarJudge 辅助簇）。它是 `apply_stage2` 用来「定位信号棒序号、判断是否为无需已收盘信号棒的计划型限价单」的 3 个确定性辅助函数。选它作为下一刀的关键动机：① 它是一个**高内聚自足簇**——`_get_signal_seq`（定位信号棒序号：优先 `bar_analysis.signal_bar.bar`，否则 K1）、`has_background_limit_path`（§9.0P=是 背景驱动限价路径检测）、`is_planned_limit_order`（计划型限价单判定，内部调用 `has_background_limit_path`），三者互相配合、不被其他 judge 引用；② 依赖近乎全为 stdlib——只 `logging`/`typing.Any`，唯一的项目触点 `parse_k_seq`（来自 `pa_agent.util.price_tick`，该模块仅 import stdlib `re`/`typing`）走 `_get_signal_seq` 函数体内 **call-time import**，**不引用任何 judge/override/router、不回依赖 `decision_nodes`**（无环前提：`signal_context` ← `decision_nodes`），故可一刀干净剥离而不触发循环导入。至此 `decision_nodes.py` 仅余 `DecisionNodeEngine` 编排层（`apply_stage1`/`apply_stage2`）——大文件拆分 M3 收官在即。

### 代码清理

- **新增 `pa_agent/ai/signal_context.py`（§9 信号棒/限价单上下文辅助簇模块）**：把 `_get_signal_seq`/`has_background_limit_path`/`is_planned_limit_order` 三个辅助函数（含 `# ── SignalBarJudge` 分隔头下的整块，src[1641:4440]）**逐字节搬迁**至新模块（保留全部 docstring、中文 reason/pattern 白名单、`parse_k_seq` call-time import、§9.0P 检测与 pending 判定分支、`_get_signal_seq` 特有的双空行排版及默认 K1 兜底），import 仅 `from __future__ import annotations` + `logging` + `typing.Any`（新增 `logger = logging.getLogger(__name__)` 供 `_get_signal_seq` 的 `logger.debug(..., exc_info=True)` 失败记录），无其他 import 期项目依赖、无副作用。模块 docstring 说明其「signal-context 辅助簇」定位、`parse_k_seq` call-time import 打破环与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `signal_context` 导入三个辅助**：删除原 `# ── SignalBarJudge` 分隔头 + 3 个函数定义块（src[1641:4440]），在文件顶部 import 组新增 `from pa_agent.ai.signal_context import (_get_signal_seq, has_background_limit_path, is_planned_limit_order)`（字母序排在 `signal_bar_judges` 之后、`trace_nodes` 之前）。三者在 `DecisionNodeEngine.apply_stage2` 链（`sig = _get_signal_seq(...)`、`_planned_limit = is_planned_limit_order(out)`、`has_background_limit_path(out)`）**确有引用**，属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import is_planned_limit_order` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`stage2_normalizer.py` 的两处 call-time import 与 `test_decision_nodes_judges.py` 无需改动）。文件进一步收缩约 99 行（13785→11109 字节，`decision_nodes.py` 至此仅余 `DecisionNodeEngine` 编排层）。

### 验证

- `py_compile` 通过（`signal_context.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes._get_signal_seq is signal_context._get_signal_seq`、`decision_nodes.has_background_limit_path is signal_context.has_background_limit_path`、`decision_nodes.is_planned_limit_order is signal_context.is_planned_limit_order`（**同一对象**），且三者 `inspect.getmodule(...).__name__ == "pa_agent.ai.signal_context"`（"IDENTITY_OK"）。
- **测试站点 import 完整性**：以 AST 提取 `tests/unit/*.py`（含 `test_decision_nodes_judges.py`/`test_order_method_router.py` 等）与 `stage2_normalizer.py`/`prompt_assembler.py` 中全部 `from pa_agent.ai.decision_nodes import ...` 名字（TOTAL=18），逐一断言 `hasattr(decision_nodes, name)`（MISSING 为空，"AST_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`signal_context` 不经 PyQt6 链可直接跑）：从 `git show HEAD:` 取拆分前的三个辅助函数 `exec` 重建为 `old_*`，与经**重导出的 `decision_nodes.*` 路径**（即 `apply_stage2`/测试实际调用路径）在 **51224 个可控用例**（`is_planned_limit_order`/`has_background_limit_path` 的 order_type×§9.0P answer×strength×freshness×quality×pattern×entry_bar×signal_bar 组合，加 `_get_signal_seq` 的 bar 值×bar_analysis 形态组合）上逐例断言返回值**完全一致**（CASES=51224 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **14** 条（8×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）→ 拆分后 `decision_nodes.py`（12：8×RUF001、2×RUF100、1×I001、1×RUF005）+ 新增 `signal_context.py`（2：1×RUF100、1×SIM103）合计 **14**，**逐类别完全一致、零净新增告警**（`SIM103`「return bool 可简化」与其中 1 条 `RUF100`（`# noqa: BLE001`）随 `is_planned_limit_order`/`_get_signal_seq` 迁入新模块）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。
- 说明：本机缺 `hypothesis`/`PyQt6` 依赖，`test_decision_nodes_judges.py`（import hypothesis）与经 `pa_agent.util.__init__`→`event_bus`→PyQt6 的链在本机无法收集，属**既有环境缺口**，与本轮纯结构搬迁无关；`test_order_method_router.py::test_model_breakout_preserved_for_broad_channel` 的失败经 `git stash` 将 `decision_nodes.py` 还原至 HEAD 复现，确认为**第二十六轮既有失败**（位于 `route_order_method`，本轮未触碰），非本轮引入。

---

## [Unreleased] — 2026-07-14（第二十六轮：继续拆分 decision_nodes，提取 order_method_router §11 下单方式路由 R-M3-10）

本轮为**大文件拆分 M3 的第十刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇、第二十二轮 `direction_judge.py` §2.3 方向判定器、第二十三轮 `diagnostic_judges.py` §1 诊断判定器簇、第二十四轮 `always_in_judges.py` §2.4/§2.5 判定器簇、第二十五轮 `override_arbiter.py` 受控 override 裁决簇）。前九刀先后抽走了「共享底层（常量/几何/闸门/结果层）」「全部 section-judge 簇」与「override 裁决层」，本刀转向**§11 下单方式路由层**——`OrderMethodRouter` 簇。它是 `DecisionNodeEngine.apply_stage2` 用来「把阶段一 `cycle_position`（及模型自身的 order_type / entry_basis 提示）映射为最终下单方式（市价单/突破单/限价单/不下单）并生成 §11 trace 节点」的确定性路由。选它作为下一刀的关键动机：① 它是一个**高内聚自足簇**——单个大函数 `route_order_method` + 模块级 `_CYCLE_ORDER_METHOD` 路由表（cycle_position → 候选下单方式），内嵌 `_trace_answer`/`_sec14_violated`/`_has_trade_prices` 辅助随函数整体迁出、`_METHOD_NODE`/`_node_reasons` 为函数内局部表，不与其他簇共享；② 依赖全部收敛到**唯一叶子模块 `trace_nodes`**——只 import `_coerce_dict`/`_coerce_trace_list`/`NodeFill`，**不引用任何 judge、不引用 override 裁决、不回依赖 `decision_nodes`**（无环前提：`order_method_router` ← `decision_nodes`），故可一刀干净剥离而不触发循环导入。至此 `decision_nodes.py` 仅余 SignalBarJudge 辅助（`_get_signal_seq`/`has_background_limit_path`/`is_planned_limit_order`）与 `DecisionNodeEngine` 编排层，大文件拆分接近尾声。

### 代码清理

- **新增 `pa_agent/ai/order_method_router.py`（§11 下单方式路由簇模块）**：把 `_CYCLE_ORDER_METHOD` 路由表与 `route_order_method` **逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、§10.3/§14 安全闸门短路、spike_ending/breakout_fallback 例外分支、`_METHOD_NODE`/`_node_reasons` 局部表与 `NodeFill` 节点 answer 取值及原文件特有的双空行排版），import 仅 `from __future__ import annotations` + `typing.Any` + `from pa_agent.ai.trace_nodes import NodeFill, _coerce_dict, _coerce_trace_list`，无其他项目依赖、无副作用（无 `logger`——本簇原本不记日志）。模块 docstring 说明其「order-method-router 簇」定位、唯一叶子依赖 `trace_nodes` 与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `order_method_router` 导入 `route_order_method`**：删除原 `_CYCLE_ORDER_METHOD` + `route_order_method` 定义块（含 `# ── OrderMethodRouter` 分隔头，src[4377:12455]），在文件顶部 import 组新增 `from pa_agent.ai.order_method_router import route_order_method`（字母序排在 `direction_judge` 之后、`override_arbiter` 之前，单一 import 块内避免新增 I001 区块）。`route_order_method` 在 `DecisionNodeEngine.apply_stage2` 链 `sec11_fills = route_order_method(stage1_json, decision, decision_trace)` **确有引用**，属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import route_order_method` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_order_method_router.py` 无需改动）。`trace_nodes` 的三个 import（`_coerce_dict`/`_coerce_trace_list`/`NodeFill`）在 `decision_nodes.py` 内仍被 `apply_stage2` 等**确有引用**，故**保持正常 import**（不转重导出）。文件进一步收缩约 357 行（23190→14273 字节）。

### 验证

- `py_compile` 通过（`order_method_router.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes.route_order_method is order_method_router.route_order_method`（**同一对象**）、`inspect.getmodule(decision_nodes.route_order_method).__name__ == "pa_agent.ai.order_method_router"`、`decision_nodes.NodeFill is order_method_router.NodeFill`，且 `_CYCLE_ORDER_METHOD` `hasattr(decision_nodes, name) is False`、`hasattr(order_method_router, name) is True`（"IDENTITY_OK"）。
- **测试站点 import 完整性**：以 AST 提取 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py`/`test_order_method_router.py`/`test_trend_context.py` 与 `prompt_assembler.py`/`stage2_normalizer.py` 中全部 `from pa_agent.ai.decision_nodes import ...` 名字（TOTAL=18），逐一断言 `hasattr(decision_nodes, name)`（MISSING 为空，"AST_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`order_method_router`/`trace_nodes` 不经 PyQt6 链可直接跑）：从 `git show HEAD:` 取拆分前的 OrderMethodRouter 块 `exec` 重建为 `old_route`（注入叶子依赖到命名空间），与经**重导出的 `decision_nodes.route_order_method` 路径**（即 `apply_stage2`/测试实际调用路径）在 **2400 个可控用例**（`cycle_position` 10 值 × `spike_stage` 5 值 × `order_type` 4 值 × §10.3 answer 3 值 × has_basis 2 值 × has_trade_prices 2 值）上逐例断言返回 `NodeFill` 列表（`node_id`/`answer`/`reason`/`bar_range`/`branch`/`section`）与被就地改写的 `decision.order_type` 的归一化输出**逐字节一致**（CASES=2400 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **31** 条（25×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）→ 拆分后 `decision_nodes.py`（14：8×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）+ 新增 `order_method_router.py`（17：17×RUF001）合计 **31**，**逐类别完全一致、零净新增告警**（17×RUF001 随中文 reason 串迁入新模块；新模块因无 `logger` 行，section-header 注释初次紧邻 import 块触发 1 条 I001，已用 `ruff --select I001 --fix` 收敛为单空行、恢复零净新增；`decision_nodes.py` 的 RUF100 仍为 3——三个 `# noqa: F401` 均生效未被判为冗余）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十五轮：继续拆分 decision_nodes，提取 override_arbiter 受控 override 裁决簇 R-M3-9）

本轮为**大文件拆分 M3 的第九刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇、第二十二轮 `direction_judge.py` §2.3 方向判定器、第二十三轮 `diagnostic_judges.py` §1 诊断判定器簇、第二十四轮 `always_in_judges.py` §2.4/§2.5 判定器簇）。前八刀先后抽走了「共享底层（常量/几何/闸门/结果层）」与「全部 section-judge 簇」，本刀转向**决策合并与受控 override 裁决层**——`OverrideArbiter` 簇。它是 `DecisionNodeEngine` 在 `apply_stage1`/`apply_stage2` 末尾用来「把程序算出的决策节点并入 AI 的 gate_trace / decision_trace，并对 AI 提交的 `node_overrides` 施加锁定/安全闸门/可覆盖规则集裁决」的确定性机器。选它作为下一刀的关键动机：① 它是一个**高内聚自足簇**——9 个函数（4 公开 `merge_program_nodes`/`merge_program_nodes_head`/`apply_overrides`/`write_override_trace` + 5 私有 `_conservativeness_rank`/`_node_id_sort_key`/`_validate_dir_override`/`_sync_always_in_from_24_override`/`_sync_order_type_from_11_override`）逻辑闭环、互相调用但**不被其他 judge 引用**；② 依赖全部收敛到**叶子模块 + call-time import**——只 import `_coerce_trace_list`（来自 `trace_nodes` 叶子）与 5 个 override 权限集常量（`LOCKED_NODES`/`OVERRIDABLE_NODES`/`AI_PRIMARY_NODES`/`AI_PRIMARY_SUPPLEMENT_NODES`/`SAFETY_GATE_NODES`，来自 `decision_thresholds` 叶子），唯一的 `TRACE_ANSWERS`（来自 `decision_tree`）走 `apply_overrides` 函数体内 **call-time import**——因 `decision_tree` 不 import `decision_nodes`，故 `override_arbiter` ← `decision_nodes` 无环（保留原 call-time 位置即可干净剥离，不触发循环导入）。至此 `decision_nodes.py` 仅余 SignalBarJudge 辅助（`_get_signal_seq`/`has_background_limit_path`/`is_planned_limit_order`）、OrderMethodRouter（`route_order_method`）与 `DecisionNodeEngine` 编排层。

### 代码清理

- **新增 `pa_agent/ai/override_arbiter.py`（受控 override 裁决簇模块）**：把 `_conservativeness_rank`、`write_override_trace`、`_node_id_sort_key`、`merge_program_nodes`、`merge_program_nodes_head`、`apply_overrides`、`_validate_dir_override`、`_sync_always_in_from_24_override`、`_sync_order_type_from_11_override` 九者**逐字节搬迁**至新模块（保留全部 docstring、中文日志/reason 串、合并模式区分与 override 规则顺序、`program_answer`/`program_branch`/`override_reason`/`overridden_by_ai` 等节点键写入、原文件特有的双空行排版），import 仅 `from __future__ import annotations` + `logging` + `typing.Any` + `from pa_agent.ai.decision_thresholds import (5 个 override 权限集常量)` + `from pa_agent.ai.trace_nodes import _coerce_trace_list`，`TRACE_ANSWERS` 保留在 `apply_overrides` 函数体内 call-time import（打破与 `decision_tree` 的潜在环），无其他项目依赖、无副作用。模块 docstring 说明其「override-arbiter 簇」定位、叶子依赖 + call-time import 打破环的动机与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `override_arbiter` 导入合并/裁决函数**：删除原 9 个函数定义块（含 `# ── OverrideArbiter` 分隔头，src[12362:26284]），在文件顶部 import 组新增 `from pa_agent.ai.override_arbiter import (apply_overrides, merge_program_nodes, merge_program_nodes_head, write_override_trace)`（字母序排在 `direction_judge` 之后、`preflight` 之前，单一 import 块内避免新增 I001 区块）。`apply_overrides`/`merge_program_nodes`/`merge_program_nodes_head` 在 `DecisionNodeEngine.apply_stage1`/`apply_stage2` 链中**确有引用**，属**正常 import**（非纯重导出，无需 `# noqa: F401`）；`write_override_trace` 迁出后在本文件内已无引用，但 `test_decision_nodes_judges.py` 仍从 `decision_nodes` 命名空间 import 它——故补 `# noqa: F401`（标注「re-exported for tests; used in override_arbiter」），保持既有测试站点逐字节兼容。因 `from pa_agent.ai.decision_nodes import apply_overrides` 等站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/`、`prompt_assembler.py`、`stage2_normalizer.py` 均无需改动）。
- **5 个 override 权限集常量从 `decision_nodes` import 块剪除**：`AI_PRIMARY_NODES`/`AI_PRIMARY_SUPPLEMENT_NODES`/`LOCKED_NODES`/`OVERRIDABLE_NODES`/`SAFETY_GATE_NODES` 随 9 函数迁出后在 `decision_nodes.py` 内**已无任何引用点**，且全仓库**无任何站点**从 `decision_nodes` 命名空间 import 它们（唯一消费方即迁出的 override_arbiter，直接从 `decision_thresholds` import），故直接剪除、不做重导出（无兼容风险）。`ALWAYS_IN_SAME_SIDE_RATIO`/`BAR_COUNT_THRESHOLD`/`SIGNAL_BAR_LONG_ATR_RATIO`（仍被测试从 `decision_nodes` 命名空间 import）**保留为 `# noqa: F401` 纯重导出**。文件进一步收缩约 597 行（37343→23190 字节）。

### 验证

- `py_compile` 通过（`override_arbiter.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes.apply_overrides is override_arbiter.apply_overrides`、`decision_nodes.merge_program_nodes is override_arbiter.merge_program_nodes`、`decision_nodes.merge_program_nodes_head is override_arbiter.merge_program_nodes_head`、`decision_nodes.write_override_trace is override_arbiter.write_override_trace`（**同一对象**）、`inspect.getmodule(decision_nodes.apply_overrides).__name__ == "pa_agent.ai.override_arbiter"`（"IDENTITY_OK"）。
- **测试站点 import 完整性**：以 AST 提取 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py`/`test_order_method_router.py`/`test_trend_context.py` 与 `prompt_assembler.py`/`stage2_normalizer.py` 中全部 `from pa_agent.ai.decision_nodes import ...` 名字（TOTAL=18），逐一断言 `hasattr(decision_nodes, name)`（MISSING 为空，"AST_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`override_arbiter`/`decision_thresholds`/`trace_nodes` 不经 PyQt6 链可直接跑）：从 `git show HEAD~1:` 取拆分前的 OverrideArbiter 块 `exec` 重建为 `old_*`（注入叶子依赖到命名空间），与经**重导出的 `decision_nodes.*` 路径**（即 `apply_stage1`/`apply_stage2`/测试实际调用路径）在 **46 个可控用例**（`write_override_trace` 16 个 answer×branch 组合、`merge_program_nodes`/`merge_program_nodes_head` 各 4 个 trace 场景、`apply_overrides` 11 个 override 规则场景 × stage1/stage2）上逐例断言返回节点列表与 `out`（`direction`/`bar_analysis.always_in`/`decision.order_type`）的 `json.dumps(sort_keys=True)` 归一化输出**逐字节一致**（CASES=46 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **37** 条（31×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）→ 拆分后 `decision_nodes.py`（31：25×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）+ 新增 `override_arbiter.py`（6：6×RUF001）合计 **37**，**逐类别完全一致、零净新增告警**（6×RUF001 随中文日志/reason 串迁入新模块；`decision_nodes.py` 的 RUF100 仍为 3——`ALWAYS_IN_SAME_SIDE_RATIO`/`BAR_COUNT_THRESHOLD`/`SIGNAL_BAR_LONG_ATR_RATIO` 三个 `# noqa: F401` 均生效未被判为冗余，未因剪除 5 个 override 常量而产生新冗余 noqa）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十四轮：继续拆分 decision_nodes，提取 always_in_judges §2.4/§2.5 判定器簇 R-M3-8）

本轮为**大文件拆分 M3 的第八刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇、第二十二轮 `direction_judge.py` §2.3 方向判定器、第二十三轮 `diagnostic_judges.py` §1 诊断判定器簇），是**第四个被剥离的 section-judge 簇**。本刀选 **§2「趋势状态」两判定器**——`judge_always_in`（§2.4 Always-In 状态，近端 K8-K1 主判 + 背景 K20-K1 参考的双窗口 Brooks 对齐）与 `judge_momentum_strength`（§2.5 动量强度，双窗口三近端信号：趋势棒占优、K 线重叠、回撤深度）。选它们作为下一刀的关键动机：① 这两个 judge **共享私有辅助 `_max_pullback_atr`**（`_eval_always_in_gates` 与 `judge_momentum_strength` 均调用），故整簇一起迁出——连同 §2.4 专属的 `_weighted_ema_side_weights`/`_eval_always_in_gates` 与共享的 `_max_pullback_atr` 一并搬迁，避免共享辅助被跨模块拆散；② 依赖全部为**叶子模块**——`NodeFill`（来自 `trace_nodes`）、几何原语 `_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio`（来自 `bar_geometry`）、Always-In/动量阈值常量（来自 `decision_thresholds`），**不引用任何其他 judge、不回依赖 `decision_nodes`**（无环前提：`always_in_judges` ← `decision_nodes`），故可一刀干净剥离而不触发循环导入。至此 `decision_nodes.py` 内已无任何 section-judge 定义（全部委托各子模块），仅余 SignalBarJudge 辅助（`_get_signal_seq`/`has_background_limit_path`/`is_planned_limit_order`）、OrderMethodRouter、OverrideArbiter 与 `DecisionNodeEngine` 编排层。

### 代码清理

- **新增 `pa_agent/ai/always_in_judges.py`（§2.4/§2.5 判定器簇模块）**：把 `_weighted_ema_side_weights`、`_eval_always_in_gates`、`_max_pullback_atr`、`judge_always_in`、`judge_momentum_strength` 五者**逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、双窗口 gate/评分算术、`answer`/`branch`/`bar_range` 取值与原文件特有的双空行排版），import 仅 `from __future__ import annotations` + `math` + `typing.Any` + `from pa_agent.ai.bar_geometry import (_count_trend_bars, _find_swings, _mean_overlap_ratio)` + `from pa_agent.ai.decision_thresholds import (...10 个 Always-In/动量/斜率阈值...)` + `from pa_agent.ai.trace_nodes import NodeFill`，无其他项目依赖、无副作用。模块 docstring 说明其「第四个被剥离的 section-judge 簇」定位、因 `_max_pullback_atr` 共享而整簇一起迁出的动机、叶子依赖与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `always_in_judges` 导入这两个 judge**：删除原 5 个函数定义块（含 `# ── AlwaysInJudge`/`# ── MomentumStrengthJudge` 分隔头），在文件顶部 import 组新增 `from pa_agent.ai.always_in_judges import judge_always_in, judge_momentum_strength`（字母序排在最前——`bar_geometry` 已随本轮迁出而整块剪除，故 `always_in_judges` 成为 `pa_agent.ai` 组首个 import，置于 `decision_thresholds` 之前，单一 import 块内避免新增 I001 区块）。这两个名字在 `decision_nodes.py` 函数体内**确有引用**（`apply_stage2` 链 `fill_24 = judge_always_in(frame)`、`fill_25 = judge_momentum_strength(frame, direction=direction)`），属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import judge_always_in` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_decision_nodes_judges.py`、`test_trend_context.py`、`prompt_assembler.py` 均无需改动）。
- **`bar_geometry` 整块 import 与 `import math` 从 `decision_nodes` 剪除，9 个 Always-In/动量常量剪除，`ALWAYS_IN_SAME_SIDE_RATIO` 转纯重导出**：`_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio` 随五函数迁出后在 `decision_nodes.py` 内**已无任何引用点**（其他消费方如 `trend_context.py`/`direction_judge.py`/`diagnostic_judges.py` 直接从 `bar_geometry` import），故整块 import 直接剪除；`import math` 亦随之无引用而剪除。9 个常量——`ALWAYS_IN_NEAR_SAME_SIDE_RATIO`/`ALWAYS_IN_NEAR_WINDOW`/`ALWAYS_IN_PULLBACK_ATR_RATIO`/`ALWAYS_IN_WINDOW`/`EMA_SLOPE_LOOKBACK`/`MOMENTUM_OVERLAP_WEAK`/`MOMENTUM_PULLBACK_DEEP_ATR`/`MOMENTUM_TREND_BAR_MIN_RATIO`/`MOMENTUM_TREND_RATIO_STRONG`——迁出后在本文件内均无引用、且全仓库无站点从 `decision_nodes` 命名空间取用（其他消费方直接从 `decision_thresholds` import），故直接剪除、不做重导出（无兼容风险）。`ALWAYS_IN_SAME_SIDE_RATIO` 随 `judge_always_in` 迁出后在本文件内亦无引用，但 `test_decision_nodes_judges.py` 仍从 `decision_nodes` 命名空间 import 它——故在 `decision_thresholds` 的 import 行上补 `# noqa: F401`（标注「re-exported for tests; used in always_in_judges」），保持既有测试站点逐字节兼容。文件进一步收缩约 415 行（50692→37343 字节）。

### 验证

- `py_compile` 通过（`always_in_judges.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes.judge_always_in is always_in_judges.judge_always_in`、`decision_nodes.judge_momentum_strength is always_in_judges.judge_momentum_strength`（**同一对象**）、`decision_nodes.NodeFill is always_in_judges.NodeFill`、`inspect.getmodule(decision_nodes.judge_always_in).__name__ == "pa_agent.ai.always_in_judges"`，且 9 个已剪除常量 + 3 个几何原语 + 3 个私有辅助（`_weighted_ema_side_weights`/`_eval_always_in_gates`/`_max_pullback_atr`）`hasattr(decision_nodes, name) is False`、保留的 `ALWAYS_IN_SAME_SIDE_RATIO`/`BAR_COUNT_THRESHOLD`/`SIGNAL_BAR_LONG_ATR_RATIO` `hasattr is True`（"IDENTITY_OK"）。
- **测试站点 import 完整性**：以 AST 提取 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py`/`test_trend_context.py` 与 `prompt_assembler.py` 中全部 `from pa_agent.ai.decision_nodes import ...` 名字，逐一断言 `hasattr(decision_nodes, name)`（MISSING 为空——含 `ALWAYS_IN_SAME_SIDE_RATIO`/`judge_always_in` 及其余既有名）。
- **运行时行为对比**（本机 `decision_nodes`/`always_in_judges`/`bar_geometry`/`data.base` 不经 PyQt6 链可直接跑）：从 `git show HEAD:` 取拆分前的五函数源码 `exec` 重建为 `old_*`，与经**重导出的 `decision_nodes.*` 路径**（即 `apply_stage2`/测试实际调用路径）在 **36 个可控帧**（`n∈{20,25,30,50}` × `ema_slope∈{up,down,flat}` × `close_pattern∈{up,down,flat}`）上逐例断言 `judge_always_in`（1 次/帧）与 `judge_momentum_strength`（`direction∈{bullish,bearish,neutral}` 各 1 次/帧）的 `NodeFill`（`node_id`/`answer`/`reason`/`bar_range`/`branch`/`section`）输出**逐字节一致**（CASES=144 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **128** 条（119×RUF001、3×RUF100、1×I001、1×RUF002、1×RUF005、1×SIM103、1×SIM105、1×SIM114）→ 拆分后 `decision_nodes.py`（37：31×RUF001、3×RUF100、1×I001、1×RUF005、1×SIM103）+ 新增 `always_in_judges.py`（91：88×RUF001、1×RUF002、1×SIM105、1×SIM114）合计 **128**，**逐类别完全一致、零净新增告警**（88×RUF001+1×RUF002 随中文 reason 串/注释/docstring 迁入新模块，1×SIM105+1×SIM114 随 `judge_always_in`/`_eval_always_in_gates` 迁出；`decision_nodes.py` 的 RUF100 仍为 3——新增的 `ALWAYS_IN_SAME_SIDE_RATIO` `# noqa: F401` 生效未被判为冗余，未因剪除 9 常量/几何块而产生新冗余 noqa）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十三轮：继续拆分 decision_nodes，提取 diagnostic_judges §1.1/§1.3 诊断判定器簇 R-M3-7）

本轮为**大文件拆分 M3 的第七刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇、第二十二轮 `direction_judge.py` §2.3 方向判定器），是**第三个被剥离的 section-judge 簇**。本刀选 **§1「市场诊断」判定器簇**——`judge_data_sufficiency`（§1.1 数据充分性）与 `judge_market_chaos`（§1.3 极端混乱诊断）：两者是 `DecisionNodeEngine.apply_stage1` 依次填充的两个 §1 诊断节点，在源文件中相邻且逻辑内聚。选它们作为下一刀的关键动机：① 两者均为**确定性纯函数、无跨 judge 共享的私有辅助**——`judge_data_sufficiency` 仅记录已收盘 K 线数（前置闸门已通过，恒 `是`）；`judge_market_chaos` 恒返回 `否`（extreme_tr 需 AI 综合判断、不设硬性程序门槛），但在 reason 串内嵌三项客观混乱信号计数（EMA 斜率平坦、K 线重叠高、无方向共识）供 AI 决定是否提交 §1.3=是 覆盖；② 依赖全部为**叶子模块**——`NodeFill`（来自 `trace_nodes`）、几何原语 `_count_trend_bars`/`_mean_overlap_ratio`（来自 `bar_geometry`）、诊断阈值常量（来自 `decision_thresholds`），**不引用任何其他 judge、不回依赖 `decision_nodes`**（无环前提：`diagnostic_judges` ← `decision_nodes`），故可一刀干净剥离而不触发循环导入。（注：AlwaysIn 判定器簇因其私有辅助 `_max_pullback_atr` 被 §2.5 `judge_momentum_strength` 共享引用，尚未构成干净单刀，留待后续先抽共享辅助再拆。）

### 代码清理

- **新增 `pa_agent/ai/diagnostic_judges.py`（§1 诊断判定器簇模块）**：把 `judge_data_sufficiency` 与 `judge_market_chaos` **逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、`chaos_score` 算术、三项混乱信号描述串与 `answer`/`bar_range` 取值及原文件特有的双空行排版），import 仅 `from __future__ import annotations` + `math` + `typing.Any` + `from pa_agent.ai.bar_geometry import _count_trend_bars, _mean_overlap_ratio` + `from pa_agent.ai.decision_thresholds import (...7 个诊断/窗口/斜率/趋势棒阈值...)` + `from pa_agent.ai.trace_nodes import NodeFill`，无其他项目依赖、无副作用。模块 docstring 说明其「第三个被剥离的 section-judge 簇」定位、叶子依赖与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `diagnostic_judges` 导入这两个 judge**：删除原 `judge_data_sufficiency`/`judge_market_chaos` 定义块（含 `# ── DataSufficiencyJudge`/`# ── MarketChaosJudge` 分隔头），在文件顶部 import 组新增 `from pa_agent.ai.diagnostic_judges import judge_data_sufficiency, judge_market_chaos`（字母序排在 `decision_thresholds` 之后、`direction_judge` 之前，单一 import 块内，避免新增 I001 区块）。这两个名字在 `decision_nodes.py` 函数体内**确有引用**（`apply_stage1` 链 `fill_11 = judge_data_sufficiency(frame)`、`fill_13 = judge_market_chaos(frame)`），属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import judge_data_sufficiency` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_decision_nodes_judges.py`、`prompt_assembler.py` 均无需改动）。
- **3 个 CHAOS_*/1 个 TREND_BAR_DOMINANCE_RATIO 常量从 `decision_nodes` import 块剪除，`BAR_COUNT_THRESHOLD` 转为纯重导出**：`CHAOS_DIRECTION_SCORE_MAX`/`CHAOS_EMA_FLAT_ATR_RATIO`/`CHAOS_OVERLAP_THRESHOLD`/`TREND_BAR_DOMINANCE_RATIO` 随两 judge 迁出后在 `decision_nodes.py` 内**已无任何引用点**，且全仓库**无任何站点**从 `decision_nodes` 命名空间 import 它们（其他消费方如 `trend_context.py`/`direction_judge.py` 直接从 `decision_thresholds` import），故直接剪除、不做重导出（无兼容风险）。`BAR_COUNT_THRESHOLD` 随 `judge_data_sufficiency` 迁出后在本文件内亦无引用，但 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py` 仍从 `decision_nodes` 命名空间 import 它——故在 `decision_thresholds` 的 import 行上补 `# noqa: F401`（标注「re-exported for tests; used in diagnostic_judges」），保持既有测试站点逐字节兼容。`ALWAYS_IN_WINDOW`/`EMA_SLOPE_LOOKBACK`（仍被 AlwaysIn/Momentum 引用）**保留**。文件进一步收缩约 175 行（56635→54416 字节）。

### 验证

- `py_compile` 通过（`diagnostic_judges.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes.judge_data_sufficiency is diagnostic_judges.judge_data_sufficiency`、`decision_nodes.judge_market_chaos is diagnostic_judges.judge_market_chaos`（**同一对象**）、`decision_nodes.NodeFill is diagnostic_judges.NodeFill`、`inspect.getmodule(decision_nodes.judge_data_sufficiency).__name__ == "pa_agent.ai.diagnostic_judges"`，且 4 个已剪除常量（3×CHAOS_*、TREND_BAR_DOMINANCE_RATIO）`hasattr(decision_nodes, name) is False`、保留的 `BAR_COUNT_THRESHOLD` `hasattr is True`（"IDENTITY_OK"）。
- **测试站点 import 完整性**：以 AST 提取 `test_decision_nodes_judges.py`/`test_decision_nodes_preflight.py`/`test_trend_context.py` 与 `prompt_assembler.py` 中全部 `from pa_agent.ai.decision_nodes import ...` 名字，逐一断言 `hasattr(decision_nodes, name)`（MISSING 为空——含 `BAR_COUNT_THRESHOLD`/`judge_data_sufficiency`/`judge_market_chaos` 及其余既有名）。
- **运行时行为对比**（本机 `decision_nodes`/`diagnostic_judges`/`data.base` 不经 PyQt6 链可直接跑）：从 `git show HEAD:` 取拆分前的 `judge_data_sufficiency`/`judge_market_chaos` 源码 `exec` 重建为 `old_*`，与经**重导出的 `decision_nodes.*` 路径**（即 `apply_stage1`/测试实际调用路径）在 **36 个可控帧**（`n∈{20,25,30,50}` × `ema_slope∈{up,down,flat}` × `close_pattern∈{up,down,flat}`）上逐例断言两 judge 的 `NodeFill`（`node_id`/`answer`/`reason`/`bar_range`/`branch`/`section`）输出**逐字节一致**（CASES=36 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **150** 条（138×RUF001、4×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM114）→ 拆分后 `decision_nodes.py`（128：119×RUF001、1×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM114）+ 新增 `diagnostic_judges.py`（22：19×RUF001、3×RUF002）合计 **150**，**逐类别完全一致、零净新增告警**（19×RUF001+3×RUF002 随中文 reason 串/注释/docstring 迁入新模块；`decision_nodes.py` 的 RUF100 仍为 3——`SIGNAL_BAR_LONG_ATR_RATIO` 与新增的 `BAR_COUNT_THRESHOLD` `# noqa: F401` 均生效未被判为冗余，未因剪除 4 常量而产生新冗余 noqa；新模块 import 块间距按 ruff `I001` 收敛为单空行）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十二轮：继续拆分 decision_nodes，提取 direction_judge §2.3 方向判定器 R-M3-6）

本轮为**大文件拆分 M3 的第六刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层、第二十一轮 `signal_bar_judges.py` §9 信号棒判定器簇），是**第二个被剥离的 section-judge**。本刀选 **§2.3「方向」判定器** `judge_direction`——它是一个**完全自足的单函数**：五信号投票（EMA 斜率、加权收盘重心、波段结构 HH/HL vs LL/LH、趋势棒占优、K 线重叠比）+ 中窗口确认过滤，输出 `(direction, NodeFill)` 填充 §2.3 节点。选它作为下一刀的关键动机：① 它是**单函数、无跨 judge 共享的私有辅助**（内部 `_weighted_avg`/`_weighted_avg_med` 为函数内嵌套定义，随函数整体迁出，不影响其他 judge）；② 依赖全部为**叶子模块**——`NodeFill`（来自 `trace_nodes`）、几何原语 `_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio`（来自 `bar_geometry`）、方向阈值常量（来自 `decision_thresholds`），**不引用任何其他 judge、不回依赖 `decision_nodes`**（无环前提：`direction_judge` ← `decision_nodes`），故可一刀干净剥离而不触发循环导入。（注：AlwaysIn 判定器簇因其私有辅助 `_max_pullback_atr` 被 §2.5 `judge_momentum_strength` 共享引用，尚未构成干净单刀，留待后续先抽共享辅助再拆。）

### 代码清理

- **新增 `pa_agent/ai/direction_judge.py`（§2.3 方向判定器模块）**：把 `judge_direction` **逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、`score` 算术、`answer`/`branch`/`bar_range` 取值与嵌套 `_weighted_avg`/`_weighted_avg_med` 辅助），import 仅 `from __future__ import annotations` + `math` + `typing.Any` + `from pa_agent.ai.bar_geometry import (_count_trend_bars, _find_swings, _mean_overlap_ratio)` + `from pa_agent.ai.decision_thresholds import (...9 个方向/重叠/斜率/趋势棒阈值...)` + `from pa_agent.ai.trace_nodes import NodeFill`，无其他项目依赖、无副作用。模块 docstring 说明其「第二个被剥离的 section-judge」定位、叶子依赖与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `direction_judge` 导入 `judge_direction`**：删除原 `judge_direction` 定义块（含 `# ── DirectionJudge` 分隔头），在文件顶部 import 组新增 `from pa_agent.ai.direction_judge import judge_direction`（字母序排在 `decision_thresholds` 之后、`preflight` 之前，单一 import 块内，避免新增 I001 区块）。该名字在 `decision_nodes.py` 函数体内**确有引用**（`apply_stage2` 链 `direction, fill_23 = judge_direction(frame)`），属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import judge_direction` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_decision_nodes_judges.py`、`test_trend_context.py`、`prompt_assembler.py` 均无需改动）。
- **7 个 DIRECTION_*/OVERLAP_* 常量从 `decision_nodes` import 块剪除**：`DIRECTION_BEAR_THRESHOLD`/`DIRECTION_BULL_THRESHOLD`/`DIRECTION_STRONG_SHORT_SCORE`/`DIRECTION_WINDOW`/`DIRECTION_WINDOW_MED`/`OVERLAP_HIGH_THRESHOLD`/`OVERLAP_LOW_THRESHOLD` 随 `judge_direction` 迁出后在 `decision_nodes.py` 内**已无任何引用点**，且全仓库**无任何站点**从 `decision_nodes` 命名空间 import 这些常量（其他消费方如 `trend_context.py` 直接从 `decision_thresholds` import），故直接剪除、不做重导出（无兼容风险）。`EMA_SLOPE_LOOKBACK`（仍被 `judge_market_chaos`/AlwaysIn 引用）与 `TREND_BAR_DOMINANCE_RATIO`（仍被 `judge_market_chaos` 引用）**保留**。文件进一步收缩 307 行（74588→61701 字节）。

### 验证

- `py_compile` 通过（`direction_judge.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python` 断言 `decision_nodes.judge_direction is direction_judge.judge_direction`（**同一对象**）、`decision_nodes.NodeFill is direction_judge.NodeFill`、`inspect.getmodule(decision_nodes.judge_direction).__name__ == "pa_agent.ai.direction_judge"`，且 7 个已剪除常量 `hasattr(decision_nodes, name) is False`、保留的 `EMA_SLOPE_LOOKBACK`/`TREND_BAR_DOMINANCE_RATIO` `hasattr is True`（"IDENTITY_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`direction_judge`/`data.base` 不经 PyQt6 链可直接跑）：从 `git show HEAD:` 取拆分前的 `judge_direction` 源码 `exec` 重建为 `old_judge`，与经**重导出的 `decision_nodes.judge_direction` 路径**在 **36 个可控帧**（`n∈{20,25,30,50}` × `ema_slope∈{up,down,flat}` × `close_pattern∈{up,down,flat}`）上逐例断言 `(direction, NodeFill)` 输出**逐字节一致**（CASES=36 MISMATCHES=0，"RUNTIME_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **180** 条（161×RUF001、6×RUF003、5×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM114）→ 拆分后 `decision_nodes.py`（150：138×RUF001、4×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM114）+ 新增 `direction_judge.py`（30：23×RUF001、6×RUF003、1×RUF002）合计 **180**，**逐类别完全一致、零净新增告警**（23×RUF001+6×RUF003+1×RUF002 随中文 reason 串/注释/docstring 迁入新模块；`decision_nodes.py` 的 RUF100 仍为 3——`SIGNAL_BAR_LONG_ATR_RATIO` `# noqa: F401` 生效未被判为冗余，未因剪除 7 常量而产生新冗余 noqa）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十一轮：继续拆分 decision_nodes，提取 signal_bar_judges §9 判定器簇 R-M3-5）

本轮为**大文件拆分 M3 的第五刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门、第二十轮 `trace_nodes.py` 结果层），是**首次剥离 section-judge 本身**。前四刀已把各 judge 共享的「底层依赖」（常量/几何/闸门/`NodeFill` 结果层）抽成无环叶子模块，为拆 judge 铺好路。本刀选**最自足的 §9「信号棒」判定器簇**作为第一个 judge 模块：`judge_signal_bar_closed`（§9.1 信号棒恒已收盘）、`judge_signal_bar_direction`（§9.2 bar_type 与下单方向一致性，外包棒降级为「弱」集合并告警）、`judge_signal_bar_length`（§9.3 过长棒判定，对比 `SIGNAL_BAR_LONG_ATR_RATIO`）、`judge_follow_through`（§9.5 follow_through_1_2 映射），连同 §9.2 的 4 个 bar-type 常量（`_LONG_BAR_TYPES`/`_SHORT_BAR_TYPES`/`_LONG_BAR_TYPES_WEAK`/`_SHORT_BAR_TYPES_WEAK`）。选它作为第一个 judge 的关键动机：这簇**只依赖叶子模块**——`NodeFill`（来自 `trace_nodes`）与 `SIGNAL_BAR_LONG_ATR_RATIO`（来自 `decision_thresholds`），**不引用任何其他 judge、不回依赖 `decision_nodes`**（无环前提：`signal_bar_judges` ← `decision_nodes`），故能一刀干净剥离而不触发循环导入。

### 代码清理

- **新增 `pa_agent/ai/signal_bar_judges.py`（§9 信号棒判定器簇模块）**：把上述 4 个 judge 与 4 个 bar-type 常量**逐字节搬迁**至新模块（保留全部 docstring、中文 reason 串、`answer`/`bar_range` 取值与原文件特有的双空行排版），import 仅 `from __future__ import annotations` + `typing.Any` + `from pa_agent.ai.decision_thresholds import SIGNAL_BAR_LONG_ATR_RATIO` + `from pa_agent.ai.trace_nodes import NodeFill`，无其他项目依赖、无副作用。模块 docstring 说明其「首个被剥离的 judge 簇」定位、叶子依赖与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `signal_bar_judges` 导入这 4 个 judge**：删除原 4 个 judge 定义块与 §9.2 的 4 个常量块，在文件顶部 import 组新增 `from pa_agent.ai.signal_bar_judges import (judge_follow_through, judge_signal_bar_closed, judge_signal_bar_direction, judge_signal_bar_length)`（字母序排在 `preflight` 之后、`trace_nodes` 之前，单一 import 块内，避免新增 I001 区块）。这 4 个名字在 `decision_nodes.py` 函数体内**确有引用**（`apply_stage2` 的 §9 填充链 `fill_91`/`fill_92`/`fill_93`/`fill_95`），属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import judge_signal_bar_*` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_decision_nodes_judges.py` 无需改动）。
- **`SIGNAL_BAR_LONG_ATR_RATIO` 转为纯重导出**：该常量原在 `judge_signal_bar_length` 体内引用，随函数迁出后在 `decision_nodes.py` 内已无其他引用点，但 `test_decision_nodes_judges.py` 仍从 `decision_nodes` 命名空间 import 它——故在 `decision_thresholds` 的 import 行上补 `# noqa: F401`（标注「re-exported for tests; used in signal_bar_judges」），保持既有测试站点逐字节兼容。4 个 bar-type 常量为私有实现细节、全仓库无 import 点，随簇迁入新模块、`decision_nodes` 不再暴露（无兼容风险）。文件进一步收缩约 250 行（80654→68220 字节）。

### 验证

- `py_compile` 通过（`signal_bar_judges.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python -c` 断言 `decision_nodes.judge_signal_bar_closed`/`judge_signal_bar_direction`/`judge_signal_bar_length`/`judge_follow_through` 均 `is` `signal_bar_judges` 下的**同一对象**，`decision_nodes.SIGNAL_BAR_LONG_ATR_RATIO is signal_bar_judges.SIGNAL_BAR_LONG_ATR_RATIO`、`decision_nodes.NodeFill is signal_bar_judges.NodeFill`，且 `hasattr(signal_bar_judges, "_LONG_BAR_TYPES") is True`、`hasattr(decision_nodes, "_LONG_BAR_TYPES") is False`（"IDENTITY_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`signal_bar_judges`/`data.base` 不经 PyQt6 链可直接跑）：经**重导出的 `decision_nodes.*` 路径**（即 `apply_stage2`/测试实际调用路径）逐例断言输出**逐字节一致**——§9.1→`(9.1,是,K{sig})`；§9.2 无方向→`不适用`、trend_bull 顺多→`是`、outside_bull 顺多→`否`且含「外包棒」、trend_bull 逆空→`否`、trend_bear 顺空→`是`；§9.3 ratio=None→`是`含「无法计算」、2.5→`是`含「过长」、1.0→`否`；§9.5 `yes/failed/no/pending/None`→`是/否/否/等待/等待`，且 `bar_range` 在 `sig>1` 为 `K{sig}-K1`、`sig==1` 为 `K1`（"RUNTIME_OK"/"ALL_GREEN"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **220** 条（200×RUF001、6×RUF003、5×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM108、1×SIM114）→ 拆分后 `decision_nodes.py`（180：161×RUF001、6×RUF003、5×RUF002、3×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM114）+ 新增 `signal_bar_judges.py`（40：39×RUF001、1×SIM108）合计 **220**，**逐类别完全一致、零净新增告警**（39×RUF001 随中文 reason 串、1×SIM108 随 `judge_signal_bar_length` 迁入新模块；`decision_nodes.py` 的 RUF100 仍为 3——新增的 `SIGNAL_BAR_LONG_ATR_RATIO` `# noqa: F401` 生效未被判为冗余）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第二十轮：继续拆分 decision_nodes，提取 trace_nodes 结果层模块 R-M3-4）

本轮为**大文件拆分 M3 的第四刀**（第十七轮 `decision_thresholds.py` 常量、第十八轮 `bar_geometry.py` 几何原语、第十九轮 `preflight.py` 数据闸门），继续把 `pa_agent/ai/decision_nodes.py`（AI 层最大单文件）中**所有 section-judge 共享的「结果层」**剥离。目标是这一簇彼此紧邻、逻辑内聚的辅助：`NodeFill`（frozen dataclass——每个 judge 的返回类型）+ `_coerce_dict`/`_coerce_trace_list`（把松散的 AI JSON 防御性归一为 dict/trace 列表）+ `_node_label`/`build_program_trace_node`（把 `NodeFill` 转成合法决策 trace dict，问题文本经 call-time import 从 `decision_tree` 惰性解析）。选它作为第四刀的关键动机：`NodeFill` 是**每个 section-judge 都会 return 的公共结果类型**——先把这层抽到无环叶子模块，后续把 `DirectionJudge`/`AlwaysInJudge`/`MomentumJudge`/`SignalBarJudge` 等各自拆成独立子模块时，才能各自 `from pa_agent.ai.trace_nodes import NodeFill` 而**不与 `decision_nodes` 形成 import 循环**。该模块仅依赖 stdlib（`logging`/`dataclasses`/`typing.Any`），对 `decision_tree` 的引用走 call-time import，**无 import 期项目依赖**（无环前提：`trace_nodes` 为叶子 ← `decision_nodes`）。

### 代码清理

- **新增 `pa_agent/ai/trace_nodes.py`（trace 结果层模块）**：把 `NodeFill`、`_coerce_dict`、`_coerce_trace_list`、`_node_label`、`build_program_trace_node` 五者**逐字节搬迁**至新模块（保留全部 docstring、trace dict 键序与惰性 `node_label` 回退逻辑）；import 仅 `logging`/`dataclass`/`Any`，`node_label` 查询走 call-time import。模块 docstring 说明其「结果层」定位与「先抽叶子以打破后续 judge 拆分的循环依赖」动机。
- **`decision_nodes.py` 改为从 `trace_nodes` 导入这四者**：删除原五个定义块，在文件顶部 import 组新增 `from pa_agent.ai.trace_nodes import (NodeFill, _coerce_dict, _coerce_trace_list, build_program_trace_node)`（字母序排在 `preflight` 之后、单一 import 块内，避免新增 I001 区块）。这四个名字在 `decision_nodes.py` 函数体内**确有引用**（`NodeFill` 遍布各 judge，`_coerce_*` 用于 `route_order_method`/`apply_stage2`，`build_program_trace_node` 用于 `apply_stage1`/`apply_stage2`），属**正常 import**（非纯重导出，无需 `# noqa: F401`）。因 `from pa_agent.ai.decision_nodes import NodeFill` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`tests/unit/test_decision_nodes_judges.py` 等无需改动）。
- **`_node_label` 随簇迁入、不再重导出**：该私有辅助全仓库**无任何 import/调用点**（仅曾与 `build_program_trace_node` 相邻定义），逻辑上属同一「trace 构建」簇，故整簇迁至 `trace_nodes.py` 并在那里保留 `logger`；`decision_nodes.py` 不再暴露 `_node_label`（无兼容风险）。同时删除 `decision_nodes.py` 中因 `NodeFill` 迁出而不再使用的 `from dataclasses import dataclass`。文件进一步收缩约 100 行。

### 验证

- `py_compile` 通过（`trace_nodes.py`、`decision_nodes.py`，EXIT=0）。
- **重导出/迁移等价性**：`python -c` 断言 `decision_nodes.NodeFill is trace_nodes.NodeFill`、`decision_nodes._coerce_dict is trace_nodes._coerce_dict`、`decision_nodes._coerce_trace_list is trace_nodes._coerce_trace_list`、`decision_nodes.build_program_trace_node is trace_nodes.build_program_trace_node` 均为**同一对象**；且 `hasattr(decision_nodes, "_node_label") is False`、`hasattr(trace_nodes, "_node_label") is True`（"IDENTITY_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`trace_nodes`/`data.base` 不经 PyQt6 链可直接跑）：`_coerce_dict`/`_coerce_trace_list` 对 dict/None/str/list/混入非 dict 元素的归一化逐例一致；`NodeFill` frozen 语义（改字段抛 `FrozenInstanceError`）与默认值 `branch=None`/`section=None` 一致；`build_program_trace_node` 输出 trace dict 键（`node_id`/`question`/`answer`/`reason`/`bar_range`/`skipped=False`）一致，`branch`/`section` 为 None 时省略、非 None 时写入；经 `decision_nodes` 命名空间调用 `judge_data_sufficiency`→`build_program_trace_node` 冒烟通过（"COERCE_OK"/"NODEFILL_OK"/"BUILD_OK"/"SMOKE_OK"/"ALL_GREEN"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **222** 条（200×RUF001、6×RUF003、5×RUF002、5×RUF100、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM108、1×SIM114）→ 拆分后 `decision_nodes.py`（220）+ 新增 `trace_nodes.py`（2×RUF100）合计 **222**，**逐类别完全一致、零净新增告警**（`decision_nodes.py` 的 RUF100 由 5 降至 3——迁走的 2 个 `# noqa: BLE001` 随 `_node_label`/`build_program_trace_node` 进入 `trace_nodes.py` 计为其 2×RUF100）。全仓库 `ruff check pa_agent` 总数 **3796** 保持不变。
- `git diff` 密钥扫描（`sk-...` / `api_key=` / `Bearer` / `secret=` / `token=`）无命中——纯结构搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第十九轮：继续拆分 decision_nodes，提取 preflight 数据闸门模块 R-M3-3）

本轮为**大文件拆分 M3 的第三刀**（第十七轮提取 `decision_thresholds.py` 常量、第十八轮提取 `bar_geometry.py` 几何原语），继续把 `pa_agent/ai/decision_nodes.py`（AI 层最大单文件）中**自足的前置数据质量闸门**剥离。目标是 `PreflightResult`（frozen dataclass 结果类型）+ `check_preflight_data`（对外入口，含异常保护）+ `_check_preflight_data_inner`（内部实现）这一组「Stage1 前数据校验」逻辑。它们：① 是**纯函数**（无 AI 调用、无副作用，仅在异常分支写一条 warning 日志），依次校验「frame/bars 非空且 OHLC 合法 → 已收盘 K 线数 ≥ 20 → EMA20/ATR14 非全 NaN」，任一不满足即保守返回 `ok=False`；② 仅依赖 stdlib（`logging`/`math`/`dataclass`/`typing.Any`）与同级纯数据模块 `decision_thresholds` 的 `BAR_COUNT_THRESHOLD`——无循环依赖前提（`decision_thresholds` 为叶子 ← `preflight` ← `decision_nodes`）；③ 在 `decision_nodes.py` 内部**不再被任何其他函数引用**，仅由 `orchestrator/two_stage.py`（`submit()` 的 Step 2.5 前置闸门）与 `tests/unit/test_decision_nodes_preflight.py` 从 `decision_nodes` 命名空间 import——故属**纯重导出**场景（与 M2 一致，需 `# noqa: F401`），而非第十七/十八轮的「函数体内确有引用的正常 import」。

### 代码清理

- **新增 `pa_agent/ai/preflight.py`（前置数据质量闸门模块）**：把 `PreflightResult` 与 `check_preflight_data`/`_check_preflight_data_inner` **逐字节搬迁**至新模块（保留全部 docstring、三类 `failed_check` 令牌与中文 reason 串），import 仅 `logging`/`math`/`dataclass`/`Any` 与 `from pa_agent.ai.decision_thresholds import BAR_COUNT_THRESHOLD`，无其他项目依赖、无副作用。模块 docstring 说明其来源、near-stdlib 定位与「行为须与原文一致（三类令牌与 reason 串被下游消费）」的约束。
- **`decision_nodes.py` 改为从 `preflight` 重导出**：删除原 `PreflightResult` 类定义块（保留同区的「Result types」header 与 `NodeFill`）与整个 `PreflightDataGate` 函数区，在文件顶部 import 组新增 `from pa_agent.ai.preflight import (PreflightResult, check_preflight_data)  # noqa: F401`（字母序排在 `decision_thresholds` 之后、单一 import 块内，避免新增 I001 区块）。因这两个名字在 `decision_nodes.py` 内已无其他引用点，属**故意的纯重导出**（`# noqa: F401`）；既有 `from pa_agent.ai.decision_nodes import check_preflight_data` 站点仍从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`two_stage.py`、`test_decision_nodes_preflight.py` 无需改动）。文件进一步收缩约 230 行。

### 验证

- `py_compile` 通过（`preflight.py`、`decision_nodes.py`，EXIT=0）。
- **重导出等价性**：`python -c` 断言 `decision_nodes.check_preflight_data is preflight.check_preflight_data`、`decision_nodes.PreflightResult is preflight.PreflightResult` 均为**同一对象**，且 `decision_nodes.BAR_COUNT_THRESHOLD is decision_thresholds.BAR_COUNT_THRESHOLD == 20`（"IDENTITY_OK"）。
- **运行时行为对比**（本机 `decision_nodes`/`preflight`/`data.base` 不经 PyQt6 链可直接跑）：经**重导出的 `decision_nodes.check_preflight_data` 路径**（即 `two_stage`/测试实际调用路径）构造真实 `KlineFrame` 断言输出**逐字节一致**——`None`→`bars_empty_or_bad_ohlc`、n=19→`bar_count_lt_20`、n=20→`ok=True`/`reason=""`/`failed_check=None`、全 NaN 指标→`indicators_all_nan`、首棒 high<low→`bars_empty_or_bad_ohlc`、字符串/整数入参不崩溃、仅 EMA 或仅 ATR 为 NaN→通过（"RUNTIME_OK"/"SMOKE_OK"）。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件 **232** 条（209×RUF001、6×RUF003、6×RUF100、5×RUF002、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM108、1×SIM114）→ 拆分后 `decision_nodes.py`（222）+ 新增 `preflight.py`（10：9×RUF001、1×RUF100）合计 **232**，**逐类别完全一致、零净新增告警**（其中 9×RUF001 随中文 reason 串迁入新模块；`decision_nodes.py` 的 RUF100 由 6 降至 5——迁走的 `# noqa: BLE001` 随函数进入 `preflight.py` 计为其 1×RUF100）。
- `git diff` 密钥扫描（`sk-...` / `api_key` / `Bearer` / `secret=` / `token=`）无命中——纯函数搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第十八轮：继续拆分 decision_nodes，提取 bar_geometry 几何原语模块 R-M3-2）

本轮为**大文件拆分 M3 的第二刀**（第十七轮已提取 `decision_thresholds.py` 常量模块），继续把 `pa_agent/ai/decision_nodes.py`（AI 层最大单文件）中**与决策语义无关的纯 K 线几何原语**剥离。目标是 3 个 stdlib-only、无项目依赖的底层计算函数：`_count_trend_bars`（趋势棒计数：body/close-position 阈值分类）、`_mean_overlap_ratio`（相邻棒重叠比均值）、`_find_swings`（左右各 2 根枢轴的波段高低点检测）。这些函数：① **纯几何计算**（仅依赖 builtins 与 `typing.Any`，无 `math`/`logging`/无任何模块级常量）；② 同时被 `decision_nodes.py`（`judge_market_chaos`/`judge_direction`/`_eval_always_in_gates`/`judge_momentum_strength` 等）与 `trend_context.py` 引用；③ 与常量一样，是后续把各 section-judge 拆成独立子模块的**共享底层依赖**——先抽到无环依赖的独立模块，section-judge 才能各自 import 而不循环。

### 代码清理

- **新增 `pa_agent/ai/bar_geometry.py`（纯 K 线几何原语模块）**：把上述 3 个函数**逐字节搬迁**至新模块（保留全部 docstring 与分类阈值），仅 `from __future__ import annotations` 与 `from typing import Any`，无项目 import、无副作用。模块 docstring 说明其来源、stdlib-only 定位与「行为须与原文一致」的约束。
- **`decision_nodes.py` 改为从 `bar_geometry` 导入这 3 个原语**：删除原函数定义块，在文件顶部 import 组新增 `from pa_agent.ai.bar_geometry import (...)`（字母序排在 `decision_thresholds` 之前）。这 3 个函数在 `decision_nodes.py` 函数体内**确有引用**（正常 import，非需 `# noqa: F401` 的纯重导出）；因既有 `from pa_agent.ai.decision_nodes import <原语>` 站点仍能从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**。文件进一步收缩约 110 行。
- **`trend_context.py` 改为直接从源模块导入**：把原先 `from pa_agent.ai.decision_nodes import (..., _count_trend_bars, _find_swings, _mean_overlap_ratio)` 拆为两条——常量仍从 `decision_thresholds` 取（第十七轮已迁移），3 个几何原语改从 `bar_geometry` 取。直连源模块，减少对 `decision_nodes` 命名空间的重导出耦合，取到的仍是同一对象。

### 验证

- `py_compile` 通过（`bar_geometry.py`、`decision_nodes.py`、`trend_context.py`，EXIT=0）。
- **重导出等价性**：`python -c` 断言 `decision_nodes`、`bar_geometry`、`trend_context` 三个命名空间下的 `_count_trend_bars`/`_find_swings`/`_mean_overlap_ratio` 均 `is` **同一对象**（"re-export OK, 3 geom names identical"、"tc uses bg objects: True"）。
- **运行时行为对比**（本机不经 PyQt6 链可直接跑）：搬迁前后用同一组构造 K 线断言三函数输出**逐字节一致**——`_count_trend_bars` 窗口 8/10 → `(5,3)`/`(6,4)`、`_mean_overlap_ratio` 窗口 8 → `0.440693`、`_find_swings` 窗口 10 → `([113.0],[97.0])`、窗口 4（<5 根）→ `([],[])`。
- `ruff check` 对比基线：基线 `decision_nodes.py`+`trend_context.py` 两文件合计 **254** 条（231×RUF001、6×RUF003、6×RUF100、5×RUF002、1×I001、1×RUF005、1×SIM103、1×SIM105、1×SIM108、1×SIM114）→ 拆分后三文件（含新增 `bar_geometry.py`）合计**逐类别完全一致**，**零净新增告警**；`bar_geometry.py` 单独 `ruff check` **All checks passed**。（既存 1×I001 系 `decision_nodes.py` 头部双空行 import 间距的历史告警，非本轮引入。）
- `git diff` 密钥扫描（`sk-...` / `"api_key":` / `Bearer` / `secret=` / `token=`）无命中——纯函数搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第十七轮：拆分 decision_nodes，提取 decision_thresholds 常量模块 R-M3）

本轮继续**大文件拆分**，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M3**（拆分 `decision_nodes.py`——按 §1/§2/§9/§11/preflight/risk 拆分子模块），是 M1-M4 拆分组的第二刀，紧接第十六轮的 M2。`pa_agent/ai/decision_nodes.py` 是 AI 层**最大的单文件（3073 行）**：文件头部集中了 **28 个模块级调参常量与节点权限集合**（§1.1 数据充分性阈值、§2.3 方向投票窗口/阈值、§2.4 Always-In 窗口/占比、§2.5 动量强度阈值、§1.3 极端混沌阈值、`LOCKED_NODES`/`OVERRIDABLE_NODES`/`AI_PRIMARY_NODES`/`SAFETY_GATE_NODES` 等 override 权限集）。这些常量：① 是**纯数据**（无 import、无副作用），编码了经过调优的 Brooks 价格行为阈值与闸门/override 策略；② 同时被 `decision_nodes.py` 自身与 `trend_context.py` 引用；③ 是后续把各 section-judge（DirectionJudge/AlwaysInJudge/MomentumJudge 等）拆成独立子模块的**共享依赖前提**——必须先把它们抽到一个无环依赖的独立模块，section-judge 才能各自 import 而不产生循环依赖。

### 代码清理

- **新增 `pa_agent/ai/decision_thresholds.py`（调参常量/权限集纯数据模块）**：把 `decision_nodes.py` 头部（原 47-119 行）的 28 个常量**逐字节搬迁**至新模块（含全部中文调参注释与 §编号），仅 `from __future__ import annotations`，无任何 import 与副作用。模块 docstring 说明其来源、纯数据定位与「取值须与原文逐字节一致」的约束。
- **`decision_nodes.py` 改为从 `decision_thresholds` 导入这 28 个常量**：删除原常量定义块，在文件顶部 import 组新增 `from pa_agent.ai.decision_thresholds import (...)`。这 28 个常量在 `decision_nodes.py` 函数体内**确有引用**（故是正常 import 而非需 `# noqa: F401` 的纯重导出）；因所有既有 `from pa_agent.ai.decision_nodes import <常量>` 站点仍能从 `decision_nodes` 命名空间取到同一对象，**跨模块 import 逐字节兼容**（`trend_context.py` 及 `test_decision_nodes_*` 等无需改动）。文件从 3073 行降至约 3001 行。

### 验证

- `py_compile` 通过（`decision_thresholds.py`、`decision_nodes.py`，EXIT=0）。
- **重导出等价性**：`python -c` 逐一断言 `decision_nodes` 与 `decision_thresholds` 的 **28 个常量 `is` 同一对象**（"re-export OK, all 28 names identical"），并确认 `trend_context` 仍可正常 import。
- **运行时冒烟**（本机 `decision_nodes`/`data.base` 不经 PyQt6 链，可直接跑；`hypothesis` 未装故既有 `test_decision_nodes_*` 无法 collect，另写自足冒烟脚本）：断言 28 个常量取值与原文一致（`BAR_COUNT_THRESHOLD==20`、`LOCKED_NODES`/`OVERRIDABLE_NODES`/`SAFETY_GATE_NODES` 集合逐字相等等），且 `check_preflight_data` 行为不变（n=19→`bar_count_lt_20` 失败、n=20→通过、`None`→保守失败）——"SMOKE_OK"。
- `ruff check` 对比基线：基线 `decision_nodes.py` 单文件的错误码分布（1×I001、209×RUF001、5×RUF002、20×RUF003、1×RUF005、6×RUF100、1×SIM103、1×SIM105、1×SIM108、1×SIM114）→ 拆分后两文件合计**逐类别完全一致**（其中 14×RUF003 随中文注释迁入新模块），**零净新增告警**（新模块自身仅继承 14×RUF003 既有 Chinese-comment 告警）。
- `git diff` 密钥扫描（`sk-...` / `"api_key":` / `Bearer` / `secret=` / `token=`）无命中——纯常量搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第十六轮：拆分 JsonValidator，提取 json_repair 模块 R-M2）

本轮为一次**大文件拆分**，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M2**（拆分 `json_validator.py`）范畴——报告 §7 建议的迭代顺序为「R1-R8 → M1-M4 大文件拆分 → 安全 M8-M10 → 性能 L1-L7」，本项是 M1-M4 拆分组的第一刀。`pa_agent/ai/json_validator.py` 原为 **1023 行**的单一大文件，其中**前半段（原 65-427 行，约 360 行）是一组自足的纯 JSON 文本提取/修复函数**（去 markdown fence、修不转义引号、补截断括号、闭合未完结字符串等），**与后半段的 `JsonValidator` 校验器类混杂在同一文件**。这组修复函数：① 仅依赖 stdlib（`json`/`logging`/`re`），零依赖 `JsonValidator` 类及任何项目模块；② 被 `validation_retry.py`、`prompt_assembler.py`、`tools/debug_stage2_json.py`、多个测试等**跨模块直接 import**（关注点独立）。两者混居导致文件臃肿、职责不清、修改修复逻辑时需在千行文件中定位。

### 代码清理

- **新增 `pa_agent/ai/json_repair.py`（JSON 提取与修复模块）**：把上述纯函数块**逐字节搬迁**至新模块——含 4 个模块级常量（`_FENCE_RE` / `_TRAILING_FENCE_RE` / `_LEADING_FENCE_RE` / `_STRING_END_CHARS`）与 11 个函数（`_extract_outer_json_object` / `_strip_fences` / `_escape_control_chars_in_json_strings` / `coalesce_model_json_text` / `format_model_json_for_context` / `_repair_unescaped_quotes` / `_repair_semicolon_separator` / `_balance_json_brackets` / `_inject_stage1_missing_tail` / `_repair_unclosed_string_before_brace` / `_try_repair_json_syntax`）。模块 docstring 说明其来源与 stdlib-only 定位。
- **`json_validator.py` 改为从 `json_repair` 重导出**：删除原 65-427 行的函数实现，替换为单个 `from pa_agent.ai.json_repair import (...)` 平铺分组 import（15 个名），并以 `# noqa: E402, F401` 声明「这是**故意的重导出**」。**29 处既有 import 站点全部逐字节兼容**（外部只 import `JsonValidator`/`Ok`/`ValidationError`/`coalesce_model_json_text`/`format_model_json_for_context`/`_strip_fences`/`_repair_unclosed_string_before_brace`/`_repair_unescaped_quotes` 等，均从 `json_validator` 原路径仍可取到同一对象）。
- **保留在 `json_validator.py`**：`Ok`/`ValidationError`/`Result` 结果类型、`_EXPLICIT_S9_TRADABLE_TOKENS` 常量、`JsonValidator` 校验器类（含全部 `_check_*` 方法）及其辅助 `_parse_k_seq`/`_bar_by_seq`/`_all_stage2_reasons`；文件从 1023 行降至约 660 行。（**第二十八轮补充**：`_EXPLICIT_S9_TRADABLE_TOKENS`、7 个业务规则 `_check_*` 与 3 个辅助已进一步拆出至 `business_rules.py`，`json_validator.py` 再降至 415 行——见文件顶部第二十八轮条目。）

### 验证

- `py_compile` 通过（`json_repair.py`、`json_validator.py`，EXIT=0）。
- **重导出等价性**：`python -c` 逐一断言 `json_validator` 与 `json_repair` 的 **15 个重导出名 `is` 同一对象**（"re-export OK, all 15 names identical"）——保证跨模块调用行为逐字节不变。
- **真实 pytest 回归**（本机 `json_validator`/`json_repair` 不经 PyQt6 链，可直接跑）：`tests/unit/test_json_validator.py` + `tests/property/test_json_validator_categories.py` 合计 26 项 → **16 passed / 10 failed**；逐一比对 `git stash` 后的**基线**，确认这 **10 项失败在基线上以完全相同的原因失败**（5 项 `ModuleNotFoundError: PyQt6`、2 项 `tools/stage2_raw_sample.txt` 缺文件、2 项既有 `test_truncated_stage1_*` 断言、1 项 fence 相关），均属**本机环境缺失/既有失败，非本轮回归——拆分引入零新增失败**。
- `ruff check` 对比基线：基线 `json_validator.py` 单文件 **9** 条（2×RUF003、2×RUF001、2×I001、1×SIM108、1×SIM114、1×RUF005）→ 拆分后两文件合计 **9** 条（错误码逐类别一致，仅在两文件间重新分布），**零净新增告警**。
- `git diff` 密钥扫描（`sk-...` / `"api_key":` / `Bearer` / `secret=` / `token=`）无命中——纯代码搬迁，无密钥。

---

## [Unreleased] — 2026-07-14（第十五轮：实现 API Key 本地至静态加密 Windows DPAPI R-M8）

本轮补齐一处**真实的安全短板**，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M8**（实现真正的本地 API Key 加密）范畴——报告 §7 建议的「补齐安全短板（M8-M10）」组中，M9/M10 已在前两轮完成，M8 为最后一项。此前 `provider.api_key` **以明文写入** `config/settings.json`：模型中虽保留 `api_key_encrypted` 字段，但**从无任何加解密逻辑**，`pa_agent/security/` 包仅是空占位。后果：`settings.json` 一旦泄漏即等于密钥泄漏（此前仅靠 `.gitignore` + pre-commit + 运行时脱敏三层防护，均属"防止外泄"而非"至静态加密"）。

### 安全加固

- **新增 `pa_agent/security/secret_store.py`（本地密钥加密模块）**：提供 `encrypt_secret` / `decrypt_secret` / `is_encryption_available` / `looks_encrypted`。Windows 下经 **DPAPI**（`CryptProtectData` / `CryptUnprotectData`，`ctypes` 直调 `crypt32`，与 `workbuddy_connector.py` 既有 DPAPI 用法同源）把明文加密为**自描述令牌** `dpapi:v1:<base64(blob)>`。DPAPI 将密文绑定到**当前 Windows 用户账户**，密文在他机/他账户下无法解密。`CRYPTPROTECT_UI_FORBIDDEN` 确保 headless 环境不弹窗。
- **`config/settings.py` 接入至静态加密**：
  - `save_settings` 落盘前调 `_encrypt_provider_key_for_disk(data)`——**仅改写 `model_dump()` 产生的 dict**（绝不触碰内存态 `Settings`）：把明文 `api_key` 加密进 `api_key_encrypted`、并将磁盘上的 `api_key` 置空。
  - `load_settings` 校验后调 `_decrypt_provider_key_in_place(settings)`——把 `api_key_encrypted` 令牌解密回内存态 `provider.api_key`，并清空内存中的 `api_key_encrypted`（密文不驻留内存；所有调用方仍统一读明文 `provider.api_key`，零改动）。
  - **向后兼容**：磁盘上的**旧明文 key**（`api_key` 有值、无令牌）照常加载使用，并在**下次保存时自动加密**（无缝迁移，无需手动干预）。
- **优雅降级**：非 Windows 平台或 DPAPI 不可用时，`encrypt_secret` 返回 `None`，`save_settings` 回退为**明文至静态**（与改动前行为完全一致，仍受 `.gitignore` + pre-commit + 运行时脱敏保护）——不因缺少加密能力而丢失或损坏 key。

### 明确不改（保持原样）

- **运行时脱敏三层（`mask_secret` / `MaskingFormatter` / `PendingWriter._sanitize`）**：本轮只加"至静态加密"，不改"运行时脱敏"；内存态 `api_key` 仍是明文，脱敏读取路径与 provider 降级 key 同步（M9）逻辑均零改动。
- **所有 `save_settings` 调用点**（GUI 各设置对话框、`main_window`、`two_stage` provider 降级、qclaw/workbuddy `sync_*_on_load`）：全部经由统一的 `save_settings`，加密在函数内部生效，调用点无需感知，逐一核实无绕过直接写盘的路径。
- **`.githooks/pre-commit`**：已扫描 `api_key_encrypted` 大 base64 令牌与 `sk-...` 模式，DPAPI 令牌命中既有规则，无需新增。

### 验证

- `py_compile` 通过（`security/secret_store.py`、`config/settings.py`）。
- **真实 pytest 通过**（本机 `config.settings` 不经 PyQt6 链，可直接跑）：`tests/unit/test_settings_round_trip.py`、新增 `tests/unit/test_secret_store.py`、`tests/unit/test_data_source_factory.py` 合计 **28 passed**。
  - 新增 `test_secret_store.py`：DPAPI 往返还原、中文/emoji unicode 往返、**密文不含明文**、空串→`None`、未知 scheme→`None`、损坏 base64→`None`、**篡改密文→`None`**、`looks_encrypted` 判定。
  - 改写 `test_api_key_present_on_disk`→`test_api_key_encrypted_at_rest`（平台感知：Windows 断言磁盘 `api_key` 为空、`api_key_encrypted` 为 `dpapi:` 令牌、**全文不含明文**、且 load 能解密还原；非 Windows 走明文回退分支）。
  - 新增 `test_legacy_plaintext_key_reencrypted_on_next_save`（旧明文 key 加载可用、再保存后被加密）。
  - **DPAPI 实机验证**：`CryptProtectData`/`CryptUnprotectData` 往返还原成功、密文 246B 且不含明文（win32 实测）。
- `ruff check` 对比基线：`config/settings.py` 改动前 **37** 条 → 改动后 **37** 条（既有 RUF003/E402/UP037/I001/SIM102，逐类别一致，无新增）；新增 `secret_store.py` / `test_secret_store.py` **All checks passed**；`test_settings_round_trip.py` **3→3**（既有 F401/I001）。四文件合计 **40→40**，零新增告警。
- `git diff` 密钥扫描（`sk-...` / `"api_key":` / `Bearer` / `secret=` / `token=`）无命中明文密钥（测试固定串如 `sk-super-secret-key` 用连字符分段，不匹配 12+ 连续字母数字的 pre-commit 规则）。
- 建议在项目 venv 运行 `pytest tests/unit/test_secret_store.py tests/unit/test_settings_round_trip.py -q` 回归。

---

## [Unreleased] — 2026-07-14（第十四轮：数据源工厂配置注入，移除工厂对 settings.json 的直接读取 R-M6）

本轮为一处**分层依赖倒置**清理，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M6**（统一数据源配置注入——「移除工厂对 `settings.json` 的直接读取」）范畴。`data/factory.py` 的 `create_data_source(kind)` 在构造 Tushare 源时，会在函数体内 `from pa_agent.config.settings import load_settings` 并直接 `load_settings(SETTINGS_JSON_PATH)` 读盘取配置。问题有二：① **数据层反向依赖配置层并触发磁盘 IO**——工厂本应是纯构造器，却隐藏了一次读盘副作用（数据源切换属 GUI 交互热路径，`main_window._switch_data_source` 每次切到 Tushare 都会多一次 `settings.json` 读盘）；② **配置来源不一致**——`app_context.bootstrap` 与 `main_window._switch_data_source` 两个调用点**手上已持有** `Settings` 实例（前者局部 `settings`、后者 `self._ctx.settings`），工厂却无视调用方的内存态、另起一次读盘，理论上可能拿到与调用方不同步的磁盘内容。

### 代码清理

- **`create_data_source(kind, settings=None)` 增加注入形参**：调用方可把已加载的 `Settings` 注入工厂；仅 Tushare 分支需要它（取 API token）。签名向后兼容（`settings` 默认 `None`）。
- **保留惰性回退**：当调用方省略 `settings` 时（如现有单测 `test_create_data_source_returns_expected_types` 直接 `create_data_source("tushare")`、或未来独立/脚本化构造），Tushare 分支仍惰性 `load_settings(SETTINGS_JSON_PATH)` 兜底，行为与改动前完全一致。
- **两个调用点改为注入**：`app_context.bootstrap` 传入局部 `settings`（`create_data_source(ds_kind, settings)`）；`main_window._switch_data_source` 传入 `getattr(self._ctx, "settings", None)`。注入路径下工厂**不再读盘**，直接复用调用方的内存态配置，消除热路径中的冗余 IO 与潜在配置不一致。
- **类型注解**：`Settings` 仅用于注解，置于 `TYPE_CHECKING` 块导入（`data/factory.py` 无第三方依赖、导入开销为零），符合项目 3.11+ typing 约定。

### 明确不改（保持原样）

- **`TushareSource.__init__(settings=None)` 与 `_configured_token()`**：仍支持「注入 settings → 读 `tushare.token`；否则回退环境变量 `TUSHARE_TOKEN`」的既有取值优先级，零改动。
- **非 Tushare 分支**（mt5 / tradingview / eastmoney / akshare / yfinance）：从不接触 `settings`，注入形参对其无副作用，构造逻辑逐字节不变。
- **`normalize_data_source_kind` / `default_symbol_for_kind` / `data_source_label`** 等工厂内其余函数：不涉及 settings 读取，未改动。

### 验证

- `py_compile` 通过（`data/factory.py`、`app_context.py`、`gui/main_window.py`）。
- **行为验证**：用 `unittest.mock.patch` 断言 `create_data_source`：① 注入 `settings` 时**不调用** `load_settings`（零读盘）且注入实例被原样转发给 `TushareSource._settings`；② 省略 `settings` 时惰性调用 `load_settings` 恰一次（回退兜底）且回退实例被转发；③ 非 Tushare 分支（含注入/不注入）**从不调用** `load_settings`——全部 PASS。另复刻现有单测逻辑（`create_data_source` 对 mt5/tradingview/eastmoney/tushare 返回预期类型）通过，向后兼容无破坏。
- `ruff check` 对比基线：`data/factory.py` 改动前 **2** 条 → 改动后 **2** 条（均为既有 RUF002 中文标点，位于新增/原有 docstring）；三文件合计 **325** 条 → **325** 条，逐类别一致，无新增告警。
- `git diff` 密钥扫描（`sk-...` / `api_key=...` / `Bearer` / `secret` / `token=`）无命中明文密钥。
- 建议在项目 venv 运行 `pytest tests/unit/test_data_source_factory.py -q` 回归工厂路径。

---

## [Unreleased] — 2026-07-14（第十三轮：provider 自动降级后同步刷新记录写入器脱敏 key R-M9）

本轮为一处**真实的密钥脱敏失效**修复，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M9**（`PendingWriter` 动态 key 脱敏失效——「key 修改后同步更新 writer」）范畴。`PendingWriter` 在序列化每条 `AnalysisRecord` 前，会用**构造时传入的 `api_key`** 递归扫描并把明文 key 替换为掩码（`_sanitize`）。运行时若用户在 GUI「AI 模型」对话框改 key，`main_window._open_ai_model_settings_dialog` 已配套调用 `pending_writer.set_api_key(new_key)`（M9 命名的 `gui/settings_dialog.py` 实为**未被实例化的死代码**，真正生效的是 `AIModelSettingsDialog` 分支），脱敏能跟上。**但另一条运行时改 key 的路径——`orchestrator/two_stage.py` 的 provider 自动降级（`_finish_provider_fallback`，WorkBuddy→Cursor→QClaw）——在切换 provider 时会 `update_api_key(...)` 刷新日志脱敏 formatter，却从未刷新 `PendingWriter` 的脱敏 key**。后果：同一次 `submit()` 内发生网络降级并切换到新 provider（新 key）后，后续 `save_full`/`save_partial` 落盘的记录仍用**旧 key** 做脱敏——**新 provider 的明文 API key 会原样写进记录 JSON 未被掩码**（记录目录虽被 gitignore，但明文密钥落盘仍是安全隐患，且违反项目「持久化记录中不出现明文 key」的安全边界）。

### 安全加固

- **`_finish_provider_fallback` 补齐记录写入器 key 同步**：在既有「`update_provider` → best-effort `save_settings` + `update_api_key`（刷新日志脱敏）」之后，新增 `if hasattr(self._pending_writer, "set_api_key"): self._pending_writer.set_api_key(new_key)`，使记录写入器的脱敏 key 与降级后的 provider key 对齐。**与 GUI 设置保存路径（`main_window._open_ai_model_settings_dialog` 中 `update_api_key(key)` 后紧跟 `pending_writer.set_api_key(key)`）行为一致**，两条运行时改 key 路径的脱敏语义从此统一。
- **`hasattr` 守卫**：兼容注入了不带 `set_api_key` 的 writer（如测试 double/旧实现），缺失时静默跳过、不影响降级主流程。
- 把 `self._settings.provider.api_key` 提取为局部 `new_key` 复用于 `update_api_key` 与 `set_api_key`，避免二次属性读取、语义不变。

### 明确不改（保持原样）

- **降级链调用点 `_stream_chat_resilient` 与三个 `_try_*_fallback` 包装器**：尝试顺序、`tried_*` 标志、连接器 call-time 导入与 patch 点、返回语义全部零改动；本轮只在共享尾部 `_finish_provider_fallback` 追加一行同步。
- **`err` 非空（降级不可用）路径**：仍在 `update_provider` 之前提前 `return False`，**不触碰** writer/formatter，与原逻辑一致。
- **`gui/settings_dialog.py`（死代码）**：既未被任何处实例化（仅 `AIModelSettingsDialog`/`FeishuSettingsDialog`/`GeneralSettingsDialog` 被 `main_window` 使用），本轮不改动亦不删除（清理死代码另属独立范畴，避免扩大本轮 diff）。
- **`app_context.bootstrap()`**：构造 `PendingWriter` 时传入的初始 `api_key` 逻辑正确（启动期 key 即当时的 provider key），无需改动。
- **既有告警**（RUF001 中文标点、E402 等）：不在本轮范围内，未改动。

### 验证

- `py_compile` 通过（`two_stage.py`）。
- **行为验证**：因本机缺 `PyQt6`（经 `util/__init__`→`event_bus` 链，与既往各轮一致），用等价脚本 stub `PyQt6.QtCore` 后断言 `_finish_provider_fallback`：① 成功降级时以**新 key** 调用 `pending_writer.set_api_key` 恰一次；② 同时仍以新 key 调用 `update_api_key`（日志脱敏不回退）；③ writer 缺 `set_api_key` 时（`hasattr` 守卫）不崩溃、仍返回 `True`；④ `err` 非空时提前返回 `False` 且**不触碰** writer 与 formatter——全部 PASS。
- `ruff check` 对比基线（`two_stage.py`）：改动前 **40** 条 → 改动后 **40** 条，逐类别一致（RUF001 22 / E402 11 / UP037 5 / I001 1 / RUF100 1），无新增告警。
- `git diff` 密钥扫描（`sk-...` / `api_key=...` / `Bearer` / `secret` / `token=`）仅命中 `self._settings.provider.api_key` 与 `set_api_key`/`update_api_key` 标识符引用，无明文密钥。
- 建议在项目 venv 运行 `pytest tests/unit/test_qclaw_auto_fallback.py tests/unit/test_pending_writer_no_plaintext_key.py -q` 回归降级与脱敏路径。

---

## [Unreleased] — 2026-07-14（第十二轮：修正分析记录文件名分钟字段 + 统一 basename R-M10）

本轮为一处**真实的记录文件名缺陷**修复，属后端审查报告（`docs/backend_review_report.md`）路线图 §5.2 的 **M10**（记录/日志文件名安全与正确性）范畴——§5.1（R1–R8）近期低风险项已全部完成。`records/pending_writer.py` 头部注释声明的记录文件命名约定是 `{YYYY-MM-DD_HH-mm-ss}_{symbol}_{timeframe}.json`，但实现用 `strftime("%Y-%m-%d_%H-%m-%S")`——**中间的 `%m` 是「月」而非「分钟」（应为 `%M`）**。后果：每个记录文件名的「分钟」位实际写成了月份，**同一天同一小时同一秒生成的两次分析会得到相同文件名并静默互相覆盖**（增量/持续跟踪同一分钟内多次触发时尤甚）。此外 `orchestrator/free_chat.py` 的 `_derive_record_id` **复制了同一段逻辑并带同样的 `%m` 错误**，还**跳过了 `sanitize_filename_component`**——导致 followup 侧车文件（`.followups.jsonl`）的 basename 既可能与记录文件不一致（分钟位错），又缺少路径安全过滤（symbol 含 `/` 时）。

### 崩溃修复 / 安全加固

- **修正分钟字段 `%m`→`%M`**：记录 basename 现正确输出分钟（如 `2026-07-14_09-38-05`，中间 `38` 为分钟而非月份 `07`），消除同小时同秒不同分钟的文件名碰撞与静默覆盖风险。
- **提升为单一事实来源 `build_record_basename(record)`**：把原私有 `_build_basename` 改名为公开函数（补全 docstring 说明命名约定与「PendingWriter 与 FreeChatSession 必须派生同一 stem」的约束），`save_full`/`save_partial` 两处调用同步更新。
- **`free_chat._derive_record_id` 改为委托**：删除其重复且有缺陷（`%m` 错误 + 未 sanitize）的内联实现，改为 `from pa_agent.records.pending_writer import build_record_basename` 后直接调用（call-time 导入避免 orchestrator↔records 顶层循环导入）。这样 followup 侧车 basename **必然**与记录文件一致，且复用同一套 symbol/timeframe 文件名过滤。
- 同步更新 `analysis_history.py` 中引用旧私有名 `_build_basename` 的注释为 `build_record_basename`。

### 明确不改（保持原样）

- **`trade_logger.py` 的时间戳格式**：其用 `strftime("%Y%m%d_%H%M%S")`（`%M` 正确），无此缺陷，本轮不动。
- **历史已落盘的旧文件名**：不做迁移/重命名（记录目录被 gitignore 忽略、且旧文件的 `meta` 内含真实时间戳，`analysis_history` 以 `meta.symbol/meta.timeframe` 与内容为权威匹配，不依赖文件名分钟位）；本轮只修正**新写入**文件名的正确性。
- **既有告警**（RUF001/RUF100 等）：不在本轮范围内，未改动。

### 验证

- `py_compile` 通过（`pending_writer.py`、`free_chat.py`、`analysis_history.py`）。
- **行为验证**：因本机缺 `PyQt6`（经 `util/__init__`→`event_bus` 链，与既往各轮一致），用等价脚本 stub `PyQt6.QtCore` 后断言：① 分钟位输出为「分钟」而非「月」（`09-38-05` 中 `38`）；② 同小时同秒但分钟不同（00 vs 45）的两条记录 basename 不再相同（碰撞消除）；③ `BTC/USD` 被 sanitize 为 `BTC-USD`（stem 中无路径分隔符）；④ `free_chat._derive_record_id(rec) == build_record_basename(rec)`——全部 PASS。
- `ruff check` 对比基线（三文件）：改动前 **67** 条 → 改动后 **66** 条，减少的 1 条源于删除 `free_chat` 重复实现；无新增告警。
- `git diff` 密钥扫描（`sk-...` / `api_key=...` / `Bearer` / `secret`）仅命中 `self._api_key` 标识符引用，无明文密钥。
- 建议在项目 venv 运行 `pytest tests/unit/test_pending_writer_sanitize.py tests/unit/test_pending_writer_no_plaintext_key.py -q` 回归记录写入路径。

---

## [Unreleased] — 2026-07-14（第十一轮：统一 provider fallback R3）

本轮落实后端审查报告（`docs/backend_review_report.md`）路线图 §5.1 的 **R3**：统一 provider 自动降级逻辑。`orchestrator/two_stage.py` 中的三个网络降级方法 `_try_qclaw_fallback` / `_try_cursor_fallback` / `_try_workbuddy_fallback` 各约 33 行、结构近乎完全相同，仅在「连接器 `apply_*` 函数、`is_openclaw_*_model` 守卫、provider 名称字符串、Cursor 多一个 `preferred_model` 入参」四点上不同；三者尾部（`err` 判空 → `update_provider` → best-effort `save_settings` + `update_api_key` → 记录切换日志）逐行重复，任一处改动都要同步改三遍、极易偏移。**原则：抽出单一共享尾部方法，消除重复；外部行为、返回值、日志输出文本、连接器 patch 点与改动前逐字节一致**——降级链的调用点 `_stream_chat_resilient` 依赖三方法的返回语义（`True` 表示已切换可重试、`False` 表示不适用/失败），且 `tests/unit/test_qclaw_auto_fallback.py` 依赖连接器函数为 call-time 导入方可 patch。

### 代码清理

- **新增共享尾部 `_finish_provider_fallback(provider_name, err) -> bool`**：把三方法完全相同的尾部（`err` 判空告警 → `self._client.update_provider(...)` → `try: save_settings + update_api_key except: 告警` → `logger.info` 记录切换 → `return True`）合并为一处；`provider_name` 参数注入 provider 名，日志文案由字面量（如 `"QClaw auto-fallback unavailable: %s"`）改为 `"%s auto-fallback unavailable: %s"` + 参数，**输出文本与原字面量逐字节等价**。
- **三个 `_try_*_fallback` 瘦身为薄包装器**：各自保留 **call-time 连接器导入**（`apply_*` / `is_openclaw_*_model`，确保测试可 `patch("pa_agent.ai.qclaw_connector.apply_qclaw_provider_to_settings")`）、守卫、`apply_*` 调用，尾部改为 `return self._finish_provider_fallback(<name>, err)`。守卫从两个 `if`（`if not is_openclaw_*: return False` / `if self._settings is None: return False`）合并为 `if not is_openclaw_*(original_model) or self._settings is None: return False`（短路语义等价）。Cursor 的 `preferred_model=original_model` 入参保留在其包装器中。
- 净减少约 37 行重复代码（`git diff --stat`：25 insertions / 62 deletions）；顺带移除 2 条因合并而多余的 `# noqa`（RUF100 3→1）。

### 明确不改（保持原样）

- **调用点 `_stream_chat_resilient` 零改动**：WorkBuddy → Cursor → QClaw 的尝试顺序、`tried_*` 标志、network-error 判定、重试循环全部不变。
- **连接器导入位置**：三个 `apply_*` / `is_openclaw_*_model` 仍在各包装器方法体内 call-time 导入，不上提到模块顶层——否则 `test_qclaw_fallback_skipped_for_non_openclaw_model` 的 `patch("pa_agent.ai.qclaw_connector.apply_...")` 会失效。
- **既有告警**（RUF001 中文标点等）：不在 R3 范围内，未改动。

### 验证

- `py_compile` 通过（`orchestrator/two_stage.py`）。
- **等价性验证**：从 git `HEAD` 提取旧三方法，逐行确认新「薄包装器 + `_finish_provider_fallback`」与原实现在守卫、`apply_*` 调用、`err` 分支、`update_provider`、`save_settings`/`update_api_key`、日志文案上语义一致。
- **行为验证**：因本机缺 `PyQt6`（经 `util/__init__`→`event_bus` 链，与既往各轮一致），用等价脚本 stub `PyQt6.QtCore` 后复刻 `test_qclaw_auto_fallback.py` 三个用例（fallback 成功→ `stream_chat` 调 2 次、不可用→调 1 次、非 openclaw 模型→ `_try_qclaw_fallback` 返回 False 且 `apply_*` 未被调用且可 patch），并补充 Cursor/WorkBuddy 守卫可 patch、`_finish_provider_fallback` 的 err 分支（不触碰 client）与成功分支（`update_provider` 被调）——全部 PASS。
- `ruff check` 对比基线：改动前 **42** 条 → 改动后 **40** 条，减少的 2 条为 RUF100（3→1，合并去重后多余的 `# noqa`）；其余类别（RUF001:22、E402:11、UP037:5、I001:1）与改动前**逐项一致、零新增**。
- `git diff` 密钥扫描（`sk-...` / `api_key=...` / `Bearer` / `secret`）仅命中 `update_api_key(...)` 标识符引用，无明文密钥。
- 建议在项目 venv 运行 `pytest tests/unit/test_qclaw_auto_fallback.py -q` 回归。

---

## [Unreleased] — 2026-07-14（第十轮：策略文件注册表 R1）

本轮落实后端审查报告（`docs/backend_review_report.md`）§4.3/§10「代码重复」与路线图 §5.1 的 **R1**：提取策略文件注册表。此前同一批策略/提示 `.txt` 文件名字面量在 `ai/router.py`（阶段一→阶段二文件路由）与 `ai/prompt_assembler.py`（提示词组装）中各写一遍，新增或重命名策略文件需同步改两处、极易漏改或写错中文文件名。**原则：抽出单一权威文件名常量，消除重复；文件名取值与顺序逐字节不变**——阶段二提示前缀命中 DeepSeek KV 缓存依赖 byte-identical 前缀，故所有消费方构建的文件列表必须与改动前完全一致。

### 代码清理

- **新增 `pa_agent/ai/strategy_files.py`（单一事实来源）**：把 27 个策略/提示 `.txt` 文件名各定义一次为模块级常量（`PERSONA`/`BINARY_DECISION`/`MARKET_DIAGNOSIS`/`BULLISH_CHANNEL_ID` 等）。纯数据模块，仅 `from __future__ import annotations`，无第三方依赖，可安全被 `router.py`（运行期可导入）与 `prompt_assembler.py` 共同引用。
- **`ai/router.py` 引用注册表**：17 组文件名常量（`_BULLISH_CHANNEL_FILES`、`_WEDGE_FILE`…）与 `_ALL_VALID_FILES`（27 文件 frozenset）的字面量改为引用 `strategy_files as sf` 的常量；常量名、聚合结构、`route_strategy_files` 及其分支逻辑全部保持不变。
- **`ai/prompt_assembler.py` 引用注册表**：`COMMON_SYSTEM_STAGE1_TXT_FILES`、`COMMON_SYSTEM_STAGE2_TXT_FILES`、`STAGE1_TASK_PROMPT_TXT_FILES`、`STAGE2_BASE_PROMPT_TXT_FILES`、`STAGE2_FULL_STRATEGY_PROMPT_TXT_FILES`、`_CHANNEL_FILE_GROUPS`、`_SPIKE_FILE_GROUPS` 内的文件名字面量改为引用 `sf.*`；**导出符号名、元组元素顺序、行尾注释一律不变**，消费函数（`stage1_prompt_txt_files`、`stage2_user_task_txt_files`、`stage2_prompt_txt_files`）零改动。

### 明确不改（保持原样）

- **`ai/pattern_routing.py` 不纳入本轮**：该文件的策略文件名嵌在 `STAGE1_DETECTED_PATTERNS_GUIDE` / `STAGE1_PATTERN_BRIEFS_BLOCK` 两段**提示词 markdown 表格散文**里（如 `| wedge | … | 文件14-楔形形态分析交易.txt |`），属 KV 缓存敏感的提示正文；用字符串插值替换会带来逐字节差异风险且无功能收益，故本轮不动，保留为提示内容。
- **既有告警**（RUF001 中文标点等）：不在 R1 范围内，未改动。

### 验证

- `py_compile` 通过（`strategy_files.py`、`router.py`、`prompt_assembler.py`）。
- **等价性验证**：`router.py` 常量与 `_ALL_VALID_FILES`（27 文件）实测与改动前字面量逐一相等；`prompt_assembler.py` 五个导出元组从 git `HEAD` 提取旧字面量后与新值逐元素比对，全部 byte-identical（长度 2/2/2/4/22）。`route_strategy_files` 对 property 测试 4 个精确用例（spike-transitioning、alternative-cycle、broad-channel-neutral、pattern-overlays）输出与断言一致；复刻 `test_prompt_txt_files.py` 全部 4 个用例（stage1 列表、bullish 路由过滤、full-library、stage2 顺序）对新常量断言通过。
- `ruff check` 对比基线：`strategy_files.py`/`router.py` **All checks passed**；`prompt_assembler.py` 1384 条、`pattern_routing.py` 54 条**与改动前逐项一致、零新增**。
- `git diff` 密钥扫描（`sk-...` / `api_key=...`）0 命中；新增文件同样无敏感内容。
- 本机 `PyQt6` / `hypothesis` 缺失（与既往各轮一致），无法直接跑 `pytest`；已用等价脚本复刻两测试文件的全部断言逻辑对新常量验证通过，建议在项目 venv 运行 `pytest tests/property/test_router_determinism.py tests/unit/test_prompt_txt_files.py -q` 回归。

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
