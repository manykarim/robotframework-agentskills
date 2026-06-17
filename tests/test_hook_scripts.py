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
VALIDATE_PROJECT_SCRIPT = PLUGIN_SCRIPTS / "validate_robot_project.mjs"
CHECK_ENV_SCRIPT = PLUGIN_SCRIPTS / "check_rf_environment.mjs"


def _module_importable(module: str) -> bool:
    """True if any interpreter the hook scripts would try has ``module``.

    Mirrors the scripts' resolution order (python_runtime.json is absent in
    a source checkout, so this is the PATH fallbacks plus the test runner's
    own interpreter, which is what `python3` typically resolves to under
    `uv run`)."""
    import sys

    for py in (sys.executable, "python3", "python"):
        if py is None:
            continue
        try:
            rc = subprocess.run(
                [py, "-c", f"import {module}"],
                capture_output=True,
                timeout=30,
            ).returncode
        except (OSError, subprocess.SubprocessError):
            continue
        if rc == 0:
            return True
    return False


_HAS_ROBOCOP = _module_importable("robocop")
_HAS_ROBOT = _module_importable("robot")
_HAS_FIND_UNUSED = _module_importable("robotframework_find_unused")


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
        "Automate the desktop calculator with PlatynUI",
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


# --- Stop-hook loop safety (stop_hook_active) -----------------------------


def _robot_transcript(tmp_path: Path) -> Path:
    return _write_transcript(
        tmp_path,
        [json.dumps({"type": "tool_use", "input": {"file_path": "/w/tests/login.robot"}})],
    )


def test_remind_silent_when_stop_hook_active(tmp_path: Path) -> None:
    """The loop fix: on a continuation (stop_hook_active=true) the reminder
    must stay silent so it cannot re-invoke the model and loop."""
    transcript = _robot_transcript(tmp_path)
    out, _err, rc = _run(
        REMIND_SCRIPT,
        {"transcript_path": str(transcript), "stop_hook_active": True},
    )
    assert rc == 0
    assert out == ""


def test_remind_fires_when_not_stop_hook_active(tmp_path: Path) -> None:
    """Explicit stop_hook_active=false still emits the reminder."""
    transcript = _robot_transcript(tmp_path)
    out, _err, rc = _run(
        REMIND_SCRIPT,
        {"transcript_path": str(transcript), "stop_hook_active": False},
    )
    assert rc == 0
    assert "additionalContext" in out


def test_remind_fires_at_most_once_per_session(tmp_path: Path) -> None:
    """Same session_id → first invocation emits, second is deduped silent."""
    import tempfile
    import os

    transcript = _robot_transcript(tmp_path)
    session_id = "pytest-session-loopfix-001"
    marker = os.path.join(tempfile.gettempdir(), f"rf-agentskills-reminded-{session_id}")
    try:
        os.path.exists(marker) and os.remove(marker)
        payload = {"transcript_path": str(transcript), "session_id": session_id}
        out1, _e1, rc1 = _run(REMIND_SCRIPT, payload)
        out2, _e2, rc2 = _run(REMIND_SCRIPT, payload)
        assert rc1 == 0 and rc2 == 0
        assert "additionalContext" in out1, "first invocation should remind"
        assert out2 == "", "second invocation in same session should be deduped"
    finally:
        if os.path.exists(marker):
            os.remove(marker)


