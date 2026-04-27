"""Anti-corruption layer over Anthropic's session JSONL schema.

The internal event types defined here are **not** thin wrappers over
the raw dicts — they form a stable internal vocabulary. When Anthropic
ships a schema change, only this module needs to adapt.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_log = logging.getLogger(__name__)


EventKind = Literal[
    "tool_call",
    "tool_result",
    "thinking",
    "user_message",
    "assistant_message",
    "unknown",
]


class _EventBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: EventKind
    raw: dict[str, Any] = Field(default_factory=dict)


class ToolCall(_EventBase):
    kind: EventKind = "tool_call"
    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    tool_use_id: str = ""


class ToolResult(_EventBase):
    kind: EventKind = "tool_result"
    tool_use_id: str = ""
    is_error: bool = False
    content_text: str = ""


class ThinkingBlock(_EventBase):
    kind: EventKind = "thinking"
    text: str = ""


class UserMessage(_EventBase):
    kind: EventKind = "user_message"
    text: str = ""


class AssistantMessage(_EventBase):
    kind: EventKind = "assistant_message"
    text: str = ""


class UnknownEvent(_EventBase):
    kind: EventKind = "unknown"


SessionEvent = (
    ToolCall
    | ToolResult
    | ThinkingBlock
    | UserMessage
    | AssistantMessage
    | UnknownEvent
)


def _coerce_tool_result_content(raw: Any) -> str:
    """Normalise tool_result content (str | list[dict] | other) into one string."""

    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for block in raw:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    # Preserve non-text block types as JSON for completeness.
                    try:
                        parts.append(json.dumps(block, sort_keys=True))
                    except (TypeError, ValueError):
                        parts.append(str(block))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(raw)


def _iter_content_blocks(message: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield content blocks from either Claude Code or raw Anthropic schemas."""

    content = message.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                yield block
    elif isinstance(content, str):
        # Compact form: treat entire content as text.
        yield {"type": "text", "text": content}


def _classify_entry(entry: dict[str, Any]) -> Iterator[SessionEvent]:
    """Convert one JSONL line (already parsed) into zero or more events."""

    entry_type = entry.get("type")

    # Claude Code session JSONL wraps the actual message under "message".
    message = entry.get("message")
    if isinstance(message, dict):
        role = message.get("role")
        for block in _iter_content_blocks(message):
            block_type = block.get("type")
            if block_type == "tool_use":
                yield ToolCall(
                    raw=block,
                    tool_name=str(block.get("name", "")),
                    tool_input=block.get("input", {}) or {},
                    tool_use_id=str(block.get("id", "")),
                )
            elif block_type == "tool_result":
                is_error_raw = block.get("is_error", False)
                is_error = bool(is_error_raw) if is_error_raw is not None else False
                yield ToolResult(
                    raw=block,
                    tool_use_id=str(block.get("tool_use_id", "")),
                    is_error=is_error,
                    content_text=_coerce_tool_result_content(block.get("content")),
                )
            elif block_type == "thinking":
                yield ThinkingBlock(raw=block, text=str(block.get("thinking", "")))
            elif block_type == "text":
                text = str(block.get("text", ""))
                if role == "user":
                    yield UserMessage(raw=block, text=text)
                elif role == "assistant":
                    yield AssistantMessage(raw=block, text=text)
                else:
                    yield UnknownEvent(raw=block)
            else:
                yield UnknownEvent(raw=block)
        return

    # Some entries are meta events (e.g., session_start, hook_fire). Keep
    # them available under UnknownEvent so downstream metrics can see them.
    if entry_type is not None:
        yield UnknownEvent(raw=entry)


def parse_session_jsonl(path: Path) -> Iterator[SessionEvent]:
    """Yield one :class:`SessionEvent` per content block in the session.

    Malformed lines are logged and skipped — the caller should treat a
    partial session as a valid data point, not an error (per ADR-003's
    "timed-out runs are valid data points" principle).
    """

    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                _log.warning(
                    "Skipping malformed JSONL line %s:%d — %s",
                    path,
                    line_no,
                    exc,
                )
                continue
            if not isinstance(entry, dict):
                continue
            yield from _classify_entry(entry)


def summarise_session(path: Path) -> dict[str, int]:
    """Return quick event counts for eyeballing a session.

    Memory-efficient: streams the file; does not materialise a list.
    """

    counts: dict[str, int] = {
        "tool_call": 0,
        "tool_result": 0,
        "thinking": 0,
        "user_message": 0,
        "assistant_message": 0,
        "unknown": 0,
    }
    for event in parse_session_jsonl(path):
        counts[event.kind] = counts.get(event.kind, 0) + 1
    return counts
