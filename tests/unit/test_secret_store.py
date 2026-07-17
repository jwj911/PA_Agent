"""Unit tests for pa_agent.security.secret_store (M8 local encryption)."""

from __future__ import annotations

import pytest

from pa_agent.security.secret_store import (
    decrypt_secret,
    encrypt_secret,
    is_encryption_available,
    looks_encrypted,
)

_ENC_AVAILABLE = is_encryption_available()
_requires_enc = pytest.mark.skipif(
    not _ENC_AVAILABLE, reason="local encryption (DPAPI) unavailable on this platform"
)


@_requires_enc
def test_round_trip_recovers_plaintext():
    token = encrypt_secret("sk-live-abcdef123456")
    assert token is not None
    assert token.startswith("dpapi:v1:")
    assert decrypt_secret(token) == "sk-live-abcdef123456"


@_requires_enc
def test_ciphertext_does_not_contain_plaintext():
    secret = "sk-super-secret-value-XYZ"
    token = encrypt_secret(secret)
    assert token is not None
    assert secret not in token


@_requires_enc
def test_unicode_secret_round_trip():
    secret = "密钥-ключ-🔑-abc"
    token = encrypt_secret(secret)
    assert token is not None
    assert decrypt_secret(token) == secret


def test_encrypt_empty_returns_none():
    assert encrypt_secret("") is None


def test_decrypt_none_and_empty():
    assert decrypt_secret(None) is None
    assert decrypt_secret("") is None


def test_decrypt_unknown_scheme_returns_none():
    assert decrypt_secret("sk-plaintext-not-a-token") is None
    assert decrypt_secret("aes:v1:whatever") is None


def test_decrypt_corrupt_base64_returns_none():
    assert decrypt_secret("dpapi:v1:@@@not-valid-base64@@@") is None


@_requires_enc
def test_decrypt_tampered_blob_returns_none():
    import base64

    token = encrypt_secret("sk-tamper-target")
    assert token is not None
    raw = base64.b64decode(token[len("dpapi:v1:") :])
    tampered = bytes([raw[0] ^ 0xFF]) + raw[1:]
    bad_token = "dpapi:v1:" + base64.b64encode(tampered).decode("ascii")
    assert decrypt_secret(bad_token) is None


def test_looks_encrypted():
    assert looks_encrypted("dpapi:v1:abc") is True
    assert looks_encrypted("dpapi:anything") is True
    assert looks_encrypted("sk-plaintext") is False
    assert looks_encrypted("") is False
    assert looks_encrypted(None) is False
