"""CLI smoke tests via Typer's CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from rf_skill_eval.cli import app

runner = CliRunner()


def test_doctor_runs() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "rf-skill-eval doctor" in result.stdout


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
