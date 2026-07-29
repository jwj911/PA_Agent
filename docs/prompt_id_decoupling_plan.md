# Prompt ID 与文件名解耦方案

> 状态：M1-M4.3 与 M5.0-M5.2 已完成；后续分批迁移剩余 27 个模板
>
> 日期：2026-07-29
>
> 适用范围：L2 Prompt 模板引擎、策略路由、两阶段 Pipeline、分析记录与 Prompt 调试界面
>
> 前置基线：29 个运行时 Prompt 已纳入 `TemplateStore`、manifest 与 UTF-8 golden snapshot

## 1. 决策摘要

当前系统把 `.txt` 文件名同时用作模板身份、文件定位、路由结果、模型输出值、Pipeline 状态、
分析记录字段和 GUI 展示文本。任何重命名、移动或后缀迁移都会跨越上述边界，不能只修改
`TemplateStore`。

本方案采用三层身份模型：

1. **`prompt_id`**：程序内部唯一、稳定、不可由文件路径推导的逻辑身份。
2. **`source_path`**：相对 `prompt_engineering/` 的可变存储位置。
3. **`display_name`**：面向文档、GUI 和诊断界面的可变显示名称。

另保留 **`legacy_filename`** 作为旧 API 和旧记录的不可变兼容投影。它不再用于定位文件，
也不会随 `source_path` 迁移为 `.prompt.md`。

迁移遵循以下决策：

- 路由器、Prompt 组装器、Pipeline 和新记录最终只以 `prompt_id` 传递模板身份。
- 文件系统访问只能由 manifest/catalog 将 `prompt_id` 解析为 `source_path` 后执行。
- `prompt_id` 由程序路由产生，模型不得选择、拼写或输出 `prompt_id`。
- 现有 `strategy_files_needed` 和 `strategy_files_used` 在兼容期保留；新旧字段双读、双写，
  但内部核心不再把文件名当作身份。
- M1-M3 必须保持 Stage 1、Stage 2、standalone、continuation 和共享 system prompt
  **字节完全一致**；任何 Prompt 文本或 JSON 输出合同变化推迟到 M4 单独评估。
- `.txt` 改为 `.prompt.md` 仅是 M5 可选存储迁移，不是本方案的前置条件。

## 2. 当前耦合面

| 边界 | 当前合同 | 风险 |
|---|---|---|
| `ai/strategy_files.py` | 常量值是中文 `.txt` 文件名 | 重命名会改变路由和调用方输入 |
| `prompting/template_manifest.py` | `TemplateSpec.name` 同时是主键和路径，强制 `.txt` | 无法独立演进逻辑身份与存储格式 |
| `prompting/template_store.py` | 文件名用于查 manifest、缓存、加载和 snapshot | 缓存与审计身份随路径变化 |
| `ai/router.py` | 返回 `list[str]` 文件名 | 路由结果携带存储细节 |
| `PromptAssembler` / builders | 静态列表、loader 和 `TemplateContext` 传递文件名 | 文件名扩散到所有组装路径 |
| Stage 1 JSON | 模型必填 `strategy_files_needed` | 模型承担本应由程序负责的存储路由 |
| Pipeline / `AnalysisRecord` | `strategy_files`、`strategy_files_used` | 历史记录在重命名后失去稳定语义 |
| GUI | 显示“注入的 `.txt` 文件” | 展示层与物理格式绑定 |
| 测试与 golden | 大量断言固定 `.txt` 名称和顺序 | 一次重命名会造成高噪声迁移 |

## 3. 目标与非目标

### 3.1 目标

- Prompt 文件可以重命名、移动或迁移为 `.prompt.md`，而不改变路由身份和历史记录语义。
- manifest 成为 `prompt_id -> source_path` 的唯一映射来源。
- 依赖关系、模板版本、缓存、snapshot 和安全日志以 `prompt_id` 为主键。
- 旧 API、旧 Stage 1 输出和旧记录在兼容期继续可读。
- 路由顺序、Prompt 内容、Provider 行为、JSON 校验和 KV-cache 前缀在 M1-M3 保持不变。
- 未知 ID、别名冲突、路径逃逸和未注册模板全部失败关闭。

### 3.2 非目标

- 本轮不改任何 Prompt 正文，不执行 `.txt` 到 `.md` 的批量重命名。
- 本轮不修改 Stage 1/Stage 2 JSON schema、Provider 路由或决策逻辑。
- 本方案不引入多 Agent，也不改变当前两阶段调用次数。
- 不借此删除 `TemplateStore` 旧 loader、`route_strategy_files()` 或旧记录字段。
- 不把任意文件扫描、自动发现或目录 glob 引入 Prompt 加载路径。

## 4. 身份模型

### 4.1 `PromptId`

建议新增 `pa_agent/ai/prompting/prompt_ids.py`：

```python
from typing import NewType

PromptId = NewType("PromptId", str)

PERSONA = PromptId("pa.persona")
BINARY_DECISION = PromptId("pa.binary_decision")
MARKET_DIAGNOSIS = PromptId("pa.market_diagnosis")
```

采用 `NewType` 而不是封闭 `Enum`：

- 静态检查能区分 ID 与普通文件名字符串；
- JSON、日志和记录仍可稳定序列化为字符串；
- 后续新增模板不需要修改中央枚举类或引入插件继承问题。

ID 规则：

- 仅允许小写 ASCII、数字、点和下划线，正则为
  `^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$`。
- ID 不包含后缀、目录、版本号、阶段号或中文显示名称。
- ID 发布后不可复用；模板废弃时保留 tombstone 或兼容别名，不把旧 ID 分配给新语义。
- 内容修订只增加 `TemplateSpec.version`，不更换 ID。
- 模板职责发生不兼容变化时创建新 ID，并显式声明迁移关系。

