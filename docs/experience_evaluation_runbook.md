# L5 经验库离线评估运行手册

本文用于把本地真实经验库转为脱敏人工标注模板，并生成固定 instrument-group split 下的
Recall@K、NDCG@K、fallback rate 和 ranking stability 报告。流程只做离线评估，不修改
`ExperienceReader` 的线上排序或权重。

## 1. 数据前置条件

- `experience/<cycle_position>/success_cases|failure_cases/*.json` 至少包含两个 instrument group；
- 文件名包含 `YYYY-MM-DD_HH-mm-ss`；
- 每条案例可解析出 symbol、timeframe、direction 和 detected_patterns；
- symbol 只在本地用于生成 opaque HMAC ID，不进入导出文件；
- 经验 JSON、标注文件、dataset、split 和报告均保留在被 Git 忽略的 `artifacts/`。

## 2. 设置会话 salt

使用至少 16 字节的随机 salt。导出与评估必须使用同一个值；salt 不写入命令参数、文件、日志、
仓库或聊天。

```powershell
$env:PA_AGENT_EXPERIENCE_EVAL_SALT = "<session-only-random-salt>"
```

## 3. 导出人工标注模板

```powershell
py -3.12 tools/run_experience_evaluation.py export-labels `
  --experience-dir experience `
  --output artifacts/experience-eval/annotations.json
```

输出 schema 为 `pa-agent.experience-annotation.v1`。模板只包含：

- opaque `case_id` / `instrument_id`；
- timeframe、cycle position、direction、patterns、success/failure；
- 同 cycle 的 opaque candidate IDs、candidate count 和 similarity fallback 标志；
- `reviewed=false` 与空 `relevant_ids`。

模板不得包含 symbol、价格、K 线原文、截图/本地路径、API Key、salt 或 Provider 内容。

## 4. 人工标注

逐条复核模板：

1. 从 `candidate_ids` 中选择结构上相关的案例 ID，写入 `relevant_ids`；
2. 允许确实没有相关案例时保留空列表；
3. 完成后把 `reviewed` 改为 `true`；
4. 不修改模板中的其他元数据、catalog digest 或候选列表。

评估命令会拒绝未复核、漏项、重复 case、catalog digest 不匹配、元数据被修改或引用候选集外 ID。

## 5. 生成固定 split 与报告

```powershell
py -3.12 tools/run_experience_evaluation.py evaluate `
  --experience-dir experience `
  --annotations artifacts/experience-eval/annotations.json `
  --output-dir artifacts/experience-eval/report `
  --evaluation-fraction 0.2 `
  --k 3
```

输出：

- `dataset.json`：`pa-agent.experience-eval.v1` 脱敏标注数据集；
- `split.json`：`pa-agent.experience-split.v1` instrument-grouped 固定切分；
- `report.json`：`pa-agent.experience-eval-report.v1` 旧排序与 similarity 排序指标对照。

报告只保留版本、dataset digest、split、计数、Recall/NDCG/fallback/stability、score
distribution 和指标差值，不包含原始案例内容。

## 6. 验收边界

- 至少两个 instrument group，且 train/evaluation group 无交叉；
- 所有案例 `reviewed=true`；
- 报告可用同一经验目录、annotation 和 salt 重复生成；
- 线上排序保持不变，`online_sorting_changed=false`；
- 在 evaluation case 数量和人工标签不足时，不据指标调整线上权重；
- 指标改善、ranking stability 和人工抽样均满足后，权重变更必须另开迭代并保留 legacy fallback。

完成后清除 salt：

```powershell
Remove-Item Env:PA_AGENT_EXPERIENCE_EVAL_SALT -ErrorAction SilentlyContinue
```
