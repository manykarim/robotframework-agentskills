"""Tests for the pure transforms (substitution, frontmatter, hooks, JSON merges).

No filesystem I/O beyond ``tmp_path`` for the merge tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from rf_agentskills import transforms as _x


# ---- substitute_plugin_root ------------------------------------------------


def test_substitute_plugin_root_replaces_token() -> None:
    result = _x.substitute_plugin_root(
        'cmd: ${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh',
        '/install/dir',
    )
    assert result == 'cmd: /install/dir/scripts/foo.sh'


def test_substitute_plugin_root_handles_empty_token() -> None:
    assert _x.substitute_plugin_root('no token here', '/whatever') == 'no token here'


def test_substitute_plugin_root_bytes() -> None:
    out = _x.substitute_plugin_root_bytes(
        b'cmd: ${CLAUDE_PLUGIN_ROOT}/x', '/install',
    )
    assert out == b'cmd: /install/x'


def test_is_substitution_candidate_by_suffix() -> None:
    assert _x.is_substitution_candidate(Path('a.sh'))
    assert _x.is_substitution_candidate(Path('a.md'))
    assert _x.is_substitution_candidate(Path('a.json'))
    assert _x.is_substitution_candidate(Path('a.ps1'))
    assert not _x.is_substitution_candidate(Path('a.png'))


# ---- frontmatter ----------------------------------------------------------


def test_parse_frontmatter_basic() -> None:
    doc = _x.parse_frontmatter("---\nname: foo\ndesc: bar\n---\nbody text\n")
    assert doc.frontmatter == {"name": "foo", "desc": "bar"}
    assert doc.body == "body text\n"


def test_parse_frontmatter_no_frontmatter() -> None:
    doc = _x.parse_frontmatter("just body\n")
    assert doc.frontmatter == {}
    assert doc.body == "just body\n"


def test_parse_frontmatter_invalid_yaml_returns_empty_fm() -> None:
    doc = _x.parse_frontmatter("---\n[oops\n---\nbody")
    assert doc.frontmatter == {}


def test_render_frontmatter_roundtrip() -> None:
    rendered = _x.render_frontmatter({"a": 1, "b": "two"}, "body\n")
    parsed = _x.parse_frontmatter(rendered)
    assert parsed.frontmatter == {"a": 1, "b": "two"}
    assert parsed.body == "body\n"


# ---- skill_md_to_cursor_mdc -----------------------------------------------


def test_skill_md_to_cursor_mdc_preserves_description() -> None:
    src = (
        '---\n'
        'name: libdoc-search\n'
        'description: Search RF library docs\n'
        '---\n'
        'Use this skill...\n'
    )
    mdc = _x.skill_md_to_cursor_mdc(src)
    parsed = _x.parse_frontmatter(mdc)
    assert parsed.frontmatter["description"] == "Search RF library docs"
    assert parsed.frontmatter["alwaysApply"] is False
    assert "**/*.robot" in parsed.frontmatter["globs"]
    # Source name preserved as comment in body
    assert "libdoc-search" in parsed.body


def test_skill_md_to_cursor_mdc_custom_globs() -> None:
    src = '---\nname: x\ndescription: y\n---\nbody'
    mdc = _x.skill_md_to_cursor_mdc(src, default_globs=["**/*.feature"])
    parsed = _x.parse_frontmatter(mdc)
    assert parsed.frontmatter["globs"] == ["**/*.feature"]


# ---- subagent_md_to_codex_toml --------------------------------------------


def test_subagent_md_to_codex_toml() -> None:
    src = (
        '---\n'
        'name: rf-test-architect\n'
        'description: Plan and design Robot Framework test suites\n'
        '---\n'
        '# Robot Framework Test Architect\n\nYou are a senior...\n'
    )
    toml_text = _x.subagent_md_to_codex_toml(src)
    assert 'name = "rf-test-architect"' in toml_text
    assert "description" in toml_text
    assert "developer_instructions" in toml_text
    # The full body lives inside developer_instructions
    assert "Robot Framework Test Architect" in toml_text


# ---- skill_md_to_opencode_command -----------------------------------------


def test_skill_md_to_opencode_command_keeps_description_only() -> None:
    src = '---\nname: libdoc-search\ndescription: blah\nextra: drop\n---\nbody'
    out = _x.skill_md_to_opencode_command(src)
    parsed = _x.parse_frontmatter(out)
    assert parsed.frontmatter == {"description": "blah"}


# ---- rewrite_hooks_for_cursor --------------------------------------------


def test_rewrite_hooks_for_cursor_event_names_and_mcp_namespace() -> None:
    hooks = {
        "PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "x"}]},
            {"matcher": "mcp__rf-mcp__execute_step", "hooks": []},
            {"matcher": "mcp__rf-mcp__.*", "hooks": []},
        ],
        "UserPromptSubmit": [{"matcher": "", "hooks": []}],
        "Stop": [{"matcher": "", "hooks": []}],
    }
    out = _x.rewrite_hooks_for_cursor(hooks)
    # Event names lowercased / mapped
    assert "postToolUse" in out
    assert "beforeSubmitPrompt" in out
    assert "stop" in out
    # MCP matchers namespaced
    matchers = [e["matcher"] for e in out["postToolUse"]]
    assert "Write|Edit" in matchers           # built-in alternation kept
    assert "MCP:rf-mcp:execute_step" in matchers
    assert "MCP:rf-mcp" in matchers           # mcp__rf-mcp__.* → MCP:rf-mcp


# ---- rewrite_hooks_for_windows -------------------------------------------


def test_rewrite_hooks_for_windows_swaps_sh_to_ps1() -> None:
    hooks = {
        "PostToolUse": [
            {"matcher": "Write|Edit", "hooks": [
                {"type": "command", "command": "/install/scripts/validate_robot.sh"}
            ]}
        ],
        "SessionStart": [
            {"matcher": "", "hooks": [
                {"type": "command", "command": "/install/scripts/check_rf_environment.sh"}
            ]}
        ],
    }
    out = _x.rewrite_hooks_for_windows(hooks)
    cmd = out["PostToolUse"][0]["hooks"][0]["command"]
    assert ".ps1" in cmd
    assert "powershell" in cmd
    assert "ExecutionPolicy Bypass" in cmd


def test_rewrite_hooks_for_windows_leaves_non_sh_alone() -> None:
    hooks = {"X": [{"matcher": "", "hooks": [
        {"type": "prompt", "prompt": "do thing"},
        {"type": "command", "command": "/x/some.py"},
    ]}]}
    out = _x.rewrite_hooks_for_windows(hooks)
    assert out["X"][0]["hooks"][0]["prompt"] == "do thing"
    assert out["X"][0]["hooks"][1]["command"] == "/x/some.py"


# ---- merge_json_file / remove_json_keys ----------------------------------


def test_merge_json_file_creates_new(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    added = _x.merge_json_file(p, "hooks", {"X": [1]})
    data = json.loads(p.read_text())
    assert data == {"hooks": {"X": [1]}}
    assert added == ["hooks"]


def test_merge_json_file_preserves_siblings(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"theme": "dark"}))
    added = _x.merge_json_file(p, "hooks", {"X": [1]})
    data = json.loads(p.read_text())
    assert data == {"theme": "dark", "hooks": {"X": [1]}}
    assert added == ["hooks"]


def test_remove_json_keys_drops_only_listed(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"theme": "dark", "hooks": {"X": [1]}}))
    _x.remove_json_keys(p, ["hooks"])
    data = json.loads(p.read_text())
    assert data == {"theme": "dark"}


def test_remove_json_keys_deletes_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"hooks": {"X": [1]}}))
    _x.remove_json_keys(p, ["hooks"])
    assert not p.exists()


# ---- merge_json_at_path / remove_json_keys_at_path -----------------------


def test_merge_json_at_path_nested(tmp_path: Path) -> None:
    p = tmp_path / "mcp.json"
    added = _x.merge_json_at_path(p, ["mcpServers"], {"rf-tools": {"command": "x"}})
    data = json.loads(p.read_text())
    assert data == {"mcpServers": {"rf-tools": {"command": "x"}}}
    assert added == ["rf-tools"]


def test_merge_json_at_path_existing_siblings(tmp_path: Path) -> None:
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({"mcpServers": {"rf-mcp": {"a": 1}}, "other": True}))
    added = _x.merge_json_at_path(p, ["mcpServers"], {"rf-tools": {"b": 2}})
    data = json.loads(p.read_text())
    assert data["mcpServers"] == {"rf-mcp": {"a": 1}, "rf-tools": {"b": 2}}
    assert data["other"] is True
    assert added == ["rf-tools"]


def test_remove_json_keys_at_path_removes_nested_only(tmp_path: Path) -> None:
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps(
        {"mcpServers": {"rf-mcp": {"a": 1}, "rf-tools": {"b": 2}}, "other": True}
    ))
    _x.remove_json_keys_at_path(p, ["mcpServers"], ["rf-tools"])
    data = json.loads(p.read_text())
    assert "rf-tools" not in data["mcpServers"]
    assert "rf-mcp" in data["mcpServers"]
    assert data["other"] is True


def test_remove_json_keys_at_path_drops_empty_parent(tmp_path: Path) -> None:
    """When the only nested key is removed, the parent is dropped too."""
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({"mcpServers": {"rf-tools": {"b": 2}}, "other": True}))
    _x.remove_json_keys_at_path(p, ["mcpServers"], ["rf-tools"])
    data = json.loads(p.read_text())
    assert data == {"other": True}


def test_remove_json_keys_at_path_deletes_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({"mcpServers": {"rf-tools": {"b": 2}}}))
    _x.remove_json_keys_at_path(p, ["mcpServers"], ["rf-tools"])
    assert not p.exists()


# ---- TOML merges ---------------------------------------------------------


def test_merge_toml_table_creates_nested(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    _x.merge_toml_table(p, ["mcp_servers", "rf_mcp"], {"command": "uv", "args": ["run"]})
    text = p.read_text()
    assert "[mcp_servers.rf_mcp]" in text
    assert 'command = "uv"' in text


def test_merge_toml_table_preserves_existing(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('model = "o3"\n[notice]\nhidden = true\n')
    _x.merge_toml_table(p, ["mcp_servers", "rf_mcp"], {"command": "x"})
    text = p.read_text()
    assert "model" in text and "notice" in text and "rf_mcp" in text


def test_remove_toml_table_drops_only_listed(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        'model = "o3"\n[mcp_servers.rf_mcp]\ncommand = "uv"\n'
        '[mcp_servers.other]\ncommand = "x"\n'
    )
    _x.remove_toml_table(p, ["mcp_servers", "rf_mcp"])
    text = p.read_text()
    assert "rf_mcp" not in text
    assert "other" in text
    assert "model" in text


# ---- YAML merges ---------------------------------------------------------


def test_merge_yaml_block_extends_existing(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("extensions:\n  github:\n    cmd: a\n")
    _x.merge_yaml_block(p, "extensions", {"rf-tools": {"cmd": "b"}})
    data = yaml.safe_load(p.read_text())
    assert data["extensions"]["github"]["cmd"] == "a"
    assert data["extensions"]["rf-tools"]["cmd"] == "b"


def test_remove_yaml_keys_under_parent(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text("extensions:\n  rf-tools:\n    cmd: x\n  other:\n    cmd: y\n")
    _x.remove_yaml_keys(p, ["rf-tools"], parent_key="extensions")
    data = yaml.safe_load(p.read_text())
    assert "rf-tools" not in data["extensions"]
    assert "other" in data["extensions"]