### 4.2 初始 ID 映射

M1 初始状态下，`legacy_filename` 与表中的 `source_path` 相同；M5 只改变 `source_path`。

| `prompt_id` | 当前 `source_path` | `display_name` |
|---|---|---|
| `pa.persona` | `提示词大纲_人设与思维方式.prompt.md` | 人设与思维方式 |
| `pa.binary_decision` | `二元决策.prompt.md` | 交易二元决策树 |
| `pa.market_diagnosis` | `市场诊断框架.txt` | 市场诊断框架 |
| `pa.kline_signal` | `文件16-K线信号识别.txt` | K 线信号识别 |
| `pa.bar_checklist` | `逐棒分析检查单.txt` | 逐棒分析检查单 |
| `pa.stop_target_position` | `文件17-止损和止盈与仓位管理.txt` | 止损、止盈与仓位约束 |
| `pa.measured_move` | `文件23-MeasuredMove与结构目标.txt` | Measured Move 与结构目标 |
| `pa.channel.bullish.identification` | `上涨通道分析识别.txt` | 上涨通道识别 |
| `pa.channel.bullish.strategy` | `上涨通道交易策略.txt` | 上涨通道策略 |
| `pa.channel.bearish.identification` | `下跌通道分析识别.txt` | 下跌通道识别 |
| `pa.channel.bearish.strategy` | `下跌通道交易策略.txt` | 下跌通道策略 |
| `pa.spike.bullish.identification` | `极速上涨分析识别.txt` | 极速上涨识别 |
| `pa.spike.bullish.strategy` | `极速上涨交易策略.txt` | 极速上涨策略 |
| `pa.spike.bearish.identification` | `极速下跌分析识别.txt` | 极速下跌识别 |
| `pa.spike.bearish.strategy` | `极速下跌交易策略.txt` | 极速下跌策略 |
| `pa.range.identification` | `震荡区间分析识别.txt` | 震荡区间识别 |
| `pa.range.strategy` | `震荡区间交易策略.txt` | 震荡区间策略 |
| `pa.channel.width` | `文件13-窄通道与宽通道策略.txt` | 窄通道与宽通道 |
| `pa.pattern.wedge` | `文件14-楔形形态分析交易.txt` | 楔形 |
| `pa.pattern.second_entry` | `文件15-二次入场机会.txt` | 二次入场 |
| `pa.pattern.breakout_failure` | `文件18-突破失败与突破测试.txt` | 突破失败与突破测试 |
| `pa.pattern.h1_h2_l1_l2` | `文件19-H1H2-L1L2计数.txt` | H1/H2/L1/L2 计数 |
| `pa.context.always_in_20gb` | `文件20-AlwaysIn与20GB.txt` | Always In 与 20GB |
| `pa.context.barbwire` | `文件21-铁丝网与无交易环境.txt` | 铁丝网与无交易环境 |
| `pa.context.failed_signal_magnet` | `文件22-信号失败后的磁力位.txt` | 失败信号与磁力位 |
| `pa.pattern.final_flag` | `文件24-最终旗形与趋势末端.txt` | 最终旗形与趋势末端 |
| `pa.pattern.mtr` | `文件25-主要趋势反转MTR.txt` | 主要趋势反转 MTR |
| `pa.pattern.triangle` | `文件27-三角形与收敛形态.txt` | 三角形与收敛形态 |
| `pa.pattern.double_top_bottom` | `文件28-双重顶底与微型结构.txt` | 双重顶底与微型结构 |

### 4.3 `TemplateSpec`

目标数据结构：

```python
@dataclass(frozen=True, slots=True)
class TemplateSpec:
    prompt_id: PromptId
    source_path: str
    legacy_filename: str
    display_name: str
    stages: tuple[StageName, ...]
    role: TemplateRole
    output_contract: str | None = None
    dependencies: tuple[PromptId, ...] = ()
    legacy_aliases: tuple[str, ...] = ()
    version: str = MANIFEST_VERSION
```

约束：

- `prompt_id`、`source_path`、`legacy_filename` 和所有 `legacy_aliases` 分别唯一。
- `dependencies` 只能引用已注册 ID。
- `source_path` 必须是相对 POSIX 路径，不得包含绝对路径、`..`、空组件或反斜杠。
- 运行时解析后的路径必须仍位于 `PROMPT_DIR` 内。
- 允许的运行时格式仅为 `.txt` 和 `.prompt.md`；普通 `_reference/*.md` 不会因后缀匹配被加载。
- `legacy_filename` 固定为迁移前公开的 `.txt` 名称，供旧 API 和旧记录投影。
- `legacy_aliases` 仅供额外的精确兼容映射；两者都不参与文件系统拼接，也不得包含目录分隔符。

## 5. 目标模块与接口

```text
ai/prompting/
├── prompt_ids.py          # PromptId 类型与稳定 ID 常量
├── template_manifest.py   # ID、路径、显示名、阶段、依赖、版本
├── prompt_catalog.py      # 严格 ID 查询与 legacy 精确映射
├── template_store.py      # ID 核心加载、缓存、渲染和 snapshot
└── compatibility.py       # 文件名 API、旧 loader 和旧记录适配
```

核心 API：

```python
catalog.spec(prompt_id) -> TemplateSpec
catalog.source_path(prompt_id) -> str
catalog.legacy_filename(prompt_id) -> str
catalog.display_name(prompt_id) -> str
catalog.resolve_legacy_filename(filename) -> PromptId

store.load_id(prompt_id, stage=...) -> str
store.load_many_ids(prompt_ids, stage=...) -> tuple[str, ...]
store.render_id(prompt_id, context, stage=...) -> str
store.snapshot_id(prompt_id, stage=...) -> TemplateIdSnapshot
store.snapshots_ids(prompt_ids, stage=...) -> tuple[TemplateIdSnapshot, ...]

route_strategy_prompt_ids(stage1_json) -> list[PromptId]
```

