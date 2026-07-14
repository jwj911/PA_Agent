"""Filename component sanitization (standalone, no dependencies).

Used to build record/log filenames from user- or market-derived values
(symbol, timeframe) so they cannot cause path traversal or produce
illegal names on Windows.
"""
from __future__ import annotations

import re

# Characters illegal in Windows filenames plus path separators.
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Windows reserved device names (case-insensitive), with or without extension.
_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def sanitize_filename_component(value: str, fallback: str = "unknown") -> str:
    """Return *value* reduced to a safe single filename component.

    - Replaces illegal characters and path separators with ``-``.
    - Strips leading/trailing dots, spaces and dashes (blocks ``..`` traversal
      and trailing-dot/space quirks on Windows).
    - Guards against Windows reserved device names (CON, NUL, COM1, ...).
    - Returns *fallback* when the result would otherwise be empty.
    """
    cleaned = _ILLEGAL_CHARS.sub("-", value or "")
    cleaned = cleaned.strip(" .-")
    if not cleaned:
        return fallback
    if cleaned.split(".", 1)[0].lower() in _RESERVED_NAMES:
        return f"_{cleaned}"
    return cleaned
