# DDD Architecture — `rf-agentskills-eval`

**Status:** Draft (v1)
**Date:** 2026-04-14
**Scope:** Domain-Driven Design for the CI-based skill evaluation system described in
`docs/ci/claude-code-extension-quality-evaluation.md` and
`docs/ci/rf-agentskills-eval-implementation-plan.md`.

This document defines bounded contexts, aggregates, entities, value objects, domain events,
the ubiquitous language, and the physical Python module layout (managed with `uv`) for the
evaluation subsystem. It is intentionally **design-only** — no source code is generated.

---

## 1. Problem Framing

The parent project ships 11 Agent Skills distributed via three channels (root `skills/`,
Claude Code plugin, VS Code extension). We need a CI-driven harness that answers:

1. Does a given skill / bundle measurably improve Claude Code's behavior on RF tasks?
2. Has a shipped skill regressed (model drift, skill drift, or harness drift)?
3. Which skill should ship, iterate, or be removed?

The harness is a **test framework for probabilistic agents**, not a conventional unit test
runner. The core domain is **evaluation**: defining tasks, running A/B sessions, parsing
telemetry, scoring, and producing signed scorecards.

### Core Domain
**Scoring & Metrics** — the reason this system exists. Getting the statistical comparison
and shipping gate right is what separates a scorecard from a log dump.

### Supporting Subdomains
- **Evaluation Orchestration** — sequencing suites, replicates, arms.
- **Skill Invocation** — driving Claude Code sessions under controlled conditions.
- **Dataset / Fixtures** — versioned task bank and SUT snapshots.
- **Result Persistence** — runs, metrics, scorecards, longitudinal trend.

### Generic Subdomains
- **CI Integration** — GitHub Actions matrix glue, artifact upload, PR comment.
- **Reporting** — HTML/JSON scorecards.

---

## 2. Ubiquitous Language

| Term | Definition |
|------|------------|
| **Skill** | An Agent Skill shipped in `skills/` (identified by its `name:` field). |
| **Skill Bundle** | The full set of skills under evaluation in one run. |
| **Profile** | A `CLAUDE_CONFIG_DIR` configuration — `control`, `treatment`, or `treatment-<skill>`. |
| **Arm** | A profile's role in the A/B comparison (`control` vs `treatment`). |
| **Task** | A YAML-defined scenario with a prompt, a fixture, and success criteria. |
| **Tier** | Task difficulty class: `narrow`, `realistic`, `adversarial`. |
| **Fixture** | A git-pinned SUT (System Under Test) project copied fresh per run. |
| **Run** | One invocation of `claude -p` against one `(task, profile)` pair. |
| **Replicate** | An index within a cell `(task, profile)` — N=8 is the default. |
| **Session JSONL** | Claude Code's native log at `~/.claude/projects/<slug>/*.jsonl`. |
| **Telemetry** | Structured rows extracted from session JSONL + hook logs. |
| **Metric** | A scalar value computed from telemetry or grader output (e.g., `read_edit_ratio`). |
| **Primary Metric** | Gating metric; regression blocks ship. |
| **Secondary Metric** | Informational; reported but not gating. |
| **Grader** | Subsystem that runs the produced RF files and applies `success_criteria`. |
| **Criterion** | A single pass/fail check within `success_criteria` (`robot_pass`, `file_exists`, …). |
| **Arm Comparison** | Statistical result for one metric across control vs treatment. |
| **Scorecard** | Signed per-skill/per-bundle report with verdict: SHIP / ITERATE / HOLD. |
| **Shipping Gate** | The rule set over primary metrics that produces the verdict. |
| **Canary** | A scheduled re-run that detects model or skill regression over time. |
| **Eval Suite** | A named collection of tasks + profiles + replicate count (e.g., `rf-full-v1`). |

---

## 3. Bounded Contexts

