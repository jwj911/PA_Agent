"""Tests for applying the GUI theme."""
from __future__ import annotations

from dataclasses import dataclass, field

from pa_agent.gui.theme import apply as theme_apply


@dataclass
class _FakeApplication:
    style_sheet: str | None = None
    styles: list[str] = field(default_factory=list)

    def setStyleSheet(self, value: str) -> None:
        self.style_sheet = value

    def setStyle(self, value: str) -> None:
        self.styles.append(value)


def test_apply_theme_loads_qss_and_sets_fusion_style(tmp_path, monkeypatch) -> None:
    qss_path = tmp_path / "dark.qss"
    qss_path.write_text("QWidget { color: #e6edf3; }\n", encoding="utf-8")
    monkeypatch.setattr(theme_apply, "_QSS_PATH", qss_path)
    app = _FakeApplication()

    theme_apply.apply_theme(app)

    assert app.style_sheet == "QWidget { color: #e6edf3; }\n"
    assert app.styles == ["Fusion"]


def test_apply_theme_sets_fusion_style_when_qss_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(theme_apply, "_QSS_PATH", tmp_path / "missing.qss")
    app = _FakeApplication()

    theme_apply.apply_theme(app)

    assert app.style_sheet is None
    assert app.styles == ["Fusion"]
