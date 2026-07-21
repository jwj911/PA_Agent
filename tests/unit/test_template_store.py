"""Tests for the manifest-backed prompt template store."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from pa_agent.ai import strategy_files as sf
from pa_agent.ai.prompt_assembler import PromptAssembler
from pa_agent.ai.prompting import (
    TEMPLATE_MANIFEST,
    TemplateContext,
    TemplateSpec,
    TemplateStore,
    TemplateStoreError,
    template_files_for_stage,
)
from pa_agent.data.snapshot import build_analysis_frame
from tests.fixtures.kline_bars import make_newest_first_bars

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt_engineering"
GOLDEN_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "prompt_golden.json"


def _strategy_registry_values() -> set[str]:
    return {value for name, value in vars(sf).items() if name.isupper() and isinstance(value, str)}


def test_manifest_covers_strategy_registry_and_stage_contracts() -> None:
    manifest_names = {spec.name for spec in TEMPLATE_MANIFEST}

    assert manifest_names == _strategy_registry_values()
    assert template_files_for_stage("stage1") == (
        sf.PERSONA,
        sf.BINARY_DECISION,
        sf.MARKET_DIAGNOSIS,
        sf.KLINE_SIGNAL,
    )
    assert sf.PERSONA in template_files_for_stage("stage2")
    assert sf.MARKET_DIAGNOSIS not in template_files_for_stage("stage2")
    assert all(spec.version == "v1" for spec in TEMPLATE_MANIFEST)


def test_template_store_matches_utf8_golden_snapshots() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    store = TemplateStore(PROMPT_DIR)
    names = [entry["name"] for entry in golden["templates"]]
    actual = [asdict(snapshot) for snapshot in store.snapshots(names)]

    assert golden["manifest_version"] == "v1"
    assert names == [spec.name for spec in TEMPLATE_MANIFEST]
    assert actual == golden["templates"]

    assembler = PromptAssembler(prompt_dir=PROMPT_DIR)
    system_prompt = assembler._build_stage1_system_prompt()
    encoded = system_prompt.encode("utf-8")
    expected = golden["shared_system_prompt"]
    assert {
        "byte_length": len(encoded),
        "char_length": len(system_prompt),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    } == expected
    assert assembler._build_stage2_system_prompt() == system_prompt

    legacy = PromptAssembler(prompt_dir=PROMPT_DIR, use_template_store=False)
    assert (
        assembler._build_shared_system_prompt_inner() == legacy._build_shared_system_prompt_inner()
    )

    frame = build_analysis_frame(
        make_newest_first_bars(25, with_forming=False),
        20,
        "TEST",
        "5m",
    )
    assert frame is not None
    assert assembler.build_stage1(frame) == legacy.build_stage1(frame)


def test_stage2_and_continuation_match_legacy_template_loading() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["stage2_fixture"]
    frame = build_analysis_frame(
        make_newest_first_bars(golden["bar_count"], with_forming=False),
        20,
        golden["symbol"],
        golden["timeframe"],
    )
    assert frame is not None

    stage1_json = golden["stage1_json"]
    strategy_files = golden["strategy_files"]
    assembler = PromptAssembler(prompt_dir=PROMPT_DIR)
    legacy = PromptAssembler(prompt_dir=PROMPT_DIR, use_template_store=False)

    standalone = assembler.build_stage2(frame, stage1_json, strategy_files, [])
    assert standalone == legacy.build_stage2(
        frame,
        stage1_json,
        strategy_files,
        [],
    )

    stage1_messages = assembler.build_stage1(frame)
    continuation_kwargs = {
        "frame": frame,
        "stage1_messages": stage1_messages,
        "stage1_reply_content": golden["reply"],
        "stage1_json": stage1_json,
        "strategy_files": strategy_files,
        "experience_entries": [],
    }
    continuation_standalone = assembler.build_stage2_continuation(
        **continuation_kwargs,
        use_prefix_chain=False,
    )
    continuation_prefix = assembler.build_stage2_continuation(
        **continuation_kwargs,
        use_prefix_chain=True,
    )

    def snapshots(messages: list[dict]) -> list[dict[str, str | int]]:
        return [
            {
                "role": message["role"],
                "byte_length": len(message["content"].encode("utf-8")),
                "sha256": hashlib.sha256(message["content"].encode("utf-8")).hexdigest(),
            }
            for message in messages
        ]

    assert snapshots(standalone) == golden["snapshots"]["standalone"]
    assert snapshots(continuation_standalone) == golden["snapshots"]["continuation_standalone"]
    assert snapshots(continuation_prefix) == golden["snapshots"]["continuation_prefix"]

    for use_prefix_chain in (False, True):
        assert assembler.build_stage2_continuation(
            **continuation_kwargs,
            use_prefix_chain=use_prefix_chain,
        ) == legacy.build_stage2_continuation(
            **continuation_kwargs,
            use_prefix_chain=use_prefix_chain,
        )


def test_template_store_rejects_unknown_template_and_wrong_stage() -> None:
    store = TemplateStore(PROMPT_DIR)

    with pytest.raises(TemplateStoreError, match="Unknown prompt template"):
        store.load("unknown.txt")
    with pytest.raises(TemplateStoreError, match="not assigned to stage"):
        store.load(sf.MARKET_DIAGNOSIS, stage="stage2")


def test_template_store_import_is_pyqt_free(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from pa_agent.ai.prompting import TemplateStore

TemplateStore(Path(r"PLACEHOLDER"))
assert "pa_agent.util.event_bus" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", code.replace("PLACEHOLDER", str(tmp_path))],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_template_store_cache_is_explicitly_invalidated(tmp_path: Path) -> None:
    template_name = "fixture.txt"
    template_path = tmp_path / template_name
    template_path.write_text("one", encoding="utf-8")
    manifest = (TemplateSpec(name=template_name, stages=("stage1",), role="task"),)
    store = TemplateStore(tmp_path, manifest=manifest)

    assert store.load(template_name) == "one"
    template_path.write_text("two", encoding="utf-8")
    assert store.load(template_name) == "one"
    store.clear_cache(template_name)
    assert store.load(template_name) == "two"


def test_template_store_render_is_strict_and_non_executable(tmp_path: Path) -> None:
    template_name = "fixture.txt"
    (tmp_path / template_name).write_text(
        "symbol=$symbol stage=${stage}",
        encoding="utf-8",
    )
    store = TemplateStore(
        tmp_path,
        manifest=(TemplateSpec(name=template_name, stages=("stage2",), role="task"),),
    )
    context = TemplateContext(stage="stage2", symbol="TEST", timeframe="5m", bar_count=1)

    assert store.render(template_name, context, stage="stage2") == "symbol=TEST stage=stage2"

    with pytest.raises(TemplateStoreError, match="Missing template variable"):
        store.render(template_name, {"symbol": "TEST"}, stage="stage2")

    (tmp_path / template_name).write_text("broken ${", encoding="utf-8")
    store.clear_cache(template_name)
    with pytest.raises(TemplateStoreError, match="Invalid template syntax"):
        store.render(template_name, context, stage="stage2")


def test_template_store_reports_missing_and_invalid_utf8(tmp_path: Path) -> None:
    manifest = (
        TemplateSpec(name="missing.txt", stages=("stage1",), role="task"),
        TemplateSpec(name="invalid.txt", stages=("stage1",), role="task"),
    )
    store = TemplateStore(tmp_path, manifest=manifest)
    (tmp_path / "invalid.txt").write_bytes(b"\xff")

    with pytest.raises(TemplateStoreError, match="not found"):
        store.load("missing.txt")
    with pytest.raises(TemplateStoreError, match="not valid UTF-8"):
        store.load("invalid.txt")


def test_manifest_rejects_path_escape(tmp_path: Path) -> None:
    manifest = (TemplateSpec(name="../escape.txt", stages=("stage1",), role="task"),)

    with pytest.raises(ValueError, match="Invalid template name"):
        TemplateStore(tmp_path, manifest=manifest)
