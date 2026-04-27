# Skill Evaluation Harness — Usage Guide

Primary user-facing guide for the `rf-skill-eval` harness: what it is,
how to set it up, how to run evaluations locally, and how CI uses the
same machinery on every PR.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [One-time Setup](#one-time-setup)
- [Running Evaluations](#running-evaluations)
  - [Smoke run](#smoke-run-fastest-feedback)
  - [Local full run](#local-full-run-pre-push-check)
  - [Manual one-off](#manual-one-off-targeted-debugging)
  - [Batch runs](#batch-runs)
  - [Scoring and reports](#scoring-and-reports)
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
- **Tiered.** PR runs are narrow (fast, cheap). Main-merge runs add
  realistic tasks. Weekly canary runs everything. See
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
CLAUDE_MODEL_DEFAULT=claude-haiku-4-5
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

There are three common entry points, from fastest to most thorough.

### Smoke run (fastest feedback)

One Haiku task against the minimal fixture. Completes in roughly
two minutes and confirms the full pipeline works end-to-end.

```bash
scripts/eval-smoke.sh
```

What it does:

1. Loads `.env`.
2. Runs `eval/tasks/narrow/narrow-keyword-builder-01.yaml` with
   `claude-haiku-4-5`, arm `treatment` (skill enabled).
3. Scores the run and prints the JSON scorecard to stdout.

Use this whenever you change a skill's `SKILL.md` and want to confirm
you did not break invocation.

### Local full run (pre-push check)

All narrow-tier tasks, both arms (skill on / skill off), Haiku only.
Roughly 15–25 minutes depending on rate-limit headroom.

```bash
scripts/eval-local.sh
```

What it does:

1. Enumerates every `eval/tasks/narrow/*.yaml`.
2. Runs each task twice (control + treatment).
3. Writes per-run artifacts to `eval/runs/<run-id>/`.
4. Aggregates into a scorecard at `eval/reports/<batch-id>/`.
5. Prints PASS/ITERATE/HOLD verdicts per skill.

Run this before pushing a PR that touches `skills/**`. See
[local-testing.md](local-testing.md) for when to skip it.

### Manual one-off (targeted debugging)

When a specific task fails, run it directly with extra logging:

```bash
uv run rf-skill-eval run \
  --task eval/tasks/narrow/narrow-libdoc-search-01.yaml \
  --arm treatment \
  --model claude-haiku-4-5 \
  --output eval/runs/manual-$(date +%s) \
  --log-level DEBUG
```

Flags:

- `--task` — path to a task YAML.
- `--arm` — `control` (skill disabled) or `treatment` (skill enabled).
- `--model` — `claude-haiku-4-5` or `claude-sonnet-4-6` (see
  [Model Policy](#model-policy)).
- `--output` — directory to write artifacts into.
- `--log-level` — `DEBUG` to see every tool call and hook event.

### Batch runs

Invoke many cells in one command — useful when iterating on scoring
logic without re-running Claude:

```bash
uv run rf-skill-eval run-batch \
  --plan eval/plans/narrow-haiku.json \
  --output eval/runs/batch-$(date +%Y%m%d)
```

A plan file is JSON produced by `rf-skill-eval plan`. See the output
of `uv run rf-skill-eval plan --help` for options.

### Scoring and reports

Given an existing runs directory, regenerate the scorecard without
re-invoking Claude:

```bash
uv run rf-skill-eval score eval/runs/batch-20260414/
uv run rf-skill-eval report \
  --batch eval/runs/batch-20260414/ \
  --format html,json,md \
  --out eval/reports/batch-20260414/
```

`report` produces three files:

- `scorecard.json` — machine-readable, schema-validated.
- `scorecard.html` — human-browsable with per-task failure gallery.
- `scorecard.md` — compact PR-comment-ready summary.

### Benchmarking

For timing-sensitive harness changes:

```bash
uv run rf-skill-eval bench --iterations 3
```

Benchmarks parser throughput, rubric evaluation, and report rendering
against a fixed synthetic dataset. Use this when optimizing telemetry
code.

---

## Understanding Reports

A scorecard summarizes one batch (one or more cells) into verdicts.

### Verdicts

| Verdict   | Meaning                                                        |
| --------- | -------------------------------------------------------------- |
| `SHIP`    | At least one primary metric improves with δ ≥ 0.33, CI excludes zero, nothing regresses, cost within budget. |
| `ITERATE` | Mixed signal — some primary metrics up, some down, or improvements small. Wait for next iteration. |
| `HOLD`    | Any primary metric regresses with δ ≥ 0.33, or cost blows budget. Do not ship. |

See [ADR-004](architecture/adr/ADR-004-scoring-model.md) for the full
gating rule.

### Primary metrics (gating)

1. `first_run_test_pass_pct` — did the produced RF suite pass on first
   `robot` invocation?
2. `executed_before_complete` — did the agent run the test via rf-mcp
   before claiming done?
3. `user_interrupts_per_1k` — rate of user interrupts per 1000 tool
   calls.
4. `convention_violations_per_task` — lint violations from the RF
   convention grader.

All four are externally grounded (grader-derived), never model
self-reported.

### Sample scorecard JSON excerpt

```json
{
  "batch_id": "2026-04-14T12:00:00Z",
  "skill": "keyword-builder",
  "verdict": "SHIP",
  "gate_reasons": [
    "first_run_test_pass_pct: +0.42 (δ=0.48, 95% CI [0.21, 0.63])",
    "no primary regression",
    "input_tokens_per_task: +18% (within 30% budget)"
  ],
  "metrics": {
    "primary": [...],
    "secondary": [...],
    "cost": [...]
  }
}
```

### Sample PR comment (rendered markdown)

```markdown
### rf-skill-eval: keyword-builder — SHIP

| Metric                         | control | treatment | δ     | 95% CI        |
| ------------------------------ | ------- | --------- | ----- | ------------- |
| first_run_test_pass_pct        | 0.41    | 0.83      | +0.48 | [0.21, 0.63]  |
| executed_before_complete       | 0.25    | 0.75      | +0.50 | [0.28, 0.66]  |
| convention_violations_per_task | 2.8     | 1.1       | -0.39 | [-0.58, -0.18]|
| input_tokens_per_task          | 12.1k   | 14.3k     | +18%  | —             |

Full HTML report: [scorecard.html](...)
```

---

## Adding a New Task

1. Pick a tier: `narrow/` (single skill, ~5 min), `realistic/`
   (multi-step, ~20 min), or `adversarial/` (tests failure modes).
2. Copy an existing task as a template:

   ```bash
   cp eval/tasks/narrow/narrow-libdoc-search-01.yaml \
      eval/tasks/narrow/narrow-my-new-task-01.yaml
   ```

3. Edit the YAML:

   ```yaml
   id: narrow-my-new-task-01
   tier: narrow
   timeout_min: 8
   fixture: sut-minimal
   skill_scope: [libdoc-search]
   prompt: |
     Write a Robot Framework test that ...
   success_criteria:
     - type: robot_pass
       path: tests/my_test.robot
     - type: no_deprecated_keywords
       path: tests/my_test.robot
     - type: lint_clean
       path: tests/my_test.robot
   ```

4. Validate the task schema:

   ```bash
   uv run rf-skill-eval tasks validate \
     eval/tasks/narrow/narrow-my-new-task-01.yaml
   ```

5. Run it locally with `--arm treatment` and inspect the artifacts.

See [`eval/tasks/README.md`](../../eval/tasks/README.md) for the full
schema reference and conventions.

---

## CI Reference

The harness is wired into GitHub Actions via a single workflow with
three triggers.

### Workflow

`.github/workflows/skill-evaluation.yml`

### Triggers

| Trigger             | Tier scope                         | Budget    | When                        |
| ------------------- | ---------------------------------- | --------- | --------------------------- |
| `pull_request`      | narrow (changed-skills only)       | ≤ 15 min  | PRs touching `skills/`, `eval/`, or the plugin |
| `schedule`          | narrow + realistic + adversarial   | ≤ 4 hours | Sunday 04:00 UTC (weekly canary) |
| `workflow_dispatch` | user-selected                      | varies    | Manual runs via `gh workflow run` |

The PR trigger runs a narrow-tier matrix with `N=4` replicates per
arm, scoped to only the skills changed in the PR (a preflight step
computes this from `git diff`).

### Artifacts

Every matrix cell uploads:

- `eval/runs/<cell_id>/` — session JSONL, hook logs, fixture end-state.
- `eval/reports/<batch_id>/` — aggregated scorecard (HTML + JSON + MD).

Retention: 30 days for PR runs, 365 days for canary.

### PR comment

The `summarize-pr` job posts (or updates) a single comment marker with
the scorecard. Format matches the [sample above](#sample-pr-comment-rendered-markdown).

### Manual workflow dispatch

```bash
# Run the weekly canary immediately:
gh workflow run skill-evaluation.yml -f tier=canary

# Run against a specific skill only:
gh workflow run skill-evaluation.yml \
  -f tier=narrow -f skill_filter=libdoc-search

# Force API-key auth (for fork-like testing):
gh workflow run skill-evaluation.yml -f use_api_key=true
```

See [faq.md](faq.md) for more manual-trigger recipes.

---

## Model Policy

Only two models are supported:

| Model                 | Default use             | Why                                   |
| --------------------- | ----------------------- | ------------------------------------- |
| `claude-haiku-4-5`    | PR narrow, smoke, local | Cheap, fast, low variance             |
| `claude-sonnet-4-6`   | Realistic, canary       | Higher fidelity for multi-step tasks  |

**Opus is explicitly blocked.** Reasons:

- **Cost.** Opus is 5× Sonnet, 25× Haiku. A single canary run on Opus
  would exceed the weekly subscription budget.
- **Variance.** Opus's higher capability masks skill effects. A good
  skill gets credit for work the base model would have done anyway.
- **Rubric calibration.** The gating thresholds in
  [ADR-004](architecture/adr/ADR-004-scoring-model.md) are calibrated
  against Haiku/Sonnet's baseline behavior.

Attempting to pass `--model claude-opus-...` fails at CLI argument
parse time. There is no workaround — add a new ADR if you believe
Opus inclusion is justified.

---

## Cost Expectations

Very rough per-task estimates (Haiku unless noted). Real costs vary
with prompt length and turn count.

| Scope                      | Tasks | Arms | Replicates | Est. cost (API key) | Subscription impact |
| -------------------------- | ----- | ---- | ---------- | ------------------- | ------------------- |
| Smoke                      | 1     | 1    | 1          | ~$0.005             | ~1 min of 5-hr window |
| Local full (narrow)        | ~20   | 2    | 1          | ~$0.25              | ~15 min of 5-hr window |
| PR narrow (changed-skills) | ~4–8  | 2    | 4          | ~$0.30–0.60         | ~10 min of 5-hr window |
| Weekly canary (all tiers)  | ~60   | 2    | 8          | ~$6 (Sonnet: ~$30)  | ~2 hours of 5-hr window |

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
