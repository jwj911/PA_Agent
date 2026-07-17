"""Tests for K-line adjustment preference helpers."""

from __future__ import annotations

from types import SimpleNamespace

from pa_agent.data.kline_adjust import (
    apply_kline_adjust_from_settings,
    get_kline_adjust,
    set_kline_adjust,
)


def _reset_adjust() -> None:
    set_kline_adjust("qfq")


def test_set_kline_adjust_accepts_supported_values() -> None:
    try:
        set_kline_adjust("hfq")
        assert get_kline_adjust() == "hfq"

        set_kline_adjust("none")
        assert get_kline_adjust() == "none"

        set_kline_adjust(" QFQ ")
        assert get_kline_adjust() == "qfq"
    finally:
        _reset_adjust()


def test_set_kline_adjust_falls_back_to_default() -> None:
    try:
        set_kline_adjust("unsupported")
        assert get_kline_adjust() == "qfq"

        set_kline_adjust(None)
        assert get_kline_adjust() == "qfq"
    finally:
        _reset_adjust()


def test_apply_kline_adjust_from_settings_reads_general_section() -> None:
    try:
        settings = SimpleNamespace(general=SimpleNamespace(kline_adjust="hfq"))
        apply_kline_adjust_from_settings(settings)

        assert get_kline_adjust() == "hfq"
    finally:
        _reset_adjust()


def test_apply_kline_adjust_from_settings_none_resets_default() -> None:
    try:
        set_kline_adjust("none")
        apply_kline_adjust_from_settings(None)

        assert get_kline_adjust() == "qfq"
    finally:
        _reset_adjust()
