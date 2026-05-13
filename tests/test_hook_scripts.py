"""Unit tests for the Node.js hook scripts in plugins/rf-agentskills/scripts/.

We invoke each ``.mjs`` script as a subprocess (driven by ``node``) with
synthetic Claude Code event JSON on stdin and assert on the
``(stdout, exit-code)`` pair. No live LLM involved; these are
deterministic shell tests.

Cross-platform: the scripts are pure Node.js (per the
[claudefa.st cross-platform-hooks guidance](https://claudefa.st/blog/tools/hooks/cross-platform-hooks))
so they run identically on Linux, macOS, and Windows. The whole module
is gated only on whether ``node`` is on PATH — most CI agents have it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None,
    reason="Node.js not on PATH; rf-agentskills hooks are Node-based",
)

PLUGIN_SCRIPTS = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "rf-agentskills"
    / "scripts"
)
INJECT_SCRIPT = PLUGIN_SCRIPTS / "maybe_inject_rf_context.mjs"
REMIND_SCRIPT = PLUGIN_SCRIPTS / "maybe_remind_robot_tests.mjs"
VALIDATE_SCRIPT = PLUGIN_SCRIPTS / "validate_robot.mjs"
CHECK_ENV_SCRIPT = PLUGIN_SCRIPTS / "check_rf_environment.mjs"


def _run(script: Path, payload: dict | None = None, *,
         stdin: str | None = None, env: dict | None = None) -> tuple[str, str, int]:
    """Pipe ``payload`` as JSON to ``node script`` and return (stdout, stderr, rc).

    When ``stdin`` is passed verbatim it overrides ``payload`` (used for
    malformed-JSON / empty / pathological inputs).
    """
    if stdin is None:
        stdin = json.dumps(payload) if payload is not None else ""
    proc = subprocess.run(
        [NODE, str(script)],  # type: ignore[arg-type]  # NODE is non-None per skipif
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    return proc.stdout, proc.stderr, proc.returncode


def _expect_no_injection(stdout: str) -> None:
    """A non-injecting hook must not emit the additionalContext envelope."""
    assert "additionalContext" not in stdout, (
        f"expected no additionalContext, got: {stdout!r}"
    )


def _expect_injection(stdout: str) -> dict:
    """Parse stdout and return the hookSpecificOutput payload."""
    assert stdout.strip(), "expected JSON injection, got empty stdout"
    payload = json.loads(stdout)
    assert "hookSpecificOutput" in payload, payload
    assert "additionalContext" in payload["hookSpecificOutput"], payload
    return payload["hookSpecificOutput"]


# --- maybe_inject_rf_context.mjs: positive cases --------------------------


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


# --- maybe_inject_rf_context.mjs: negative cases --------------------------


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
    out, _err, rc = _run(INJECT_SCRIPT, stdin="")
    assert rc == 0
    _expect_no_injection(out)


def test_inject_handles_malformed_json() -> None:
    out, _err, rc = _run(INJECT_SCRIPT, stdin="not valid json {")
    # Hook is non-blocking — it must exit 0 even on bad input.
    assert rc == 0
    _expect_no_injection(out)


# --- maybe_remind_robot_tests.mjs -----------------------------------------


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


# --- validate_robot.mjs ---------------------------------------------------


def test_validate_silently_skips_when_no_tool_input(tmp_path: Path) -> None:
    """No TOOL_INPUT environment variable → exit 0, no output."""
    # Copy the parent env and strip TOOL_INPUT. We can't pass ``env={}``
    # because Windows requires SystemRoot/Path to spawn any process —
    # an empty env crashes the node child with exit code 134.
    import os
    env = {k: v for k, v in os.environ.items() if k != "TOOL_INPUT"}
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 0
    assert out == ""
    assert err == ""


def test_validate_silently_skips_for_non_rf_file(tmp_path: Path) -> None:
    """A Write/Edit to a .py file should be ignored by the validator."""
    import os
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps({"file_path": "/tmp/foo.py"})
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 0
    assert out == ""
    assert err == ""


def test_validate_silently_skips_for_missing_file(tmp_path: Path) -> None:
    """A .robot path that doesn't exist on disk should be ignored."""
    import os
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps(
        {"file_path": str(tmp_path / "does-not-exist.robot")}
    )
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 0
    assert out == ""


def test_validate_accepts_valid_robot_file(tmp_path: Path) -> None:
    """A well-formed .robot file → exit 0 with a stderr OK message
    (assuming the test runner has robotframework installed)."""
    import os
    robot_file = tmp_path / "ok.robot"
    robot_file.write_text(
        "*** Test Cases ***\nLogin\n    Log    hello\n", encoding="utf-8"
    )
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps({"file_path": str(robot_file)})
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    # Either "syntax OK" (robotframework installed) or
    # "skipping syntax validation" (robotframework missing) — both rc=0.
    assert rc == 0
    assert ("syntax OK" in err) or ("skipping syntax validation" in err), err


# --- check_rf_environment.mjs ---------------------------------------------


def test_check_rf_environment_runs_to_completion() -> None:
    """SessionStart diagnostic must always exit 0 and print to stderr."""
    out, err, rc = _run(CHECK_ENV_SCRIPT, stdin="")
    assert rc == 0
    assert "Robot Framework Environment Check" in err


# --- Cross-script invariants ----------------------------------------------


@pytest.mark.parametrize(
    "script",
    [INJECT_SCRIPT, REMIND_SCRIPT, VALIDATE_SCRIPT, CHECK_ENV_SCRIPT],
)
def test_scripts_exist(script: Path) -> None:
    assert script.is_file(), f"{script} missing"


@pytest.mark.parametrize("script", [INJECT_SCRIPT, REMIND_SCRIPT])
def test_scripts_exit_zero_on_pathological_inputs(script: Path) -> None:
    """A misbehaving hook script can break user sessions; double-check
    that neither stdin-consuming script ever exits non-zero on weird
    input."""
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
            [NODE, str(script)],  # type: ignore[arg-type]
            input=stdin,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, (
            f"{script.name} exited {proc.returncode} on {stdin!r}: "
            f"stderr={proc.stderr!r}"
        )
