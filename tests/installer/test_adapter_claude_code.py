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
    # Use ``.as_posix()`` so substring checks work the same on Windows
    # (where ``str(WindowsPath)`` would use ``\``).
    dst_paths = [t.dst.as_posix() for t in plan.targets]
    # Skills tree
    assert any("/skills/rf-libdoc/SKILL.md" in p for p in dst_paths)
    assert any("/agents/rf-test-architect.md" in p for p in dst_paths)
    # Co-located hook scripts (and the skill scripts the Stop hook runs)
    assert any("/rf-agentskills-files/scripts/" in p for p in dst_paths)
    assert any("/rf-agentskills-files/skills/rf-results/scripts/rf_results.py" in p
               for p in dst_paths)
    # The rf-tools MCP server is gone
    assert not any("/servers/" in p or p.endswith(".mcp.json") for p in dst_paths)


def test_plan_substitutes_plugin_root_token(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    # ``to_native_path_string`` renders Windows paths with forward
    # slashes, so we compare against the posix form regardless of OS.
    plugin_root_abs = (install_prefix / "rf-agentskills-files").resolve().as_posix()
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
    paths = [t.dst.as_posix() for t in plan.targets]
    assert any("/agents/" in p for p in paths)
    # Skills not in the plan
    assert not any(p.endswith("SKILL.md") and "/skills/" in p for p in paths)


def test_plan_writes_python_runtime_config(install_prefix: Path) -> None:
    """Replaces the old test_plan_marks_sh_files_executable now that
    hook scripts are Node-based — none of our bundled scripts use ``.sh``
    anymore. The new uniform expectation is that every plan that copies
    scripts also emits a ``python_runtime.json`` config pinning the
    install-time interpreter (so .mjs hooks find the right Python)."""
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    runtime = [
        t for t in plan.targets
        if t.dst.name == "python_runtime.json"
        and t.dst.parent.name == "scripts"
    ]
    assert runtime, "expected python_runtime.json target in scripts/"
    cfg = json.loads(runtime[0].payload.decode("utf-8"))
    assert "interpreter" in cfg
    assert cfg["fallbacks"] == ["python3", "python"]


def test_plan_merges_hooks_only(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    descriptions = [m.description for m in plan.merges]
    assert any("hooks" in d for d in descriptions)
    assert not any("MCP" in d.upper() for d in descriptions)


def test_plan_merge_kinds(install_prefix: Path) -> None:
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    by_kind = {m.kind: m for m in plan.merges}
    assert "json_hooks" in by_kind   # hooks block (granular, ownership-aware)
    assert by_kind["json_hooks"].key_path == ("hooks",)
    assert by_kind["json_hooks"].marker  # install-dir ownership marker recorded
    assert set(by_kind) == {"json_hooks"}  # no MCP server merge any more


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
    assert (install_prefix / "skills" / "rf-libdoc" / "SKILL.md").is_file()
    assert (install_prefix / "settings.json").is_file()
    settings = json.loads((install_prefix / "settings.json").read_text())
    assert "hooks" in settings
    assert not (install_prefix / ".mcp.json").exists()

    # Now uninstall — manifest is CWD/project-scoped (fake_home chdir), so
    # the absolute paths recorded at install are removed from the prefix.
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

    target = install_prefix / "skills" / "rf-libdoc" / "SKILL.md"
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

    target = install_prefix / "skills" / "rf-libdoc" / "SKILL.md"
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


# ---- Windows-platform regression test -------------------------------------


def test_plan_succeeds_with_windows_style_substitution_target(
    install_prefix: Path, monkeypatch
) -> None:
    """Regression for docs/issues/win-powershell-install-fix-proposal.md.

    The Claude Code adapter's ``_hooks_merge_op`` and ``_mcp_merge_op``
    both call ``json.loads(substituted_text)`` during plan-build. On
    Windows, ``to_native_path_string`` used to return a backslash-
    separator path; substituted into the JSON template that produced
    ``Invalid \\escape`` and crashed install entirely.

    We mock the helper to return a Windows-style **forward-slash**
    path (what the post-fix function returns on Windows) and verify
    plan-build completes. If anyone reverts the fix and the helper
    starts returning backslashes again, this test reproduces the
    crash.
    """
    from rf_agentskills import transforms as _x

    monkeypatch.setattr(
        _x, "to_native_path_string",
        lambda p: "C:/Users/x/.claude/rf-agentskills-files",
    )
    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))

    # plan() called json.loads internally — would have crashed pre-fix.
    assert plan.merges, "expected at least the hooks + mcp merges"
    # The substituted Windows path should appear in payloads…
    win_marker = b"C:/Users/x/.claude/rf-agentskills-files"
    assert any(win_marker in t.payload for t in plan.targets), (
        "expected the substituted Windows path to land in at least "
        "one staged target"
    )
    # …and no payload contains the unescaped-backslash form.
    bad_marker = b"C:\\Users\\x\\.claude\\rf-agentskills-files"
    assert all(bad_marker not in t.payload for t in plan.targets)


