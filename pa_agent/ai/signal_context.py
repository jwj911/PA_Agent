"""Signal-bar / limit-order context helpers for the decision node engine.

Signal-context helper cluster split out of :mod:`pa_agent.ai.decision_nodes`
(report §5.2 M3). These three deterministic helpers give
:meth:`DecisionNodeEngine.apply_stage2` its §9 context: where the signal bar
sits and whether the order is a pending limit plan that does not require a
closed signal bar:

- :func:`_get_signal_seq` — locate the signal-bar sequence
  (prefer ``bar_analysis.signal_bar.bar``, else K1).
- :func:`has_background_limit_path` — True when ``decision_trace`` records
  §9.0P=是 (background-driven limit path).
- :func:`is_planned_limit_order` — True when the order is a pending limit plan
  without requiring a closed signal bar.

The cluster is essentially stdlib-only (``logging`` / ``typing.Any``); the sole
project touch, ``parse_k_seq``, is a call-time import inside
:func:`_get_signal_seq` (``pa_agent.util.price_tick`` imports no project
modules), so ``signal_context`` ← ``decision_nodes`` has no import cycle.
``decision_nodes`` re-exports these names, so existing
``from pa_agent.ai.decision_nodes import is_planned_limit_order`` sites keep
working byte-for-byte. Behaviour (§9.0P detection, planned-limit predicate
branches, default K1 fallback) must stay identical to the originals.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_signal_seq(out: dict[str, Any], bars: Any) -> int:

    """Locate signal bar seq: prefer bar_analysis.signal_bar.bar, else K1."""

    try:

        from pa_agent.util.price_tick import parse_k_seq

        bar_analysis = out.get("bar_analysis")

        if isinstance(bar_analysis, dict):

            signal_bar = bar_analysis.get("signal_bar")

            if isinstance(signal_bar, dict):

                bar_str = signal_bar.get("bar")

                if bar_str:

                    seq = parse_k_seq(bar_str)

                    if seq is not None and seq >= 1:

                        return seq

    except Exception:

        logger.debug("signal bar seq parse failed", exc_info=True)

    return 1  # default to K1


def has_background_limit_path(out: dict[str, Any]) -> bool:
    """True when decision_trace records §9.0P=是 (background-driven limit path)."""
    trace = out.get("decision_trace")
    if not isinstance(trace, list):
        return False
    for item in trace:
        if not isinstance(item, dict):
            continue
        if str(item.get("node_id", "")).strip() != "9.0P":
            continue
        return str(item.get("answer", "") or "").strip() == "是"
    return False


def is_planned_limit_order(out: dict[str, Any]) -> bool:
    """True when order is a pending limit plan without requiring a closed signal bar."""
    decision = out.get("decision")
    if not isinstance(decision, dict) or decision.get("order_type") != "限价单":
        return False
    if has_background_limit_path(out):
        return True
    bar_analysis = out.get("bar_analysis")
    if not isinstance(bar_analysis, dict):
        return False
    entry_bar = bar_analysis.get("entry_bar")
    signal_bar = bar_analysis.get("signal_bar")
    if not isinstance(entry_bar, dict) or not isinstance(signal_bar, dict):
        return False
    strength = str(entry_bar.get("strength", "") or "").strip().lower()
    freshness = str(entry_bar.get("freshness", "") or "").strip().lower()
    pending = (
        strength == "not_triggered"
        or entry_bar.get("bar") is None
        or freshness == "pending"
    )
    if not pending:
        return False
    quality = str(signal_bar.get("quality", "") or "").strip().lower()
    pattern = str(signal_bar.get("pattern", "") or "").strip().lower()
    if signal_bar.get("bar") is None and quality in ("invalid", "weak"):
        return True
    return quality == "weak" and pattern in (
        "",
        "none",
        "tr_boundary",
        "breakout_pullback",
        "h1",
        "h2",
        "l1",
        "l2",
        "wedge",
        "mtr",
        "trendline",
    )
