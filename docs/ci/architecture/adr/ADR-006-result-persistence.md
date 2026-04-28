# ADR-006: Result Persistence & Reporting — SQLite + Parquet + On-Disk Artifacts

**Status:** Accepted
**Date:** 2026-04-14
**Deciders:** System Architecture
**Related:** ADR-002, ADR-004, ADR-005

---

## Context

The harness produces three kinds of output that need durable storage:

1. **Raw artifacts per run** — session JSONL, hook logs, fixture end-state,
   stdout stream-json. Large (tens of KB to hundreds of MB per batch), rarely
   read after analysis, needed for debugging and re-analysis with new metrics.
2. **Structured metrics** — one row per `(session, metric)` tuple. Medium size
   (thousands of rows per batch), queried by the scoring layer, analytical
   access patterns (group by, percentile, bootstrap).
3. **Scorecards and longitudinal series** — small, frequently read, needed for
   PR comments, canary baselines, and the RoboCon-style scoreboard view.

Non-functional requirements:

- **Zero-ops.** No server to run. Must work in GH Actions without a sidecar.
- **Append-only.** Historical scorecards are never mutated — ensures the
  canary's rolling baseline is trustworthy.
- **Portable.** Must open on a developer laptop with standard tools
  (`sqlite3`, `polars`, `pandas`).
- **Queryable for trends.** "Show me `first_run_test_pass_pct` for
  skill X over the last 12 canary runs" must be a one-liner.
- **Diff-friendly for git review.** Scorecards checked into the repo (or an
  orphan branch) should show reviewable diffs, not opaque binaries.

---

## Decision

**Use a three-tier storage stack: on-disk files for raw artifacts, Parquet for
structured metrics, and SQLite for scorecards + longitudinal series.**

### Tier 1 — Raw artifacts (on-disk filesystem)

```
eval/runs/<batch_id>/<cell_id>/
├── session.jsonl          ← copied from ~/.claude/projects/
├── hooks.log.jsonl        ← filtered by session id
├── stdout.stream.jsonl    ← claude CLI stdout
├── fixture-end-state/     ← the SUT dir after the run
└── metadata.json          ← env snapshot, timings, exit code
```

- One directory per cell (`(task_id, arm, replicate_idx)` encoded in
  `cell_id`).
- Retention managed by the CI artifact lifecycle (ADR-005): 30 days for PR,
  365 days for canary.
- Never mutated after write.
- Addressed by `ArtifactUri` value objects stored in SQLite.

### Tier 2 — Structured metrics (Parquet)

```
eval/runs/<batch_id>/metrics.parquet
```

- One Parquet file per batch. Schema:

  | column | type | note |
  |--------|------|------|
  | `batch_id` | string | |
  | `cell_id` | string | |
  | `task_id` | string | |
  | `profile_id` | string | control / treatment / treatment-<skill> |
  | `arm` | string | control / treatment |
  | `replicate_idx` | int32 | |
  | `tier` | string | narrow / realistic / adversarial |
  | `metric_id` | string | e.g., `read_edit_ratio` |
  | `metric_family` | string | e.g., `tool_workflow` |
  | `value` | float64 | null when `insufficient_data` or NA |
  | `session_id` | string | for traceability back to JSONL |
  | `cc_version` | string | |
  | `model_name` | string | |
  | `computed_at` | timestamp[ns, UTC] | |

- Written once at end of `compute_metrics` phase; never updated.
- Read via `polars.scan_parquet` for statistical comparisons (lazy; efficient
  groupby across batches).
- Columnar + snappy compression — ~10× smaller than equivalent CSV, 100×
  faster scans on our access patterns.
