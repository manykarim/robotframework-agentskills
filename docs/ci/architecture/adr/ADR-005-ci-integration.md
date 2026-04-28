# ADR-005: CI Integration — Tiered GitHub Actions with Matrix Strategy

**Status:** Accepted
**Date:** 2026-04-14
**Deciders:** System Architecture
**Related:** ADR-001, ADR-003, ADR-006

---

## Context

The harness must run in GitHub Actions for three different cadences:

1. **Per PR** — fast feedback on skill changes. Must complete in ≤ 15 min.
2. **Main-branch merge** — broader coverage; gate for releases.
3. **Weekly canary** — full bundle + all tiers; detects model regressions.

The repo already has CI for plugin validation (`validate-plugin` job, per `git
log`). The eval harness adds a new job family without disrupting existing CI.

Concerns:

- **Runtime budget.** A full run is 480 cells × ~10 min ≈ 80 hours serial.
  Parallelism is essential.
- **API cost control.** Every CI run consumes Anthropic credit. Untriggered runs
  are expensive; over-triggered PRs are worse.
- **Artifact size.** Session JSONLs + fixture end-states can easily exceed 1 GB
  per batch.
- **Determinism.** GH runners vary in hardware; we pin versions explicitly.
- **Caching.** `uv` installs are fast but not free; Claude Code install is the
  main cold-start cost.
- **Secret management.** The auth secret (`CLAUDE_CODE_OAUTH_TOKEN` primary,
  `ANTHROPIC_API_KEY` fallback — see Authentication below) must be scoped to
  the eval job only.

---

## Decision

**Implement three tiered workflows with matrix parallelism, a layered cache
strategy, and typed artifacts.** Authentication uses a subscription-based
OAuth token by default, with an API-key fallback for untrusted/fork PRs.

### Authentication

**Primary: `CLAUDE_CODE_OAUTH_TOKEN` (subscription-based).** Generated locally
via `claude setup-token` (OAuth flow, token format `sk-ant-oat01-…`,
~1-year expiry) or the `claude /install-github-app` wizard's "Create a
long-lived token with your Claude subscription" path. Stored as repo secret
`CLAUDE_CODE_OAUTH_TOKEN`. Consumed by `anthropics/claude-code-action@v1`
which wraps the same `claude -p` subprocess invocation described in ADR-003
(the action is an auth + invocation wrapper; the invocation semantics are
unchanged).

This is the default for maintainer-run CI on this repo because billing rolls
into the maintainer's existing Pro/Max subscription (no per-token charges for
the weekly canary or main-merge runs), which makes cost predictable.

**Fallback: `ANTHROPIC_API_KEY` (per-token billed).** Used for:
- PRs from forks / untrusted contributors (repo secrets are not injected into
  fork-triggered runs by GitHub default — behavior we rely on and document).
- Budget-capped or experimental runs gated behind a workflow-dispatch input
  (see implementation plan Phase 3).
- Any run that would otherwise exceed the 5-hour subscription window quota.

**Rate-limit implications.** Subscription rate limits operate on 5-hour
rolling windows shared with the maintainer's *interactive* Claude Code
sessions. Consequences:
- Weekly canary is scheduled for off-hours (03:00 UTC Monday) to avoid
  collision with interactive usage windows.
- PR narrow-tier batches must stay small (N=4 × changed-skill-scoped tasks
  only) so they fit inside the remaining quota headroom.
- Matrix `max-parallel` is capped to 1–2 concurrent `claude -p` subprocesses
  per run — the bottleneck is no longer runner minutes but the shared 5-hour
  subscription budget. (The earlier "8-wide overnight" note in ADR-003 still
  applies when using `ANTHROPIC_API_KEY`; with OAuth it must be clamped
  lower.)

**Token rotation.** OAuth token expires ~1 year after issuance. An annual
calendar task reminds the maintainer to re-run `claude setup-token` and
update the repo secret. `npx @claude-flow/cli@latest doctor` (or an
equivalent check in the `install-claude-code` composite action) verifies the
token is present and not near expiry at workflow start.

