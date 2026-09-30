"""SQLite-backed implementation of the RunRepository port.

Follows ADR-006's append-only discipline: ``INSERT`` only, never
``UPDATE`` / ``DELETE`` in normal operation. The one exception is the
schema migration on open, which back-fills new columns of old rows.

Schema versions (``PRAGMA user_version``):

* ``0``/``1`` — original schema (``verdicts.passed`` boolean only);
* ``2`` — verdict ``status``/``reason``/``gating``/``category``, run
  ``arm``/``replicate``/usage/``error`` and scorecard ``gate_result``/
  ``incomplete_reason``. Old verdict rows migrate ``passed=1`` -> ``passed``
  and ``passed=0`` -> ``failed``.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ...domain.run import Run, RunUsage
from ...domain.scorecard import Scorecard
from ...domain.verdict import Verdict

_log = logging.getLogger(__name__)

SCHEMA_VERSION = 2

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

#: (table, column, SQL type/default) added by schema version 2.
_V2_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("runs", "workspace_dir", "TEXT"),
    ("runs", "arm", "TEXT"),
    ("runs", "replicate", "INTEGER NOT NULL DEFAULT 0"),
    ("runs", "error", "TEXT"),
    ("runs", "usage_json", "TEXT"),
    ("runs", "input_tokens", "INTEGER"),
    ("runs", "output_tokens", "INTEGER"),
    ("runs", "num_turns", "INTEGER"),
    ("runs", "duration_ms", "INTEGER"),
    ("runs", "total_cost_usd", "REAL"),
    ("verdicts", "status", "TEXT"),
    ("verdicts", "reason", "TEXT NOT NULL DEFAULT ''"),
    ("verdicts", "gating", "INTEGER NOT NULL DEFAULT 0"),
    ("verdicts", "category", "TEXT NOT NULL DEFAULT 'outcome'"),
    ("scorecards", "gate_result", "TEXT"),
    ("scorecards", "incomplete_reason", "TEXT"),
)


class SqliteRunRepository:
    """Concrete :class:`RunRepository` adapter backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()

    # --- schema -------------------------------------------------------------

    @property
    def schema_version(self) -> int:
        return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}

    def _migrate(self) -> None:
        if self.schema_version >= SCHEMA_VERSION:
            return
        _log.info("migrating %s to schema version %d", self._db_path, SCHEMA_VERSION)
        self._conn.execute("BEGIN")
        try:
            for table, column, decl in _V2_COLUMNS:
                if column not in self._columns(table):
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            self._conn.execute(
                "UPDATE verdicts SET status = CASE passed WHEN 1 THEN 'passed' ELSE 'failed' END "
                "WHERE status IS NULL"
            )
            self._conn.execute(
                "UPDATE runs SET arm = CASE profile_name "
                "WHEN 'control' THEN 'baseline' WHEN 'baseline' THEN 'baseline' "
                "ELSE 'treatment' END WHERE arm IS NULL"
            )
            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    # --- RunRepository ------------------------------------------------------

    def save_run(self, run: Run) -> None:
        usage = run.usage
        self._conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id, task_id, profile_name, started_at, finished_at,
                exit_code, session_jsonl_path, artifacts_dir, workspace_dir,
                model, timed_out, arm, replicate, error, usage_json,
                input_tokens, output_tokens, num_turns, duration_ms, total_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                run.effective_arm,
                run.replicate,
                run.error,
                usage.model_dump_json() if usage else None,
                usage.total_input_tokens if usage else None,
                usage.output_tokens if usage else None,
                usage.num_turns if usage else None,
                usage.duration_ms if usage else None,
                usage.total_cost_usd if usage else None,
            ),
        )

    def save_verdicts(self, verdicts: list[Verdict]) -> None:
        self._conn.executemany(
            """
            INSERT INTO verdicts (
                run_id, check_name, passed, score, details, status, reason, gating, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    v.run_id,
                    v.check_name,
                    1 if v.passed else 0,
                    v.score,
                    v.details,
                    v.status,
                    v.reason,
                    1 if v.gating else 0,
                    v.category,
                )
                for v in verdicts
            ],
        )

    def save_scorecard(self, scorecard: Scorecard) -> None:
        self._conn.execute(
            """
            INSERT INTO scorecards (
                run_id, task_id, created_at, pass_rate, total_score, details_json,
                gate_result, incomplete_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scorecard.run_id,
                scorecard.task_id,
                scorecard.created_at.isoformat(),
                scorecard.pass_rate,
                scorecard.total_score,
                json.dumps([v.model_dump(mode="json") for v in scorecard.verdicts]),
                scorecard.gate_result,
                scorecard.incomplete_reason,
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

    def load_scorecards(self) -> list[Scorecard]:
        """Latest scorecard per run (re-scoring appends; the newest wins)."""
        latest: dict[str, Scorecard] = {}
        cur = self._conn.execute("SELECT * FROM scorecards ORDER BY scorecard_id ASC")
        for row in cur.fetchall():
            verdicts_data = json.loads(row["details_json"] or "[]")
            verdicts = tuple(Verdict.model_validate(v) for v in verdicts_data)
            latest[row["run_id"]] = Scorecard(
                run_id=row["run_id"],
                task_id=row["task_id"],
                verdicts=verdicts,
                created_at=_parse_iso(row["created_at"]),
                incomplete_reason=_row_get(row, "incomplete_reason"),
            )
        return list(latest.values())

    # --- utilities ----------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteRunRepository:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _row_to_run(row: sqlite3.Row) -> Run:
    usage_json = _row_get(row, "usage_json")
    usage = RunUsage.model_validate_json(usage_json) if usage_json else None
    replicate_raw = _row_get(row, "replicate")
    return Run(
        id=row["run_id"],
        task_id=row["task_id"],
        profile_name=row["profile_name"],
        started_at=_parse_iso(row["started_at"]),
        finished_at=_parse_iso(row["finished_at"]) if row["finished_at"] else None,
        exit_code=row["exit_code"],
        session_jsonl_path=Path(row["session_jsonl_path"]) if row["session_jsonl_path"] else None,
        artifacts_dir=Path(row["artifacts_dir"]),
        workspace_dir=Path(ws) if (ws := _row_get(row, "workspace_dir")) else None,
        model=row["model"],
        timed_out=bool(row["timed_out"]),
        arm=_row_get(row, "arm") or "",
        replicate=int(replicate_raw) if replicate_raw is not None else 0,
        usage=usage,
        error=_row_get(row, "error"),
    )


def _row_get(row: sqlite3.Row, key: str) -> str | None:
    """Safe row access for columns added via ALTER TABLE on old DBs."""
    with contextlib.suppress(KeyError, IndexError):
        value = row[key]
        return None if value is None else str(value)
    return None


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