Six bounded contexts, each owning a coherent piece of the eval lifecycle. Contexts
communicate via **domain events** (in-process publish/subscribe) and **artifacts on disk**
(run directories, Parquet files, SQLite). No context reads another's internal state.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Evaluation Orchestration                          │
│   (plans runs, supervises replicates, emits domain events)           │
└──────────────────────────────────────────────────────────────────────┘
           │                │                │               │
           ▼                ▼                ▼               ▼
    ┌───────────┐    ┌────────────┐   ┌────────────┐  ┌─────────────┐
    │ Fixtures  │    │   Skill    │   │ Telemetry  │  │  Grader     │
    │ & Tasks   │───▶│ Invocation │──▶│ & Metrics  │──│ (criterion) │
    └───────────┘    └────────────┘   └────────────┘  └─────────────┘
                                             │               │
                                             ▼               ▼
                                      ┌──────────────────────────┐
                                      │  Scoring & Verdict       │
                                      │  (core domain)           │
                                      └──────────────────────────┘
                                                  │
                                                  ▼
                                      ┌──────────────────────────┐
                                      │ Result Persistence &     │
                                      │ Reporting                │
                                      └──────────────────────────┘
                                                  │
                                                  ▼
                                      ┌──────────────────────────┐
                                      │ CI Integration           │
                                      │ (Actions matrix, artifacts)
                                      └──────────────────────────┘
