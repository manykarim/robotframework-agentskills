"""SQLite-backed implementation of the RunRepository port.

Follows ADR-006's append-only discipline: ``INSERT`` only, never
``UPDATE`` / ``DELETE`` in normal operation. Schema is initialised on
first open.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ...domain.run import Run
from ...domain.scorecard import Scorecard
from ...domain.verdict import Verdict

_log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    exit_code INTEGER,
    session_jsonl_path TEXT,
    artifacts_dir TEXT NOT NULL,
    workspace_dir TEXT,
    model TEXT NOT NULL,
    timed_out INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    check_name TEXT NOT NULL,
    passed INTEGER NOT NULL,
    score REAL NOT NULL,
    details TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS scorecards (
    scorecard_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    pass_rate REAL NOT NULL,
    total_score REAL NOT NULL,
    details_json TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_verdicts_run ON verdicts(run_id);
CREATE INDEX IF NOT EXISTS idx_scorecards_run ON scorecards(run_id);
"""


class SqliteRunRepository:
    """Concrete :class:`RunRepository` adapter backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        # Best-effort in-place migration for DBs created before workspace_dir
        # was added. Adding a column is idempotent-failure-safe: catch OperationalError.
        with contextlib.suppress(sqlite3.OperationalError):
            self._conn.execute("ALTER TABLE runs ADD COLUMN workspace_dir TEXT")

    # --- RunRepository ------------------------------------------------------

    def save_run(self, run: Run) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, task_id, profile_name, started_at, finished_at,
                exit_code, session_jsonl_path, artifacts_dir, workspace_dir,
                model, timed_out
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.task_id,
                run.profile_name,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.exit_code,
                str(run.session_jsonl_path) if run.session_jsonl_path else None,
                str(run.artifacts_dir),
                str(run.workspace_dir) if run.workspace_dir else None,
                run.model,
                1 if run.timed_out else 0,
            ),
        )

    def save_verdicts(self, verdicts: list[Verdict]) -> None:
        self._conn.executemany(
            """
            INSERT INTO verdicts (run_id, check_name, passed, score, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(v.run_id, v.check_name, 1 if v.passed else 0, v.score, v.details) for v in verdicts],
        )

    def save_scorecard(self, scorecard: Scorecard) -> None:
        self._conn.execute(
            """
            INSERT INTO scorecards (
                run_id, task_id, created_at, pass_rate, total_score, details_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                scorecard.run_id,
                scorecard.task_id,
                scorecard.created_at.isoformat(),
                scorecard.pass_rate,
                scorecard.total_score,
                json.dumps([v.model_dump() for v in scorecard.verdicts]),
            ),
        )

    def load_run(self, run_id: str) -> Run | None:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_run(row)

    def list_runs(self) -> list[Run]:
        rows = self._conn.execute("SELECT * FROM runs ORDER BY started_at ASC").fetchall()
        return [_row_to_run(r) for r in rows]

    # --- utilities ----------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteRunRepository:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _row_to_run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["run_id"],
        task_id=row["task_id"],
        profile_name=row["profile_name"],
        started_at=_parse_iso(row["started_at"]),
        finished_at=_parse_iso(row["finished_at"]) if row["finished_at"] else None,
        exit_code=row["exit_code"],
        session_jsonl_path=Path(row["session_jsonl_path"]) if row["session_jsonl_path"] else None,
        artifacts_dir=Path(row["artifacts_dir"]),
        workspace_dir=Path(row["workspace_dir"]) if _row_get(row, "workspace_dir") else None,
        model=row["model"],
        timed_out=bool(row["timed_out"]),
    )


def _row_get(row: sqlite3.Row, key: str) -> str | None:
    """Safe row access for columns added via ALTER TABLE on old DBs.

    Only used for TEXT columns; casts to ``str`` so mypy is happy on strict.
    """
    try:
        value = row[key]
    except (KeyError, IndexError):
        return None
    if value is None:
        return None
    return str(value)


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
