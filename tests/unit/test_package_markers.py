"""Tests for lightweight package marker modules."""
from __future__ import annotations

import importlib


def test_core_package_markers_import_without_public_exports() -> None:
    for module_name in (
        "pa_agent.ai",
        "pa_agent.config",
        "pa_agent.data",
        "pa_agent.notify",
    ):
        module = importlib.import_module(module_name)

        assert module.__name__ == module_name
        assert not hasattr(module, "__all__")


def test_core_package_markers_keep_expected_docstrings() -> None:
    expected_docstrings = {
        "pa_agent.ai": "PA Agent AI client and prompt assembly package.",
        "pa_agent.config": "PA Agent configuration package.",
        "pa_agent.data": "PA Agent data layer package.",
        "pa_agent.notify": None,
    }

    for module_name, expected_docstring in expected_docstrings.items():
        module = importlib.import_module(module_name)

        assert module.__doc__ == expected_docstring
