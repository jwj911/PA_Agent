"""Tests for captured East Money quote API constants."""

from __future__ import annotations

from pa_agent.data.eastmoney_field_enums import FIELDS_TEN_DEPTH
from pa_agent.data.eastmoney_quote_api import (
    ASK_FIELD_PAIRS,
    BID_FIELD_PAIRS,
    DETAILS_FIELDS1,
    DETAILS_FIELDS2,
    DETAILS_GET_PATH,
    DETAILS_SSE_PATH,
    FREE_DEPTH_LEVELS,
    L2_ASK_EXTENDED,
    L2_BID_EXTENDED,
    L2_DEPTH_LEVELS,
    ORDER_BOOK_FIELDS,
    QUOTE_HOSTS,
    STOCK_GET_PATH,
    STOCK_SSE_PATH,
    TEN_DEPTH_FIELDS,
    TRENDS2_PATH,
    TRENDS2_SSE_PATH,
)


def test_quote_hosts_prefer_delay_then_realtime_mirrors() -> None:
    assert QUOTE_HOSTS == (
        "push2delay.eastmoney.com",
        "push2.eastmoney.com",
        "82.push2.eastmoney.com",
        "91.push2.eastmoney.com",
    )


def test_quote_paths_are_stable() -> None:
    assert STOCK_GET_PATH == "/api/qt/stock/get"
    assert STOCK_SSE_PATH == "/api/qt/stock/sse"
    assert DETAILS_GET_PATH == "/api/qt/stock/details/get"
    assert DETAILS_SSE_PATH == "/api/qt/stock/details/sse"
    assert TRENDS2_PATH == "/api/qt/stock/trends2/get"
    assert TRENDS2_SSE_PATH == "/api/qt/stock/trends2/sse"


def test_order_book_pairs_are_nearest_price_first() -> None:
    assert ASK_FIELD_PAIRS == (
        ("f39", "f40"),
        ("f37", "f38"),
        ("f35", "f36"),
        ("f33", "f34"),
        ("f31", "f32"),
    )
    assert BID_FIELD_PAIRS == (
        ("f19", "f20"),
        ("f17", "f18"),
        ("f15", "f16"),
        ("f13", "f14"),
        ("f11", "f12"),
    )


def test_l2_extended_pairs_expand_to_ten_levels() -> None:
    assert FREE_DEPTH_LEVELS == 5
    assert L2_DEPTH_LEVELS == 10
    assert L2_ASK_EXTENDED == (
        ("f29", "f30"),
        ("f27", "f28"),
        ("f25", "f26"),
        ("f23", "f24"),
        ("f21", "f22"),
    )
    assert L2_BID_EXTENDED == (
        ("f9", "f10"),
        ("f7", "f8"),
        ("f5", "f6"),
        ("f3", "f4"),
        ("f1", "f2"),
    )


def test_fields_constants_include_required_order_book_and_tick_fields() -> None:
    fields = ORDER_BOOK_FIELDS.split(",")

    for field in ("f43", "f57", "f58", "f170", "f11", "f20", "f31", "f40"):
        assert field in fields
    assert DETAILS_FIELDS1 == "f1"
    assert DETAILS_FIELDS2 == "f51,f52,f53,f54,f55"
    assert TEN_DEPTH_FIELDS == FIELDS_TEN_DEPTH
