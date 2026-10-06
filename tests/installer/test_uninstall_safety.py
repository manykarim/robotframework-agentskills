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


def _fake_legacy_mcp_install(home: Path, mcp: Path) -> Path:
    """Re-create what installers before content 2.0.0 left: rf-tools in .mcp.json,
    the staged server file and their manifest records."""
    from rf_agentskills import manifest as _m

    servers = json.loads(mcp.read_text(encoding="utf-8"))
    servers["mcpServers"]["rf-tools"] = {"command": "python3", "args": ["x/rf-tools-server.py"]}
    mcp.write_text(json.dumps(servers, indent=2), encoding="utf-8")
    server = home / ".claude" / "rf-agentskills-files" / "servers" / "rf-tools-server.py"
    server.parent.mkdir(parents=True, exist_ok=True)
    server.write_text("# old server\n", encoding="utf-8")
    manifest_path = _m.default_manifest_path()
    manifest = _m.Manifest.load(manifest_path)
    manifest.upsert(_m.Installation(
        agent="claude-code", scope="user", installed_at=_m.now_iso(), bundle_version="0.6.0",
        files=[_m.file_entry_for(server)],
        config_merges=[_m.ConfigMerge(path=str(mcp), added_keys=["rf-tools"],
                                      kind="json_nested", key_path=["mcpServers"])],
    ))
    manifest.save(manifest_path)
    return server


def test_reinstall_retires_legacy_rf_tools_and_keeps_foreign_server(fake_home: Path) -> None:
    _, mcp = _seed(fake_home)
    server = _fake_legacy_mcp_install(fake_home, mcp)
    _install(fake_home)
    servers = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert list(servers) == ["some-other-server"]
    assert not server.exists()
    _uninstall(fake_home)
    assert list(json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]) == ["some-other-server"]


def test_uninstall_of_legacy_record_removes_only_rf_tools(fake_home: Path) -> None:
    _, mcp = _seed(fake_home)
    server = _fake_legacy_mcp_install(fake_home, mcp)
    _uninstall(fake_home)
    assert list(json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]) == ["some-other-server"]
    assert not server.exists()


def test_install_never_writes_an_mcp_server(fake_home: Path) -> None:
    _, mcp = _seed(fake_home)
    _install(fake_home)
    assert json.loads(mcp.read_text(encoding="utf-8")) == FOREIGN_MCP


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


def test_retire_legacy_mcp_cleans_every_config_shape(tmp_path: Path) -> None:
    import yaml

    from rf_agentskills import manifest as _m
    from rf_agentskills.cli import _retire_legacy_mcp

    toml = tmp_path / "config.toml"
    _x.merge_toml_table(toml, ["mcp_servers", "rf-tools"], {"command": "python3"})
    _x.merge_toml_table(toml, ["mcp_servers", "mine"], {"command": "node"})
    goose = tmp_path / "config.yaml"
    goose.write_text(yaml.safe_dump({"extensions": {"rf-tools": {"cmd": "python3"}, "mine": {}}}))
    vscode = tmp_path / ".vscode" / "mcp.json"
    vscode.parent.mkdir()
    vscode.write_text(json.dumps({"servers": {"rf-tools": {}, "mine": {}}}))
    desktop = tmp_path / "claude_desktop_config.json"
    desktop.write_text(json.dumps({"mcpServers": {"rf-tools": {}, "mine": {}}, "theme": "dark"}))
    hooks = _m.ConfigMerge(path=str(tmp_path / "settings.json"), added_keys=["Stop"],
                           kind="json_hooks", key_path=["hooks"], marker="x")
    merges = [
        _m.ConfigMerge(path=str(toml), added_keys=["rf-tools"], kind="toml_table",
                       key_path=["mcp_servers", "rf-tools"]),
        _m.ConfigMerge(path=str(goose), added_keys=["rf-tools"], kind="yaml_block",
                       key_path=["extensions"]),
        _m.ConfigMerge(path=str(vscode), added_keys=["rf-tools"], kind="json_top"),
        _m.ConfigMerge(path=str(desktop), added_keys=["rf-tools"], kind="json_nested",
                       key_path=["mcpServers"]),
        hooks,
    ]
    kept, cleaned = _retire_legacy_mcp(merges)
    assert kept == [hooks] and len(cleaned) == 4
    assert "rf-tools" not in toml.read_text() and "mine" in toml.read_text()
    assert list(yaml.safe_load(goose.read_text())["extensions"]) == ["mine"]
    assert json.loads(vscode.read_text()) == {"servers": {"mine": {}}}
    assert json.loads(desktop.read_text()) == {"mcpServers": {"mine": {}}, "theme": "dark"}
