"""Experience-library renderer for Stage 2 prompts.

Extracted from ``prompt_assembler.py`` (report §5.2 M1, the ``ExperienceRenderer``
产出). This is the pure text-block renderer that folds recent experience-library
cases into the Stage 2 user turn (for reference only, never to override the
model's independent read of the current chart). It depends only on stdlib
``json`` (no project imports, no side effects), so it stays importable without the
GUI stack. ``PromptAssembler`` re-binds ``render_experience`` as
``_render_experience`` staticmethod so the existing
``self._render_experience(...)`` call site keeps working byte-for-byte. The block
header / Chinese caveat / per-case markdown fence / truncation ellipsis must stay
byte-for-byte identical (the model is prompted against this exact block shape).
"""
from __future__ import annotations

import json
from typing import Any


def render_experience(
    entries: list[Any],
    *,
    max_chars_per_entry: int = 400,
) -> str:
    """Render experience library entries as a text block."""
    lines = [
        "## 经验库(最近案例,供参考)",
        "以下案例仅作对照，**不得**因相似就改变对本图结构/方向的独立判断。",  # noqa: RUF001
    ]
    for i, entry in enumerate(entries, 1):
        if isinstance(entry, dict):
            blob = json.dumps(entry, ensure_ascii=False, indent=2)
        elif hasattr(entry, "content"):
            blob = json.dumps(
                getattr(entry, "content", entry),
                ensure_ascii=False,
                indent=2,
            )
        else:
            blob = str(entry)
        if len(blob) > max_chars_per_entry:
            blob = blob[: max_chars_per_entry - 3] + "..."
        lines.append(f"\n### 案例 {i}\n```json\n{blob}\n```")
    return "\n".join(lines)
