"""Tests for Stage 2 business-rule validators."""

from __future__ import annotations

from types import SimpleNamespace

from pa_agent.ai import business_rules


def test_check_no_order_invariant_rejects_prices_on_no_order() -> None:
    error = business_rules.check_no_order_invariant(
        {
            "decision": {
                "order_type": "不下单",
                "entry_price": 100.0,
                "stop_loss_price": None,
            }
        }
    )

    assert error == {
        "fields": ["entry_price"],
        "allowed": {"entry_price": [None]},
    }


def test_check_no_order_invariant_requires_prices_for_trade_orders() -> None:
    error = business_rules.check_no_order_invariant(
        {
            "decision": {
                "order_type": "限价单",
                "entry_price": 100.0,
                "take_profit_price": None,
                "take_profit_price_2": 120.0,
                "stop_loss_price": 95.0,
                "order_direction": "做多",
            }
        }
    )

    assert error is not None
    assert error["fields"] == ["take_profit_price"]
    assert error["allowed"]["take_profit_price"] == ["<finite number>"]


def test_check_breakout_order_basis_requires_bar_extreme_and_rule() -> None:
    error = business_rules.check_breakout_order_basis(
        {
            "decision": {
                "order_type": "突破单",
                "order_direction": "做多",
                "entry_basis_extreme": "low",
            }
        }
    )

    assert error is not None
    assert error["fields"] == [
        "decision.entry_basis_bar",
        "decision.entry_rule",
        "decision.entry_basis_extreme",
    ]
    assert error["allowed"]["decision.entry_basis_extreme"] == ["做多突破单必须使用 high"]


def test_check_breakout_price_extreme_validates_entry_against_bar() -> None:
    frame = SimpleNamespace(bars=[SimpleNamespace(seq=3, high=100.0, low=90.0)])
    decision = {
        "order_type": "突破单",
        "order_direction": "做多",
        "entry_basis_bar": "K3",
        "entry_basis_extreme": "high",
    }

    assert business_rules.check_breakout_price_extreme(
        {"decision": {**decision, "entry_price": 99.5}},
        frame,
    ) == ["做多突破单 entry_price=99.5 must be above K3.high=100"]
    assert (
        business_rules.check_breakout_price_extreme(
            {"decision": {**decision, "entry_price": 100.5}},
            frame,
        )
        == []
    )


def test_k_seq_and_stage2_reason_helpers_are_defensive() -> None:
    frame = SimpleNamespace(bars=[SimpleNamespace(seq=1), SimpleNamespace(seq=12)])

    assert business_rules._parse_k_seq("K12") == 12
    assert business_rules._parse_k_seq("signal k 3") == 3
    assert business_rules._parse_k_seq("bad") is None
    assert business_rules._bar_by_seq(frame, 12) is frame.bars[1]
    assert business_rules._bar_by_seq(frame, 99) is None
    assert (
        business_rules._all_stage2_reasons(
            {
                "decision": {"reasoning": "alpha", "risk_assessment": "beta"},
                "decision_trace": [{"reason": "gamma"}, "noise"],
            }
        )
        == "alpha\n\nbeta\ngamma"
    )


def test_check_signal_chain_requires_reasoning_for_weak_signal() -> None:
    obj = {
        "decision": {"order_type": "限价单", "trade_confidence": 40},
        "bar_analysis": {
            "signal_bar": {"bar": "K3", "quality": "weak", "pattern": "weak_close"},
            "entry_bar": {"bar": "K1", "freshness": "fresh", "follow_through": True},
        },
        "decision_trace": [],
    }

    errors = business_rules.check_signal_chain(obj)
    assert errors == [
        "weak/invalid signal_bar requires explicit §9 reasoning for why the setup remains tradable"
    ]

    obj["decision_trace"] = [{"reason": "tr_boundary exception"}]
    assert business_rules.check_signal_chain(obj) == []