```

### 3.1 Evaluation Orchestration (Supporting)

**Purpose:** Plan and sequence a batch; own the run lifecycle.

**Aggregates**
- `EvalSuite` (root) — immutable plan: tasks, profiles, replicate count, randomization seed.
- `RunBatch` (root) — a concrete execution of an `EvalSuite` with timestamp + env metadata.

**Entities**
- `RunCell` — one `(task_id, profile_id, replicate_idx)` coordinate within a batch.

**Value Objects**
- `ReplicateCount` (int ≥ 1)
- `RandomizationSeed`
- `EnvironmentSnapshot` (cc_version, model_name, os, rf_version, mcp_version)

**Domain Events**
- `BatchPlanned { batch_id, cell_count, seed }`
- `CellDispatched { batch_id, cell_id }`
- `CellCompleted { batch_id, cell_id, outcome, duration }`
- `BatchCompleted { batch_id, success_rate }`

**Invariants**
- A `RunBatch` is immutable once started (no cells added mid-batch).
- Cells are dispatched in a randomized order derived from the seed.

**Domain-relevant scheduling constraint.** When the CI deployment uses the
subscription-based `CLAUDE_CODE_OAUTH_TOKEN` auth path (see ADR-005
"Authentication"), batch scheduling must respect the Claude
subscription's 5-hour rate-limit windows — shared with the maintainer's
interactive sessions. This shows up in Orchestration as: a cap on
concurrent `SessionExecution`s per batch (1–2 under OAuth, up to 8 under
API-key fallback), and canary-tier batches scheduled for off-hours. The
`ShippingGate` / `Scorecard` contexts do not care about this — the
constraint lives purely in Orchestration's planning logic and in the
infrastructure adapter that enforces concurrency.

### 3.2 Skill Invocation (Supporting)

**Purpose:** Execute one session of Claude Code against one cell, capture all artifacts.

**Aggregates**
- `SessionExecution` (root) — one `claude -p` invocation and its captured artifacts.

**Entities**
- `CapturedArtifactSet` — JSONL, hook logs, fixture end-state, stdout stream-json.

**Value Objects**
- `Profile` (`{id, config_dir, skills_enabled: set[SkillName]}`)
- `InvocationCommand` (immutable built from profile + task)
- `InvocationOutcome` (`normal | timeout | tool_error | exit_nonzero`)
- `SessionId`
- `WallClock` (start, end, duration)

**Domain Events**
- `SessionStarted { session_id, cell_id, profile_id }`
- `SessionEnded { session_id, outcome, artifact_paths }`

**Invariants**
- Every session runs in a fresh copy of the task's fixture (never re-used).
- Profile is chosen by ID; the system never mutates profiles between sessions.
- Captured artifacts are write-once (append to the run directory, never overwrite).

**Strategy (see ADR-003):** Subprocess invocation of the `claude` CLI in print mode.

### 3.3 Dataset / Fixtures (Supporting)

**Purpose:** Versioned inputs — the task bank and the SUT fixtures.

**Aggregates**
- `TaskBank` (root) — named, versioned collection of tasks (e.g., `rf-full-v1`).
- `FixtureCatalog` (root) — git-pinned SUT projects.

**Entities**
- `Task` — one YAML scenario (id, tier, prompt, fixture_ref, success_criteria, timeout).
- `Fixture` — one SUT project (id, git_url, sha, local_path).
- `SuccessCriterion` — one check within a task (polymorphic: `RobotPassCriterion`,
  `FileExistsCriterion`, `FileContainsCriterion`, `LintCleanCriterion`,
  `NoDeprecatedKeywordsCriterion`, `ImportResolvesCriterion`, `CustomPythonCriterion`).

**Value Objects**
- `TaskId`, `TaskTier (narrow|realistic|adversarial)`
- `FixtureRef (id + sha)`
- `TimeoutMinutes`
- `SkillScope` (list of skill names a task is meant to exercise)

**Invariants**
- A `Task` always references a `FixtureRef` pinned to a specific SHA.
- `SuccessCriterion` types are closed (new types require explicit addition).
- Task YAML is validated on load; malformed tasks never enter a batch plan.

### 3.4 Telemetry & Metrics (Core)

**Purpose:** Parse session JSONL + hook logs into a tidy metrics dataframe.

**Aggregates**
- `SessionTelemetry` (root) — parsed representation of one session.

**Entities**
- `ToolCall`, `ThinkingBlock`, `UserMessage`, `HookFire` (from plan §2.2).

**Value Objects**
- `MetricId` (string enum — one per metric in the catalog)
- `MetricValue` (`float | int | bool | None`)
- `MetricRow` (`{session_id, metric_id, value, tier, task_id, profile_id, replicate_idx}`)
- `MetricFamily` (`tool_workflow | thinking_depth | linguistic | user_signal | rf_specific | outcome_cost`)

**Domain Events**
- `TelemetryParsed { session_id, tool_call_count }`
- `MetricsComputed { session_id, metrics_count }`

**Invariants**
- Metrics are pure functions: same input → same output; no hidden state.
- A metric may legitimately return `None` (e.g., `read_edit_ratio` when edits=0) —
  downstream stats layer handles nulls.
- RF-specific metrics that depend on grader output are computed **after** grading, not during parsing.

### 3.5 Scoring & Verdict (Core)

**Purpose:** Compare arms statistically and render a shipping verdict.

**Aggregates**
- `Scorecard` (root) — per-skill or per-bundle signed result.
- `ShippingGate` (root, singleton per config) — the rule set.

**Entities**
- `ArmComparison` — statistical result for one metric × one (task-or-tier) scope.
- `MetricVerdict` — primary/secondary classification + pass/fail under the gate.

**Value Objects**
- `EffectSize` (Cliff's delta, float ∈ [-1, +1])
- `ConfidenceInterval` (low, high, alpha)
- `PValue` (float ∈ [0, 1])
- `Verdict` (`SHIP | ITERATE | HOLD`)
- `GateRule` (e.g., `min_primary_improvement_delta=0.33`, `max_cost_increase_pct=30`)

**Domain Events**
- `ComparisonComputed { scorecard_id, metric_id }`
- `VerdictRendered { scorecard_id, verdict, rationale }`

**Invariants**
- Primary metrics are a pre-registered, small set (per ADR-004). Gating uses only these.
- Multiple-testing correction (Benjamini-Hochberg) is applied only to the primary set.
- A `Verdict` is derived, not set — it is the pure output of `ShippingGate(Scorecard)`.

**See ADR-004** for the scoring model (rubric-based effect-size gating over deterministic
grader results, not LLM-as-judge).

### 3.6 Result Persistence & Reporting (Supporting)

**Purpose:** Store artifacts durably, render scorecards, maintain longitudinal view.

**Aggregates**
- `ResultStore` (root) — SQLite + Parquet + filesystem artifacts.
- `Report` (root) — one generated HTML/JSON scorecard.

**Entities**
- `RunArtifact` (pointer to on-disk run directory)
- `MetricsSnapshot` (Parquet file handle)
- `LongitudinalSeries` (time-series of a metric for a skill)

**Value Objects**
- `ReportFormat` (`html | json | markdown`)
- `ArtifactUri` (local path or GH Actions artifact URL)

**Domain Events**
- `ScorecardPersisted { scorecard_id, uri }`
- `RegressionDetected { skill_name, metric_id, sigma }`

**Invariants**
- Persistence is append-only. Old scorecards are never mutated.
- Longitudinal view is derived from the append log; no separate write path.

**See ADR-006** for the storage model (SQLite for metadata, Parquet for metrics, on-disk
artifacts for raw sessions).

### 3.7 CI Integration (Generic)

**Purpose:** Glue layer between GitHub Actions and the domain. Owns the reusable workflow,
matrix strategy, cache keys, artifact upload, and PR-comment rendering.

**Aggregates**
- None — this context holds no domain state. It is a thin adapter.

**Entities / Value Objects**
- `CiRun` (GH Actions run id + metadata — opaque to the domain)
- `ArtifactBundle` (inputs to `actions/upload-artifact`)

**Infrastructure adapters**
- `anthropics/claude-code-action@v1` — the auth + invocation wrapper for
  Claude Code in GitHub Actions. Consumes either `CLAUDE_CODE_OAUTH_TOKEN`
  (primary, subscription-based) or `ANTHROPIC_API_KEY` (fallback,
  per-token billed). See ADR-005 "Authentication".
- `actions/upload-artifact@v4` — artifact persistence adapter.
- `.github/actions/install-claude-code` — composite action pinning the
  `claude` CLI version (referenced by `EnvironmentSnapshot`).
- `actions/github-script` / `gh` — PR-comment and issue-creation
  adapters for `ScorecardPersisted` / `RegressionDetected` events.

**Domain Events (consumed)**
- `ScorecardPersisted` → triggers PR comment.
- `RegressionDetected` → triggers `::error::` annotation.

**See ADR-005.**

---

## 4. Context Map

```
                         upstream                    downstream
