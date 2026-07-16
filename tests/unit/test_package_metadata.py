"""Tests for the top-level package metadata."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pa_agent


def test_package_version_matches_project_metadata() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]

    assert pa_agent.__version__ == project["version"]


def test_package_docstring_describes_pa_agent() -> None:
    assert pa_agent.__doc__ == "PA Agent — AI K-line analysis decision aid package."
