"""Stage 2 prompt builder for :mod:`pa_agent.ai.prompt_assembler`.

This module owns Stage 2 message construction and Stage 2 user-turn rendering.
``PromptAssembler`` keeps the public facade, system prompt cache, and legacy
private wrapper names.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pa_agent.ai.decision_stance import build_decision_stance_guidance, normalize_stance

if TYPE_CHECKING:
    from collections.abc import Callable

    from pa_agent.data.base import KlineFrame


class Stage2PromptBuilder:
    """Build standalone and prefix-chain Stage 2 prompt messages."""

    def __init__(
        self,
        *,
        build_stage2_system_prompt: Callable[[], str],
        load: Callable[[str], str],
        load_full_strategy_library: Callable[[], bool],
        prompt_settings: Any = None,
        stage2_user_task_txt_files: Callable[..., list[str]],
        build_next_cycle_prediction_instruction: Callable[..., str],
        stage2_api_task_rule: str,
        stage2_output_contract: str,
        next_bar_prediction_instruction: str,
        next_bar_disabled_note: str,
        stage2_tail_reminder: str,
        market_features_authority_note: str,
        render_trend_conflict_guidance: Callable[[dict], str],
        render_transition_guidance: Callable[[dict], str],
        render_planned_limit_hint: Callable[[dict, KlineFrame], str],
        render_experience: Callable[..., str],
        render_previous_prediction: Callable[[Any | None], str],
        compact_stage1_for_stage2: Callable[[dict], dict],
        render_simple_market_features_block: Callable[[KlineFrame], str],
        render_kline_table: Callable[..., str],
        render_kline_feature_table: Callable[..., str],
        normalize_stage1_assistant_for_chain: Callable[[dict, str], str],
    ) -> None:
        self._build_stage2_system_prompt = build_stage2_system_prompt
        self._load = load
        self._load_full_strategy_library = load_full_strategy_library
        self._prompt_settings = prompt_settings
        self._stage2_user_task_txt_files = stage2_user_task_txt_files
        self._build_next_cycle_prediction_instruction = build_next_cycle_prediction_instruction
        self._stage2_api_task_rule = stage2_api_task_rule
        self._stage2_output_contract = stage2_output_contract
        self._next_bar_prediction_instruction = next_bar_prediction_instruction
        self._next_bar_disabled_note = next_bar_disabled_note
        self._stage2_tail_reminder = stage2_tail_reminder
        self._market_features_authority_note = market_features_authority_note
        self._render_trend_conflict_guidance = render_trend_conflict_guidance
        self._render_transition_guidance = render_transition_guidance
        self._render_planned_limit_hint = render_planned_limit_hint
        self._render_experience = render_experience
        self._render_previous_prediction = render_previous_prediction
        self._compact_stage1_for_stage2 = compact_stage1_for_stage2
        self._render_simple_market_features_block = render_simple_market_features_block
        self._render_kline_table = render_kline_table
        self._render_kline_feature_table = render_kline_feature_table
        self._normalize_stage1_assistant_for_chain = normalize_stage1_assistant_for_chain

    def build_stage2(
        self,
        frame: KlineFrame,
        stage1_json: dict,
        strategy_files: list[str],
        experience_entries: list[Any],
        *,
        decision_stance: str = "conservative",
    ) -> list[dict]:
        """Build a standalone Stage 2 request (kept for tests/tools)."""
        system_content = self._build_stage2_system_prompt()
        user_content = self.build_stage2_user_prompt(
            frame=frame,
            stage1_json=stage1_json,
            strategy_files=strategy_files,
            experience_entries=experience_entries,
            decision_stance=decision_stance,
            enable_next_bar_prediction=False,
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def build_stage2_continuation(
        self,
        *,
        frame: KlineFrame,
        stage1_messages: list[dict],
        stage1_reply_content: str,
        stage1_json: dict,
        strategy_files: list[str],
        experience_entries: list[Any],
        decision_stance: str = "conservative",
        previous_record: Any | None = None,
        enable_next_bar_prediction: bool = False,
        provider_settings: Any | None = None,
        use_prefix_chain: bool | None = None,
        structure_flip_cooldown_bars: int = 3,
    ) -> list[dict]:
        """Build Stage 2 messages, optionally chaining after Stage 1 for KV cache.

        Prefix-chain mode (DeepSeek native, default when safe):
          [system, user(S1...), assistant(S1 JSON), user(S2 task only)]

        Standalone mode (OpenClaw Agent and similar):
          [system, user(S2 task + full K-line tables)]
        """
        from pa_agent.ai.deepseek_client import supports_kv_prefix_chain

        if use_prefix_chain is None:
            use_prefix_chain = supports_kv_prefix_chain(provider_settings)

        chain_after_s1 = bool(use_prefix_chain and stage1_messages)
        stage2_user_content = self.build_stage2_user_prompt(
            frame=frame,
            stage1_json=stage1_json,
            strategy_files=strategy_files,
            experience_entries=experience_entries,
            decision_stance=decision_stance,
            previous_record=previous_record,
            enable_next_bar_prediction=enable_next_bar_prediction,
            omit_kline_block=chain_after_s1,
            structure_flip_cooldown_bars=structure_flip_cooldown_bars,
        )

        if chain_after_s1:
            assistant_content = self._normalize_stage1_assistant_for_chain(
                stage1_json,
                stage1_reply_content,
            )
            chain = [dict(m) for m in stage1_messages]
            chain.append({"role": "assistant", "content": assistant_content})
            chain.append({"role": "user", "content": stage2_user_content})
            return chain

        system_content = self._build_stage2_system_prompt()
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": stage2_user_content},
        ]

    def build_stage2_user_prompt(
        self,
        *,
        frame: KlineFrame,
        stage1_json: dict,
        strategy_files: list[str],
        experience_entries: list[Any],
        decision_stance: str = "conservative",
        previous_record: Any | None = None,
        enable_next_bar_prediction: bool = False,
        omit_kline_block: bool = False,
        structure_flip_cooldown_bars: int = 3,
    ) -> str:
        """Build the Stage 2 task turn for standalone or prefix-chain mode."""
        from pa_agent.ai.decision_continuity import (
            build_continuity_context,
            render_continuity_prompt_block,
        )

        stance_block = build_decision_stance_guidance(normalize_stance(decision_stance))
        continuity_ctx = build_continuity_context(
            frame=frame,
            stage1_json=stage1_json,
            previous_record=previous_record,
            cooldown_bars=structure_flip_cooldown_bars,
        )
        continuity_block = render_continuity_prompt_block(continuity_ctx)
        conflict_block = self._render_trend_conflict_guidance(stage1_json)
        transition_block = self._render_transition_guidance(stage1_json)
        planned_limit_block = self._render_planned_limit_hint(stage1_json, frame)
        stage2_parts = [
            stance_block,
            continuity_block,
            conflict_block,
            transition_block,
            planned_limit_block,
            *(
                self._load(name)
                for name in self._stage2_user_task_txt_files(
                    strategy_files,
                    direction=str(stage1_json.get("direction", "") or ""),
                    load_full_strategy_library=self._load_full_strategy_library(),
                )
            ),
        ]
        if experience_entries:
            max_chars = 400
            if self._prompt_settings is not None:
                max_chars = int(
                    getattr(
                        self._prompt_settings,
                        "experience_max_chars_per_entry",
                        400,
                    )
                )
            stage2_parts.append(
                self._render_experience(
                    experience_entries,
                    max_chars_per_entry=max_chars,
                )
            )
        stage2_parts.append(self._stage2_output_contract)
        if enable_next_bar_prediction:
            stage2_parts.append(self._next_bar_prediction_instruction)
        else:
            stage2_parts.append(self._next_bar_disabled_note)
        stage2_parts.append(
            self._build_next_cycle_prediction_instruction(
                enable_next_bar=enable_next_bar_prediction
            )
        )
        # Static strategy / contract blocks first -> better KV prefix reuse across runs.
        stage2_context = "\n\n---\n\n".join(p for p in stage2_parts if p)

        from pa_agent.util.price_tick import format_breakout_tick_hint

        n_bars = len(frame.bars)
        breakout_tick_hint = format_breakout_tick_hint(frame)
        prev_pred_block = self._render_previous_prediction(previous_record)
        compact_s1 = json.dumps(
            self._compact_stage1_for_stage2(stage1_json),
            ensure_ascii=False,
            indent=2,
        )

        if omit_kline_block:
            kline_block = (
                "## K线数据\n\n"
                "完整 K 线表与几何特征已包含在上方阶段一用户消息中"
                "（序号按当前分析窗口编号，K1=最新已收盘）。"
                "阶段二须结合该表与下方阶段一诊断 JSON 做交易者方程与定价。\n\n"
            )
            simple_features_block = self._render_simple_market_features_block(frame)
            if simple_features_block:
                kline_block += (
                    self._market_features_authority_note
                    + simple_features_block
                    + "\n\n"
                )
            if breakout_tick_hint:
                kline_block += f"{breakout_tick_hint}\n\n"
        else:
            kline_table = self._render_kline_table(frame)
            feature_table = self._render_kline_feature_table(frame)
            simple_features_block = self._render_simple_market_features_block(frame)
            kline_block = (
                f"## K线数据(共{n_bars}根，含阳阴列；各节点 bar_range 由你据实填写)\n\n"
                f"{kline_table}\n\n"
                "## K线几何特征(程序预计算，仅作逐棒客观辅助；不得替代交易者方程；"
                "基于当前 N 根已收盘 K 线，指标非全历史延续)\n\n"
                f"{feature_table}\n\n"
            )
            if simple_features_block:
                kline_block += f"{simple_features_block}\n\n"
            if breakout_tick_hint:
                kline_block += f"{breakout_tick_hint}\n\n"

        kline_intro = (
            "完整 K 线表见上方阶段一用户消息。\n\n"
            if omit_kline_block
            else "本消息下方附有完整 K 线表与几何特征。\n\n"
        )
        return (
            f"{self._stage2_api_task_rule}\n\n"
            "## 阶段二任务\n\n"
            "你现在独立执行阶段二：交易决策、风险收益和下单方式评估（基于阶段一诊断结果）。\n"
            "以下 JSON 是程序校验通过后的阶段一诊断结果，请以此为权威依据；"
            f"{kline_intro}"
            f"{stage2_context}\n\n"
            "---\n\n"
            f"## 阶段一诊断结果\n\n```json\n"
            f"{compact_s1}"
            f"\n```\n\n"
            f"{kline_block}"
            f"{prev_pred_block + chr(10) if prev_pred_block else ''}"
            f"请根据以上诊断和K线数据,按《二元决策.txt》§3–§11、§14 输出 JSON 决策结果"
            f"(含 decision_trace 与 terminal)。\n"
            f"注意:如果判断不下单,entry_price、take_profit_price、take_profit_price_2、stop_loss_price、order_direction 必须全部为 null。\n\n"
            f"{self._stage2_tail_reminder}"
        )
