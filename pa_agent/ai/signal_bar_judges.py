"""Signal-bar section judges (§9.1/§9.2/§9.3/§9.5) for the decision node engine.

Section-judge cluster split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). These four deterministic judges evaluate the *signal bar* once its
sequence is located, filling the §9 nodes:

- :func:`judge_signal_bar_closed` (§9.1) — signal bar is always closed.
- :func:`judge_signal_bar_direction` (§9.2) — bar_type vs order direction
  consistency (outside bars demoted to a cautionary "weak" set).
- :func:`judge_signal_bar_length` (§9.3) — overlong-bar check against
  ``SIGNAL_BAR_LONG_ATR_RATIO``.
- :func:`judge_follow_through` (§9.5) — follow_through_1_2 mapping.

This is the first *judge* cluster extracted after the shared result layer
(``trace_nodes``): these judges depend only on leaf modules — ``NodeFill``
(from :mod:`pa_agent.ai.trace_nodes`) and ``SIGNAL_BAR_LONG_ATR_RATIO`` (from
:mod:`pa_agent.ai.decision_thresholds`) — so pulling them here creates no import
cycle. ``decision_nodes`` re-exports these names, so existing
``from pa_agent.ai.decision_nodes import judge_signal_bar_*`` sites keep working
byte-for-byte. Behaviour (answers, Chinese reason strings, bar_range) must stay
identical to the originals.
"""
from __future__ import annotations

from typing import Any

from pa_agent.ai.decision_thresholds import SIGNAL_BAR_LONG_ATR_RATIO
from pa_agent.ai.trace_nodes import NodeFill


def judge_signal_bar_closed(sig: int, frame: Any) -> NodeFill:

    """§9.1: signal bar is always closed (all bars in KlineFrame are closed)."""

    return NodeFill(

        node_id="9.1",

        answer="是",

        reason=f"K{sig}为已收盘K线（KlineFrame内所有K线均已收盘），可作为信号棒。",

        bar_range=f"K{sig}",

    )





# §9.2 direction consistency sets
# Outside bars are intentionally excluded from the primary "consistent" set
# because 文件16 §外包棒 states:
#   "外包棒是K线级别的凝滞区——在外包棒突破上进场几乎从来都不明智"
# They are moved to a separate "weak" set that earns answer=否 with a warning,
# so AI can still decide to override with node_overrides if context warrants.
_LONG_BAR_TYPES: frozenset[str] = frozenset({"trend_bull"})
_SHORT_BAR_TYPES: frozenset[str] = frozenset({"trend_bear"})
# Outside bars in the direction: weak/ambiguous — flagged as "否" with caution note
_LONG_BAR_TYPES_WEAK: frozenset[str] = frozenset({"outside_bull"})
_SHORT_BAR_TYPES_WEAK: frozenset[str] = frozenset({"outside_bear"})


