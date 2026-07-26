"""Stage 1 normalizer maps common wrong strategy file names."""

from __future__ import annotations

from pa_agent.ai.router import route_strategy_files
from pa_agent.ai.stage1_normalizer import normalize_stage1


def test_model_strategy_file_aliases_do_not_override_router():
    obj = {
        "cycle_position": "trading_range",
        "direction": "neutral",
        "diagnosis_confidence": 50,
        "market_phase": "stable",
        "detected_patterns": [],
        "key_signals": [],
        "htf_context": "",
        "entry_setup": "",
        "strategy_files_needed": [
            "交易区间分析识别.txt",
            "交易区间交易策略.txt",
            "宽通道分析识别.txt",
        ],
        "bar_by_bar_summary": [
            {
                "bar": "K1",
                "role": "structure",
                "bar_type": "doji",
                "context_effect": "neutral",
                "follow_through": "pending",
                "trapped_side": "none",
                "reason": "test",
            }
        ],
        "gate_trace": [
            {
                "node_id": "0.1",
                "question": "q",
                "answer": "是",
                "reason": "r",
                "bar_range": "K10-K1",
            }
        ],
        "gate_result": "wait",
    }
    out = normalize_stage1(obj)
    assert out["strategy_files_needed"] == route_strategy_files(out)
    assert "文件13-窄通道与宽通道策略.txt" not in out["strategy_files_needed"]
