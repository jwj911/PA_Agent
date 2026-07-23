"""Sanitized export and offline evaluation pipeline for experience cases."""

from __future__ import annotations

import hmac
import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from pa_agent.data.base import KlineBar
from pa_agent.records.experience_eval import (
    EXPERIENCE_FEATURE_VERSION,
    ExperienceEvalCase,
    ExperienceEvalDataset,
    ExperienceEvalSplit,
    apply_fixed_split,
    build_fixed_split,
    evaluate_rankings,
)
from pa_agent.records.experience_similarity import score_kline_similarity

EXPERIENCE_ANNOTATION_SCHEMA = "pa-agent.experience-annotation.v1"
EXPERIENCE_REPORT_SCHEMA = "pa-agent.experience-eval-report.v1"
_TS_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})")


@dataclass(frozen=True, slots=True)
class _CatalogCase:
    case_id: str
    instrument_id: str
    timeframe: str
    cycle_position: str
    direction: str
    patterns: tuple[str, ...]
    outcome: str
    timestamp_key: str
    content: dict[str, Any]

    def sanitized_metadata(self, candidate_ids: tuple[str, ...]) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "instrument_id": self.instrument_id,
            "timeframe": self.timeframe,
            "cycle_position": self.cycle_position,
            "direction": self.direction,
            "patterns": list(self.patterns),
            "outcome": self.outcome,
            "candidate_count": len(candidate_ids),
            "candidate_ids": list(candidate_ids),
            "similarity_fallback": _bars_from_content(self.content) is None,
        }


def export_annotation_template(
    experience_dir: Path,
    *,
    salt: str,
) -> dict[str, Any]:
    """Build a deterministic, sanitized human-labeling template."""
    catalog = _load_catalog(experience_dir, salt=_validated_salt(salt))
    metadata = _sanitized_catalog(catalog)
    return {
        "schema": EXPERIENCE_ANNOTATION_SCHEMA,
        "feature_version": EXPERIENCE_FEATURE_VERSION,
        "catalog_digest": _catalog_digest(metadata),
        "cases": [
            {
                **case,
                "reviewed": False,
                "relevant_ids": [],
            }
            for case in metadata
        ],
    }


def evaluate_annotated_experience(
    experience_dir: Path,
    annotations: dict[str, Any],
    *,
    salt: str,
    evaluation_fraction: float = 0.2,
    k: int = 3,
) -> tuple[ExperienceEvalDataset, ExperienceEvalSplit, dict[str, Any]]:
    """Validate labels, build a fixed split, and compare legacy/new rankings."""
    catalog = _load_catalog(experience_dir, salt=_validated_salt(salt))
    metadata = _sanitized_catalog(catalog)
    annotation_cases = _validate_annotations(annotations, metadata)
    catalog_by_id = {case.case_id: case for case in catalog}

    dataset_cases: list[ExperienceEvalCase] = []
    for item in annotation_cases:
        case = catalog_by_id[item["case_id"]]
        dataset_cases.append(
            ExperienceEvalCase(
                case_id=case.case_id,
                instrument_id=case.instrument_id,
                timeframe=case.timeframe,
                cycle_position=case.cycle_position,
                direction=case.direction,
                patterns=case.patterns,
                relevant_ids=tuple(item["relevant_ids"]),
                candidate_count=item["candidate_count"],
                similarity_fallback=bool(item["similarity_fallback"]),
            )
        )
    dataset = ExperienceEvalDataset(
        feature_version=EXPERIENCE_FEATURE_VERSION,
        cases=tuple(dataset_cases),
    )
    split = build_fixed_split(dataset, evaluation_fraction=evaluation_fraction)
    _train, evaluation = apply_fixed_split(dataset, split)
    legacy_rankings, similarity_rankings, similarity_scores = _rank_catalog(catalog)
    evaluation_ids = {case.case_id for case in evaluation.cases}
    evaluation_legacy = {
        case_id: ranking
        for case_id, ranking in legacy_rankings.items()
        if case_id in evaluation_ids
    }
    evaluation_similarity = {
        case_id: ranking
        for case_id, ranking in similarity_rankings.items()
        if case_id in evaluation_ids
    }
    evaluation_scores = {
        case_id: scores
        for case_id, scores in similarity_scores.items()
        if case_id in evaluation_ids
    }
    legacy_metrics = evaluate_rankings(evaluation, evaluation_legacy, k=k)
    similarity_metrics = evaluate_rankings(
        evaluation,
        evaluation_similarity,
        k=k,
        baseline_rankings=evaluation_legacy,
        scores=evaluation_scores,
    )
    report = {
        "schema": EXPERIENCE_REPORT_SCHEMA,
        "feature_version": EXPERIENCE_FEATURE_VERSION,
        "dataset_digest": split.dataset_digest,
        "split": split.to_dict(),
        "k": k,
        "case_count": len(dataset.cases),
        "instrument_group_count": len({case.instrument_id for case in dataset.cases}),
        "train_case_count": len(split.train_case_ids),
        "evaluation_case_count": len(split.evaluation_case_ids),
        "outcome_counts": _count_values(case.outcome for case in catalog),
        "cycle_position_counts": _count_values(case.cycle_position for case in catalog),
        "legacy_metrics": legacy_metrics.to_dict(),
        "similarity_metrics": similarity_metrics.to_dict(),
        "metric_delta": {
            "recall_at_k": similarity_metrics.recall_at_k - legacy_metrics.recall_at_k,
            "ndcg_at_k": similarity_metrics.ndcg_at_k - legacy_metrics.ndcg_at_k,
        },
        "online_sorting_changed": False,
    }
    return dataset, split, report


