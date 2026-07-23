"""Enforce release gates for L1/L2 compatibility surface removal."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "config" / "compatibility_policy.json"
POLICY_SCHEMA = "pa-agent.compatibility-policy.v1"
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def check_compatibility_policy(
    repo_root: Path,
    policy: dict[str, Any],
    *,
    release_tags: set[str] | None = None,
) -> list[str]:
    """Return deterministic policy violations without modifying the workspace."""
    errors: list[str] = []
    if policy.get("schema") != POLICY_SCHEMA:
        return ["unsupported compatibility policy schema"]
    surfaces = policy.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        return ["compatibility policy surfaces must be a non-empty object"]

    project_version = _project_version(repo_root, errors)
    package_version = _package_version(repo_root, errors)
    current_release = _version(policy.get("current_release"), "current_release", errors)
    if project_version and package_version and project_version != package_version:
        errors.append("package version does not match pyproject version")
    if project_version and current_release and project_version != current_release:
        errors.append("policy current_release does not match project version")

    tags = release_tags if release_tags is not None else _release_tags(repo_root)
    for surface_name in sorted(surfaces):
        surface = surfaces[surface_name]
        if not isinstance(surface, dict):
            errors.append(f"{surface_name}: surface policy must be an object")
            continue
        status = surface.get("status")
        if status not in {"retain", "deprecated", "remove"}:
            errors.append(f"{surface_name}: status must be retain, deprecated, or remove")
            continue
        earliest = _version(
            surface.get("earliest_removal_release"),
            f"{surface_name}.earliest_removal_release",
            errors,
        )
        deprecation_release = _version(
            surface.get("required_deprecation_release"),
            f"{surface_name}.required_deprecation_release",
            errors,
        )
        if earliest and deprecation_release and deprecation_release >= earliest:
            errors.append(
                f"{surface_name}: deprecation release must precede earliest removal release"
            )
        if status in {"retain", "deprecated"}:
            _check_required_symbols(repo_root, surface_name, surface, errors)

        deprecated_since = surface.get("deprecated_since")
        if status == "retain" and deprecated_since is not None:
            errors.append(f"{surface_name}: retain status must not set deprecated_since")
        if status in {"deprecated", "remove"}:
            deprecated_version = _version(
                deprecated_since,
                f"{surface_name}.deprecated_since",
                errors,
            )
            if (
                deprecated_version
                and deprecation_release
                and deprecated_version < deprecation_release
            ):
                errors.append(f"{surface_name}: deprecated_since is earlier than required release")
        if status == "remove":
            _check_removal_gate(
                repo_root,
                surface_name,
                surface,
                current_release,
                earliest,
                deprecation_release,
                tags,
                errors,
            )
    return errors


def _check_required_symbols(
    repo_root: Path,
    surface_name: str,
    surface: dict[str, Any],
    errors: list[str],
) -> None:
    required = surface.get("required_symbols")
    if not isinstance(required, list) or not required:
        errors.append(f"{surface_name}: required_symbols must be a non-empty array")
        return
    for index, requirement in enumerate(required):
        if not isinstance(requirement, dict):
            errors.append(f"{surface_name}: required symbol {index} must be an object")
            continue
        path_value = requirement.get("path")
        contains = requirement.get("contains")
        if not isinstance(path_value, str) or not isinstance(contains, str) or not contains:
            errors.append(f"{surface_name}: required symbol {index} is invalid")
            continue
        path = (repo_root / path_value).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"{surface_name}: required symbol path escapes repository")
            continue
        if not path.is_file():
            errors.append(f"{surface_name}: required file is missing: {path_value}")
            continue
        if contains not in path.read_text(encoding="utf-8"):
            errors.append(f"{surface_name}: required compatibility marker missing: {path_value}")


def _check_removal_gate(
    repo_root: Path,
    surface_name: str,
    surface: dict[str, Any],
    current_release: tuple[int, int, int] | None,
    earliest: tuple[int, int, int] | None,
    deprecation_release: tuple[int, int, int] | None,
    release_tags: set[str],
    errors: list[str],
) -> None:
    if current_release and earliest and current_release < earliest:
        errors.append(f"{surface_name}: current release is earlier than removal release")
    if deprecation_release:
        expected_tag = f"v{_format_version(deprecation_release)}"
        if expected_tag not in release_tags:
            errors.append(f"{surface_name}: required deprecation release tag is missing")
    evidence = surface.get("removal_evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{surface_name}: removal_evidence must be a non-empty array")
        return
    evidence_dir = repo_root / "docs" / "compatibility_evidence" / surface_name
    for name in evidence:
        if not isinstance(name, str) or not name:
            errors.append(f"{surface_name}: removal evidence name is invalid")
            continue
        if not (evidence_dir / f"{name}.json").is_file():
            errors.append(f"{surface_name}: removal evidence is missing: {name}")


def _project_version(repo_root: Path, errors: list[str]) -> tuple[int, int, int] | None:
    try:
        payload = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
        value = payload["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        errors.append("cannot read project version")
        return None
    return _version(value, "project.version", errors)


def _package_version(repo_root: Path, errors: list[str]) -> tuple[int, int, int] | None:
    try:
        text = (repo_root / "pa_agent" / "__init__.py").read_text(encoding="utf-8")
    except OSError:
        errors.append("cannot read package version")
        return None
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if match is None:
        errors.append("cannot parse package version")
        return None
    return _version(match.group(1), "pa_agent.__version__", errors)


def _version(
    value: object,
    label: str,
    errors: list[str],
) -> tuple[int, int, int] | None:
    text = str(value or "")
    if not _VERSION_PATTERN.fullmatch(text):
        errors.append(f"{label} must use MAJOR.MINOR.PATCH")
        return None
    return tuple(int(part) for part in text.split("."))  # type: ignore[return-value]


def _format_version(value: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in value)


def _release_tags(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _load_policy(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid compatibility policy JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("compatibility policy must be an object")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        policy = _load_policy(args.policy.resolve())
    except ValueError as exc:
        print(f"Compatibility policy check failed: {exc}", file=sys.stderr)
        return 2
    errors = check_compatibility_policy(repo_root, policy)
    if errors:
        print("Compatibility policy check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "Compatibility policy passed: "
        f"{len(policy['surfaces'])} retained/deprecation surfaces checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
