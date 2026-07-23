"""PyQt-free command-line adapter for headless PA Agent workflows."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from pa_agent.config.settings import Settings
from pa_agent.data.base import KlineBar, KlineFrame, normalize_kline_bar
from pa_agent.data.snapshot import compute_indicators
from pa_agent.util.event_sink import JsonlEventSink, NullEventSink
from pa_agent.util.events import AppEvent
from pa_agent.util.timefmt import now_local_ms

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2
EXIT_DATA_ERROR = 3
EXIT_PROVIDER_ERROR = 4
EXIT_VALIDATION_ERROR = 5
EXIT_CANCELLED = 130

_SNAPSHOT_SCHEMA = "pa-agent.snapshot.v1"
_ANALYSIS_SCHEMA = "pa-agent.analysis.v1"


class CliError(Exception):
    """Expected command-line failure with a stable process exit code."""

    def __init__(self, message: str, *, code: int) -> None:
        super().__init__(message)
        self.code = code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pa-agent headless")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate-config",
        help="validate a settings JSON file without starting Qt or a data source",
    )
    validate.add_argument("--settings", type=Path, help="settings JSON path")
    validate.add_argument("--output", type=Path, help="write JSON result to this path")

    snapshot = commands.add_parser(
        "snapshot",
        help="normalize a JSON K-line snapshot without network access",
    )
    snapshot.add_argument("--input", required=True, type=Path, help="input snapshot JSON path")
    snapshot.add_argument("--output", type=Path, help="write normalized JSON to this path")
    snapshot.add_argument("--symbol", help="override the input symbol")
    snapshot.add_argument("--timeframe", help="override the input timeframe")

    analyze = commands.add_parser(
        "analyze",
        help="validate a snapshot and optionally run the two-stage provider workflow",
    )
    analyze.add_argument("--input", required=True, type=Path, help="input snapshot JSON path")
    analyze.add_argument("--output", type=Path, help="write JSON result to this path")
    analyze.add_argument("--settings", type=Path, help="optional settings JSON path")
    analyze.add_argument("--prompt-dir", type=Path, help="optional prompt directory")
    analyze.add_argument(
        "--records-dir",
        type=Path,
        help="optional analysis record directory for --run",
    )
    analyze.add_argument(
        "--events",
        type=Path,
        help="write --run orchestrator events to a JSONL file",
    )
    analyze.add_argument(
        "--correlation-id",
        help="correlation id for --run events (generated when omitted)",
    )
    analyze.add_argument(
        "--run",
        "--execute",
        dest="run",
        action="store_true",
        help="opt in to provider calls and execute both analysis stages",
    )
    analyze.add_argument("--symbol", help="override the input symbol")
    analyze.add_argument("--timeframe", help="override the input timeframe")

    return parser


def _read_json(path: Path) -> Any:
    try:
        text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(f"无法读取 JSON 文件 {path}: {exc}", code=EXIT_DATA_ERROR) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CliError(f"JSON 解析失败 {path}: {exc}", code=EXIT_DATA_ERROR) from exc


def _write_json(payload: Mapping[str, Any], output: Path | None) -> None:
    text = json.dumps(_json_safe(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output is None or str(output) == "-":
        sys.stdout.write(text)
        return
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise CliError(f"无法写入 JSON 文件 {output}: {exc}", code=EXIT_DATA_ERROR) from exc


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _resolve_settings_path(path: Path | None) -> Path:
    if path is not None:
        return path
    from pa_agent.config.paths import SETTINGS_JSON_PATH

    return SETTINGS_JSON_PATH


def _load_settings_file(path: Path | None) -> tuple[Path, dict[str, Any], Settings]:
    settings_path = _resolve_settings_path(path)
    try:
        raw = _read_json(settings_path)
    except CliError as exc:
        raise CliError(str(exc), code=EXIT_CONFIG_ERROR) from exc
    if not isinstance(raw, dict):
        raise CliError("settings JSON 根节点必须是对象。", code=EXIT_CONFIG_ERROR)
    try:
        settings = Settings.model_validate(raw)
    except PydanticValidationError as exc:
        raise CliError(f"settings 配置校验失败: {exc}", code=EXIT_CONFIG_ERROR) from exc
    return settings_path, raw, settings


def _validate_config(args: argparse.Namespace) -> None:
    settings_path, raw, settings = _load_settings_file(args.settings)
    provider = raw.get("provider")
    provider_raw = provider if isinstance(provider, dict) else {}
    _write_json(
        {
            "command": "validate-config",
            "valid": True,
            "settings_path": str(settings_path.resolve()),
            "provider": {
                "model": settings.provider.model,
                "base_url": settings.provider.base_url,
                "api_key_configured": bool(
                    str(provider_raw.get("api_key") or "").strip()
                    or str(provider_raw.get("api_key_encrypted") or "").strip()
                ),
            },
            "general": {
                "data_source": settings.general.last_data_source,
                "symbol": settings.general.last_symbol,
                "timeframe": settings.general.last_timeframe,
            },
        },
        args.output,
    )


def _coerce_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise CliError(f"字段 {field} 必须是布尔值。", code=EXIT_DATA_ERROR)


def _coerce_bar(raw: Any, index: int) -> KlineBar:
    if not isinstance(raw, Mapping):
        raise CliError(f"bars[{index}] 必须是对象。", code=EXIT_DATA_ERROR)
    missing = [field for field in ("ts_open", "open", "high", "low", "close") if field not in raw]
    if missing:
        raise CliError(
            f"bars[{index}] 缺少字段: {', '.join(missing)}。",
            code=EXIT_DATA_ERROR,
        )
    try:
        bar = KlineBar(
            seq=int(raw.get("seq", index + 1)),
            ts_open=float(raw["ts_open"]),
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            volume=float(raw.get("volume", 0.0)),
            amount=float(raw.get("amount", 0.0)),
            pct_chg=(float(raw["pct_chg"]) if raw.get("pct_chg") is not None else None),
            closed=_coerce_bool(raw.get("closed", True), field=f"bars[{index}].closed"),
        )
    except (TypeError, ValueError) as exc:
        raise CliError(f"bars[{index}] 数值字段无效: {exc}", code=EXIT_DATA_ERROR) from exc
    return normalize_kline_bar(bar)


def _snapshot_payload(raw: Any, *, symbol: str | None, timeframe: str | None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CliError("snapshot JSON 根节点必须是对象。", code=EXIT_DATA_ERROR)

    meta = raw.get("meta")
    meta_raw = meta if isinstance(meta, Mapping) else {}
    bars_raw = raw.get("bars")
    if bars_raw is None:
        bars_raw = raw.get("kline_data")
    if not isinstance(bars_raw, Sequence) or isinstance(bars_raw, (str, bytes)):
        raise CliError("snapshot JSON 必须包含 bars 数组或 kline_data 数组。", code=EXIT_DATA_ERROR)

    resolved_symbol = symbol or raw.get("symbol") or meta_raw.get("symbol")
    resolved_timeframe = timeframe or raw.get("timeframe") or meta_raw.get("timeframe")
    if not str(resolved_symbol or "").strip() or not str(resolved_timeframe or "").strip():
        raise CliError("snapshot 必须提供非空 symbol 和 timeframe。", code=EXIT_DATA_ERROR)

    bars = tuple(_coerce_bar(item, index) for index, item in enumerate(bars_raw))
    if not bars:
        raise CliError("snapshot bars 不能为空。", code=EXIT_DATA_ERROR)
    snapshot_ts = raw.get("snapshot_ts_local_ms", meta_raw.get("timestamp_local_ms"))
    try:
        snapshot_ts_ms = int(snapshot_ts) if snapshot_ts is not None else now_local_ms()
    except (TypeError, ValueError) as exc:
        raise CliError("snapshot_ts_local_ms 必须是整数。", code=EXIT_DATA_ERROR) from exc

    frame = KlineFrame(
        symbol=str(resolved_symbol),
        timeframe=str(resolved_timeframe),
        bars=bars,
        indicators=compute_indicators(list(bars)),
        snapshot_ts_local_ms=snapshot_ts_ms,
    )
    return _frame_to_payload(frame)


def _frame_to_payload(frame: KlineFrame) -> dict[str, Any]:
    return {
        "schema": _SNAPSHOT_SCHEMA,
        "symbol": frame.symbol,
        "timeframe": frame.timeframe,
        "snapshot_ts_local_ms": frame.snapshot_ts_local_ms,
        "bars": [
            {
                "seq": bar.seq,
                "ts_open": bar.ts_open,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "amount": bar.amount,
                "pct_chg": bar.pct_chg,
                "closed": bar.closed,
            }
            for bar in frame.bars
        ],
        "indicators": {
            "ema20": list(frame.indicators.ema20),
            "atr14": list(frame.indicators.atr14),
        },
    }


def _load_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    return _snapshot_payload(
        _read_json(args.input),
        symbol=getattr(args, "symbol", None),
        timeframe=getattr(args, "timeframe", None),
    )


def _snapshot(args: argparse.Namespace) -> None:
    _write_json(_load_snapshot(args), args.output)


def _prompt_stats(messages: list[dict[str, Any]]) -> dict[str, Any]:
    chars_by_role: dict[str, int] = {}
    for message in messages:
        role = str(message.get("role", "unknown"))
        content = message.get("content", "")
        chars_by_role[role] = chars_by_role.get(role, 0) + len(str(content))
    return {
        "message_count": len(messages),
        "chars": sum(chars_by_role.values()),
        "chars_by_role": chars_by_role,
    }


def _record_path(ctx: Any, record: Any) -> Path | None:
    """Resolve the record path from the existing PendingWriter contract."""
    pending_writer = getattr(ctx, "pending_writer", None)
    pending_dir = getattr(pending_writer, "pending_dir", None)
    if pending_dir is None:
        pending_dir = getattr(pending_writer, "_pending_dir", None)
    if pending_dir is None:
        return None
    from pa_agent.records.pending_writer import build_record_basename

    try:
        return Path(pending_dir) / f"{build_record_basename(record)}.json"
    except (TypeError, ValueError):
        return None


def _public_record_exception(
    record: Any,
    settings: Settings | None,
) -> dict[str, Any] | None:
    exception = getattr(record, "exception", None)
    if not isinstance(exception, Mapping):
        return None
    # Raw provider text is retained in the persisted record but is not echoed
    # by the CLI result, keeping stdout suitable for automation and logs.
    public_exception = {key: value for key, value in exception.items() if key != "raw_text"}
    if "message" in public_exception:
        public_exception["message"] = _masked_error_text(
            public_exception["message"],
            settings,
        )
    return public_exception


def _record_exit_code(record: Any, event_names: Sequence[str]) -> int:
    """Map orchestrator terminal state to the stable headless exit codes."""
    if "Cancelled" in event_names:
        return EXIT_CANCELLED
    exception = getattr(record, "exception", None)
    error_type = exception.get("type") if isinstance(exception, Mapping) else None
    if error_type == "user_cancelled":
        return EXIT_CANCELLED
    if error_type == "insufficient_data":
        return EXIT_DATA_ERROR
    if error_type == "validation_error":
        return EXIT_VALIDATION_ERROR
    if error_type in {"network_error", "provider_error", "program_error"}:
        return EXIT_PROVIDER_ERROR
    return EXIT_OK if exception is None else EXIT_PROVIDER_ERROR


def _runner_exception_type(exc: Exception) -> str:
    try:
        from pa_agent.ai.deepseek_client import CancelledError

        if isinstance(exc, CancelledError):
            return "user_cancelled"
    except ImportError:
        pass

    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator

    if TwoStageOrchestrator._is_network_error(exc):
        return "network_error"
    if isinstance(exc, PydanticValidationError):
        return "validation_error"
    return "program_error"


def _masked_error_text(value: object, settings: Settings | None) -> str:
    text = str(value)
    api_key = getattr(getattr(settings, "provider", None), "api_key", "") or ""
    if api_key:
        from pa_agent.util.mask_secret import mask_secret

        text = text.replace(api_key, mask_secret(api_key))
    return text


def _persist_runner_error(ctx: Any, frame: KlineFrame, exc: Exception) -> Any:
    """Persist an unexpected runner exception using the existing partial schema."""
    from pa_agent.orchestrator.two_stage import _build_empty_record

    record = _build_empty_record(frame, getattr(ctx, "settings", None))
    error_type = _runner_exception_type(exc)
    record = record.model_copy(
        update={
            "exception": {
                "type": error_type,
                "stage": "runner",
                "message": _masked_error_text(exc, getattr(ctx, "settings", None)),
            }
        }
    )
    pending_writer = getattr(ctx, "pending_writer", None)
    if pending_writer is not None:
        pending_writer.save_partial(record, error_type)
    return record


def _run_analyze(
    *,
    args: argparse.Namespace,
    snapshot: dict[str, Any],
    frame: KlineFrame,
    settings: Settings,
) -> int:
    """Run the existing TwoStageOrchestrator through a headless adapter."""
    from pa_agent.app_context import AppContext
    from pa_agent.headless import HeadlessAdapterError, HeadlessAnalysisAdapter

    correlation_id = str(getattr(args, "correlation_id", None) or uuid.uuid4().hex)
    event_sink = (
        JsonlEventSink(args.events)
        if getattr(args, "events", None) is not None
        else NullEventSink()
    )
    try:
        bootstrap_kwargs: dict[str, Any] = {
            "settings": settings,
            "prompt_dir": args.prompt_dir,
            "event_sink": event_sink,
            "sync_providers": False,
            "configure_logs": False,
        }
        records_dir = getattr(args, "records_dir", None)
        if records_dir is not None:
            bootstrap_kwargs["records_pending_dir"] = records_dir
        try:
            ctx = AppContext.bootstrap_headless(**bootstrap_kwargs)
        except Exception as exc:
            raise CliError(
                "headless core 装配失败: " f"{_masked_error_text(exc, settings)}",
                code=EXIT_PROVIDER_ERROR,
            ) from exc

        try:
            result = HeadlessAnalysisAdapter(
                ctx,
                event_sink=event_sink,
                correlation_id=correlation_id,
            ).run(frame)
            record = result.record
            event_names = list(result.event_names)
        except HeadlessAdapterError as exc:
            raise CliError(str(exc), code=EXIT_PROVIDER_ERROR) from exc
        except Exception as exc:
            record = _persist_runner_error(ctx, frame, exc)
            event_names.append("RunnerFailed")
            event_sink.publish(AppEvent.orchestrator("RunnerFailed", correlation_id=correlation_id))

        record_path = _record_path(ctx, record)
        exit_code = _record_exit_code(record, event_names)
        if exit_code == EXIT_CANCELLED:
            status = "cancelled"
        elif getattr(record, "exception", None) is None:
            status = "completed"
        else:
            status = "partial"

        _write_json(
            {
                "command": "analyze",
                "schema": _ANALYSIS_SCHEMA,
                "dry_run": False,
                "provider_called": any(
                    name in event_names for name in ("Stage1Started", "Stage2Started")
                ),
                "status": status,
                "exit_code": exit_code,
                "correlation_id": correlation_id,
                "events": event_names,
                "record_path": str(record_path.resolve()) if record_path else None,
                "record": {
                    "symbol": snapshot["symbol"],
                    "timeframe": snapshot["timeframe"],
                    "stage1_complete": getattr(record, "stage1_diagnosis", None) is not None,
                    "stage2_complete": getattr(record, "stage2_decision", None) is not None,
                    "exception": _public_record_exception(record, settings),
                },
            },
            args.output,
        )
        return exit_code
    finally:
        close = getattr(event_sink, "close", None)
        if close is not None:
            close()


def _analyze(args: argparse.Namespace) -> int:
    snapshot = _load_snapshot(args)
    if args.settings is None:
        settings = Settings()
    else:
        _, _, settings = _load_settings_file(args.settings)

    from pa_agent.app_context import AppContext

    bars = tuple(_coerce_bar(item, index) for index, item in enumerate(snapshot["bars"]))
    frame = KlineFrame(
        symbol=snapshot["symbol"],
        timeframe=snapshot["timeframe"],
        bars=bars,
        indicators=compute_indicators(list(bars)),
        snapshot_ts_local_ms=int(snapshot["snapshot_ts_local_ms"]),
    )
    if getattr(args, "run", False):
        return _run_analyze(
            args=args,
            snapshot=snapshot,
            frame=frame,
            settings=settings,
        )

    try:
        ctx = AppContext.bootstrap_headless(
            settings=settings,
            prompt_dir=args.prompt_dir,
            sync_providers=False,
            configure_logs=False,
        )
    except Exception as exc:
        raise CliError(f"headless core 装配失败: {exc}", code=EXIT_PROVIDER_ERROR) from exc
    if ctx.assembler is None:
        raise CliError("headless core 未装配 PromptAssembler。", code=EXIT_PROVIDER_ERROR)
    try:
        messages = ctx.assembler.build_stage1(frame)
    except Exception as exc:
        raise CliError(f"Stage 1 dry-run 组装失败: {exc}", code=EXIT_VALIDATION_ERROR) from exc

    _write_json(
        {
            "command": "analyze",
            "schema": _ANALYSIS_SCHEMA,
            "dry_run": True,
            "provider_called": False,
            "status": "validated",
            "snapshot": snapshot,
            "stage1_prompt": _prompt_stats(messages),
        },
        args.output,
    )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the headless command adapter and return a process exit code."""
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "validate-config":
            _validate_config(args)
        elif args.command == "snapshot":
            _snapshot(args)
        elif args.command == "analyze":
            return _analyze(args)
        else:  # pragma: no cover - argparse enforces the command set.
            raise CliError(f"未知 headless 命令: {args.command}", code=EXIT_CONFIG_ERROR)
    except CliError as exc:
        print(f"pa-agent headless: {exc}", file=sys.stderr)
        return exc.code
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