def _load_catalog(experience_dir: Path, *, salt: bytes) -> tuple[_CatalogCase, ...]:
    root = Path(experience_dir)
    paths = sorted(root.glob("*/*_cases/*.json"), key=lambda path: path.as_posix())
    if not paths:
        raise ValueError("experience directory contains no JSON cases")

    cases: list[_CatalogCase] = []
    for index, path in enumerate(paths, start=1):
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"experience case {index} is not readable JSON") from exc
        if not isinstance(content, dict):
            raise ValueError(f"experience case {index} must be a JSON object")

        relative_key = path.relative_to(root).as_posix()
        cycle_position = path.parent.parent.name.strip()
        outcome = _outcome_from_directory(path.parent.name)
        symbol = _required_text(
            _first_value(
                content,
                ("meta", "symbol"),
                ("record", "meta", "symbol"),
                ("symbol",),
            ),
            f"experience case {index} symbol",
        )
        timeframe = _required_text(
            _first_value(
                content,
                ("meta", "timeframe"),
                ("record", "meta", "timeframe"),
                ("timeframe",),
            ),
            f"experience case {index} timeframe",
        )
        direction = _required_text(
            _first_value(
                content,
                ("stage1_diagnosis", "direction"),
                ("record", "stage1_diagnosis", "direction"),
                ("direction",),
            ),
            f"experience case {index} direction",
        )
        raw_patterns = _first_value(
            content,
            ("stage1_diagnosis", "detected_patterns"),
            ("record", "stage1_diagnosis", "detected_patterns"),
            ("detected_patterns",),
        )
        patterns = _string_tuple(raw_patterns, f"experience case {index} patterns")
        cases.append(
            _CatalogCase(
                case_id=_opaque_id("case", relative_key, salt),
                instrument_id=_opaque_id("instrument", symbol, salt),
                timeframe=timeframe,
                cycle_position=_required_text(cycle_position, f"experience case {index} cycle"),
                direction=direction,
                patterns=patterns,
                outcome=outcome,
                timestamp_key=_timestamp_key(path.name),
                content=content,
            )
        )
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("opaque experience case ids are not unique")
    return tuple(cases)


def _sanitized_catalog(catalog: tuple[_CatalogCase, ...]) -> list[dict[str, Any]]:
    by_cycle: dict[str, tuple[str, ...]] = {}
    for case in catalog:
        by_cycle.setdefault(case.cycle_position, ())
        by_cycle[case.cycle_position] = (
            *by_cycle[case.cycle_position],
            case.case_id,
        )
    return [
        case.sanitized_metadata(
            tuple(
                case_id
                for case_id in sorted(by_cycle[case.cycle_position])
                if case_id != case.case_id
            )
        )
        for case in catalog
    ]


