"""Manifest mapping stable Prompt IDs to runtime template files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pa_agent.ai import strategy_files as sf
from pa_agent.ai.prompting import prompt_ids as pid
from pa_agent.ai.prompting.prompt_catalog import PromptCatalog
from pa_agent.ai.prompting.prompt_ids import PromptId

StageName = Literal["stage1", "stage2"]
TemplateRole = Literal["system", "task", "base", "strategy"]
MANIFEST_VERSION = "v2"


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    """Static metadata separating logical identity from physical storage."""

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

    @property
    def name(self) -> str:
        """Return the immutable filename used by pre-ID callers."""
        return self.legacy_filename


def _spec(
    prompt_id: PromptId,
    source_path: str,
    display_name: str,
    stages: tuple[StageName, ...],
    role: TemplateRole,
    *,
    output_contract: str | None = None,
    dependencies: tuple[PromptId, ...] = (),
    legacy_filename: str | None = None,
    legacy_aliases: tuple[str, ...] = (),
) -> TemplateSpec:
    return TemplateSpec(
        prompt_id=prompt_id,
        source_path=source_path,
        legacy_filename=source_path if legacy_filename is None else legacy_filename,
        display_name=display_name,
        stages=stages,
        role=role,
        output_contract=output_contract,
        dependencies=dependencies,
        legacy_aliases=legacy_aliases,
    )


TEMPLATE_MANIFEST: tuple[TemplateSpec, ...] = (
    _spec(
        pid.PERSONA,
        "提示词大纲_人设与思维方式.prompt.md",
        "人设与思维方式",
        ("stage1", "stage2"),
        "system",
        legacy_filename=sf.PERSONA,
    ),
    _spec(
        pid.BINARY_DECISION,
        "二元决策.prompt.md",
        "交易二元决策树",
        ("stage1", "stage2"),
        "system",
        output_contract="stage1_diagnosis",
        legacy_filename=sf.BINARY_DECISION,
    ),
    _spec(
        pid.MARKET_DIAGNOSIS,
        sf.MARKET_DIAGNOSIS,
        "市场诊断框架",
        ("stage1",),
        "task",
        output_contract="stage1_diagnosis",
        dependencies=(pid.BINARY_DECISION,),
    ),
    _spec(
        pid.KLINE_SIGNAL,
        sf.KLINE_SIGNAL,
        "K 线信号识别",
        ("stage1", "stage2"),
        "base",
        output_contract="stage1_diagnosis|stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
    ),
    _spec(
        pid.BAR_CHECKLIST,
        sf.BAR_CHECKLIST,
        "逐棒分析检查单",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
    ),
    _spec(
        pid.STOP_TARGET_POSITION,
        sf.STOP_TARGET_POSITION,
        "止损、止盈与仓位约束",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
    ),
    _spec(
        pid.MEASURED_MOVE,
        sf.MEASURED_MOVE,
        "Measured Move 与结构目标",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
    ),
    _spec(
        pid.BULLISH_CHANNEL_ID,
        sf.BULLISH_CHANNEL_ID,
        "上涨通道识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BULLISH_CHANNEL_STRATEGY,
        sf.BULLISH_CHANNEL_STRATEGY,
        "上涨通道策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BULLISH_CHANNEL_ID,),
    ),
    _spec(
        pid.BEARISH_CHANNEL_ID,
        sf.BEARISH_CHANNEL_ID,
        "下跌通道识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BEARISH_CHANNEL_STRATEGY,
        sf.BEARISH_CHANNEL_STRATEGY,
        "下跌通道策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BEARISH_CHANNEL_ID,),
    ),
    _spec(
        pid.BULLISH_SPIKE_ID,
        sf.BULLISH_SPIKE_ID,
        "极速上涨识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BULLISH_SPIKE_STRATEGY,
        sf.BULLISH_SPIKE_STRATEGY,
        "极速上涨策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BULLISH_SPIKE_ID,),
    ),
    _spec(
        pid.BEARISH_SPIKE_ID,
        sf.BEARISH_SPIKE_ID,
        "极速下跌识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BEARISH_SPIKE_STRATEGY,
        sf.BEARISH_SPIKE_STRATEGY,
        "极速下跌策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BEARISH_SPIKE_ID,),
    ),
    _spec(
        pid.RANGE_ID,
        sf.RANGE_ID,
        "震荡区间识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.RANGE_STRATEGY,
        sf.RANGE_STRATEGY,
        "震荡区间策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.RANGE_ID,),
    ),
    _spec(
        pid.CHANNEL_WIDTH,
        sf.CHANNEL_WIDTH,
        "窄通道与宽通道",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.WEDGE,
        sf.WEDGE,
        "楔形",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.REVERSAL,
        sf.REVERSAL,
        "二次入场",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BREAKOUT_FAILURE,
        sf.BREAKOUT_FAILURE,
        "突破失败与突破测试",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.H1H2,
        sf.H1H2,
        "H1/H2/L1/L2 计数",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.ALWAYS_IN,
        sf.ALWAYS_IN,
        "Always In 与 20GB",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.BARBWIRE,
        sf.BARBWIRE,
        "铁丝网与无交易环境",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.MAGNET,
        sf.MAGNET,
        "失败信号与磁力位",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.FINAL_FLAG,
        sf.FINAL_FLAG,
        "最终旗形与趋势末端",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.MTR,
        sf.MTR,
        "主要趋势反转 MTR",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.TRIANGLE,
        sf.TRIANGLE,
        "三角形与收敛形态",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
    _spec(
        pid.DOUBLE_TOP_BOTTOM,
        sf.DOUBLE_TOP_BOTTOM,
        "双重顶底与微型结构",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
    ),
)


def validate_template_manifest(
    manifest: tuple[TemplateSpec, ...] = TEMPLATE_MANIFEST,
) -> dict[str, TemplateSpec]:
    """Validate and return the legacy filename index used by old callers."""
    return dict(PromptCatalog(manifest).by_legacy_filename)


TEMPLATE_CATALOG = PromptCatalog(TEMPLATE_MANIFEST)
TEMPLATE_MANIFEST_BY_ID = TEMPLATE_CATALOG.by_id
TEMPLATE_MANIFEST_BY_NAME = dict(TEMPLATE_CATALOG.by_legacy_filename)


def template_ids_for_stage(stage: StageName) -> tuple[PromptId, ...]:
    """Return manifest-ordered stable Prompt IDs assigned to *stage*."""
    return TEMPLATE_CATALOG.prompt_ids_for_stage(stage)


def template_files_for_stage(stage: StageName) -> tuple[str, ...]:
    """Return manifest-ordered legacy filenames assigned to *stage*."""
    return tuple(
        TEMPLATE_CATALOG.legacy_filename(prompt_id) for prompt_id in template_ids_for_stage(stage)
    )
