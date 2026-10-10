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
import uuid
import os
import shutil
import subprocess
import sys
import time
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
HINTS_SCRIPT = PLUGIN_SCRIPTS / "rf_error_hints.mjs"
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
        encoding="utf-8",  # Node writes UTF-8 (e.g. "×"); not the Windows code page
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
        "Use rf-results to summarise why the login test failed",
        "Have rf-keyword-consultant suggest a keyword for these duplicated steps",
        "Should I use rf-libdoc here?",
        "Check the keyword arguments with libdoc",
        "Have rf-test-architect plan a CI pipeline",
        "robotidy says this file has formatting issues",
        "rfbrowser init failed — what now?",
        "Rewrite this test using RESTinstance",
        "Automate the desktop calculator with PlatynUI",
        "Use robotcode to discover all tests tagged smoke",
        "Step through the failing login with robot-debug",
        "Add a headed profile to robot.toml",
        "Load rf-browser for this login flow",
        "Use rf-setup to prepare the project",
    ],
)
def test_inject_fires_on_rf_signals(prompt: str) -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    payload = _expect_injection(out)
    ctx = payload["additionalContext"]
    # The injected context names the rf-agentskills, so callers can spot it.
    assert "rf-agentskills" in ctx
    assert "rf-libdoc" in ctx
    assert "libdoc-search" not in ctx and "libdoc-explain" not in ctx
    assert "rf-robotcode" in ctx
    assert "rf-setup" in ctx


RETIRED_SKILLS = (
    "keyword-builder",
    "testcase-builder",
    "resource-architect",
    "libdoc-search",
    "libdoc-explain",
)


PLUGIN_ROOT = INJECT_SCRIPT.parent.parent
INJECTION_BUDGET = 450


def _catalog_names() -> set[str]:
    skills = {p.name for p in (PLUGIN_ROOT / "skills").iterdir() if p.is_dir()}
    agents = {p.stem for p in (PLUGIN_ROOT / "agents").glob("*.md")}
    return skills | agents


def test_injected_context_names_only_shipped_skills() -> None:
    """modernize-plugin-agents-and-hooks D10: every rf-* token in the injected
    text is a plugin skill dir or agent file (the plugin name and the
    ``rf-<library>`` placeholder excepted); no retired name appears."""
    import re

    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": "Write a Robot Framework login test"})
    assert rc == 0
    ctx = _expect_injection(out)["additionalContext"]
    for retired in RETIRED_SKILLS:
        assert retired not in ctx
    tokens = set(re.findall(r"\brf-[a-z][a-z-]*[a-z]\b", ctx)) - {"rf-agentskills"}
    assert tokens, ctx
    assert tokens <= _catalog_names(), tokens - _catalog_names()
    assert "robotframework-" not in ctx


@pytest.mark.parametrize(
    "prompt",
    [
        "add a data-driven login test to tests/login.robot",
        "Write a Robot Framework login test",
        "use rf-python-library to build a listener",
        "Fix this:\n*** Keywords ***\nLogin\n    [Return]    ok",
        "x" * 5000 + " robot framework",
    ],
)
def test_injection_budget_and_routing(prompt: str) -> None:
    """rf-session-context-hooks: one message <= 450 characters that routes by
    task and ends with the RF 7 syntax reminder."""
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    assert out.count("hookSpecificOutput") == 1
    hso = _expect_injection(out)
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    assert len(ctx) <= INJECTION_BUDGET, len(ctx)
    for name in ("rf-language", "rf-python-library", "rf-libdoc", "robotcode libdoc"):
        assert name in ctx, name
    assert ctx.rstrip().endswith("Write RF 7 syntax: RETURN, VAR, IF, Test Tags.")
    # No skill / subagent lists any more: the text routes by task.
    assert "Subagents:" not in ctx and "Library references:" not in ctx


@pytest.mark.parametrize(
    "prompt",
    [
        "use rf-python-library to build a listener",
        "Paste:\n*** Keywords ***\nOpen App\n    Log    hi",
        "*** Settings ***\nLibrary    Collections",
        "*** Test Cases ***\nT\n    Log    x",
        "What goes under *** Variables *** here?",
        "*** Tasks ***\nDo It\n    Log    x",
        "Ask rf-debug-expert why this fails",
        "rf-results says three tests failed",
    ],
)
def test_inject_fires_on_new_ids_and_section_headers(prompt: str) -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    _expect_injection(out)


@pytest.mark.parametrize(
    "prompt",
    [
        "Turn the copy-pasted tests in tests/login.robot into a data-driven table",
        "Add a Suite Setup keyword to resources/api.resource",
        "Why does Run Keyword If get flagged in this Robot Framework suite?",
    ],
)
def test_injected_context_names_language_skill(prompt: str) -> None:
    """add-rf-language-skill: .robot / .resource prompts are routed to rf-language."""
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    ctx = _expect_injection(out)["additionalContext"]
    assert "tests, suites, keywords, resources, variables -> rf-language" in ctx


