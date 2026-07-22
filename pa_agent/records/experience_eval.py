"""Offline ranking contracts and metrics for the experience library.

The evaluator is deliberately separate from :class:`ExperienceReader`. It
consumes sanitized ranking outputs, so offline experiments cannot silently
change the online retrieval formula or persist raw market data.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

EXPERIENCE_EVAL_SCHEMA = "pa-agent.experience-eval.v1"
EXPERIENCE_FEATURE_VERSION = "kline-geometry.v1"


@dataclass(frozen=True, slots=True)
class ExperienceEvalCase:
    """One sanitized retrieval query and its manually labeled relevant ids."""

    case_id: str
    instrument_id: str
    timeframe: str
    cycle_position: str
    direction: str
    patterns: tuple[str, ...]
    relevant_ids: tuple[str, ...]
    candidate_count: int
    similarity_fallback: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "case_id",
            "instrument_id",
            "timeframe",
            "cycle_position",
            "direction",
        ):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValueError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        patterns = tuple(dict.fromkeys(str(item).strip() for item in self.patterns if str(item).strip()))
        relevant_ids = tuple(
            dict.fromkeys(str(item).strip() for item in self.relevant_ids if str(item).strip())
        )
        if not patterns:
            patterns = ()
        try:
            candidate_count = int(self.candidate_count)
        except (TypeError, ValueError) as exc:
            raise ValueError("candidate_count must be an integer") from exc
        if candidate_count < 0:
            raise ValueError("candidate_count must be non-negative")
        if candidate_count < len(relevant_ids):
            raise ValueError("candidate_count cannot be smaller than relevant_ids")
        object.__setattr__(self, "patterns", patterns)
        object.__setattr__(self, "relevant_ids", relevant_ids)
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "similarity_fallback", bool(self.similarity_fallback))

    def to_dict(self) -> dict[str, Any]:
        """Return only sanitized, JSON-compatible case metadata."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> ExperienceEvalCase:
        """Validate and construct a case loaded from a dataset."""
        if not isinstance(value, dict):
            raise ValueError("experience evaluation case must be an object")
        required = {
            "case_id",
            "instrument_id",
            "timeframe",
            "cycle_position",
            "direction",
            "patterns",
            "relevant_ids",
            "candidate_count",
        }
        missing = sorted(required.difference(value))
        if missing:
            raise ValueError(f"experience evaluation case missing fields: {', '.join(missing)}")
        if not isinstance(value["patterns"], list) or not isinstance(value["relevant_ids"], list):
            raise ValueError("patterns and relevant_ids must be arrays")
        return cls(
            case_id=value["case_id"],
            instrument_id=value["instrument_id"],
            timeframe=value["timeframe"],
            cycle_position=value["cycle_position"],
            direction=value["direction"],
            patterns=tuple(value["patterns"]),
            relevant_ids=tuple(value["relevant_ids"]),
            candidate_count=value["candidate_count"],
            similarity_fallback=value.get("similarity_fallback", False),
        )


@dataclass(frozen=True, slots=True)
class ExperienceEvalDataset:
    """Versioned collection of sanitized ranking queries."""

    feature_version: str
    cases: tuple[ExperienceEvalCase, ...]
    schema: str = EXPERIENCE_EVAL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EXPERIENCE_EVAL_SCHEMA:
            raise ValueError(f"unsupported experience evaluation schema: {self.schema!r}")
        if not str(self.feature_version).strip():
            raise ValueError("feature_version must be non-empty")
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("experience evaluation case_id values must be unique")

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic dataset envelope."""
        return {
            "schema": self.schema,
            "feature_version": self.feature_version,
            "cases": [case.to_dict() for case in self.cases],
        }


def dump_dataset(path: Path, dataset: ExperienceEvalDataset) -> None:
    """Write a sanitized evaluation dataset without raw market payloads."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dataset.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_dataset(path: Path) -> ExperienceEvalDataset:
    """Load and validate one versioned evaluation dataset."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid experience evaluation dataset: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("experience evaluation dataset must be an object")
    if payload.get("schema") != EXPERIENCE_EVAL_SCHEMA:
        raise ValueError(f"unsupported experience evaluation schema: {payload.get('schema')!r}")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("experience evaluation dataset cases must be an array")
    return ExperienceEvalDataset(
        feature_version=str(payload.get("feature_version", "")),
        cases=tuple(ExperienceEvalCase.from_dict(item) for item in cases),
    )


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    """Macro ranking metrics produced by :func:`evaluate_rankings`."""

    k: int
    query_count: int
    recall_at_k: float
    ndcg_at_k: float
    fallback_rate: float
    ranking_stability: float | None
    score_distribution: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe metrics for reports."""
        return asdict(self)


