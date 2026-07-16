"""Tests for Stage 2 experience-library rendering."""
from __future__ import annotations

from types import SimpleNamespace

from pa_agent.ai.experience_renderer import render_experience


def test_render_experience_includes_header_and_caveat_for_empty_entries() -> None:
    assert render_experience([]) == "\n".join(
        [
            "## \u7ecf\u9a8c\u5e93(\u6700\u8fd1\u6848\u4f8b,\u4f9b\u53c2\u8003)",
            "\u4ee5\u4e0b\u6848\u4f8b\u4ec5\u4f5c\u5bf9\u7167\uff0c**\u4e0d\u5f97**"
            "\u56e0\u76f8\u4f3c\u5c31\u6539\u53d8\u5bf9\u672c\u56fe\u7ed3\u6784/"
            "\u65b9\u5411\u7684\u72ec\u7acb\u5224\u65ad\u3002",
        ]
    )


def test_render_experience_serializes_dict_entries_as_json_blocks() -> None:
    rendered = render_experience([{"symbol": "ES", "score": 2}])

    assert "\n### \u6848\u4f8b 1\n```json\n" in rendered
    assert '"symbol": "ES"' in rendered
    assert '"score": 2' in rendered
    assert rendered.endswith("\n```")


def test_render_experience_serializes_content_attribute() -> None:
    rendered = render_experience([SimpleNamespace(content={"lesson": "hold"})])

    assert '"lesson": "hold"' in rendered


def test_render_experience_truncates_long_entries_with_ellipsis() -> None:
    rendered = render_experience(["abcdef"], max_chars_per_entry=5)

    assert "ab..." in rendered
    assert "abcdef" not in rendered