`NewType` 在运行时仍是 `str`，因此禁止让同一个方法猜测参数是 ID 还是文件名。核心路径使用
显式 `*_id` 方法；现有无后缀方法在兼容期只接受 legacy 文件名。

M1 新增的 `TemplateIdSnapshot` 字段：

```text
prompt_id
version
byte_length
sha256
```

`source_path` 可以作为诊断元数据查询，但不得参与 snapshot 身份或 digest 比较。这样只改变物理路径
不会改变历史模板身份。旧 `TemplateSnapshot(name=...)` 在兼容期保持不变，继续用于现有
golden 文件和旧调用方。

兼容 API：

```python
route_strategy_files(stage1_json) -> list[str]
stage1_prompt_txt_files() -> list[str]
stage2_prompt_txt_files(...) -> list[str]
TemplateStore.load(filename, ...)
TemplateStore.load_many(filenames, ...)
TemplateStore.snapshot(filename, ...)
```

兼容 API 必须通过 catalog 投影，不能维护第二份独立文件名常量表。
其中 `route_strategy_files()` 和 `*_txt_files()` 返回 `legacy_filename`，不得返回可变的
`source_path`；只有 `TemplateStore` 可以把 ID 解析为实际存储路径。

## 6. 各边界的目标合同

### 6.1 路由与 Prompt 组装

- `router.py` 的主实现返回有序 `PromptId` 列表。
- `route_strategy_files()` 只作为 `PromptId -> legacy_filename` 的兼容投影。
- `PromptAssembler`、`Stage1PromptBuilder`、`Stage2PromptBuilder` 的新内部列表使用 ID。
- 在 M1-M3，为保持 Prompt 字节不变，写入模型上下文的旧字段仍投影为当前文件名。
- 去重以 ID 为准，禁止同一 ID 因多个 legacy 文件名重复注入。
- Stage 1/Stage 2 的顺序继续由显式 tuple 定义，不按 ID 或路径排序。

### 6.2 模型输出

`prompt_id` 是程序内部身份，不应成为模型推理结果。目标状态是：

1. Stage 1 只输出 `cycle_position`、`direction`、`detected_patterns` 等诊断事实。
2. 程序根据已校验的诊断调用 `route_strategy_prompt_ids()`。
3. `strategy_files_needed` 在 M4 前继续保留，Normalizer 仍可用 router 补全。
4. M4 经独立评估后，从新 schema 中移除 `strategy_files_needed`；旧 schema 和旧记录继续兼容读取。

不建议把 `strategy_files_needed` 简单替换成 `strategy_prompt_ids_needed`，否则只是把“模型拼写文件名”
改成“模型拼写内部 ID”，并没有消除职责错位。

### 6.3 Pipeline 与记录

Pipeline 目标字段：

```text
strategy_prompt_ids: list[PromptId]
```

新记录在兼容期双写：

```json
{
  "strategy_prompt_ids_used": ["pa.channel.bullish.identification"],
  "strategy_files_used": ["上涨通道分析识别.txt"]
}
```

规则：

- 新代码读取记录时优先使用 `strategy_prompt_ids_used`。
- 旧记录只有 `strategy_files_used` 时，通过精确 legacy map 在内存中解析 ID，不回写原文件。
- 未知 legacy 值保留原字符串用于展示，但不得据此访问磁盘；诊断只记录 unresolved 数量。
- M1-M3 的增量 Prompt 仍只渲染旧 `strategy_files_used` 投影，避免新增字段改变 Prompt 字节。
- 最终移除旧字段必须遵循 `compatibility_removal_policy`，不得随 M1-M5 一并删除。

### 6.4 GUI 与可观测性

GUI 默认显示：

```text
市场诊断框架 [pa.market_diagnosis]
```

调试 tooltip 可显示当前相对 `source_path`、版本和摘要前缀，但不得显示完整 Prompt 内容。

日志只允许记录：

- `prompt_id`
- stage / role / version
- 模板数量、字节长度、SHA-256
- legacy 解析成功/失败计数

日志继续禁止记录完整 Prompt、K 线原文、Provider Token 和模板变量值。

## 7. 分阶段迁移

### M0：冻结基线（已完成）

- 固定 29 个模板当前 ID 映射、加载顺序和 UTF-8 digest。
- 保留现有 shared system、Stage 1、Stage 2 standalone、continuation standalone 和
  continuation prefix-chain golden。
- 统计文件名进入模型输出、Pipeline、记录和 GUI 的全部调用点。

**退出门禁**：现有 L2 golden、Prompt 合同测试和 Pipeline 等价测试通过。

### M1：引入 ID 与 Catalog，保持旧调用方（已完成）

- 新增 `prompt_ids.py`、`PromptCatalog` 和带 `prompt_id/source_path` 的 manifest。
- `TemplateSpec.name` 暂时作为只读兼容属性返回 `legacy_filename`。
- `TemplateStore` 增加 `load_id()`、`load_many_ids()` 和 `snapshot_id()`；
  旧 `load()`、`load_many()`、`snapshot()` 委托 compatibility。
- 依赖关系由文件名改为 ID。
- manifest 不再以 `.txt` 后缀定义模板身份。

**退出门禁**：

- 29 个 ID、路径、legacy alias 一一对应且无冲突；
- ID 加载与旧文件名加载内容逐字节相等；
- 所有 Prompt 消息 golden 不变；
- 路径逃逸、未知 ID 和 alias 冲突失败关闭。