def test_copilot_plan_with_windows_style_substitution_target(
    install_prefix: Path, monkeypatch
) -> None:
    """Same regression as the Claude Code test; Copilot inherits the
    JSON merge paths from ClaudeCodeAdapter."""
    from rf_agentskills import transforms as _x
    from rf_agentskills.adapters.copilot import CopilotAdapter

    monkeypatch.setattr(
        _x, "to_native_path_string",
        lambda p: "C:/Users/x/.claude/rf-agentskills-files",
    )
    plan = CopilotAdapter().plan(InstallOptions(prefix=install_prefix))
    assert plan.merges
    assert all(
        b"C:\\Users\\x\\.claude\\rf-agentskills-files" not in t.payload
        for t in plan.targets
    )


# ---- Hook-command file-existence regression test --------------------------


def test_every_hook_command_resolves_to_an_existing_file(
    install_prefix: Path, fake_home: Path, tmp_path: Path
) -> None:
    """Every script invoked by an emitted hook command must actually exist
    in the on-disk install tree.

    This is the regression test for v0.4.1's broken ``.sh→.ps1`` rewrite:
    that release shipped hook commands referencing ``.ps1`` files that
    were never bundled, so every Claude Code SessionStart on Windows
    logged an error. A test of this shape — *do the things our hooks
    refer to actually exist?* — would have caught it pre-release. The
    test runs on every CI cell (POSIX + Windows).
    """
    import re
    from rf_agentskills.cli import main

    rc = main([
        "install", "--agent", "claude-code",
        "--prefix", str(install_prefix),
    ])
    assert rc == 0, "claude-code install must succeed"

    settings = install_prefix / "settings.json"
    assert settings.is_file(), "expected settings.json was written"
    blob = json.loads(settings.read_text(encoding="utf-8"))
    assert "hooks" in blob, "expected a hooks block in settings.json"

    # Collect every "command" field from the hooks block (any depth).
    commands: list[str] = []
    def walk(v: object) -> None:
        if isinstance(v, dict):
            if v.get("type") == "command" and isinstance(v.get("command"), str):
                commands.append(v["command"])
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(blob["hooks"])
    assert commands, "hooks block contained no commands"

    # Each `node "<…>.mjs"` (or python / bash etc. in future) names a
    # script file as its last positional argument. Extract that path
    # and assert it exists on disk.
    for cmd in commands:
        m = re.search(r'"([^"]+\.(?:mjs|cjs|js|py|sh|ps1))"', cmd)
        assert m, f"hook command did not name a script file: {cmd!r}"
        script_path = Path(m.group(1))
        assert script_path.is_file(), (
            f"hook command references missing file: {script_path}\n"
            f"  full command: {cmd!r}"
        )


def test_install_skips_hooks_with_note_when_node_absent(
    install_prefix: Path, fake_home: Path, monkeypatch
) -> None:
    """When ``node`` isn't on PATH, the install should still succeed,
    but skip writing the hooks block (which would otherwise reference
    an unrunnable ``node "<…>.mjs"`` command) and surface a clear note."""
    from rf_agentskills import transforms as _x

    monkeypatch.setattr(_x, "node_available", lambda: False)

    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    # The settings.json hooks merge (description starts with "merge hooks
    # block …") must be absent. Other merges (e.g. .mcp.json) can stay —
    # the Node gap only affects hooks.
    hook_merges = [
        m for m in plan.merges if m.description.startswith("merge hooks block")
    ]
    assert hook_merges == [], (
        f"expected no hooks merge when node is absent, got: {hook_merges}"
    )
    # Note explaining the gap, mentioning Node.
    flat = " ".join(plan.notes).lower()
    assert "node" in flat
    assert ("hooks" in flat or "hook" in flat)


