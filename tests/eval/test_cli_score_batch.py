"""End-to-end test for the ``score-batch`` CLI command using seeded SQLite."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from typer.testing import CliRunner

from rf_skill_eval.cli import app
from rf_skill_eval.domain.run import Run
from rf_skill_eval.infrastructure.persistence.sqlite_repo import SqliteRunRepository


def _write_task(tasks_dir: Path, task_id: str, target_file: str) -> Path:
    path = tasks_dir / f"{task_id}.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "id": task_id,
                "skill": "keyword-builder",
                "description": "test",
                "prompt": "x",
                "model": "claude-haiku-4-5",
                "max_turns": 2,
                "timeout_seconds": 60,
                "allowed_tools": ["Write"],
                "tier": "narrow",
                "grader_checks": [
                    {"type": "file_exists", "path": target_file},
                ],
                "expected_files": [{"path": target_file}],
            }
        )
    )
    return path


def test_score_batch_passes_when_file_exists(tmp_path: Path) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run_id = "t-1-treatment-abc12345"
    artifacts_dir = runs_dir / run_id
    workspace = artifacts_dir / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "hello.txt").write_text("ok")

    _write_task(tasks_dir, "t-1", "hello.txt")
    repo = SqliteRunRepository(runs_dir / "eval.db")
    repo.save_run(
        Run(
            id=run_id,
            task_id="t-1",
            profile_name="treatment",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            exit_code=0,
            artifacts_dir=artifacts_dir,
            workspace_dir=workspace,
            model="claude-haiku-4-5",
            timed_out=False,
        )
    )
    repo.close()

    result = CliRunner().invoke(
        app,
        ["score-batch", "--runs-dir", str(runs_dir), "--tasks-dir", str(tasks_dir)],
    )

    assert result.exit_code == 0, result.stdout
    assert "t-1" in result.stdout


def test_score_batch_fails_when_run_dir_has_no_db(tmp_path: Path) -> None:
    runs_dir = tmp_path / "empty"
    runs_dir.mkdir()
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    result = CliRunner().invoke(
        app,
        ["score-batch", "--runs-dir", str(runs_dir), "--tasks-dir", str(tasks_dir)],
    )

    assert result.exit_code == 2


def test_report_aggregates_multiple_db(tmp_path: Path) -> None:
    """``report`` must walk runs-dir recursively and union all eval.db rows."""

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "t-1", "hello.txt")
    _write_task(tasks_dir, "t-2", "world.txt")

    parent = tmp_path / "parent"
    narrow_dir = parent / "narrow"
    realistic_dir = parent / "realistic"
    for tier_dir, run_id, task_id, fname in (
        (narrow_dir, "t-1-treatment-n1111111", "t-1", "hello.txt"),
        (realistic_dir, "t-2-treatment-r2222222", "t-2", "world.txt"),
    ):
        workspace = tier_dir / run_id / "workspace"
        workspace.mkdir(parents=True)
        (workspace / fname).write_text("ok")
        repo = SqliteRunRepository(tier_dir / "eval.db")
        repo.save_run(
            Run(
                id=run_id, task_id=task_id, profile_name="treatment",
                started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
                exit_code=0, artifacts_dir=tier_dir / run_id,
                workspace_dir=workspace, model="claude-haiku-4-5", timed_out=False,
            )
        )
        repo.close()

    cli = CliRunner()
    for tier_dir in (narrow_dir, realistic_dir):
        r = cli.invoke(app, ["score-batch", "--runs-dir", str(tier_dir),
                             "--tasks-dir", str(tasks_dir)])
        assert r.exit_code == 0, r.stdout

    out_path = tmp_path / "out.md"
    r = cli.invoke(app, ["report", "--runs-dir", str(parent), "--format", "md",
                         "--output", str(out_path)])
    assert r.exit_code == 0, r.stdout
    body = out_path.read_text()
    assert "t-1" in body and "t-2" in body
