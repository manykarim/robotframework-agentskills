"""Session parser coverage for ``tool_result`` blocks."""

from __future__ import annotations

import json
from pathlib import Path

from rf_skill_eval.infrastructure.telemetry.session_parser import (
    ToolCall,
    ToolResult,
    parse_session_jsonl,
    summarise_session,
)


def _write_session(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_tool_result_emitted_with_string_content(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call_1",
                            "name": "mcp__rf-mcp__manage_session",
                            "input": {"action": "start"},
                        }
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_1",
                            "is_error": False,
                            "content": "session started",
                        }
                    ],
                },
            },
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    calls = [e for e in events if isinstance(e, ToolCall)]
    results = [e for e in events if isinstance(e, ToolResult)]
    assert len(calls) == 1
    assert calls[0].tool_use_id == "call_1"
    assert len(results) == 1
    assert results[0].tool_use_id == "call_1"
    assert results[0].is_error is False
    assert results[0].content_text == "session started"


def test_tool_result_coerces_list_content(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_2",
                            "is_error": True,
                            "content": [
                                {"type": "text", "text": "boom"},
                                {"type": "text", " text": "extra"},
                            ],
                        }
                    ],
                },
            }
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    results = [e for e in events if isinstance(e, ToolResult)]
    assert len(results) == 1
    assert results[0].is_error is True
    # First block coerces to "boom"; second has malformed key so is JSON-encoded.
    assert "boom" in results[0].content_text


def test_summarise_includes_tool_result_counter(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": "c1", "name": "Read", "input": {}}
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "c1",
                            "content": "ok",
                        }
                    ],
                },
            },
        ],
    )
    counts = summarise_session(jsonl)
    assert counts["tool_call"] == 1
    assert counts["tool_result"] == 1


def test_tool_result_missing_is_error_defaults_false(tmp_path: Path) -> None:
    jsonl = tmp_path / "session.jsonl"
    _write_session(
        jsonl,
        [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "c9",
                            "content": "",
                        }
                    ],
                },
            }
        ],
    )
    events = list(parse_session_jsonl(jsonl))
    results = [e for e in events if isinstance(e, ToolResult)]
    assert len(results) == 1
    assert results[0].is_error is False