- Cross-batch queries (the canary's 30-day baseline) scan multiple Parquet
  files via `polars.scan_parquet("eval/runs/*/metrics.parquet")`.

### Tier 3 — Scorecards + longitudinal series (SQLite)

Single database file: `eval/reports/eval.db`

Tables (conceptual):

- `scorecards`
  - `scorecard_id` PK
  - `subject` (skill name or `bundle`)
  - `batch_id` FK → (batch record)
  - `suite_name`, `suite_version`
  - `verdict` (`SHIP | ITERATE | HOLD`)
  - `rationale` (text)
  - `created_at`
  - `env_snapshot` (JSON)
  - `gate_rule_snapshot` (JSON — frozen copy of the gate used)

- `arm_comparisons`
  - `comparison_id` PK
  - `scorecard_id` FK
  - `metric_id`
  - `metric_family`
  - `is_primary` (bool)
  - `median_control`, `median_treatment`
  - `delta` (Cliff's δ)
  - `p_value`, `p_value_corrected`
  - `ci_low`, `ci_high`
  - `n_control`, `n_treatment`
  - `gate_pass` (nullable bool; null for secondary)

- `longitudinal_points`
  - `skill_name`
  - `metric_id`
  - `canary_run_id` (FK to batches from canary workflow)
  - `value_median`, `value_iqr_low`, `value_iqr_high`
  - `created_at`

- `regression_events`
  - `event_id` PK
  - `skill_name`, `metric_id`
  - `baseline_window` (e.g., 30d)
  - `sigma_deviation`
  - `created_at`
  - `issue_url` (GH issue opened by canary)

- `batches`
  - `batch_id` PK
  - `workflow_tier` (`pr | merge | canary`)
  - `trigger_ref`, `commit_sha`
  - `started_at`, `completed_at`
  - `cells_planned`, `cells_completed`, `cells_failed`

All writes are `INSERT` (append-only). No `UPDATE` or `DELETE` in normal
operation. Schema migrations are additive.

### Publishing scorecards

- **Per PR:** scorecard uploaded as GH Actions artifact + rendered as a PR
  comment (via Markdown renderer — `infrastructure/reporting/md_renderer.py` —
  truncated if >65 KB).
- **Per merge:** HTML + JSON scorecard uploaded; `eval.db` updated.
- **Per canary:** same as merge, plus `longitudinal_points` rows appended and
  `regression_events` generated. `eval.db` is committed to an orphan
  `eval-history` branch (LFS-tracked) weekly. The main branch is never polluted
  by eval state.

### Reporting formats

| Format | Use case | Renderer |
|--------|----------|----------|
| HTML | Archive + browse (Jinja2 templates) | `html_renderer.py` |
| JSON | Machine-readable (other tools, dashboards) | `json_renderer.py` |
| Markdown | PR comments | `md_renderer.py` |

A single `Scorecard` aggregate renders to all three; formats are
presentation-only, never round-tripped back into state.

---

## Consequences

### Positive

- **Zero-ops.** SQLite + Parquet + files. No server, no network, no Postgres
  container. Works identically on laptop and in GH Actions.
- **Fast.** Polars + Parquet scan 100K-row longitudinal history in
  milliseconds — fast enough to re-analyze historical data for every canary
  run.
- **Reproducible.** Re-running analysis against an existing run dir produces
  byte-identical metrics Parquet (given a fixed metric catalog version).
- **Diff-friendly.** Scorecards are JSON + HTML; longitudinal trends are a
  single SQLite file reviewable with `sqlite3` on the command line.
- **Right tool per tier.** Filesystem for blobs; Parquet for analytics;
  SQLite for relational metadata and trend queries. No single tier is asked
  to do a job it's bad at.
- **Simple retention policy.** CI controls raw artifact retention; SQLite +
  Parquet kept forever (they're tiny in aggregate — < 1 GB per year).

### Negative

- **Three storage mechanisms to keep consistent.** Mitigated by: each tier has
  a single writer in `infrastructure/persistence/`; the domain only sees
  `Repository` protocols. No reader of tier N writes to tier M.
- **Git-branch state management.** Committing SQLite to an orphan `eval-history`
  branch is unusual; reviewers unfamiliar with the pattern may be confused.
  Mitigated by: README documents the pattern; the orphan branch is never merged
  and never touched by humans — only by the canary workflow.
- **Parquet tooling dependency.** `polars` is a hard dependency of the eval
  package. Mitigated by: `polars` is already needed for statistical analysis
  (ADR-004); no net new dependency.
- **No multi-writer safety.** SQLite locks do not tolerate concurrent writers
  from multiple machines. Mitigated by: CI is the only writer; the workflow
  serializes the analyze step; local re-analysis is single-threaded.

### Neutral

- SQLite file size at 1 year of canaries: ~5–15 MB. Negligible.

---

## Alternatives Considered

### Postgres / managed DB

- **Pros:** Familiar; concurrent writers; rich SQL; server-side analytics.
- **Cons:** Requires a running server; credentials management; CI
  complexity; overkill for this volume.
- **Why rejected:** No concurrent writers; scale does not justify the ops cost.

### Pure filesystem (JSON files per scorecard + per batch)

- **Pros:** Zero tooling; every reviewer has `jq`.
- **Cons:** Cross-batch queries (the canary rolling baseline is the key case)
  become O(n) directory scans; no relational integrity. Hard to keep scorecard
  metadata consistent with metric rows.
- **Why rejected:** Longitudinal queries are the headline feature; need a
  real store.

### DuckDB instead of Parquet + SQLite

- **Pros:** Single embedded analytical DB; great Parquet reading; one tool.
- **Cons:** DuckDB's on-disk `.duckdb` format is new and less universally
  tooled than SQLite; moving parts for relational-style metadata queries.
- **Why compromised:** We **use** DuckDB-style access patterns via polars
  reading Parquet (polars implements a query engine similar to DuckDB). This
  gives us analytical speed without committing to a less-mainstream on-disk
  format for long-lived metadata.

### JSON Lines per scorecard + append-only log

- **Pros:** Simple; reviewable; easy to script.
- **Cons:** Canary rolling-baseline queries become a full-scan every run;
  no indexes; scorecard/longitudinal separation harder to enforce.
- **Why rejected:** Same as pure filesystem — wrong tool for trend queries.

### Store scorecards in main-branch git

- **Pros:** Full diff history for free.
- **Cons:** Pollutes PR diffs with auto-generated scoreboard noise; conflicts
  across parallel PRs; makes rebasing a mess.
- **Why rejected:** Orphan branch keeps history visible without polluting
  working branches.

---

## Implementation Notes

- `domain/persistence/repositories.py` defines `Protocol`s:
  `RunArtifactRepository`, `MetricsRepository`, `ScorecardRepository`,
  `LongitudinalRepository`. Application layer depends only on these.
- `infrastructure/persistence/sqlite_repo.py` uses stdlib `sqlite3` + typed
  row adapters; no SQLAlchemy needed at this size.
- `infrastructure/persistence/parquet_store.py` wraps polars write; schema
  version is encoded in a Parquet key-value metadata field so the reader can
  detect old formats.
- `infrastructure/persistence/artifact_store.py` is a thin wrapper over
  `pathlib.Path` — the "store" is just the filesystem with a conventional
  layout.
- Schema migrations: bump `schema_version` table row; apply additive
  migrations on startup. Breaking schema changes require a new database file
  (never drop columns).
- The `eval-history` orphan branch commit is a single step in the canary
  workflow: checkout orphan branch → copy `eval.db` → commit with
  `--allow-empty` if unchanged → push.

---

## References

- `docs/ci/rf-agentskills-eval-implementation-plan.md` §7 — scorecard format.
- Polars docs — lazy Parquet scans: https://docs.pola.rs/.
- SQLite append-only patterns — the `INSERT`-only schema as audit-log discipline.
