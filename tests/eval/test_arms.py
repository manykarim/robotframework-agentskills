"""Arm provisioning through the real ClaudeCodeRunner (tasks 3.1-3.3, 5.3 wiring).

A fake ``claude`` executable (a Python script) stands in for the CLI: it
records its argv/cwd/env and prints a canned stream-json transcript, so no
model is ever called.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.task import Task
from rf_skill_eval.infrastructure.runner.claude_code_runner import (
    ClaudeCodeRunner,
    baseline_isolation_problems,
)

_REPO = Path(__file__).resolve().parents[2]
_PLUGIN = _REPO / "plugins" / "rf-agentskills"

_FAKE_CLAUDE = """#!{python}
import json, os, sys
record = {{"argv": sys.argv[1:], "cwd": os.getcwd(),
          "config_dir": os.environ.get("CLAUDE_CONFIG_DIR")}}
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as fh:
    fh.write(json.dumps(record) + "\\n")
skill = os.environ.get("FAKE_CLAUDE_SKILL")
if skill:
    print(json.dumps({{"type": "assistant", "message": {{"role": "assistant", "content": [
        {{"type": "tool_use", "id": "t1", "name": "Skill", "input": {{"skill": skill}}}}]}}}}))
    print(json.dumps({{"type": "user", "message": {{"role": "user", "content": [
        {{"type": "tool_result", "tool_use_id": "t1", "content": "Launching skill"}}]}}}}))
print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "num_turns": 1,
                  "duration_ms": 10, "total_cost_usd": 0.002,
                  "usage": {{"input_tokens": 3, "output_tokens": 4}}}}))
