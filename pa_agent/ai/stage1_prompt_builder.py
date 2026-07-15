"""Stage 1 user-prompt builder for :mod:`pa_agent.ai.prompt_assembler`.

This module owns the Stage 1 user turn construction: full Stage 1,
incremental Stage 1, continuation-mode incremental Stage 1, and the
program market-feature injection helpers used by those prompts.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from pa_agent.ai.kline_table_renderer import render_kline_feature_table, render_kline_table
from pa_agent.ai.market_features import (
    compute_simple_market_features,
    inject_market_features_section,
    render_simple_market_features,
)
from pa_agent.ai.pattern_routing import (
    STAGE1_DETECTED_PATTERNS_GUIDE,
    STAGE1_PATTERN_BRIEFS_BLOCK,
)
from pa_agent.ai.program_prefill_hint import render_program_prefill_hint

if TYPE_CHECKING:
    from collections.abc import Callable

    from pa_agent.data.base import KlineFrame
    from pa_agent.records.schema import AnalysisRecord

logger = logging.getLogger(__name__)


def render_simple_market_features_block(frame: KlineFrame) -> str:
    """Render simple structure pre-computations (range, swings, HL count, MM)."""
    try:
        features = compute_simple_market_features(frame)
        return render_simple_market_features(features)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_render_simple_market_features_block failed: %s", exc)
        return ""


def inject_market_features_block(prompt: str, frame: KlineFrame) -> str:
    """Refresh or insert program market-features into a Stage 1 user prompt."""
    block = render_simple_market_features_block(frame)
    if not block:
        return prompt
    return inject_market_features_section(prompt, block)


class Stage1PromptBuilder:
    """Build full and incremental Stage 1 user prompts."""

    def __init__(
        self,
        *,
        load: Callable[[str], str],
        prompt_settings: Any = None,
        stage1_task_prompt_txt_files: tuple[str, ...],
        stage1_output_reminder_for_mode: Callable[[str], str],
        stage1_tail_reminder: str,
        incremental_output_hard_rules: str,
        market_features_authority_note: str,
        render_kline_table_fn: Callable[..., str] = render_kline_table,
        render_kline_feature_table_fn: Callable[..., str] = render_kline_feature_table,
        render_program_prefill_hint_fn: Callable[[KlineFrame], str] = render_program_prefill_hint,
        render_market_features_block_fn: Callable[[KlineFrame], str] = render_simple_market_features_block,
    ) -> None:
        self._load = load
        self._prompt_settings = prompt_settings
        self._stage1_task_prompt_txt_files = stage1_task_prompt_txt_files
        self._stage1_output_reminder_for_mode = stage1_output_reminder_for_mode
        self._stage1_tail_reminder = stage1_tail_reminder
        self._incremental_output_hard_rules = incremental_output_hard_rules
        self._market_features_authority_note = market_features_authority_note
        self._render_kline_table = render_kline_table_fn
        self._render_kline_feature_table = render_kline_feature_table_fn
        self._render_program_prefill_hint = render_program_prefill_hint_fn
        self._render_simple_market_features_block = render_market_features_block_fn

    def _stage1_pattern_supplement(self) -> str:
        """Pattern tag table + briefs for Stage 1 (optional via settings)."""
        if self._prompt_settings is not None and not getattr(
            self._prompt_settings, "stage1_inject_pattern_briefs", True
        ):
            return ""
        return f"{STAGE1_DETECTED_PATTERNS_GUIDE}\n\n---\n\n{STAGE1_PATTERN_BRIEFS_BLOCK}"

    def build_stage1_user_prompt(
        self, frame: KlineFrame, *, analysis_mode: str = "original"
    ) -> str:
        """Build the Stage 1 task turn; stage-specific rules stay out of system."""
        pattern_block = self._stage1_pattern_supplement()
        prefill_hint = self._render_program_prefill_hint(frame)
        stage1_parts = [
            *(self._load(name) for name in self._stage1_task_prompt_txt_files),
            *([pattern_block] if pattern_block else []),
            self._stage1_output_reminder_for_mode(analysis_mode),
        ]
        stage1_context = "\n\n---\n\n".join(p for p in stage1_parts if p)
        kline_table = self._render_kline_table(frame)
        feature_table = self._render_kline_feature_table(frame)
        simple_features_block = self._render_simple_market_features_block(frame)
        n_bars = len(frame.bars)
        if n_bars > 40:
            bg_window = f"**长程背景 K{n_bars}–K41**（较老部分）：\n"
        else:
            bg_window = (
                f"**长程背景**（当前仅 {n_bars} 根，不足 41 根，与近期窗口重叠；"
                f"以程序预填 §2.2 为准）：\n"
            )
        return (
            "## 阶段一任务\n\n"
            "你现在只执行阶段一：市场诊断与闸门判断。不要评估具体下单、止损、止盈或仓位。\n\n"
            f"{stage1_context}\n\n"
            "---\n\n"
            f"## 当前分析目标\n\n"
            f"品种:{frame.symbol} 周期:{frame.timeframe} K线数量:{n_bars}\n"
            f"（K线序号：1=最新已收盘，最大 K{n_bars}；"
            f"每个决策节点的 bar_range 由你自行选择子区间，勿超出 K{n_bars}-K1）\n\n"
            f"## ⚠️ 分析窗口分层规则（与程序 §2.2/§2.3/§2.4 预填一致，必须遵守）\n\n"
            f"你收到全部 {n_bars} 根 K 线数据；下列分层与 `市场诊断框架.txt`、程序三窗口摘要**同一标准**：\n\n"
            f"{bg_window}"
            f"- swing 高低点、磁力位参考 → 写入 `htf_context`；§2.2 背景方向\n"
            f"- **禁止**用背景方向否决近期 `direction`；冲突时近期为主、背景作风险参考\n\n"
            f"**近期结构 K{min(40, n_bars)}–K1：**\n"
            f"- `cycle_position`、`direction`、通道/区间/波段主结构\n"
            f"- 程序 §2.3 方向投票与多数闸门 bar_range 优先此窗口\n\n"
            f"**即时惯性 K{min(8, n_bars)}–K1：**\n"
            f"- §2.4 Always In、§2.5 惯性强度、近端 spike_stage / 尖峰识别\n\n"
            f"**即时信号 K{min(10, n_bars)}–K1：**\n"
            f"- 信号棒/入场棒/二次入场/突破失败（阶段二 §9 裁定窗口）\n\n"
            f"**逐棒摘要 K5–K1：**\n"
            f"- `bar_by_bar_summary` **必须**恰好 5 条（窗口≥5 根时），每条 1 句 reason\n\n"
            f"## K线数据(序号1=最新已收盘K线,序号越大越早;不含当前未收盘K线;"
            f"阳阴列由程序按收盘价与开盘价计算:收盘>开盘=阳线,收盘<开盘=阴线,相等=平)\n\n"
            f"{kline_table}\n\n"
            "## K线几何特征(程序预计算；「类型」列为单字段 bar_type，判定优先级：inside/outside > doji/trend/flat/other；"
            "不替代周期判断；基于当前 N 根已收盘 K 线，指标非全历史延续)\n\n"
            f"{feature_table}\n\n"
            + (f"{simple_features_block}\n\n" if simple_features_block else "")
            + (f"{prefill_hint}\n\n" if prefill_hint else "")
            + f"请根据以上数据，严格输出阶段一 JSON 诊断结果。\n\n"
            f"{self._stage1_tail_reminder}"
        )

    def build_incremental_stage1_user_prompt(
        self,
        frame: KlineFrame,
        previous_record: AnalysisRecord,
        new_bar_count: int,
        *,
        analysis_mode: str = "original",
    ) -> str:
        """Build a Stage 1 update turn using the last completed analysis."""
        pattern_block = self._stage1_pattern_supplement()
        prefill_hint = self._render_program_prefill_hint(frame)
        stage1_parts = [
            *(self._load(name) for name in self._stage1_task_prompt_txt_files),
            *([pattern_block] if pattern_block else []),
            self._stage1_output_reminder_for_mode(analysis_mode),
        ]
        stage1_context = "\n\n---\n\n".join(p for p in stage1_parts if p)
        n_bars = len(frame.bars)
        new_count = max(0, min(new_bar_count, n_bars))
        new_kline_table = self._render_kline_table(frame, limit=new_count)
        new_feature_table = self._render_kline_feature_table(frame, limit=new_count)
        full_kline_table = self._render_kline_table(frame)
        full_feature_table = self._render_kline_feature_table(frame)
        simple_features_block = self._render_simple_market_features_block(frame)
        previous_summary = {
            "meta": previous_record.meta.model_dump(),
            "stage1_diagnosis": previous_record.stage1_diagnosis or {},
            "stage2_decision": previous_record.stage2_decision or {},
            "strategy_files_used": previous_record.strategy_files_used or [],
        }
        return (
            "## 阶段一增量任务\n\n"
            "你现在只执行阶段一：基于上一轮已完成分析和新增 K 线，更新市场诊断与闸门判断。\n"
            "不要评估具体下单、止损、止盈或仓位；这些留到阶段二。\n\n"
            "增量分析规则：\n"
            "- 先检查上一轮诊断在新增 K 线后是否仍成立。\n"
            "- 如果市场结构未被破坏，可以延续上一轮 cycle_position/direction，但必须用新增 K 线重新说明依据。\n"
            "- 如果新增 K 线出现突破、反转、极端波动或让原结论失效，必须更新诊断。\n"
            "- 必须输出顶层字段 **incremental_delta**（不可省略），结构示例：\n"
            '  "incremental_delta": {"new_closed_bars":["K1"],'
            '"changed_fields":["direction","cycle_position"],'
            '"summary":"相对上一轮：新增K1突破区间上沿，方向由中性转偏多"}\n'
            "- new_closed_bars 长度必须等于「新增已收盘K线」数量（1根则只写 [\"K1\"]）。\n"
            "- 并在 summary / risk_warning / gate_trace 中说明相对上一轮变化。\n"
            "- gate_result=proceed 时 gate_trace 仍须覆盖 §1.2、§1.3、§2.1、§2.2、§2.5（§1.1/§2.3/§2.4 由程序填充）。\n"
            "- 输出仍必须是完整阶段一 JSON，而不是差异补丁。\n\n"
            f"{self._incremental_output_hard_rules}\n\n"
            f"{stage1_context}\n\n"
            "---\n\n"
            f"## 当前分析目标\n\n"
            f"品种:{frame.symbol} 周期:{frame.timeframe} K线数量:{n_bars} 新增已收盘K线:{new_count}\n"
            f"（K线序号：1=最新已收盘，最大 K{n_bars}；"
            f"每个决策节点的 bar_range 由你自行选择子区间，勿超出 K{n_bars}-K1）\n\n"
            "## 上一轮已完成分析（仅作为延续上下文）\n\n"
            f"```json\n{json.dumps(previous_summary, ensure_ascii=False, indent=2)}\n```\n\n"
            f"## 新增 K线数据(共{new_count}根，序号1=最新已收盘；含阳阴列)\n\n"
            f"{new_kline_table}\n\n"
            f"## 新增 K线几何特征(共{new_count}根；多棒形态按完整{n_bars}根窗口计算，"
            f"与前棒重叠/内包/ioi 以完整表为准)\n\n"
            f"{new_feature_table}\n\n"
            f"## 当前完整 K线数据(共{n_bars}根，用于必要时复核整体结构；含阳阴列)\n\n"
            f"{full_kline_table}\n\n"
            f"## 当前完整 K线几何特征(用于逐棒辅助，不替代周期判断；"
            f"基于当前 N 根已收盘 K 线，指标非全历史延续)\n\n"
            f"{full_feature_table}\n\n"
            + (f"{simple_features_block}\n\n" if simple_features_block else "")
            + (f"{prefill_hint}\n\n" if prefill_hint else "")
            + "请基于上一轮结论、新增K线和当前完整K线，严格输出更新后的阶段一 JSON 诊断结果。\n\n"
            f"{self._stage1_tail_reminder}"
        )

    def build_incremental_stage1_continuation_user_prompt(
        self,
        frame: KlineFrame,
        previous_record: AnalysisRecord,
        new_bar_count: int,
        *,
        analysis_mode: str = "original",
    ) -> str:
        """Build the incremental continuation user turn (message [3] in 4-message mode).

        Only sends NEW K-line data; the model can reference the full K-line table
        from the previous Stage 1 user message ([1]) above.
        Injects program prefill hint so the AI knows updated §2.3/§2.4 verdicts
        even when the full K-line table is not re-sent.
        """
        prefill_hint = self._render_program_prefill_hint(frame)
        simple_features_block = self._render_simple_market_features_block(frame)
        if simple_features_block:
            simple_features_block = self._market_features_authority_note + simple_features_block
        n_bars = len(frame.bars)
        new_count = max(0, min(new_bar_count, n_bars))
        new_kline_table = self._render_kline_table(frame, limit=new_count)
        new_feature_table = self._render_kline_feature_table(frame, limit=new_count)
        previous_summary = {
            "meta": previous_record.meta.model_dump(),
            "stage1_diagnosis": previous_record.stage1_diagnosis or {},
            "stage2_decision": previous_record.stage2_decision or {},
            "strategy_files_used": previous_record.strategy_files_used or [],
        }
        return (
            "## 阶段一增量更新任务\n\n"
            "上方是你上一轮完成的阶段一诊断。现在基于新增 K 线，更新诊断与闸门判断。\n"
            "完整 K 线数据已包含在上方阶段一用户消息中（K线序号已重新编号，"
            "K1=当前最新已收盘K线），你可以回溯查看任何历史 K 线。\n\n"
            "⚠ 反锚定要求——这是增量分析最重要的原则：\n"
            "- 不要因为上一轮已得出结论就倾向于延续它；上一轮结论只是参考起点，不是约束。\n"
            "- 如果新增 K 线改变了市场结构（突破、反转、趋势加速/衰竭），必须果断推翻上一轮结论，而非在旧结论上微调。\n"
            "- 判断标准：如果你是第一次看到这组完整 K 线（包括上方历史K线+新增K线），你会得出什么结论？那才是正确结论。\n"
            "- 每次增量更新都应视为一次重新诊断——只是你不必重复描述未变的部分。\n\n"
            "增量分析规则：\n"
            "- 先独立审视完整 K 线数据，形成自己的判断，再与上一轮结论对照。\n"
            "- 如果市场结构确实未被破坏，可以延续上一轮 cycle_position/direction，但必须用新增 K 线重新说明依据。\n"
            "- 如果新增 K 线出现突破、反转、极端波动或让原结论失效，必须更新诊断——宁可过度更新，不可锚定延续。\n"
            "- 若 K1 收盘已突破上一轮 resistance_levels 或跌破 support_levels，必须重算支撑/阻力，"
            "不得原样延续已失效价位（程序也会按收盘价剔除失效档位）。\n"
            "- 必须输出顶层字段 **incremental_delta**（不可省略），结构示例：\n"
            '  "incremental_delta": {"new_closed_bars":["K1"],'
            '"changed_fields":["direction","cycle_position"],'
            '"summary":"相对上一轮：新增K1突破区间上沿，方向由中性转偏多"}\n'
            "- new_closed_bars 长度必须等于「新增已收盘K线」数量（1根则只写 [\"K1\"]）。\n"
            "- 并在 summary / risk_warning / gate_trace 中说明相对上一轮变化。\n"
            "- gate_result=proceed 时 gate_trace 仍须覆盖 §1.2、§1.3、§2.1、§2.2、§2.5（§1.1/§2.3/§2.4 由程序填充）。\n"
            "- 输出仍必须是完整阶段一 JSON，而不是差异补丁。\n\n"
            f"{self._incremental_output_hard_rules}\n\n"
            f"## 当前分析目标更新\n\n"
            f"品种:{frame.symbol} 周期:{frame.timeframe} K线数量:{n_bars} 新增已收盘K线:{new_count}\n"
            f"（K线序号已重新编号：1=最新已收盘，最大 K{n_bars}；"
            f"每个决策节点的 bar_range 由你自行选择子区间，勿超出 K{n_bars}-K1）\n\n"
            "## 上一轮已完成分析（仅作为延续上下文）\n\n"
            f"```json\n{json.dumps(previous_summary, ensure_ascii=False, indent=2)}\n```\n\n"
            f"## 新增 K线数据(共{new_count}根，序号1=最新已收盘；含阳阴列)\n\n"
            f"{new_kline_table}\n\n"
            f"## 新增 K线几何特征(共{new_count}根；多棒形态按完整{n_bars}根窗口计算，"
            f"与前棒重叠/内包/ioi 以完整表为准)\n\n"
            f"{new_feature_table}\n\n"
            + (f"{simple_features_block}\n\n" if simple_features_block else "")
            + (f"{prefill_hint}\n\n" if prefill_hint else "")
            + "请基于上方完整K线数据、上一轮结论和新增K线，严格输出更新后的阶段一 JSON 诊断结果。\n\n"
            f"{self._stage1_tail_reminder}"
        )