**Security.** The OAuth token is long-lived and tied to a user account,
so blast radius on compromise is higher than a scoped API key:
- Stored only as a GitHub repo secret (environment-scoped where possible).
- `main` is under branch protection so no unreviewed workflow change can
  exfiltrate it.
- Fork PRs never receive secrets (GitHub default behavior, not overridden).
- Injected via `env:` only on the `execute` step, never exposed to earlier
  steps; never logged.
- On suspected compromise: revoke via Anthropic console, rotate the secret.

**Workflow usage (primary path).**

```yaml
- uses: anthropics/claude-code-action@v1
  with:
    claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    claude_args: "--max-turns 5 --model claude-opus-4-6"
```

From the invocation layer's point of view (ADR-003), OAuth token and API key
are interchangeable — they just set different env vars
(`CLAUDE_CODE_OAUTH_TOKEN` vs `ANTHROPIC_API_KEY`) consumed by the same
`claude` binary. Which one is active is a deployment concern of this ADR,
not ADR-003.

### Workflow tier 1 — `eval-pr.yml` (per PR)

- **Trigger:** `pull_request` on paths `skills/**`, `eval/**`,
  `plugins/rf-agentskills/**`.
- **Scope:** Narrow tier only. `N=4` replicates. Tasks: only those whose
  `skill_scope` intersects the PR's changed skills (computed by a preflight step).
- **Matrix:** `strategy.matrix = { arm: [control, treatment], shard: 0..3 }`.
  Each shard gets 1/4 of the selected tasks; arms fan out within a shard.
- **Runtime budget:** ≤ 15 min wall clock.
- **Failure policy:** PR gets a comment with the partial scorecard; CI is
  `neutral` (not `failure`) unless a primary metric regresses beyond the ADR-004
  threshold.

### Workflow tier 2 — `eval-merge.yml` (main branch push)

- **Trigger:** `push` on `main` after merge.
- **Scope:** Narrow + realistic tiers. `N=6` replicates. All tasks whose
  fixtures exist (adversarial tier excluded — reported-only in v1).
- **Matrix:** `strategy.matrix = { arm, shard: 0..7 }` (eight shards).
- **Runtime budget:** ≤ 60 min.
- **Output:** Scorecard uploaded to artifact store; longitudinal series updated.

### Workflow tier 3 — `eval-canary.yml` (weekly)

- **Trigger:** `schedule: cron: "0 3 * * 1"` (Monday 03:00 UTC).
- **Scope:** Full bundle — narrow + realistic + adversarial. `N=8` replicates.
- **Matrix:** `strategy.matrix = { arm, shard: 0..15 }` (sixteen shards).
- **Runtime budget:** ≤ 4 hours.
- **Special behavior:** Compares current scorecard to the 30-day rolling
  baseline. Emits `RegressionDetected` if any primary metric moves ≥ 2σ.
  Regression opens a GitHub issue via `gh issue create`.

