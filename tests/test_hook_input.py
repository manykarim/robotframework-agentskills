"""``_hook_input.mjs``: one reader for every agent's hook input (marketplace-distribution D2).

Fixtures in ``tests/fixtures/hook_inputs/`` follow the input shapes recorded on
2026-10-08 from Claude Code, Copilot CLI, VS Code, Codex and Cursor.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "plugins" / "rf-agentskills" / "scripts" / "_hook_input.mjs"
FIXTURES = ROOT / "tests" / "fixtures" / "hook_inputs"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")
CWD = "/work/proj"


def _normalize(name: str) -> dict:
    payload = (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
    code = (
        f"import {{ normalizeHookInput }} from {json.dumps(HELPER.as_uri())};"
        "const r = normalizeHookInput(JSON.parse(process.argv[1]));"
        "delete r.event; process.stdout.write(JSON.stringify(r));"
    )
    out = subprocess.run([NODE, "--input-type=module", "-e", code, payload],  # type: ignore[list-item]
                         capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize(("name", "files"), [
    ("claude-code-write", ["tests/a.robot"]),
    ("copilot-cli-edit", ["tests/a.robot"]),
    ("cursor-write", ["tests/a.robot"]),
    ("cursor-after-file-edit", ["resources/b.resource"]),
    ("vscode-create-file", ["tests/a.robot"]),
    ("vscode-multi-replace", ["tests/a.robot", "resources/b.resource"]),
    ("vscode-apply-patch", ["tests/a.robot"]),
    ("codex-apply-patch", ["tests/new.robot", "resources/b.resource"]),
])
def test_edit_inputs_yield_the_edited_files(name: str, files: list[str]) -> None:
    r = _normalize(name)
    assert r["isEdit"] is True and r["isShell"] is False
    assert r["files"] == [f"{CWD}/{f}" for f in files]


@pytest.mark.parametrize(("name", "command"), [
    ("codex-bash", "robot tests"),
    ("vscode-run-in-terminal", "robot tests"),
])
def test_shell_inputs_yield_the_command(name: str, command: str) -> None:
    r = _normalize(name)
    assert r["isShell"] is True and r["isEdit"] is False
    assert r["command"] == command and r["files"] == []


def test_read_tool_is_neither_edit_nor_shell() -> None:
    # VS Code runs every hook for every tool: reading a .robot file must not
    # look like an edit.
    r = _normalize("vscode-read-file")
    assert r["isEdit"] is False and r["isShell"] is False and r["files"] == []
