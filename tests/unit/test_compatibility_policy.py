"""Tests for L1/L2 compatibility removal policy gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.check_compatibility_policy import (
    POLICY_SCHEMA,
    check_compatibility_policy,
    main,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "compatibility_policy.json"


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _minimal_repo(tmp_path: Path, version: str) -> Path:
    (tmp_path / "pa_agent").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "fixture"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (tmp_path / "pa_agent" / "__init__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_current_policy_retains_required_l1_l2_surfaces() -> None:
    policy = _policy()

    errors = check_compatibility_policy(ROOT, policy, release_tags=set())

    assert policy["schema"] == POLICY_SCHEMA
    assert errors == []


def test_retain_policy_rejects_a_missing_compatibility_marker() -> None:
    policy = _policy()
    policy["surfaces"]["l1_legacy_registrar"]["required_symbols"][0]["contains"] = (
        "marker-that-does-not-exist"
    )

    errors = check_compatibility_policy(ROOT, policy, release_tags=set())

    assert any("required compatibility marker missing" in error for error in errors)


def test_remove_is_blocked_before_release_tag_and_evidence(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path, "0.1.0")
    policy = {
        "schema": POLICY_SCHEMA,
        "current_release": "0.1.0",
        "surfaces": {
            "surface": {
                "status": "remove",
                "deprecated_since": "0.2.0",
                "earliest_removal_release": "0.3.0",
                "required_deprecation_release": "0.2.0",
                "required_symbols": [{"path": "removed.py", "contains": "legacy"}],
                "removal_evidence": ["inventory"],
            }
        },
    }

    errors = check_compatibility_policy(repo, policy, release_tags=set())

    assert any("earlier than removal release" in error for error in errors)
    assert any("release tag is missing" in error for error in errors)
    assert any("removal evidence is missing" in error for error in errors)


def test_remove_passes_only_after_release_and_evidence(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path, "0.3.0")
    evidence = repo / "docs" / "compatibility_evidence" / "surface"
    evidence.mkdir(parents=True)
    (evidence / "inventory.json").write_text("{}", encoding="utf-8")
    policy = {
        "schema": POLICY_SCHEMA,
        "current_release": "0.3.0",
        "surfaces": {
            "surface": {
                "status": "remove",
                "deprecated_since": "0.2.0",
                "earliest_removal_release": "0.3.0",
                "required_deprecation_release": "0.2.0",
                "required_symbols": [{"path": "removed.py", "contains": "legacy"}],
                "removal_evidence": ["inventory"],
            }
        },
    }

    errors = check_compatibility_policy(repo, policy, release_tags={"v0.2.0"})

    assert errors == []


def test_policy_current_release_must_match_project_version() -> None:
    policy = copy.deepcopy(_policy())
    policy["current_release"] = "0.2.0"

    errors = check_compatibility_policy(ROOT, policy, release_tags=set())

    assert any("current_release" in error for error in errors)


def test_cli_checks_repository_policy(capsys) -> None:
    exit_code = main(["--repo-root", str(ROOT), "--policy", str(POLICY_PATH)])

    assert exit_code == 0
    assert "2 retained/deprecation surfaces checked" in capsys.readouterr().out