"""


@pytest.fixture
def fake_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    exe = tmp_path / "bin" / "claude"
    exe.parent.mkdir()
    exe.write_text(_FAKE_CLAUDE.format(python=sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "claude-calls.jsonl"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake-token")
    monkeypatch.delenv("FAKE_CLAUDE_SKILL", raising=False)
    return exe


def _calls(tmp_path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (tmp_path / "claude-calls.jsonl").read_text().splitlines()]


def _runner(tmp_path: Path, exe: Path, fixtures: Path | None = None) -> ClaudeCodeRunner:
    return ClaudeCodeRunner(
        claude_binary=str(exe),
        fixtures_root=fixtures or (_REPO / "eval" / "fixtures"),
        repo_root=tmp_path / "fake-repo",
        plugin_root=_PLUGIN,
    )


def _task(**kw: object) -> Task:
    data: dict[str, object] = {
        "id": "narrow-arm-01",
        "skill": "rf-browser",
        "prompt": "do it",
        "fixture": "sut-minimal",
        "allowed_tools": ["Read", "Write", "mcp__rf-mcp__*"],
        "mcp_servers": ["rf-mcp"],
        "max_turns": 5,
        "timeout_seconds": 60,
    }
    data.update(kw)
    return Task.model_validate(data)


def _mcp(config_dir: Path) -> dict[str, object]:
    return json.loads((config_dir / ".mcp.json").read_text())["mcpServers"]


def test_baseline_arm_provisions_no_plugin_parts(tmp_path: Path, fake_claude: Path) -> None:
    (tmp_path / "fake-repo").mkdir()
    out = tmp_path / "runs"
    run = _runner(tmp_path, fake_claude).execute(
        _task(), Profile.for_arm("baseline", out / "cfg"), out
    )
    assert run.error is None, run.error
    assert run.arm == "baseline"
    config = run.artifacts_dir / "claude_config"
    workspace = run.workspace_dir
    assert workspace is not None
    for base in (config, workspace / ".claude"):
        for part in ("skills", "agents", "rf-agentskills"):
            assert not (base / part).exists(), base / part
    settings = json.loads((config / "settings.json").read_text())
    assert "hooks" not in settings
    assert not (workspace / ".claude" / "settings.json").exists()
    assert set(_mcp(config)) == {"rf-mcp"}  # per-task server only
    assert baseline_isolation_problems(config, workspace, _PLUGIN) == []
    assert run.usage is not None and run.usage.total_cost_usd == pytest.approx(0.002)


def test_treatment_arm_provisions_plugin_as_shipped(tmp_path: Path, fake_claude: Path) -> None:
    (tmp_path / "fake-repo").mkdir()
    out = tmp_path / "runs"
    run = _runner(tmp_path, fake_claude).execute(
        _task(), Profile.for_arm("treatment", out / "cfg"), out
    )
    config = run.artifacts_dir / "claude_config"
    shipped = sorted(p.name for p in (_PLUGIN / "skills").iterdir() if p.is_dir())
    assert sorted(p.name for p in (config / "skills").iterdir()) == shipped
    assert (config / "agents").is_dir()
    assert json.loads((config / "settings.json").read_text()).get("hooks")
    assert set(_mcp(config)) == {"rf-mcp"}  # the plugin ships no MCP server


def test_arms_differ_only_by_the_plugin(tmp_path: Path, fake_claude: Path) -> None:
    (tmp_path / "fake-repo").mkdir()
    out = tmp_path / "runs"
    r = _runner(tmp_path, fake_claude)
    t_run = r.execute(_task(), Profile.for_arm("treatment", out / "cfg"), out)
    b_run = r.execute(_task(), Profile.for_arm("baseline", out / "cfg"), out)
    t_call, b_call = _calls(tmp_path)
    # identical flags (model, turns, tools, permission mode); prompt differs only by the
    # per-run workspace path in the preamble
    def _flags(argv: list[str]) -> list[str]:
        return [a for i, a in enumerate(argv) if i == 0 or argv[i - 1] != "-p"]

    assert _flags(t_call["argv"]) == _flags(b_call["argv"])  # type: ignore[arg-type]
    t_prompt = t_call["argv"][1].replace(str(t_run.workspace_dir.resolve()), "<ws>")  # type: ignore[index,union-attr]
    b_prompt = b_call["argv"][1].replace(str(b_run.workspace_dir.resolve()), "<ws>")  # type: ignore[index,union-attr]
    assert t_prompt == b_prompt
    # same fixture contents (ignoring the plugin's project-scope .claude/)
    def _tree(ws: Path) -> list[str]:
        return sorted(
            str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file() and ".claude" not in p.parts
        )

    assert _tree(t_run.workspace_dir) == _tree(b_run.workspace_dir)  # type: ignore[arg-type]
    t_mcp = _mcp(t_run.artifacts_dir / "claude_config")
    b_mcp = _mcp(b_run.artifacts_dir / "claude_config")
    assert t_mcp["rf-mcp"] == b_mcp["rf-mcp"]
    assert (t_run.arm, b_run.arm) == ("treatment", "baseline")


def test_baseline_fixture_with_skills_is_refused(tmp_path: Path, fake_claude: Path) -> None:
    (tmp_path / "fake-repo").mkdir()
    fixtures = tmp_path / "fixtures"
    (fixtures / "sut-leaky" / ".claude" / "skills" / "rf-browser").mkdir(parents=True)
    out = tmp_path / "runs"
    run = _runner(tmp_path, fake_claude, fixtures).execute(
        _task(fixture="sut-leaky"), Profile.for_arm("baseline", out / "cfg"), out
    )
    assert run.error is not None and run.error.startswith("arm-leak")
    assert not (tmp_path / "claude-calls.jsonl").exists()  # never launched


def test_baseline_transcript_with_skill_load_marks_run_error(
    tmp_path: Path, fake_claude: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "fake-repo").mkdir()
    monkeypatch.setenv("FAKE_CLAUDE_SKILL", "rf-agentskills:rf-browser")
    out = tmp_path / "runs"
    r = _runner(tmp_path, fake_claude)
    baseline = r.execute(_task(), Profile.for_arm("baseline", out / "cfg"), out)
    treatment = r.execute(_task(), Profile.for_arm("treatment", out / "cfg"), out)
    assert baseline.error == "arm-leak: baseline transcript loaded rf-browser"
    assert treatment.error is None


def test_trigger_profile_disables_hooks_and_uses_empty_workspace(
    tmp_path: Path, fake_claude: Path
) -> None:
    (tmp_path / "fake-repo").mkdir()
    out = tmp_path / "runs"
    task = Task(
        id="trigger-rf-browser-br-t01",
        skill="rf-browser",
        prompt="Write a Browser test",
        allowed_tools=("Skill", "Read", "Glob", "Grep"),
        max_turns=3,
    )
    profile = Profile.for_arm("treatment", out / "cfg", hooks_enabled=False, isolated_workspace=True)
    run = _runner(tmp_path, fake_claude).execute(task, profile, out)
    config = run.artifacts_dir / "claude_config"
    assert (config / "skills" / "rf-browser" / "SKILL.md").is_file()
    assert "hooks" not in json.loads((config / "settings.json").read_text())
    assert run.workspace_dir == run.artifacts_dir / "workspace"
    call = _calls(tmp_path)[0]
    argv = call["argv"]
    assert argv[argv.index("--max-turns") + 1] == "3"  # type: ignore[union-attr,index]
    assert argv[argv.index("--allowedTools") + 1] == "Skill,Read,Glob,Grep"  # type: ignore[union-attr,index]
    assert call["cwd"] == str(run.workspace_dir.resolve())  # type: ignore[union-attr]
    assert os.path.basename(str(call["config_dir"])) == "claude_config"
    assert set(_mcp(config)) == set()  # the plugin ships no MCP server