**实施结果（2026-07-26）**：

- 新增 `prompt_ids.py` 与 `prompt_catalog.py`，29 个稳定 ID、当前路径、legacy 文件名和显示名
  已进入 manifest；依赖关系已改用 ID。
- `TemplateStore` 已增加 ID 版 load/render/snapshot/cache API；旧文件名 API、`TemplateSpec.name`
  和 legacy `TemplateSnapshot` 保持兼容，并与 ID API 共用按 ID 建立的缓存。
- Catalog 已拒绝非法 ID、不安全路径、非运行时扩展名、非法 legacy 名、重复 ID/路径/alias、
  跨模板路径冲突和未知依赖。
- Prompt/Catalog/Store/Assembler 聚焦单测 93 项通过；L2 compatibility observation 与 router
  property 测试 8 项通过；完整非 live unit 层 1,070 项通过。现有 29 个模板 digest、
  shared system、Stage 1、Stage 2 standalone 和 continuation golden 均未更新。
- Ruff、Ruff format、`py_compile`、CI target 清单、3,724 条 Ruff baseline 和
  `git diff --check` 通过。本地 Black 完成格式化后在当前 Windows 环境的退出阶段挂起；
  最终 Black 权威验收仍由 CI 固定环境执行。

### M2：路由与组装内部切换到 ID

- 新增 `route_strategy_prompt_ids()`，以 ID 完成路由、去重和方向过滤。
- `route_strategy_files()` 通过 `legacy_filename` 生成兼容投影，并保持当前返回值和顺序。
- PromptAssembler 新增 `stage1_prompt_ids()`、`stage2_prompt_ids()`；
  旧 `*_txt_files()` helper 继续返回路径。
- `TemplateContext` 新增 `strategy_prompt_ids` 和以 ID 为键的 `template_versions`；
  旧 `strategy_files` 在兼容层生成。
- 一次只切换 router、shared system、Stage 1、Stage 2 中的一层，每层独立提交。

**M2.1 Router 双入口实施结果（2026-07-26）**：

- `route_strategy_prompt_ids()` 已成为路由逻辑的唯一实现，周期、方向、近期尖峰、备选周期、
  pattern overlay 和 stable dedup 全部在 `PromptId` 上执行。
- `route_strategy_files()`、原私有 filename helper 和 filename 常量继续保留，但全部通过
  `TEMPLATE_CATALOG.legacy_filename(s)` 从 ID 投影，不再维护第二份路由规则。
- 新增 300 组 property 等价验证：ID 路由确定、只返回合法 ID、无重复，且逐项投影后与
  legacy filename 路由完全相等。
- Normalizer、Pipeline RouteStep、现有文件名合同和 Prompt golden 回归通过；本切片未修改
  PromptAssembler、TemplateContext、Prompt 正文、schema、Pipeline state 或 record。

**M2.2 Shared system 与 Stage 1 实施结果（2026-07-26）**：

- PromptAssembler 新增 shared system/Stage 1 ID 元组和 `stage1_prompt_ids()`；原
  `COMMON_SYSTEM_*_TXT_FILES`、`STAGE1_TASK_PROMPT_TXT_FILES` 与
  `stage1_prompt_txt_files()` 均由 Catalog 投影，返回值和顺序不变。
- compatibility 层新增 shared system 与 Stage 1 的原子 ID loader；严格加载失败或显式关闭
  TemplateStore 时，按 ID 查 `legacy_filename` 后整组回退旧 `_load()`。
- `Stage1PromptBuilder` 内部只接收 `PromptId` loader 与 ID tuple；全量、增量和 continuation
  的消息结构及 Prompt 字节保持不变。
- 增加 ID loader 调用批次、强制失败 fallback、ID/filename 列表投影和五轮 compatibility
  observation 证据；M2.2 未切换 Stage 2、TemplateContext、Pipeline state 或 record。
- Prompt/Store/compatibility 聚焦回归 65 项、完整非 live unit 层 1,071 项通过；3,724 条
  Ruff baseline 与全部 Prompt golden 保持不变。

**M2.3 Stage 2 与 TemplateContext 实施结果（2026-07-26）**：

- Stage 2 base、全策略库、方向组和 routed strategy 全部使用 Prompt ID；旧
  `STAGE2_*_TXT_FILES`、`stage2_*_txt_files()` 和 PromptAssembler 公共 `strategy_files`
  参数继续作为 Catalog 兼容投影。
- `Stage2PromptBuilder` 仅接收 ID loader 与 `strategy_prompt_ids`；standalone、continuation
  和 prefix-chain 在进入 builder 前完成 legacy filename 解析。
- TemplateContext 新增权威 `strategy_prompt_ids`，自动双写 `strategy_files`；旧
  `from_stage2_inputs()` 保留，新 `from_stage2_prompt_ids()` 供内部使用，不一致双合同失败关闭。
- Stage 2 ID loader 优先使用 M1 Store protocol；旧注入 Store 自动投影为 filename 后调用
  `load_many()`，warning 文本和整组 fallback 行为不变。
- Prompt 聚焦回归 67 项、完整非 live unit 层 1,073 项、关键两阶段/Pipeline 集成 24 项通过；
  全部 golden、KV 前缀和 3,724 条 Ruff baseline 保持不变。

**退出门禁**：

- 对所有 cycle/direction/pattern fixture，
  `map_ids_to_legacy_filenames(route_strategy_prompt_ids(x)) == route_strategy_files(x)`；
- 新旧 assembler 在五类 golden 上字节完全相等；
- KV-cache 共享 system 前缀 digest 不变；
- Provider、schema、normalizer 和重试行为不变。