Fixtures/Tasks ────────── Shared Kernel (Task schema) ──▶ Orchestration
Orchestration ────────── Customer/Supplier ─────────────▶ Skill Invocation
Skill Invocation ─────── Published Language (JSONL) ────▶ Telemetry & Metrics
Telemetry & Metrics ──── Customer/Supplier ─────────────▶ Scoring & Verdict
Scoring & Verdict ────── Customer/Supplier ─────────────▶ Persistence & Reporting
Persistence & Reporting  Open Host Service (artifacts) ─▶ CI Integration
```

- **Shared Kernel:** Task YAML schema (Pydantic) shared by Fixtures/Tasks and Orchestration.
- **Published Language:** Claude Code session JSONL format — Telemetry consumes it but does
  not own it (upstream is Anthropic). A frozen internal `TelemetryRow` schema insulates
  downstream contexts from Anthropic schema changes (anti-corruption layer inside Telemetry).
- **Anti-Corruption Layer:** Skill Invocation wraps the `claude` CLI; the rest of the domain
  never sees CLI flags or env vars.

---

## 5. Module / Package Layout

Managed with `uv` (see ADR-001). New tree under `eval/` at the repo root — keeps the
evaluation system cleanly separated from the production `skills/`, `plugins/`, and
`vscode-extension/` trees that sync-skills manages.

```
eval/                                   ← self-contained evaluation subsystem
├── pyproject.toml                      ← uv-managed; package: rf-agentskills-eval
├── uv.lock                             ← committed
├── README.md                           ← quickstart + CI entry points
├── .python-version                     ← pinned for uv (3.12)
│
├── src/
│   └── rf_agentskills_eval/
│       ├── __init__.py
│       ├── domain/                     ← pure domain (no I/O)
│       │   ├── __init__.py
│       │   ├── orchestration/          ← bounded context 3.1
│       │   │   ├── aggregates.py       ← EvalSuite, RunBatch
│       │   │   ├── events.py
│       │   │   └── invariants.py
│       │   ├── invocation/             ← bounded context 3.2
│       │   │   ├── aggregates.py       ← SessionExecution
│       │   │   ├── profile.py          ← Profile VO
│       │   │   └── events.py
│       │   ├── dataset/                ← bounded context 3.3
│       │   │   ├── task.py             ← Task, TaskBank
│       │   │   ├── fixture.py
│       │   │   └── criteria.py         ← SuccessCriterion hierarchy
│       │   ├── telemetry/              ← bounded context 3.4
│       │   │   ├── schema.py           ← ToolCall, ThinkingBlock, UserMessage, HookFire
│       │   │   ├── metrics/
│       │   │   │   ├── catalog.py      ← MetricId enum + registry
│       │   │   │   ├── workflow.py     ← read_edit_ratio, etc.
│       │   │   │   ├── linguistic.py
│       │   │   │   ├── user_signals.py
│       │   │   │   ├── rf_specific.py
│       │   │   │   └── outcome_cost.py
│       │   │   └── events.py
│       │   ├── scoring/                ← bounded context 3.5 (CORE)
│       │   │   ├── comparison.py       ← ArmComparison, stats
│       │   │   ├── gate.py             ← ShippingGate, GateRule
│       │   │   ├── scorecard.py        ← Scorecard aggregate
│       │   │   └── events.py
│       │   └── persistence/            ← bounded context 3.6 (interfaces only)
│       │       ├── repositories.py     ← Protocols: RunRepository, ScorecardRepository
│       │       └── events.py
│       │
│       ├── application/                ← use cases / command handlers
│       │   ├── plan_batch.py           ← PlanEvalBatchCommand
│       │   ├── execute_cell.py
│       │   ├── parse_telemetry.py
│       │   ├── grade_run.py
│       │   ├── compute_scorecard.py
│       │   └── publish_report.py
│       │
│       ├── infrastructure/             ← I/O, CLI, external adapters
│       │   ├── cli/
│       │   │   ├── main.py             ← `uv run rf-eval …` entry point (Typer)
│       │   │   ├── plan.py
│       │   │   ├── run.py
│       │   │   ├── analyze.py
│       │   │   └── report.py
│       │   ├── runner/
│       │   │   ├── claude_cli.py       ← subprocess adapter (ADR-003)
│       │   │   ├── profile_manager.py  ← CLAUDE_CONFIG_DIR setup
│       │   │   ├── fixture_copy.py     ← git worktree / cp -r
│       │   │   └── capture.py          ← JSONL + hook log capture
│       │   ├── grader/
│       │   │   ├── robot_runner.py     ← subprocess `robot`
│       │   │   ├── criteria_impl.py    ← concrete SuccessCriterion impls
│       │   │   └── lint.py             ← ruff / robotidy wrappers
│       │   ├── persistence/
│       │   │   ├── sqlite_repo.py      ← scorecards, longitudinal series
│       │   │   ├── parquet_store.py    ← metrics dataframes
│       │   │   └── artifact_store.py   ← run dirs
│       │   ├── reporting/
│       │   │   ├── html_renderer.py    ← Jinja2 templates
│       │   │   ├── json_renderer.py
│       │   │   └── templates/          ← .html.j2 files
│       │   └── ci/
│       │       ├── gh_annotations.py   ← ::error::, ::warning::
│       │       └── pr_comment.py
│       │
│       └── config/
│           ├── settings.py             ← pydantic-settings
│           └── logging.py
│
├── tasks/                              ← task bank YAML (data, not code)
│   ├── narrow/
│   ├── realistic/
│   └── adversarial/
│
├── fixtures/                           ← submodules or git-pinned refs
│   ├── sut-login-app/
│   ├── sut-selenium-legacy/
│   └── sut-rf-library-dev/
│
├── profiles/                           ← CLAUDE_CONFIG_DIR templates
│   ├── control/
│   └── treatment/                      ← generated from root skills/ via build step
│
├── runs/                               ← gitignored; one dir per cell
│   └── .gitkeep
│
├── reports/                            ← gitignored; generated scorecards
│   └── .gitkeep
│
└── tests/                              ← (not created in this design task, but layout)
    ├── unit/
    ├── integration/
    └── fixtures/                       ← synthetic JSONL for parser tests
