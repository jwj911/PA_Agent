"""Tests for the security package marker."""

from __future__ import annotations

import importlib


def test_security_package_marker_imports_without_public_exports() -> None:
    module = importlib.import_module("pa_agent.security")

    assert module.__name__ == "pa_agent.security"
    assert module.__doc__ == "PA Agent security and secret store package."
    assert not hasattr(module, "__all__")
    assert not hasattr(module, "encrypt_secret")
    assert not hasattr(module, "decrypt_secret")
