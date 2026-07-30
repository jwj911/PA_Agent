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
        "市场诊断框架.prompt.md",
        "市场诊断框架",
        ("stage1",),
        "task",
        output_contract="stage1_diagnosis",
        dependencies=(pid.BINARY_DECISION,),
        legacy_filename=sf.MARKET_DIAGNOSIS,
    ),
    _spec(
        pid.KLINE_SIGNAL,
        "文件16-K线信号识别.prompt.md",
        "K 线信号识别",
        ("stage1", "stage2"),
        "base",
        output_contract="stage1_diagnosis|stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
        legacy_filename=sf.KLINE_SIGNAL,
    ),
    _spec(
        pid.BAR_CHECKLIST,
        "逐棒分析检查单.prompt.md",
        "逐棒分析检查单",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
        legacy_filename=sf.BAR_CHECKLIST,
    ),
    _spec(
        pid.STOP_TARGET_POSITION,
        "文件17-止损和止盈与仓位管理.prompt.md",
        "止损、止盈与仓位约束",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
        legacy_filename=sf.STOP_TARGET_POSITION,
    ),
    _spec(
        pid.MEASURED_MOVE,
        "文件23-MeasuredMove与结构目标.prompt.md",
        "Measured Move 与结构目标",
        ("stage2",),
        "base",
        output_contract="stage2_decision",
        dependencies=(pid.BINARY_DECISION,),
        legacy_filename=sf.MEASURED_MOVE,
    ),
    _spec(
        pid.BULLISH_CHANNEL_ID,
        "上涨通道分析识别.prompt.md",
        "上涨通道识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BULLISH_CHANNEL_ID,
    ),
    _spec(
        pid.BULLISH_CHANNEL_STRATEGY,
        "上涨通道交易策略.prompt.md",
        "上涨通道策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BULLISH_CHANNEL_ID,),
        legacy_filename=sf.BULLISH_CHANNEL_STRATEGY,
    ),
    _spec(
        pid.BEARISH_CHANNEL_ID,
        "下跌通道分析识别.prompt.md",
        "下跌通道识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BEARISH_CHANNEL_ID,
    ),
    _spec(
        pid.BEARISH_CHANNEL_STRATEGY,
        "下跌通道交易策略.prompt.md",
        "下跌通道策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BEARISH_CHANNEL_ID,),
        legacy_filename=sf.BEARISH_CHANNEL_STRATEGY,
    ),
    _spec(
        pid.BULLISH_SPIKE_ID,
        "极速上涨分析识别.prompt.md",
        "极速上涨识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BULLISH_SPIKE_ID,
    ),
    _spec(
        pid.BULLISH_SPIKE_STRATEGY,
        "极速上涨交易策略.prompt.md",
        "极速上涨策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BULLISH_SPIKE_ID,),
        legacy_filename=sf.BULLISH_SPIKE_STRATEGY,
    ),
    _spec(
        pid.BEARISH_SPIKE_ID,
        "极速下跌分析识别.prompt.md",
        "极速下跌识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BEARISH_SPIKE_ID,
    ),
    _spec(
        pid.BEARISH_SPIKE_STRATEGY,
        "极速下跌交易策略.prompt.md",
        "极速下跌策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.BEARISH_SPIKE_ID,),
        legacy_filename=sf.BEARISH_SPIKE_STRATEGY,
    ),
    _spec(
        pid.RANGE_ID,
        "震荡区间分析识别.prompt.md",
        "震荡区间识别",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.RANGE_ID,
    ),
    _spec(
        pid.RANGE_STRATEGY,
        "震荡区间交易策略.prompt.md",
        "震荡区间策略",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        dependencies=(pid.RANGE_ID,),
        legacy_filename=sf.RANGE_STRATEGY,
    ),
    _spec(
        pid.CHANNEL_WIDTH,
        "文件13-窄通道与宽通道策略.prompt.md",
        "窄通道与宽通道",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.CHANNEL_WIDTH,
    ),
    _spec(
        pid.WEDGE,
        "文件14-楔形形态分析交易.prompt.md",
        "楔形",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.WEDGE,
    ),
    _spec(
        pid.REVERSAL,
        "文件15-二次入场机会.prompt.md",
        "二次入场",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.REVERSAL,
    ),
    _spec(
        pid.BREAKOUT_FAILURE,
        "文件18-突破失败与突破测试.prompt.md",
        "突破失败与突破测试",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BREAKOUT_FAILURE,
    ),
    _spec(
        pid.H1H2,
        "文件19-H1H2-L1L2计数.prompt.md",
        "H1/H2/L1/L2 计数",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.H1H2,
    ),
    _spec(
        pid.ALWAYS_IN,
        "文件20-AlwaysIn与20GB.prompt.md",
        "Always In 与 20GB",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.ALWAYS_IN,
    ),
    _spec(
        pid.BARBWIRE,
        "文件21-铁丝网与无交易环境.prompt.md",
        "铁丝网与无交易环境",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.BARBWIRE,
    ),
    _spec(
        pid.MAGNET,
        "文件22-信号失败后的磁力位.prompt.md",
        "失败信号与磁力位",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.MAGNET,
    ),
    _spec(
        pid.FINAL_FLAG,
        "文件24-最终旗形与趋势末端.prompt.md",
        "最终旗形与趋势末端",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.FINAL_FLAG,
    ),
    _spec(
        pid.MTR,
        "文件25-主要趋势反转MTR.prompt.md",
        "主要趋势反转 MTR",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.MTR,
    ),
    _spec(
        pid.TRIANGLE,
        "文件27-三角形与收敛形态.prompt.md",
        "三角形与收敛形态",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.TRIANGLE,
    ),
    _spec(
        pid.DOUBLE_TOP_BOTTOM,
        "文件28-双重顶底与微型结构.prompt.md",
        "双重顶底与微型结构",
        ("stage2",),
        "strategy",
        output_contract="stage2_decision",
        legacy_filename=sf.DOUBLE_TOP_BOTTOM,
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
