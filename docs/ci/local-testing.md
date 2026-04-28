# Local Testing — Pre-Push Checklist

Fast reference for running the eval harness locally before pushing a
PR. For the full user guide, see [usage.md](usage.md).

## Table of Contents

- [Decision: smoke vs local vs skip](#decision-smoke-vs-local-vs-skip)
- [Commands](#commands)
- [Troubleshooting](#troubleshooting)
  - [`rfbrowser init` failures](#rfbrowser-init-failures)
  - [OAuth token expiry](#oauth-token-expiry)
  - [Rate-limit exhaustion](#rate-limit-exhaustion)
  - [`uv sync` cache issues](#uv-sync-cache-issues)
- [Iterating on a failing task](#iterating-on-a-failing-task)
- [Adding a new skill to the eval task bank](#adding-a-new-skill-to-the-eval-task-bank)

---

## Decision: smoke vs local vs skip

| Your change touches…                        | Recommended check        |
| ------------------------------------------- | ------------------------ |
| `skills/**/SKILL.md` (prompt content)       | `eval-local.sh`          |
| `skills/**/scripts/*.py` (skill script)     | `eval-smoke.sh` + unit tests |
| `eval/src/**` (harness code)                | `uv run pytest` + smoke  |
| `eval/tasks/**` (new task)                  | Manual one-off on that task |
| `docs/**`, `README.md`, `CHANGELOG.md`      | Skip — CI skips too      |
| `plugins/rf-agentskills/**` (only plugin)   | Skip — sync-skills CI handles this |
| `.github/workflows/**`                      | Skip locally; CI validates |

When in doubt, run smoke. It is two minutes.

---

## Commands

Copy-paste from top to bottom. These assume one-time setup from
[usage.md](usage.md#one-time-setup) is already done.

```bash
# 1. Fast sanity check (one Haiku task, ~2 min)
scripts/eval-smoke.sh

# 2. If smoke passes and you touched SKILL.md, run the full narrow tier
scripts/eval-local.sh

# 3. If a specific task fails, rerun it with DEBUG logging
uv run rf-skill-eval run \
  --task eval/tasks/narrow/<task-file>.yaml \
  --arm treatment \
  --model claude-haiku-4-5 \
  --output eval/runs/debug-$(date +%s) \
  --log-level DEBUG

# 4. Regenerate the scorecard without re-invoking Claude
uv run rf-skill-eval score eval/runs/batch-<date>/
uv run rf-skill-eval report \
  --batch eval/runs/batch-<date>/ \
  --format html,md \
  --out eval/reports/batch-<date>/

# 5. Open the HTML report
xdg-open eval/reports/batch-<date>/scorecard.html
# or on macOS:
open eval/reports/batch-<date>/scorecard.html
```

---

## Troubleshooting

### `rfbrowser init` failures

Symptom: `uv run rfbrowser init` hangs, times out, or errors with
"Failed to download Chromium".

**Corporate proxy.** Set the standard proxy env vars before the
command:

```bash
export HTTPS_PROXY=http://proxy.corp.example:8080
export HTTP_PROXY=http://proxy.corp.example:8080
uv run rfbrowser init
```

**Missing system libraries (Linux).** Playwright needs glibc packages
that are not in minimal base images:

```bash
sudo apt-get update
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
  libgbm1 libpango-1.0-0 libcairo2 libasound2
uv run rfbrowser init
```

**Already installed with wrong Node version.** Remove the cached
install and reinstall:

```bash
rm -rf ~/.cache/ms-playwright
uv run rfbrowser init
```

If `rfbrowser init` still fails, run smoke anyway with
`--task narrow-keyword-builder-01.yaml` (uses `sut-minimal`, no
browser). Skip browser fixtures until the install succeeds.

### OAuth token expiry

Symptom: `doctor` reports "token expires in X days" or `run` fails
with HTTP 401.

OAuth tokens are valid for roughly one year from issuance. To rotate:

```bash
claude setup-token
# Copy the new sk-ant-oat01-... token
```

Then update `.env`:

```bash
sed -i 's/^CLAUDE_CODE_OAUTH_TOKEN=.*/CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-new-token/' .env
```

And the repo secret (maintainers only):

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN --body "sk-ant-oat01-new-token"
```

See [faq.md](faq.md#token-rotation) for the full rotation procedure.

### Rate-limit exhaustion

Symptom: `run` errors with HTTP 429 or the subprocess exits with
"rate limit exceeded".

The OAuth subscription enforces a 5-hour rolling window shared with
your interactive Claude Code sessions. During local full runs this
can bite.

**Options:**

1. **Wait.** Check when the window resets:

   ```bash
   claude usage
   ```

2. **Switch to API key** for this run. Comment out
   `CLAUDE_CODE_OAUTH_TOKEN` in `.env`, uncomment
   `ANTHROPIC_API_KEY`, and rerun. API keys bill per token but have
   no 5-hour cap.

3. **Reduce scope.** Run smoke (`eval-smoke.sh`) or a single task
   instead of the full narrow tier.

4. **Defer to CI.** If the change is narrow and you trust the
   smoke result, push and let CI (which uses the same subscription
   but runs outside your interactive windows) do the full check.

### `uv sync` cache issues

Symptom: `uv sync` reports lock drift, fails to resolve, or produces
stale bytecode.

```bash
# Clear the uv cache and retry
uv cache clean
uv sync --reinstall

# If lockfile genuinely drifted, regenerate it
uv lock --upgrade

# Verify lock integrity
uv lock --check
```

If `uv lock --check` fails on `main`, file an issue — CI enforces
lock integrity and should have caught it.

---

## Iterating on a failing task

When a task fails and you need to debug the agent's behavior:

### 1. Run with DEBUG logging

```bash
uv run rf-skill-eval run \
  --task eval/tasks/narrow/<task>.yaml \
  --arm treatment \
  --model claude-haiku-4-5 \
  --output eval/runs/debug-$(date +%s) \
  --log-level DEBUG
```

### 2. Inspect the session JSONL

Each run dir contains a `session.jsonl` with one line per turn
(`user`, `assistant`, `tool_use`, `tool_result`, `thinking`,
`summary`). Browse with `jq`:

```bash
# All tool calls and their results
jq -c 'select(.type == "tool_use" or .type == "tool_result")
       | {turn: .turn_idx, tool: .name, ok: .result_ok}' \
  eval/runs/debug-<id>/session.jsonl

# Assistant text only (to spot reasoning loops)
jq -r 'select(.type == "assistant") | .text' \
  eval/runs/debug-<id>/session.jsonl

# Grader verdict
cat eval/runs/debug-<id>/grader.json
```

### 3. Compare control vs treatment

The same task run against both arms side-by-side shows exactly what
the skill changed:

```bash
diff -u \
  <(jq -r 'select(.type=="assistant").text' eval/runs/debug-control/session.jsonl) \
  <(jq -r 'select(.type=="assistant").text' eval/runs/debug-treatment/session.jsonl)
```

### 4. Replay without re-invoking Claude

Once you have captured a run, you can re-score it after editing
rubric or metric code without spending another API call:

```bash
uv run rf-skill-eval score eval/runs/debug-<id>/ --mode deterministic-only
```

---

## Adding a new skill to the eval task bank

When you add a new skill under `skills/<skill-name>/`, add its eval
tasks in the same PR:

1. **Create at least 3 narrow tasks.** Each tests one clearly-scoped
   behavior. Put them under `eval/tasks/narrow/`:

   ```
   eval/tasks/narrow/narrow-<skill-name>-01.yaml
   eval/tasks/narrow/narrow-<skill-name>-02.yaml
   eval/tasks/narrow/narrow-<skill-name>-03.yaml
   ```

2. **Pin a fixture.** Reuse `sut-minimal` if the skill does not need
   a browser; otherwise `sut-browser`. Add a new fixture under
   `eval/fixtures/` only if existing fixtures cannot exercise the
   skill.

3. **Author `success_criteria` carefully.** A weak grader produces
   noisy primary metrics. Combine criterion types:

   ```yaml
   success_criteria:
     - type: robot_pass
       path: tests/my.robot
     - type: lint_clean
       path: tests/my.robot
     - type: no_deprecated_keywords
       path: tests/my.robot
   ```

4. **Tag `skill_scope` correctly.** The PR preflight filters tasks
   by this tag. Mis-tagging means your skill never runs in CI for
   PRs that touch it.

5. **Run locally** to establish that treatment beats control:

   ```bash
   scripts/eval-local.sh
   ```

6. **Validate schemas** before committing:

   ```bash
   for f in eval/tasks/narrow/narrow-<skill-name>-*.yaml; do
     uv run rf-skill-eval tasks validate "$f"
   done
   ```

See [`eval/tasks/README.md`](../../eval/tasks/README.md) for the full
schema. See [usage.md](usage.md#adding-a-new-task) for a worked
example.
