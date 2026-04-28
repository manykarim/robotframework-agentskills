"""SQLite repository round-trip."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from rf_skill_eval.domain.run import Run
from rf_skill_eval.domain.scorecard import Scorecard
from rf_skill_eval.domain.verdict import Verdict
from rf_skill_eval.infrastructure.persistence.sqlite_repo import SqliteRunRepository


def _run(artifacts: Path) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="r1",
        task_id="t1",
        profile_name="treatment",
        started_at=now,
        finished_at=now,
        exit_code=0,
        artifacts_dir=artifacts,
    )


def test_save_and_load_run(tmp_path: Path) -> None:
    db = tmp_path / "eval.db"
    with SqliteRunRepository(db) as repo:
        original = _run(tmp_path)
        repo.save_run(original)
        loaded = repo.load_run("r1")
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.task_id == original.task_id


def test_save_verdicts_and_scorecard(tmp_path: Path) -> None:
    db = tmp_path / "eval.db"
    with SqliteRunRepository(db) as repo:
        repo.save_run(_run(tmp_path))
        verdicts = [
            Verdict(run_id="r1", check_name="a", passed=True, score=1.0),
            Verdict(run_id="r1", check_name="b", passed=False, score=0.0),
        ]
        repo.save_verdicts(verdicts)
        sc = Scorecard(run_id="r1", task_id="t1", verdicts=tuple(verdicts))
        repo.save_scorecard(sc)
        runs = repo.list_runs()
        assert [r.id for r in runs] == ["r1"]
