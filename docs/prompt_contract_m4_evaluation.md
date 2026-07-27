# M4 Prompt 合同评估

> 状态：M4.3a 离线评估完成；M4.3b 真实 Provider 观察因缺少会话级凭据阻塞
>
> 日期：2026-07-27
>
> 机器可读报告：[`evaluations/prompt_contract_m4_2026-07-27.json`](./evaluations/prompt_contract_m4_2026-07-27.json)

## 1. 评估边界

本轮以 Prompt ID M3.3 提交 `2fc73e23a532534c9b468bab54ab8559e44bf871` 为基线，
使用相同的固定合成 K 线 fixture 比较 M4.2。报告只保存消息计数、字节数、字符数、
`cl100k_base` 估算 token、SHA-256 和聚合合同指标，不保存 Prompt、模型回复、行情正文、
价格、symbol、Provider 凭据或本地绝对路径。

离线路由合同语料包含 4 个合成 Stage 1 输出：

1. 旧 filename 输出与 router 一致；
2. 新 schema 不输出 filename；
3. 旧 `strategy_files_needed` 与 router 冲突；
4. 旧 `recommended_strategy_files` 与 router 冲突。

这些案例用于验证 schema、Normalizer 和 router 的确定性合同，不代表真实模型输出分布。

## 2. 离线结果

| 指标 | M3.3 | M4.2 | 变化 |
|---|---:|---:|---:|
| schema 校验失败 | 0/4 | 0/4 | 0 |
| 需要重试 | 0/4 | 0/4 | 0 |
| Normalizer 后路由冲突 | 2/4 | 0/4 | -50 个百分点 |
| 四种 Prompt 合计估算 token | 309,649 | 309,642 | -7 |

单一 Prompt 形态的最大 token 上浮为 prefix-chain 的 10 tokens，比例约 `0.0089%`，
低于版本化门禁 `0.1%`；四种形态的消息数量均未变化，字节数均下降。离线门禁通过。

## 3. 限制与后续

当前进程未设置 `PA_AGENT_LIVE_API_KEY`，因此没有执行真实 Provider 请求。
机器可读报告必须保持：

- `live_observation.status=blocked_missing_session_api_key`；
- `live_observation.evidence_collected=false`；
- `gates.m4_exit_gate_passed=false`。

获得会话级凭据后，按 [`live_observation_runbook.md`](./live_observation_runbook.md) 执行
legacy/Pipeline 成对观察，并额外记录真实校验失败率、重试率、输入/输出 token 和语义冲突。
不得读取持久化配置绕过凭据要求，也不得把离线合成指标表述为真实 Provider 结果。

## 4. 复现

```powershell
python tools/evaluate_prompt_contract_m4.py `
  --output docs/evaluations/prompt_contract_m4_2026-07-27.json
python -m pytest tests/unit/test_prompt_contract_evaluation.py -q
```