### M3：Pipeline、记录与 GUI 双合同

- Pipeline state 和 orchestrator callback 增加 `strategy_prompt_ids`。
- `AnalysisRecord` 增加可选 `strategy_prompt_ids_used`，新记录双写旧文件名字段。
- demo、history、replay、headless 和 GUI 读取器支持新旧记录。
- Prompt 调试界面改为显示名称 + ID；路径只作为次级诊断信息。
- 旧 callback、旧记录字段和 GUI 方法保留兼容适配。

**M3.1 AnalysisRecord 双合同实施结果（2026-07-26）**：

- `AnalysisRecord` 新增默认空列表 `strategy_prompt_ids_used`。现有 Pipeline 和 legacy 路径即使
  仍只传 `strategy_files_used`，已知 legacy filename 也会在模型校验时解析为稳定 ID；序列化
  后的新记录因此同时包含 ID 与不可变 legacy filename。
- ID-only 输入由 Catalog 自动投影 `strategy_files_used`；ID/file 同时存在但不一致、或 ID
  未注册时失败关闭。`model_copy(update=...)` 使用同一同步合同，覆盖现有编排的增量更新路径。
- 旧记录中的未知 legacy filename 原样保留，ID 列表保持为空；读取过程不把该值解释为
  `source_path`，也不回写原文件。demo、history、replay 和 headless 通过共享 schema 获得兼容。
- 新增 8 项记录身份合同测试并纳入 targeted pytest/focused Ruff；记录/兼容聚焦回归 49 项、
  完整非 live unit 层 1,081 项、integration 层 79 项通过，3,724 条 Ruff baseline 保持不变。
- 本切片未修改 Pipeline state、orchestrator callback、GUI、Prompt 正文、模型 JSON schema
  或 golden。M3.2 继续迁移 Pipeline state/route outputs，M3.3 再处理 GUI 展示。

**M3.2 Pipeline state/route outputs 双合同实施结果（2026-07-26）**：

- `PipelineState` 新增权威 `strategy_prompt_ids`；构造器、`set_route_outputs()` 和兼容
  `route_output` setter 同步 `strategy_prompt_ids`/`strategy_files`，ID-only 输入由 Catalog
  投影 legacy filename，ID/file 不一致或未知 ID 时失败关闭。
- 现有 filename router 结果若全部已注册则在 RouteStep 边界解析为 ID；包含未知兼容 filename
  时保留原列表且 ID 为空，不把未知值当作 `source_path`。`route_outputs` 同时暴露两个字段。
- Stage 2 继续使用 legacy filename 投影和原 `on_stage2_files` callback，因此 Prompt 字节与
  GUI/headless 适配器合同不变；Stage 2 snapshot、取消 partial 与 PersistStep 显式把 ID
  传入 `AnalysisRecord`，不再依赖持久化模型被动补全。
- 安全摘要和 route lifecycle 日志只增加 Prompt ID 数量，不记录 ID、filename、Prompt 内容
  或行情。Pipeline import 继续不加载 PyQt6。
- Pipeline 聚焦回归 51 项、全终态/legacy 等价专项 29 项、完整非 live unit 层 1,085 项、
  integration 层 80 项通过；全部 Prompt golden、CI target 和 3,724 条 Ruff baseline 不变。
- 本切片未修改 `two_stage.py`、orchestrator callback、GUI、Prompt 正文或模型 JSON schema。
  M3.3 只处理 GUI 显示名/tooltip，并保留旧 filename callback 兼容入口。

**M3.3 GUI 显示合同实施结果（2026-07-26）**：

- `PromptFilesPanel` 默认显示 `display_name [prompt_id]`，不再把 `.txt` filename 当作用户可见
  身份；tooltip 仅显示稳定 ID、相对 `source_path`、不可变 `legacy_filename` 和 manifest 版本，
  不显示 Prompt 正文。
- 旧 `set_stage1_files()`、`set_stage2_files()`、`set_latest_run()` 和
  `on_stage2_files` callback 保持兼容，由面板通过 Catalog 解析 ID；新增显式 Prompt ID setter，
  为后续调用方提供不依赖 filename 的入口。
- 未知旧 filename 原样显示并标记 `[unresolved]`，不据此访问磁盘；内置 JSON 合同和经验库
  说明改用“非 Prompt 模板”，不再绑定 `.txt` 物理格式。
- 新增 3 项 Qt 面板测试并纳入 targeted pytest/focused Ruff，覆盖 legacy filename 解析、
  ID 直传、显示文本、tooltip 和 unresolved fallback；GUI/headless/demo 专项 11 项、
  完整非 live unit 层 1,088 项、integration 层 80 项通过。
- `prompt_files_panel.py` 纳入 focused Ruff；该文件 12 条已审查的历史中文标点诊断以行级
  `RUF001` 豁免收口，全仓 baseline 从 3,724 降至 3,712，未引入其他诊断漂移。
- 本切片未修改 orchestrator、Prompt 正文、模型 JSON schema、golden 或 KV-cache 前缀。
  M1-M3 字节等价约束保持满足，下一阶段 M4 才允许有意修改模型输出合同。

**退出门禁**：

- 新记录 round-trip 同时保留 ID 与 legacy 投影；
- 旧记录不改盘即可加载、回放和显示；
- legacy/Pipeline 固定终态矩阵的事件、Prompt 和记录业务字段等价；
- 日志与记录脱敏扫描无新增泄漏。

### M4：移除模型对文件名的职责

此阶段会有意改变 Prompt 字节，必须与 M1-M3 分开。

