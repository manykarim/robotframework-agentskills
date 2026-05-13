"""Unit tests for the bash hook scripts in plugins/rf-agentskills/scripts/.

We invoke the scripts as subprocesses with synthetic Claude Code event
JSON on stdin and assert on the (stdout, exit-code) pair. No live LLM
involved; these are deterministic shell tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# The hook scripts under test are bash (``#!/usr/bin/env bash``). On Windows
# they're not natively executable — the corresponding ``.ps1`` ports run
# there instead, and the Claude Code adapter switches to those at install
# time (see ``transforms.rewrite_hooks_for_windows``). Skip the whole
# module on Windows; the PowerShell variants don't have their own unit
# tests yet.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="bash hook scripts run on POSIX only; .ps1 ports used on Windows",
)

PLUGIN_SCRIPTS = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "rf-agentskills"
    / "scripts"
)
INJECT_SCRIPT = PLUGIN_SCRIPTS / "maybe_inject_rf_context.sh"
REMIND_SCRIPT = PLUGIN_SCRIPTS / "maybe_remind_robot_tests.sh"


def _run(script: Path, payload: dict) -> tuple[str, str, int]:
    """Pipe ``payload`` as JSON to ``script`` and return (stdout, stderr, rc)."""
    proc = subprocess.run(
        [str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout, proc.stderr, proc.returncode


def _expect_no_injection(stdout: str) -> None:
    """A non-injecting hook must not emit the additionalContext envelope."""
    assert "additionalContext" not in stdout, (
        f"expected no additionalContext, got: {stdout!r}"
    )


def _expect_injection(stdout: str) -> dict:
    """Parse stdout and return the hookSpecificOutput payload."""
    assert stdout.strip(), f"expected JSON injection, got empty stdout"
    payload = json.loads(stdout)
    assert "hookSpecificOutput" in payload, payload
    assert "additionalContext" in payload["hookSpecificOutput"], payload
    return payload["hookSpecificOutput"]


# --- maybe_inject_rf_context.sh: positive cases ---------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "I'm writing a Robot Framework test suite using SeleniumLibrary.",
        "Help me debug my .robot file at tests/login.robot",
        "Refactor common keywords into a .resource file please",
        "Look up the Browser Library `Click` keyword signature",
        "What does AppiumLibrary provide for swiping?",
        "Show me how to use libdoc to search for keywords",
        "Run robocop against this resource file",
        "I want to use the testcase-builder skill to author a login test",
        "Suggest a resource-architect refactor for these duplicated steps",
        "Should I use libdoc-search or libdoc-explain here?",
        "Have rf-test-architect plan a CI pipeline",
        "robotidy says this file has formatting issues",
        "rfbrowser init failed — what now?",
        "Rewrite this test using RESTinstance",
    ],
)
def test_inject_fires_on_rf_signals(prompt: str) -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    payload = _expect_injection(out)
    ctx = payload["additionalContext"]
    # The injected context names the rf-agentskills, so callers can spot it.
    assert "rf-agentskills" in ctx
    assert "libdoc-search" in ctx


# --- maybe_inject_rf_context.sh: negative cases ---------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "Write a JSON file at data/colors.json with two keys",
        "What's the SHA256 of this string?",
        "Help me design a REST API in FastAPI",
        "Refactor this Python function for readability",
        "Explain the difference between a list and a tuple",
        "Set up a Vite + React project",
        "Investigate this Kubernetes deployment failure",
        "Write a SQL query that joins users and orders",
        "Generate a Markdown report from this CSV",
        "Translate this paragraph to French",
        # Words like "test" / "library" / "keyword" alone must NOT trigger
        # because they are too generic.
        "Write a unit test for this function",
        "I need a Python library for ZIP file handling",
        "What's a good keyword for SEO in this title?",
        # Bare "RF" is intentionally not a trigger (radio-frequency,
        # request-for-..., etc.).
        "What does RF stand for in your domain?",
    ],
)
def test_inject_skips_on_non_rf_prompts(prompt: str) -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    _expect_no_injection(out)


def test_inject_handles_missing_prompt_field() -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"session_id": "x"})
    assert rc == 0
    _expect_no_injection(out)


def test_inject_handles_empty_stdin() -> None:
    proc = subprocess.run(
        [str(INJECT_SCRIPT)], input="", capture_output=True, text=True, timeout=10
    )
    assert proc.returncode == 0
    _expect_no_injection(proc.stdout)


def test_inject_handles_malformed_json() -> None:
    proc = subprocess.run(
        [str(INJECT_SCRIPT)],
        input="not valid json {",
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Hook is non-blocking — it must exit 0 even on bad input.
    assert proc.returncode == 0
    _expect_no_injection(proc.stdout)


# --- maybe_remind_robot_tests.sh ------------------------------------------


def _write_transcript(tmp_path: Path, lines: list[str]) -> Path:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return transcript


def test_remind_fires_when_robot_file_was_written(tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            json.dumps({"type": "assistant"}),
            json.dumps(
                {
                    "type": "tool_use",
                    "input": {
                        "file_path": "/work/tests/login.robot",
                        "content": "*** Test Cases ***",
                    },
                }
            ),
        ],
    )
    out, _err, rc = _run(REMIND_SCRIPT, {"transcript_path": str(transcript)})
    assert rc == 0
    payload = _expect_injection(out)
    assert "robot --outputdir" in payload["additionalContext"]


def test_remind_fires_for_resource_file(tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            json.dumps(
                {
                    "type": "tool_use",
                    "input": {"file_path": "resources/common.resource"},
                }
            )
        ],
    )
    out, _err, rc = _run(REMIND_SCRIPT, {"transcript_path": str(transcript)})
    assert rc == 0
    _expect_injection(out)


def test_remind_skips_when_only_non_rf_files_written(tmp_path: Path) -> None:
    transcript = _write_transcript(
        tmp_path,
        [
            json.dumps(
                {
                    "type": "tool_use",
                    "input": {"file_path": "data/colors.json"},
                }
            ),
            json.dumps(
                {
                    "type": "tool_use",
                    "input": {"file_path": "src/main.py"},
                }
            ),
        ],
    )
    out, _err, rc = _run(REMIND_SCRIPT, {"transcript_path": str(transcript)})
    assert rc == 0
    _expect_no_injection(out)


def test_remind_skips_when_transcript_path_missing() -> None:
    out, _err, rc = _run(REMIND_SCRIPT, {"session_id": "abc"})
    assert rc == 0
    _expect_no_injection(out)


def test_remind_skips_when_transcript_file_missing() -> None:
    out, _err, rc = _run(
        REMIND_SCRIPT, {"transcript_path": "/nonexistent/transcript.jsonl"}
    )
    assert rc == 0
    _expect_no_injection(out)


def test_remind_does_not_match_substring_in_unrelated_path(tmp_path: Path) -> None:
    """A file like `notes.robotic.md` must NOT count as a .robot file."""
    transcript = _write_transcript(
        tmp_path,
        [
            json.dumps(
                {
                    "type": "tool_use",
                    "input": {"file_path": "notes.robotic.md"},
                }
            )
        ],
    )
    out, _err, rc = _run(REMIND_SCRIPT, {"transcript_path": str(transcript)})
    assert rc == 0
    _expect_no_injection(out)


# --- Cross-script invariants ----------------------------------------------


@pytest.mark.parametrize("script", [INJECT_SCRIPT, REMIND_SCRIPT])
def test_scripts_are_executable(script: Path) -> None:
    import os

    assert script.is_file(), script
    assert os.access(script, os.X_OK), f"{script} is not executable"


@pytest.mark.parametrize("script", [INJECT_SCRIPT, REMIND_SCRIPT])
def test_scripts_exit_zero_on_pathological_inputs(script: Path) -> None:
    """A misbehaving hook script can break user sessions; double-check
    that neither script ever exits non-zero on weird input."""
    for stdin in [
        "",
        "\x00\x01garbage\xff",
        "{}",
        "[]",
        '"just a string"',
        '{"prompt": null}',
        '{"prompt": 12345}',
        '{"prompt": ' + ('"' + "x" * 10_000 + '"') + "}",
    ]:
        proc = subprocess.run(
            [str(script)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, (
            f"{script.name} exited {proc.returncode} on {stdin!r}: stderr={proc.stderr!r}"
        )
