"""Uninstall-correctness tests — coexistence with the user and other tools.

These guard the granular, ownership-aware config merges (see
``transforms.merge_hooks_block`` / ``remove_owned_hook_entries`` and the
``json_hooks`` / ``json_nested`` merge kinds). The earlier whole-`hooks`-key
replace destroyed foreign and user hooks on install and stranded our own on
uninstall; these tests pin the fixed behavior.

Everything runs sandboxed via the ``fake_home`` fixture (HOME + XDG +
Windows env redirected at a tempdir), so no real user config is touched.
``transforms.node_available`` is forced True so the hooks merge always runs
regardless of whether the CI box has Node.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rf_agentskills import transforms as _x
from rf_agentskills.cli import main


FOREIGN_SETTINGS = {
    "model": "opus",
    "hooks": {
        "PostToolUse": [
            {"matcher": "OtherTool",
             "hooks": [{"type": "command", "command": "echo other-tool-hook"}]}
        ],
        "Notification": [
            {"matcher": "*",
             "hooks": [{"type": "command", "command": "echo my-own-hook"}]}
        ],
    },
}

FOREIGN_MCP = {"mcpServers": {"some-other-server": {"command": "node", "args": ["x.js"]}}}


@pytest.fixture(autouse=True)
def _force_node(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hooks merge is gated on Node being present; force it on for tests."""
    monkeypatch.setattr(_x, "node_available", lambda: True)


def _seed(home: Path) -> tuple[Path, Path]:
    claude = home / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    settings = claude / "settings.json"
    settings.write_text(json.dumps(FOREIGN_SETTINGS, indent=2), encoding="utf-8")
    mcp = home / ".mcp.json"
    mcp.write_text(json.dumps(FOREIGN_MCP, indent=2), encoding="utf-8")
    return settings, mcp


def _install(home: Path) -> None:
    assert main(["install", "--agent", "claude-code", "--scope", "user"]) == 0


def _uninstall(home: Path) -> None:
    assert main(["uninstall", "--agent", "claude-code", "--scope", "user"]) == 0


def _hooks(settings: Path) -> dict:
    return json.loads(settings.read_text(encoding="utf-8")).get("hooks", {})


# --- 2.2 / 2.3: hooks coexistence -----------------------------------------


def test_install_preserves_foreign_and_user_hooks(fake_home: Path) -> None:
    settings, _ = _seed(fake_home)
    _install(fake_home)
    h = _hooks(settings)
    # ours added
    assert "Write|Edit" in [g["matcher"] for g in h["PostToolUse"]]
    assert {"SessionStart", "Stop", "UserPromptSubmit"} <= set(h)
    # theirs untouched
    assert any(g["matcher"] == "OtherTool" for g in h["PostToolUse"])
    assert "Notification" in h


def test_uninstall_removes_only_our_hooks(fake_home: Path) -> None:
    settings, _ = _seed(fake_home)
    _install(fake_home)
    _uninstall(fake_home)
    data = json.loads(settings.read_text(encoding="utf-8"))
    h = data.get("hooks", {})
    # unrelated top-level key kept; foreign + user hooks kept
    assert data.get("model") == "opus"
    assert any(g["matcher"] == "OtherTool" for g in h.get("PostToolUse", []))
    assert "Notification" in h
    # ours gone, and no orphaned command referencing the deleted install dir
    assert "SessionStart" not in h and "Stop" not in h
    assert "UserPromptSubmit" not in h
    assert "rf-agentskills-files" not in settings.read_text(encoding="utf-8")


# --- 2.4: MCP coexistence --------------------------------------------------


def test_mcp_server_coexists_and_uninstalls_cleanly(fake_home: Path) -> None:
    _, mcp = _seed(fake_home)
    _install(fake_home)
    servers = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert "some-other-server" in servers and "rf-tools" in servers
    _uninstall(fake_home)
    servers = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert list(servers) == ["some-other-server"]


# --- 2.5: idempotent re-install -------------------------------------------


def test_reinstall_is_idempotent(fake_home: Path) -> None:
    settings, _ = _seed(fake_home)
    _install(fake_home)
    _install(fake_home)  # again
    h = _hooks(settings)
    # exactly one rf-agentskills PostToolUse group (no duplicates), foreign kept
    ours = [g for g in h["PostToolUse"] if g["matcher"] == "Write|Edit"]
    assert len(ours) == 1
    assert sum(1 for g in h["PostToolUse"] if g["matcher"] == "OtherTool") == 1


# --- 2.6: pruning vs retention --------------------------------------------


def test_shared_file_retained_but_emptied_block_pruned(fake_home: Path) -> None:
    """A file with foreign content survives; only our event keys are pruned."""
    settings, _ = _seed(fake_home)
    _install(fake_home)
    _uninstall(fake_home)
    assert settings.is_file()  # retained — model + foreign hooks remain
    h = _hooks(settings)
    # PostToolUse retained (foreign group remains); our solo events pruned
    assert "PostToolUse" in h
    assert "SessionStart" not in h


def test_file_deleted_when_only_ours(fake_home: Path) -> None:
    """With no foreign content, uninstall removes the now-empty settings file."""
    # Do NOT seed foreign hooks: settings.json is created solely by our merge.
    (fake_home / ".claude").mkdir(parents=True, exist_ok=True)
    settings = fake_home / ".claude" / "settings.json"
    _install(fake_home)
    assert settings.is_file()
    _uninstall(fake_home)
    assert not settings.exists()  # emptied to {} → removed


# --- 2.7: user-modified file is skipped, not deleted -----------------------


def test_user_modified_installed_file_is_skipped(fake_home: Path) -> None:
    _install(fake_home)
    skill_files = list((fake_home / ".claude" / "skills").rglob("SKILL.md"))
    assert skill_files, "expected installed skills"
    edited = skill_files[0]
    edited.write_text(edited.read_text(encoding="utf-8") + "\n<!-- user edit -->\n",
                      encoding="utf-8")
    _uninstall(fake_home)
    assert edited.is_file()  # user edit detected via hash → preserved
    assert "<!-- user edit -->" in edited.read_text(encoding="utf-8")
