"""Safety guards for the explicit live headless observation harness."""

from __future__ import annotations

from pathlib import Path

from tools.run_live_headless_observation import main


def test_live_observation_requires_explicit_confirmation(tmp_path: Path, capsys) -> None:
    assert main(["--output-dir", str(tmp_path)]) == 2
    assert "--confirm-live" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_live_observation_requires_environment_key(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.delenv("PA_AGENT_LIVE_API_KEY", raising=False)

    assert main(["--confirm-live", "--output-dir", str(tmp_path)]) == 2
    assert "PA_AGENT_LIVE_API_KEY" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
