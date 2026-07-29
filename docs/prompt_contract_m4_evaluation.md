# M4 Prompt 合同评估

> 状态：M4.3a 离线评估、tokenizer 可复现性门禁与 M3-compatible 真实基线完成；M4 候选观察等待会话级凭据
>
> 日期：2026-07-29
>
> 离线报告：[`evaluations/prompt_contract_m4_2026-07-27.json`](./evaluations/prompt_contract_m4_2026-07-27.json)
>
> 真实基线：[`evaluations/prompt_contract_live_m3_baseline_2026-07-27.json`](./evaluations/prompt_contract_live_m3_baseline_2026-07-27.json)

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

### 1.1 Tokenizer 可复现性

M3.3 基线使用 `tiktoken 0.12.0` 的 `cl100k_base` 编码。`pyproject.toml` 因此精确固定
`tiktoken==0.12.0`，`test_project_pins_the_baseline_tokenizer_version` 会校验项目依赖声明与
基线元数据一致。若 fresh install 解析到其他版本，评估器必须保持
`tokenizer_comparable=false` 并关闭离线门禁，不能用新版本 token 数与旧基线比较。

升级 tokenizer 时必须在独立迭代中同时更新依赖版本、重建 M3 基线、重生成 M4 报告并审查
四种 Prompt 的 token 差异；不得只放宽版本比较或修改精确结果断言。GitHub Actions runs
`30228832510`、`30234921782` 暴露的双矩阵失败即由未固定的 `tiktoken>=0.7` 在 fresh
runner 中解析到 `0.13.0` 导致。固定版本后的 GitHub Actions run `30416289654` 已在
Python 3.11/3.12 全门禁通过。

## 2. 离线结果

| 指标 | M3.3 | M4.2 | 变化 |
|---|---:|---:|---:|
| schema 校验失败 | 0/4 | 0/4 | 0 |
| 需要重试 | 0/4 | 0/4 | 0 |
| Normalizer 后路由冲突 | 2/4 | 0/4 | -50 个百分点 |
| 四种 Prompt 合计估算 token | 309,649 | 309,642 | -7 |

单一 Prompt 形态的最大 token 上浮为 prefix-chain 的 10 tokens，比例约 `0.0089%`，
低于版本化门禁 `0.1%`；四种形态的消息数量均未变化，字节数均下降。离线门禁通过。

## 3. M3-Compatible 真实基线

2026-07-23/24 的三组 legacy/Pipeline 真实成功 pair 仍保存在 Git 忽略目录。M1-M3 明确保持
Prompt 字节、schema 和 Provider 行为不变，因此这 6 条记录可作为 M3-compatible 基线。
`tools/summarize_prompt_contract_live.py` 会先逐条验证 summary/event/record 自洽性，再仅输出
聚合值和 fixture/provider 合同哈希。

| 指标 | M3-compatible 基线 |
|---|---:|
| 观察数 | 6（legacy 3、Pipeline 3） |
| 完成并实际调用 Provider | 6/6 |
| 终局校验失败 | 0/6 |
| 发生验证重试 | 0/6 |
| 模型输出 Prompt filename | 6/6 |
| 模型 filename 与 router 冲突 | 6/6 |
| 平均输入 token | 110,240.33 |
| 平均输出 token | 14,862.83 |
| 平均总 token | 125,103.17 |

6 条记录的 fixture 哈希和 Provider 配置哈希分别保持唯一。报告不包含原始路径、correlation id、
Prompt、回复、行情、symbol、价格或 Provider 配置值。M4 候选必须使用相同两个合同哈希，
至少包含一条 legacy 和一条 Pipeline 观察。

## 4. 限制与后续

当前进程未设置 `PA_AGENT_LIVE_API_KEY`，因此没有执行真实 Provider 请求。
机器可读报告必须保持：

- `live_observation.status=blocked_missing_session_api_key`；
- `live_observation.evidence_collected=false`；
- `gates.m4_exit_gate_passed=false`。

获得会话级凭据后，按 [`live_observation_runbook.md`](./live_observation_runbook.md) 在独立目录
执行 M4 legacy/Pipeline 成对观察，生成候选聚合报告，再由
`tools/compare_prompt_contract_live.py` 与上述 M3-compatible 基线比较。真实终局校验失败率和
验证重试率不得上升，fixture/provider 合同必须相同，平均输入 token 增幅不得超过 10%。
不得读取持久化配置绕过凭据要求，也不得把离线合成指标表述为真实 Provider 结果。

## 5. 复现

```powershell
python -c "from importlib.metadata import version; print(version('tiktoken'))"
python tools/evaluate_prompt_contract_m4.py `
  --output docs/evaluations/prompt_contract_m4_2026-07-27.json
python tools/summarize_prompt_contract_live.py `
  --observations-root artifacts/live-observation `
  --contract-version m3-compatible `
  --output docs/evaluations/prompt_contract_live_m3_baseline_2026-07-27.json
python -m pytest `
  tests/unit/test_prompt_contract_evaluation.py `
  tests/unit/test_prompt_contract_live_summary.py `
  tests/unit/test_prompt_contract_live_comparison.py -q
```
