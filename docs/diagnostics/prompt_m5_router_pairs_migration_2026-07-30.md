# M5 Router 语义对模板迁移诊断报告

> 诊断 ID：`PA-M5-ROUTER-PAIRS-001`
>
> 日期：2026-07-30
>
> 状态：M5.4 本地全部质量门禁与远端验收均已完成

## 目标

M5.3 已迁移 Stage 1/Base 模板。M5.4 继续按 router 运行边界迁移五组
channel/spike/range 识别与策略语义对，共 10 个 Stage 2 strategy 模板。该批必须同时保持
物理内容、Prompt 身份、依赖关系、兼容文件名、路由顺序和组装结果不变。

## 变更

本批使用 `git mv` 将以下物理文件迁移为同名 `.prompt.md`：

- `pa.channel.bullish.identification` / `pa.channel.bullish.strategy`；
- `pa.channel.bearish.identification` / `pa.channel.bearish.strategy`；
- `pa.spike.bullish.identification` / `pa.spike.bullish.strategy`；
- `pa.spike.bearish.identification` / `pa.spike.bearish.strategy`；
- `pa.range.identification` / `pa.range.strategy`。

manifest 只更新对应 `source_path`。稳定 Prompt ID、不可变 `.txt` `legacy_filename`、
manifest `v2`、阶段、角色、输出合同和识别模板到策略模板的依赖保持不变；不保留重复
`.txt` 实体。迁移合同参数表从 7 个扩展到 17 个已迁移模板。

## 正文证据

文件移动前后摘要逐项相同：

| Prompt ID | raw bytes / SHA-256 | `TemplateStore` bytes / SHA-256 |
|---|---|---|
| `pa.channel.bullish.identification` | 15,822 / `532cf24d78d0c24f1e6cf25f409ebffdab33b2ca88478486d1d319822387092b` | 15,549 / `6693c26cb41280c70173812486e7260b7dbc9041419b797e9fe9c71bd13e6017` |
| `pa.channel.bullish.strategy` | 12,944 / `a28e2cc98ed9d29c1a76313b9d0d0690d9cffb58e1b2122a40335c54f677dfed` | 12,658 / `c3e8820eee43ca94b62397fb4849696aa9879e305cc0859a1ef2bb854dd7432c` |
| `pa.channel.bearish.identification` | 16,895 / `7e3a885f431f018f3ea1a375248e7363b4a060701746141d7a2e9de465e7b5c3` | 16,597 / `99af681990d1f2f67a073ae7dac35299bc0797c24ee3984004a1f72796ba11aa` |
| `pa.channel.bearish.strategy` | 14,951 / `c8bdf5328d2182a605e8e889305c1b35cc2b1c56935bc82f370a1417a7f17c73` | 14,629 / `a4f3b7aaae7384cb2b37f1a31934bd2d86b0c93cdc44773189f3e1e2e505b043` |
| `pa.spike.bullish.identification` | 20,072 / `76147c2b58e5a084cc55df48d7b80c1fff0e487ccb22da415c3530fb5c182810` | 19,750 / `31aa1db7cd0e44e439708d43591779806197437c04d08a892036af7d22dadb5a` |
| `pa.spike.bullish.strategy` | 7,691 / `443dd8fc0c68e84e7c8b577b0c5359220a25fb7e7b9d8d89f67050b54b929a22` | 7,519 / `ad01f837949956ab22224e6b46bd7834d4b2fe5479c36ffb623e04fab5606e7b` |
| `pa.spike.bearish.identification` | 20,709 / `1827f6bd7de0a60000b78bc92d7d1e5ea08f9b0fdc63c36e9cde616abcb74474` | 20,372 / `1e9d95177c9c0490f0308a9ae5e949a8413b3288ce8c6f729d69074d9bc12ee5` |
| `pa.spike.bearish.strategy` | 7,451 / `821666c5c00a8ae0a2505ce9db1cab5cb26213d624da43cda19df962da018e12` | 7,293 / `ab982e20c0f0086887832b539e6af4c344b71526f26fb801111b2c187b107b5b` |
| `pa.range.identification` | 17,666 / `c3ee637a218f47c75cc1f6faa9ffb74ccb21158c8fd07286fe9c66100f066402` | 17,342 / `8906b083b9390d0f00dc61139182a8684bc2586792cec38d34f275e7e01c2a59` |
| `pa.range.strategy` | 17,025 / `d5cd113227d86814405171f5aee1723f3d07ef9bf7fa1528ef1fc7ab7bcaaac2` | 16,718 / `0b6d3db3e282559243a238c3bc9bafc20d0f4bad3ebc61ab9e3efcfab3dde58b` |

