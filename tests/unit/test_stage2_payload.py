"""Tests for Stage 2 payload preparation helpers."""
from __future__ import annotations

from typing import Any

from pa_agent.ai import stage2_normalizer
from pa_agent.gui.stage2_payload import merge_stage2_for_panels, prepare_stage2_for_ui


def test_merge_stage2_for_panels_returns_empty_for_non_dict() -> None:
    assert merge_stage2_for_panels(None) == {}
    assert merge_stage2_for_panels(["bad"]) == {}


def test_merge_stage2_for_panels_hoists_top_level_predictions() -> None:
    payload = merge_stage2_for_panels(
        {
            "decision": {"order_type": "\u9650\u4ef7\u5355"},
            "next_bar_prediction": {"direction": "bullish"},
            "next_cycle_prediction": {"direction": "neutral"},
        }
    )

    assert payload == {
        "order_type": "\u9650\u4ef7\u5355",
        "next_bar_prediction": {"direction": "bullish"},
        "next_cycle_prediction": {"direction": "neutral"},
    }


def test_prepare_stage2_for_ui_deepcopies_before_normalizing(monkeypatch) -> None:
    original = {"decision": {"order_type": "\u5e02\u4ef7\u5355"}}
    stage1_json = {"market": "context"}
    calls: list[tuple[dict[str, Any], dict[str, Any] | None, bool]] = []

    def fake_ensure(
        out: dict[str, Any],
        *,
        stage1_json: dict[str, Any] | None = None,
        skip_next_bar: bool = False,
    ) -> None:
        calls.append((out, stage1_json, skip_next_bar))
        out["decision"]["normalized"] = True
        out["next_bar_prediction"] = {"direction": "bearish"}

    monkeypatch.setattr(stage2_normalizer, "ensure_stage2_predictions", fake_ensure)

    payload = prepare_stage2_for_ui(original, stage1_json=stage1_json)

    assert payload == {
        "order_type": "\u5e02\u4ef7\u5355",
        "normalized": True,
        "next_bar_prediction": {"direction": "bearish"},
    }
    assert original == {"decision": {"order_type": "\u5e02\u4ef7\u5355"}}
    assert calls[0][1] is stage1_json
    assert calls[0][2] is False


def test_prepare_stage2_for_ui_respects_skip_next_bar(monkeypatch) -> None:
    original = {
        "decision": {"order_type": "\u4e0d\u4e0b\u5355"},
        "next_bar_prediction": {"direction": "bullish"},
        "next_cycle_prediction": {"direction": "neutral"},
    }

    def fake_ensure(
        out: dict[str, Any],
        *,
        stage1_json: dict[str, Any] | None = None,
        skip_next_bar: bool = False,
    ) -> None:
        assert "next_bar_prediction" not in out
        assert stage1_json is None
        assert skip_next_bar is True

    monkeypatch.setattr(stage2_normalizer, "ensure_stage2_predictions", fake_ensure)

    assert prepare_stage2_for_ui(original, skip_next_bar=True) == {
        "order_type": "\u4e0d\u4e0b\u5355",
        "next_cycle_prediction": {"direction": "neutral"},
    }