def _validate_annotations(
    annotations: dict[str, Any],
    metadata: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(annotations, dict):
        raise ValueError("experience annotations must be an object")
    if annotations.get("schema") != EXPERIENCE_ANNOTATION_SCHEMA:
        raise ValueError("unsupported experience annotation schema")
    if annotations.get("feature_version") != EXPERIENCE_FEATURE_VERSION:
        raise ValueError("experience annotation feature version mismatch")
    expected_digest = _catalog_digest(metadata)
    if annotations.get("catalog_digest") != expected_digest:
        raise ValueError("experience annotation catalog digest mismatch")
    values = annotations.get("cases")
    if not isinstance(values, list):
        raise ValueError("experience annotation cases must be an array")

    expected = {case["case_id"]: case for case in metadata}
    actual: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("experience annotation case must be an object")
        case_id = str(value.get("case_id", "")).strip()
        if case_id not in expected or case_id in actual:
            raise ValueError("experience annotation case ids do not match catalog")
        for field in expected[case_id]:
            if value.get(field) != expected[case_id][field]:
                raise ValueError("experience annotation metadata was modified")
        if value.get("reviewed") is not True:
            raise ValueError("every experience annotation case must be reviewed")
        relevant_ids = value.get("relevant_ids")
        if not isinstance(relevant_ids, list) or not all(
            isinstance(item, str) and item for item in relevant_ids
        ):
            raise ValueError("relevant_ids must be an array of opaque ids")
        normalized_relevant = list(dict.fromkeys(relevant_ids))
        candidates = set(expected[case_id]["candidate_ids"])
        if not set(normalized_relevant).issubset(candidates):
            raise ValueError("relevant_ids must be selected from candidate_ids")
        actual[case_id] = {**value, "relevant_ids": normalized_relevant}
    if set(actual) != set(expected):
        raise ValueError("experience annotations must cover every catalog case")
    return [actual[case["case_id"]] for case in metadata]


def _rank_catalog(
    catalog: tuple[_CatalogCase, ...],
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[float]],
]:
    legacy_rankings: dict[str, list[str]] = {}
    similarity_rankings: dict[str, list[str]] = {}
    similarity_scores: dict[str, list[float]] = {}
    for query in catalog:
        candidates = [
            candidate
            for candidate in catalog
            if candidate.case_id != query.case_id
            and candidate.cycle_position == query.cycle_position
        ]
        bars = _bars_from_content(query.content)

        def context_score(
            candidate: _CatalogCase,
            query_case: _CatalogCase = query,
        ) -> int:
            score = 2 if candidate.direction.lower() == query_case.direction.lower() else 0
            score += len(
                {pattern.lower() for pattern in query_case.patterns}.intersection(
                    pattern.lower() for pattern in candidate.patterns
                )
            )
            return score

        def similarity(
            candidate: _CatalogCase,
            query_bars: tuple[KlineBar, ...] | None = bars,
        ) -> float:
            if query_bars is None:
                return -1.0
            value = score_kline_similarity(query_bars, candidate.content)
            return value if value is not None else -1.0

        legacy = sorted(
            candidates,
            key=lambda candidate: (
                context_score(candidate),
                candidate.timestamp_key,
                candidate.case_id,
            ),
            reverse=True,
        )
        ranked = sorted(
            candidates,
            key=lambda candidate: (
                context_score(candidate),
                similarity(candidate),
                candidate.timestamp_key,
                candidate.case_id,
            ),
            reverse=True,
        )
        legacy_rankings[query.case_id] = [candidate.case_id for candidate in legacy]
        similarity_rankings[query.case_id] = [candidate.case_id for candidate in ranked]
        similarity_scores[query.case_id] = [
            value for candidate in ranked if (value := similarity(candidate)) >= 0.0
        ]
    return legacy_rankings, similarity_rankings, similarity_scores


def _bars_from_content(content: dict[str, Any]) -> tuple[KlineBar, ...] | None:
    raw = content.get("kline_data")
    if not isinstance(raw, list):
        record = content.get("record")
        raw = record.get("kline_data") if isinstance(record, dict) else None
    if not isinstance(raw, list) or len(raw) < 3:
        return None
    bars: list[KlineBar] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            return None
        try:
            values = tuple(float(item[name]) for name in ("open", "high", "low", "close"))
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in values):
            return None
        open_, high, low, close = values
        bars.append(
            KlineBar(
                seq=index + 1,
                ts_open=0,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=0,
            )
        )
    return tuple(bars)


def _first_value(content: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value: Any = content
        for key in path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            if value is not None:
                return value
    return None


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _validated_salt(value: str) -> bytes:
    salt = str(value or "").encode("utf-8")
    if len(salt) < 16:
        raise ValueError("experience evaluation salt must be at least 16 bytes")
    return salt


def _opaque_id(prefix: str, value: str, salt: bytes) -> str:
    digest = hmac.new(salt, value.encode("utf-8"), sha256).hexdigest()
    return f"{prefix}-{digest[:24]}"


def _outcome_from_directory(name: str) -> str:
    if name == "success_cases":
        return "success"
    if name == "failure_cases":
        return "failure"
    raise ValueError("experience case directory must declare success or failure")


def _timestamp_key(filename: str) -> str:
    match = _TS_PATTERN.search(filename)
    if match is None:
        raise ValueError("experience case filename must contain a timestamp")
    return match.group(1)


def _catalog_digest(metadata: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        metadata,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


__all__ = [
    "EXPERIENCE_ANNOTATION_SCHEMA",
    "EXPERIENCE_REPORT_SCHEMA",
    "evaluate_annotated_experience",
    "export_annotation_template",
]
