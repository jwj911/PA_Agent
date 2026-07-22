"""Repeated L2 TemplateStore/legacy-loader compatibility observation."""

from __future__ import annotations

import json
from pathlib import Path

from pa_agent.ai.prompt_assembler import PromptAssembler
from pa_agent.data.snapshot import build_analysis_frame
from tests.fixtures.kline_bars import make_newest_first_bars

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt_engineering"
GOLDEN_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "prompt_golden.json"
OBSERVATION_ROUNDS = 5


def test_template_store_and_legacy_loader_remain_byte_equal_over_observation_rounds() -> None:
    """Repeat all migrated prompt paths to catch cache or fallback drift."""
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    fixture = golden["stage2_fixture"]
    frame = build_analysis_frame(
        make_newest_first_bars(fixture["bar_count"], with_forming=False),
        20,
        fixture["symbol"],
        fixture["timeframe"],
    )
    assert frame is not None

    stage1_json = fixture["stage1_json"]
    strategy_files = fixture["strategy_files"]
    template_store = PromptAssembler(prompt_dir=PROMPT_DIR, use_template_store=True)
    legacy = PromptAssembler(prompt_dir=PROMPT_DIR, use_template_store=False)

    for _round in range(OBSERVATION_ROUNDS):
        assert template_store._build_shared_system_prompt_inner() == (
            legacy._build_shared_system_prompt_inner()
        )
        assert template_store._build_stage1_system_prompt() == legacy._build_stage1_system_prompt()
        assert template_store._build_stage2_system_prompt() == legacy._build_stage2_system_prompt()

        stage1_messages = template_store.build_stage1(frame)
        legacy_stage1_messages = legacy.build_stage1(frame)
        assert stage1_messages == legacy_stage1_messages

        for decision_stance in ("conservative", "balanced"):
            assert template_store.build_stage2(
                frame,
                stage1_json,
                strategy_files,
                [],
                decision_stance=decision_stance,
            ) == legacy.build_stage2(
                frame,
                stage1_json,
                strategy_files,
                [],
                decision_stance=decision_stance,
            )

        continuation_kwargs = {
            "frame": frame,
            "stage1_messages": stage1_messages,
            "stage1_reply_content": fixture["reply"],
            "stage1_json": stage1_json,
            "strategy_files": strategy_files,
            "experience_entries": [],
        }
        legacy_kwargs = {
            **continuation_kwargs,
            "stage1_messages": legacy_stage1_messages,
        }
        for use_prefix_chain in (False, True):
            assert template_store.build_stage2_continuation(
                **continuation_kwargs,
                use_prefix_chain=use_prefix_chain,
            ) == legacy.build_stage2_continuation(
                **legacy_kwargs,
                use_prefix_chain=use_prefix_chain,
            )