```

### 5.1 Package Metadata (conceptual — `eval/pyproject.toml`)

```toml
[project]
name = "rf-agentskills-eval"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "typer>=0.12",
  "polars>=0.20",
  "scipy>=1.12",
  "numpy>=1.26",
  "pyyaml>=6.0",
  "jinja2>=3.1",
  "robotframework>=7.0",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-cov", "ruff", "mypy"]

[project.scripts]
rf-eval = "rf_agentskills_eval.infrastructure.cli.main:app"

[tool.uv]
package = true
```

### 5.2 Integration With Existing Repo

- The evaluation subsystem **consumes** `skills/` (the canonical source) via the
  existing `scripts/sync-skills.sh` pipeline — `profiles/treatment/` is populated from
  `skills/` at harness-init time.
- The MCP server (`plugins/rf-agentskills/servers/rf-tools-server.py`) is **not** a
  dependency of the harness. The harness evaluates skills via session observation,
  not via tool invocation.
- Drift detection (`scripts/check-drift.sh`) runs independently of the eval harness.
- CI adds a new `eval` job (ADR-005) alongside the existing `validate-plugin` job.

---

## 6. Key Cross-Cutting Concerns

### 6.1 Reproducibility
- Every `RunBatch` records an `EnvironmentSnapshot` (CC version, model, RF version, seed).
- Fixtures pinned by SHA; tasks versioned by filename + content hash.
- Metric implementations versioned in `catalog.py` — changing a metric bumps its ID.

### 6.2 Idempotency
- Parsing, metric computation, and scoring are pure functions over run artifacts.
- Re-running `compute_scorecard` on the same run dir yields the same scorecard.

### 6.3 Observability
- Domain events are logged to structured JSON logs for traceability.
- CI integration emits GH Actions annotations (`::error::`, `::notice::`).

### 6.4 Cost Control
- N=8 replicates default; configurable per tier.
- Max turns and wall-clock timeouts enforced at the Skill Invocation layer.
- CI schedule avoids running the full bundle on every PR; PRs get a narrow subset (ADR-005).

---

## 7. Non-Goals

- No real-time dashboard (batch reports only).
- No LLM-as-judge scoring (ADR-004 chooses deterministic grader + telemetry metrics).
- No multi-user generalization of scorecards (the eval measures *this* project's tasks).
- No cross-agent portability (evaluates Claude Code specifically; other agents out of scope).

---

## 8. See Also

- `adr/ADR-001-uv-dependency-management.md`
- `adr/ADR-002-ddd-bounded-contexts.md`
- `adr/ADR-003-skill-invocation-strategy.md`
- `adr/ADR-004-scoring-model.md`
- `adr/ADR-005-ci-integration.md`
- `adr/ADR-006-result-persistence.md`
- `docs/ci/claude-code-extension-quality-evaluation.md`
- `docs/ci/rf-agentskills-eval-implementation-plan.md`
- `docs/skill-architecture-review.md`