def evaluate_rankings(
    dataset: ExperienceEvalDataset,
    rankings: dict[str, list[str] | tuple[str, ...]],
    *,
    k: int = 3,
    baseline_rankings: dict[str, list[str] | tuple[str, ...]] | None = None,
    scores: dict[str, list[float] | tuple[float, ...]] | None = None,
) -> RankingMetrics:
    """Evaluate sanitized rankings without invoking the online reader.

    ``Recall@K`` and ``NDCG@K`` are macro-averaged over queries. Ranking
    stability is top-K overlap against ``baseline_rankings`` when provided.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if not dataset.cases:
        return RankingMetrics(k, 0, 0.0, 0.0, 0.0, None, _score_distribution(()))

    normalized: dict[str, tuple[str, ...]] = {}
    for case in dataset.cases:
        normalized[case.case_id] = _normalize_ranking(rankings.get(case.case_id, ()))

    recalls = [
        _recall_at_k(normalized[case.case_id], set(case.relevant_ids), k)
        for case in dataset.cases
    ]
    ndcgs = [
        _ndcg_at_k(normalized[case.case_id], set(case.relevant_ids), k)
        for case in dataset.cases
    ]
    stability = None
    if baseline_rankings is not None:
        stability = mean(
            _top_k_overlap(
                normalized[case.case_id],
                _normalize_ranking(baseline_rankings.get(case.case_id, ())),
                k,
            )
            for case in dataset.cases
        )
    score_values = (
        value
        for case in dataset.cases
        for value in (scores or {}).get(case.case_id, ())
    )
    return RankingMetrics(
        k=k,
        query_count=len(dataset.cases),
        recall_at_k=mean(recalls),
        ndcg_at_k=mean(ndcgs),
        fallback_rate=mean(case.similarity_fallback for case in dataset.cases),
        ranking_stability=stability,
        score_distribution=_score_distribution(score_values),
    )


def _normalize_ranking(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError("ranking must be an array")
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _recall_at_k(ranking: tuple[str, ...], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranking[:k]).intersection(relevant)) / len(relevant)


def _ndcg_at_k(ranking: tuple[str, ...], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(index + 2)
        for index, item in enumerate(ranking[:k])
        if item in relevant
    )
    ideal_hits = min(k, len(relevant))
    ideal = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    return dcg / ideal if ideal else 0.0


def _top_k_overlap(left: tuple[str, ...], right: tuple[str, ...], k: int) -> float:
    width = min(k, len(left), len(right))
    if width == 0:
        return 1.0 if not left and not right else 0.0
    return len(set(left[:k]).intersection(right[:k])) / width


def _score_distribution(values: Any) -> dict[str, float]:
    finite = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite:
        return {"count": 0.0}
    return {
        "count": float(len(finite)),
        "min": finite[0],
        "p50": _percentile(finite, 0.50),
        "p95": _percentile(finite, 0.95),
        "max": finite[-1],
        "mean": mean(finite),
    }


def _percentile(values: list[float], quantile: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] + (values[upper] - values[lower]) * weight


__all__ = [
    "EXPERIENCE_EVAL_SCHEMA",
    "EXPERIENCE_FEATURE_VERSION",
    "ExperienceEvalCase",
    "ExperienceEvalDataset",
    "RankingMetrics",
    "dump_dataset",
    "evaluate_rankings",
    "load_dataset",
]
