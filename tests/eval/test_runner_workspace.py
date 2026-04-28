"""Tests for workspace provisioning and prompt shaping in the runner.

Does not execute any subprocess — we exercise the private helpers that
stage the fixture and build the prompt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.task import Task
from rf_skill_eval.errors import SkillRunnerError
from rf_skill_eval.infrastructure.runner.claude_code_runner import (
    ClaudeCodeRunner,
    _detect_workspace_violations,
    _snapshot_repo_root,
)


def _make_task(fixture: str | None, tmp_path: Path) -> Task:
    return Task(
        id="t-1",
        skill="keyword-builder",
        description="smoke",
        prompt="Write a keyword.",
        model="claude-haiku-4-5",
        max_turns=4,
        timeout_seconds=60,
        allowed_tools=("Read", "Write"),
        grader_checks=(),
        expected_files=(),
        tier="narrow",
        fixture=fixture,
    )


def test_provision_workspace_copies_fixture(tmp_path: Path) -> None:
    fixtures_root = tmp_path / "fixtures"
    (fixtures_root / "sut-x").mkdir(parents=True)
    (fixtures_root / "sut-x" / "hello.txt").write_text("hi")
    (fixtures_root / "sut-x" / "sub").mkdir()
    (fixtures_root / "sut-x" / "sub" / "nested.txt").write_text("yo")
    runner = ClaudeCodeRunner(fixtures_root=fixtures_root)
    artifacts = tmp_path / "run-1"
    artifacts.mkdir()
    task = _make_task("sut-x", tmp_path)

    workspace = runner._provision_workspace(task, artifacts)

    assert workspace == artifacts / "workspace"
    assert (workspace / "hello.txt").read_text() == "hi"
    assert (workspace / "sub" / "nested.txt").read_text() == "yo"


def test_provision_workspace_without_fixture(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path / "nowhere")
    artifacts = tmp_path / "run-2"
    artifacts.mkdir()
    task = _make_task(None, tmp_path)

    workspace = runner._provision_workspace(task, artifacts)

    assert workspace == artifacts


def test_provision_workspace_missing_fixture_raises(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path / "fixtures")
    artifacts = tmp_path / "run-3"
    artifacts.mkdir()
    task = _make_task("does-not-exist", tmp_path)

    with pytest.raises(SkillRunnerError, match="does-not-exist"):
        runner._provision_workspace(task, artifacts)


def test_build_cmd_adds_preamble_when_fixture_present(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    task = _make_task("sut-x", tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()

    cmd = runner._build_cmd(task, workspace)

    assert "-p" in cmd
    prompt = cmd[cmd.index("-p") + 1]
    assert "isolated workspace" in prompt
    assert str(workspace.resolve()) in prompt
    assert task.prompt in prompt


def test_build_cmd_no_preamble_when_no_fixture(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    task = _make_task(None, tmp_path)

    cmd = runner._build_cmd(task, None)

    prompt = cmd[cmd.index("-p") + 1]
    assert prompt == task.prompt
    assert "isolated workspace" not in prompt


def test_build_cmd_passes_bypass_permission_mode(tmp_path: Path) -> None:
    """Headless runs need bypassPermissions so plugin hooks aren't blocked
    by the interactive trust prompt that never gets answered."""
    runner = ClaudeCodeRunner(fixtures_root=tmp_path)
    task = _make_task(None, tmp_path)

    cmd = runner._build_cmd(task, None)

    assert "--permission-mode" in cmd
    assert cmd[cmd.index("--permission-mode") + 1] == "bypassPermissions"


def test_profile_smoke(tmp_path: Path) -> None:
    """Make sure Profile still works — regression guard."""
    profile = Profile(name="treatment", enabled_skills=("keyword-builder",),
                      claude_config_dir=tmp_path)
    assert profile.name == "treatment"


def test_snapshot_excludes_workspace_and_caches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("a")
    (repo / ".git").mkdir()
    (repo / ".git" / "HEAD").write_text("ref")
    (repo / ".venv").mkdir()
    (repo / ".venv" / "libs").write_text("x")
    workspace = repo / "eval" / "runs" / "batch" / "run-1" / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "hello.txt").write_text("hi")

    snap = _snapshot_repo_root(repo.resolve(), workspace.resolve())

    # Only src/a.py is included; workspace, .git, .venv, eval/runs are excluded.
    assert any(p.name == "a.py" for p in snap)
    assert not any("hello.txt" in str(p) for p in snap)
    assert not any(".git" in p.parts for p in snap)
    assert not any(".venv" in p.parts for p in snap)


def test_detect_violations_flags_new_files_outside_workspace(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "existing.py").write_text("a")
    workspace = repo / "workspace"
    workspace.mkdir()

    pre = _snapshot_repo_root(repo.resolve(), workspace.resolve())
    # Simulate agent creating a file outside workspace:
    (repo / "resources").mkdir()
    violation_path = (repo / "resources" / "leaked.resource").resolve()
    violation_path.write_text("oops")
    # And one legitimately inside workspace (should NOT be flagged):
    (workspace / "legit.txt").write_text("ok")

    violations = _detect_workspace_violations(repo.resolve(), workspace.resolve(), pre)

    assert violation_path in violations
    assert not any("legit.txt" in str(v) for v in violations)


def test_record_violations_cleans_up_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = ClaudeCodeRunner(repo_root=repo, cleanup_violations=True)
    artifacts = tmp_path / "run-a"
    artifacts.mkdir()
    bad = repo / "leaked.file"
    bad.write_text("leak")

    runner._record_violations(artifacts, [bad])

    assert not bad.exists()
    report = artifacts / "workspace_violations.json"
    assert report.is_file()
    import json as _json
    data = _json.loads(report.read_text())
    assert data["count"] == 1
    assert data["cleaned_up"] is True


def test_write_settings_emits_workspace_allow_list(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()

    runner._write_settings(config_dir, workspace)

    import json as _json
    settings = _json.loads((config_dir / "settings.json").read_text())
    assert "permissions" in settings
    allow = settings["permissions"]["allow"]
    deny = settings["permissions"]["deny"]
    assert any(f"Write({workspace.resolve()}" in rule for rule in allow)
    assert any("Write(/home/**)" in rule for rule in deny)


def _make_plugin(plugin_root: Path, skill_names: tuple[str, ...] = ("libdoc-search",)) -> None:
    """Create a minimal plugin layout with skills, agents, hooks, and an MCP server."""
    for skill_name in skill_names:
        skill_dir = plugin_root / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_name}\n"
            "description: test\n"
            "---\n\n"
            '```bash\npython3 "${CLAUDE_PLUGIN_ROOT}/scripts/foo.py"\n```\n',
            encoding="utf-8",
        )
    scripts_dir = plugin_root / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "foo.py").write_text("print('foo')", encoding="utf-8")
    (scripts_dir / "validate.sh").write_text(
        '#!/usr/bin/env bash\necho ok\n', encoding="utf-8"
    )

    agents_dir = plugin_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "rf-architect.md").write_text(
        "---\nname: rf-architect\ndescription: test\n---\nbody\n",
        encoding="utf-8",
    )

    hooks_dir = plugin_root / "hooks"
    hooks_dir.mkdir(parents=True)
    import json as _json
    (hooks_dir / "hooks.json").write_text(
        _json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Write|Edit",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    (plugin_root / ".mcp.json").write_text(
        _json.dumps(
            {
                "mcpServers": {
                    "rf-tools": {
                        "command": "python3",
                        "args": ["${CLAUDE_PLUGIN_ROOT}/servers/srv.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_stage_plugin_substitutes_plugin_root_token(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "rf-agentskills"
    _make_plugin(plugin_root)
    runner = ClaudeCodeRunner(plugin_root=plugin_root)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    plugin_dst = runner._stage_plugin(config_dir)

    assert plugin_dst is not None
    assert plugin_dst == config_dir / "rf-agentskills"
    plugin_root_abs = str(plugin_dst.resolve())

    # Token should be gone everywhere; absolute path appears in its place.
    skill_md = (plugin_dst / "skills" / "libdoc-search" / "SKILL.md").read_text()
    hooks_json = (plugin_dst / "hooks" / "hooks.json").read_text()
    mcp_json = (plugin_dst / ".mcp.json").read_text()
    for content in (skill_md, hooks_json, mcp_json):
        assert "${CLAUDE_PLUGIN_ROOT}" not in content
        assert plugin_root_abs in content


def test_provision_skills_copies_every_skill_to_both_locations(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "rf-agentskills"
    _make_plugin(plugin_root, skill_names=("libdoc-search", "keyword-builder"))
    runner = ClaudeCodeRunner(plugin_root=plugin_root)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()

    plugin_dst = runner._stage_plugin(config_dir)
    assert plugin_dst is not None
    runner._provision_skills(plugin_dst, config_dir, workspace)

    for name in ("libdoc-search", "keyword-builder"):
        assert (config_dir / "skills" / name / "SKILL.md").is_file()
        assert (workspace / ".claude" / "skills" / name / "SKILL.md").is_file()


def test_provision_agents_copies_to_both_locations(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "rf-agentskills"
    _make_plugin(plugin_root)
    runner = ClaudeCodeRunner(plugin_root=plugin_root)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()

    plugin_dst = runner._stage_plugin(config_dir)
    assert plugin_dst is not None
    runner._provision_agents(plugin_dst, config_dir, workspace)

    assert (config_dir / "agents" / "rf-architect.md").is_file()
    assert (workspace / ".claude" / "agents" / "rf-architect.md").is_file()


def test_extra_mcp_servers_returns_substituted_servers(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "rf-agentskills"
    _make_plugin(plugin_root)
    runner = ClaudeCodeRunner(plugin_root=plugin_root)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    plugin_dst = runner._stage_plugin(config_dir)
    assert plugin_dst is not None
    servers = runner._extra_mcp_servers(plugin_dst)

    assert servers is not None
    assert "rf-tools" in servers
    args = servers["rf-tools"]["args"]
    assert any(str(plugin_dst.resolve()) in a for a in args)
    assert all("${CLAUDE_PLUGIN_ROOT}" not in a for a in args)


def test_extract_hooks_returns_substituted_hooks(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins" / "rf-agentskills"
    _make_plugin(plugin_root)
    runner = ClaudeCodeRunner(plugin_root=plugin_root)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    plugin_dst = runner._stage_plugin(config_dir)
    assert plugin_dst is not None
    hooks = runner._extract_hooks(plugin_dst)

    assert hooks is not None
    assert "PostToolUse" in hooks
    cmd = hooks["PostToolUse"][0]["hooks"][0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" not in cmd
    assert str(plugin_dst.resolve()) in cmd


def test_write_settings_includes_hooks_when_provided(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    hooks = {"PostToolUse": [{"matcher": "Write", "hooks": []}]}

    runner._write_settings(config_dir, workspace, hooks=hooks)

    import json as _json
    user_settings = _json.loads((config_dir / "settings.json").read_text())
    assert "hooks" in user_settings
    assert user_settings["hooks"] == hooks

    # Project-scope copy is what Claude Code actually reads hooks from
    # in headless mode — covered by the same call, not a separate API.
    project_settings_path = workspace / ".claude" / "settings.json"
    assert project_settings_path.is_file()
    project_settings = _json.loads(project_settings_path.read_text())
    assert project_settings == {"hooks": hooks}


def test_write_settings_skips_project_file_when_no_hooks(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()

    runner._write_settings(config_dir, workspace, hooks=None)

    # Permissions still go to the user-scope file.
    assert (config_dir / "settings.json").is_file()
    # No hooks → no project-scope file (avoid creating .claude/ noise).
    assert not (workspace / ".claude" / "settings.json").exists()


def test_stage_plugin_returns_none_when_plugin_missing(tmp_path: Path) -> None:
    runner = ClaudeCodeRunner(plugin_root=tmp_path / "missing")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    assert runner._stage_plugin(config_dir) is None
