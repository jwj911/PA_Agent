# L6/L3 真实观察运行手册

本文用于在具备授权 Provider 凭据的环境中收集 L6 Headless 与 L3 Pipeline rollout 证据。
命令必须从仓库根目录执行，不读取 `config/settings.json`，不把凭据或观察产物提交到 Git。

## 1. 前置条件

- 仅在受控终端会话设置 `PA_AGENT_LIVE_API_KEY`；
- 可选设置 `PA_AGENT_LIVE_BASE_URL` 和 `PA_AGENT_LIVE_MODEL`；
- 不修改持久化配置；harness 未传 flag 时显式运行 legacy，传
  `--pipeline-builder-enabled` 时显式运行 Pipeline，与应用默认值无关；
- legacy 与 Pipeline 使用不同的 correlation id 和输出目录；
- `artifacts/` 已被 `.gitignore` 排除。

PowerShell 示例：

```powershell
$env:PA_AGENT_LIVE_API_KEY = "<session-only-secret>"
$env:PA_AGENT_LIVE_BASE_URL = "https://api.deepseek.com"
$env:PA_AGENT_LIVE_MODEL = "deepseek-v4-flash"
```

## 2. 运行两条路径

先运行 legacy：

```powershell
py -3.12 tools/run_live_headless_observation.py `
  --confirm-live `
  --output-dir artifacts/live-observation/legacy `
  --correlation-id legacy-live-001
```

再显式运行 Pipeline：

```powershell
py -3.12 tools/run_live_headless_observation.py `
  --confirm-live `
  --pipeline-builder-enabled `
  --output-dir artifacts/live-observation/pipeline `
  --correlation-id pipeline-live-001
```

每次运行只应输出 `pa-agent.live-observation.v1` 脱敏摘要。真实 Prompt、Provider 回复、价格、
symbol、API Key 和认证 token 值不得进入摘要或提交内容。

## 3. 单体自洽校验

```powershell
py -3.12 tools/validate_live_observation.py `
  --summary artifacts/live-observation/legacy/summary.json `
  --events artifacts/live-observation/legacy/legacy-live-001.events.jsonl `
  --records-dir artifacts/live-observation/legacy/records

py -3.12 tools/validate_live_observation.py `
  --summary artifacts/live-observation/pipeline/summary.json `
  --events artifacts/live-observation/pipeline/pipeline-live-001.events.jsonl `
  --records-dir artifacts/live-observation/pipeline/records
```

两次输出均须为 `pa-agent.live-observation-validation.v1` 且 `valid=true`。

## 4. Legacy/Pipeline 成对校验

```powershell
py -3.12 tools/compare_live_observations.py `
  --legacy-summary artifacts/live-observation/legacy/summary.json `
  --legacy-events artifacts/live-observation/legacy/legacy-live-001.events.jsonl `
  --legacy-records-dir artifacts/live-observation/legacy/records `
  --pipeline-summary artifacts/live-observation/pipeline/summary.json `
  --pipeline-events artifacts/live-observation/pipeline/pipeline-live-001.events.jsonl `
  --pipeline-records-dir artifacts/live-observation/pipeline/records