### Shared job anatomy (all three tiers)

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    outputs:
      cells: ${{ steps.plan.outputs.cells }}  # JSON array for matrix expansion
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "eval/uv.lock"
      - run: cd eval && uv sync --frozen
      - id: plan
        run: cd eval && uv run rf-eval plan --tier narrow --changed-skills "${{ needs.detect.outputs.skills }}" --shards 4 --output cells.json
      - uses: actions/upload-artifact@v4
        with:
          name: plan
          path: eval/cells.json

  execute:
    needs: plan
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      max-parallel: 8
      matrix:
        include: ${{ fromJson(needs.plan.outputs.cells) }}
    steps:
      - uses: actions/checkout@v5
        with: { submodules: true }     # fixtures are submodules
      - uses: astral-sh/setup-uv@v4
        with: { enable-cache: true, cache-dependency-glob: "eval/uv.lock" }
      - name: Install Claude Code
        uses: ./.github/actions/install-claude-code    # cached local action
      - run: cd eval && uv sync --frozen
      - run: cd eval && uv run rf-eval run --cell "${{ matrix.cell_id }}" --arm "${{ matrix.arm }}"
        env:
          # Primary: subscription-based OAuth token (see Authentication section).
          # Fallback ANTHROPIC_API_KEY path is selected via workflow input for
          # fork PRs and budget-capped runs — see implementation plan Phase 3.
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: run-${{ matrix.cell_id }}-${{ matrix.arm }}
          path: eval/runs/${{ matrix.cell_id }}/
          retention-days: 30

  analyze:
    needs: execute
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v4
      - run: cd eval && uv sync --frozen
      - uses: actions/download-artifact@v4
        with: { path: eval/runs, pattern: run-* }
      - run: cd eval && uv run rf-eval analyze --batch ${{ github.run_id }} --output reports/
      - run: cd eval && uv run rf-eval report --format html,json --out reports/
      - uses: actions/upload-artifact@v4
        with: { name: scorecard, path: eval/reports/, retention-days: 365 }
      - name: PR comment
        if: github.event_name == 'pull_request'
        run: cd eval && uv run rf-eval ci pr-comment --pr ${{ github.event.pull_request.number }}
