"""Stage-2 contextual guidance renderers for decision prompts.

Extracted from ``prompt_assembler.py`` (report §5.2 M1). These are the
deterministic, Stage-2-only guidance blocks that translate Stage-1 diagnosis
fields into short prompt paragraphs steering the decision model: new-vs-old
trend conflict (Brooks 并列原则), state-transition risk sizing, and the planned
limit-order hint driven by cycle/level structure. They depend only on stdlib
``math`` and the PyQt6-free ``KlineFrame`` leaf, so this module stays importable
without the GUI stack. ``PromptAssembler`` re-binds ``render_*`` /
``parse_level_midpoint`` as ``_render_*`` / ``_parse_level_midpoint``
staticmethods so existing ``self._render_planned_limit_hint(...)`` call sites keep
working byte-for-byte. Block headers / Chinese guidance strings / numeric
formatting must stay byte-for-byte identical (the model is prompted against these
exact blocks).
"""
from __future__ import annotations

import math

from pa_agent.data.base import KlineFrame


def render_trend_conflict_guidance(stage1_json: dict) -> str:
    """Stage-2 guidance when long-range background conflicts with recent direction."""
    tc = stage1_json.get("trend_context")
    if not isinstance(tc, dict) or not tc.get("conflict"):
        return ""
    bg = tc.get("background_direction", "neutral")
    td = tc.get("trading_direction", "neutral")
    spike = tc.get("recent_spike")
    lines = [
        "## 新旧趋势冲突指导（Brooks 并列原则）",
        "",
        f"长程背景方向：**{bg}**；交易主方向（近期）：**{td}**。",
        f"- {tc.get('with_trend_rule', '')}",
        "- **禁止**产出逆近期主方向的三价；顺近期即顺势。",
        "- 禁止追高潮/SCS；climax_risk 预警或触发后禁追原方向。",
        "- 在 risk_assessment / watch_points 写明长程背景磁力位。",
    ]
    if spike:
        lines.append(f"- 程序检测到近端 **{spike}** 尖峰：优先按尖峰/回撤逻辑，不追突破。")
    return "\n".join(lines) + "\n"


def render_transition_guidance(stage1_json: dict) -> str:
    """Render dynamic risk guidance from Stage 1 market_phase fields."""
    if stage1_json.get("market_phase") != "transitioning":
        return ""
    risk = stage1_json.get("transition_risk") or "medium"
    if risk == "high":
        size = "trade_confidence 倾向 30–45，只接受二次入场/突破回踩/边界强信号"
        selectivity = "只接受最清晰的二次入场、突破回踩或边界信号"
    elif risk == "medium":
        size = "trade_confidence 倾向 45–60，放弃弱信号与中部位置"
        selectivity = "选择性入场，放弃弱信号和中间位置"
    else:
        size = "trade_confidence 略降（约 55–65）"
        selectivity = "保持正常流程，但在 reason 中说明状态转换风险"
    return (
        "## 状态转换期风险指导\n\n"
        f"阶段一判断 market_phase=transitioning，transition_risk={risk}。\n"
        f"- 信号把握：{size}（**禁止**在 JSON 写仓位比例/手数）。\n"
        f"- 入场选择：{selectivity}。\n"
        "- 不因为状态转换而跳过 §9、§10、§14；只是提高信号质量门槛并降低交易频率。"
    )


def parse_level_midpoint(raw: object) -> float | None:
    """Parse support/resistance level string to a numeric midpoint."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        try:
            lo = float(parts[0])
            hi = float(parts[1])
            return (lo + hi) / 2.0
        except (TypeError, ValueError, IndexError):
            return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def render_planned_limit_hint(stage1_json: dict, frame: KlineFrame) -> str:
    """Contextual hint when channel/range structure favors planned limit orders."""
    cycle = str(stage1_json.get("cycle_position", "") or "").strip().lower()
    if cycle not in (
        "broad_channel",
        "trading_range",
        "normal_channel",
        "trending_tr",
    ):
        return ""

    bars = getattr(frame, "bars", None) or ()
    if not bars:
        return ""

    try:
        close = float(getattr(bars[0], "close", 0))
    except (TypeError, ValueError):
        return ""

    indicators = getattr(frame, "indicators", None)
    atr = None
    try:
        atr_vals = getattr(indicators, "atr14", ()) or ()
        if atr_vals and not math.isnan(float(atr_vals[0])):
            atr = float(atr_vals[0])
    except (TypeError, ValueError, IndexError):
        atr = None

    proximity = max(atr * 0.35, abs(close) * 0.0008) if atr and atr > 0 else abs(close) * 0.002

    supports = stage1_json.get("support_levels") or []
    resistances = stage1_json.get("resistance_levels") or []
    if not isinstance(supports, list):
        supports = []
    if not isinstance(resistances, list):
        resistances = []

    near_support: float | None = None
    near_resist: float | None = None
    support_label = ""
    resist_label = ""
    for lv in supports:
        mid = parse_level_midpoint(lv)
        if mid is not None and mid <= close and abs(close - mid) <= proximity:
            if near_support is None or mid > near_support:
                near_support = mid
                support_label = str(lv)
    for lv in resistances:
        mid = parse_level_midpoint(lv)
        if mid is not None and mid >= close and abs(close - mid) <= proximity:
            if near_resist is None or mid < near_resist:
                near_resist = mid
                resist_label = str(lv)

    direction = str(stage1_json.get("direction", "neutral") or "neutral").strip().lower()
    lines = [
        "## §9.0 / §9.0P 计划型限价提示（程序根据阶段一结构生成）",
        "",
        "**优先级：市场周期 + 方向背景 > 独立信号棒。**",
        f"- cycle_position=**{cycle}** → 默认优先考虑 **限价单**（§11），"
        "尤其在通道/区间 **边界** 或 **顺势回撤/反弹结构位**（非中部）。",
        "- 若无强信号棒：§9.0=否，**必须** 继续写 **§9.0P** 并尝试背景限价三价。",
        "- §9.0P=是：signal_bar.bar=null、quality=invalid；entry_bar pending；"
        "三价写入 decision，不要只在 watch_points 写触发条件。",
        "- 定价：先定结构 TP1/TP2，再定结构 stop；RR>1.0 时程序自动向外扩 stop（保持 TP 不变）。",
    ]
    if near_support is not None:
        lines.append(
            f"- 价格靠近下方支撑 **{support_label}**（约 {near_support:.4f}）→ "
            "可评估 **做多限价单**（回撤至支撑买入）。"
        )
    if near_resist is not None:
        lines.append(
            f"- 价格靠近上方阻力 **{resist_label}**（约 {near_resist:.4f}）→ "
            "可评估 **做空限价单**（反弹至阻力卖出）。"
        )
    if near_support is None and near_resist is None:
        lines.append(
            "- 未识别到极近的支撑/阻力；若仍在通道/区间边界区域，"
            "请结合 K 线摆动高低点与 EMA 自行定价。"
        )
    if direction == "neutral":
        lines.append(
            "- 阶段一 direction=neutral：**§9.0P 默认 wait**（禁止双边边界挂单）。"
        )
    return "\n".join(lines) + "\n"
