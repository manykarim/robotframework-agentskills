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


# --- schema migration (strengthen-skill-eval-harness 1.5) ----------------------

_LEGACY_DB = Path(__file__).parent / "fixtures" / "legacy-eval-v1.db"


def test_legacy_db_migrates_on_open_and_round_trips(tmp_path: Path) -> None:
    import shutil
    import sqlite3

    from rf_skill_eval.infrastructure.persistence.sqlite_repo import SCHEMA_VERSION

    db = tmp_path / "eval.db"
    shutil.copy(_LEGACY_DB, db)
    raw = sqlite3.connect(db)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 0
    assert "status" not in {r[1] for r in raw.execute("PRAGMA table_info(verdicts)")}
    raw.close()

    with SqliteRunRepository(db) as repo:
        assert repo.schema_version == SCHEMA_VERSION
        statuses = [
            (r["check_name"], r["status"])
            for r in repo._conn.execute(
                "SELECT check_name, status FROM verdicts WHERE run_id='legacy-run-1' ORDER BY id"
            )
        ]
        assert statuses == [
            ("file_exists:reports/run-summary.md", "passed"),
            ("file_contains:reports/run-summary.md", "failed"),
        ]
        runs = {r.id: r for r in repo.list_runs()}
        assert runs["legacy-run-1"].effective_arm == "treatment"
        assert runs["legacy-run-2"].effective_arm == "baseline"  # old 'control' profile
        cards = {c.run_id: c for c in repo.load_scorecards()}
        assert [v.status for v in cards["legacy-run-1"].verdicts] == ["passed", "failed"]

        # New rows round-trip alongside the migrated ones.
        repo.save_run(_run(tmp_path).model_copy(update={"id": "new-run", "arm": "baseline"}))
        new = [
            Verdict.skipped("new-run", "lint", "robocop not installed"),
            Verdict(run_id="new-run", check_name="robot", status="passed", score=1.0, gating=True),
        ]
        repo.save_verdicts(new)
        repo.save_scorecard(Scorecard(run_id="new-run", task_id="t1", verdicts=tuple(new)))

    # Re-open: migration is idempotent and data is intact.
    with SqliteRunRepository(db) as repo:
        cards = {c.run_id: c for c in repo.load_scorecards()}
        assert cards["new-run"].gate_result == "pass"
        assert cards["new-run"].verdicts[0].status == "skipped"
        assert cards["new-run"].verdicts[0].reason == "robocop not installed"
        row = repo._conn.execute(
            "SELECT gate_result FROM scorecards WHERE run_id='new-run'"
        ).fetchone()
        assert row["gate_result"] == "pass"
        assert repo.load_run("new-run").effective_arm == "baseline"  # type: ignore[union-attr]


def test_fresh_db_has_current_schema_and_usage_round_trip(tmp_path: Path) -> None:
    from rf_skill_eval.domain.run import RunUsage
    from rf_skill_eval.infrastructure.persistence.sqlite_repo import SCHEMA_VERSION

    with SqliteRunRepository(tmp_path / "eval.db") as repo:
        assert repo.schema_version == SCHEMA_VERSION
        usage = RunUsage(input_tokens=5, output_tokens=7, num_turns=2, total_cost_usd=0.01)
        repo.save_run(_run(tmp_path).model_copy(update={"usage": usage, "replicate": 2}))
        loaded = repo.load_run("r1")
        assert loaded is not None
        assert loaded.usage == usage
        assert loaded.replicate == 2


def test_latest_scorecard_per_run_wins(tmp_path: Path) -> None:
    with SqliteRunRepository(tmp_path / "eval.db") as repo:
        repo.save_run(_run(tmp_path))
        first = Verdict(run_id="r1", check_name="a", status="failed", score=0.0, gating=True)
        second = Verdict(run_id="r1", check_name="a", status="passed", score=1.0, gating=True)
        repo.save_scorecard(Scorecard(run_id="r1", task_id="t1", verdicts=(first,)))
        repo.save_scorecard(Scorecard(run_id="r1", task_id="t1", verdicts=(second,)))
        cards = repo.load_scorecards()
        assert len(cards) == 1
        assert cards[0].gate_result == "pass"