@pytest.mark.parametrize(
    "prompt",
    [
        "my robot framework library says it contains no keywords",
        "Why does my @keyword method not show up as a keyword?",
        "Should ROBOT_LIBRARY_SCOPE be SUITE for a database client?",
        "Write a robot listener that marks flaky tests as skipped",
        "Load rf-python-library for libraries/Inventory.py",
    ],
)
def test_injected_context_names_python_library_skill(prompt: str) -> None:
    """add-rf-python-library-skill: Python library prompts are routed to rf-python-library."""
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": prompt})
    assert rc == 0
    ctx = _expect_injection(out)["additionalContext"]
    assert "Python libraries/listeners -> rf-python-library" in ctx


def test_inject_fires_on_language_skill_id() -> None:
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": "Load rf-language for this suite"})
    assert rc == 0
    assert "rf-language" in _expect_injection(out)["additionalContext"]


def test_subagents_route_language_work_to_rf_language() -> None:
    agents = INJECT_SCRIPT.parent.parent / "agents"
    for name in ("rf-test-architect.md", "rf-keyword-consultant.md", "rf-migration-guide.md"):
        text = (agents / name).read_text(encoding="utf-8")
        assert "rf-language" in text, name
        assert "scripts/rf_conventions" not in text, name
    migration = (agents / "rf-migration-guide.md").read_text(encoding="utf-8")
    assert "references/migration.md" in migration and "rf_conventions" in migration


def test_injected_context_states_skill_boundaries() -> None:
    """The routing text keeps the description boundaries (sharpen-skill-descriptions
    D2, user decision 1): rf-browser / rf-requests are the defaults, installs go to
    rf-setup, library usage goes to the matching library skill."""
    out, _err, rc = _run(INJECT_SCRIPT, {"prompt": "Write a Robot Framework login test"})
    assert rc == 0
    ctx = _expect_injection(out)["additionalContext"]
    assert "library usage -> rf-<library>" in ctx
    assert "defaults: rf-browser web, rf-requests API" in ctx
    assert "installs -> rf-setup" in ctx


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
        # Bare "listener" is a JavaScript / GUI term, not a Robot Framework signal.
        "Add an event listener in JavaScript that tracks button clicks",
        # Bare "RF" is intentionally not a trigger (radio-frequency,
        # request-for-..., etc.).
        "What does RF stand for in your domain?",
        "run the unit tests and fix the RF amplifier model",
        "refactor this React component",
        # Markdown bold / emphasis is not an RF section header.
        "*** Important *** read this first",
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


def test_remind_uses_absolute_results_script_path(tmp_path: Path) -> None:
    """The reminder names the real rf_results.py (computed from the hook's own
    location) and runs it through the project environment."""
    transcript = _write_transcript(
        tmp_path,
        [json.dumps({"type": "tool_use", "input": {"file_path": "/w/a.robot", "content": "x"}})],
    )
    out, _err, rc = _run(REMIND_SCRIPT, {"transcript_path": str(transcript),
                                         "session_id": f"abs-path-{os.getpid()}-{time.time_ns()}"})
    assert rc == 0
    ctx = _expect_injection(out)["additionalContext"]
    expected = (PLUGIN_SCRIPTS.parent / "skills" / "rf-results" / "scripts" / "rf_results.py").resolve()
    assert expected.is_file()
    assert f'uv run python "{expected}"' in ctx
    assert "${CLAUDE_PLUGIN_ROOT}" not in ctx
    assert "pip install" not in ctx


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


# --- validate_robot.mjs: deprecation tier (modernize-plugin-agents-and-hooks) ---

HOOK_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hooks"
PRE_CHANGE_VALIDATE = HOOK_FIXTURES / "validate_robot_pre_change.mjs"
_needs_robocop = pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
_posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX stub interpreter")


def _sample_payload(kind: str, file: Path, cwd: Path, session: str = "") -> dict:
    """A real captured PostToolUse payload (fixture) pointed at ``file``."""
    raw = (HOOK_FIXTURES / "posttooluse_payloads.json").read_text(encoding="utf-8")
    raw = raw.replace("__FILE__", json.dumps(str(file))[1:-1])
    raw = raw.replace("__CWD__", json.dumps(str(cwd))[1:-1])
    payload = json.loads(raw)[kind]
    payload["session_id"] = session
    return payload


def _hook_env(**extra: str) -> dict:
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("TOOL_INPUT", "RF_AGENTSKILLS_DEPRECATION_CHECK", "RF_AGENTSKILLS_FILE_DRYRUN",
                     "RF_AGENTSKILLS_HOOK_TIMEOUT_MS")
    }
    if sys.prefix != sys.base_prefix:
        env["VIRTUAL_ENV"] = sys.prefix  # the test env (has Robocop + RF)
    env.update(extra)
    return env


def _context(out: str) -> str:
    if not out.strip():
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def _write_payload(file: Path, cwd: Path, session: str = "") -> dict:
    return _sample_payload("write_create", file, cwd, session) | {
        "tool_input": {"file_path": str(file), "content": file.read_text(encoding="utf-8")},
    }


def _new_session() -> str:
    import uuid

    return f"pytest-{uuid.uuid4().hex}"


@pytest.fixture
def session_id():
    import tempfile

    sid = _new_session()
    yield sid
    marker = Path(tempfile.gettempdir()) / f"rf-agentskills-depr-{sid}.json"
    marker.unlink(missing_ok=True)