def test_validate_project_silent_when_stop_hook_active() -> None:
    """The opt-in project validator must not re-block on a continuation,
    even with the flag enabled and a persistent finding."""
    import os

    env = os.environ.copy()
    env["RF_AGENTSKILLS_PROJECT_VALIDATION"] = "1"
    out, err, rc = _run(
        VALIDATE_PROJECT_SCRIPT,
        {"cwd": str(Path.cwd()), "stop_hook_active": True},
        env=env,
    )
    assert rc == 0
    assert out == "" and err == ""


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
    """A well-formed .robot file → exit 0 and no model-facing error,
    whether or not Robocop is installed (graceful no-op when absent)."""
    import os
    robot_file = tmp_path / "ok.robot"
    robot_file.write_text(
        "*** Test Cases ***\nLogin\n    [Documentation]    ok\n    Log    hello\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps({"file_path": str(robot_file)})
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 0, err
    assert "validation found errors" not in err


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_clean_undocumented_file_passes(tmp_path: Path) -> None:
    """`--threshold E` must NOT flag style-only issues: an undocumented
    but structurally valid file passes cleanly (no DOC03 noise)."""
    import os
    robot_file = tmp_path / "undoc.robot"
    # No [Documentation] anywhere — default Robocop would emit DOC02/DOC03.
    robot_file.write_text(
        "*** Test Cases ***\nLogin\n    Log    hello\n", encoding="utf-8"
    )
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps({"file_path": str(robot_file)})
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 0, err
    assert err == "", f"style-only findings should be suppressed, got: {err!r}"


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_flags_structural_error_with_exit_2(tmp_path: Path) -> None:
    """A structural error (unterminated FOR) → exit 2 (NOT 1) with the
    diagnostic on stderr so the agent receives it and can self-correct."""
    import os
    robot_file = tmp_path / "broken.robot"
    robot_file.write_text(
        "*** Test Cases ***\nT\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["TOOL_INPUT"] = json.dumps({"file_path": str(robot_file)})
    out, err, rc = _run(VALIDATE_SCRIPT, stdin="", env=env)
    assert rc == 2, f"expected exit 2, got {rc}; stderr={err!r}"
    assert "broken.robot" in err
    # The specific Robocop error id for invalid FOR syntax.
    assert "ERR" in err


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_reads_file_path_from_stdin_json(tmp_path: Path) -> None:
    """The new script reads `tool_input.file_path` from stdin JSON (the
    documented PostToolUse contract), not just the legacy TOOL_INPUT env."""
    import os
    robot_file = tmp_path / "broken_stdin.robot"
    robot_file.write_text(
        "*** Test Cases ***\nT\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n",
        encoding="utf-8",
    )
    # Strip TOOL_INPUT so only the stdin path can satisfy the hook.
    env = {k: v for k, v in os.environ.items() if k != "TOOL_INPUT"}
    payload = {"tool_input": {"file_path": str(robot_file)}}
    out, err, rc = _run(VALIDATE_SCRIPT, stdin=json.dumps(payload), env=env)
    assert rc == 2, f"expected exit 2 via stdin input, got {rc}; stderr={err!r}"
    assert "broken_stdin.robot" in err


# --- check_rf_environment.mjs ---------------------------------------------


def test_check_rf_environment_runs_to_completion() -> None:
    """SessionStart diagnostic must always exit 0 and print to stderr."""
    out, err, rc = _run(CHECK_ENV_SCRIPT, stdin="")
    assert rc == 0
    assert "Robot Framework Environment Check" in err


# --- validate_robot_project.mjs (Stop tier, opt-in) -----------------------


def test_project_validation_noop_when_flag_unset(tmp_path: Path) -> None:
    """Without RF_AGENTSKILLS_PROJECT_VALIDATION the whole tier is a no-op,
    even when the project contains broken Robot Framework code."""
    import os
    (tmp_path / "suite.robot").write_text(
        "*** Settings ***\nResource    nonexistent.resource\n"
        "*** Test Cases ***\nT\n    Log    hi\n",
        encoding="utf-8",
    )
    env = {
        k: v for k, v in os.environ.items()
        if k != "RF_AGENTSKILLS_PROJECT_VALIDATION"
    }
    payload = {"cwd": str(tmp_path)}
    out, err, rc = _run(
        VALIDATE_PROJECT_SCRIPT, stdin=json.dumps(payload), env=env
    )
    assert rc == 0
    assert out == ""
    assert err == ""


@pytest.mark.skipif(not _HAS_ROBOT, reason="robotframework not installed")
def test_project_validation_detects_broken_import_via_error_line(
    tmp_path: Path,
) -> None:
    """A broken import surfaces only as a dryrun `[ ERROR ]` line (dryrun
    exits 0 for it). The tier must catch it anyway and exit 2."""
    import os
    (tmp_path / "suite.robot").write_text(
        "*** Settings ***\nResource    nonexistent.resource\n"
        "*** Test Cases ***\nT\n    [Documentation]    ok\n    Log    hi\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["RF_AGENTSKILLS_PROJECT_VALIDATION"] = "1"
    payload = {"cwd": str(tmp_path)}
    out, err, rc = _run(
        VALIDATE_PROJECT_SCRIPT, stdin=json.dumps(payload), env=env
    )
    assert rc == 2, f"expected exit 2, got {rc}; stderr={err!r}"
    assert "nonexistent.resource" in err


@pytest.mark.skipif(not _HAS_FIND_UNUSED, reason="find-unused not installed")
def test_project_validation_reports_unused_keyword(tmp_path: Path) -> None:
    """An never-called keyword is reported by the find-unused check."""
    import os
    (tmp_path / "helpers.resource").write_text(
        "*** Keywords ***\nUsed Keyword\n    Log    used\n"
        "Unused Keyword\n    Log    nobody calls me\n",
        encoding="utf-8",
    )
    (tmp_path / "suite.robot").write_text(
        "*** Settings ***\nResource    helpers.resource\n"
        "*** Test Cases ***\nT\n    [Documentation]    ok\n    Used Keyword\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["RF_AGENTSKILLS_PROJECT_VALIDATION"] = "1"
    payload = {"cwd": str(tmp_path)}
    out, err, rc = _run(
        VALIDATE_PROJECT_SCRIPT, stdin=json.dumps(payload), env=env
    )
    assert rc == 2, f"expected exit 2, got {rc}; stderr={err!r}"
    assert "Unused Keyword" in err


# --- Cross-script invariants ----------------------------------------------


@pytest.mark.parametrize(
    "script",
    [
        INJECT_SCRIPT,
        REMIND_SCRIPT,
        VALIDATE_SCRIPT,
        VALIDATE_PROJECT_SCRIPT,
        CHECK_ENV_SCRIPT,
    ],
)
def test_scripts_exist(script: Path) -> None:
    assert script.is_file(), f"{script} missing"


@pytest.mark.parametrize(
    "script",
    [INJECT_SCRIPT, REMIND_SCRIPT, VALIDATE_SCRIPT, VALIDATE_PROJECT_SCRIPT],
)
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
