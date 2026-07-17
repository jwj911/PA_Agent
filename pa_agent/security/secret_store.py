"""Local secret encryption for at-rest protection of API keys.

The API key is kept in memory as plaintext (all callers read
``settings.provider.api_key``), but on Windows it is encrypted at rest via
DPAPI (``CryptProtectData`` / ``CryptUnprotectData``) so that a leaked
``settings.json`` does not directly expose the key. DPAPI ties the ciphertext
to the current Windows user account, so the blob is useless on another machine
or under another account.

Token format (self-describing):

    dpapi:v1:<base64(DPAPI blob)>

On non-Windows platforms (or when DPAPI is unavailable), encryption gracefully
degrades: :func:`encrypt_secret` returns ``None`` and callers fall back to
plaintext-at-rest (the pre-existing behaviour), still protected by
``.gitignore`` + pre-commit + runtime masking.
"""

from __future__ import annotations

import base64
import binascii
import logging
import sys

logger = logging.getLogger(__name__)

#: Scheme prefix identifying a DPAPI-encrypted token in settings.json.
_SCHEME_PREFIX = "dpapi:v1:"

#: CRYPTPROTECT_UI_FORBIDDEN — never show a UI prompt (headless-safe).
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


def is_encryption_available() -> bool:
    """True when local at-rest encryption (Windows DPAPI) is usable here."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        ctypes.windll.crypt32  # noqa: B018 — probe that crypt32 is loadable
        return True
    except (OSError, AttributeError):  # pragma: no cover - platform dependent
        logger.debug("secret_store: crypt32 unavailable", exc_info=True)
        return False


def looks_encrypted(value: str | None) -> bool:
    """True when *value* is one of our self-describing encrypted tokens."""
    return isinstance(value, str) and value.startswith("dpapi:")


def encrypt_secret(plaintext: str) -> str | None:
    """Encrypt *plaintext* to a ``dpapi:v1:`` token, or ``None`` if unavailable.

    Returns ``None`` for empty input, on non-Windows platforms, or when the
    DPAPI call fails — callers then fall back to storing plaintext at rest.
    """
    if not plaintext:
        return None
    if not is_encryption_available():
        return None
    blob = _dpapi_protect(plaintext.encode("utf-8"))
    if blob is None:
        return None
    return _SCHEME_PREFIX + base64.b64encode(blob).decode("ascii")


def decrypt_secret(token: str | None) -> str | None:
    """Decrypt a ``dpapi:v1:`` *token* back to plaintext, or ``None`` on failure.

    Returns ``None`` when the value is not a recognised token, when its base64
    is malformed, or when DPAPI cannot decrypt it (e.g. different Windows user
    or machine). Callers treat ``None`` as "no usable key".
    """
    if not token or not token.startswith(_SCHEME_PREFIX):
        return None
    b64 = token[len(_SCHEME_PREFIX) :]
    try:
        blob = base64.b64decode(b64.encode("ascii"), validate=True)
    except (binascii.Error, ValueError):
        logger.debug("secret_store: malformed base64 in encrypted token", exc_info=True)
        return None
    plain = _dpapi_unprotect(blob)
    if plain is None:
        return None
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:  # pragma: no cover - defensive
        logger.debug("secret_store: decrypted bytes are not valid utf-8", exc_info=True)
        return None


# ── Windows DPAPI (ctypes) ──────────────────────────────────────────────────


def _dpapi_protect(data: bytes) -> bytes | None:
    """Encrypt *data* with the current user's DPAPI master key. None on failure."""
    try:
        import ctypes
        from ctypes import wintypes

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
            ]

        buf_in = (ctypes.c_ubyte * len(data))(*data)
        blob_in = DATA_BLOB(len(data), buf_in)
        blob_out = DATA_BLOB()
        ok = crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            logger.debug("secret_store: CryptProtectData failed")
            return None
        try:
            size = blob_out.cbData
            ptr = ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_ubyte * size))
            return bytes(ptr.contents)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    except Exception:  # any ctypes/OS error -> graceful fallback
        logger.debug("secret_store: DPAPI protect raised", exc_info=True)
        return None


def _dpapi_unprotect(blob: bytes) -> bytes | None:
    """Decrypt a DPAPI *blob* for the current user. None on failure."""
    try:
        import ctypes
        from ctypes import wintypes

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
            ]

        buf_in = (ctypes.c_ubyte * len(blob))(*blob)
        blob_in = DATA_BLOB(len(blob), buf_in)
        blob_out = DATA_BLOB()
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            logger.debug("secret_store: CryptUnprotectData failed")
            return None
        try:
            size = blob_out.cbData
            ptr = ctypes.cast(blob_out.pbData, ctypes.POINTER(ctypes.c_ubyte * size))
            return bytes(ptr.contents)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    except Exception:  # any ctypes/OS error -> graceful fallback
        logger.debug("secret_store: DPAPI unprotect raised", exc_info=True)
        return None
