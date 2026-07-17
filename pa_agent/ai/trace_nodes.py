"""Trace-node result types and builders for the decision node engine.

Near-stdlib helpers split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). This module hosts the shared *result layer* every section-judge
produces and consumes:

- :class:`NodeFill` — the frozen intermediate representation a judge returns.
- :func:`_coerce_dict` / :func:`_coerce_trace_list` — defensive coercion of
  loosely-typed AI JSON into dicts / trace-node lists.
- :func:`_node_label` / :func:`build_program_trace_node` — resolve a node's
  question text and convert a :class:`NodeFill` into a valid decision-trace
  dict (question pulled lazily from the decision tree).

Extracting this leaf first breaks the import cycle that would otherwise appear
when the section-judges are pulled into their own modules: judges import
``NodeFill`` from here instead of from ``decision_nodes``. ``decision_nodes``
re-exports these names, so existing ``from pa_agent.ai.decision_nodes import
NodeFill`` sites keep working byte-for-byte.

Behaviour must stay identical to the originals (trace dict keys, coercion
tolerance, lazy ``node_label`` lookup fallback). The two builders reach into
:mod:`pa_agent.ai.decision_tree` via a call-time import, so this module has no
import-time project dependency (only stdlib ``logging`` / ``dataclasses`` /
``typing``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _coerce_dict(value: Any) -> dict[str, Any]:
    """Return *value* when it is a dict; otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def _coerce_trace_list(trace: Any) -> list[dict[str, Any]]:
    """Keep only dict trace nodes; tolerate non-list or string elements from AI JSON."""
    if not isinstance(trace, list):
        return []
    return [item for item in trace if isinstance(item, dict)]


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NodeFill:
    """Intermediate representation of a program-filled trace node."""

    node_id: str
    answer: str  # ∈ TRACE_ANSWERS: 是/否/中性/等待/不适用
    reason: str  # non-empty
    bar_range: str  # like "K20-K1" / "K1" / "不适用"
    branch: str | None = None
    section: str | None = None


# ── Helper: node label ────────────────────────────────────────────────────────


def _node_label(node_id: str) -> str:
    """Get human-readable question text for a node id from the decision tree."""
    try:
        from pa_agent.ai.decision_tree import node_label as _nl

        return _nl(node_id)
    except Exception:
        logger.debug("node_label lookup failed for %s", node_id, exc_info=True)
        return node_id


def build_program_trace_node(fill: NodeFill, *, tree: Any = None) -> dict[str, Any]:
    """Convert a NodeFill to a valid trace dict (question from decision tree node_label)."""
    try:
        from pa_agent.ai.decision_tree import node_label as _nl

        question = _nl(fill.node_id, tree)
    except Exception:
        question = fill.node_id

    node: dict[str, Any] = {
        "node_id": fill.node_id,
        "question": question,
        "answer": fill.answer,
        "reason": fill.reason,
        "bar_range": fill.bar_range,
        "skipped": False,
    }
    if fill.branch:
        node["branch"] = fill.branch
    if fill.section:
        node["section"] = fill.section
    return node