EDITED_RESOURCE = (
    "*** Keywords ***\nFirst\n    Log    one\n    [Return]    x\n\nSecond\n    Log    two\n    Log    two\n"
)


@_needs_robocop
def test_depr_return_added_by_edit_is_a_warning(tmp_path: Path, session_id: str) -> None:
    """The captured Edit payload adds `[Return]` on line 4 -> exit 0, DEPR11 listed
    with file, line and RETURN; nothing on stderr (never exit 2)."""
    res = tmp_path / "kw.resource"
    res.write_text(EDITED_RESOURCE, encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _sample_payload("edit", res, tmp_path, session_id), env=_hook_env())
    assert rc == 0, err
    assert err == ""
    ctx = _context(out)
    assert "WARN DEPR11 kw.resource:4" in ctx and "`RETURN`" in ctx
    assert "not blocking" in ctx


@_needs_robocop
def test_replace_all_patch_scopes_touched_lines(tmp_path: Path, session_id: str) -> None:
    """edit_replace_all touches lines 7-8 only: the older `[Return]` on line 4 is
    counted, not listed."""
    res = tmp_path / "kw.resource"
    res.write_text(EDITED_RESOURCE.replace("two", "deux"), encoding="utf-8")
    payload = _sample_payload("edit_replace_all", res, tmp_path, session_id)
    out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_hook_env())
    assert rc == 0, err
    ctx = _context(out)
    assert "WARN DEPR11" not in ctx
    assert "DEPR11 ×1" in ctx


@_needs_robocop
@pytest.mark.parametrize("mode", [None, "warn", "block", "BLOCK", "nonsense"])
def test_run_keyword_if_never_exits_2(tmp_path: Path, session_id: str, mode: str | None) -> None:
    """Default, `warn` and unknown values (incl. a legacy `block`) all warn only."""
    suite = tmp_path / "rkif.robot"
    suite.write_text(
        "*** Test Cases ***\nT\n    Run Keyword If    ${TRUE}    Log    yes\n", encoding="utf-8"
    )
    env = _hook_env(**({"RF_AGENTSKILLS_DEPRECATION_CHECK": mode} if mode else {}))
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path, session_id), env=env)
    assert rc == 0, err
    assert err == ""
    ctx = _context(out)
    assert "WARN DEPR08 rkif.robot:3" in ctx and "`IF`" in ctx


@_needs_robocop
def test_set_suite_variable_is_a_hint(tmp_path: Path, session_id: str) -> None:
    suite = tmp_path / "var.robot"
    suite.write_text("*** Test Cases ***\nT\n    Set Suite Variable    ${X}    1\n", encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path, session_id), env=_hook_env())
    assert rc == 0, err
    ctx = _context(out)
    assert "HINT DEPR05 var.robot:3" in ctx and "VAR" in ctx


@_needs_robocop
def test_untouched_force_tags_is_counted(tmp_path: Path, session_id: str) -> None:
    """An edit that does not touch the existing `Force Tags` line -> exit 0 and a
    per-rule count, no individual warning."""
    suite = tmp_path / "tags.robot"
    suite.write_text(
        "*** Settings ***\nForce Tags    smoke\n\n*** Test Cases ***\nT\n    Log    changed\n",
        encoding="utf-8",
    )
    payload = _sample_payload("edit", suite, tmp_path, session_id)
    payload["tool_input"] = {"file_path": str(suite), "old_string": "Log    old", "new_string": "Log    changed"}
    payload["tool_response"]["structuredPatch"] = [
        {"oldStart": 5, "oldLines": 2, "newStart": 5, "newLines": 2,
         "lines": [" T", "-    Log    old", "+    Log    changed"]},
    ]
    out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_hook_env())
    assert rc == 0, err
    ctx = _context(out)
    assert "WARN DEPR07" not in ctx
    assert "DEPR07 ×1" in ctx


@_needs_robocop
def test_edit_without_patch_uses_new_string_span(tmp_path: Path, session_id: str) -> None:
    """Fallback 2 (D4): no structuredPatch -> the lines where new_string occurs."""
    suite = tmp_path / "span.robot"
    suite.write_text(
        "*** Settings ***\nForce Tags    smoke\n\n*** Keywords ***\nK\n    [Return]    x\n",
        encoding="utf-8",
    )
    payload = {"session_id": session_id, "cwd": str(tmp_path), "tool_name": "Edit",
               "tool_input": {"file_path": str(suite), "old_string": "RETURN", "new_string": "    [Return]    x"}}
    out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_hook_env())
    assert rc == 0, err
    ctx = _context(out)
    assert "WARN DEPR11 span.robot:6" in ctx
    assert "WARN DEPR07" not in ctx and "DEPR07 ×1" in ctx


