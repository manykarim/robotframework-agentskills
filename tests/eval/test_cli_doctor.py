"""CLI smoke tests via Typer's CliRunner."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from typer.testing import CliRunner

from rf_skill_eval.cli import app

runner = CliRunner()


def test_doctor_runs() -> None:
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