```

### Caching strategy

| Cache | Key | Benefit |
|-------|-----|---------|
| `uv` cache | `uv.lock` hash | ~3 s install vs ~40 s cold |
| Claude Code install | `claude-cli-version` | ~5 s vs ~30 s cold |
| `robotframework` libs | `pyproject.toml` hash (covered by uv cache) | — |
| Fixtures | git submodule cache | ~1 s vs ~10 s clone |

### Artifacts and retention

- **Run artifacts** (JSONL, hook logs, stdout): 30 days for PR/merge, 365 days
  for canary.
- **Scorecards** (HTML + JSON): 365 days for all tiers.
- **Longitudinal series**: stored in SQLite (see ADR-006); committed to an
  orphan `eval-history` branch via a post-canary step. Never retained as job
  artifact.

### Concurrency control

- `concurrency: { group: eval-${{ github.ref }}, cancel-in-progress: true }` on
  PR workflow — new pushes cancel superseded runs.
- Canary workflow has `cancel-in-progress: false` — never lose a scheduled run.
- `strategy.max-parallel: 1–2` on the `execute` matrix under the default
  OAuth-token auth path (see Authentication) so concurrent `claude -p`
  subprocesses do not exhaust the subscription's 5-hour window. The
  API-key fallback path may raise this to 8.

### Secrets

- `CLAUDE_CODE_OAUTH_TOKEN` (primary) and `ANTHROPIC_API_KEY` (fallback) —
  see Authentication section above. Either is scoped to eval jobs only;
  referenced via `env:` on the `execute` step, never exposed to earlier
  steps; never logged.
- `GITHUB_TOKEN` with `pull-requests: write` for PR comments and
  `issues: write` for regression issues.

---

## Consequences

### Positive

- **Tiered cost.** PRs pay for narrow-only runs (~$X per PR); heavy coverage
  runs weekly on schedule. Predictable spend.
- **Fast PR feedback.** Matrix shards + parallel arms fit ≤ 15 min for
  typical PRs.
- **Clean separation from existing CI.** New workflows; existing
  `validate-plugin` untouched.
- **Regression canary built-in.** Weekly workflow auto-opens issues on
  statistical drift.
- **Reusable.** `.github/actions/install-claude-code` is a composite local
  action; any workflow can consume it.

### Negative

- **Matrix-generation complexity.** `plan` job computes the matrix JSON at
  runtime; GH Actions debugging across matrix expansions is clunky. Mitigated by:
  dumping the plan as an artifact first, so failures are traceable without
  re-running.
- **Auth-secret blast radius.** Every `execute` shard carries the auth
  secret. For the default `CLAUDE_CODE_OAUTH_TOKEN` this is a long-lived,
  user-account-bound token — mitigated by the Authentication section's
  controls (repo-secret scope, branch protection, fork PRs never receive
  secrets, annual rotation). For the `ANTHROPIC_API_KEY` fallback path,
  mitigated by a dedicated Anthropic key scoped to the eval project, quarterly
  rotation, and audit log review.
- **Subscription rate-limit exhaustion.** Under the OAuth path, a runaway
  canary or a PR batch overlapping with heavy interactive use can exhaust
  the 5-hour window and starve both CI and the maintainer. Mitigated by:
  `max-parallel` cap (1–2), off-hours canary schedule, narrow PR scoping,
  and an escape hatch to switch to the API-key fallback via workflow input.
- **Flaky sessions re-run policy.** A single failed cell does not
  re-run — the timeout/error is valid data (see ADR-003). Reviewers used to
  retry-until-green CI need to understand this.
- **Artifact volume.** Canary batches can exceed GitHub's per-workflow
  artifact limits. Mitigated by: gzip on upload; offload raw JSONL to an
  external object store (S3/GCS) in v2 if limits bite.

### Neutral

- Local runs reproduce CI exactly via `uv run rf-eval plan && uv run rf-eval
  run`. No "works in CI, broken locally" drift.

---

## Alternatives Considered

### Single monolithic workflow

- **Pros:** Simple.
- **Cons:** Either too slow for PRs or too shallow for weekly canary. No way to
  tune cost per trigger.
- **Why rejected:** Tiered budget is a primary goal.

### Self-hosted runners

- **Pros:** Consistent hardware; no per-minute billing; custom images.
- **Cons:** Operational burden; security (runners on maintainer hardware);
  doesn't solve API cost, only runner cost.
- **Why rejected:** Overhead not justified for a small project; revisit if
  runner cost ever dominates.

### External orchestrator (n8n on the Netcup box, per parent doc §8)

- **Pros:** More flexible scheduling and alerting.
- **Cons:** Adds external dependency; PR feedback loop is harder to wire.
- **Why deferred:** Reasonable v2 for the canary/alerting piece; CI remains the
  PR-gate substrate.

### `ANTHROPIC_API_KEY` only (no OAuth path)

- **Pros:** Simpler mental model; no long-lived user-bound token; no
  5-hour window scheduling constraints; concurrency can scale freely.
- **Cons:** Per-token billing makes the weekly canary (full bundle,
  N=8, 16 shards) cost variable and expensive — the exact failure mode
  subscription billing exists to avoid for a maintainer-run project.
  PR batches also accrue per-token cost on every push.
- **Why rejected:** The maintainer already pays for a Pro/Max
  subscription; folding CI spend into that flat rate is materially cheaper
  and more predictable. We retain API key as a fallback (see
  Authentication) for fork PRs and overflow runs, which gives us the
  benefits without the cost baseline.

### Reusable workflow (one workflow, called from three triggers)

- **Pros:** Less duplication across the three YAML files.
- **Cons:** The three tiers legitimately differ in budget, scope, and failure
  policy — a shared workflow with mode flags becomes a parameterization
  nightmare.
- **Why compromised:** Use `workflow_call` to share the `execute` + `analyze`
  jobs; keep `plan` tier-specific. (Consistent with the repo's existing
  `workflow_call` usage per `git log`.)

---

## Implementation Notes

- Preflight step to compute `changed-skills` uses `git diff` scoped to
  `skills/**` and maps to skill names via each skill's `SKILL.md` `name:` field
  (per 2026-03-17 memory: plugin dirs match name field).
- `install-claude-code` composite action pins a specific CC version via
  `CLAUDE_VERSION` input; the `EnvironmentSnapshot` records it.
- Runs that exceed the job timeout are captured by `infrastructure/runner/`
  as `InvocationOutcome.timeout`; the analyze step treats them as data, not
  errors.
- A single `eval-history` orphan branch holds the longitudinal SQLite; canary
  workflow commits to it with `git commit --allow-empty` + LFS for the .db.

---

## References

- `docs/ci/rf-agentskills-eval-implementation-plan.md` §4.3, §8
- Existing repo workflows (from `git log`): `validate-plugin`, `workflow_call`
- GitHub Actions docs: matrix strategy, concurrency, artifact retention.