```

输出须为 `pa-agent.live-observation-pair-validation.v1` 且 `valid=true`。比较合同包括：

- legacy 明确关闭 Pipeline，另一条路径明确开启；
- 两次都实际到达 Provider 调用边界；
- correlation id 不同且各自事件流内部一致；
- terminal status、exception type、事件序列和记录写入结果一致；
- record 顶层字段、meta 字段、消息角色、阶段 payload presence、异常形状和 usage 字段一致。

该 L3 shape-only 成对校验刻意不比较两次独立 Provider 请求的正文、Prompt、价格、symbol、
时间戳、单次 token usage 计数或归一化 JSON 值。模型输出并非字节确定性；这些值不能作为
Pipeline 等价依据。M4 仅按第 7 节对多条观察做 aggregate-only 用量比较。若终态或事件序列因
Provider 输出波动不同，应保留两次失败摘要并重跑完整 pair，不得手工修改 artifact。

## 5. 验收与清理

- 至少完成一个 legacy/Pipeline `valid=true` pair，作为真实成功主路径证据；
- 默认 Pipeline 切换要求高于单个成功 pair：须按相同 Provider/model/shape-only 合同重复完整
  pair，观察无未解释的终态、事件或 record 结构偏差；不得选择性丢弃失败 pair；
- final/partial/cancel/failure 的控制流等价继续由固定 fixture 测试覆盖，不能用单次 live 成功
  替代失败路径矩阵；
- 人工复核仅看脱敏 validation 输出、GitHub/本地退出码和文件边界，不打开或提交原始记录正文；
- 完成后清除当前终端的 Provider 环境变量：

```powershell
Remove-Item Env:PA_AGENT_LIVE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:PA_AGENT_LIVE_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:PA_AGENT_LIVE_MODEL -ErrorAction SilentlyContinue
```

## 6. 已验收基线

2026-07-23/24 已完成三个连续真实成功 pair：

- correlation id：`legacy-live-20260723144709` /
  `pipeline-live-20260723144709`；
- correlation id：`legacy-live-20260723223943` /
  `pipeline-live-20260723223943`；
- correlation id：`legacy-live-20260724002527` /
  `pipeline-live-20260724002527`；
- 6 个单体 `pa-agent.live-observation-validation.v1` 均为 `valid=true`；
- 3 个成对 `pa-agent.live-observation-pair-validation.v1` 均为 `valid=true`；
- 六条路径均 `status=completed`、无 exception、写入 record，并产生相同 5 事件序列；
- shape-only record 合同一致；18 个本地产物文件中 API Key 原文字节扫描为 0 命中；
- process/user/machine 环境变量均已清理，原始 artifact 未提交。

该基线证明 L6 真实成功主路径和 L3 三轮稳定观察。结合 fixed-fixture 全终态矩阵，
`orchestrator.pipeline_builder_enabled` 已默认 `true`；显式 `false` 保留 legacy 回滚。

## 7. M4 Prompt 合同观察

M4 使用相同 live harness，但候选产物必须写入独立目录，不能混入历史基线。冻结的
M3-compatible 基线使用 Moonshot `https://api.moonshot.cn/v1` / `kimi-k3`；M4 候选必须使用
同一 Provider 合同，否则 Provider usage token 不可比较，comparator 会按设计失败关闭。
`run_live_headless_observation.py` 的通用默认值是 DeepSeek，不能依赖默认值执行本组对照。

```powershell
$env:PA_AGENT_LIVE_BASE_URL = "https://api.moonshot.cn/v1"
$env:PA_AGENT_LIVE_MODEL = "kimi-k3"

py -3.12 tools/run_live_headless_observation.py `
  --confirm-live `
  --output-dir artifacts/prompt-contract-m4-candidate-moonshot/legacy `
  --correlation-id m4-legacy-live-001

py -3.12 tools/run_live_headless_observation.py `
  --confirm-live `
  --pipeline-builder-enabled `
  --output-dir artifacts/prompt-contract-m4-candidate-moonshot/pipeline `
  --correlation-id m4-pipeline-live-001
```

随后生成 aggregate-only 候选报告、与 M3-compatible 基线比较，并由总评估器重新计算
comparison 后生成 M4 退出报告：

```powershell
py -3.12 tools/summarize_prompt_contract_live.py `
  --observations-root artifacts/prompt-contract-m4-candidate-moonshot `
  --contract-version m4.2 `
  --output docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json

py -3.12 tools/compare_prompt_contract_live.py `
  --baseline docs/evaluations/prompt_contract_live_m3_baseline_2026-07-27.json `
  --candidate docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json `
  --output docs/evaluations/prompt_contract_live_m4_comparison_2026-07-29.json

py -3.12 tools/evaluate_prompt_contract_m4.py `
  --live-baseline docs/evaluations/prompt_contract_live_m3_baseline_2026-07-27.json `
  --live-candidate docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json `
  --live-comparison docs/evaluations/prompt_contract_live_m4_comparison_2026-07-29.json `
  --output docs/evaluations/prompt_contract_m4_exit_2026-07-29.json
```

比较结果必须为 `pa-agent.prompt-contract-live-comparison.v1`，且
`gates.live_gate_passed=true`。门禁要求：

- 基线和候选各自 artifact 全部有效，且均包含 legacy/Pipeline；
- fixture 与 Provider 配置哈希完全一致；
- 终局校验失败率和验证重试率不高于 M3-compatible 基线；
- 模型 Prompt identity 输出率与语义路由冲突率不得回退；
- 平均输入 token 增幅不超过 10%，输出/总 token 只记录差值用于人工复核。

这里的 token 指 Provider 返回的**用量计数**，不是 API Key、Bearer token 或任何凭据值。
聚合器只输出计数、比率和合同哈希，不输出 correlation id、文件路径、Prompt、模型回复、
行情、symbol、价格或 Provider 配置值。没有会话级 `PA_AGENT_LIVE_API_KEY` 时不得执行候选
观察，也不得用历史记录复制出候选报告。

2026-07-29 的 M4 候选 legacy/Pipeline 均完成 5 事件并写入 record，单体 artifact 有效；
comparison 的 11 项 gate 全部通过，最终报告为 `m4_exit_gate_passed=true`。原始 artifact
继续留在 Git 忽略目录，只提交上述三份 aggregate-only 报告。
