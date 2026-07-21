"""Tests for the PyQt-free headless command adapter."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from pa_agent.ai.deepseek_client import AIReply, AIUsage
from pa_agent.app_context import AppContext
from pa_agent.cli import EXIT_CONFIG_ERROR, EXIT_PROVIDER_ERROR, main
from pa_agent.config.settings import Settings
from pa_agent.main import main as app_main
from pa_agent.records.pending_writer import PendingWriter
from tests.fixtures.ai_payloads import VALID_STAGE1, VALID_STAGE2
from tests.fixtures.validators import schema_test_validator


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


def _long_snapshot_payload() -> dict:
    bars = []
    for index in range(20):
        base = 2000 + (19 - index) * 2
        bars.append(
            {
                "seq": index + 1,
                "ts_open": 1_700_000_000 - index * 60_000,
                "open": base,
                "high": base + 10,
                "low": base - 10,
                "close": base + 5,
                "volume": 100,
                "closed": True,
            }
        )
    return {
        "symbol": "TEST",
        "timeframe": "5m",
        "snapshot_ts_local_ms": 1_700_000_000_000,
        "bars": bars,
    }


def _reply(payload: dict) -> AIReply:
    content = json.dumps(payload, ensure_ascii=False)
    usage = AIUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return AIReply(
        content=content,
        reasoning_content="",
        raw={"content": content},
        usage=usage,
        request_id="fake",
        latency_ms=1,
    )


class _FakeClient:
    def __init__(self, replies: list[object]) -> None:
        self._replies = list(replies)
        self.calls = 0

    def stream_chat(self, _messages, **_kwargs):
        self.calls += 1
        reply = self._replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


class _FakeAssembler:
    def build_stage1(self, _frame, **_kwargs):
        return [{"role": "user", "content": "stage1"}]

    def build_stage2_continuation(self, **_kwargs):
        return [{"role": "user", "content": "stage2"}]


def _fake_headless_context(
    *,
    client: _FakeClient,
    records_dir: Path,
    settings: Settings,
    event_sink,
) -> SimpleNamespace:
    return SimpleNamespace(
        settings=settings,
        event_sink=event_sink,
        client=client,
        assembler=_FakeAssembler(),
        router=lambda _stage1: [],
        validator=schema_test_validator(),
        pending_writer=PendingWriter(records_dir),
        exp_reader=SimpleNamespace(),
    )


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


def test_analyze_run_persists_final_record_and_jsonl_events(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "input.json"
    records_dir = tmp_path / "records"
    events_path = tmp_path / "events.jsonl"
    _write_json(input_path, _long_snapshot_payload())
    client = _FakeClient([_reply(VALID_STAGE1), _reply(VALID_STAGE2)])

    def fake_bootstrap(cls, **kwargs):
        return _fake_headless_context(
            client=client,
            records_dir=kwargs["records_pending_dir"],
            settings=kwargs["settings"],
            event_sink=kwargs["event_sink"],
        )

    monkeypatch.setattr(AppContext, "bootstrap_headless", classmethod(fake_bootstrap))

    assert (
        main(
            [
                "analyze",
                "--input",
                str(input_path),
                "--run",
                "--records-dir",
                str(records_dir),
                "--events",
                str(events_path),
                "--correlation-id",
                "run-final",
            ]
        )
        == 0
    )

    result = json.loads(capsys.readouterr().out)
    assert result["dry_run"] is False
    assert result["provider_called"] is True
    assert result["status"] == "completed"
    assert result["events"] == [
        "Stage1Started",
        "Stage1Done",
        "Stage2Started",
        "Stage2Done",
        "RecordSaved",
    ]
    assert client.calls == 2

    record_paths = list(records_dir.glob("*.json"))
    assert len(record_paths) == 1
    record_payload = json.loads(record_paths[0].read_text(encoding="utf-8"))
    assert record_payload["stage1_diagnosis"] is not None
    assert record_payload["stage2_decision"] is not None
    assert record_payload["exception"] is None

    event_lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [event["payload"]["event"] for event in event_lines] == result["events"]
    assert {event["correlation_id"] for event in event_lines} == {"run-final"}


def test_analyze_run_maps_timeout_and_persists_partial_record(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_path = tmp_path / "input.json"
    records_dir = tmp_path / "records"
    _write_json(input_path, _long_snapshot_payload())
    settings = Settings()
    client = _FakeClient([_reply(VALID_STAGE1), TimeoutError("offline timeout")])

    def fake_bootstrap(cls, **kwargs):
        return _fake_headless_context(
            client=client,
            records_dir=kwargs["records_pending_dir"],
            settings=settings,
            event_sink=kwargs["event_sink"],
        )

    monkeypatch.setattr(AppContext, "bootstrap_headless", classmethod(fake_bootstrap))

    assert (
        main(
            [
                "analyze",
                "--input",
                str(input_path),
                "--run",
                "--records-dir",
                str(records_dir),
                "--correlation-id",
                "run-partial",
            ]
        )
        == EXIT_PROVIDER_ERROR
    )

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "partial"
    assert result["exit_code"] == EXIT_PROVIDER_ERROR
    assert result["record"]["stage1_complete"] is True
    assert result["record"]["stage2_complete"] is False
    assert result["record"]["exception"]["type"] == "network_error"

    record_paths = list(records_dir.glob("*.json"))
    assert len(record_paths) == 1
    record_payload = json.loads(record_paths[0].read_text(encoding="utf-8"))
    assert record_payload["_partial_reason"] == "network_error"
    assert record_payload["exception"]["type"] == "network_error"


def test_bootstrap_headless_accepts_injected_client(tmp_path: Path) -> None:
    fake_client = object()

    ctx = AppContext.bootstrap_headless(
        settings=Settings(),
        client=fake_client,
        records_pending_dir=tmp_path,
        sync_providers=False,
        configure_logs=False,
    )

    assert ctx.client is fake_client


def test_main_dispatches_headless_without_importing_qt(tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "input.json"
    _write_json(input_path, _snapshot_payload())

    assert app_main(["headless", "snapshot", "--input", str(input_path)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "pa-agent.snapshot.v1"
