"""Validate CI workflow target lists stay parseable and deterministic."""

from __future__ import annotations

import argparse
import shlex
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"
STEP_MARKER_PREFIX = "      - name: "

_PYTEST_OPTIONS_WITH_VALUE = {"-m", "-p", "--cov", "--cov-report", "--tb"}
_RUFF_OPTIONS_WITH_VALUE: set[str] = set()


@dataclass(frozen=True)
class WorkflowTargetList:
    """A parsed list of path targets from one CI step."""

    label: str
    step_name: str
    targets: tuple[str, ...]


def extract_step_lines(workflow_text: str, step_name: str) -> list[str]:
    """Return the raw lines belonging to a named GitHub Actions step."""
    lines = workflow_text.splitlines()
    marker = f"{STEP_MARKER_PREFIX}{step_name}"
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == marker:
            start = index + 1
            break
    if start is None:
        raise ValueError(f"CI step not found: {step_name}")

    step_lines: list[str] = []
    for line in lines[start:]:
        if line.startswith(STEP_MARKER_PREFIX):
            break
        step_lines.append(line)
    return step_lines


def extract_command_targets(
    step_lines: Sequence[str],
    *,
    command: Sequence[str],
    options_with_value: set[str],
) -> tuple[str, ...]:
    """Extract path-like arguments after a command in a folded workflow step."""
    command_tokens = tuple(command)
    targets: list[str] = []
    collecting = False
    skip_next = False

    for raw_line in step_lines:
        line = raw_line.strip()
        if not line:
            continue
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError as exc:
            raise ValueError(f"Cannot parse workflow line: {line}") from exc
        if not tokens:
            continue

        if not collecting:
            if tuple(tokens[: len(command_tokens)]) != command_tokens:
                continue
            collecting = True
            tokens = tokens[len(command_tokens) :]

        for token in tokens:
            if skip_next:
                skip_next = False
                continue
            if token in options_with_value:
                skip_next = True
                continue
            if token.startswith("-"):
                continue
            targets.append(_normalize_target(token))

    if skip_next:
        raise ValueError(f"Option without value in command: {' '.join(command_tokens)}")
    return tuple(target for target in targets if target)


def collect_workflow_targets(workflow_text: str) -> tuple[WorkflowTargetList, ...]:
    """Collect the CI target lists that must stay clean and parseable."""
    targeted_pytest = WorkflowTargetList(
        label="targeted pytest",
        step_name="Run targeted tests",
        targets=extract_command_targets(
            extract_step_lines(workflow_text, "Run targeted tests"),
            command=("python", "-m", "pytest"),
            options_with_value=_PYTEST_OPTIONS_WITH_VALUE,
        ),
    )
    focused_ruff = WorkflowTargetList(
        label="focused Ruff",
        step_name="Run focused Ruff checks",
        targets=extract_command_targets(
            extract_step_lines(workflow_text, "Run focused Ruff checks"),
            command=("python", "-m", "ruff", "check"),
            options_with_value=_RUFF_OPTIONS_WITH_VALUE,
        ),
    )
    return targeted_pytest, focused_ruff


def validate_workflow_targets(
    repo_root: Path,
    workflow_text: str,
) -> tuple[tuple[WorkflowTargetList, ...], list[str]]:
    """Return parsed target lists and deterministic validation errors."""
    target_lists = collect_workflow_targets(workflow_text)
    errors: list[str] = []

    for target_list in target_lists:
        if not target_list.targets:
            errors.append(f"{target_list.label} target list is empty.")
            continue

        duplicates = _duplicates(target_list.targets)
        if duplicates:
            errors.append(
                f"{target_list.label} contains duplicate targets: {', '.join(duplicates)}"
            )

        missing = _missing_targets(repo_root, target_list.targets)
        if missing:
            errors.append(f"{target_list.label} contains missing paths: {', '.join(missing)}")

    black_lines = extract_step_lines(workflow_text, "Run focused Black format check")
    black_script = "\n".join(line.strip() for line in black_lines)
    if "Run focused Ruff checks" not in black_script:
        errors.append("focused Black step no longer anchors on the focused Ruff step name.")
    if "python -m black --check @targets" not in black_script:
        errors.append("focused Black step no longer reuses the parsed @targets list.")

    return target_lists, errors


def _normalize_target(target: str) -> str:
    normalized = target.replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _duplicates(targets: Sequence[str]) -> list[str]:
    counts = Counter(targets)
    return sorted(target for target, count in counts.items() if count > 1)


def _missing_targets(repo_root: Path, targets: Sequence[str]) -> list[str]:
    return sorted(target for target in targets if not (repo_root / target).exists())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow",
        type=Path,
        default=DEFAULT_WORKFLOW_PATH,
        help="Path to the GitHub Actions workflow to validate.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root used to validate target path existence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    workflow_path = args.workflow.resolve()

    try:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        target_lists, errors = validate_workflow_targets(repo_root, workflow_text)
    except (OSError, ValueError) as exc:
        print(f"CI workflow target check failed: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("CI workflow target check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    for target_list in target_lists:
        print(f"{target_list.label}: {len(target_list.targets)} targets")
    print("CI workflow target lists passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
