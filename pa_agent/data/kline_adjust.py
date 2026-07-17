"""K-line price adjustment (复权) preference for A-share HTTP sources."""

from __future__ import annotations

import threading
from typing import Literal

KlineAdjust = Literal["qfq", "hfq", "none"]

_DEFAULT: KlineAdjust = "qfq"
_current: KlineAdjust = _DEFAULT
_LOCK = threading.Lock()


def set_kline_adjust(adjust: str | None) -> None:
    global _current
    key = str(adjust or "qfq").strip().lower()
    with _LOCK:
        _current = key if key in ("qfq", "hfq", "none") else _DEFAULT  # type: ignore[assignment]


def get_kline_adjust() -> KlineAdjust:
    with _LOCK:
        return _current


def apply_kline_adjust_from_settings(settings: object | None) -> None:
    if settings is None:
        set_kline_adjust(_DEFAULT)
        return
    general = getattr(settings, "general", settings)
    set_kline_adjust(getattr(general, "kline_adjust", _DEFAULT))
