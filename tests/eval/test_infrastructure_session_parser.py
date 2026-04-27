"""Session JSONL parser — anti-corruption layer over Anthropic schema."""

from __future__ import annotations

import json
from pathlib import Path

from rf_skill_eval.infrastructure.telemetry.session_parser import (
    AssistantMessage,
    ThinkingBlock,
    ToolCall,
    UserMessage,
    parse_session_jsonl,
    summarise_session,
)


def _write_session(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_parses_tool_call_and_thinking(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "reason..."},
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/tmp/x"},
                        },
                    ],
                },
            },
            {
                "type": "message",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "hi"}],
                },
            },
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["ThinkingBlock", "ToolCall", "UserMessage"]
    tool = next(e for e in events if isinstance(e, ToolCall))
    assert tool.tool_name == "Read"
    assert tool.tool_input == {"file_path": "/tmp/x"}


def test_summarise_counts(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "ok"}],
                },
            },
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {}},
                        {"type": "thinking", "thinking": "..."},
                    ],
                },
            },
        ],
    )
    counts = summarise_session(jsonl)
    assert counts["assistant_message"] == 1
    assert counts["tool_call"] == 1
    assert counts["thinking"] == 1


def test_skips_malformed_lines(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text(
        "not-json\n"
        + json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "hi"}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    events = list(parse_session_jsonl(jsonl))
    assert len(events) == 1
    assert isinstance(events[0], AssistantMessage)


def test_handles_string_content(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "message",
                "message": {"role": "user", "content": "plain string body"},
            }
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    assert len(events) == 1
    assert isinstance(events[0], UserMessage)
    assert events[0].text == "plain string body"


def test_handles_standalone_thinking(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "message",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "pondering"},
                    ],
                },
            }
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    assert isinstance(events[0], ThinkingBlock)
    assert events[0].text == "pondering"
