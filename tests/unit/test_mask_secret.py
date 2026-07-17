"""Tests for secret masking."""

from __future__ import annotations

import pytest

from pa_agent.util.mask_secret import mask_secret


@pytest.mark.parametrize(
    ("secret", "expected"),
    [
        ("", ""),
        ("abc", "abc"),
        ("abcd", "abcd"),
        ("abcde", "*bcde"),
        ("sk-super-secret-value", "*****************alue"),
        ("密钥abcd", "**abcd"),
    ],
)
def test_mask_secret_preserves_only_last_four_characters(secret: str, expected: str) -> None:
    assert mask_secret(secret) == expected
