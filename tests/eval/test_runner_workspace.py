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
