"""Tests for the secondary adapters: Codex, Cursor, Goose, OpenCode, Claude Desktop.

Parametrised round-trip tests cover universal behavior (install → list →
uninstall → empty) across all five. Individual targeted tests
exercise per-adapter transforms (subagent.md→TOML for Codex,
SKILL.md→MDC for Cursor, JSON→YAML extension shape for Goose, etc.).

The Claude Code + Copilot adapters have their own dedicated test file
(test_adapter_claude_code.py); this file covers the rest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from rf_agentskills import transforms as _x
from rf_agentskills.adapters import by_name
from rf_agentskills.adapters._base import InstallOptions
from rf_agentskills.cli import main


# ---- universal round-trip parametrised over every secondary adapter -------


SECONDARY_AGENTS = ["codex", "cursor", "goose", "opencode", "claude-desktop"]


@pytest.mark.parametrize("agent", SECONDARY_AGENTS)
def test_plan_returns_non_empty_for_each_adapter(
    install_prefix: Path, agent: str
) -> None:
    """Every adapter should produce *some* targets or merges by default."""
    cls = by_name(agent)
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    assert plan.targets or plan.merges, (
        f"adapter {agent!r} produced an empty plan"
    )


@pytest.mark.parametrize("agent", SECONDARY_AGENTS)
def test_dry_run_writes_no_files(
    install_prefix: Path, fake_home: Path, agent: str
) -> None:
    rc = main([
        "install", "--agent", agent,
        "--prefix", str(install_prefix), "--dry-run",
    ])
    assert rc == 0
    files = [p for p in install_prefix.rglob("*") if p.is_file()]
    assert files == [], f"{agent} dry-run wrote files: {files}"


@pytest.mark.parametrize("agent", SECONDARY_AGENTS)
def test_install_then_uninstall_clears_prefix(
    install_prefix: Path, fake_home: Path, agent: str
) -> None:
    rc = main(["install", "--agent", agent, "--prefix", str(install_prefix)])
    assert rc == 0

    # Something should have landed.
    files_after_install = [p for p in install_prefix.rglob("*") if p.is_file()]
    assert files_after_install, f"{agent} install left no files"

    # Uninstall reverses cleanly.
    rc = main(["uninstall", "--agent", agent])
    assert rc == 0
    files_left = [p for p in install_prefix.rglob("*") if p.is_file()]
    assert files_left == [], (
        f"{agent} uninstall left orphaned files: {files_left}"
    )


@pytest.mark.parametrize("agent", SECONDARY_AGENTS)
def test_substitution_token_does_not_leak_into_payloads(
    install_prefix: Path, agent: str
) -> None:
    cls = by_name(agent)
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    for tgt in plan.targets:
        # SKILL bodies and shell scripts get substituted at install time.
        # The literal token must not survive past plan() — adapters that
        # leave it in place will break at runtime.
        assert b"${CLAUDE_PLUGIN_ROOT}" not in tgt.payload, (
            f"{agent} left unsubstituted token in {tgt.dst}"
        )


# ---- Codex-specific ----------------------------------------------------


def test_codex_subagents_become_toml(install_prefix: Path) -> None:
    cls = by_name("codex")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    toml_targets = [t for t in plan.targets if str(t.dst).endswith(".toml")]
    assert toml_targets, "expected at least one .toml subagent target"
    for t in toml_targets:
        body = t.payload.decode("utf-8")
        assert "name =" in body
        assert "developer_instructions =" in body
        assert t.transform_name == "subagent_md_to_codex_toml"


def test_codex_mcp_uses_toml_table_kind(install_prefix: Path) -> None:
    cls = by_name("codex")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    toml_merges = [m for m in plan.merges if m.kind == "toml_table"]
    assert toml_merges, "expected a toml_table MCP merge"
    assert any(m.key_path[0] == "mcp_servers" for m in toml_merges)


def test_codex_post_install_mentions_codex_hooks_flag() -> None:
    cls = by_name("codex")
    assert cls is not None
    notes = cls().post_install(InstallOptions())
    assert any("codex_hooks" in n for n in notes), (
        "Codex must remind user to flip the experimental flag manually"
    )


def test_codex_e2e_writes_valid_toml_files(
    install_prefix: Path, fake_home: Path
) -> None:
    import tomli_w  # noqa: F401  (just to confirm dep present)
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    rc = main(["install", "--agent", "codex", "--prefix", str(install_prefix)])
    assert rc == 0

    # config.toml should parse and contain a [mcp_servers.<name>] table
    cfg = install_prefix / "config.toml"
    assert cfg.is_file()
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert "mcp_servers" in data
    assert data["mcp_servers"]  # non-empty

    # All written .toml subagents are valid TOML
    for toml_file in (install_prefix / "agents").glob("*.toml"):
        agent = tomllib.loads(toml_file.read_text(encoding="utf-8"))
        assert "name" in agent
        assert "developer_instructions" in agent


# ---- Cursor-specific ---------------------------------------------------


def test_cursor_skills_install_natively_to_skills_dir(
    install_prefix: Path,
) -> None:
    """Cursor 2.4+ reads SKILL.md natively — verbatim copy, no MDC transform."""
    cls = by_name("cursor")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    skill_targets = [t for t in plan.targets
                     if str(t.dst).endswith("SKILL.md")
                     and "/skills/" in str(t.dst)]
    assert skill_targets, "expected SKILL.md targets under <root>/skills/<name>/"
    # The frontmatter should be unchanged from the source SKILL.md
    for t in skill_targets:
        doc = _x.parse_frontmatter(t.payload.decode("utf-8"))
        assert "name" in doc.frontmatter
        assert "description" in doc.frontmatter
    # No MDC files anywhere (the transform was removed)
    mdc_targets = [t for t in plan.targets if str(t.dst).endswith(".mdc")]
    assert mdc_targets == []


def test_cursor_subagents_copy_natively(install_prefix: Path) -> None:
    """Cursor 2.4 added native subagent support — same .md format as Claude."""
    cls = by_name("cursor")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    agent_targets = [t for t in plan.targets
                     if str(t.dst).endswith(".md") and "/agents/" in str(t.dst)]
    assert agent_targets, "expected agents/<name>.md targets"


def test_cursor_hooks_use_namespaced_matchers(
    install_prefix: Path, fake_home: Path
) -> None:
    """Cursor hooks need ``MCP:rf-mcp`` not ``mcp__rf-mcp__.*``."""
    rc = main(["install", "--agent", "cursor", "--prefix", str(install_prefix)])
    assert rc == 0
    hooks_path = install_prefix / "hooks.json"
    if not hooks_path.is_file():
        pytest.skip("cursor adapter doesn't emit hooks.json (acceptable)")
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    flat = json.dumps(hooks)
    # No leftover Claude-style mcp__rf-mcp__ matchers.
    assert "mcp__rf-mcp__" not in flat, (
        "Cursor hooks should namespace MCP matchers as MCP:rf-mcp"
    )


# ---- Goose-specific ----------------------------------------------------


def test_goose_writes_goosehints_persona(install_prefix: Path) -> None:
    cls = by_name("goose")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    hints = [t for t in plan.targets if t.dst.name == ".goosehints"]
    assert len(hints) == 1
    body = hints[0].payload.decode("utf-8")
    assert "rf-test-architect" in body
    assert "Skills:" in body or "skills:" in body.lower()


def test_goose_mcp_yaml_merge_kind(install_prefix: Path) -> None:
    cls = by_name("goose")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    yaml_merges = [m for m in plan.merges if m.kind == "yaml_block"]
    assert yaml_merges, "expected a yaml_block MCP merge"
    assert yaml_merges[0].key_path == ("extensions",)


def test_goose_skills_install_to_agents_dir(install_prefix: Path) -> None:
    """Goose v1.25+ reads skills from ``~/.agents/skills/`` (Summon ext)."""
    cls = by_name("goose")
    assert cls is not None
    plan = cls().plan(InstallOptions(
        prefix=install_prefix, what=frozenset({"skills"})
    ))
    skill_targets = [t for t in plan.targets
                     if "/agents/skills/" in str(t.dst) and t.dst.name == "SKILL.md"]
    assert skill_targets, (
        "expected SKILL.md targets under <prefix>/agents/skills/<name>/"
    )


def test_goose_subagents_still_fold_into_goosehints(install_prefix: Path) -> None:
    """Goose has no subagent primitive — only skills are first-class."""
    cls = by_name("goose")
    assert cls is not None
    plan = cls().plan(InstallOptions(
        prefix=install_prefix, what=frozenset({"agents"})
    ))
    # No <prefix>/agents/<name>.md targets (those would be Claude Code shape)
    agent_md_targets = [t for t in plan.targets
                        if str(t.dst).endswith(".md")
                        and "/agents/" in str(t.dst)
                        and "/skills/" not in str(t.dst)]
    assert agent_md_targets == []
    # Goosehints should be written instead
    hints = [t for t in plan.targets if t.dst.name == ".goosehints"]
    assert len(hints) == 1
    # And there's a note explaining the fold
    assert any("subagent" in n.lower() for n in plan.notes)


def test_goose_e2e_yaml_round_trip(
    install_prefix: Path, fake_home: Path
) -> None:
    rc = main(["install", "--agent", "goose", "--prefix", str(install_prefix)])
    assert rc == 0
    cfg = install_prefix / "config.yaml"
    assert cfg.is_file()
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert "extensions" in data
    assert data["extensions"]  # non-empty

    rc = main(["uninstall", "--agent", "goose"])
    assert rc == 0
    # config.yaml should be gone (the only key we added was extensions
    # and we cleaned it).
    assert not cfg.exists() or yaml.safe_load(cfg.read_text()) == {}


# ---- OpenCode-specific -------------------------------------------------


def test_opencode_subagents_copied_directly(install_prefix: Path) -> None:
    cls = by_name("opencode")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    agent_targets = [t for t in plan.targets if "/agents/" in str(t.dst)]
    assert agent_targets, "expected agents/<name>.md targets"
    # Direct copy: transform name reflects only substitution, not a reformat
    for t in agent_targets:
        assert t.transform_name == "plugin_root_substitution"


def test_opencode_skills_install_natively_to_skills_dir(
    install_prefix: Path,
) -> None:
    """OpenCode reads SKILL.md natively (per opencode.ai/docs/skills/, May 2026)."""
    cls = by_name("opencode")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    skill_targets = [t for t in plan.targets
                     if str(t.dst).endswith("SKILL.md")
                     and "/skills/" in str(t.dst)]
    assert skill_targets, "expected SKILL.md targets under <root>/skills/<name>/"
    for t in skill_targets:
        doc = _x.parse_frontmatter(t.payload.decode("utf-8"))
        # Native frontmatter preserved (name + description required by docs)
        assert "name" in doc.frontmatter
        assert "description" in doc.frontmatter
    # No commands/<name>.md transforms anymore
    cmd_targets = [t for t in plan.targets if "/commands/" in str(t.dst)]
    assert cmd_targets == []


def test_opencode_mcp_translation_to_command_array(
    install_prefix: Path, fake_home: Path
) -> None:
    rc = main(["install", "--agent", "opencode", "--prefix", str(install_prefix)])
    assert rc == 0
    cfg = install_prefix / "opencode.json"
    assert cfg.is_file()
    data = json.loads(cfg.read_text())
    assert "mcp" in data
    for name, spec in data["mcp"].items():
        # OpenCode shape: {type: "local", command: [<cmd>, *args]}
        assert spec["type"] == "local"
        assert isinstance(spec["command"], list), (
            f"server {name!r} command should be a list, got {spec['command']!r}"
        )


def test_opencode_post_install_mentions_hooks_skipped() -> None:
    cls = by_name("opencode")
    assert cls is not None
    notes = cls().post_install(InstallOptions())
    assert any("hook" in n.lower() for n in notes)


# ---- Claude Desktop-specific -------------------------------------------


def test_claude_desktop_only_emits_mcp_and_scripts(install_prefix: Path) -> None:
    cls = by_name("claude-desktop")
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))
    # No skills/agents/hooks files
    targets_paths = [str(t.dst) for t in plan.targets]
    assert not any("/skills/" in p for p in targets_paths)
    assert not any("/agents/" in p and p.endswith(".md") for p in targets_paths)
    # Has co-located scripts/servers (for MCP path resolution)
    assert any("rf-agentskills-files" in p for p in targets_paths)
    # Has the MCP merge
    assert any("mcpServers" in str(m.key_path) or m.kind == "json_nested"
               for m in plan.merges)


@pytest.mark.parametrize("category", ["skills", "agents", "hooks"])
def test_claude_desktop_skips_with_note_for_unsupported_categories(
    install_prefix: Path, category: str
) -> None:
    cls = by_name("claude-desktop")
    assert cls is not None
    plan = cls().plan(InstallOptions(
        prefix=install_prefix, what=frozenset({category})
    ))
    # The note should reference the missing native support
    flat = " ".join(plan.notes).lower()
    assert "no native" in flat or "not installed" in flat, (
        f"category={category} should produce a skip note, got {plan.notes}"
    )


def test_claude_desktop_config_path_per_os(monkeypatch: pytest.MonkeyPatch) -> None:
    from rf_agentskills.adapters.claude_desktop import ClaudeDesktopAdapter
    adapter = ClaudeDesktopAdapter()

    monkeypatch.setattr(sys, "platform", "darwin")
    p = adapter._config_path()
    assert "Library/Application Support/Claude" in str(p)

    monkeypatch.setattr(sys, "platform", "linux")
    p = adapter._config_path()
    assert ".config/Claude" in str(p)


def test_claude_desktop_config_path_windows(monkeypatch: pytest.MonkeyPatch,
                                            tmp_path: Path) -> None:
    from rf_agentskills.adapters.claude_desktop import ClaudeDesktopAdapter
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    p = ClaudeDesktopAdapter()._config_path()
    assert str(tmp_path / "Roaming" / "Claude" / "claude_desktop_config.json") == str(p)


def test_claude_desktop_e2e_round_trip(
    install_prefix: Path, fake_home: Path
) -> None:
    rc = main(["install", "--agent", "claude-desktop", "--prefix", str(install_prefix)])
    assert rc == 0
    cfg = install_prefix / "claude_desktop_config.json"
    assert cfg.is_file()
    data = json.loads(cfg.read_text())
    assert "mcpServers" in data
    assert data["mcpServers"]

    rc = main(["uninstall", "--agent", "claude-desktop"])
    assert rc == 0
    files_left = [p for p in install_prefix.rglob("*") if p.is_file()]
    assert files_left == []


# ---- Windows-platform regression tests ------------------------------------


@pytest.mark.parametrize("agent", SECONDARY_AGENTS)
def test_plan_succeeds_with_windows_style_substitution_target(
    agent: str, install_prefix: Path, monkeypatch
) -> None:
    """Regression for docs/issues/win-powershell-install-fix-proposal.md.

    Every adapter calls ``to_native_path_string`` to compute the
    substitution target and then runs the substituted text through a
    parser (``json.loads`` for JSON adapters, ``tomllib.loads`` for
    Codex, ``yaml.safe_load`` for Goose). With backslash-separator
    Windows paths this used to crash with ``Invalid \\escape``
    (JSON), or fail TOML/YAML scalar parsing similarly.

    We mock the helper to return a Windows-style **forward-slash**
    path (what the post-fix function returns on Windows) and assert
    that plan-build completes and no payload retains an
    unescaped-backslash form of the same path.
    """
    from rf_agentskills import transforms as _x

    win_path = "C:/Users/x/.config/rf-agentskills-files"
    monkeypatch.setattr(_x, "to_native_path_string", lambda p: win_path)

    cls = by_name(agent)
    assert cls is not None
    plan = cls().plan(InstallOptions(prefix=install_prefix))

    # Each adapter produces *something* — targets, merges, or both.
    assert plan.targets or plan.merges, (
        f"adapter {agent!r} produced an empty plan under Windows-mock"
    )

    # No payload should contain the literal backslash-separator form
    # of the substituted path — that would mean someone bypassed
    # to_native_path_string or reverted the fix.
    bad_marker = b"C:\\Users\\x\\.config\\rf-agentskills-files"
    for tgt in plan.targets:
        assert bad_marker not in tgt.payload, (
            f"{agent}: payload for {tgt.dst} contains the pre-fix "
            f"backslash form of the substituted path"
        )
