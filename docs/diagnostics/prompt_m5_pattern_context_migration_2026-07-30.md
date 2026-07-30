# M5 Pattern/Context 模板迁移诊断报告

> 诊断 ID：`PA-M5-PATTERN-CONTEXT-001`
>
> 日期：2026-07-30
>
> 状态：M5.5 实现与本地全部质量门禁已完成；远端验收待执行

## 目标

M5.4 已迁移 router 的 channel/spike/range 语义对。M5.5 迁移最后 12 个独立
pattern/context 模板，完成 29 个运行时模板的 `.prompt.md` 物理存储迁移。该批必须保持
正文、Prompt 身份、兼容文件名、路由顺序和组装结果不变。

## 变更

本批使用 `git mv` 迁移以下模板：

- `pa.channel.width`；
- `pa.pattern.wedge`；
- `pa.pattern.second_entry`；
- `pa.pattern.breakout_failure`；
- `pa.pattern.h1_h2_l1_l2`；
- `pa.context.always_in_20gb`；
- `pa.context.barbwire`；
- `pa.context.failed_signal_magnet`；
- `pa.pattern.final_flag`；
- `pa.pattern.mtr`；
- `pa.pattern.triangle`；
- `pa.pattern.double_top_bottom`。

manifest 只更新对应 `source_path`。稳定 Prompt ID、不可变 `.txt` `legacy_filename`、
manifest `v2`、阶段、角色和输出合同保持不变；不保留重复 `.txt` 实体。迁移合同参数表现
覆盖全部 29 个运行时模板。

## 正文证据

文件移动前后摘要逐项相同：

| Prompt ID | raw bytes / SHA-256 | `TemplateStore` bytes / SHA-256 |
|---|---|---|
| `pa.channel.width` | 15,377 / `2f6749282417fd548b473f6b7224e2fc2b6aa06bce3a602b916dfe20d17f020d` | 15,103 / `1f0369c6cc7a7ee7472d8099a71d5fe330887f952b4123d66b688cf748eed608` |
| `pa.pattern.wedge` | 16,925 / `eb81069cb658f1a52cf1afd8d190876bfd3e863bfc54b822dd533c3fbc59f05f` | 16,596 / `739a7cfb6ae95b8b23180a68d67fae8f8c7e918488217805d350a556849db1fe` |
| `pa.pattern.second_entry` | 14,220 / `de1dae65f664e800349243501bb33b039e6869ae67f1fbf93e39af824cc95808` | 13,946 / `e4768f3c7cfe2c9895111cae5f18813b5516eee9d963b04bcefe45d2b9b7a43f` |
| `pa.pattern.breakout_failure` | 4,826 / `f6a3c2da464e7e91a7c33024c51bde344a634b2bc75ea0f1ae8a5c9d861df5af` | 4,705 / `77a233d15d9a3bd3154fcfaa9694c043cd11b1221012c57fedc7ed07b2930d72` |
| `pa.pattern.h1_h2_l1_l2` | 3,386 / `7bcbdbb0aa7887e427e2c20767682168253c2d74e46089275d7f3363186a0e84` | 3,288 / `a56eb7cebc929cdbca8ad529f410f03fb3efb59c4cdf6bd9af592f0d78e52f57` |
| `pa.context.always_in_20gb` | 3,788 / `172d959885eb64b8c324c0ff82483d73ef3590213971de61ec08090553263888` | 3,690 / `04654e63a90917664e62094f480ae1bfaeffd2e693249ad75d27a433c0cef683` |
| `pa.context.barbwire` | 4,298 / `dd71ef49094a2f0953499464a8add59322b5383d71195647537e3a9029f5b1ab` | 4,204 / `344e69a655f7a29bba121ce0cdd864310acbbcfb1012e9e16ae4dbb99b5ee984` |
| `pa.context.failed_signal_magnet` | 3,003 / `fbfd72ba94e47d74729665cd2f3c798e6842700dd625226b2f0d64681c0abfc3` | 2,916 / `561e029dd934e2c8fdbae83df40b962c82c3c65c1e5c7e981a3a1717bf46e773` |
| `pa.pattern.final_flag` | 4,191 / `75f15b43ebbb7949d4df4fbb06b130a5c3e3a0e3dcc9088bc09cb76e3fc100d2` | 4,105 / `8d081612af686239d22a706833b0bf0a999687c8223cb88917ae599df4592c23` |
| `pa.pattern.mtr` | 4,411 / `5ebdb545a8b27f3c9ecb223f46dfb2876377f93fb3bb6e487d7b4b4181e723b4` | 4,323 / `fb63ae3c5820ee04458f28644a64e5acdf978bf6f69b66b0da103990553a09cf` |
| `pa.pattern.triangle` | 3,230 / `3ae92ce573aa31724b4f05fd534edb25b065c5e43e048d1585db6dff42d986a6` | 3,151 / `0c77d80007ece9a2512ef3b0a3f289c8e496019f697539391309c6dde1c2eca7` |
| `pa.pattern.double_top_bottom` | 2,459 / `3c324e884fb7b61dd2cd089bccf362ed1b9cc67c62fa2090b495df0f0e4541bb` | 2,401 / `6047bac659692aace621d476abe5d172c5336124a5efa6eab7d82950efe7306a` |

