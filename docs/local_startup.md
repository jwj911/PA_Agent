# PA Agent 本地启动说明

本文说明如何在本机启动当前项目，并补充开发者常用的本地验证命令。命令默认在 Windows PowerShell 中执行，且都应从项目根目录运行：

```powershell
cd d:\Code\price_action_agent
```

## 一分钟启动

普通 GUI 使用路径：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python run.py
```

首次启动后，在 GUI 的设置里填写 **Base URL**、**模型名** 与 **API Key**。如果需要先生成本地配置文件，也可以执行：

```powershell
copy config\settings.example.json config\settings.json
```

`config/settings.json` 是本地运行配置，已被 `.gitignore` 忽略，不应提交到 Git。

## 环境要求

| 项目 | 要求 |
| ---- | ---- |
| 操作系统 | Windows 10 / 11 为主支持环境；TradingView 等非 MT5 数据源可用于其他平台 |
| Python | 3.11+，本项目当前本地开发常用 Python 3.12 |
| Git | 用于拉取源码和查看变更 |
| 数据源 | 至少准备一种：MT5 / TradingView / yfinance / AkShare 等 |
| 网络 | 可访问所配置的 AI API 网关 |

MT5 数据源仅在 Windows 下可用，并要求本机 MetaTrader 5 终端已打开、已登录，且品种名与 MT5 市场报价中的名称一致。TradingView 可作为无 MT5 的启动路径，但可能受网络、匿名访问或品种权限限制。

## 安装依赖

普通使用安装基础依赖：

```powershell
pip install -e .
```

开发者安装测试、格式化和 lint 依赖：

```powershell
pip install -e ".[dev]"
```

如果 PowerShell 提示不能加载激活脚本，可在当前用户范围放宽执行策略后重新激活：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 本地配置

首次启动时，程序会读取或创建本地配置。也可以先从模板生成：

```powershell
copy config\settings.example.json config\settings.json
```

推荐在 GUI 设置中维护以下字段：

- `Base URL`：OpenAI 兼容 API 根地址。
- `模型名`：网关支持的模型名称。
- `API Key`：只填写自己的本地密钥，不写入文档、Issue、日志或测试样例。

Windows 下保存设置时，API Key 会按当前实现写入本地受保护配置；非 Windows 平台会按 `config/README.md` 中说明的兼容路径处理。无论哪种平台，都不要提交 `config/settings.json`。

如需自定义 TradingView 品种别名，可按需生成本地别名文件：

```powershell
copy config\tv_symbol_aliases.example.json config\tv_symbol_aliases.json
```

## 启动方式

推荐普通用户使用：

```powershell
python run.py
```

`run.py` 会处理 Spyder/Jupyter 这类内嵌 IPython 内核场景，必要时转到独立进程启动 GUI，避免内核直接退出。

其他等价入口：

```powershell
python -m pa_agent.main
pa-agent
```

无 GUI 的配置/snapshot 辅助命令：

```powershell
pa-agent headless validate-config --settings config\settings.json
pa-agent headless snapshot --input snapshot.json --output normalized.json
pa-agent headless analyze --input snapshot.json --output dry-run.json
```

headless 命令不创建 Qt `EventBus`，不连接数据源，stdout 只输出结构化 JSON，诊断写 stderr。
其中 `analyze` 当前只做 provider-free Stage 1 prompt dry-run，不调用真实 Provider，也不写入
分析记录；真实两阶段无 GUI runner 仍在后续迭代中。`snapshot.json` 可以是包含 `symbol`、
`timeframe`、`bars` 的对象，也可以使用分析记录中的 `meta` + `kline_data` 结构。

如果本机安装了 `make`，也可以使用：

```powershell
make run
```

## 开发者验证

本轮文档不要求真实 API Key、真实网络或真实 MT5 环境作为验证前提。开发者本地验证可优先运行无 live 依赖的命令。

检查 CI 目标清单：

```powershell
python scripts/check_ci_workflow_targets.py
```

运行非 live、非 e2e 测试。Qt 相关测试在无显示环境下使用 offscreen：

```powershell
$env:QT_QPA_PLATFORM="offscreen"
python -m pytest -m "not e2e and not live" --tb=line -q
```

检查 Ruff 基线：

```powershell
python scripts/check_ruff_baseline.py
```

Focused Ruff 的目标文件以 `.github/workflows/ci.yml` 中的清单为准。需要全量格式检查时，可参考 Makefile：

```powershell
make lint
```

## 常见问题

| 现象 | 处理 |
| ---- | ---- |
| `ModuleNotFoundError: No module named 'pa_agent'` | 确认在项目根目录执行，并已运行 `pip install -e .` 或 `pip install -e ".[dev]"` |
| `No module named 'PyQt6'` | 重新安装依赖：`pip install -e .` |
| 激活 `.venv` 失败 | 使用 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重新激活 |
| GUI 没出现或 Spyder/Jupyter 内核退出 | 在普通 PowerShell 终端执行 `python run.py` |
| MT5 未连接 | 打开并登录 MetaTrader 5，确认品种名含后缀且与市场报价一致 |
| API 调用失败 | 检查 Base URL、模型名、API Key 与网络连通性 |
| 启动后立即退出或无明显错误 | 查看 `logs/pa_agent.log` 与 `logs/crash.log` |

## 相关文档

- [README](../README.md)
- [PA Agent 使用文档](../PA_Agent使用文档.md)
- [配置字段说明](../config/README.md)
- [CI 质量门禁](ci_quality_gates.md)
