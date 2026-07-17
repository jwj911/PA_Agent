"""Tests for East Money quote field enum helpers."""

from __future__ import annotations

from pa_agent.data.eastmoney_field_enums import (
    FIELDS_TEN_DEPTH,
    L2_ASK_PRICE_FIELDS,
    L2_BID_PRICE_FIELDS,
    QUOTE_BASIC_ENUMS,
    QUOTE_L2_DEPTH_ENUMS,
    build_fields_param,
)


def test_build_fields_param_preserves_first_seen_order_and_deduplicates() -> None:
    fields = build_fields_param([21, 21, 22]).split(",")

    assert fields[:5] == ["f19", "f59", "f60", "f532", "f39"]
    assert fields.count("f19") == 1
    assert fields.count("f59") == 1
    assert fields.count("f60") == 1


def test_build_fields_param_ignores_unknown_enums_but_keeps_core_fields() -> None:
    fields = build_fields_param([999]).split(",")

    assert fields[:5] == ["f43", "f57", "f58", "f60", "f170"]
    assert "f530" in fields
    assert "f532" in fields


def test_build_fields_param_includes_l2_depth_slots() -> None:
    fields = build_fields_param([*QUOTE_L2_DEPTH_ENUMS]).split(",")

    for field in (*L2_ASK_PRICE_FIELDS, *L2_BID_PRICE_FIELDS):
        assert field in fields


def test_ten_depth_fields_matches_basic_plus_l2_enums() -> None:
    assert build_fields_param([*QUOTE_BASIC_ENUMS, *QUOTE_L2_DEPTH_ENUMS]) == FIELDS_TEN_DEPTH