排除预期 `source_path` 变化后的内容身份摘要在迁移前后均为
`7614a9be9435c4015b2c83639ce490ded746e244e7890634f310f45b3a717525`。

## 路由与组装合同

10 组规范化路由用例覆盖全部 12 个 Prompt ID。Prompt ID 与 legacy filename 的有序路由
摘要在迁移前后均为
`3c42df2872e5d8f5522c0eb5d09c20640090a0a526d47bbe3e83d30ed2898b70`。
固定 25 根 K 线 fixture 的 Stage 2 组装摘要为：

| 用例 | Stage 2 SHA-256 |
|---|---|
| channel context | `de7f5542cccc4ba1cd47964f0fd2b36a4cd249a7c637a431a406687b24e4a1cf` |
| wedge | `27e6f684e9d1928af9c344b7ac6555f43f70e72a18ab5a3fa9f4fb2384f87683` |
| breakout failure | `25017bffe7cdf6ff979da52546aa4d5f296feee4347c90446f4dd21a79ff1fcf` |
| always in | `df4b1a52e6b0344df5fad6fb69b2593a2fe920907eaa498cf6fd7a552c20b428` |
| barbwire | `b59f1296cb070be8a9e9c156d1e03a88c955606b5a49e6787f311cc6dd843344` |
| magnet | `f479eb61e4b322b7fd9d280be325cca9bb8c564657f6a36b15b015582722c3a8` |
| final flag | `20178725a3cc564962e75a5cb945aa6b74e8d6798bbfccc23ef457aa43044677` |
| MTR | `92212359ecb07dc6e9e25793e70f467020443c12324fc56b1df8496f34976cb3` |
| triangle | `91cec6022a2a29326f28afa7f178edcd32f800b58489205c9f3a32f77afd3dc0` |
| double top/bottom | `69696ebd58277b5508e463c4feb6162c6c231ebf1174535dd7a70566c7ee64d6` |

10 组组装合同摘要在迁移前后均为
`155063ffed987bab45bdc641b89556e8f1e876f13ec1d3b2d5f102dda1475e26`；
路由与组装总合同摘要均为
`0a0e16c00cf6e5b00bd0f948c3598115bb37d0b9f69c5421d2b4f9f5dfd9c17f`。

M4 最终退出报告 SHA-256 保持
`ce8b9555c8b947cce70046f415e3715f7db09d8f759eb4db808d440cc0e2c79a`，
`offline_gate_passed`、`live_gate_passed` 和 `m4_exit_gate_passed` 均为 `true`。

## 验证

- Prompt Catalog、Store、Assembler、router、记录与迁移合同聚焦回归 144 项通过。
- `prompt_engineering/` 中有 29 个 `.prompt.md`、0 个 `.txt`，总数仍为 29。
- 正文身份、10 组路由、10 组 Stage 2 组装和 M4 最终退出报告均与迁移前证据一致。
- CI targeted 177 个目标全部通过，coverage 56.83%。
- 完整 `not e2e and not live` 回归通过。
- Ruff 0.15.13 baseline 精确保持 3,712 条批准诊断。
- 293 个 focused Ruff 目标与展开后的 363 个 focused Black 文件通过。
- CI 清单自检、兼容政策、`py_compile` 和 `git diff --check` 通过。

## 后续

实现提交推送并通过 GitHub Actions Python 3.11/3.12 双矩阵后，M5.5 方可收口。随后执行
29/29 模板的最终完成审计，再评估语义审查 Agent；不得在该审计前混入 Prompt 正文优化或
多 Agent 实现。
