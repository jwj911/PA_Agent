"""Unit tests for Cursor SDK stream event mapping."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import pa_agent.ai.cursor_sdk_client as cursor_sdk_client


@pytest.fixture(autouse=True)
def _reset_cursor_sdk_patch_flags(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in (
        "_PATCHED_CURSOR_SDK_BRIDGE",
        "_PATCHED_CURSOR_SDK_AUTH_TOKENS",
        "_PATCHED_CURSOR_SDK_BRIDGE_ARGV",
        "_PATCHED_CURSOR_SDK_POPEN",
    ):
        monkeypatch.setattr(cursor_sdk_client, name, False)
    yield


def _install_cursor_sdk_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ModuleType, ModuleType, ModuleType, ModuleType, list[list[str]]]:
    cursor_pkg = ModuleType("cursor_sdk")
    tool_cb = ModuleType("cursor_sdk._tool_callback")
    store_cb = ModuleType("cursor_sdk._store_callback")
    bridge_mod = ModuleType("cursor_sdk._bridge")
    errors_mod = ModuleType("cursor_sdk.errors")

    class CursorSDKError(Exception):
        pass

    def unsafe_token() -> str:
        return "-unsafe"

    def tool_argv(endpoint: Any) -> list[str]:
        return [
            "cursor-sdk-bridge.js",
            "--tool-callback-url",
            str(endpoint),
            "--tool-callback-auth-token",
            "-tool-token",
        ]

    def store_argv(endpoint: Any) -> list[str]:
        return [
            "cursor-sdk-bridge.js",
            "--store-callback-url",
            str(endpoint),
            "--store-callback-auth-token",
            "-store-token",
        ]

    popen_calls: list[list[str]] = []

    def fake_popen(argv: Any, *args: Any, **kwargs: Any) -> SimpleNamespace:
        del args, kwargs
        popen_calls.append(list(argv))
        return SimpleNamespace()

    tool_cb._new_auth_token = unsafe_token  # type: ignore[attr-defined]
    tool_cb.tool_callback_bridge_argv = tool_argv  # type: ignore[attr-defined]
    store_cb._new_auth_token = unsafe_token  # type: ignore[attr-defined]
    store_cb.store_callback_bridge_argv = store_argv  # type: ignore[attr-defined]
    errors_mod.CursorSDKError = CursorSDKError  # type: ignore[attr-defined]
    bridge_mod.READY_LINE_PREFIX = "cursor-sdk-bridge ready "  # type: ignore[attr-defined]
    bridge_mod.parse_discovery_line = lambda line: {"line": line.strip()}  # type: ignore[attr-defined]
    bridge_mod.subprocess = SimpleNamespace(Popen=fake_popen)  # type: ignore[attr-defined]

    cursor_pkg._tool_callback = tool_cb  # type: ignore[attr-defined]
    cursor_pkg._store_callback = store_cb  # type: ignore[attr-defined]
    cursor_pkg._bridge = bridge_mod  # type: ignore[attr-defined]
    cursor_pkg.errors = errors_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "cursor_sdk", cursor_pkg)
    monkeypatch.setitem(sys.modules, "cursor_sdk._tool_callback", tool_cb)
    monkeypatch.setitem(sys.modules, "cursor_sdk._store_callback", store_cb)
    monkeypatch.setitem(sys.modules, "cursor_sdk._bridge", bridge_mod)
    monkeypatch.setitem(sys.modules, "cursor_sdk.errors", errors_mod)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    return tool_cb, store_cb, bridge_mod, errors_mod, popen_calls


class _FakeStderr:
    def __init__(self, lines: list[str]) -> None:
        self._lines = list(lines)

    def readline(self) -> str:
        if self._lines:
            return self._lines.pop(0)
        return ""


class _FakeProcess:
    def __init__(self, lines: list[str]) -> None:
        self.stderr = _FakeStderr(lines)

    def poll(self) -> int | None:
        return None


def _auth_token_from(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _assert_sanitized(argv: list[str], flag: str) -> None:
    token = _auth_token_from(argv, flag)
    assert token
    assert not token.startswith("-")


def test_safe_bridge_auth_token_never_starts_with_dash() -> None:
    for _ in range(100):
        assert not cursor_sdk_client._safe_bridge_auth_token().startswith("-")


def test_patch_cursor_sdk_bridge_auth_tokens_uses_stub_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_cb, store_cb, _, _, _ = _install_cursor_sdk_stub(monkeypatch)

    cursor_sdk_client._patch_cursor_sdk_bridge_auth_tokens()

    for _ in range(20):
        assert not tool_cb._new_auth_token().startswith("-")  # type: ignore[attr-defined]
        assert not store_cb._new_auth_token().startswith("-")  # type: ignore[attr-defined]


def test_sanitize_cursor_bridge_argv_fixes_dash_prefixed_token() -> None:
    argv = [
        "cursor-sdk-bridge.js",
        "--tool-callback-url",
        "http://127.0.0.1:1",
        "--tool-callback-auth-token",
        "-startsWithDash",
    ]
    fixed = cursor_sdk_client._sanitize_cursor_bridge_argv(argv)
    assert fixed[4] != "-startsWithDash"
    assert not fixed[4].startswith("-")


def test_ensure_cursor_sdk_patches_stub_bridge_without_launching_real_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_cb, store_cb, bridge_mod, _, popen_calls = _install_cursor_sdk_stub(monkeypatch)
    monkeypatch.setattr(cursor_sdk_client.sys, "platform", "win32")

    cursor_sdk_client._ensure_cursor_sdk_patches()

    tool_argv = tool_cb.tool_callback_bridge_argv("http://127.0.0.1:1")  # type: ignore[attr-defined]
    store_argv = store_cb.store_callback_bridge_argv("http://127.0.0.1:2")  # type: ignore[attr-defined]
    _assert_sanitized(tool_argv, "--tool-callback-auth-token")
    _assert_sanitized(store_argv, "--store-callback-auth-token")

    bridge_mod.subprocess.Popen(  # type: ignore[attr-defined]
        [
            "cursor-sdk-bridge.js",
            "--tool-callback-auth-token",
            "-late-token",
        ]
    )
    assert popen_calls
    _assert_sanitized(popen_calls[-1], "--tool-callback-auth-token")

    discovery = bridge_mod._read_discovery(  # type: ignore[attr-defined]
        _FakeProcess(["noise\n", 'cursor-sdk-bridge ready {"port":1}\n']),
        timeout=1.0,
    )
    assert discovery == {"line": 'cursor-sdk-bridge ready {"port":1}'}


def test_consume_thinking_delta_emits_reasoning_callback() -> None:
    reasoning: list[str] = []
    content: list[str] = []
    emitted: list[str] = []

    event = SimpleNamespace(
        interaction_update=SimpleNamespace(type="thinking-delta", text="alpha "),
        sdk_message=None,
        step=None,
    )
    cursor_sdk_client._consume_cursor_stream_event(
        event,
        reasoning_parts=reasoning,
        content_parts=content,
        on_reasoning_token=emitted.append,
        on_content_token=None,
    )

    assert reasoning == ["alpha "]
    assert emitted == ["alpha "]
    assert content == []


def test_consume_text_delta_emits_content_callback() -> None:
    reasoning: list[str] = []
    content: list[str] = []
    emitted: list[str] = []

    event = SimpleNamespace(
        interaction_update=SimpleNamespace(type="text-delta", text='{"ok":'),
        sdk_message=None,
        step=None,
    )
    cursor_sdk_client._consume_cursor_stream_event(
        event,
        reasoning_parts=reasoning,
        content_parts=content,
        on_reasoning_token=None,
        on_content_token=emitted.append,
    )

    assert content == ['{"ok":']
    assert emitted == ['{"ok":']
    assert reasoning == []
