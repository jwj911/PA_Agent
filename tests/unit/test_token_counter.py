"""Tests for lightweight token estimation."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from pa_agent.ai.token_counter import estimate_tokens


class _FakeEncoding:
    def encode(self, value: str) -> list[str]:
        return value.split()


def test_estimate_tokens_uses_tiktoken_encoding_when_available(monkeypatch) -> None:
    calls: list[str] = []

    def get_encoding(model_hint: str) -> _FakeEncoding:
        calls.append(model_hint)
        return _FakeEncoding()

    monkeypatch.setitem(sys.modules, "tiktoken", SimpleNamespace(get_encoding=get_encoding))

    assert (
        estimate_tokens(
            [
                {"role": "system", "content": "alpha beta"},
                {"role": "user", "content": "gamma", "ignored": 123},
            ],
            model_hint="fake_base",
        )
        == 15
    )
    assert calls == ["fake_base"]


def test_estimate_tokens_falls_back_to_char_count_when_tiktoken_unavailable(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    assert estimate_tokens([{"content": "x" * 12}, {"content": "abcd"}]) == 4


def test_estimate_tokens_fallback_returns_at_least_one(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    assert estimate_tokens([{"content": ""}, {"role": "user"}]) == 1
