"""Tests for the ClaudeCodeAdapter — plan structure + end-to-end install/uninstall.

We never touch ``~/.claude/`` itself: every test passes a ``--prefix``
or uses the ``fake_home`` fixture so destinations are inside
``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rf_agentskills.adapters.claude_code import ClaudeCodeAdapter
from rf_agentskills.adapters._base import InstallOptions


# ---- plan() ---------------------------------------------------------------


def test_plan_writes_skills_agents_and_plugin_files(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    dst_paths = [str(t.dst) for t in plan.targets]
    # Skills tree
    assert any("/skills/libdoc-search/SKILL.md" in p for p in dst_paths)
    assert any("/agents/rf-test-architect.md" in p for p in dst_paths)
    # Co-located scripts/servers under rf-agentskills-files/
    assert any("/rf-agentskills-files/scripts/" in p for p in dst_paths)
    assert any("/rf-agentskills-files/servers/" in p for p in dst_paths)


def test_plan_substitutes_plugin_root_token(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    plugin_root_abs = str((install_prefix / "rf-agentskills-files").resolve())
    found_substituted_payload = False
    for t in plan.targets:
        if "${CLAUDE_PLUGIN_ROOT}" in t.payload.decode("utf-8", errors="replace"):
            pytest.fail(f"unsubstituted token in payload for {t.dst}")
        if plugin_root_abs.encode() in t.payload:
            found_substituted_payload = True
    assert found_substituted_payload, "expected the substituted abs path somewhere"


def test_plan_what_filter_excludes_skills(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(
        InstallOptions(prefix=install_prefix, what=frozenset({"agents"}))
    )
    paths = [str(t.dst) for t in plan.targets]
    assert any("/agents/" in p for p in paths)
    # Skills not in the plan
    assert not any(p.endswith("SKILL.md") and "/skills/" in p for p in paths)


def test_plan_marks_sh_files_executable(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    sh_targets = [t for t in plan.targets if t.dst.suffix == ".sh"]
    assert sh_targets, "no .sh files in the plan"
    assert all(t.executable for t in sh_targets)


def test_plan_includes_hooks_and_mcp_merges(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    descriptions = [m.description for m in plan.merges]
    assert any("hooks" in d for d in descriptions)
    assert any("MCP" in d.upper() for d in descriptions)


def test_plan_merge_kinds(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    by_kind = {m.kind: m for m in plan.merges}
    assert "json_top" in by_kind   # hooks block
    assert "json_nested" in by_kind  # MCP servers under mcpServers
    assert by_kind["json_nested"].key_path == ("mcpServers",)


# ---- detect() -------------------------------------------------------------


def test_detect_with_no_claude_dir(monkeypatch, fake_home: Path) -> None:
    """Adapter shouldn't claim detection when neither CLI nor ~/.claude exist."""
    monkeypatch.setenv("PATH", "")
    # fake_home empties HOME → no ~/.claude there
    assert ClaudeCodeAdapter().detect() is False


def test_detect_with_claude_dir(fake_home: Path) -> None:
    (fake_home / ".claude").mkdir()
    assert ClaudeCodeAdapter().detect() is True


# ---- post_install ---------------------------------------------------------


def test_post_install_returns_user_facing_notes() -> None:
    notes = ClaudeCodeAdapter().post_install(InstallOptions(prefix=Path("/tmp")))
    assert notes
    assert any("session" in n.lower() for n in notes)


# ---- end-to-end via the CLI -----------------------------------------------


def test_end_to_end_install_and_uninstall(install_prefix: Path, fake_home: Path) -> None:
    """Install then uninstall round-trip leaves the prefix empty."""
    from rf_agentskills.cli import main

    rc = main([
        "install",
        "--agent", "claude-code",
        "--prefix", str(install_prefix),
    ])
    assert rc == 0

    # Verify some real files landed
    assert (install_prefix / "skills" / "libdoc-search" / "SKILL.md").is_file()
    assert (install_prefix / "settings.json").is_file()
    settings = json.loads((install_prefix / "settings.json").read_text())
    assert "hooks" in settings
    assert (install_prefix / ".mcp.json").is_file()
    mcp = json.loads((install_prefix / ".mcp.json").read_text())
    assert "mcpServers" in mcp

    # Now uninstall
    rc = main(["uninstall", "--agent", "claude-code"])
    assert rc == 0

    # Prefix should be empty (or contain no rf-agentskills artifacts)
    leftovers = list(install_prefix.rglob("*"))
    files_left = [p for p in leftovers if p.is_file()]
    assert files_left == [], f"expected empty install dir, got {files_left}"


def test_install_dry_run_writes_nothing(install_prefix: Path, fake_home: Path) -> None:
    from rf_agentskills.cli import main

    rc = main([
        "install",
        "--agent", "claude-code",
        "--prefix", str(install_prefix),
        "--dry-run",
    ])
    assert rc == 0
    # Nothing was actually written
    files = [p for p in install_prefix.rglob("*") if p.is_file()]
    assert files == []


def test_install_warns_on_conflict_without_force(
    install_prefix: Path, fake_home: Path,
) -> None:
    """A pre-existing file at a destination path should not be silently overwritten."""
    from rf_agentskills.cli import main

    target = install_prefix / "skills" / "libdoc-search" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER OWNED CONTENT")

    rc = main([
        "install",
        "--agent", "claude-code",
        "--prefix", str(install_prefix),
    ])
    # Non-zero: conflicts produced warnings.
    assert rc != 0
    # User content preserved
    assert target.read_text() == "USER OWNED CONTENT"


def test_install_force_overwrites_conflict(install_prefix: Path, fake_home: Path) -> None:
    from rf_agentskills.cli import main

    target = install_prefix / "skills" / "libdoc-search" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("USER OWNED CONTENT")

    rc = main([
        "install",
        "--agent", "claude-code",
        "--prefix", str(install_prefix),
        "--force",
    ])
    assert rc == 0
    # Replaced
    assert target.read_text() != "USER OWNED CONTENT"