- 新 Stage 1 输出合同不再要求 `strategy_files_needed`。
- router 成为策略模板选择的唯一权威来源。
- Normalizer 继续兼容旧模型输出和旧记录，但忽略其文件名建议作为路由权威。
- Prompt 正文中的 ``*.txt`` 交叉引用改为稳定文档标题，例如 `《市场诊断框架》`；
  不向模型暴露物理路径或要求模型输出 `prompt_id`。
- 更新 schema 版本、golden、使用文档和兼容策略。

**M4.1 Stage 1 schema 与兼容 Normalizer 实施结果（2026-07-26）**：

- Stage 1 schema 新增 `pa-agent.stage1-output.v2` 标识，并从 `required` 与 `properties` 中移除
  `strategy_files_needed`；旧模型仍可携带该额外字段，不会因兼容输入被拒绝。
- Normalizer 同时接受旧 `strategy_files_needed` 与 `recommended_strategy_files`，但只把它们
  视为兼容输入并忽略其内容；输出中的同名兼容字段始终由 `route_strategy_files()` 生成，
  缺少核心诊断字段或 router 异常时保守回退为空列表。
- 新增 schema v2、无 filename 字段校验、旧建议不覆盖 router 和 alias 不越权测试；schema/
  Normalizer/Pipeline 聚焦回归 47 项、属性/Pipeline 专项 32 项、完整非 live unit 层
  1,090 项、integration 层 80 项通过，3,712 条 Ruff baseline 不变。
- 本切片未修改 Prompt 正文、增量合同、Stage 2 carryover、golden 或 Provider 行为。M4.2
  单独移除模型可见字段与物理 filename 交叉引用，并更新预期 Prompt/golden。

**M4.2 Prompt、carryover 与 golden 实施结果（2026-07-27）**：

- 29 个运行时模板正文不再暴露 `.txt` 交叉引用、`strategy_files_needed` 或
  `recommended_strategy_files`；Python 生成的 Stage 1/Stage 2 提醒、特殊形态路由表和
  二元决策引用统一改用稳定显示标题。
- Stage 1 增量上下文、prefix-chain assistant 历史和 Stage 2 compact context 在进入模型前
  剥离程序路由字段；上一轮 `strategy_files_used` 不再进入模型上下文。兼容记录、Pipeline
  状态、router 投影和旧 callback 合同保持不变。
- Prompt manifest 统一升级到 `v2`。29 个 Prompt ID 的版本均更新，实际正文 SHA-256 只在
  预期的 14 个模板发生变化；共享 system、Stage 1、Stage 2 standalone 和 continuation
  golden 已按受控漂移更新。
- 新增运行时模板和组装 Prompt 不泄漏 filename/路由字段的合同断言。Prompt/Normalizer
  聚焦回归 89 项、完整非 live unit 层 1,092 项、integration 层 80 项、property 层 55 项
  通过；CI 目标清单、`py_compile`、focused Ruff、Black 24.10.0 受影响目标、
  3,712 条 Ruff baseline 和差异检查通过。
- 本切片不包含真实 Provider 调用，也不据固定 golden 推断模型质量。M4.3 必须独立比较
  校验失败率、重试率、Token 和语义冲突率，并按 L6 runbook 留存脱敏观察证据。

**M4.3a 离线合同评估结果（2026-07-27）**：

- 新增 `pa-agent.prompt-contract-evaluation.v1` 评估器和 M3.3 聚合基线，以固定 fixture
  比较 Stage 1、Stage 2 standalone、continuation standalone 和 prefix-chain；报告只保存
  消息计数、字节/字符数、估算 token、SHA-256 和聚合合同指标。
- 4 个合成路由合同案例中，M3.3 与 M4.2 的 schema 校验失败和重试均为 0；Normalizer 后的
  路由冲突由 2/4 降为 0/4。四种 Prompt 合计估算 token 由 309,649 降为 309,642；
  单项最大上浮 10 tokens（约 0.0089%），低于 0.1% 门禁。
- 离线门禁通过，但当前进程缺少 `PA_AGENT_LIVE_API_KEY`。报告明确记录
  `blocked_missing_session_api_key`、`evidence_collected=false` 和
  `m4_exit_gate_passed=false`；不得据此宣称 M4 完成。
- 评估器单测 5 项、完整非 live unit 层 1,097 项、integration 层 80 项、property 层
  55 项通过；CI 清单自检、focused Ruff/Black、3,712 条 Ruff baseline 和差异检查通过。
- M3.3 token 基线固定使用 `tiktoken 0.12.0`；`pyproject.toml` 精确固定同一版本，并由
  依赖/基线一致性单测保护。升级 tokenizer 必须重建 M3 基线和 M4 报告，不能把不同版本的
  token 指标直接比较。
- 复用 2026-07-23/24 三组真实 legacy/Pipeline pair 建立 6 条 M3-compatible 聚合基线：
  6/6 完成、0 次终局校验失败、0 次验证重试；模型 6/6 输出 Prompt filename，且 6/6 与
  router 冲突。基线只保存 usage 聚合和 fixture/provider 合同哈希。
- 新增 live 聚合器与 comparator；M4 候选必须至少包含一条 legacy 和一条 Pipeline 记录，
  使用相同合同哈希，并满足校验失败/重试不回退和平均输入 token 增幅不超过 10%。
- live 聚合/比较单测 9 项、完整非 live unit 层 1,106 项、integration 层 80 项、property
  层 55 项通过；CI 清单、focused Ruff/Black、3,712 条 Ruff baseline 和报告重生成检查通过。
- 评估口径、限制与复现命令见
  [`prompt_contract_m4_evaluation.md`](./prompt_contract_m4_evaluation.md)，机器可读证据见
  [`evaluations/prompt_contract_m4_2026-07-27.json`](./evaluations/prompt_contract_m4_2026-07-27.json)。