def judge_signal_bar_direction(
    sig: int,
    order_direction: str | None,
    features: dict[int, Any],
) -> NodeFill:
    """§9.2: check signal bar direction consistency with order direction.

    Classification:
      trend_bull / trend_bear → 是 (consistent, strong signal bar)
      outside_bull / outside_bear → 否 with warning (outside bar = K-line
        level congestion zone; Al Brooks: "almost never wise to enter on
        outside bar breakout")
      doji / inside / other / unknown → 否 (not directionally consistent)

    AI can use node_overrides to accept an outside_bull/bear signal bar if
    the context strongly warrants it (e.g. breakout continuation in spike).
    """
    if not order_direction or order_direction not in ("做多", "做空"):
        return NodeFill(
            node_id="9.2",
            answer="不适用",
            reason="无交易计划方向（order_direction缺失），§9.2不适用。",
            bar_range="不适用",
        )

    feat = features.get(sig)
    bar_type = str(feat.bar_type) if feat else "unknown"

    if order_direction == "做多":
        if bar_type in _LONG_BAR_TYPES:
            answer = "是"
            reason = (
                f"K{sig} bar_type={bar_type}，属于做多强信号棒类型"
                f"（{sorted(_LONG_BAR_TYPES)}），方向一致。"
            )
        elif bar_type in _LONG_BAR_TYPES_WEAK:
            answer = "否"
            reason = (
                f"K{sig} bar_type={bar_type}（外包棒），方向偏多但"
                "外包棒是K线级别的凝滞区，直接追外包棒突破风险高；"
                "建议等待后续确认棒或在 node_overrides 中说明理由后覆盖。"
            )
        else:
            answer = "否"
            reason = (
                f"K{sig} bar_type={bar_type}，"
                f"做多强信号棒类型={sorted(_LONG_BAR_TYPES)}，"
                "方向不一致。"
            )
    else:  # 做空
        if bar_type in _SHORT_BAR_TYPES:
            answer = "是"
            reason = (
                f"K{sig} bar_type={bar_type}，属于做空强信号棒类型"
                f"（{sorted(_SHORT_BAR_TYPES)}），方向一致。"
            )
        elif bar_type in _SHORT_BAR_TYPES_WEAK:
            answer = "否"
            reason = (
                f"K{sig} bar_type={bar_type}（外包棒），方向偏空但"
                "外包棒是K线级别的凝滞区，直接追外包棒突破风险高；"
                "建议等待后续确认棒或在 node_overrides 中说明理由后覆盖。"
            )
        else:
            answer = "否"
            reason = (
                f"K{sig} bar_type={bar_type}，"
                f"做空强信号棒类型={sorted(_SHORT_BAR_TYPES)}，"
                "方向不一致。"
            )

    return NodeFill(
        node_id="9.2",
        answer=answer,
        reason=reason,
        bar_range=f"K{sig}",
    )





def judge_signal_bar_length(sig: int, features: dict[int, Any]) -> NodeFill:

    """§9.3: check if signal bar is overlong (range_atr_ratio > 2.0)."""

    feat = features.get(sig)

    ratio = feat.range_atr_ratio if feat else None



    if ratio is None:

        answer = "是"

        reason = (

            f"K{sig} range_atr_ratio无法计算（ATR预热不足或range=0），"

            "按潜在过长保守处理→是。"

        )

    elif ratio > SIGNAL_BAR_LONG_ATR_RATIO:

        answer = "是"

        reason = (

            f"K{sig} range_atr_ratio={ratio:.3f} > {SIGNAL_BAR_LONG_ATR_RATIO}，"

            "信号棒过长，止损可能超过ATR 2倍，需用资金管理止损或放弃。"

        )

    else:

        answer = "否"

        reason = (

            f"K{sig} range_atr_ratio={ratio:.3f} ≤ {SIGNAL_BAR_LONG_ATR_RATIO}，"

            "信号棒长度在可接受范围内，不过长。"

        )



    return NodeFill(

        node_id="9.3",

        answer=answer,

        reason=reason,

        bar_range=f"K{sig}",

    )





# ── FollowThroughJudge ────────────────────────────────────────────────────────



def judge_follow_through(sig: int, features: dict[int, Any]) -> NodeFill:

    """§9.5: follow_through_1_2 mapping."""

    feat = features.get(sig)

    ft = feat.follow_through_1_2 if feat else None



    _FT_MAP = {

        "yes": "是",

        "failed": "否",

        "no": "否",

        "pending": "等待",

    }



    if ft in _FT_MAP:

        answer = _FT_MAP[ft]

        reason = f"K{sig}的follow_through_1_2={ft!r}→{answer}。"

    else:

        answer = "等待"

        reason = f"K{sig}的follow_through_1_2={ft!r}（缺失或未知），保守取等待。"



    # bar_range covers signal bar and subsequent bars

    if sig > 1:

        bar_range = f"K{sig}-K1"

    else:

        bar_range = "K1"



    return NodeFill(

        node_id="9.5",

        answer=answer,

        reason=reason,

        bar_range=bar_range,

    )
