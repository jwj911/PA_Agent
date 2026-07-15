"""Program pre-fill hint renderer for the Stage 1 user prompt (M1 fourth-plus cut).

Extracted from :class:`pa_agent.ai.prompt_assembler.PromptAssembler` per report
§5.2 M1 (the fifth cut).  This module renders the compact block that surfaces the
deterministic engine's §1.1 / §2.3 / §2.4 verdicts *inside the Stage 1 user prompt*
so the AI can see exactly what the program computed before making its own judgement
(and optionally override via ``node_overrides``).

PyQt6-free leaf: module-level imports are limited to ``logging`` + ``typing``.
``KlineFrame`` is annotation-only and kept under ``TYPE_CHECKING``.  The sole
project touch points — the deterministic judges (``judge_data_sufficiency`` /
``judge_direction`` / ``judge_always_in`` from ``decision_nodes``) and the trend
summary helpers (``build_trend_context`` / ``render_three_window_summary`` from
``trend_context``) — keep their original **in-function call-time imports** (which
also breaks the ``prompt_assembler`` ↔ ``decision_nodes``/``trend_context`` cycle),
so this module can be imported standalone.

``render_program_prefill_hint`` was originally ``PromptAssembler``'s
``@staticmethod _render_program_prefill_hint``; after moving it here (dropping the
leading underscore and the ``@staticmethod`` decorator) ``prompt_assembler.py``
re-binds it in the class body as
``_render_program_prefill_hint = staticmethod(render_program_prefill_hint)`` so the
existing ``self._render_program_prefill_hint(...)`` call sites stay byte-for-byte
compatible.  The block header / Chinese hint strings / §2.2 background-vs-recent
summary / override-gate wording must stay byte-identical (the Stage 1 prefix is
KV-cache sensitive and the AI aligns to this block's exact shape).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pa_agent.data.base import KlineFrame

logger = logging.getLogger(__name__)


def render_program_prefill_hint(frame: KlineFrame) -> str:
    """Render a compact block showing program pre-computed node verdicts.

    This is injected into the Stage 1 user prompt so the AI can see
    exactly what the deterministic engine computed for §1.1 / §2.3 / §2.4
    *before* making its own judgement.  The AI can still override via
    node_overrides when it sees structural evidence the program missed.

    Why this matters (from prompt_engineering 二元决策.txt §2.3/§2.4):
    - §2.3 direction is now a 5-signal vote; each signal value is exposed
      so the AI knows which signals contributed and why.
    - §2.4 Always In now has 3 gates (ratio, slope, swing+pullback); the
      AI can see whether Gate 3 confirmed or was weak.
    """
    try:
        from pa_agent.ai.decision_nodes import (
            judge_data_sufficiency,
            judge_direction,
            judge_always_in,
        )
        from pa_agent.ai.trend_context import (
            build_trend_context,
            render_three_window_summary,
        )

        hint_lines: list[str] = [
            "## 程序预填充节点判断依据（§1.1 / §2.3 / §2.4，供 AI 参考）",
            "",
            "程序已确定性计算以下节点，结果将写入 gate_trace。"
            "你可以在理解以下依据后，于 node_overrides 中提交有充分理由的覆盖。",
            "",
        ]

        # §1.1
        fill_11 = judge_data_sufficiency(frame)
        hint_lines.append(f"**§1.1 数据是否足够** → {fill_11.answer}")
        hint_lines.append(f"  依据：{fill_11.reason}")
        hint_lines.append("")

        # §2.3
        direction, fill_23 = judge_direction(frame)
        trend_ctx = build_trend_context(frame, direction)
        n_bars_hint = len(frame.bars)
        hint_lines.append(render_three_window_summary(frame, trend_ctx))
        hint_lines.append("")
        hint_lines.append(
            "**§2.2 长程背景 vs 近期方向（程序摘要，供 gate_trace 2.2 引用）**"
        )
        hint_lines.append(
            f"  背景方向（K{n_bars_hint}-K41）≈ {trend_ctx['background_direction']}；"
            f"交易主方向（近期）≈ {trend_ctx['trading_direction']}；"
            f"关系={trend_ctx['relationship']}"
            + ("；**冲突时不否决近期、不自动减半仓位**" if trend_ctx.get("conflict") else "")
        )
        hint_lines.append("")

        hint_lines.append(
            f"**§2.3 当前方向（多/空/中性）** → {fill_23.answer}"
            + (f"（branch={fill_23.branch}）" if fill_23.branch else "")
        )
        hint_lines.append(f"  依据：{fill_23.reason}")
        hint_lines.append("")

        # §2.4
        fill_24 = judge_always_in(frame)
        hint_lines.append(
            f"**§2.4 是否 Always In** → {fill_24.answer}"
            + (f"（branch={fill_24.branch}）" if fill_24.branch else "")
        )
        hint_lines.append(f"  依据：{fill_24.reason}")
        hint_lines.append("")

        hint_lines.append(
            "⚠️ §1.1 为锁定节点不可覆盖。§2.3/§2.4 可通过 node_overrides 覆盖，"
            "但门槛较高：\n"
            "  • §2.3 覆盖须指明具体 K 线序号+结构特征，且该特征超出五信号投票的计算范围；\n"
            "  • §2.4 近端K8-K1为主判、背景K20-K1仅参考；覆盖须基于近端结构突变证据；\n"
            "  • override_reason 必须具体，不接受「整体看跌」「感觉已变」等模糊描述。"
        )
        return "\n".join(hint_lines)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_render_program_prefill_hint failed: %s", exc)
        return ""
