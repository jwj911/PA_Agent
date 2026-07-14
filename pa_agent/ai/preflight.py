"""Deterministic pre-AI data quality gate for the decision node engine.

Near stdlib-only helper (only ``BAR_COUNT_THRESHOLD`` from the sibling pure-data
module :mod:`pa_agent.ai.decision_thresholds`) split out of
:mod:`pa_agent.ai.decision_nodes` (report §5.2 M3). ``check_preflight_data`` is a
pure function (no AI calls, no side effects beyond a warning log) that guards
Stage 1 against empty / invalid / insufficient K-line data. ``decision_nodes``
re-exports :class:`PreflightResult` and :func:`check_preflight_data` so existing
``from pa_agent.ai.decision_nodes import ...`` sites (orchestrator, tests) keep
working byte-for-byte.

Behaviour must stay identical to the original: the three failed_check tokens
(``bars_empty_or_bad_ohlc`` / ``bar_count_lt_20`` / ``indicators_all_nan``) and
their Chinese reason strings are consumed downstream.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from pa_agent.ai.decision_thresholds import BAR_COUNT_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreflightResult:
    """Result of preflight data gate check."""

    ok: bool
    reason: str
    failed_check: str | None  # bars_empty_or_bad_ohlc / bar_count_lt_20 / indicators_all_nan


def check_preflight_data(frame: Any) -> PreflightResult:
    """Pre-AI call deterministic data quality gate (pure function, no AI calls).

    Checks in order:
    1. frame/bars non-empty and OHLC valid
    2. bar count >= 20
    3. EMA20/ATR14 not all NaN

    Returns PreflightResult(ok=False, ...) conservatively on any doubt.
    """
    try:
        return _check_preflight_data_inner(frame)
    except Exception as exc:  # noqa: BLE001
        logger.warning("check_preflight_data: unexpected exception: %s", exc)
        return PreflightResult(
            ok=False,
            reason=f"数据校验时发生异常：{exc}",
            failed_check="bars_empty_or_bad_ohlc",
        )


def _check_preflight_data_inner(frame: Any) -> PreflightResult:
    """Inner implementation without exception guard."""
    # ── Check 1: frame and bars non-empty, OHLC valid ────────────────────────
    if frame is None:
        return PreflightResult(
            ok=False,
            reason="frame 为空，无法分析。",
            failed_check="bars_empty_or_bad_ohlc",
        )

    bars = getattr(frame, "bars", None)
    if not bars:
        return PreflightResult(
            ok=False,
            reason="K线序列为空，无法分析。",
            failed_check="bars_empty_or_bad_ohlc",
        )

    # Validate each bar's OHLC
    for bar in bars:
        try:
            o = float(getattr(bar, "open", None))
            h = float(getattr(bar, "high", None))
            lo = float(getattr(bar, "low", None))
            c = float(getattr(bar, "close", None))
        except (TypeError, ValueError):
            return PreflightResult(
                ok=False,
                reason="存在K线 OHLC 字段缺失或非数值，数据不合法。",
                failed_check="bars_empty_or_bad_ohlc",
            )

        if not (math.isfinite(o) and math.isfinite(h) and math.isfinite(lo) and math.isfinite(c)):
            return PreflightResult(
                ok=False,
                reason="存在K线 OHLC 含 NaN/Inf 等非有限数值。",
                failed_check="bars_empty_or_bad_ohlc",
            )

        if h < lo:
            return PreflightResult(
                ok=False,
                reason=f"存在K线 high({h}) < low({lo})，数据不合法。",
                failed_check="bars_empty_or_bad_ohlc",
            )

    # ── Check 2: bar count >= 20 ──────────────────────────────────────────────
    try:
        n = max(int(getattr(b, "seq", 0)) for b in bars)
    except (TypeError, ValueError):
        return PreflightResult(
            ok=False,
            reason="无法读取K线 seq 字段，无法计算K线数量。",
            failed_check="bars_empty_or_bad_ohlc",
        )

    if n < BAR_COUNT_THRESHOLD:
        return PreflightResult(
            ok=False,
            reason=f"已收盘K线数量 {n} 根不足 {BAR_COUNT_THRESHOLD} 根，数据不足以分析。",
            failed_check="bar_count_lt_20",
        )

    # ── Check 3: EMA20/ATR14 at least one non-NaN ────────────────────────────
    indicators = getattr(frame, "indicators", None)
    if indicators is not None:
        ema20 = getattr(indicators, "ema20", ())
        atr14 = getattr(indicators, "atr14", ())

        def _all_nan(seq: Any) -> bool:
            try:
                return all(math.isnan(float(v)) for v in seq) if seq else True
            except (TypeError, ValueError):
                return True

        if _all_nan(ema20) and _all_nan(atr14):
            return PreflightResult(
                ok=False,
                reason="EMA20 与 ATR14 全为 NaN，指标预热不足，无法分析。",
                failed_check="indicators_all_nan",
            )

    return PreflightResult(ok=True, reason="", failed_check=None)
