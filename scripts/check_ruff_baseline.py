"""Fail when repository-wide Ruff diagnostics differ from the approved baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_PATH = ROOT / "scripts" / "ruff_baseline.json"


@dataclass(frozen=True, order=True)
class RuffIssue:
    """Stable subset of a Ruff JSON diagnostic used for baseline comparison."""

    path: str
    code: str
    row: int
    column: int
    end_row: int
    end_column: int
    message: str

    @classmethod
    def from_ruff_json(cls, issue: dict[str, Any]) -> RuffIssue:
        location = issue["location"]
        end_location = issue["end_location"]
        filename = Path(issue["filename"]).resolve()
        try:
            path = filename.relative_to(ROOT).as_posix()
        except ValueError as exc:
            raise ValueError(f"Ruff reported a file outside the repository: {filename}") from exc
        return cls(
            path=path,
            code=issue["code"],
            row=int(location["row"]),
            column=int(location["column"]),
            end_row=int(end_location["row"]),
            end_column=int(end_location["column"]),
            message=issue["message"],
        )

    @classmethod
    def from_baseline_json(cls, issue: dict[str, Any]) -> RuffIssue:
        return cls(
            path=issue["path"],
            code=issue["code"],
            row=int(issue["row"]),
            column=int(issue["column"]),
            end_row=int(issue["end_row"]),
            end_column=int(issue["end_column"]),
            message=issue["message"],
        )

    def to_baseline_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "code": self.code,
            "row": self.row,
            "column": self.column,
            "end_row": self.end_row,
            "end_column": self.end_column,
            "message": self.message,
        }

    def display(self) -> str:
        return f"{self.path}:{self.row}:{self.column}: {self.code} {self.message}"


def ruff_version() -> str:
    """Return the exact Ruff version used to generate the diagnostics."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Unable to determine Ruff version:\n{result.stderr.strip()}")
    return result.stdout.strip()


def collect_ruff_issues() -> set[RuffIssue]:
    """Run repository-wide Ruff and normalize its JSON output."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", ".", "--output-format=json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Ruff failed to run:\n{result.stderr.strip()}")

    raw_issues = json.loads(result.stdout)
    if not isinstance(raw_issues, list):
        raise ValueError("Ruff JSON output must be a list of diagnostics.")
    return {RuffIssue.from_ruff_json(issue) for issue in raw_issues}


def load_baseline(path: Path) -> tuple[str, set[RuffIssue]]:
    """Load the approved Ruff version and issue set."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload["ruff_version"]
    raw_issues = payload["issues"]
    if not isinstance(version, str) or not isinstance(raw_issues, list):
        raise ValueError(f"Invalid Ruff baseline format: {path}")

    issues = {RuffIssue.from_baseline_json(issue) for issue in raw_issues}
    if len(issues) != len(raw_issues):
        raise ValueError(f"Ruff baseline contains duplicate diagnostics: {path}")
    return version, issues


def write_baseline(path: Path, *, version: str, issues: set[RuffIssue]) -> None:
    """Write a deterministic approved diagnostic set after an intentional review."""
    payload = {
        "ruff_version": version,
        "issue_count": len(issues),
        "issues": [issue.to_baseline_json() for issue in sorted(issues)],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def compare_issues(
    expected: set[RuffIssue], current: set[RuffIssue]
) -> tuple[list[RuffIssue], list[RuffIssue]]:
    """Return unexpected and removed diagnostics in deterministic order."""
    return sorted(current - expected), sorted(expected - current)


def _print_issues(title: str, issues: list[RuffIssue]) -> None:
    print(f"{title} ({len(issues)}):")
    for issue in issues[:20]:
        print(f"  {issue.display()}")
    if len(issues) > 20:
        print(f"  ... {len(issues) - 20} more")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to the approved Ruff diagnostic baseline.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate the baseline after an intentional reviewed cleanup.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        version = ruff_version()
        current = collect_ruff_issues()
        baseline_path = args.baseline.resolve()
        if args.write_baseline:
            write_baseline(baseline_path, version=version, issues=current)
            print(f"Wrote Ruff baseline: {baseline_path} ({len(current)} diagnostics, {version})")
            return 0

        expected_version, expected = load_baseline(baseline_path)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Ruff baseline check failed: {exc}", file=sys.stderr)
        return 2

    if version != expected_version:
        print(
            "Ruff baseline version mismatch: "
            f"expected {expected_version}, got {version}. "
            "Update the pinned dependency or regenerate the baseline intentionally.",
            file=sys.stderr,
        )
        return 1

    unexpected, removed = compare_issues(expected, current)
    if unexpected or removed:
        print("Ruff baseline changed. Review and update it in a dedicated cleanup iteration.")
        if unexpected:
            _print_issues("Unexpected diagnostics", unexpected)
        if removed:
            _print_issues("Removed diagnostics", removed)
        return 1

    print(f"Ruff baseline passed: {len(current)} approved diagnostics ({version}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
