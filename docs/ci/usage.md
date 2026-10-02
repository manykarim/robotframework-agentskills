# Skill Evaluation Harness — Usage Guide

Primary user-facing guide for the `rf-skill-eval` harness: what it is,
how to set it up, how to run evaluations locally, and how CI uses the
same machinery on every PR.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [One-time Setup](#one-time-setup)
- [Running Evaluations](#running-evaluations)
  - [Validate before you spend anything](#validate-before-you-spend-anything)
  - [Smoke run](#smoke-run-fastest-feedback)
  - [Local narrow run](#local-narrow-run-pre-push-check)
  - [One task, one arm](#one-task-one-arm)
  - [Batches: arms × replicates](#batches-arms--replicates)
  - [Reports](#reports)
  - [Trigger evals](#trigger-evals)
  - [Baselines and the gate](#baselines-and-the-gate)
- [Understanding Reports](#understanding-reports)
- [Adding a New Task](#adding-a-new-task)
- [CI Reference](#ci-reference)
- [Model Policy](#model-policy)
- [Cost Expectations](#cost-expectations)
- [Related Documents](#related-documents)

---

## Overview

The skill evaluation harness answers a single question: **does this skill
actually improve Claude Code's behavior on Robot Framework tasks?** It
does this by driving headless Claude Code sessions against a pinned
task bank, capturing session telemetry, and grading the output with a
deterministic rubric.

Key properties:

- **Reproducible.** Same inputs → same scorecard, bit-for-bit. See
  [ADR-004](architecture/adr/ADR-004-scoring-model.md).
- **Paired arms.** Every task can run with the plugin (`treatment`) and
  without it (`baseline`), N replicates each, so reports show whether a
  skill actually helps (treatment − baseline deltas).
- **Tiered.** PR runs are narrow, treatment-only and gated against a stored
  baseline (fast, cheap). Weekly runs execute everything in both arms. See
  [ADR-005](architecture/adr/ADR-005-ci-integration.md).
- **Subscription-billed by default.** CI uses a long-lived OAuth token
  tied to the maintainer's Claude Pro/Max subscription, falling back
  to a per-token `ANTHROPIC_API_KEY` for fork PRs and overflow runs.
- **Locally reproducible.** `uv run rf-skill-eval run` on a fresh
  clone reproduces what CI does. No "works in CI, broken locally"
  drift.

For the full architecture, see
[`ddd-design.md`](architecture/ddd-design.md) and the ADRs under
[`architecture/adr/`](architecture/adr/).

---

## Prerequisites

Install these once per machine:

| Tool                | Minimum version | Notes                                   |
| ------------------- | --------------- | --------------------------------------- |
| `uv`                | 0.4             | Python toolchain manager                |
| Node.js             | 20              | Required by Claude Code CLI             |
| Claude Code CLI     | latest          | `npm i -g @anthropic-ai/claude-code`    |
| Git                 | 2.40            | Worktrees for fixture provisioning      |
| Python              | 3.12            | Installed automatically by `uv sync`    |

`robotframework>=7.0`, `robotframework-browser`, and other Python
dependencies are installed into the `eval/` project environment by
`uv sync`. No global `pip` installs are required.

Verify prerequisites:

```bash
uv --version
node --version
claude --version
git --version
```

---

## One-time Setup

These steps run once per contributor on a clean clone.

### 1. Generate a Claude Code OAuth token

```bash
claude setup-token
```

This triggers an OAuth flow in your browser. On success it prints a
token of the form `sk-ant-oat01-...` valid for roughly one year.
Copy it.

Alternative path: `claude /install-github-app` and follow the wizard's
"Create a long-lived token with your Claude subscription" option.

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and paste your OAuth token:

```dotenv
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
CLAUDE_MODEL_DEFAULT=claude-haiku-4-5-20251001
RF_SKILL_EVAL_LOG_LEVEL=INFO
```

`.env` is gitignored. Do **not** commit it.

If you do not have a Claude subscription and want to pay per token,
comment out `CLAUDE_CODE_OAUTH_TOKEN` and uncomment
`ANTHROPIC_API_KEY` instead. See [faq.md](faq.md#subscription) for
details.

### 3. Install Python dependencies

```bash
uv sync
```

This creates `.venv/` inside `eval/`, installs the harness plus all
runtime dependencies (pydantic, polars, typer, robotframework, scipy,
etc.), and pins everything to `eval/uv.lock`.

### 4. Install Playwright browsers

Browser-library fixtures need Chromium. Run:

```bash
uv run rfbrowser init
```

This fetches Chromium and its system dependencies. It can take a few
minutes on a cold cache. See
[local-testing.md](local-testing.md#rfbrowser-init-failures) for
troubleshooting.

### 5. Verify the setup

```bash
uv run rf-skill-eval doctor
```

`doctor` checks:

- `uv` version and lockfile integrity
- Python version (3.12)
- Claude Code CLI presence and version
- OAuth token presence and expiry (warns if < 30 days)
- `robotframework` importability
- `rfbrowser` Chromium install
- Fixture submodule health

A green doctor means you are ready to run evaluations.

---

## Running Evaluations

> Every command below that starts Claude sessions accepts `--max-cost-usd`.
> Use it. When the reported cost reaches the cap, no further session starts,
> the remaining runs are recorded `incomplete` (reason `budget`) and the
> command exits non-zero.

### Validate before you spend anything

```bash
uv run rf-skill-eval validate-tasks eval/tasks   # schema, model ids, skills, fixtures, gating
uv run rf-skill-eval coverage                    # every shipped skill has a narrow task + trigger set
uv run rf-skill-eval doctor --tasks-dir eval/tasks --strict   # grader tools / libraries present
uv run pytest tests/eval -q                      # harness unit tests (no API calls)
```

### Smoke run (fastest feedback)

```bash
scripts/eval-smoke.sh
```

Runs `eval/tasks/narrow/narrow-libdoc-search-01.yaml` once with
`claude-haiku-4-5-20251001` in the `treatment` arm, grades it and prints the
report.

### Local narrow run (pre-push check)

```bash
scripts/eval-local.sh
```

Lint + unit tests, then the narrow tier in the treatment arm with `--runs 3`
(and optionally the realistic tier), then a report.

### One task, one arm

```bash
uv run rf-skill-eval run \
  --task eval/tasks/narrow/narrow-libdoc-search-01.yaml \
  --arm treatment \
  --max-cost-usd 1 \
  --output eval/runs/manual-$(date +%s)
```

- `--arm` — `treatment` (the plugin as shipped: skills, hooks, subagents,
  `rf-tools`) or `baseline` (no plugin parts; everything else identical).
  `--profile control` still works as a deprecated alias of `baseline`.
- `--model` — override the task's model (see [Model Policy](#model-policy)).

### Batches: arms × replicates

```bash
uv run rf-skill-eval run-batch \
  --tasks-dir eval/tasks/narrow \
  --arms treatment,baseline \
  --runs 3 \
  --max-cost-usd 5 \
  --output eval/runs/batch-$(date +%Y%m%d)
```

- `--arms` — default `treatment` only.
- `--runs N` — replicates per task × arm (default 3), each in a fresh
  workspace.
- `--skills rf-browser,plugin` / `--tier narrow` — select tasks
  (`plugin` = bundle canaries).
- Runs are graded inline. `score-batch` re-grades an existing directory.
- A pre-dispatch estimate (tasks × arms × runs × historical mean cost from
  `eval/baselines/`) is printed; the batch is refused when it exceeds 1.5×
  the cap.
- `bench --task … --runs N` is an alias for a single-task batch that prints
  replicate statistics.

### Reports

```bash
uv run rf-skill-eval report --runs-dir eval/runs/batch-20260927 --output report.md
uv run rf-skill-eval report --runs-dir eval/runs/pr --baseline eval/baselines/narrow.json --format json --output report.json
```

Per task and arm: pass rate (runs whose gate result is `pass` / runs
attempted), outcome pass rate, incomplete runs, mean input/output tokens,
turns, duration and cost (stdev in JSON), a flaky flag (0 < pass rate < 1),
and the treatment − baseline delta computed from **outcome** checks only
("unavailable" when an arm has no runs). When the baseline arm was not run,
`--baseline` supplies its numbers from the stored file. Skipped/errored checks
are listed with reasons; process checks (e.g. "the skill was invoked") are
shown for the treatment arm only; adversarial tasks are marked non-gating.

### Trigger evals

```bash
uv run rf-skill-eval trigger --skills rf-browser,rf-selenium --split validation --max-cost-usd 2
```

Runs each query of `eval/triggers/<skill>.yaml` (default 3 times) with the
plugin staged but hooks off, `--max-turns 3`, and only the tools
`Skill,Read,Glob,Grep` *available* (`claude --tools`; in bypass mode
`--allowedTools` alone only pre-approves). Each session starts in a fresh copy
of `eval/fixtures/sut-trigger/`, a neutral Robot Framework project that imports
no test library. Reports TP/FP/TN/FN, precision, recall and accuracy per skill
for train and validation (and holdout, when selected) separately, plus the
other skills loaded for failing queries. See
[`eval/triggers/README.md`](../../eval/triggers/README.md).

| Option | Meaning |
|---|---|
| `--split train,validation,holdout2` | Comma list of `train`, `validation`, `holdout`, `holdout<N>`; a holdout name runs only that split's post-tuning queries, each reported in its own column. |
| `--concurrency 1\|2` | Queries run at once (default 1; max 2, the ADR-002 OAuth cap). |
| `--variant-root <dir>` | Stage `<dir>/plugins/rf-agentskills` instead of the shipped plugin. |
| `--listing-budget <chars>` | Set `SLASH_COMMAND_TOOL_CHAR_BUDGET` (skill-listing budget) for the sessions; default: not set, Claude Code's own budget. |
| `--output <dir>` | Also the resume key: re-running with the same directory skips finished queries. |

**Resume.** Every finished query is appended to `<output>/outcomes.jsonl`,
keyed by (variant id, model, listing budget, skill, query id, split). Re-run
the same command with the same `--output` after a crash or a budget stop: only
the missing or incomplete queries run, and `trigger-results.json` aggregates
all of them. Keep `--output` outside the repository tree (see the
contamination warning).

**Listing budget and description visibility.** Claude Code lists skill
descriptions only while they fit `context window × 4 × 1%` characters (about
8000 for Haiku 4.5; bundled skills first, then the others alphabetically;
the rest appear by name only). By default the harness leaves that budget
alone, which is what gates. To measure the 1M-context condition:

```bash
uv run rf-skill-eval trigger --split validation --listing-budget 40000 \
  --variant-root /tmp/variants/compact --concurrency 2 --max-cost-usd 7 \
  --output /tmp/evalruns/compact-val
```

- The budget is recorded as `listing_budget` in the results (`null` = default)
  and is part of the resume key, so default and `40000` batches can share one
  `--output` without mixing: the default batch writes `trigger-results.json`
  and `trigger-report.md`, a budget batch `trigger-results-budget-<N>.json`
  and `trigger-report-budget-<N>.md` (`baseline update` only reads
  `trigger-results.json`).
- If `SLASH_COMMAND_TOOL_CHAR_BUDGET` is already exported and
  `--listing-budget` is not given, the exported value is used and recorded
  (a note is printed); unset it to measure the default.
- Each run's `skill_listing` attachment in `session.jsonl` is parsed. Every
  outcome carries `visible_descriptions` (one list per run: the rf-* skills
  listed *with* their description), and the results carry a `visibility` map
  per skill: `own_visible/own_listed` (sessions of the skill's own queries)
  and `all_visible/all_listed` (every session). The report adds a
  "Description visibility" table, e.g. `| rf-results | 0/24 | 0/288 |` means
  the model saw only the name `rf-results`.

**Run isolation.** Task runs (profiles with write-capable tools) snapshot the
repository before and after the session. Files that appear outside the run's
workspace are listed in `<run>/workspace_violations.json` and the run gets an
`isolation-violation: …` error, which makes its gate result `incomplete` (not
a pass). Nothing is deleted: the file may belong to a developer or another
tool working in the repository at the same time. Trigger sessions have no
write-capable tool and skip the snapshot.

**Description variants.** Measure candidate descriptions without editing
`skills/`:

```bash
uv run python scripts/build-description-variant.py \
  --candidates openspec/changes/tune-skill-descriptions/candidates/rf-results.yaml \
  --out /tmp/variants/rf-results-it1          # prints the variant id
uv run rf-skill-eval trigger --skills rf-results --split train \
  --variant-root /tmp/variants/rf-results-it1 --concurrency 2 --max-cost-usd 2 \
  --output /tmp/evalruns/rf-results-it1
```

The variant id is a hash of every staged description (an empty candidates
file gives the shipped id); `trigger-results.json` records `variant_id` and
`variant_root`.

### Baselines and the gate

```bash
# after a weekly-equivalent run (both arms, N=3, all tiers, triggers):
uv run rf-skill-eval baseline update --from eval/runs/full --output-dir eval/baselines
# compare a PR run with the stored baseline:
uv run rf-skill-eval gate --runs-dir eval/runs/pr --baseline eval/baselines/narrow.json
uv run rf-skill-eval gate --trigger-results eval/runs/triggers/trigger-results.json
```

`gate` exits 0 (pass), 1 (fail: pass-rate drop > 1/N, mean input tokens
+30 %, incomplete runs, trigger validation accuracy down by more than one
query, cost over `--max-cost-usd`) or 3 (`rebaseline-needed` only: the task
definition, fixture or model changed, or no baseline entry exists — never a
pass). Baseline files are promoted through a reviewed PR
([`eval/baselines/README.md`](../../eval/baselines/README.md)).

---

## Understanding Reports

### Verdicts and gate results

Each grader check yields `passed`, `failed`, `skipped` (could not be
evaluated — with a reason) or `error` (grader defect). Skipped/errored checks
never count as passes. A run's gate result is `pass`, `fail` or
`incomplete`; CI treats `incomplete` as a failure. Gating checks are those
whose type equals the task's `primary_metric`, or that set `gating: true`.

The Mann-Whitney / Cliff's δ / SHIP-ITERATE-HOLD model in
[ADR-004](architecture/adr/ADR-004-scoring-model.md) remains the long-term
target; with N=3 it is underpowered, so reports show raw rates and deltas and
the gate uses the tolerances above (see the ADR-004 amendment).

---

## Adding a New Task

1. Pick a tier: `narrow/` (one skill), `realistic/` (multi-step) or
   `adversarial/` (tempts a failure mode; never gates).
2. Copy an existing task as a template and edit it (schema:
   [`eval/tasks/README.md`](../../eval/tasks/README.md)).
3. `uv run rf-skill-eval validate-tasks eval/tasks && uv run rf-skill-eval coverage`.
4. Run it once: `uv run rf-skill-eval run --task <file> --max-cost-usd 1`.

A new skill needs at least one narrow task **and** a trigger set, or
`coverage` fails and names it.

---

## CI Reference

Workflow: `.github/workflows/skill-evaluation.yml` (tiers and caps: ADR-005
amendment).

| Trigger | Jobs | Scope | Arms | N | Model | Cap |
|---|---|---|---|---|---|---|
| `pull_request` | `preflight` → `pr-eval` | narrow tasks of changed skills + `plugin` canaries (all narrow tasks when the harness changed); validation-split trigger evals when a SKILL.md `description` changed | treatment | 3 | `claude-haiku-4-5-20251001` | `PR_NARROW_CAP_USD`=10, `PR_TRIGGER_CAP_USD`=20 |
| `schedule` (Sun 04:00 UTC) | `preflight` → `full-eval` | all tiers + all trigger sets | treatment, baseline | 3 | tier defaults | 12 + 12 + 8 + 8 = $40 |
| `workflow_dispatch` | `preflight` → `full-eval` | inputs `tiers`, `arms`, `runs`, `model`, `allow_opus`, `max_cost_usd`, `triggers` | input | input | input | `max_cost_usd` per invocation |
| all | `harness-tests` | ruff, mypy, `pytest tests/eval` (no API calls) | – | – | – | – |

- The PR job gates against `eval/baselines/narrow.json` and posts one PR
  comment (report + gate result + trigger report).
- The weekly job uploads the report and a `candidate-baseline-<run>`
  artifact; a maintainer promotes it with a PR. The PR gate becomes a
  **required** check only after two weekly baselines have been recorded.
- Without credentials (fork PRs) the eval jobs are skipped and a `not-run`
  job writes "not run: no credentials" to the summary — never a passing
  result.

### Manual workflow dispatch

```bash
# Weekly-equivalent run now:
gh workflow run skill-evaluation.yml
# Only the narrow tier, treatment arm, 5 replicates:
gh workflow run skill-evaluation.yml -f tiers=narrow -f arms=treatment -f runs=5 -f max_cost_usd=10
# Opus check (manual only; needs the opt-in and a cap):
gh workflow run skill-evaluation.yml -f tiers=narrow -f model=claude-opus-5-5 -f allow_opus=true -f max_cost_usd=20
# Force API-key auth:
gh workflow run skill-evaluation.yml -f use_api_key=true
```

---

## Model Policy

| Model | Default use | Why |
| --- | --- | --- |
| `claude-haiku-4-5-20251001` | narrow tier, trigger evals, PRs, smoke, local | Cheap, fast, low variance |
| `claude-sonnet-5` | realistic and adversarial tiers | Higher fidelity for multi-step tasks |
| `claude-opus-5-5` | manual runs only, explicit opt-in | Checks a skill does not *hurt* the strongest model |

- Task YAML and trigger sets may declare Haiku or Sonnet only.
- Opus requires `--model claude-opus-5-5 --allow-opus --max-cost-usd <cap>`;
  without either flag the harness refuses to start and names the missing one.
  It never runs on PRs or the weekly schedule (≈5× Sonnet per token).
- Retired ids (`claude-haiku-4-5`, `claude-sonnet-4-6`) are rejected with a
  migration hint.

---

## Cost Expectations

Very rough per-task estimates (Haiku unless noted). Real costs vary
with prompt length and turn count.

| Scope                      | Tasks | Arms | Replicates | Est. cost (API key) | Subscription impact |
| -------------------------- | ----- | ---- | ---------- | ------------------- | ------------------- |
| Smoke                      | 1     | 1    | 1          | ~$0.005             | ~1 min of 5-hr window |
| Local narrow               | ~12   | 1    | 3          | ~$0.25              | ~15 min of 5-hr window |
| PR narrow (changed-skills) | ~4–8  | 1    | 3          | ~$0.30–0.60         | ~10 min of 5-hr window |
| Weekly (all tiers)         | ~25   | 2    | 3          | ~$6 (Sonnet: ~$30)  | ~2 hours of 5-hr window |

On the OAuth/subscription path, cost is flat as long as you stay
inside the 5-hour rolling window. On the `ANTHROPIC_API_KEY` fallback,
every token is billed. See [faq.md](faq.md#api-key-fallback) for when
to prefer which.

---

## Related Documents

- [local-testing.md](local-testing.md) — pre-push checklist and
  troubleshooting.
- [faq.md](faq.md) — common questions, rate limits, rotation.
- [architecture/ddd-design.md](architecture/ddd-design.md) — bounded
  contexts and module layout.
- [architecture/adr/ADR-004-scoring-model.md](architecture/adr/ADR-004-scoring-model.md) — scoring rubric and gate.
- [architecture/adr/ADR-005-ci-integration.md](architecture/adr/ADR-005-ci-integration.md) — workflow, auth, secrets.
- [architecture/adr/ADR-006-result-persistence.md](architecture/adr/ADR-006-result-persistence.md) — how historical results are stored.
- [`eval/tasks/README.md`](../../eval/tasks/README.md) — task schema
  reference and tier definitions.
