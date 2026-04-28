"""Session-based grader checks — happy, failure, and missing-transcript paths."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from rf_skill_eval.domain.run import Run
from rf_skill_eval.scoring.session_based import (
    check_tool_call_count,
    check_tool_call_sequence,
    check_tool_result_count,
)


def _run(artifacts: Path) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="r-session",
        task_id="t-session",
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
    )


def _write_transcript(artifacts: Path, entries: list[dict[str, object]]) -> None:
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "stdout.stream.jsonl").write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
    )


def _assistant_tool_use(
    name: str, call_id: str, *, tool_input: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": call_id,
                    "name": name,
                    "input": tool_input or {},
                }
            ],
        },
    }


def _user_tool_result(
    call_id: str, *, is_error: bool = False, content: str = "ok"
) -> dict[str, object]:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "is_error": is_error,
                    "content": content,
                }
            ],
        },
    }


# --- tool_call_count ---------------------------------------------------------


def test_tool_call_count_happy(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use("mcp__rf-mcp__manage_session", "c1"),
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c2"),
            _assistant_tool_use("Read", "c3"),
        ],
    )
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {"tool_pattern": "mcp__rf-mcp__.*", "min": 2},
    )
    assert v.passed is True
    assert "count=2" in v.details


def test_tool_call_count_zero_max_enforced(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [_assistant_tool_use("mcp__rf-mcp__manage_session", "c1")],
    )
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {"tool_pattern": "mcp__rf-mcp__.*", "min": 0, "max": 0},
    )
    assert v.passed is False


def test_tool_call_count_missing_transcript(tmp_path: Path) -> None:
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {"tool_pattern": ".*", "min": 1},
    )
    assert v.passed is False
    assert "no session transcript" in v.details


def test_tool_call_count_input_pattern_matches_skill_arg(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use(
                "Skill",
                "c1",
                tool_input={"skill": "libdoc-search", "args": "BuiltIn"},
            ),
            _assistant_tool_use("Skill", "c2", tool_input={"skill": "debug"}),
        ],
    )
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {
            "tool_pattern": "Skill",
            "input_pattern": "libdoc-search",
            "min": 1,
        },
    )
    assert v.passed is True
    assert "count=1" in v.details
    assert "input_pattern=" in v.details


def test_tool_call_count_input_pattern_matches_bash_command(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use(
                "Bash",
                "c1",
                tool_input={"command": "python3 /plugin/scripts/rf_libdoc.py --library BuiltIn"},
            ),
            _assistant_tool_use(
                "Bash", "c2", tool_input={"command": "ls -la"}
            ),
        ],
    )
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {
            "tool_pattern": "(Bash|Skill)",
            "input_pattern": "(rf_libdoc|libdoc-search)",
            "min": 1,
        },
    )
    assert v.passed is True
    assert "count=1" in v.details


def test_tool_call_count_input_pattern_no_match_fails(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [_assistant_tool_use("Bash", "c1", tool_input={"command": "ls"})],
    )
    v = check_tool_call_count(
        _run(tmp_path),
        "n",
        {
            "tool_pattern": "Bash",
            "input_pattern": "rf_libdoc",
            "min": 1,
        },
    )
    assert v.passed is False
    assert "count=0" in v.details


# --- tool_result_count -------------------------------------------------------


def test_tool_result_count_happy_ok_status(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c1"),
            _user_tool_result("c1", is_error=False, content="done"),
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c2"),
            _user_tool_result("c2", is_error=True, content="fail"),
            _assistant_tool_use("Read", "c3"),
            _user_tool_result("c3", is_error=False, content="file body"),
        ],
    )
    v = check_tool_result_count(
        _run(tmp_path),
        "n",
        {
            "tool_pattern": "mcp__rf-mcp__.*",
            "status": "ok",
            "min": 1,
        },
    )
    assert v.passed is True
    assert "ok=1" in v.details
    assert "error=1" in v.details


def test_tool_result_count_fails_when_all_errors(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c1"),
            _user_tool_result("c1", is_error=True, content="fail"),
        ],
    )
    v = check_tool_result_count(
        _run(tmp_path),
        "n",
        {"tool_pattern": "mcp__rf-mcp__.*", "status": "ok", "min": 1},
    )
    assert v.passed is False


def test_tool_result_count_missing_transcript(tmp_path: Path) -> None:
    v = check_tool_result_count(
        _run(tmp_path),
        "n",
        {"tool_pattern": ".*", "status": "any", "min": 1},
    )
    assert v.passed is False
    assert "no session transcript" in v.details


# --- tool_call_sequence ------------------------------------------------------


def test_tool_call_sequence_happy(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use("mcp__rf-mcp__get_available_keywords", "c1"),
            _assistant_tool_use("Read", "c2"),
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c3"),
            _assistant_tool_use("Write", "c4"),
        ],
    )
    v = check_tool_call_sequence(
        _run(tmp_path),
        "n",
        {"patterns": ["mcp__rf-mcp__.*", "(Write|Edit)"]},
    )
    assert v.passed is True
    assert "matched 2/2" in v.details


def test_tool_call_sequence_fails_on_wrong_order(tmp_path: Path) -> None:
    _write_transcript(
        tmp_path,
        [
            _assistant_tool_use("Write", "c1"),
            _assistant_tool_use("mcp__rf-mcp__execute_step", "c2"),
        ],
    )
    v = check_tool_call_sequence(
        _run(tmp_path),
        "n",
        {"patterns": ["mcp__rf-mcp__.*", "(Write|Edit)"]},
    )
    assert v.passed is False
    assert "missing" in v.details


def test_tool_call_sequence_missing_transcript(tmp_path: Path) -> None:
    v = check_tool_call_sequence(
        _run(tmp_path),
        "n",
        {"patterns": ["Read"]},
    )
    assert v.passed is False
    assert "no session transcript" in v.details


def test_tool_call_sequence_falls_back_to_session_jsonl(tmp_path: Path) -> None:
    # stdout.stream.jsonl is missing; the parser should use session_jsonl_path.
    session_path = tmp_path / "session.jsonl"
    session_path.write_text(
        json.dumps(_assistant_tool_use("Read", "c1")) + "\n",
        encoding="utf-8",
    )
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    now = datetime.now(UTC)
    run = Run(
        id="r",
        task_id="t",
        profile_name="p",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
        session_jsonl_path=session_path,
    )
    v = check_tool_call_sequence(run, "n", {"patterns": ["Read"]})
    assert v.passed is True
