# CI 质量门禁

## Python 版本矩阵

CI 在 `windows-latest` 上同时运行 Python **3.11** 与 **3.12**。3.11 是
`pyproject.toml` 中 `requires-python = ">=3.11"` 声明的最低支持版本，3.12 是当前开发和
覆盖率校准环境。所有安装、测试、Ruff 与 Black 门禁必须在两个矩阵任务中通过。

## CI 工作流目标清单自检

CI 在安装验证后执行：

```cmd
python scripts/check_ci_workflow_targets.py
```

该脚本使用 stdlib 解析 `.github/workflows/ci.yml` 中的 `Run targeted tests` 与
`Run focused Ruff checks` 目标清单，并检查：

- 目标清单非空；
- 同一清单内不存在重复路径；
- 每个目标路径在仓库中真实存在；
- focused Black 仍通过 `Run focused Ruff checks` 锚点复用同一份 `@targets`。

修改 targeted pytest 或 focused Ruff 清单时，应先运行该脚本。不要手工复制第二份 Black 目标列表；
Black 门禁必须继续复用 focused Ruff 的目标集合，避免两个质量门禁覆盖范围漂移。

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

## Focused Black 格式

CI 使用固定的 `black 24.10.0`。`Run focused Black format check` 从同一工作流的
`Run focused Ruff checks` 步骤读取目标路径，并运行 `python -m black --check`；两个门禁因此
始终覆盖完全相同的范围，修改 focused Ruff 清单时无需维护第二份路径列表。

本地可使用以下命令复现：

```powershell
$workflow = Get-Content .github/workflows/ci.yml
$start = [Array]::IndexOf($workflow, '      - name: Run focused Ruff checks')
$targets = @()
$collect = $false
foreach ($line in $workflow[$start..($workflow.Length - 1)]) {
    if ($line.Trim() -eq 'python -m ruff check') { $collect = $true; continue }
    if ($collect -and $line -match '^\s{6}- name:') { break }
    if ($collect -and $line -match '^\s{10}(.+)$') { $targets += $Matches[1].Trim() }
}
python -m black --check @targets
```

格式化仅限上述 focused 范围；不要通过缩小 Ruff 目标列表、跳过 Black 步骤或将尚未验证的全仓文件
并入该门禁来获得通过。

## Targeted 测试覆盖率

CI 的 targeted pytest 集在 Python 3.11 与 3.12 上均执行
`--cov=pa_agent --cov-fail-under=50`，并同时输出终端报告和 `coverage.xml`。2026-07-17
在 Windows/Python 3.12 实测基线为 **50.95%**；50% 为保留环境波动余量后的门槛。两条矩阵
任务都必须满足该门槛，不得通过缩小测试集或排除业务包来维持通过。
