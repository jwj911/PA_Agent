# 可选语义审查 Agent 评估报告

> 诊断 ID：`PA-SEMANTIC-REVIEW-EVAL-001`
>
> 日期：2026-07-30
>
> 状态：评估完成；不进入生产实现

## 评估问题

M5 已完成 Prompt ID、阶段合同和 29 个模板的物理迁移。本轮回答两个问题：

1. 是否需要把市场诊断、交易决策等职责拆成更多常驻 Agent？
2. 是否值得在 Stage 1 与程序 router 之间增加一个语义审查 Agent？

本轮只做架构与证据评估，不修改运行时调用链、Prompt 正文、schema、Provider 配置或记录
格式。

## 当前边界

当前 Pipeline 为：

```text
Stage1Step -> RouteStep -> Stage2Step -> PersistStep
```

其中：

- Stage 1 已承担市场诊断职责，Stage 2 已承担交易决策职责；逻辑角色已经分离，不需要通过
  增加 Provider 调用才能获得职责边界。
- `TwoStageJsonValidator` 在模型输出进入下一阶段前执行 JSON/schema、Normalizer、gate、
  trace、bar-by-bar、pattern、跨字段和增量一致性检查。
- Stage 2 还执行 no-order、突破单依据、信号链、预测、交易指标、Stage 1/2 coherence 和
  trace semantic checks。
- `validate_with_retry()` 只对允许的格式/语义错误做有界重试；`detect_cheat()` 防止重试时
  无依据修改 `direction`、`cycle_position` 等不可变判断。
- `RouteStep` 使用规范化 Stage 1 JSON 调用程序 router；模型不能选择 Prompt ID 或物理
  文件，router 异常失败关闭并写 partial record。

因此，新增 Agent 不是为了补齐缺失的职责分层，而只能用于发现“schema 与现有规则均通过，
但人类仍判定语义错误”的剩余问题。

## 现有实证

M4 真实候选包含 1 条 legacy 和 1 条 Pipeline：

| 指标 | 结果 |
|---|---:|
| 完成并实际调用 Provider | 2/2 |
| 终局校验失败 | 0/2 |
| 发生验证重试 | 0/2 |
| 模型 Prompt identity 输出 | 0/2 |
| 模型输出与 router 冲突 | 0/2 |
| 平均输入 token | 109,392.50 |
| 平均总 token | 124,255.00 |

这能证明当前主路径在固定合同下可用，不能证明罕见语义错误率为 0，也不能证明第三个 Agent
能改善结果。当前没有一组经人工裁决的“validator 通过但语义错误”真实案例，因而不存在可
计算的新增召回率。

仅运行 10 批可用于验证工具链和输出合同，不能作为上线依据。即使 10 个 clean case 中观察到
0 次误报，按 `rule of three`，95% 置信上界仍约为 30%，远高于可接受的 5% 误报目标。

## 方案比较

| 方案 | 潜在收益 | 主要问题 | 结论 |
|---|---|---|---|
| 保持当前两阶段与确定性校验 | 无新增调用；router 权威清晰；失败模式已测试 | 可能遗漏规则外语义错误 | 当前生产基线 |
| 常驻 Stage 1 审查 Agent | 可能发现诊断与行情叙述矛盾 | 增加调用、延迟、误报和双模型分歧；没有正样本证明收益 | 不采用 |
| 常驻 Stage 2 critic | 可能复核下单理由 | 决策后再争议会引入第三套权威与循环重试风险 | 不采用 |
| 离线 shadow 语义审查 | 可测量新增召回、误报、token 与延迟；不影响交易路径 | 需要人工标签与足量真实案例 | 唯一允许的后续试验 |

把市场诊断和交易决策分别做成独立常驻 Agent 也不推荐。当前 Stage 1/Stage 2 已提供角色、
Prompt 和输出合同隔离；新增两个 Agent 实例只会复制共享上下文、提高 token/延迟，并增加
跨 Agent 状态一致性问题。

## 评估结论

**当前不实现生产语义审查 Agent，也不引入多 Agent。**

理由：

1. 当前问题率证据不足：真实候选只有 2 条，且没有经人工确认的规则外语义错误。
2. 当前防线已覆盖 schema、归一化、coherence、trace、业务规则、重试与路由权威。
3. 第三个模型调用的准确率、误报、Provider 失败、token 和 p95 延迟均没有基线。
4. 在没有正样本时实现 Agent 会先增加系统复杂度，再寻找它要解决的问题，违反证据优先原则。

允许的下一步仅是**脱敏后喂养、离线隔离、完全人工触发**的 shadow 评估。评估结果不得自动
修改 Stage 1、重新路由、触发 Stage 2 重试或写入生产记录。

## Shadow 候选合同

若未来具备足量案例，可建立本地工具而非 Pipeline step：

```json
{
  "schema": "pa-agent.semantic-review.v1",
  "verdict": "pass|flag",
  "issues": [
    {
      "code": "stable_machine_code",
      "field": "cycle_position",
      "severity": "warning|error",
      "reason": "human-readable explanation"
    }
  ]
}
```

输入边界：

- 只读取本地、已脱敏的规范化 Stage 1 JSON、必要的程序特征和确定性校验摘要；
- 不向模型暴露 API Key、Provider 配置、本地绝对路径、Prompt ID、legacy filename 或
  原始持久化记录；
- 原始案例、Prompt 和回复只保存在 Git 忽略目录；仓库只提交 aggregate-only 指标。

执行边界：

- 每个案例最多一次审查调用，无 Agent-to-Agent 对话和无监督循环；
- reviewer 只输出 `pass|flag` 与问题列表，不产生 route、Prompt 选择或交易决策；
- Provider 失败只标记该离线样本不可用，不影响生产 Pipeline；
- 默认不开启，必须由操作者显式执行。

## 进入实现前的门禁

只有同时满足以下条件，才重新评估一个 opt-in shadow 工具：

1. 至少 20 个经人工裁决的“validator 通过但语义错误”正样本。
2. 至少 60 个按 channel/spike/range、方向和执行模式分层的 clean negative；10 批只算
   smoke，不算决策级证据。
3. 标签来自人工证据，不使用待评估模型自我标注作为真值。
4. 对正样本的新增召回率至少 80%，clean negative 误报率不超过 5%。
5. 相同输入重复运行的 verdict 稳定率至少 95%。
6. 平均输入 token 增幅不超过当前两阶段基线的 10%，p95 端到端延迟增幅不超过 20%。
7. aggregate 报告通过敏感字段扫描，并具有固定 dataset/provider/contract 哈希。

只有 shadow 门禁通过后，才另开架构迭代讨论是否增加 `SemanticReviewPort`。即便进入运行时
试验，首阶段也只能记录 advisory flag，不能成为 router 或交易决策权威。

## 后续优先级

当前不创建 Agent 代码。L2 保持现状并继续观察 validator/retry/route 指标；项目优先级恢复为
L5 真实 outcome/evidence 数据收集。只有积累到上述正负样本门槛，才重新打开语义审查 Agent
议题。