**M4.3b 真实 Provider 退出结果（2026-07-29）**：

- 在干净 `main@8b62b29` detached worktree 中，使用与 M3-compatible 基线相同的
  Provider/fixture 合同分别执行一次 legacy 与 Pipeline；两条路径均完成 5 事件、调用
  Provider、写入 record，单体 artifact 均为 `valid=true`。
- 候选终局校验失败和验证重试均为 0/2；模型 Prompt identity 输出与 router 语义冲突均由
  基线 6/6 降至候选 0/2。
- 平均输入 token 由 110,240.33 降至 109,392.50，减少 847.83（约 0.769%）；Provider 与
  fixture 合同哈希一致，10% token 门禁通过。
- comparator 的 11 项 gate 全部通过。最终评估器重新计算 comparison、校验候选/比较
  SHA-256，并生成 `m4_exit_gate_passed=true` 的最终报告。
- 原始 summary/event/record 留在 Git 忽略目录；仓库只保存 aggregate-only 候选、比较和
  退出报告。M4 退出条件已满足，可进入独立的 M5 物理路径迁移。

**退出门禁**：

- Stage 1/Stage 2 schema、normalizer、retry 和路由测试通过；
- 固定 fixture 下除预期字段/文案外无非预期 Prompt 漂移；
- 校验失败率、重试率、Token 和语义冲突率不劣于 M3 基线；
- 真实 Provider 观察按 L6 runbook 完成，产物脱敏检查通过。

### M5：可选 `.prompt.md` 存储迁移

- M5.0 先消除剩余物理路径耦合：legacy filename 只能经 Catalog 解析当前 `source_path`，
  默认决策树通过 `pa.binary_decision` 加载；不得依赖磁盘上存在同名 `.txt` 实体。
- 使用 `git mv` 分批把运行时模板改为 `.prompt.md`。
- 每批只修改 manifest 的 `source_path`，`prompt_id`、版本、路由和记录身份不变。
- 旧 `.txt` 名称继续作为 `legacy_filename`，但不得保留重复实体文件。
- `_reference/*.md` 继续是参考层，不进入运行时 manifest。

**M5.0 Source Path 准备结果（2026-07-29）**：

- 诊断 `PA-M5-SOURCE-PATH-001` 确认 assembler fallback 和默认 decision tree 仍直接读取
  legacy `.txt` 物理路径，直接执行 M5 会破坏显式回滚与 GUI 决策树。
- `PromptCatalog.source_path_for_legacy_filename()` 已成为兼容名称到当前物理路径的唯一投影；
  `PromptAssembler._load()` 保留 legacy 输入/缓存合同但通过该投影读取。
- 默认 `load_decision_tree()` 已改用 `TemplateStore.load_id(pa.binary_decision)`；显式 `path`
  入口和返回的 legacy `source` 保持兼容。
- 新增迁移态回归：只有 `.prompt.md` 实体时 legacy API 仍可读取；测试 fixture 和实体存在性
  检查均按 manifest `source_path` 执行。
- 本切片未移动 Prompt 文件。29 个 ID、legacy filename、正文、manifest v2 和组装合同不变；
  第一批 `git mv` 必须在本切片独立提交并通过 CI 后开始。

**M5.1 Persona 单模板迁移结果（2026-07-29）**：

- 首批只迁移无模板依赖的 `pa.persona`，使用 `git mv` 将物理路径改为
  `提示词大纲_人设与思维方式.prompt.md`；manifest 只修改对应 `source_path`。
- 稳定 ID 仍为 `pa.persona`，不可变 `legacy_filename` 仍为
  `提示词大纲_人设与思维方式.txt`；新实体存在且旧 `.txt` 实体不存在。
- 原始文件保持 5,702 bytes /
  `6a8b31bf6686a086092dfbe00b8a772aca5d8159ac39c74b1e3e983214553fb0`；
  `TemplateStore` 正文保持 5,604 bytes /
  `1bb0b0ccc326ef6170624dc8d64f1dc0509abaa4f14538c14153c4b5b14f853b`。
- Stage 1、Stage 2 standalone、continuation standalone 和 continuation prefix 的组装摘要
  与迁移前冻结值逐项相同；M4 candidate Prompt metrics 也逐对象相等。
- 批次诊断为
  [`PA-M5-PERSONA-001`](./diagnostics/prompt_m5_persona_migration_2026-07-29.md)；
  实现提交 `fe119af` 与 GitHub Actions run `30474245087` 的 Python 3.11/3.12 双矩阵
  已通过，M5.1 已收口。

**M5.2 Binary Decision 单模板迁移结果（2026-07-29）**：

- 高耦合共享系统模板 `pa.binary_decision` 单独使用 `git mv` 迁移为
  `二元决策.prompt.md`；manifest 只修改 `source_path`，legacy filename 仍为
  `二元决策.txt`。
- raw 正文保持 43,260 bytes /
  `7a67b6bee0425279fbdad1880f265c1feb796897418792f667a19d5c537c9c13`；
  `TemplateStore` 正文保持 42,164 bytes /
  `723111253fa41d732e123943ab12dc94e2c459988978f2fad807699ff704525c`。
- 四种 assembled Prompt digest、M4 最终报告和决策树 14 sections / 54 nodes /
  `cb9b2f7982126bc4995394a8dc81067b0b5d2119a70c36f74aad3a47fb017c91`
  解析摘要逐项不变。
- 批次诊断为
  [`PA-M5-BINARY-001`](./diagnostics/prompt_m5_binary_decision_migration_2026-07-29.md)；
  实现提交 `980c294` 与 GitHub Actions run `30490054789` 的 Python 3.11/3.12 双矩阵
  已通过，M5.2 已收口。

**退出门禁**：