@_needs_robocop
def test_same_finding_is_listed_once_per_session(tmp_path: Path, session_id: str) -> None:
    suite = tmp_path / "twice.robot"
    suite.write_text(
        "*** Test Cases ***\nT\n    Run Keyword If    ${TRUE}    Log    yes\n", encoding="utf-8"
    )
    payload = _write_payload(suite, tmp_path, session_id)
    out1, _e1, rc1 = _run(VALIDATE_SCRIPT, payload, env=_hook_env())
    out2, _e2, rc2 = _run(VALIDATE_SCRIPT, payload, env=_hook_env())
    assert rc1 == rc2 == 0
    assert "WARN DEPR08" in _context(out1)
    ctx2 = _context(out2)
    assert "WARN DEPR08" not in ctx2 and "DEPR08 ×1" in ctx2
    # A different session lists it again.
    out3, _e3, _rc3 = _run(VALIDATE_SCRIPT, payload | {"session_id": session_id + "-b"}, env=_hook_env())
    assert "WARN DEPR08" in _context(out3)
    import tempfile

    (Path(tempfile.gettempdir()) / f"rf-agentskills-depr-{session_id}-b.json").unlink(missing_ok=True)


@_needs_robocop
def test_error_suppresses_warning_until_next_clean_edit(tmp_path: Path, session_id: str) -> None:
    """Unterminated FOR + new `[Return]` -> exit 2 with only the error on stderr;
    the DEPR11 warning is not recorded and shows on the next clean edit."""
    res = tmp_path / "mixed.resource"
    res.write_text(
        "*** Keywords ***\nK\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n    [Return]    x\n",
        encoding="utf-8",
    )
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=_hook_env())
    assert rc == 2, err
    assert "ERR" in err and "mixed.resource" in err
    assert "DEPR" not in err and "DEPR" not in out
    assert json.loads(out)["decision"] == "block"  # the error, for Copilot CLI
    res.write_text(
        "*** Keywords ***\nK\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n    END\n    [Return]    x\n",
        encoding="utf-8",
    )
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=_hook_env())
    assert rc == 0, err
    assert "WARN DEPR11 mixed.resource:6" in _context(out)


@_needs_robocop
def test_warning_output_is_capped(tmp_path: Path, session_id: str) -> None:
    body = "".join(f"K{i}\n    [Return]    {i}\n" for i in range(25))
    res = tmp_path / "many.resource"
    res.write_text("*** Keywords ***\n" + body, encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=_hook_env())
    assert rc == 0, err
    ctx = _context(out)
    depr_block = ctx.split("\n\n")[0]
    assert depr_block.count("WARN DEPR11") == 10
    assert "15 more" in depr_block
    assert len(depr_block) <= 2000


@_needs_robocop
def test_off_mode_silences_deprecations_but_not_errors(tmp_path: Path, session_id: str) -> None:
    res = tmp_path / "off.resource"
    res.write_text("*** Keywords ***\nK\n    [Return]    x\n", encoding="utf-8")
    env = _hook_env(RF_AGENTSKILLS_DEPRECATION_CHECK="off")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=env)
    assert rc == 0, err
    assert "DEPR" not in out and err == ""
    broken = tmp_path / "broken.robot"
    broken.write_text("*** Test Cases ***\nT\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n", encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(broken, tmp_path, session_id), env=env)
    assert rc == 2 and "ERR" in err


@_needs_robocop
def test_project_robocop_config_is_respected(tmp_path: Path, session_id: str) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.robocop.lint]\nignore = ["DEPR08"]\n', encoding="utf-8")
    suite = tmp_path / "cfg.robot"
    suite.write_text("*** Test Cases ***\nT\n    Run Keyword If    ${TRUE}    Log    yes\n", encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path, session_id), env=_hook_env())
    assert rc == 0, err
    assert "DEPR08" not in _context(out)


@_needs_robocop
def test_read_only_tmpdir_still_warns(tmp_path: Path, session_id: str) -> None:
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    res = tmp_path / "ro.resource"
    res.write_text("*** Keywords ***\nK\n    [Return]    x\n", encoding="utf-8")
    try:
        env = _hook_env(TMPDIR=str(ro), TEMP=str(ro), TMP=str(ro))
        out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=env)
    finally:
        ro.chmod(0o700)
    assert rc == 0, err
    assert "WARN DEPR11" in _context(out)


@_needs_robocop
def test_no_robocop_cache_left_in_project(tmp_path: Path, session_id: str) -> None:
    """--no-cache: the hook never leaves .robocop_cache/ in the user's project."""
    res = tmp_path / "c.resource"
    res.write_text("*** Keywords ***\nK\n    [Return]    x\n", encoding="utf-8")
    _run(VALIDATE_SCRIPT, _write_payload(res, tmp_path, session_id), env=_hook_env())
    assert not (tmp_path / ".robocop_cache").exists()


