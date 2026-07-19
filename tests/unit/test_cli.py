"""Tests for the PyQt-free headless command adapter."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from pa_agent.app_context import AppContext
from pa_agent.cli import EXIT_CONFIG_ERROR, main
from pa_agent.main import main as app_main


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _snapshot_payload() -> dict:
    return {
        "symbol": "TEST",
        "timeframe": "5m",
        "snapshot_ts_local_ms": 1_700_000_000_000,
        "bars": [
            {
                "seq": 1,
                "ts_open": 1_700_000_000,
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 10,
                "closed": True,
            },
            {
                "seq": 2,
                "ts_open": 1_699_999_700,
                "open": 9,
                "high": 11,
                "low": 8,
                "close": 10,
                "volume": 9,
                "closed": True,
            },
        ],
    }


def test_validate_config_emits_structured_result_without_key(tmp_path: Path, capsys) -> None:
    settings_path = tmp_path / "settings.json"
    _write_json(
        settings_path,
        {
            "provider": {
                "model": "test-model",
                "base_url": "https://example.test/v1",
                "api_key": "secret-value",
            },
            "general": {"last_symbol": "TEST", "last_timeframe": "5m"},
        },
    )

    assert main(["validate-config", "--settings", str(settings_path)]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["valid"] is True
    assert payload["provider"]["model"] == "test-model"
    assert payload["provider"]["api_key_configured"] is True
    assert "secret-value" not in captured.out
    assert captured.err == ""


def test_validate_config_invalid_json_uses_config_exit_code(
    tmp_path: Path,
    capsys,
) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{broken", encoding="utf-8")

    assert main(["validate-config", "--settings", str(settings_path)]) == EXIT_CONFIG_ERROR
    assert "JSON 解析失败" in capsys.readouterr().err


def test_snapshot_normalizes_bars_and_non_finite_indicators(
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "input.json"
    _write_json(input_path, _snapshot_payload())

    assert main(["snapshot", "--input", str(input_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pa-agent.snapshot.v1"
    assert payload["symbol"] == "TEST"
    assert len(payload["bars"]) == 2
    assert payload["indicators"]["ema20"][0] is None
    assert payload["indicators"]["atr14"][0] is None


def test_analyze_builds_provider_free_stage1_dry_run(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "input.json"
    _write_json(input_path, _snapshot_payload())
    seen: dict[str, object] = {}

    class _FakeAssembler:
        def build_stage1(self, frame):
            seen["frame"] = frame
            return [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ]

    def fake_bootstrap(cls, **kwargs):
        seen["settings"] = kwargs["settings"]
        return SimpleNamespace(assembler=_FakeAssembler())

    monkeypatch.setattr(AppContext, "bootstrap_headless", classmethod(fake_bootstrap))

    assert main(["analyze", "--input", str(input_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "pa-agent.analysis.v1"
    assert payload["dry_run"] is True
    assert payload["provider_called"] is False
    assert payload["stage1_prompt"]["message_count"] == 2
    assert seen["frame"].symbol == "TEST"


def test_main_dispatches_headless_without_importing_qt(tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "input.json"
    _write_json(input_path, _snapshot_payload())

    assert app_main(["headless", "snapshot", "--input", str(input_path)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "pa-agent.snapshot.v1"
