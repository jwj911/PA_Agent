# L6/L3 真实观察运行手册

本文用于在具备授权 Provider 凭据的环境中收集 L6 Headless 与 L3 Pipeline rollout 证据。
命令必须从仓库根目录执行，不读取 `config/settings.json`，不把凭据或观察产物提交到 Git。

## 1. 前置条件

- 仅在受控终端会话设置 `PA_AGENT_LIVE_API_KEY`；
- 可选设置 `PA_AGENT_LIVE_BASE_URL` 和 `PA_AGENT_LIVE_MODEL`；
- 保持 `orchestrator.pipeline_builder_enabled` 默认值为 `false`；
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
symbol、API Key 和 token 值不得进入摘要或提交内容。

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

成对校验刻意不比较两次独立 Provider 请求的正文、Prompt、价格、symbol、时间戳、token 数值或
归一化 JSON 值。模型输出并非字节确定性；这些值既不能作为 Pipeline 等价依据，也不能进入脱敏
报告。若终态或事件序列因 Provider 输出波动不同，应保留两次失败摘要并重跑完整 pair，不得手工
修改 artifact。

## 5. 验收与清理

- 至少完成一个 legacy/Pipeline `valid=true` pair，作为真实成功主路径证据；
- final/partial/cancel/failure 的控制流等价继续由固定 fixture 测试覆盖，不能用单次 live 成功
  替代失败路径矩阵；
- 人工复核仅看脱敏 validation 输出、GitHub/本地退出码和文件边界，不打开或提交原始记录正文；
- 完成后清除当前终端的 Provider 环境变量：

```powershell
Remove-Item Env:PA_AGENT_LIVE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:PA_AGENT_LIVE_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:PA_AGENT_LIVE_MODEL -ErrorAction SilentlyContinue
```