@pytest.mark.rf61
@_posix_only
def test_rf61_project_gets_no_var_hint(tmp_path: Path, session_id: str) -> None:
    """Robocop gates DEPR05 by the project's RF version: a project .venv with RF 6.1
    gets no VAR hint (the .venv wins over the test env)."""
    import importlib.metadata

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not installed")
    robocop_version = importlib.metadata.version("robotframework-robocop")
    venv = tmp_path / ".venv"
    try:
        subprocess.run([uv, "venv", "-q", str(venv)], check=True, capture_output=True, timeout=120)
        subprocess.run(
            [uv, "pip", "install", "-q", "--python", str(venv / "bin" / "python"),
             "robotframework==6.1.1", f"robotframework-robocop=={robocop_version}"],
            check=True, capture_output=True, timeout=300,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        pytest.skip(f"cannot build an RF 6.1 venv (offline?): {exc}")
    suite = tmp_path / "old.robot"
    suite.write_text(
        "*** Test Cases ***\nT\n    Set Suite Variable    ${X}    1\n    Run Keyword If    ${TRUE}    Log    x\n",
        encoding="utf-8",
    )
    env = _hook_env()
    env.pop("VIRTUAL_ENV", None)
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path, session_id), env=env)
    assert rc == 0, err
    ctx = _context(out)
    assert "DEPR08" in ctx, "the RF 6.1 venv's Robocop ran"
    assert "DEPR05" not in ctx


