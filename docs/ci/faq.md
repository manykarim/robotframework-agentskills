# Skill Evaluation Harness — FAQ

Common questions about the `rf-skill-eval` harness and its CI
integration. For setup see [usage.md](usage.md); for pre-push
workflow see [local-testing.md](local-testing.md).

## Table of Contents

- [Why can't I use Opus?](#why-cant-i-use-opus)
- [My workflow ran out of rate limit, what now?](#my-workflow-ran-out-of-rate-limit-what-now)
- [Does this send my code to Anthropic?](#does-this-send-my-code-to-anthropic)
- [How do I trigger the canary manually?](#how-do-i-trigger-the-canary-manually)
- [The PR comment says a metric regressed — how do I debug?](#the-pr-comment-says-a-metric-regressed-how-do-i-debug)
- [Can I run this without a paid Claude subscription?](#can-i-run-this-without-a-paid-claude-subscription)
  <a id="subscription"></a>
  <a id="api-key-fallback"></a>
- [How do I rotate my OAuth token?](#how-do-i-rotate-my-oauth-token)
  <a id="token-rotation"></a>
- [What's the difference between narrow / realistic / adversarial tiers?](#whats-the-difference-between-narrow--realistic--adversarial-tiers)
- [Where are historical results stored?](#where-are-historical-results-stored)
- [Why is rf-mcp required?](#why-is-rf-mcp-required)

---

## Why can't I use Opus?

Three reasons, in order of importance:

1. **Cost.** Opus is roughly 5× Sonnet and 25× Haiku per token. A
   single weekly canary on Opus would exceed the maintainer's
   subscription budget and force a move to per-token billing.
2. **Variance masking.** Skill effects are measured as δ (Cliff's
   delta) between control and treatment arms. Opus's higher baseline
   capability compresses this delta — a skill that genuinely helps
   Haiku may look neutral on Opus because Opus would have solved the
   task anyway.
3. **Rubric calibration.** The gating thresholds
   (`|δ| ≥ 0.33` medium-effect, +30% token budget) in
   [ADR-004](architecture/adr/ADR-004-scoring-model.md) are
   calibrated against Haiku/Sonnet behavior. Opus metrics would not
   be comparable without re-baselining the entire rubric.

The CLI rejects `--model claude-opus-...` at argument parse time. If
you believe Opus coverage is justified, open an ADR rather than
patching the allow-list.

---

## My workflow ran out of rate limit, what now?

The OAuth subscription path shares a 5-hour rolling window with the
maintainer's interactive Claude Code sessions. When it is exhausted
you have four options, ordered from least to most disruptive:

1. **Wait and re-run.** The window resets on a rolling basis. Use
   `claude usage` locally or re-run the workflow after a few hours.
2. **Schedule off-hours.** The weekly canary is already scheduled for
   04:00 UTC Sunday to minimize collision. For ad-hoc PR runs, push
   late in the day and retry in the morning.
3. **Reduce concurrency.** The matrix is already capped at
   `max-parallel: 1–2` for OAuth auth
   ([ADR-005](architecture/adr/ADR-005-ci-integration.md)). If you
   locally raised it, lower it back.
4. **Switch to API-key auth for the run.** Re-dispatch the workflow
   with `use_api_key=true`:

   ```bash
   gh workflow run skill-evaluation.yml -f use_api_key=true
   ```

   API keys bill per token but have no 5-hour cap. This is the
   designed escape hatch for overflow runs.

For PRs from forks, the API-key path is automatic — repo secrets
(including the OAuth token) are not exposed to fork-triggered runs
by GitHub default, and the workflow falls back to the API key.

---

## Does this send my code to Anthropic?

**Yes.** The harness drives `claude -p` subprocesses. Prompts, tool
calls, file contents read by the agent, and test outputs observed by
the agent all traverse Anthropic's API — identical to running
Claude Code interactively.

This means:

- Do not include production secrets in your test fixtures. Use
  placeholder credentials in `eval/fixtures/sut-*/`.
- The `sut-browser` fixture's demo app runs on `localhost`; the
  page text seen during test execution is sent along with the
  session. Review fixture content before committing.
- Session JSONLs captured under `eval/runs/` contain the agent's
  view of your code. Artifact retention is 30 days (PR) and 365
  days (canary) inside GitHub Actions.

See Anthropic's data-handling policy:
https://www.anthropic.com/legal/privacy

The harness does not add any *additional* telemetry beyond what
Claude Code itself sends. If a specific fixture contains sensitive
content, mark its task YAML `skip_in_ci: true` and run it only
locally.

---

## How do I trigger the canary manually?

The weekly canary runs all three tiers with `N=8` replicates. To run
it on-demand:

```bash
gh workflow run skill-evaluation.yml -f tier=canary
```

To run it with API-key auth (avoids the subscription window):

```bash
gh workflow run skill-evaluation.yml \
  -f tier=canary -f use_api_key=true
```

Watch progress:

```bash
gh run list --workflow=skill-evaluation.yml --limit 5
gh run watch
```

Full-canary runs take up to four hours on subscription auth.
Schedule accordingly.

---

## The PR comment says a metric regressed — how do I debug?

Step-by-step:

1. **Read the scorecard.** The PR comment lists the regressing
   metric, the δ, and the 95% CI. Confirm the CI excludes zero — a
   wide CI that crosses zero is noise, not a real regression.

2. **Download the artifacts** from the failing run:

   ```bash
   gh run download <run-id> --dir /tmp/eval-artifacts
   ```

   Artifacts include every matrix cell's `runs/<cell_id>/` plus the
   aggregated `scorecard/` directory.

3. **Open the HTML scorecard:**

   ```bash
   xdg-open /tmp/eval-artifacts/scorecard/scorecard.html
   ```

   Scroll to the "Failure Gallery" section — it shows the two or
   three worst individual sessions for the regressing metric with
   links to their session JSONL.

4. **Inspect the session JSONL** for a failing cell:

   ```bash
   jq -c 'select(.type == "tool_use" or .type == "user")
          | {turn: .turn_idx, tool: .name, text: .text}' \
     /tmp/eval-artifacts/run-<cell>-treatment/session.jsonl
   ```

5. **Reproduce locally:**

   ```bash
   uv run rf-skill-eval run \
     --task eval/tasks/<tier>/<task>.yaml \
     --arm treatment \
     --log-level DEBUG
   ```

   See [local-testing.md](local-testing.md#iterating-on-a-failing-task)
   for the full debug loop.

6. **If it reproduces, fix the skill.** If it does not reproduce
   (three local runs all pass), the regression is flaky — file an
   issue tagged `flaky-eval` and retry the PR run. Per
   [ADR-005](architecture/adr/ADR-005-ci-integration.md), CI does
   not auto-retry failed cells; a single failure is valid data.

---

## Can I run this without a paid Claude subscription?

**Yes, via the `ANTHROPIC_API_KEY` fallback.** Every token is billed
per-call (no subscription flat rate), but the harness works
identically otherwise.

Locally:

```bash
# In .env, comment out CLAUDE_CODE_OAUTH_TOKEN and uncomment:
ANTHROPIC_API_KEY=sk-ant-api03-...
```

In CI (fork PRs automatically use this path, since repo secrets are
not injected into fork-triggered runs):

```bash
gh workflow run skill-evaluation.yml -f use_api_key=true
```

The workflow reads `ANTHROPIC_API_KEY` from repo secrets in this
mode. For a one-off run, the maintainer can temporarily add a
dedicated API key as a repo secret and remove it after.

Cost expectations are in
[usage.md](usage.md#cost-expectations). A full weekly canary on
API-key billing is roughly $6 (Haiku) or $30 (if Sonnet is in the
matrix).

---

## How do I rotate my OAuth token?

OAuth tokens expire roughly one year after issuance. Rotate annually
or immediately on suspected compromise.

### 1. Generate a fresh token

```bash
claude setup-token
```

Copy the new `sk-ant-oat01-...` value.

### 2. Update your local `.env`

```bash
sed -i 's/^CLAUDE_CODE_OAUTH_TOKEN=.*/CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-NEW/' .env
```

### 3. Update the repo secret

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN --body "sk-ant-oat01-NEW"
```

### 4. Revoke the old token

Visit https://console.anthropic.com/ and revoke the previous OAuth
token from your account's authorized applications list.

### 5. Verify

```bash
uv run rf-skill-eval doctor
gh workflow run skill-evaluation.yml -f tier=smoke
```

The workflow-start check in `install-claude-code` should report
"token valid, expires in ~365 days".

Repo maintainers should keep an annual reminder (GitHub issue
auto-opened ~11 months after last rotation, per
[ADR-005](architecture/adr/ADR-005-ci-integration.md)).

---

## What's the difference between narrow / realistic / adversarial tiers?

| Tier          | Duration    | Shape                              | Gating?    |
| ------------- | ----------- | ---------------------------------- | ---------- |
| `narrow`      | ~5 min each | Single skill, single file, one behavior | Yes (PR)   |
| `realistic`   | ~20 min each | Multi-step, multi-file, real-work simulation | Yes (merge) |
| `adversarial` | ~10 min each | Deliberately tempts known failure modes | Reported-only in v1 |

- **Narrow tasks** isolate one skill's effect. Most skill PRs only
  exercise narrow tasks in CI.
- **Realistic tasks** evaluate skills under representative work.
  They gate merges to `main` but do not gate PRs.
- **Adversarial tasks** test whether a skill prevents specific
  anti-patterns (e.g., "just make the test pass" when the correct
  fix is in the product). In v1 their metrics are reported but do
  not gate ship — see
  [ADR-004](architecture/adr/ADR-004-scoring-model.md) "Anti-gaming
  for the grader".

Full tier definitions and task-authoring guidelines:
[`eval/tasks/README.md`](../../eval/tasks/README.md).

---

## Where are historical results stored?

Three layers, each answering a different question:

1. **GitHub Actions artifacts** (retention: 30 days PR, 365 days
   canary). Raw session JSONL, hook logs, per-cell `scorecard.json`.
   Use for debugging a specific regression; download with
   `gh run download`.

2. **SQLite + Parquet trend database**, committed to the orphan
   `eval-history` branch after every canary run. One row per
   `(run_id, skill_id, metric_id, arm)`. Use for longitudinal
   analysis and baseline computation.

   ```bash
   git fetch origin eval-history
   git show origin/eval-history:trends.db > /tmp/trends.db
   sqlite3 /tmp/trends.db "SELECT skill_id, metric_id, AVG(value) FROM trends WHERE timestamp > date('now','-30 day') GROUP BY 1, 2;"
   ```

3. **30-day rolling baselines**, computed on the fly from the trend
   DB by `rf-skill-eval baselines`. The gating rule in
   [ADR-004](architecture/adr/ADR-004-scoring-model.md) compares
   current-run metrics against these baselines.

Full persistence design:
[ADR-006](architecture/adr/ADR-006-result-persistence.md).

---

## Why is rf-mcp required?

`rf-mcp` is the Model Context Protocol server that exposes Robot
Framework test execution as tool calls to the agent. Several skills
(notably `testcase-builder`, `results-analysis`) rely on it for
their primary value proposition: letting the agent **run the test
it just wrote** before claiming the task is done.

The `executed_before_complete` primary metric directly counts
rf-mcp tool calls. Without rf-mcp, that metric is always zero,
treatment arms look no different from control, and the skill's
effect is invisible to the rubric.

See [`skills/README.md`](../../skills/README.md) for the rf-mcp
setup that the harness expects. The harness itself installs rf-mcp
into each per-arm profile during invocation; contributors do not
need to install it globally.