排除预期 `source_path` 变化后的 10 模板内容身份摘要在迁移前后均为
`79fe25f78598b7bb49a12430af9874ac3eb5eced8d6b29771e70165eebd0a711`。

## 路由与组装合同

基线使用规范化 `cycle_position`，不使用模型可见中文标签：

| 用例 | `cycle_position` / `direction` | 语义对 |
|---|---|---|
| bullish channel | `normal_channel` / `bullish` | bullish channel |
| bearish channel | `normal_channel` / `bearish` | bearish channel |
| bullish spike | `spike` / `bullish` | bullish spike |
| bearish spike | `spike` / `bearish` | bearish spike |
| range | `trading_range` / `neutral` | range |

五组 Prompt ID 与 legacy filename 的有序路由摘要在迁移前后均为
`17d0a7376303f2f631f70a98f6ec042446e233f09a120c05af5f2abf94c5f941`。
固定 25 根 K 线 fixture 的五组 Stage 2 组装摘要为：

| 用例 | Stage 2 SHA-256 |
|---|---|
| bullish channel | `de7f5542cccc4ba1cd47964f0fd2b36a4cd249a7c637a431a406687b24e4a1cf` |
| bearish channel | `f9b303ee377a53c2222afcfed6a33e14cfbd963010609fcc4f3b62dcb2d9a41c` |
| bullish spike | `343a062af665a1911e726ae1d316666f57f6972d20fa2d9bc6ce2c161f220e43` |
| bearish spike | `65245aafb4c7a157b3a75ea5ed7cb3c784199e7f21516997ff41ddf741b8d897` |
| range | `96d719a774bb5f916b103280626f7f87668a9b1a9f87ebac8997e931aae7b53e` |

五组组装合同摘要在迁移前后均为
`76abfc50d1735f1c55ef4e42f0546539d7e5bfa6f15d662d962a4fe88547db95`；
路由与组装总合同摘要均为
`09388ffc1ff3108812df046a9db25d0b526ee8116009860a11d0e5405aa96fda`。

M4 最终退出报告 SHA-256 保持
`ce8b9555c8b947cce70046f415e3715f7db09d8f759eb4db808d440cc0e2c79a`，
`offline_gate_passed`、`live_gate_passed` 和 `m4_exit_gate_passed` 均为 `true`。

## 验证

- Prompt Catalog、Store、Assembler、router、记录与迁移合同聚焦回归 132 项通过。
- 10 个新 `.prompt.md` 实体存在，对应旧 `.txt` 实体均不存在。
- 正文身份、五组路由、五组 Stage 2 组装和 M4 最终退出报告均与迁移前证据一致。
- CI targeted 177 个目标全部通过，coverage 56.83%。
- 完整 `not e2e and not live` 回归通过。
- Ruff 0.15.13 baseline 精确保持 3,712 条批准诊断。
- 293 个 focused Ruff 目标与展开后的 363 个 focused Black 文件通过。
- CI 清单自检、兼容政策、`py_compile` 和 `git diff --check` 通过。
- 实现提交：`47d0b76`。
- GitHub Actions run `30507318293`：
  - Windows/Python 3.11 job `90759786082` 为 `success`；
  - Windows/Python 3.12 job `90759786120` 为 `success`。

## 后续

M5.4 已收口。剩余 12 个独立 pattern/context 模板继续按小批次迁移。