def _stub_python(path: Path, body: str) -> Path:
    """A POSIX shell script that stands in for a Python interpreter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


@_posix_only
def test_garbage_robocop_output_is_silent(tmp_path: Path) -> None:
    """Robocop exits 1 but prints nothing parsable -> tool failure -> silence."""
    venv = tmp_path / "stubenv"
    _stub_python(venv / "bin" / "python",
                 'case "$1" in -c) exit 0;; esac\necho "Traceback (most recent call last): boom"\nexit 1\n')
    suite = tmp_path / "g.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path), env=_hook_env(VIRTUAL_ENV=str(venv)))
    assert (rc, out, err) == (0, "", "")


@_posix_only
def test_hung_robocop_times_out_silently(tmp_path: Path) -> None:
    import time as _time

    venv = tmp_path / "stubenv"
    _stub_python(venv / "bin" / "python", 'case "$1" in -c) exit 0;; esac\nexec sleep 30\n')
    suite = tmp_path / "h.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    env = _hook_env(VIRTUAL_ENV=str(venv), RF_AGENTSKILLS_HOOK_TIMEOUT_MS="1000")
    start = _time.monotonic()
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path), env=env)
    assert (rc, out, err) == (0, "", "")
    assert _time.monotonic() - start < 15


def _logging_stub(path: Path, log: Path, tag: str) -> Path:
    return _stub_python(path, f'echo "{tag} $*" >> "{log}"\ncase "$1" in -c) exit 0;; esac\nexit 0\n')


@_posix_only
def test_interpreter_order_venv_over_runtime_json(tmp_path: Path) -> None:
    """_python_env.mjs: <cwd>/.venv beats python_runtime.json; VIRTUAL_ENV beats .venv."""
    scripts = tmp_path / "plugin" / "scripts"
    shutil.copytree(PLUGIN_SCRIPTS, scripts)
    log = tmp_path / "calls.log"
    runtime_py = _logging_stub(tmp_path / "runtime" / "python", log, "RUNTIME")
    (scripts / "python_runtime.json").write_text(json.dumps({"interpreter": str(runtime_py)}), encoding="utf-8")
    project = tmp_path / "project"
    _logging_stub(project / ".venv" / "bin" / "python", log, "DOTVENV")
    active = _logging_stub(tmp_path / "active" / "bin" / "python", log, "ACTIVE")
    suite = project / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    env = _hook_env()
    env.pop("VIRTUAL_ENV", None)
    _run(scripts / "validate_robot.mjs", _write_payload(suite, project), env=env)
    first = log.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("DOTVENV"), first
    log.unlink()
    _run(scripts / "validate_robot.mjs", _write_payload(suite, project),
         env=env | {"VIRTUAL_ENV": str(active.parent.parent)})
    assert log.read_text(encoding="utf-8").splitlines()[0].startswith("ACTIVE")
    log.unlink()
    shutil.rmtree(project / ".venv")
    _run(scripts / "validate_robot.mjs", _write_payload(suite, project), env=env)
    assert log.read_text(encoding="utf-8").splitlines()[0].startswith("RUNTIME")


@_posix_only
def test_file_dryrun_is_off_by_default(tmp_path: Path) -> None:
    log = tmp_path / "calls.log"
    venv = tmp_path / "stubenv"
    _logging_stub(venv / "bin" / "python", log, "PY")
    suite = tmp_path / "d.robot"
    suite.write_text("*** Test Cases ***\nT\n    Missing Keyword\n", encoding="utf-8")
    _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path), env=_hook_env(VIRTUAL_ENV=str(venv)))
    calls = log.read_text(encoding="utf-8")
    assert "-m robocop" in calls
    assert "-m robot " not in calls and "import robot\n" not in calls


@pytest.mark.skipif(not _HAS_ROBOT, reason="robotframework not installed")
def test_file_dryrun_reports_unknown_keyword(tmp_path: Path) -> None:
    suite = tmp_path / "dry.robot"
    suite.write_text("*** Test Cases ***\nT\n    This Keyword Does Not Exist    1\n", encoding="utf-8")
    env = _hook_env(RF_AGENTSKILLS_FILE_DRYRUN="1", RF_AGENTSKILLS_DEPRECATION_CHECK="off")
    out, err, rc = _run(VALIDATE_SCRIPT, _write_payload(suite, tmp_path), env=env)
    assert rc == 0, err
    ctx = _context(out)
    assert "No keyword with name 'This Keyword Does Not Exist'" in ctx
    assert "advisory" in ctx
    # .resource and __init__.robot are never dry-run on their own.
    for name in ("x.resource", "__init__.robot"):
        other = tmp_path / name
        other.write_text("*** Keywords ***\nK\n    Nope Nope\n", encoding="utf-8")
        out, _err, rc = _run(VALIDATE_SCRIPT, _write_payload(other, tmp_path), env=env)
        assert rc == 0 and "No keyword with name" not in out


def test_hooks_json_declares_timeouts() -> None:
    hooks = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    expected = {"PostToolUse": 45, "UserPromptSubmit": 15, "SessionStart": 15}
    # Per-script overrides: the Bash error-hint hook only scans text.
    per_script = {"rf_error_hints.mjs": 10}
    for event, timeout in expected.items():
        for entry in hooks[event]:
            for hook in entry["hooks"]:
                script = next((s for s in per_script if s in hook["command"]), None)
                assert hook.get("timeout") == per_script.get(script, timeout), (event, hook)
    # 45 s covers Robocop check (10) + format (10) + opt-in dry run (20) + probes.
    assert expected["PostToolUse"] >= 10 + 10 + 20


def test_every_spawn_in_hooks_has_a_timeout() -> None:
    import re

    for script in sorted(PLUGIN_SCRIPTS.glob("*.mjs")):
        text = script.read_text(encoding="utf-8")
        calls = len(re.findall(r"\bspawnSync\(", text))
        guarded = len(re.findall(r"spawnOptions\(", text))
        assert guarded >= calls, f"{script.name}: {calls} spawnSync calls, {guarded} with spawnOptions"
        assert "uv run" not in re.sub(r"//.*", "", text) or script.name == "maybe_remind_robot_tests.mjs"
        assert "function loadPythonInterpreters" not in text, script.name


def test_robocop_always_runs_without_cache() -> None:
    import re

    for script in sorted(PLUGIN_SCRIPTS.glob("*.mjs")):
        text = script.read_text(encoding="utf-8")
        for m in re.finditer(r'"robocop",\s*"(check|format)"', text):
            window = text[m.start(): m.start() + 200]
            assert "--no-cache" in window, script.name


def _median_ms(script: Path, payload: dict, env: dict, cwd: Path, runs: int = 5) -> float:
    import statistics

    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run([NODE, str(script)], input=json.dumps(payload), capture_output=True,  # type: ignore[list-item]
                       text=True, timeout=60, env=env, cwd=cwd)
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


@pytest.mark.slow
@_needs_robocop
@pytest.mark.skipif(bool(os.environ.get("CI")) and not os.environ.get("RF_AGENTSKILLS_BENCH"),
                    reason="latency budget is measured on the dev machine (set RF_AGENTSKILLS_BENCH=1 in CI)")
def test_latency_budget_500_lines(tmp_path: Path) -> None:
    """D9: the new hook adds <= 150 ms (median of 5) over the pre-change hook on a
    generated 500-line valid .robot file."""
    lines = ["*** Test Cases ***"]
    for i in range(100):
        lines += [f"Test {i}", "    [Documentation]    generated", f"    Log    {i}", "    Should Be True    ${TRUE}", ""]
    suite = tmp_path / "big.robot"
    suite.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert len(suite.read_text(encoding="utf-8").splitlines()) >= 500
    payload = _write_payload(suite, tmp_path)
    env = _hook_env()
    _median_ms(VALIDATE_SCRIPT, payload, env, tmp_path, runs=1)  # warm-up
    old = _median_ms(PRE_CHANGE_VALIDATE, payload, env, tmp_path)
    new = _median_ms(VALIDATE_SCRIPT, payload, env, tmp_path)
    print(f"validate_robot.mjs latency on 500 lines: pre-change {old:.0f} ms, new {new:.0f} ms, "
          f"added {new - old:.0f} ms")
    assert new - old <= 150, (old, new)


# --- check_rf_environment.mjs ---------------------------------------------


def test_check_rf_environment_runs_to_completion() -> None:
    """SessionStart diagnostic must always exit 0 and print to stderr."""
    out, err, rc = _run(CHECK_ENV_SCRIPT, {"cwd": str(Path.cwd()), "hook_event_name": "SessionStart"})
    assert rc == 0
    assert "Robot Framework Environment Check" in err
    assert "Robocop" in err


@pytest.mark.parametrize("stdin", ["", "not json {", "[]", '"text"'])
def test_check_rf_environment_silent_on_bad_input(stdin: str) -> None:
    out, err, rc = _run(CHECK_ENV_SCRIPT, stdin=stdin)
    assert (rc, out, err) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="fake POSIX python3 shim")
def test_check_rf_environment_points_to_setup_skill(tmp_path: Path) -> None:
    """When packages are missing, the report names the rf-setup skill and uv
    commands, reports Robocop (and that checks on edit are off without it) and
    never recommends pip install or rfbrowser init. Fake ``python3``/``python`` first on
    PATH make every import check fail; the event cwd has no .venv."""
    import stat
    for name in ("python3", "python"):
        fake = tmp_path / name
        fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"
    _out, err, rc = _run(CHECK_ENV_SCRIPT, {"cwd": str(tmp_path)}, env=env)
    assert rc == 0
    assert "Not installed:" in err
    assert "rf-setup skill" in err
    assert "uv add robotframework" in err
    assert "uv add --dev robotframework-robocop" in err
    assert "robocop" in err.lower() and "checks on edit are disabled" in err
    assert "pip install" not in err
    assert "rfbrowser init" not in err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX .venv layout")
def test_check_rf_environment_uses_project_venv(tmp_path: Path) -> None:
    """Same interpreter resolution as the validation hooks: <cwd>/.venv first."""
    venv_py = tmp_path / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    _out, err, rc = _run(CHECK_ENV_SCRIPT, {"cwd": str(tmp_path)}, env=env)
    assert rc == 0
    assert f"Interpreter: {venv_py}" in err


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


def test_hooks_readme_documents_modes_and_variables() -> None:
    import re

    readme = (PLUGIN_ROOT / "hooks" / "README.md").read_text(encoding="utf-8")
    for needle in ("RF_AGENTSKILLS_DEPRECATION_CHECK", "RF_AGENTSKILLS_FILE_DRYRUN", "--no-cache",
                   "_python_env.mjs", "VIRTUAL_ENV", "ignore = [\"DEPR08\"]", "structuredPatch"):
        assert needle in readme, needle
    row = next(ln for ln in readme.splitlines() if ln.startswith("| `RF_AGENTSKILLS_DEPRECATION_CHECK`"))
    assert "`warn` (default), `off`" in row
    assert "`block`" not in readme
    # The Stop-hook trap stays documented.
    assert re.search(r"exit 0 is not\s+sufficient", readme)
    # The comma-select trap is documented, never recommended.
    assert not re.search(r"--select '[^']*,", readme.replace("(`--select 'DEPR*,ERR*'`)", ""))


# ── rf_error_hints.mjs (PostToolUse on Bash) ────────────────────────────────


def _bash_event(output: str, session: str | None = None) -> dict:
    event: dict = {"tool_name": "Bash", "tool_input": {"command": "robot tests"},
                   "tool_response": {"stdout": output, "stderr": ""}}
    if session:
        event["session_id"] = session
    return event


def _hint(stdout: str) -> str:
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"] if stdout.strip() else ""


def test_error_hint_for_keyword_with_values_in_name(tmp_path) -> None:
    out = ("Select A Team | FAIL |\nNo keyword with name 'Select team Los Angeles Lakers' found. "
           "Did you try using keyword 'teams.Select team' and forgot to use enough whitespace")
    stdout, _err, rc = _run(HINTS_SCRIPT, _bash_event(out, f"s-{uuid.uuid4().hex}"))
    hint = _hint(stdout)
    assert rc == 0
    assert "embedded-argument" in hint and "${team:\\S+}" in hint and "literal" in hint
    assert "rf-language" in hint and len(hint) <= 400


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("Multiple keywords with name 'Open App' found", "rf-language"),
        ("Invalid argument syntax '${count}: int'", "${count: int}"),
        ("Resolving variable '${missing}' failed: Variable not found", "rf-language"),
        ("Importing library 'Browser' failed: ModuleNotFoundError", "rf-setup"),
    ],
)
def test_error_hint_kinds(tmp_path, output: str, expected: str) -> None:
    stdout, _err, rc = _run(HINTS_SCRIPT, _bash_event(output))
    assert rc == 0 and expected in _hint(stdout)
    assert len(_hint(stdout)) <= 400


def test_error_hint_once_per_session(tmp_path) -> None:
    session = f"once-{uuid.uuid4().hex}"
    first, _e, _r = _run(HINTS_SCRIPT, _bash_event("No keyword with name 'A b c' found", session))
    second, _e2, rc = _run(HINTS_SCRIPT, _bash_event("No keyword with name 'X y' found", session))
    assert _hint(first) and not second.strip() and rc == 0


def test_error_hint_ignores_unrelated_output() -> None:
    stdout, _err, rc = _run(HINTS_SCRIPT, _bash_event("2 tests, 2 passed, 0 failed"))
    assert rc == 0 and not stdout.strip()


@pytest.mark.parametrize("stdin", ["", "not json", "[]", '{"tool_response": null}'])
def test_error_hint_never_blocks_on_bad_input(stdin: str) -> None:
    stdout, _err, rc = _run(HINTS_SCRIPT, stdin=stdin)
    assert rc == 0 and not stdout.strip()


def test_error_hint_bounds_long_names() -> None:
    stdout, _err, _rc = _run(HINTS_SCRIPT, _bash_event("No keyword with name '" + "x" * 500 + "' found"))
    assert len(_hint(stdout)) <= 400


# --- marketplace-distribution D2: every agent's edit input -----------------

_BROKEN_FOR = "*** Test Cases ***\nT\n    FOR    ${x}    IN    a    b\n        Log    ${x}\n"


def _clean_env() -> dict:
    import os
    env = os.environ.copy()
    env.pop("TOOL_INPUT", None)
    return env


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_codex_apply_patch_adding_broken_robot(tmp_path: Path) -> None:
    """Codex sends file edits as `apply_patch` with the patch in tool_input.command."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "new.robot").write_text(_BROKEN_FOR, encoding="utf-8")
    patch = "*** Begin Patch\n*** Add File: tests/new.robot\n" + "".join(
        f"+{line}\n" for line in _BROKEN_FOR.splitlines()) + "*** End Patch\n"
    payload = {"hook_event_name": "PostToolUse", "cwd": str(tmp_path),
               "tool_name": "apply_patch", "tool_input": {"command": patch}}
    _out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_clean_env())
    assert rc == 2, err
    assert "new.robot" in err and "ERR" in err


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_vscode_apply_patch_with_two_files(tmp_path: Path) -> None:
    """A VS Code patch (tool_input.input) touching a broken and a clean file:
    the broken one is reported, the merged result keeps exit 2."""
    (tmp_path / "bad.robot").write_text(_BROKEN_FOR, encoding="utf-8")
    (tmp_path / "ok.robot").write_text("*** Test Cases ***\nT\n    Log    hi\n", encoding="utf-8")
    patch = (f"*** Begin Patch\n*** Update File: {tmp_path / 'ok.robot'}\n@@\n+    Log    hi\n"
             f"*** Update File: {tmp_path / 'bad.robot'}\n@@\n+        Log    ${{x}}\n*** End Patch")
    payload = {"hook_event_name": "PostToolUse", "cwd": str(tmp_path),
               "tool_name": "apply_patch", "tool_input": {"input": patch}}
    _out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_clean_env())
    assert rc == 2, err
    assert "bad.robot" in err and "ok.robot" not in err


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_vscode_create_file_with_camelcase_path(tmp_path: Path) -> None:
    robot_file = tmp_path / "created.robot"
    robot_file.write_text(_BROKEN_FOR, encoding="utf-8")
    payload = {"hook_event_name": "PostToolUse", "cwd": str(tmp_path),
               "tool_name": "create_file", "tool_input": {"filePath": str(robot_file), "content": _BROKEN_FOR}}
    _out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_clean_env())
    assert rc == 2, err
    assert "created.robot" in err