def test_install_writes_hooks_normally_when_node_present(
    install_prefix: Path, fake_home: Path, monkeypatch
) -> None:
    """Smoke-test the positive branch of the Node probe."""
    from rf_agentskills import transforms as _x

    monkeypatch.setattr(_x, "node_available", lambda: True)

    plan = ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix))
    hook_merges = [
        m for m in plan.merges if m.description.startswith("merge hooks block")
    ]
    assert hook_merges, "expected hooks merge when node is present"


def test_claude_code_keeps_skill_dir_variable(install_prefix: Path, fake_home: Path) -> None:
    """Claude Code substitutes ${CLAUDE_SKILL_DIR} itself: installed SKILL.md keeps it,
    and the script sits in the installed skill's own scripts/ dir."""
    from rf_agentskills.adapters import by_name
    from rf_agentskills.cli import main as cli_main

    assert by_name("claude-code")().expands_skill_dir is True
    assert cli_main(["install", "--agent", "claude-code", "--prefix", str(install_prefix)]) == 0
    md = install_prefix / "skills" / "rf-libdoc" / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    assert 'uv run python "${CLAUDE_SKILL_DIR}/scripts/rf_libdoc.py"' in text
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    assert (md.parent / "scripts" / "rf_libdoc.py").is_file()


def test_project_install_ships_language_skill_in_manifest(fake_home: Path) -> None:
    """add-rf-language-skill 6.3: .claude/skills/rf-language is installed with its
    script and recorded in the project manifest."""
    from rf_agentskills.cli import main as cli_main

    assert cli_main(["install", "--agent", "claude-code"]) == 0
    md = fake_home / ".claude" / "skills" / "rf-language" / "SKILL.md"
    assert md.is_file()
    assert "\nname: rf-language\n" in md.read_text(encoding="utf-8")
    text = md.read_text(encoding="utf-8")
    assert 'uv run python "${CLAUDE_SKILL_DIR}/scripts/rf_conventions.py"' in text
    assert (md.parent / "scripts" / "rf_conventions.py").is_file()
    manifest = (fake_home / ".rf-agentskills" / "installed.json").read_text(encoding="utf-8")
    assert "skills/rf-language/SKILL.md" in manifest.replace("\\\\", "/")
    assert "skills/rf-language/scripts/rf_conventions.py" in manifest.replace("\\\\", "/")


def test_project_install_ships_python_library_skill(install_prefix: Path, fake_home: Path) -> None:
    """add-rf-python-library-skill 7.5: the plan lists skills/rf-python-library, and the
    install ships its checker script and records it in the manifest."""
    from rf_agentskills.cli import main as cli_main

    dst_paths = [t.dst.as_posix() for t in ClaudeCodeAdapter().plan(InstallOptions(prefix=install_prefix)).targets]
    assert any(p.endswith("/skills/rf-python-library/SKILL.md") for p in dst_paths)
    assert any(p.endswith("/skills/rf-python-library/scripts/check_library.py") for p in dst_paths)
    assert cli_main(["install", "--agent", "claude-code"]) == 0
    md = fake_home / ".claude" / "skills" / "rf-python-library" / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    assert "\nname: rf-python-library\n" in text
    assert 'uv run python "${CLAUDE_SKILL_DIR}/scripts/check_library.py"' in text
    assert (md.parent / "scripts" / "check_library.py").is_file()
    assert (md.parent / "assets" / "examples" / "ExampleLibrary.py").is_file()
    manifest = (fake_home / ".rf-agentskills" / "installed.json").read_text(encoding="utf-8")
    assert "skills/rf-python-library/scripts/check_library.py" in manifest.replace("\\\\", "/")
