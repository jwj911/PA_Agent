"""Controlled override adjudication (§ override arbiter) for PA_Agent.

Override-arbiter cluster split out of :mod:`pa_agent.ai.decision_nodes` (report
§5.2 M3). Holds the deterministic machinery that merges program-computed decision
nodes with the AI's trace and adjudicates the AI's controlled overrides:

- :func:`merge_program_nodes` / :func:`merge_program_nodes_head` — merge program
  nodes into the AI trace by ``node_id`` (program-authoritative vs AI-primary).
- :func:`apply_overrides` — apply the AI's ``node_overrides`` under the locked /
  safety-gate / overridable rule set, writing override trace fields.
- :func:`write_override_trace` — record program originals + AI override on a node.
- Private helpers ``_conservativeness_rank`` / ``_node_id_sort_key`` /
  ``_validate_dir_override`` / ``_sync_always_in_from_24_override`` /
  ``_sync_order_type_from_11_override``.

The cluster depends only on leaf data (the override permission sets from
:mod:`pa_agent.ai.decision_thresholds`) and the trace result layer
(``_coerce_trace_list`` from :mod:`pa_agent.ai.trace_nodes`); ``TRACE_ANSWERS``
is imported call-time inside :func:`apply_overrides` so there is no import cycle
with :mod:`pa_agent.ai.decision_tree`. ``decision_nodes`` re-exports the public
functions, so existing ``from pa_agent.ai.decision_nodes import apply_overrides``
sites keep working byte-for-byte. Behaviour (merge modes, override rule order,
Chinese log strings, node key writes) must stay identical to the original.
"""
from __future__ import annotations

import logging
from typing import Any

from pa_agent.ai.decision_thresholds import (
    AI_PRIMARY_NODES,
    AI_PRIMARY_SUPPLEMENT_NODES,
    LOCKED_NODES,
    OVERRIDABLE_NODES,
    SAFETY_GATE_NODES,
)
from pa_agent.ai.trace_nodes import _coerce_trace_list

logger = logging.getLogger(__name__)

# ── OverrideArbiter ───────────────────────────────────────────────────────────



def _conservativeness_rank(node_id: str, answer: str) -> int:

    """Return conservativeness rank for safety gate ordering (higher = more conservative)."""

    nid = str(node_id).strip()

    ans = str(answer).strip()



    if nid == "10.3":

        return 5 if ans == "否" else 3

    if nid == "14":

        return 5 if ans == "是" else 3

    # order_type dimension (§11 nodes)

    if nid in ("11.1", "11.2", "11.3", "11.4"):

        return 5 if ans == "不下单" else 3

    return 3





def write_override_trace(node: dict[str, Any], override: dict[str, Any]) -> None:

    """Write override trace fields to node (in-place). Records program original values."""

    node["program_answer"] = node.get("answer")

    if "branch" in node:

        node["program_branch"] = node.get("branch")

    node["answer"] = override["answer"]

    if override.get("branch"):

        node["branch"] = override["branch"]

    node["override_reason"] = str(override.get("override_reason", "")).strip()

    node["overridden_by_ai"] = True





def _node_id_sort_key(node_id: str) -> tuple[int, int, str]:
    """Numeric sort key for gate_trace node_id values.

    Converts '1.1' -> (1, 1, '1.1'), '2.3' -> (2, 3, '2.3') so that merged
    program nodes sort into natural chapter-section order regardless of how
    the AI ordered its trace entries.
    """
    parts = str(node_id or "").split(".", 1)
    try:
        major = int(parts[0])
    except (ValueError, IndexError):
        return (999, 999, node_id)
    if len(parts) == 1:
        return (major, 0, node_id)
    sub = parts[1]
    try:
        return (major, int(sub), node_id)
    except ValueError:
        return (major, 999, node_id)