@pytest.mark.parametrize(("script", "tool", "tool_input"), [
    ("validate", "read_file", {"filePath": "PATH"}),
    ("validate", "run_in_terminal", {"command": "robot tests"}),
    ("hints", "read_file", {"filePath": "PATH"}),
    ("hints", "create_file", {"filePath": "PATH", "content": "No keyword with name 'X' found"}),
])
def test_hooks_stay_silent_for_tools_they_do_not_handle(
    tmp_path: Path, script: str, tool: str, tool_input: dict
) -> None:
    """VS Code ignores Claude-format matchers and runs every hook for every tool."""
    import time
    robot_file = tmp_path / "x.robot"
    robot_file.write_text(_BROKEN_FOR, encoding="utf-8")
    tool_input = {k: (str(robot_file) if v == "PATH" else v) for k, v in tool_input.items()}
    payload = {"hook_event_name": "PostToolUse", "session_id": f"silent-{uuid.uuid4().hex}",
               "cwd": str(tmp_path), "tool_name": tool, "tool_input": tool_input,
               "tool_response": "No keyword with name 'X' found"}
    start = time.monotonic()
    out, err, rc = _run(VALIDATE_SCRIPT if script == "validate" else HINTS_SCRIPT, payload, env=_clean_env())
    elapsed = time.monotonic() - start
    assert (out, err, rc) == ("", "", 0)
    # node start-up included (50-80 ms on Linux); Windows starts node slower
    assert elapsed < (0.5 if sys.platform == "win32" else 0.2)


