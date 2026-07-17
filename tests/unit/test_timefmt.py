"""Tests for time formatting helpers."""

from __future__ import annotations

from pa_agent.util import timefmt


def test_now_local_ms_uses_epoch_milliseconds(monkeypatch) -> None:
    monkeypatch.setattr(timefmt.time, "time", lambda: 1234.567)

    assert timefmt.now_local_ms() == 1_234_567
