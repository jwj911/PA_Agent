# L5 真实证据离线评估阻塞诊断

> 诊断 ID：`PA-L5-REAL-EVIDENCE-BLOCKED-001`
>
> 日期：2026-07-31
>
> 基线：`main@71de023`
>
> 状态：真实数据前置条件稳定阻塞；L5 仍未完成

## 诊断结论

现有 curation、review catalog 和 readiness 工具按既定合同工作。本轮阻塞来自真实已平仓结果、
本地 evidence 和第二 instrument group 缺失，**不是代码缺陷**。

连续三轮只复现了相同 blocker，没有生成或推断 Recall@K、NDCG@K、fallback、ranking
stability、score distribution 或新旧差值。当前不存在可用于判断真实检索质量的指标，也没有
用合成案例、自动 outcome 或空产物伪造完成。

## Aggregate-Only 事实

| 检查 | 三轮结果 | 退出码 |
|---|---|---:|
| pending record scan | `record_count=2`、`eligible=1`、`partial=1`、`trending_tr=1` | `0` |
| annotation export preflight | `ready=false`；`evaluation_salt_missing`、`no_experience_cases` | `1` |
| evaluation preflight | `ready=false`；另含 `annotations_not_provided` | `1` |

三轮 scan、export preflight 和 evaluation preflight 的规范 JSON 对象及退出码逐轮完全一致。
该结果只证明 blocker 可复现，不代表 dataset、split 或评估报告可复现。

Review catalog 使用 `pa-agent.experience-curation-review.v1`，聚合结果为 `eligible=1`。schema
字段和安全 allowlist 检查通过，产物受 Git ignore 保护；本诊断不记录实际 `record_id`、
catalog digest、文件名或路径。操作者已明确让唯一 eligible 记录继续 defer；当前没有可核验
outcome evidence，也没有第二 instrument group。

## 规范对象摘要

SHA-256 对 UTF-8 规范 JSON 计算：键排序、无缩进、分隔符固定为 `,` 和 `:`。这里只记录完整
对象摘要，不记录原始记录、市场数据、salt、evidence 摘要或本地路径。

| 对象 | Schema | 完整 SHA-256 |
|---|---|---|
| scan | `pa-agent.experience-curation-scan.v1` | `b04c4b57ec359e05af98c49cf1a11632603985bac0d17e7f1e43faba1f951f35` |
| export preflight | `pa-agent.experience-eval-readiness.v1` | `b9cfed9309d488caf508fe248e3613b3922e560b0ff223a6216ab48e541a6372` |
| evaluation preflight | `pa-agent.experience-eval-readiness.v1` | `eba3cacf8ddac6068c9aec882abb585ee486b9ad8bff99377868a9ea144b1d7a` |

## 缺失产物

当前为：

- 0 个真实 experience JSON；
- 0 个 outcome evidence；
- 0 个 annotation；
- 0 个 dataset、split 或 report；
- 未设置 evaluation salt。

因此 dataset digest、split digest 和聚合评估指标均为“不存在”，不能填写占位值或合成值。

## 行为与安全不变量

- 未修改 `ExperienceReader` 线上排序、相似度权重或 legacy fallback；
- 未修改 Prompt、Provider 路由或 Pipeline；
- 未导入记录，未生成真实数据产物，未放宽 evidence、annotation 或 split 门禁；
- aggregate-only 文档不包含 symbol、价格、PnL、K 线、Prompt/Provider 原文、API Key、
  salt、实际 `record_id`、evidence 摘要、文件名或本地路径。

## 质量门禁

- L5 聚焦测试：**27 passed**；
- Ruff 与 `py_compile`：通过；
- CI targeted 清单：**177** 个目标；
- focused Ruff 清单：**293** 个目标；
- Ruff baseline：**3,712** 条，通过；
- `git diff --check`：通过。

## 解锁动作

L5 只有在以下真实外部输入到位后才能继续：

1. 至少两个不同 symbol 的真实 eligible 已平仓记录；
2. 每条记录都有符合 `realized-net-pnl-sign.v1` 的人工 outcome 和可复核本地 evidence；
3. 建议至少 4 个真实案例，并尽量提供同 cycle 的跨 instrument 候选；
4. export readiness 通过后再使用会话级 salt 导出 opaque 模板，并完成人工 annotation；
5. evaluation readiness 通过后才生成固定 split 和 aggregate-only 报告。

若当前唯一 eligible 记录继续 defer，则至少需要新增两个不同 symbol 的真实 eligible 已平仓
记录及其本地 evidence。满足这些条件前，L5 保持“未完成”，不得调整线上权重。