- 文件移动前后每个 ID 的内容 SHA-256 不变；
- 所有 assembled Prompt digest 不变；
- 旧记录和 legacy API 仍能通过 alias 解析；
- 确认 Markdown lint/预览收益后，再决定是否继续迁移剩余文件。

## 8. 兼容矩阵

| 输入 | M1-M3 行为 | M4+ 目标行为 |
|---|---|---|
| 新 `PromptId` | 核心路径直接接受 | 唯一核心输入 |
| 当前 `.txt` 文件名 | compatibility 精确映射 | 仅旧 API/旧记录接受 |
| 已重命名的 legacy 文件名 | manifest alias 精确映射 | 同左，禁止磁盘直读 |
| 未知 ID | 抛出明确错误 | 同左 |
| 未知旧文件名 | 不加载，记录 unresolved 数量 | 同左 |
| Stage 1 `strategy_files_needed` | 保留并归一化，router 仍为运行时权威 | 新 schema 不再要求，旧 schema 可读 |
| 旧 `strategy_files_used` 记录 | 内存映射为 ID | 继续兼容至移除政策满足 |

## 9. 测试与验收

### 9.1 Catalog 与安全

- 29 个 ID 唯一、格式合法、路径唯一、显示名非空。
- dependencies 全部引用有效 ID。
- `legacy_filename` 与 legacy alias 全局唯一，不与其他模板 ID 或兼容名称冲突。
- 拒绝绝对路径、`..`、反斜杠逃逸、普通未注册 `.md` 和未知 ID。
- manifest import 保持 PyQt-free。

### 9.2 路由与 Prompt 等价

- ID 路由映射为 `legacy_filename` 后与现有文件路由逐项、逐序相等。
- bullish/bearish 排除、full library、pattern overlays 和 stable dedup 行为不变。
- shared system、Stage 1 full/incremental/continuation、Stage 2 standalone/prefix-chain
  均做 SHA-256 或完整消息相等比较。
- M1-M3 不更新 golden digest；若 digest 变化则迁移失败。
- M4.2 只更新已审计的 manifest v2 和预期 Prompt 漂移；模板正文摘要变化必须与修改清单
  一一对应。

### 9.3 记录与 Pipeline

- 新/旧记录字段 round-trip 和旧 fixture 读取。
- legacy/Pipeline 的 route output、事件、终态和持久化边界等价。
- GUI/headless 使用相同 ID 列表，显示层不影响运行时路由。
- 未知 legacy 名称不会触发文件系统读取。

### 9.4 建议聚焦命令

```powershell
pytest -q tests/unit/test_template_store.py
pytest -q tests/unit/test_strategy_files.py tests/unit/test_prompt_txt_files.py
pytest -q tests/unit/test_template_context.py tests/unit/test_prompt_assembler.py
pytest -q tests/property/test_router_determinism.py
pytest -q tests/unit/test_pipeline.py tests/integration/test_route_pipeline_step.py
pytest -q tests/integration/test_two_stage_pipeline_equivalence.py
ruff check pa_agent/ai/prompting pa_agent/ai/router.py pa_agent/ai/prompt_assembler.py
```

M4 另需按 `docs/live_observation_runbook.md` 执行真实 Provider 对照；M1-M3 若全部 Prompt
digest 不变，不要求用 live 调用替代确定性等价证据。

## 10. 原子实施切片

1. **Catalog 基础**：`PromptId`、29 个 manifest 映射、验证器和 catalog 单测。
2. **Store 双入口**：按 ID 加载/snapshot，旧文件名适配，Prompt golden 不变。
3. **Router 双入口**：ID 路由为主，filename wrapper 等价，属性测试不变。
4. **Assembler 内部 ID**：shared system、Stage 1、Stage 2 分层切换，每层独立提交。
5. **Pipeline/Record 双写**：新增 ID 字段、旧记录回读和 GUI 展示。
6. **模型合同清理**：单独修改 Stage 1 schema/Prompt，执行离线和真实观察。
7. **可选后缀迁移**：按模板组 `git mv`，只改变 `source_path`。

每个切片必须同步 `docs/CHANGELOG.md`、`AGENTS.md` 和本方案状态；不得把 Prompt 文本优化、
多 Agent、经验库权重调整或无关重构混入同一提交。

## 11. 回滚与停止条件

- M1-M3 任一 Prompt digest 变化：立即停止，不更新 golden，不进入下一层。
- ID 路由映射为 legacy 文件名后与旧路由不一致：保留旧 router 为运行时权威，修复映射后重试。
- 旧记录无法无损读取：停止 M3，不启用新记录写入。
- M4 校验失败率、重试率、Token、p95 延迟或语义冲突显著回退：恢复 M3 输出合同。
- M5 内容 digest 变化：撤销该批路径迁移，确认换行符、编码和编辑器格式化设置。

不新增用户可见 feature flag 作为 M1 的前提：M1 是纯增量 catalog。M2-M3 通过兼容入口和
逐层原子提交回滚；只有实际实现无法维持字节等价时，才评估增加临时内部 rollout flag，
避免把永久配置债务暴露给用户。

## 12. 完成定义

只有同时满足以下条件，才算完成“Prompt ID 与文件名解耦”：

- 核心路由、组装、Pipeline 和新记录均使用 `PromptId`。
- manifest 是 ID 到物理路径的唯一映射来源。
- 模型不负责输出文件名或 Prompt ID。
- 修改某个 `source_path` 不需要修改 router、schema、历史记录或 GUI 业务逻辑。
- 旧 API 和旧记录在兼容期可用，且移除计划受兼容政策约束。
- M1-M3 有字节等价证据，M4 有合同评估证据，M5 有内容摘要不变证据。
