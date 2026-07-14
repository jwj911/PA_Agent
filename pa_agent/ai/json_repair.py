"""JSON extraction and repair helpers for model outputs.

Pure, stdlib-only functions that isolate a JSON object from mixed model output
(prose + markdown fences) and repair common LLM syntax slips (unescaped quotes,
stray semicolons, truncated/unbalanced brackets, unclosed strings).

Split out of :mod:`pa_agent.ai.json_validator` (report §5.2 M2). The
``JsonValidator`` class and the public names are re-exported from that module,
so existing imports (``from pa_agent.ai.json_validator import ...``) keep
working byte-for-byte.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

# ── Markdown fence stripper ───────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_TRAILING_FENCE_RE = re.compile(r"\n?```\s*$")
_LEADING_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?", re.IGNORECASE)


def _extract_outer_json_object(text: str) -> str:
    """Return the first top-level `{...}` object, ignoring trailing prose/fences."""
    start = text.find("{")
    if start < 0:
        return text.strip()

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:].strip()


def _strip_fences(text: str) -> str:
    """Remove markdown fences and isolate the JSON object payload."""
    t = text.strip()
    if not t:
        return t

    # ── 清洗模型输出的非标准 Unicode 引号 / 控制字符 ──
    _SMART_QUOTE_MAP = {
        "\u201c": '"',   # " → "
        "\u201d": '"',   # " → "
        "\u2018": "'",   # ' → '
        "\u2019": "'",   # ' → '
        "\u2013": "-",   # en-dash
        "\u2014": "-",   # em-dash
    }
    for bad, good in _SMART_QUOTE_MAP.items():
        t = t.replace(bad, good)
    # 去掉除 \t \n \r 外的控制字符（0x00-0x1f 除了这三个）
    t = "".join(ch for ch in t if ch >= " " or ch in "\t\n\r")

    # ── Priority: find an embedded ```json ... ``` fence anywhere in text ──
    # Handles the case where the model outputs prose first, then a fenced block.
    m_embedded = _FENCE_RE.search(t)
    if m_embedded:
        t = m_embedded.group(1).strip()
        return _repair_unescaped_quotes(_repair_semicolon_separator(_extract_outer_json_object(t)))

    # Fully fenced ```json ... ``` starting at top
    if t.startswith("```"):
        m = _FENCE_RE.search(t)
        if m:
            t = m.group(1).strip()
        else:
            t = _LEADING_FENCE_RE.sub("", t, count=1).strip()

    # Common model mistake: raw JSON + trailing ``` only
    t = _TRAILING_FENCE_RE.sub("", t).strip()

    return _repair_unescaped_quotes(_repair_semicolon_separator(_extract_outer_json_object(t)))


def _escape_control_chars_in_json_strings(text: str) -> str:
    """Escape raw newlines/tabs/control chars inside JSON string literals."""
    out: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            continue
        if escape:
            escape = False
            out.append(ch)
            continue
        if ch == "\\":
            escape = True
            out.append(ch)
            continue
        if ch == '"':
            in_string = False
            out.append(ch)
            continue
        if ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch < " ":
            continue
        else:
            out.append(ch)
    return "".join(out)


def coalesce_model_json_text(content: str, reasoning: str | None = None) -> str:
    """Prefer content JSON; fall back to reasoning when content is empty or prose."""
    stripped = _strip_fences(content or "")
    if stripped.startswith("{") or stripped.startswith("["):
        return content or ""
    if reasoning:
        from_reasoning = _strip_fences(reasoning)
        if from_reasoning.startswith("{") or from_reasoning.startswith("["):
            logger.info("Extracting JSON from reasoning_content (content was not JSON)")
            return from_reasoning
    return content or ""


def format_model_json_for_context(raw_text: str) -> str | None:
    """Extract JSON from model output and return pretty-printed text for prompts."""
    stripped = _strip_fences(raw_text or "")
    if not stripped.startswith("{"):
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    return stripped


# ── Unescaped quote repair ────────────────────────────────────────────────────

_STRING_END_CHARS = frozenset(",:}]")


def _repair_unescaped_quotes(text: str) -> str:
    """Escape ``"`` inside JSON string values that were not backslash-escaped.

    Uses a peek-ahead heuristic: a quote ends the string only when the next
    non-whitespace character is structural (`,`, `:`, `}`, `]`, or EOF).
    """
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
            continue

        if escape:
            escape = False
            out.append(ch)
            i += 1
            continue
        if ch == "\\":
            escape = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j >= n or text[j] in _STRING_END_CHARS:
                in_string = False
                out.append(ch)
            else:
                out.append('\\"')
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _repair_semicolon_separator(text: str) -> str:
    """Replace stray semicolons used as field separators outside JSON strings.

    Models occasionally write ``"field": "value";`` instead of ``"field": "value",``
    which is a common typo.  Only replaces ``;`` that appears in struct-separator
    position (outside a string, followed by optional whitespace then ``"`` or ``}``).
    """
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ";":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in ('"', '}', ']'):
                out.append(",")
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


# ── Truncated JSON repair ───────────────────────────────────────────────────────

def _balance_json_brackets(text: str) -> str:
    """Close unclosed ``{`` / ``[`` outside JSON strings."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            stack.append("{")
        elif ch == "[":
            stack.append("[")
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
    closers = "".join("]" if opener == "[" else "}" for opener in reversed(stack))
    return text + closers


def _inject_stage1_missing_tail(text: str) -> str:
    """Append minimal gate_trace tail when stage1 JSON was truncated mid-object."""
    tail = text.rstrip()
    if not tail.endswith((",", "]", "}")):
        return text

    if not tail.endswith(","):
        tail += ","

    stub_trace = (
        '{"node_id":"AUTO","question":"输出是否在gate_trace前被截断？",'
        '"answer":"否","reason":"JSON在gate_trace前截断，程序已补全最小闸门记录",'
        '"bar_range":"K1"}'
    )
    tail += f'"gate_trace":[{stub_trace}],"gate_result":"unknown"'
    return _balance_json_brackets(tail)


def _repair_unclosed_string_before_brace(text: str) -> str:
    """Close strings broken by a raw newline followed by ``}`` / ``]``.

    Models sometimes omit the closing quote in long ``summary`` / ``reasoning``
    fields, e.g. ``"summary": "text\\n}\\n  },"`` → insert ``"`` before ``}``.
    """
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
            continue
        if escape:
            escape = False
            out.append(ch)
            i += 1
            continue
        if ch == "\\":
            escape = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_string = False
            out.append(ch)
            i += 1
            continue
        if ch == "\n":
            j = i + 1
            while j < n and text[j] in " \t\r":
                j += 1
            if j < n and text[j] in "}]":
                out.append('"')
                in_string = False
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _try_repair_json_syntax(
    text: str,
    stage: Literal["stage1", "stage2"],
    *,
    allow_tail_inject: bool = False,
) -> str | None:
    """Return repaired JSON text when truncation/syntax slip caused parse failure."""
    if not text.strip().startswith("{"):
        return None

    bases: list[str] = [text.rstrip()]
    if stage == "stage1" and allow_tail_inject:
        bases.append(_inject_stage1_missing_tail(bases[0]))

    seen: set[str] = set()
    for base in bases:
        for variant in (base, _repair_unclosed_string_before_brace(base)):
            candidate = _balance_json_brackets(variant.rstrip())
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if candidate != text.rstrip():
                return candidate
    return None
