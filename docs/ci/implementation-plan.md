# Implementation Plan — CI-Based Robot Framework Agent Skills Evaluation

**Target repository:** `robotframework-agentskills`
**Companion documents:**
- `docs/ci/claude-code-extension-quality-evaluation.md` (motivating research)
- `docs/ci/rf-agentskills-eval-implementation-plan.md` (domain-level plan)
- `docs/ci/architecture/adr/*` (DDD/ADRs — authored in parallel; placeholders referenced here)
- `docs/skill-architecture-review.md` (triple-channel skill layout)

**Status:** Planning only. No source files, no workflow files, no scripts produced by this document.

---

## 1. Executive Summary

### Goal
Deliver a CI-gated, reproducible evaluation harness that grades every skill in `robotframework-agentskills` on a task bank of Robot Framework engineering scenarios, emits per-skill scorecards, and blocks PRs that regress primary quality metrics.

### Success Criteria
1. A single GitHub Actions workflow runs per-skill evaluations in a matrix and reports to each PR.
2. Every skill has at least 3 narrow tasks + pinned fixture + grader criteria.
3. Primary metrics (first-run test pass %, execution-before-completion, user-interrupts per 1K, convention-violation rate) are computed deterministically from captured session artefacts.
4. Scorecards are produced as HTML + JSON; historical trends persisted as an append-only JSONL artefact in a dedicated branch/bucket.
5. Harness is driven by `uv` end-to-end — a fresh clone + `uv sync` + `uv run rf-skill-eval run` reproduces CI locally.
6. Regression gate blocks merges when any primary metric moves beyond its baseline tolerance.

### Timeline Estimate
~6 calendar weeks (part-time, one engineer). Phase 0–2 are bootstrappable in ~2 weeks; Phases 3–5 are the productionisation tail.

| Phase | Weeks | Exit state |
|---|---|---|
| 0 — Foundations | 0.5 | uv project lives in `eval/`, lint+type clean |
| 1 — Harness core | 1.0 | One skill invoked locally, artefacts captured |
| 2 — Scoring | 1.5 | Deterministic + rubric metrics green on fixtures |
| 3 — CI integration | 1.0 | Matrix workflow posts PR comment |
| 4 — Reporting & persistence | 1.0 | HTML + trend artefact published |
| 5 — Rollout | 1.0 | All 11 skills onboarded with baselines |