def merge_program_nodes(

    trace: list[dict[str, Any]],

    program_nodes: list[dict[str, Any]],

) -> list[dict[str, Any]]:

    """Merge program nodes into trace by node_id.

    Two merge modes based on node type:

    PROGRAM-AUTHORITATIVE (default):
      Program result replaces the AI node entirely.  Used for §1.1, §2.3, §2.4
      where the program has definitive computed data.

    AI-PRIMARY (AI_PRIMARY_NODES — §1.3 and §2.5):
      If the AI already wrote the node, preserve the AI version (no program append).

    New program nodes not already in the AI trace are inserted in chapter-section
    order (1.1 < 1.2 < 2.3 < 2.5) so the UI renders the correct decision path.
    """

    result = _coerce_trace_list(trace)

    prog_by_id = {n["node_id"]: n for n in program_nodes if isinstance(n, dict) and "node_id" in n}



    replaced_ids: set[str] = set()

    for i, item in enumerate(result):

        if not isinstance(item, dict):

            continue

        nid = str(item.get("node_id", "")).strip()

        if nid not in prog_by_id:

            continue

        if nid in AI_PRIMARY_NODES:

            if nid in AI_PRIMARY_SUPPLEMENT_NODES:
                # AI-primary + program supplement in reason (§1.3 only)
                prog_node = prog_by_id[nid]
                prog_reason = str(prog_node.get("reason", "") or "").strip()
                prog_bar_range = str(prog_node.get("bar_range", "") or "").strip()
                if prog_reason:
                    ai_reason = str(item.get("reason", "") or "").strip()
                    supplement = f"【程序参考数据（{prog_bar_range}）：{prog_reason}】"
                    if supplement not in ai_reason:
                        result[i] = dict(item)
                        result[i]["reason"] = f"{ai_reason} {supplement}".strip()
            # §2.5: keep AI node as-is; program metrics are not appended to reason.

        else:

            # Program-authoritative: program result replaces AI node
            result[i] = prog_by_id[nid]

        replaced_ids.add(nid)



    # Insert new nodes then re-sort by numeric node_id so injected program nodes
    # land in their natural document position (1.1 < 1.2 < 2.3 < 2.5) rather
    # than being appended to the tail of whatever order the AI produced.

    new_nodes = [node for nid, node in prog_by_id.items() if nid not in replaced_ids]

    if new_nodes:

        result.extend(new_nodes)

        result.sort(

            key=lambda x: _node_id_sort_key(str(x.get("node_id", "")))

            if isinstance(x, dict) else (999, 999, "")

        )



    return result


def merge_program_nodes_head(

    trace: list[dict[str, Any]],

    program_nodes: list[dict[str, Any]],

) -> list[dict[str, Any]]:

    """Merge program nodes into trace, placing NEW nodes at the HEAD (before AI nodes).

    Used when gate_result=wait/unknown so the AI's terminating node stays at the end.
    Applies the same AI-PRIMARY / program-authoritative distinction as merge_program_nodes:
    §1.3 and §2.5 preserve the AI version without appending program data to reason.
    """

    # First replace existing entries in-place (same as merge_program_nodes)
    result = _coerce_trace_list(trace)

    prog_by_id = {n["node_id"]: n for n in program_nodes if isinstance(n, dict) and "node_id" in n}

    replaced_ids: set[str] = set()

    for i, item in enumerate(result):

        if not isinstance(item, dict):

            continue

        nid = str(item.get("node_id", "")).strip()

        if nid not in prog_by_id:

            continue

        if nid in AI_PRIMARY_NODES:

            if nid in AI_PRIMARY_SUPPLEMENT_NODES:
                prog_node = prog_by_id[nid]
                prog_reason = str(prog_node.get("reason", "") or "").strip()
                prog_bar_range = str(prog_node.get("bar_range", "") or "").strip()
                if prog_reason:
                    ai_reason = str(item.get("reason", "") or "").strip()
                    supplement = f"【程序参考数据（{prog_bar_range}）：{prog_reason}】"
                    if supplement not in ai_reason:
                        result[i] = dict(item)
                        result[i]["reason"] = f"{ai_reason} {supplement}".strip()

        else:

            result[i] = prog_by_id[nid]

        replaced_ids.add(nid)

    # Sort new nodes by node_id then prepend before the AI's existing nodes so
    # injected program nodes appear in chapter order, while the AI's terminating
    # node (answer=否/等待) remains at the end of the trace.
    new_nodes = sorted(
        [node for nid, node in prog_by_id.items() if nid not in replaced_ids],
        key=lambda x: _node_id_sort_key(str(x.get("node_id", ""))) if isinstance(x, dict) else (999, 999, ""),
    )

    return new_nodes + result





