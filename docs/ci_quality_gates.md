# CI 质量门禁

## Ruff 全仓基线

CI 使用固定的 `ruff 0.15.13` 运行：

```cmd
python scripts/check_ruff_baseline.py
```

该脚本执行 `python -m ruff check . --output-format=json`，并将每条诊断的相对路径、规则码、
起止位置和消息与 [`scripts/ruff_baseline.json`](../scripts/ruff_baseline.json) 做严格集合比对。
当前批准基线为 **3,725** 条诊断。

因此，以下变化都会使门禁失败：

- 新增 Ruff 诊断；
- 现有诊断的规则、位置或消息发生变化；
- 已清理的诊断从基线消失但未同步更新基线。

历史问题只能在独立清理迭代中修复。完成审查和验证后，使用以下命令更新基线，并将代码修复与
基线变更提交在同一原子提交中：

```cmd
python scripts/check_ruff_baseline.py --write-baseline
python scripts/check_ruff_baseline.py
```

不要通过扩大 Ruff `ignore`、全局 `noqa` 或删除被检查范围来绕过门禁。Ruff 版本由
`pyproject.toml` 的开发依赖固定；升级 Ruff 时必须先审查新版本诊断，再显式更新版本和基线。

## Targeted 测试覆盖率

CI 的 targeted pytest 集执行 `--cov=pa_agent --cov-fail-under=50`，并同时输出终端报告和
`coverage.xml`。51% 是 2026-07-17 Windows/Python 3.12 的实测基线；50% 为保留一百分点
环境波动余量后的门禁，不得通过缩小测试集或排除业务包来维持通过。