def test_hints_read_vscode_terminal_and_copilot_tool_result() -> None:
    for payload in (
        {"session_id": f"hints-vscode-{uuid.uuid4().hex}", "tool_name": "run_in_terminal",
         "tool_input": {"command": "robot t"}, "tool_response": "No keyword with name 'Foo' found."},
        {"session_id": f"hints-copilot-{uuid.uuid4().hex}", "tool_name": "Bash",
         "tool_input": {"command": "robot t"}, "tool_result": {"stdout": "No keyword with name 'Foo' found."}},
    ):
        out, _err, rc = _run(HINTS_SCRIPT, payload)
        assert rc == 0 and "rf-language" in out, payload


@pytest.mark.skipif(not _HAS_ROBOCOP, reason="Robocop not installed")
def test_validate_error_also_reports_decision_for_copilot(tmp_path: Path) -> None:
    """Copilot CLI passes only decision/reason to its model (not stderr or
    additionalContext): errors also go out as {"decision": "block", "reason": ...}."""
    robot_file = tmp_path / "broken.robot"
    robot_file.write_text(_BROKEN_FOR, encoding="utf-8")
    payload = {"hook_event_name": "PostToolUse", "cwd": str(tmp_path),
               "tool_name": "Edit", "tool_input": {"file_path": str(robot_file)}}
    out, err, rc = _run(VALIDATE_SCRIPT, payload, env=_clean_env())
    assert rc == 2 and "broken.robot" in err
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert decision["reason"].startswith("The edit was applied")
    assert "broken.robot" in decision["reason"] and "ERR" in decision["reason"]