### Non-goals for v1
See [Out of Scope](#out-of-scope).

---

## 2. Global Assumptions

1. The eval harness lives in a new top-level directory `eval/` inside this repo (does **not** pollute root; aligns with the project rule "never save working files to the root folder").
2. `uv` (>= 0.4) is the canonical Python toolchain. No `pip`, no `poetry`, no `hatch` in runtime commands.
3. Python version pin: **3.12** (matches Anthropic's stated support; compatible with `robotframework>=7.0`).
4. The DDD work in `docs/ci/architecture/` is authoritative once landed. This plan uses placeholder bounded-context names (see §3) that can be renamed without churn when ADRs land.
5. Skills remain single-source-of-truth at repo root `skills/`. The harness consumes skills from there, never from a distribution channel.
6. The harness never writes to `~/.claude/`. All session capture targets are relative to the run directory.
7. Claude Code headless invocations go through the `claude -p` CLI (stream-json output). Where unavailable, a recorded-transcript replay mode is used for CI determinism (see ADR placeholder below).

---

## 3. Bounded Contexts (Placeholder, aligns with forthcoming ADRs)

Context names and responsibilities. Directory names are provisional — DDD ADRs will finalise. Each context maps to a package under `eval/src/rf_skill_eval/`.

| Context | Package | Responsibility |
|---|---|---|
| **Skill Catalog** | `catalog/` | Enumerate skills, resolve their scripts + references, expose a stable `Skill` aggregate |
| **Scenario Bank** | `scenarios/` | Load/validate task YAMLs, manage fixture git pins, copy fixtures per run |
| **Execution** | `execution/` | Drive Claude Code (or replay), capture artefacts, orchestrate A/B arms |
| **Telemetry** | `telemetry/` | Parse session JSONLs + hook logs → tidy dataframe |
| **Grading** | `grading/` | Deterministic criteria (robot_pass, lint, file_exists, …) |
| **Scoring** | `scoring/` | Combine telemetry + grading into per-metric scores, rubrics, judge |
| **Reporting** | `reporting/` | HTML/JSON/MD scorecards, PR comment renderer |
| **Persistence** | `persistence/` | Append-only trend log, baselines DB, regression gate |
| **Shared Kernel** | `kernel/` | `Run`, `Task`, `Arm`, `Metric`, domain events |

Context dependencies form a DAG: `catalog, scenarios → execution → telemetry, grading → scoring → reporting, persistence`. No upward dependencies permitted.

Open ADR placeholders the plan depends on (to be filled by the parallel DDD agent):
- **ADR-001** Bounded-context boundaries and package layout
- **ADR-002** Artefact capture format + storage layout under `runs/`
- **ADR-003** Invocation mode (live Claude vs recorded-replay) + cost controls
- **ADR-004** Scoring combination policy (weights, gate definitions)
- **ADR-005** Persistence backend for trends (JSONL-in-branch vs S3 vs Postgres)
- **ADR-006** Secrets model (API keys in CI, per-arm profile isolation)

---

## 4. Phases

Each phase section lists: **Objectives → Deliverables → Tasks (each ≤1 day) → Dependencies → Validation → uv commands → Experiments → Risks & mitigations**.

---

### Phase 0 — Foundations

**Objectives**
- Establish `eval/` as a uv-managed Python project with lint, type-check, and test gates.
- Scaffold empty bounded-context packages per §3 so downstream phases have landing spots.

**Deliverables**
- `eval/pyproject.toml` with project metadata, dependency groups (`core`, `dev`, `llm-judge`, `stats`).
- `eval/uv.lock` committed.
- `.python-version` at `3.12`.
- `eval/src/rf_skill_eval/<context>/__init__.py` for every bounded context in §3.
- Pre-commit config (`.pre-commit-config.yaml` scoped to `eval/`) running `ruff format`, `ruff check`, `mypy`.
- `eval/README.md` (stub, ≤40 lines; full docs in Phase 5).
- `eval/tests/conftest.py` + one smoke test per context package importing it.

**Tasks**
1. Create `eval/` directory; add to repository `.gitignore` rules for `eval/runs/`, `eval/reports/`, `eval/.venv/`.
2. Run `uv init --package eval --name rf-skill-eval --python 3.12` and reconcile generated files.
3. Author `pyproject.toml` with `[project]`, `[project.optional-dependencies]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`.
4. Add dependency groups (see §8 Dependency Map) via `uv add` / `uv add --group dev`.
5. Create empty context packages with module docstrings only.
6. Configure `ruff` (line-length 100, select ALL minus noisy rules, per-file ignores for tests).
7. Configure `mypy` strict for `rf_skill_eval.*`, loose for tests.
8. Author `.pre-commit-config.yaml`; install hooks in contributor docs.
9. Add `eval/tests/test_imports.py` — one test per package importing it.
10. Author `eval/README.md` with quickstart (4 uv commands).

**Dependencies** None (bootstraps everything).

**Validation / Exit Criteria**
- `cd eval && uv sync` succeeds on Python 3.12.
- `uv run ruff check .` → 0 findings.
- `uv run mypy src` → 0 errors.
- `uv run pytest` → smoke tests pass (≥1 per bounded context).
- `uv lock --check` passes in CI (to be added in Phase 3).

**uv commands to run**
```bash
uv init --package eval --name rf-skill-eval --python 3.12
uv add pydantic polars typer rich jinja2
uv add --group dev pytest pytest-cov ruff mypy pre-commit
uv add --group stats scipy numpy
uv add --group llm-judge anthropic
uv sync
uv run pre-commit install
uv run pytest -q
uv lock --check
```

**Experiments**
- Benchmark `uv sync` cold vs warm on GitHub Actions ubuntu-latest to verify caching strategy for Phase 3 (target: <20s warm).
- Confirm `polars` cold-import time (we consider `pandas` if startup cost in CI is painful; expected <300 ms).

**Risks & mitigations**
- *uv version drift between contributors* — pin uv version in CI and README (`uv self update --version=...`).
- *Global CLAUDE.md forbids root files* — confirmed: everything lives under `eval/`.
- *Parallel DDD agent renames packages later* — tasks 5–9 use only `__init__.py` scaffolding; renames are `git mv`-cheap.

---

### Phase 1 — Eval Harness Core

**Objectives**
- Build the minimum pipeline that: (a) loads a skill + task, (b) invokes Claude Code (live or replay), (c) captures artefacts, (d) parses them to a tidy dataframe.
- No scoring yet — just unbiased capture + parsing.

**Deliverables**
- `catalog/` can list all 11 skills from root `skills/` and expose `Skill.id`, `Skill.version_sha`, `Skill.scripts`, `Skill.path`.
- `scenarios/` loads YAML task definitions from `eval/tasks/` with Pydantic validation.
- `scenarios/` clones a fixture via `git worktree add` into `eval/runs/<run_id>/fixture/`.
- `execution/` drives `claude -p` in subprocess mode with `CLAUDE_CONFIG_DIR` pointing at a per-arm generated profile. Records stdout stream-json, final fixture tree, hook log slice, and Claude Code session JSONL.
- `execution/replay/` — alternative executor that reads a pre-recorded session (for CI determinism in PRs that don't need live runs).
- `telemetry/` parser turns captured session JSONL + hook log into a `polars.DataFrame` with one row per parsed event.
- CLI `rf-skill-eval run --skill <id> --task <id> --arm {control,treatment}` produces a populated `runs/<run_id>/` directory.

**Tasks**
1. Model `kernel/` primitives: `Skill`, `Task`, `Arm`, `RunId`, `Artefact`, `EventRow` (Pydantic v2 + frozen=True where safe).
2. Implement `catalog.load_skills()` scanning `skills/*/SKILL.md`, parsing YAML frontmatter.
3. Implement `scenarios.load_tasks()` with schema from prior plan §3.1, including `timeout_min`, `success_criteria`, `skill_scope`.
4. Add 3 seed tasks under `eval/tasks/narrow/` (covering: keyword-builder, libdoc-search, testcase-builder). Each pins a fixture SHA.
5. Implement `scenarios.fixtures.provision(run_id, task)` using `git worktree add` with cleanup hook.
6. Write profile generator `execution.profiles.build(arm, skill_ids)` that writes a minimal `CLAUDE.md` + symlinked `skills/` into a tmpdir.
7. Implement `execution.live.LiveExecutor` wrapping `claude -p --output-format stream-json --max-turns N --allowedTools ...` via `asyncio.create_subprocess_exec`.
8. Implement `execution.capture.ArtefactSink` that writes `stdout.jsonl`, copies session JSONL from `~/.claude/projects/<slug>/`, slices hook log, snapshots fixture tree.
9. Implement `execution.replay.ReplayExecutor` that takes a recorded artefact bundle and replays it back through the capture sink (for CI without API cost).
10. Implement `telemetry.parser.parse_session(path) -> DataFrame` producing the row schema from §6.1 below.
11. Author unit tests for each of the above using fixtures in `eval/tests/fixtures/sessions/`.
12. Wire Typer CLI entrypoint `rf-skill-eval` via `[project.scripts]` in `pyproject.toml`.

**Dependencies** Phase 0.

**Validation / Exit Criteria**
- `uv run rf-skill-eval run --skill keyword-builder --task narrow-kb-basic --arm treatment --mode replay` produces a non-empty `runs/<id>/` with all expected artefacts.
- `uv run rf-skill-eval telemetry parse runs/<id>` prints a dataframe with ≥1 tool-call row.
- Parser reaches ≥90 % line coverage on synthetic sessions + 2 real recorded sessions.
- Live mode is gated by env var `RF_SKILL_EVAL_ALLOW_LIVE=1` to avoid accidental billable runs.

**uv commands to run**
```bash
uv add pyyaml gitpython anyio
uv add --group dev pytest-asyncio hypothesis
uv run rf-skill-eval catalog list
uv run rf-skill-eval tasks list
uv run rf-skill-eval run --skill keyword-builder --task narrow-kb-basic --arm treatment --mode replay
uv run pytest -q -k telemetry
```

**Experiments**
- Compare three artefact capture approaches on a 20-minute live run: (i) streaming stdout → file; (ii) polling `~/.claude/projects/` every 2 s; (iii) hybrid. Measure artefact completeness and lag. Record findings as ADR-002.
- Prototype `git worktree add` vs `cp -r` fixture provisioning on the largest fixture; pick the faster one for >50-run batches.
- Measure parser throughput on a 5 MB session JSONL. Target: <1 s/MB on CI runner.

**Risks & mitigations**
- *Claude Code session layout changes* — centralise path resolution in one module; cover with snapshot tests.
- *Live runs are expensive and flaky in CI* — default to replay mode in CI; live mode only on opt-in labels + scheduled cron.
- *Hook logs interleave across parallel arms* — every subprocess writes to an arm-scoped log dir via env overrides; collectors key by `session_id` not timestamp.
- *YAML task drift* — task YAML is versioned; `scenarios.loader` refuses unknown fields in strict mode.

---

### Phase 2 — Scoring Implementations

**Objectives**
- Produce the metrics catalog values from parsed telemetry + grader verdicts.
- Layer scoring: deterministic first, rubric second, LLM-as-judge last (opt-in).

**Deliverables**
- `grading/` with criteria: `robot_pass`, `file_exists`, `file_contains`, `no_deprecated_keywords`, `lint_clean` (ruff + robotidy), `import_resolves`, `libdoc_generates`, `custom_python`.
- `scoring/metrics/` with one module per metric family (tool-workflow, linguistic, user-signals, RF-specific, cost). Each metric is a pure function over the telemetry dataframe.
- `scoring/rubric/` — config-driven combiner: reads `eval/config/rubric.yaml` to map metrics → primary/secondary/cost, with gate thresholds.
- `scoring/judge/` (gated on `RF_SKILL_EVAL_ENABLE_JUDGE=1`) — LLM-as-judge with fixed-temperature, pinned model, and cached outputs keyed by (task, arm, run_id).
- End-to-end `rf-skill-eval score <run-dir>` produces a `scorecard.json`.

**Tasks**
1. Implement grader base class + registry; port the 8 criterion types listed in prior plan §4.4.
2. Add a `robot --outputdir` runner with subprocess timeout + stdout/stderr capture.
3. Implement RF-specific metrics: `first_run_test_pass_pct`, `executed_before_complete`, `keyword_doc_lookup_rate`, `library_import_first_try_ok_pct`, `keyword_naming_convention_pct`, `section_order_violations_per_file`, `resource_file_extraction_appropriate`.
4. Implement generic metrics: `read_edit_ratio`, `edits_without_prior_read_pct`, `write_share_of_mutations_pct`, `repeated_edit_burst_count`, `reasoning_loops_per_1k`, `simplest_rate_per_1k`, `user_interrupts_per_1k`, `user_corrections_per_task`, `rf_mcp_calls_per_task`.
5. Implement cost metrics: `input_tokens_per_task`, `output_tokens_per_task`, `cache_read_tokens_per_task`, `turns_to_success`, `time_to_success_min`.
6. Design `eval/config/rubric.yaml` with primary/secondary/cost sections + per-skill overrides.
7. Implement rubric combiner: loads config, evaluates per-metric arm comparison (control vs treatment) using stubs for stats (full stats in Phase 4).
8. Design LLM-as-judge prompt template (stored under `eval/prompts/judge/`) that grades transcripts on a fixed rubric (autonomy, convention adherence, execution verification).
9. Implement judge caller with retries, deterministic sampling (`temperature=0.0`), token budget ceiling per task, and disk cache.
10. Unit test each metric with property-based tests (hypothesis) where ratios/percentages have well-defined edge cases.
11. Integration test: fixture bundle in `eval/tests/fixtures/bundle-A/` with known expected metric values; assert the scorer reproduces them exactly.

**Dependencies** Phase 1 telemetry parser.

**Validation / Exit Criteria**
- `uv run rf-skill-eval score eval/tests/fixtures/bundle-A/run-001` produces the checked-in expected `scorecard.json` (golden-file test).
- Judge cache layer verified to return the cached verdict on the second invocation without a network call.
- `rf-skill-eval score --mode deterministic-only` runs with zero API calls.

**uv commands to run**
```bash
uv add robotframework robotframework-tidy ruff-api
uv add --group llm-judge tenacity anthropic
uv run rf-skill-eval metrics list
uv run rf-skill-eval score eval/tests/fixtures/bundle-A/run-001 --mode deterministic-only
uv run pytest -q tests/scoring
```

**Experiments**
- Measure inter-run variance on the deterministic metrics for a single task with N=10 replicates to set reasonable tolerance bands.
- Pilot the LLM judge on 20 tasks and compute Cohen's κ against a manually labelled set to decide whether to enable it as a gate metric or keep advisory.
- Benchmark `polars` vs `pandas` group-by operations on a 100-run dataframe.

**Risks & mitigations**
- *LLM judge drift* — pin model + version; snapshot judge outputs per run in artefacts; gate behind opt-in flag.
- *Metric over-fitting* — primary gate metrics must be grounded in external reality (grader), never in assistant-self-reports.
- *Convention checker false positives* — seed the convention rules from `skills/robotframework-conventions/` references so skills and eval share a single definition.
- *Cost explosion* — enforce `max_tokens` cap per judge call; warn if aggregate cost per run-batch exceeds `RF_SKILL_EVAL_BUDGET_USD`.

---

### Phase 3 — CI Integration

**Objectives**
- Run the harness in GitHub Actions for every PR touching `skills/`, `scripts/` (per-skill), `eval/`, or the workflow itself.
- Matrix the workflow across skills so failures localise quickly.
- Post a PR comment summarising deltas vs main baseline.

**Deliverables**
- `.github/workflows/skill-evaluation.yml` with jobs: `lint`, `type`, `test`, `eval-matrix`, `summarize-pr`.
- uv caching via `astral-sh/setup-uv@v3` + `uv.lock` key.
- Artefact uploads: `runs/<run_id>/`, `scorecard.json`, `scorecard.html`.
- PR comment renderer that diffs current PR scorecards against the latest `main` baseline stored in the `eval-baselines` branch.
- Concurrency group on `${{ github.ref }}` to cancel superseded runs.
- Scheduled workflow (`cron: '0 6 * * 1'`) running the full live eval on `main` against the latest Claude Code release.

**Phase 3 prerequisite (one-time setup)**
0a. Run `claude setup-token` locally (OAuth flow; produces a long-lived
    `sk-ant-oat01-…` token valid ~1 year). Alternative path:
    `claude /install-github-app` wizard → "Create a long-lived token
    with your Claude subscription".
0b. Store the token as a GitHub repo secret named `CLAUDE_CODE_OAUTH_TOKEN`
    (environment-scoped where possible; never committed).
0c. Verify branch protection on `main` is active so no unreviewed workflow
    change can exfiltrate the secret.
0d. Confirm the repo's fork-PR secret policy is at GitHub default (no
    secrets to fork-triggered runs) — this is the default; no action
    needed unless overridden.

**Tasks**
1. Draft workflow structure (jobs, matrix, triggers) — document design in `docs/ci/ci-design-notes.md` (not a workflow file — still planning).
2. Decide matrix dimensions: `{skill, arm, mode}` where `mode=replay` for PRs, `mode=live` for scheduled cron only.
3. Enumerate path filters for `on.pull_request.paths` so eval only runs on skill/harness changes.
4. Design `summarize-pr` job that downloads all matrix artefacts, runs `rf-skill-eval summarize`, posts comment via `actions/github-script`.
5. Design baseline-fetch step that checks out the `eval-baselines` branch to `/tmp/baselines/` and passes it to the summariser.
6. Define secret injection — **primary:** `CLAUDE_CODE_OAUTH_TOKEN` (subscription-based, used by default for maintainer-run CI via `anthropics/claude-code-action@v1`); **fallback:** `ANTHROPIC_API_KEY` gated behind a `workflow_dispatch` input (e.g. `auth_mode: oauth|api_key`) for fork-PR / budget-capped runs; `GITHUB_TOKEN` for PR comments. See ADR-005 "Authentication".
6a. Design the workflow-input toggle that selects OAuth vs API-key auth and passes the correct secret through to the `execute` job's `env:` block.
6b. Write the per-job invocation using `anthropics/claude-code-action@v1`:
```yaml
- uses: anthropics/claude-code-action@v1
  with:
    claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    claude_args: "--max-turns 5 --model claude-opus-4-6"
```
7. Define retention: 14 days for PR artefacts, 90 days for scheduled artefacts.
8. Add `uv lock --check` step to catch lockfile drift.
9. Plan `concurrency` + `timeout-minutes` tuning (target PR run: ≤8 min; scheduled: ≤90 min). **Under the OAuth path, cap `strategy.max-parallel` to 1–2 so concurrent `claude -p` subprocesses do not exhaust the shared 5-hour subscription window.** API-key path may raise this to 8.
9a. Schedule the weekly canary off-hours (`cron: '0 3 * * 1'`, 03:00 UTC Monday) to avoid colliding with the maintainer's interactive Claude Code usage windows.
9b. Add a **calendar-driven annual token-rotation reminder** (e.g. GH issue auto-opened ~11 months after last rotation) and a workflow-start token-presence/expiry check (via `npx @claude-flow/cli@latest doctor` or an equivalent check inside the `install-claude-code` composite action) that fails early if the token is missing or near expiry.
10. Document local-reproduction recipe: `act` command or plain shell script mirroring the matrix job for one skill.

**Dependencies** Phases 0–2.

**Validation / Exit Criteria**
- On a test PR, the matrix runs green for all skills in replay mode in ≤8 min.
- PR comment appears within 30 s of matrix completion and shows per-skill verdicts + links to HTML scorecards.
- Scheduled run on main writes a trend row to `eval-baselines` branch.
- Cold uv cache: ≤60 s setup; warm: ≤20 s.

**uv commands to run** (invoked inside CI jobs)
```bash
uv sync --frozen --no-dev --group stats
uv run --no-sync rf-skill-eval run --skill ${{ matrix.skill }} --arm ${{ matrix.arm }} --mode ${{ matrix.mode }}
uv run --no-sync rf-skill-eval score runs/${{ github.run_id }}
uv run --no-sync rf-skill-eval summarize --baselines /tmp/baselines --out pr-comment.md
uv lock --check
```

**Experiments**
- Profile a full PR matrix run to identify slowest 3 steps; tune caching accordingly.
- Compare `astral-sh/setup-uv@v3` cache hit rate vs manual `actions/cache` on `~/.cache/uv`.
- A/B `ubuntu-latest` vs `ubuntu-24.04-arm` for cost-performance.

**Risks & mitigations**
- *Flaky replays* — every replay artefact bundle is checksum-pinned; harness refuses to run if checksums mismatch.
- *PR comment spam* — summariser edits the existing bot comment instead of appending new ones (find-by-marker pattern).
- *Secret leakage* — auth secret (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`) scoped to the `execute` job only; the API-key fallback is additionally gated behind `workflow_dispatch` / scheduled events; fork PRs never receive secrets (GH default, deliberately not overridden). See ADR-005 "Security".
- *Subscription rate-limit exhaustion* — under the OAuth path, the 5-hour window is shared with the maintainer's interactive sessions. Mitigated by `max-parallel: 1–2` on the matrix, off-hours canary scheduling (`0 3 * * 1`), narrow PR-tier scoping, and the API-key fallback toggle for overflow runs.
- *OAuth token expiry* — ~1-year validity means silent breakage if not rotated. Mitigated by an annual calendar reminder (auto-opened GH issue) plus a token-presence/expiry check at workflow start via `doctor` (or equivalent in the `install-claude-code` composite action) that fails fast.
- *OAuth token compromise* — long-lived and user-account-bound, so blast radius is higher than a scoped API key. Mitigated by repo-secret scope (environment-scoped where possible), `main` branch protection, fork-PR secret isolation, annual rotation, and documented revocation procedure (revoke via Anthropic console → rotate repo secret).
- *Matrix blow-up* — start with 3 representative skills; ramp in Phase 5.

---

### Phase 4 — Reporting & Persistence

**Objectives**
- Upgrade scorecards from JSON-only to HTML + Markdown.
- Persist every run into a longitudinal JSONL trend log with a published schema.
- Add regression gate that compares current primary metrics against a rolling baseline.

**Deliverables**
- `reporting/html/templates/` — Jinja2 templates for `skill.html`, `bundle.html`, `index.html`.
- `reporting/markdown/` — compact PR-comment renderer + full run-report renderer.
- `persistence/trend_log.py` — appends one JSONL row per run to the `eval-baselines` branch (or S3 bucket, per ADR-005).
- `persistence/baselines.py` — computes rolling 30-day baselines per (skill, metric) and detects >2σ movement.
- `scoring/gate.py` — pass/fail decision combining primary gate, cost cap, regression check.
- JSON Schema document: `eval/schemas/scorecard.schema.json` + `eval/schemas/trend-row.schema.json`, both validated in CI.

**Tasks**
1. Define `scorecard.schema.json` covering: run metadata, skill identity, per-metric arm comparison, verdict, artefact pointers.
2. Define `trend-row.schema.json` — flat row with `run_id`, `skill_id`, `metric_id`, `arm`, `value`, `timestamp`, `cc_version`, `model`.
3. Implement HTML template per §7.1 of the prior plan: header / verdict / primary / secondary / per-task / failure-gallery / cost / raw-data-link.
4. Implement `reporting.markdown.pr_comment_renderer()` with a stable HTML comment marker for in-place editing.
5. Implement `reporting.index.build_index(runs_dir)` producing `reports/index.html` that links every run.
6. Implement `persistence.trend_log.append()` using a sparse checkout of the `eval-baselines` branch; push with rebase-on-fail retry.
7. Implement `persistence.baselines.rolling(skill_id, metric_id, days=30)` returning `(mean, sigma, n)`.
8. Implement `scoring.gate.evaluate(scorecard, baseline)` returning `Verdict` with reason codes.
9. Implement JSON-Schema validation step in the CLI: `rf-skill-eval validate <path>`.
10. Snapshot-test the HTML renderer with golden HTML files (whitespace-normalised).
11. Snapshot-test the PR markdown renderer.

**Dependencies** Phases 2, 3.

**Validation / Exit Criteria**
- Running `rf-skill-eval report <run-dir>` generates `scorecard.html`, `scorecard.md`, `scorecard.json` all conforming to schemas.
- The index page lists every run with clickable verdicts.
- Trend log branch receives an appended row at the end of every scheduled run.
- Gate blocks a synthetic regression (>2σ drop on a primary metric) with a clear, single-line reason.
- JSON Schemas ship under `eval/schemas/` and have CI validation.

**uv commands to run**
```bash
uv add jinja2 markupsafe jsonschema
uv add --group dev dirty-equals
uv run rf-skill-eval report runs/<id>
uv run rf-skill-eval validate runs/<id>/scorecard.json
uv run rf-skill-eval gate --run runs/<id> --baselines /tmp/baselines
```

**Experiments**
- Measure HTML render time for 500 runs (target: <2 s).
- Compare JSONL-branch vs SQLite-in-git for trend storage — pick based on read patterns for dashboarding (ADR-005).
- Prototype Datasette pointed at the trend JSONL as a local explorer (dev-only, not in CI).

**Risks & mitigations**
- *Branch push races* in trend log — rebase-on-fail + capped retries; fall back to opening an auto-PR if rebase fails 5×.
- *Schema evolution* — include `schema_version` on every row; migrator utility lives in `persistence/migrations/`.
- *HTML bloat* — cap embedded transcripts; link externally for full captures.
- *Regression false positives* — require 2 consecutive out-of-band runs before gating; first incident is a warning.

---

### Phase 5 — Rollout

**Objectives**
- Onboard all 11 skills with baselines, dashboards, and CODEOWNERS-level accountability.
- Publish contributor docs so future skills ship with eval coverage on day one.

**Deliverables**
- Per-skill baseline (30-day rolling mean + σ) committed to the `eval-baselines` branch.
- Per-skill task bank at or above: 3 narrow, 1 realistic, 1 adversarial.
- `docs/ci/adding-a-skill.md` — step-by-step: new skill → new tasks → gate tuning → merge.
- `docs/ci/runbook.md` — on-call style: red gate triage, flaky run handling, judge disable.
- `CODEOWNERS` entries for `eval/` and `skills/**/SKILL.md`.

**Tasks**
1. Ordered rollout plan: start with `libdoc-search` and `keyword-builder` (highest traffic); end with `results-analysis` (lowest maturity).
2. For each skill: author 3 narrow tasks + 1 realistic + 1 adversarial; commit with fixture pins.
3. Run 10-replicate baseline capture per skill on scheduled runner; commit baselines.
4. Tune per-skill rubric thresholds in `rubric.yaml` based on observed variance.
5. Author `adding-a-skill.md` — checklist form with copy-pasteable YAML stubs.
6. Author `runbook.md` with 5 named incident classes: flaky replay, budget blown, model-drift red gate, fixture-rot red gate, hook-log missing.
7. Enable the gate on PRs (move from warn-only to fail-on-red). Behind a workflow input toggle for the first 2 weeks.
8. Add README badge: link to latest index.html scorecard page.
9. Celebration: write RoboCon-style blog post referencing real numbers.

**Dependencies** Phases 0–4.

**Validation / Exit Criteria**
- All 11 skills have ≥5 tasks and committed baselines.
- Gate is enabled (not warn-only) on protected branches.
- `docs/ci/adding-a-skill.md` walks a new contributor through adding a skill in ≤30 min.
- Runbook covers every incident class observed during rollout.

**uv commands to run**
```bash
uv run rf-skill-eval bootstrap --skill <id> --replicates 10 --mode live
uv run rf-skill-eval baselines rebuild --skill <id>
uv run rf-skill-eval gate --dry-run
uv run rf-skill-eval stats summary --skill <id> --last 30d
```

**Experiments**
- Per-skill sensitivity: how many replicates are needed for effect sizes ≥0.33 to become significant? Use this to right-size replication.
- Compare gating policies (strict Cliff's δ vs tolerance-banded rolling baseline); pick the lower-FPR policy.
- Measure observer-induced drift: does simply shipping the eval harness cause skills to improve (via the "canary" effect)?

**Risks & mitigations**
- *Baseline bootstrapping is expensive* — schedule over multiple nights; cap concurrency at 4 live runs.
- *Skill authors resist gating* — enable as warn-only first; share scorecards in draft PRs as education.
- *Fixture rot* — weekly scheduled job re-greens baselines; if a fixture's underlying SUT changes, bump pin + bump baseline.

---

## 5. Testing Strategy

### 5.1 Test Levels
| Level | Location | Scope | Runs in |
|---|---|---|---|
| Unit | `eval/tests/unit/<context>/` | Single module, no I/O | pre-commit, PR `test` job |
| Contract | `eval/tests/contract/` | Pydantic models against fixture YAMLs/JSONs | PR `test` job |
| Integration | `eval/tests/integration/` | Bounded-context adapters (parser↔fixture, grader↔robot) | PR `test` job |
| End-to-end (replay) | `eval/tests/e2e_replay/` | Full pipeline with recorded sessions | PR `eval-matrix` job |
| End-to-end (live) | `eval/tests/e2e_live/` | Real `claude -p` invocation | Scheduled only, opt-in |

### 5.2 How tests call into bounded contexts
- Tests import **only from the public API** of each context (`from rf_skill_eval.scoring import compute_metrics`). Private modules are `_prefixed` and not re-exported.
- Each context ships a `testing/` submodule with fakes: e.g. `execution.testing.InMemoryExecutor`, `persistence.testing.FakeTrendLog`. Integration tests wire these fakes.
- Property-based tests (`hypothesis`) target pure-function metrics. Synthetic session generators live in `telemetry/testing/`.
- Golden tests live under `eval/tests/golden/<context>/` and are refreshed via `uv run pytest --regen-goldens`.

### 5.3 Coverage Targets
- Unit coverage ≥90 % for `scoring/`, `telemetry/`, `grading/`.
- End-to-end coverage: every primary metric exercised in at least one replay e2e test.
- No coverage target on `execution/live` (exercised only in scheduled runs).

### 5.4 Data fixtures
- `eval/tests/fixtures/sessions/` — hand-curated session JSONLs (≤10 KB each).
- `eval/tests/fixtures/runs/` — two full run bundles (one with skill, one without) for golden-scorecard testing.
- `eval/tests/fixtures/rf-projects/` — minimal RF projects used by the grader.

---

## 6. Schemas & Row Model (Forward Reference)

### 6.1 Telemetry row (Phase 1 output)
Columns (Polars dtypes):
- `run_id: Utf8`, `session_id: Utf8`, `turn_idx: Int32`, `ts: Datetime[ms]`, `event_kind: Utf8` (∈ {tool_use, tool_result, user, assistant, thinking, summary}), `tool_name: Utf8 | null`, `file_path: Utf8 | null`, `result_ok: Boolean | null`, `bytes: Int64 | null`, `text_len: Int64 | null`, `input_tokens: Int64 | null`, `output_tokens: Int64 | null`.

### 6.2 Scorecard schema (Phase 4)
See `eval/schemas/scorecard.schema.json` (to be authored in Phase 4). High-level keys: `run_id`, `skill`, `arms`, `metrics: {primary[], secondary[], cost[]}`, `verdict`, `gate_reasons[]`, `artefacts`.

### 6.3 Trend-row schema (Phase 4)
`{run_id, timestamp, skill_id, skill_version_sha, arm, metric_id, value, cc_version, model, baseline_mean, baseline_sigma, deviation_sigma}` — one row per (run, skill, metric, arm).

---

## 7. Dependency Map

Listed with justification and the phase that first needs them. Installed via `uv add` with appropriate groups.

### 7.1 Runtime core (default)
| Package | Why | First used |
|---|---|---|
| `pydantic>=2.7` | Domain models, schema validation | Phase 1 |
| `polars>=0.20` | Telemetry dataframe ops; faster cold-start than pandas | Phase 1 |
| `typer>=0.12` | CLI (single source for all subcommands) | Phase 0 |
| `rich>=13` | Local CLI pretty-printing; imported by typer | Phase 0 |
| `jinja2>=3.1` | HTML + MD report rendering | Phase 4 |
| `pyyaml>=6` | Task YAML loading | Phase 1 |
| `gitpython>=3.1` | Fixture worktree management | Phase 1 |
| `anyio>=4` | Async subprocess driver | Phase 1 |
| `jsonschema>=4` | Validate emitted JSON artefacts | Phase 4 |

### 7.2 Stats group (`--group stats`)
| Package | Why |
|---|---|
| `scipy>=1.13` | Mann-Whitney U |
| `numpy>=1.26` | Bootstrap CIs, array ops |

### 7.3 LLM-judge group (`--group llm-judge`, opt-in)
| Package | Why |
|---|---|
| `anthropic>=0.30` | Judge calls |
| `tenacity>=8` | Retries with backoff |

### 7.4 Grader group (runtime, but heavy)
| Package | Why |
|---|---|
| `robotframework>=7.0` | `robot` runner + libdoc | Phase 2 |
| `robotframework-tidy>=4` | Style lint for `lint_clean` criterion | Phase 2 |

### 7.5 Dev group (`--group dev`)
`pytest`, `pytest-cov`, `pytest-asyncio`, `hypothesis`, `ruff`, `mypy`, `pre-commit`, `dirty-equals`.

### 7.6 GitHub Actions dependencies (Phase 3, not Python)
| Action | Why | First used |
|---|---|---|
| `anthropics/claude-code-action@v1` | Auth + invocation wrapper for `claude -p` in GH Actions; consumes `CLAUDE_CODE_OAUTH_TOKEN` (primary) or `ANTHROPIC_API_KEY` (fallback). See ADR-005 "Authentication". | Phase 3 |
| `astral-sh/setup-uv@v3` | uv install + cache. | Phase 3 |
| `actions/checkout@v5` | Source + submodule checkout. | Phase 3 |
| `actions/upload-artifact@v4` | Run-dir + scorecard persistence. | Phase 3 |
| `actions/github-script` | PR-comment renderer. | Phase 3 |

Explicitly **not** depended on:
- `pandas` (replaced by polars for cold-start reasons).
- `poetry` / `hatch` / `pip-tools` — uv only.
- `requests` (stdlib `urllib` via `anthropic` client is sufficient).
- `httpx` unless anthropic SDK transitively requires it.

---

## 8. Open Questions (Need User Input)

1. **Live-run budget.** What monthly USD cap should the scheduled live eval respect? The plan assumes `RF_SKILL_EVAL_BUDGET_USD` but needs a number.
2. **Trend storage backend.** JSONL-in-branch (free, simple, hits git limits at ~100K rows) vs S3/R2 bucket (paid, scalable) vs Postgres (flexible query, ops burden). ADR-005 decision needed before Phase 4 ends.
3. **Gate strictness at rollout.** Start warn-only for 2 weeks, then enforce — confirm timeline OK?
4. **Judge enablement.** Do we ship v1 with LLM-as-judge as an advisory-only signal or hold it until v1.1 after Cohen's κ passes threshold?
5. **Who owns baselines?** `CODEOWNERS` for `eval-baselines` branch — single maintainer or the skill author group?
6. **Claude Code pinning.** Should the harness pin a specific `@anthropic-ai/claude-code` CLI version, or float to latest? Pinning gives repeatability; floating catches upstream regressions earlier.
7. **Python version policy.** 3.12 today — upgrade cadence policy?
8. **Do we publish the harness as its own pypi package?** Current plan keeps it inside the repo under `eval/`. Extracting is a Phase 6+ decision.
9. **Fixture ownership & licensing.** The realistic and adversarial fixtures may need to ship with the repo — are all fixtures we plan to use under compatible licences?
10. **Matrix shape at launch.** 11 skills × 2 arms × 2 modes = 44 jobs. GitHub free-tier concurrency may throttle — do we start with a curated subset?

---

## 9. Out of Scope

The following are deliberately excluded from v1. Each should get a follow-up ticket if pursued later.

1. Real-time dashboards / Grafana / Datadog integrations. Weekly batch HTML is sufficient.
2. Multi-user generalisation. Scorecards reflect this repo's tasks only.
3. Adversarial fuzzing of skills (e.g. prompt-injection resilience). Separate security workstream.
4. Cross-LLM comparisons (evaluating the same skills on non-Claude models).
5. Hook instrumentation authoring — we *consume* hook logs; authoring new hooks is a separate plan.
6. Automated fixture migration when upstream SUTs break. Manual bump.
7. UI for task authoring. YAML by hand is fine at this scale.
8. Integration with `rf-mcp` as a delivery mechanism. `rf-mcp` is infrastructure the skills use; it is not evaluated here.
9. Evaluation of the VS Code extension vs plugin distribution channels. The harness evaluates skill *content*, not packaging.
10. Python <3.12 support.
11. Windows runners — Linux + macOS only at v1. Windows can be added when a specific need emerges.
12. Generative test creation (LLM-synthesised task bank). Human-curated only.

---

## 10. Traceability

| Phase | ADR placeholders | Prior plan section | This repo artefact |
|---|---|---|---|
| 0 | — | — | `eval/` scaffold |
| 1 | ADR-001, ADR-002, ADR-003, ADR-006 | §1, §2, §4 | `catalog/`, `scenarios/`, `execution/`, `telemetry/` |
| 2 | ADR-004 | §5, §6 | `grading/`, `scoring/` |
| 3 | ADR-003, ADR-006 | §4.2, §4.3 | `.github/workflows/skill-evaluation.yml` |
| 4 | ADR-005 | §7 | `reporting/`, `persistence/`, `eval/schemas/` |
| 5 | — | §8 | `docs/ci/adding-a-skill.md`, `docs/ci/runbook.md` |

---

## 11. Quick-Start Command Reference (for later, once implemented)

```bash
# Initial clone-to-running flow
cd eval
uv sync
uv run rf-skill-eval catalog list
uv run rf-skill-eval tasks list
uv run rf-skill-eval run --skill keyword-builder --task narrow-kb-basic --arm treatment --mode replay
uv run rf-skill-eval score runs/<id>
uv run rf-skill-eval report runs/<id>
open runs/<id>/scorecard.html

# CI-equivalent pipeline
uv sync --frozen --no-dev --group stats
uv run --no-sync rf-skill-eval ci --pr ${GITHUB_PR_NUMBER}

# Maintenance
uv run rf-skill-eval baselines rebuild --skill <id>
uv run rf-skill-eval validate runs/<id>/scorecard.json
uv lock --check
```

---

*End of plan. This document is updated as ADRs land. Each phase gate requires a checkbox PR linking to its exit-criteria evidence.*
