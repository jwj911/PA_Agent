from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from textwrap import dedent

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "check_ci_workflow_targets.py"


@pytest.fixture(scope="module")
def ci_workflow_targets_module():
    spec = importlib.util.spec_from_file_location("check_ci_workflow_targets", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _workflow_text(*, pytest_targets: list[str], ruff_targets: list[str]) -> str:
    pytest_lines = "\n".join(f"          {target}" for target in pytest_targets)
    ruff_lines = "\n".join(f"          {target}" for target in ruff_targets)
    return dedent(
        f"""\
        name: CI

        jobs:
          test:
            steps:
              - name: Run targeted tests
                run: >
                  python -m pytest
        {pytest_lines}
                  --tb=line
                  -q
                  -p pytest_cov

              - name: Run focused Ruff checks
                run: >
                  python -m ruff check
        {ruff_lines}

              - name: Run focused Black format check
                shell: pwsh
                run: |
                  $start = [Array]::IndexOf($workflow, '      - name: Run focused Ruff checks')
                  python -m black --check @targets
        """
    )


def test_collect_workflow_targets_parses_folded_steps(ci_workflow_targets_module) -> None:
    workflow_text = _workflow_text(
        pytest_targets=["tests/unit/test_one.py", "tests/property"],
        ruff_targets=["scripts/check_ci_workflow_targets.py", "tests/unit/test_one.py"],
    )

    targeted_pytest, focused_ruff = ci_workflow_targets_module.collect_workflow_targets(
        workflow_text
    )

    assert targeted_pytest.targets == ("tests/unit/test_one.py", "tests/property")
    assert focused_ruff.targets == (
        "scripts/check_ci_workflow_targets.py",
        "tests/unit/test_one.py",
    )


def test_validate_workflow_targets_reports_duplicates_and_missing_paths(
    tmp_path,
    ci_workflow_targets_module,
) -> None:
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests" / "unit" / "test_one.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "check_ci_workflow_targets.py").write_text("", encoding="utf-8")

    workflow_text = _workflow_text(
        pytest_targets=[
            "tests/unit/test_one.py",
            "tests/unit/test_one.py",
            "tests/unit/missing.py",
        ],
        ruff_targets=["scripts/check_ci_workflow_targets.py"],
    )

    _, errors = ci_workflow_targets_module.validate_workflow_targets(tmp_path, workflow_text)

    assert "targeted pytest contains duplicate targets: tests/unit/test_one.py" in errors
    assert "targeted pytest contains missing paths: tests/unit/missing.py" in errors


def test_validate_workflow_targets_reports_black_anchor_drift(
    tmp_path,
    ci_workflow_targets_module,
) -> None:
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests" / "unit" / "test_one.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "check_ci_workflow_targets.py").write_text("", encoding="utf-8")

    workflow_text = _workflow_text(
        pytest_targets=["tests/unit/test_one.py"],
        ruff_targets=["scripts/check_ci_workflow_targets.py"],
    ).replace(
        "$start = [Array]::IndexOf($workflow, '      - name: Run focused Ruff checks')",
        "$start = [Array]::IndexOf($workflow, '      - name: Run stale Ruff checks')",
    )

    _, errors = ci_workflow_targets_module.validate_workflow_targets(tmp_path, workflow_text)

    assert "focused Black step no longer anchors on the focused Ruff step name." in errors


def test_validate_workflow_targets_reports_black_target_reuse_drift(
    tmp_path,
    ci_workflow_targets_module,
) -> None:
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests" / "unit" / "test_one.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "check_ci_workflow_targets.py").write_text("", encoding="utf-8")

    workflow_text = _workflow_text(
        pytest_targets=["tests/unit/test_one.py"],
        ruff_targets=["scripts/check_ci_workflow_targets.py"],
    ).replace(
        "python -m black --check @targets",
        "python -m black --check scripts/check_ci_workflow_targets.py",
    )

    _, errors = ci_workflow_targets_module.validate_workflow_targets(tmp_path, workflow_text)

    assert "focused Black step no longer reuses the parsed @targets list." in errors


def test_current_ci_workflow_targets_are_valid(ci_workflow_targets_module) -> None:
    workflow_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    target_lists, errors = ci_workflow_targets_module.validate_workflow_targets(
        ROOT,
        workflow_text,
    )

    assert errors == []
    assert {target_list.label for target_list in target_lists} == {
        "targeted pytest",
        "focused Ruff",
    }
