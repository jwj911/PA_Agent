"""Tests for East Money quote payload parsers."""

from __future__ import annotations

from pa_agent.data.eastmoney_quote import parse_order_book_payload, parse_tick_lines


def test_parse_order_book_payload_free_depth_fltt2():
    payload = {
        "f57": "600519",
        "f58": "Kweichow Moutai",
        "f43": 1688.88,
        "f170": 1.23,
        "f46": 1670.0,
        "f44": 1690.0,
        "f45": 1660.0,
        "f60": 1668.0,
        "f47": 12345,
        "f48": 987654.0,
        "f39": 1688.9,
        "f40": 10,
        "f37": 1689.0,
        "f38": 20,
        "f19": 1688.8,
        "f20": 30,
        "f17": 1688.7,
        "f18": 40,
    }

    book = parse_order_book_payload(payload, fltt=2)

    assert book is not None
    assert book.code == "600519"
    assert book.name == "Kweichow Moutai"
    assert book.price == 1688.88
    assert book.pct_chg == 1.23
    assert book.depth_levels == 5
    assert book.depth_source == "push2_free"
    assert [(level.price, level.volume) for level in book.asks] == [
        (1688.9, 10),
        (1689.0, 20),
    ]
    assert [(level.price, level.volume) for level in book.bids] == [
        (1688.8, 30),
        (1688.7, 40),
    ]


def test_parse_order_book_payload_l2_fltt1_scales_cents():
    payload = {
        "f57": "000001",
        "f58": "Ping An Bank",
        "f43": 1234,
        "f170": 125,
        "f46": 1200,
        "f44": 1240,
        "f45": 1190,
        "f60": 1210,
        "f47": 500,
        "f48": 6000.0,
        "f39": 1235,
        "f40": 11,
        "f29": 1240,
        "f30": 16,
        "f19": 1233,
        "f20": 21,
        "f9": 1228,
        "f10": 26,
    }

    book = parse_order_book_payload(payload)

    assert book is not None
    assert book.price == 12.34
    assert book.pct_chg == 1.25
    assert book.open == 12.0
    assert book.prev_close == 12.1
    assert book.depth_levels == 10
    assert book.depth_source == "push2_l2"
    assert [(level.price, level.volume) for level in book.asks] == [
        (12.35, 11),
        (12.4, 16),
    ]
    assert [(level.price, level.volume) for level in book.bids] == [
        (12.33, 21),
        (12.28, 26),
    ]


def test_parse_tick_lines_filters_invalid_and_tails():
    ticks = parse_tick_lines(
        [
            "",
            "09:30:01,12.30,100,x,1",
            "bad,line",
            "09:30:02,12.31,200,x,2",
            "09:30:03,12.32,300,x,0",
        ],
        tail=2,
    )

    assert [(tick.time, tick.price, tick.volume, tick.side_hint) for tick in ticks] == [
        ("09:30:02", 12.31, 200, "卖"),
        ("09:30:03", 12.32, 300, "中性"),
    ]
