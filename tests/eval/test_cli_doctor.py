"""CLI smoke tests via Typer's CliRunner."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from typer.testing import CliRunner

from rf_skill_eval.cli import app

runner = CliRunner()


def test_doctor_runs(monkeypatch) -> None:
    # Stub the auth ping: a developer's .env token must not trigger a live API call.
    monkeypatch.setattr("rf_skill_eval.cli._claude_auth_ping", lambda _b: (True, "stubbed"))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "rf-skill-eval doctor" in result.stdout


def test_doctor_fails_when_auth_ping_returns_api_error(monkeypatch) -> None:
    """The whole point of the ping: bad token → exit code 1, not silent pass."""

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")

    fake_completed = subprocess.CompletedProcess(
        args=["claude"],
        returncode=0,
        stdout='{"type":"result","is_error":true,"result":"API Error: Header has invalid value"}',
        stderr="",
    )
    with patch("rf_skill_eval.cli.shutil.which", return_value="/fake/claude"), patch(
        "rf_skill_eval.cli.subprocess.run", return_value=fake_completed
    ):
        result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "claude auth ping" in result.stdout
    assert "API rejected probe" in result.stdout


def test_doctor_passes_ping_with_clean_response(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake")
    fake_completed = subprocess.CompletedProcess(
        args=["claude"],
        returncode=0,
        stdout='{"type":"result","is_error":false,"result":"ok"}',
        stderr="",
    )
    with patch("rf_skill_eval.cli.shutil.which", return_value="/fake/claude"), patch(
        "rf_skill_eval.cli.subprocess.run", return_value=fake_completed
    ):
        result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "auth verified via claude --print" in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "score" in result.stdout
    assert "report" in result.stdout
    assert "doctor" in result.stdout
    assert "bench" in result.stdout


def test_run_missing_task_errors() -> None:
    result = runner.invoke(app, ["run", "--task", "/nonexistent/task.yaml"])
    assert result.exit_code != 0


# --- grader requirements (strengthen-skill-eval-harness 1.6) ---------------------

from pathlib import Path  # noqa: E402

import yaml  # noqa: E402

from rf_skill_eval import cli as cli_module  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]


def _no_ping(monkeypatch) -> None:
    # Never call the real CLI/API from these tests (a local .env may hold a token).
    monkeypatch.setattr(cli_module, "_claude_auth_ping", lambda _b: (True, "stubbed"))


def test_doctor_lists_grader_requirements_of_selected_tasks(monkeypatch) -> None:
    _no_ping(monkeypatch)
    result = runner.invoke(app, ["doctor", "--tasks-dir", str(_REPO / "eval" / "tasks" / "narrow")])
    assert result.exit_code == 0, result.stdout
    for req in ("tool:robot", "module:Browser", "module:SeleniumLibrary", "module:REST"):
        assert f"grader {req}" in result.stdout


def test_doctor_strict_fails_on_missing_grader_library(tmp_path: Path, monkeypatch) -> None:
    _no_ping(monkeypatch)
    tasks = tmp_path / "narrow"
    tasks.mkdir()
    (tasks / "t.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "narrow-x",
                "skill": "rf-results",
                "prompt": "x",
                "primary_metric": "robot_pass",
                "grader_checks": [
                    {"type": "robot_pass", "target": "t.robot", "requires": ["NoSuchLibZz"]},
                    {"type": "lint_clean", "target": "t.robot"},
                ],
            }
        )
    )
    lenient = runner.invoke(app, ["doctor", "--tasks-dir", str(tmp_path)])
    assert lenient.exit_code == 0
    assert "module:NoSuchLibZz" in lenient.stdout
    strict = runner.invoke(app, ["doctor", "--tasks-dir", str(tmp_path), "--strict"])
    assert strict.exit_code == 1


def test_grader_requirements_mapping() -> None:
    from rf_skill_eval.domain.task import Task

    task = Task(
        id="t",
        skill="rf-results",
        prompt="x",
        grader_checks=[
            {"type": "robot_dryrun", "target": "a", "requires": ["AppiumLibrary"]},
            {"type": "lint_clean", "target": "a"},
            {"type": "keywords_resolve", "target": "a", "specs": ["s.json"]},
        ],
    )
    needs = cli_module.grader_requirements([task])
    assert set(needs) == {"tool:robot", "tool:robocop", "module:robot", "module:AppiumLibrary"}
