# M4 Prompt 合同评估

> 状态：M4.3 离线与真实 Provider 合同评估完成；M4 退出门禁通过
>
> 日期：2026-07-29
>
> 历史离线报告：[`evaluations/prompt_contract_m4_2026-07-27.json`](./evaluations/prompt_contract_m4_2026-07-27.json)
>
> 真实基线：[`evaluations/prompt_contract_live_m3_baseline_2026-07-27.json`](./evaluations/prompt_contract_live_m3_baseline_2026-07-27.json)
>
> M4 候选：[`evaluations/prompt_contract_live_m4_candidate_2026-07-29.json`](./evaluations/prompt_contract_live_m4_candidate_2026-07-29.json)
>
> 真实比较：[`evaluations/prompt_contract_live_m4_comparison_2026-07-29.json`](./evaluations/prompt_contract_live_m4_comparison_2026-07-29.json)
>
> 最终退出报告：[`evaluations/prompt_contract_m4_exit_2026-07-29.json`](./evaluations/prompt_contract_m4_exit_2026-07-29.json)

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

## 4. M4.3b 真实候选结果

2026-07-29 使用与冻结基线相同的 Provider/fixture 合同，在干净 detached worktree
`main@8b62b29` 中分别执行一次 legacy 与 Pipeline。两条路径均完成 5 事件、实际调用 Provider、
写入 record，且单体 `pa-agent.live-observation-validation.v1` 均为 `valid=true`。

| 指标 | M3-compatible 基线 | M4.2 候选 | 变化 |
|---|---:|---:|---:|
| 观察数 | 6（legacy 3、Pipeline 3） | 2（legacy 1、Pipeline 1） | - |
| 终局校验失败率 | 0% | 0% | 0 |
| 验证重试 run rate | 0% | 0% | 0 |
| 模型 Prompt identity 输出率 | 100% | 0% | -100 个百分点 |
| 模型 filename 与 router 冲突率 | 100% | 0% | -100 个百分点 |
| 平均输入 token | 110,240.33 | 109,392.50 | -847.83（-0.769%） |
| 平均输出 token | 14,862.83 | 14,862.50 | -0.33 |
| 平均总 token | 125,103.17 | 124,255.00 | -848.17 |

比较器的 baseline/candidate 有效性、legacy/Pipeline 配对、Provider/fixture 哈希一致、失败率、
重试率、identity 输出、路由冲突和 10% token 阈值共 11 项 gate 全部为 true，
`gates.live_gate_passed=true`。最终评估器重新计算 comparison 并校验候选/比较文件 SHA-256，
得到：

- `live_observation.status=passed`；
- `live_observation.evidence_collected=true`；
- `gates.offline_gate_passed=true`；
- `gates.live_gate_passed=true`；
- `gates.m4_exit_gate_passed=true`。

原始 summary/event/record 继续保存在 Git 忽略的 `artifacts/`，不提交。仓库只保存聚合计数、
比率、合同哈希和报告 SHA-256；不保存 correlation id、Prompt、回复、行情、symbol、价格、
Provider 配置值或凭据。M4 已满足退出条件，后续可按独立原子切片进入 M5。

## 5. 复现

```powershell
python -c "from importlib.metadata import version; print(version('tiktoken'))"
python tools/summarize_prompt_contract_live.py `
  --observations-root artifacts/prompt-contract-m4-candidate-moonshot `
  --contract-version m4.2 `
  --output docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json
python tools/compare_prompt_contract_live.py `
  --baseline docs/evaluations/prompt_contract_live_m3_baseline_2026-07-27.json `
  --candidate docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json `
  --output docs/evaluations/prompt_contract_live_m4_comparison_2026-07-29.json
python tools/evaluate_prompt_contract_m4.py `
  --live-baseline docs/evaluations/prompt_contract_live_m3_baseline_2026-07-27.json `
  --live-candidate docs/evaluations/prompt_contract_live_m4_candidate_2026-07-29.json `
  --live-comparison docs/evaluations/prompt_contract_live_m4_comparison_2026-07-29.json `
  --output docs/evaluations/prompt_contract_m4_exit_2026-07-29.json
python -m pytest `
  tests/unit/test_prompt_contract_evaluation.py `
  tests/unit/test_prompt_contract_live_summary.py `
  tests/unit/test_prompt_contract_live_comparison.py -q
```
