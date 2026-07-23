from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_ruff_baseline.py"


@pytest.fixture(scope="module")
def ruff_baseline_module():
    spec = importlib.util.spec_from_file_location("check_ruff_baseline", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _raw_issue(*, row: int, message: str = "example") -> dict:
    return {
        "filename": str(SCRIPT_PATH),
        "code": "F401",
        "location": {"row": row, "column": 1},
        "end_location": {"row": row, "column": 5},
        "message": message,
    }


def test_issue_normalizes_path_and_round_trips(ruff_baseline_module) -> None:
    issue = ruff_baseline_module.RuffIssue.from_ruff_json(_raw_issue(row=7))

    assert issue.path == "scripts/check_ruff_baseline.py"
    assert ruff_baseline_module.RuffIssue.from_baseline_json(issue.to_baseline_json()) == issue


def test_compare_issues_flags_new_and_removed_diagnostics(ruff_baseline_module) -> None:
    expected = ruff_baseline_module.RuffIssue.from_ruff_json(_raw_issue(row=7))
    current = ruff_baseline_module.RuffIssue.from_ruff_json(_raw_issue(row=8))

    unexpected, removed = ruff_baseline_module.compare_issues({expected}, {current})

    assert unexpected == [current]
    assert removed == [expected]


def test_write_and_load_baseline_round_trip(tmp_path, ruff_baseline_module) -> None:
    issue = ruff_baseline_module.RuffIssue.from_ruff_json(_raw_issue(row=7, message="stable"))
    baseline_path = tmp_path / "ruff_baseline.json"

    ruff_baseline_module.write_baseline(
        baseline_path,
        version="ruff 0.15.13",
        issues={issue},
    )

    version, issues = ruff_baseline_module.load_baseline(baseline_path)

    assert version == "ruff 0.15.13"
    assert issues == {issue}


def test_collect_ruff_issues_decodes_json_as_utf8(
    monkeypatch,
    ruff_baseline_module,
) -> None:
    calls: list[dict] = []

    def fake_run(*_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            returncode=1,
            stdout=json.dumps(
                [_raw_issue(row=9, message="中文诊断")],
                ensure_ascii=False,
            ),
            stderr="",
        )

    monkeypatch.setattr(ruff_baseline_module.subprocess, "run", fake_run)

    issues = ruff_baseline_module.collect_ruff_issues()

    assert {issue.message for issue in issues} == {"中文诊断"}
    assert calls == [
        {
            "cwd": ruff_baseline_module.ROOT,
            "text": True,
            "encoding": "utf-8",
            "errors": "strict",
            "capture_output": True,
            "check": False,
        }
    ]