def apply_overrides(

    program_nodes: list[dict[str, Any]],

    node_overrides: Any,

    *,

    out: dict[str, Any],

    stage: str,

) -> list[dict[str, Any]]:

    """Apply controlled overrides to program nodes. Returns final node list with traces.



    Rules (in order):

    1. node_overrides not a list → ignore all

    2. invalid element → skip

    3. locked node → ignore (log)

    4. missing override_reason → reject

    5. safety gate in aggressive direction → reject

    6. §2.3 direction consistency check

    7. valid override → accept, write trace

    """

    from pa_agent.ai.decision_tree import TRACE_ANSWERS



    result = [dict(n) for n in program_nodes]

    prog_ids = {n["node_id"] for n in result if isinstance(n, dict) and "node_id" in n}



    if not isinstance(node_overrides, list):

        return result



    # Build index for fast lookup

    node_index = {n["node_id"]: i for i, n in enumerate(result) if isinstance(n, dict) and "node_id" in n}



    seen_overrides: set[str] = set()



    for ov in node_overrides:

        if not isinstance(ov, dict):

            continue

        node_id = str(ov.get("node_id", "")).strip()

        if not node_id:

            continue

        if node_id not in prog_ids:

            continue

        answer = str(ov.get("answer", "")).strip()

        if answer not in TRACE_ANSWERS:

            continue



        # Take first valid override per node_id

        if node_id in seen_overrides:

            continue

        seen_overrides.add(node_id)



        # Rule 3: locked node

        if node_id in LOCKED_NODES:

            logger.info(

                "apply_overrides: ignoring override for locked node %s (stage=%s)",

                node_id, stage,

            )

            continue



        # Rule 4: missing override_reason

        override_reason = str(ov.get("override_reason", "") or "").strip()

        if not override_reason:

            logger.debug(

                "apply_overrides: rejecting override for %s - missing override_reason",

                node_id,

            )

            continue



        # Rule 5: safety gate direction check

        if node_id in SAFETY_GATE_NODES:

            idx = node_index.get(node_id)

            if idx is not None:

                current_answer = str(result[idx].get("answer", "")).strip()

                current_rank = _conservativeness_rank(node_id, current_answer)

                new_rank = _conservativeness_rank(node_id, answer)

                if new_rank < current_rank:

                    logger.debug(

                        "apply_overrides: rejecting aggressive safety gate override "

                        "for %s (rank %d -> %d is less conservative)",

                        node_id, current_rank, new_rank,

                    )

                    continue



        # Rule 6: §2.3 direction consistency

        if node_id == "2.3":

            branch = str(ov.get("branch", "") or "").strip()

            valid = _validate_dir_override(answer, branch)

            if not valid:

                logger.debug(

                    "apply_overrides: rejecting §2.3 override - "

                    "answer/branch inconsistent: answer=%s branch=%s",

                    answer, branch,

                )

                continue

            # Accept: write trace and sync direction

            idx = node_index.get(node_id)

            if idx is not None:

                write_override_trace(result[idx], ov)

                # Sync direction field

                direction_map = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}

                if branch in direction_map:

                    out["direction"] = direction_map[branch]

            continue



        # Rule 7: accept override for OVERRIDABLE_NODES

        if node_id in OVERRIDABLE_NODES:

            idx = node_index.get(node_id)

            if idx is not None:

                write_override_trace(result[idx], ov)

                # §11 override: sync order_type

                if node_id in ("11.1", "11.2", "11.3", "11.4"):

                    _sync_order_type_from_11_override(out, result[idx], ov)

                # §2.4 override: sync bar_analysis.always_in so the field stays
                # consistent with the final (possibly AI-overridden) §2.4 branch.
                # Without this, bar_analysis.always_in keeps the program's value
                # while direction/gate_trace reflect the AI's override — self-contradiction.
                if node_id == "2.4":

                    _sync_always_in_from_24_override(out, ov)



    return result





def _validate_dir_override(answer: str, branch: str) -> bool:

    """Validate §2.3 answer/branch consistency."""

    if branch in ("bullish", "bearish"):

        return answer == "是"

    elif branch == "neutral":

        return answer == "中性"

    return False  # invalid branch





def _sync_always_in_from_24_override(
    out: dict[str, Any],
    override: dict[str, Any],
) -> None:
    """After §2.4 override accepted, sync bar_analysis.always_in to match the
    AI-overridden branch.  Without this sync, bar_analysis.always_in keeps the
    program's original value while the gate_trace §2.4 node shows the overridden
    branch — a self-contradiction that caused the confusion in the pending record.

    Mapping:
      branch=AIL  → always_in="long"
      branch=AIS  → always_in="short"
      answer=否   → always_in="neutral"
    """
    bar_analysis = out.get("bar_analysis")
    if not isinstance(bar_analysis, dict):
        return

    branch = str(override.get("branch", "") or "").strip()
    answer = str(override.get("answer", "") or "").strip()

    if branch == "AIL":
        bar_analysis["always_in"] = "long"
    elif branch == "AIS":
        bar_analysis["always_in"] = "short"
    elif answer == "否":
        bar_analysis["always_in"] = "neutral"
    # If branch is unrecognised or missing, leave as-is to avoid silent corruption.


def _sync_order_type_from_11_override(

    out: dict[str, Any],

    node: dict[str, Any],

    override: dict[str, Any],

) -> None:

    """After §11 override accepted, sync decision.order_type if not 不下单."""

    decision = out.get("decision")

    if not isinstance(decision, dict):

        return



    new_answer = str(override.get("answer", "")).strip()

    if new_answer != "是":

        return



    node_id = str(node.get("node_id", ""))

    node_method_map = {

        "11.1": "市价单",

        "11.2": "突破单",

        "11.3": "限价单",

        "11.4": "限价单",

    }

    method = node_method_map.get(node_id)

    if not method or decision.get("order_type") == "不下单":

        return



    existing = str(decision.get("order_type") or "").strip()

    has_basis = bool(

        decision.get("entry_basis_bar") and decision.get("entry_basis_extreme")

    )

    # Mirror judge_section11 breakout_fallback_to_limit: §11.2 defaults to 突破单,

    # but without basis fields the schema rejects null entry_basis_*. Preserve an

    # explicit 限价单/市价单 plan (e.g. §9.0P planned limit) instead of forcing 突破单.

    if method == "突破单" and not has_basis:

        if existing in ("限价单", "市价单"):

            return

        method = "限价单"



    decision["order_type"] = method
