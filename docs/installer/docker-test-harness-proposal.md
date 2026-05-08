# Docker test harness for the installer — proposal

**Status:** Proposal — no code changes yet. Local-only (not CI). Reviewing for direction before implementing.
**Branch:** `feature/installer` (continuation).
**Date:** 2026-05-08.

## TL;DR

Add an opt-in Docker-based test harness, run **locally only**, that exercises the installer end-to-end against real coding agents (Claude Code, Codex, Goose, OpenCode) in a clean container. A single OpenRouter API token drives all four. Per-agent smoke tests prove the agent **actually loads** the installed skill — closing the gap between "files landed at the right paths" (which our `tmp_path` tests already cover) and "the agent can use them".

Not a replacement for the existing pytest-tempdir tests. A complement: those run in milliseconds and stay in CI; this runs in minutes and is reserved for pre-push verification by maintainers.

## Why this matters

Today's installer test suite uses `tmp_path + monkeypatched $HOME`. It proves three things:

1. The right bytes are written to the right paths.
2. Transforms (substitutions, MDC conversion in older versions, etc.) produce the expected output.
3. Uninstall cleanly reverses every install.

It does **not** prove:

4. That an agent actually starts up against those paths.
5. That the agent's skill / agent / hook / MCP discovery picks them up.
6. That the install survives the agent's own loader (e.g., format validation, manifest checks).
7. That cross-agent overlap (e.g., Codex + Goose both reading `~/.agents/skills/`) doesn't trip warnings.

Those are exactly the kinds of failures that the eval harness's PR #2/#3 dance kept surfacing on Claude Code — the right files were there, but the agent silently ignored them or fired hooks differently than expected. A Docker harness lets us catch the same class of failure for the other six adapters before users do.

## Goals

1. **Reproducible.** `make docker-test` produces the same outcome on any contributor's machine.
2. **Fully isolated.** No agent state from the developer's `~/.claude/` etc. leaks in; nothing the test does pollutes the host.
3. **Single API key.** A contributor sets one env var (`OPENROUTER_API_KEY`) and the harness drives every agent it can.
4. **Cheap per run.** ≤ 5¢ for a full sweep of the four CLI agents using haiku-tier models on OpenRouter.
5. **Local only.** Never runs in GitHub Actions. The signal is for human maintainers, not the automatic CI surface.

## Non-goals

- **Not** replacing the pytest-tempdir tests. Those are the workhorse.
- **Not** covering GUI agents (Cursor IDE, Claude Desktop, VS Code Copilot). They need a graphical environment Docker can't provide cheaply.
- **Not** auto-running on every commit. Opt-in. A contributor invokes it before pushing a non-trivial installer change.
- **Not** a full eval — we're not grading skill quality, only confirming load semantics.

## What the agents support (verified)

### OpenRouter compatibility — Tier 1 (single token works)

| Agent | OpenRouter setup | Notes |
|---|---|---|
| **Claude Code** | `ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1` + `ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY` + `ANTHROPIC_MODEL=anthropic/claude-haiku-4-5` | Locked to `anthropic/*` models on OR (gateway-mode constraint). Source: code.claude.com/docs/en/llm-gateway |
| **Codex CLI** | `[model_providers.openrouter]` block in `config.toml` (`base_url`, `wire_api="responses"`); `OPENROUTER_API_KEY` env | Free choice of any OR model. Source: developers.openai.com/codex/config-reference |
| **Goose** | `GOOSE_PROVIDER=openrouter`, `GOOSE_MODEL=...`, `OPENROUTER_API_KEY`. Set `GOOSE_DISABLE_KEYRING=1` for headless | Native first-class provider |
| **OpenCode** | `provider.openrouter` block in `opencode.json` + `OPENROUTER_API_KEY` | Native first-class; broadest model coverage |

### Tier 3 — excluded from the Docker harness

| Agent | Reason |
|---|---|
| **Cursor CLI** | `cursor-agent` only routes through Cursor's managed inference. No `--base-url`; locked to a `CURSOR_API_KEY` Cursor account. |
| **GitHub Copilot CLI** | Honors `COPILOT_PROVIDER_*` env vars in interactive mode but **silently ignores them in `--no-ask-user --output-format json` mode**, falling back to a GitHub-hosted model that requires a Copilot subscription. Open issue: github.com/github/copilot-cli/issues/3048. |
| **Cursor IDE / Claude Desktop / VS Code Copilot** | GUI-only. |

The four Tier-1 agents cover all of the harness-eligible install paths: native skills (Claude Code, Codex, Goose, OpenCode), subagents (Claude Code, Cursor-via-Goose, OpenCode), hooks (Claude Code), MCP servers (every tier-1 agent).

### Headless install — verified by Docker probe

A 1.5GB Python 3.12 + Node 20 + agents image builds in **~75 seconds**:

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git build-essential jq \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code @openai/codex opencode-ai
RUN curl -fsSL https://github.com/block/goose/releases/latest/download/download_cli.sh \
    | CONFIGURE=false bash \
    && mv /root/.local/bin/goose /usr/local/bin/goose
# Versions confirmed live:
#   claude    2.1.133
#   codex     0.129.0
#   opencode  1.14.41
#   goose     latest stable
```

The Goose installer runs an interactive `goose configure` step at the end that fails in `docker build` (no network for the keyring step). Setting `CONFIGURE=false` (per the install script's own env vars) skips it cleanly, and we configure via mounted `~/.config/goose/config.yaml` instead.

### Smoke-test recipes — verified per agent

The four agents all expose **non-prompted introspection** paths. We never have to ask the model "list your skills" — we read the agent's own startup manifest.

```bash
# Claude Code — system/init event lists `skills` array
claude -p "ok" --output-format stream-json --verbose --no-session-persistence \
  | head -1 | jq -e '.skills | index("libdoc-search")'

# Codex — session rollout JSONL contains a developer message with the skill manifest
codex exec --json --skip-git-repo-check "ok" >/dev/null
ROLLOUT=$(ls -t ~/.codex/sessions/*/*/*/rollout-*.jsonl | head -1)
grep -F "/skills/libdoc-search/SKILL.md" "$ROLLOUT"

# OpenCode — first-class introspection command
opencode debug skill 2>/dev/null | grep -F '"location": "/root/.config/opencode/skills/libdoc-search/SKILL.md'

# Goose — extension load logged to stderr at startup
goose run --recipe /tmp/probe.yaml --no-session 2>&1 \
  | grep -F "Loaded extension: libdoc-search"
```

Hook firing for Claude Code is similarly inspectable via `--include-hook-events` and the `hook_started` event type, which our PR #3 work already used.

**Cost per smoke test:** ~$0.0005 per Haiku round-trip (Claude Code, Codex). Goose and OpenCode using `openai/gpt-4o-mini` via OpenRouter run ~$0.0001 per call. **Full sweep: under 1¢.**

## Architecture

A two-layer harness:

### Layer 1: image (`docs/installer/docker/Dockerfile`)

Frozen baseline with all four CLI agents pre-installed plus pip-installed `rf-agentskills`. Built once per agent-version bump (rare). Tag: `rf-agentskills-test:latest`.

```dockerfile
FROM python:3.12-slim
# … apt + node + agents (as in the verified probe above) …
COPY installer/ /work/installer/
COPY plugins/rf-agentskills/ /work/plugins/rf-agentskills/
RUN pip install --no-cache-dir /work/installer
WORKDIR /work
ENTRYPOINT ["/work/scripts/docker-harness-entry.sh"]
```

### Layer 2: harness (`scripts/docker-test-harness.sh` + `scripts/docker-harness-entry.sh`)

The host script `scripts/docker-test-harness.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${OPENROUTER_API_KEY:?must be set; get one at https://openrouter.ai/keys}"

# Build (cached after first run)
docker build -f docs/installer/docker/Dockerfile -t rf-agentskills-test:latest .

# Run with a fresh writable layer; the container's $HOME is a tmpfs
# so no agent state survives the run.
docker run --rm \
    --tmpfs /root \
    --tmpfs /tmp \
    -e OPENROUTER_API_KEY \
    -e DOCKER_HARNESS_AGENTS="${DOCKER_HARNESS_AGENTS:-claude-code codex goose opencode}" \
    -v "$PWD:/work:ro" \
    rf-agentskills-test:latest
```

The container-side entrypoint `scripts/docker-harness-entry.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /root/.config/goose /root/.codex /root/.config/opencode

# 1. Configure each agent for OpenRouter
cat > /root/.codex/config.toml <<EOF
[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
wire_api = "responses"
model_provider = "openrouter"
model = "anthropic/claude-haiku-4-5"
EOF
export ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_MODEL=anthropic/claude-haiku-4-5
export GOOSE_PROVIDER=openrouter
export GOOSE_MODEL=anthropic/claude-haiku-4-5
export GOOSE_DISABLE_KEYRING=1
# … plus opencode.json provider block …

# 2. For each requested agent, run the installer + smoke test
for agent in $DOCKER_HARNESS_AGENTS; do
    echo "::: harness :: $agent ::"
    rf-agentskills install --agent "$agent"
    case "$agent" in
        claude-code) claude_code_smoke_test ;;
        codex)       codex_smoke_test ;;
        goose)       goose_smoke_test ;;
        opencode)    opencode_smoke_test ;;
    esac
    rf-agentskills uninstall --agent "$agent"
    # Verify uninstall left no traces in the agent's discovery path
    case "$agent" in
        claude-code) [ ! -f /root/.claude/skills/libdoc-search/SKILL.md ] ;;
        # … etc …
    esac
done
```

The smoke-test functions live in `scripts/docker-harness-smoke.sh` (sourced by the entrypoint) so they're easy to read and unit-test in isolation.

### Pytest entry point (optional)

For contributors who prefer `pytest` over `make`, a thin marker-gated test:

```python
# tests/installer/test_docker_harness.py
import os, subprocess, pytest

@pytest.mark.docker
@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; Docker harness skipped",
)
def test_docker_harness_full_sweep():
    rc = subprocess.call(["scripts/docker-test-harness.sh"])
    assert rc == 0
```

`pytest -m docker` opt-in; default `pytest tests/` skips it. CI never sees the marker because `OPENROUTER_API_KEY` isn't in the GitHub Actions env.

## Trade-offs

| Pro | Con |
|---|---|
| Catches "agent silently ignored my install" — the bug class our PR #3 work uncovered the hard way | Depends on OpenRouter being up + the contributor's billing |
| Single API key drives all four CLI agents | Costs real money per run (cheap, but non-zero) |
| Docker isolation = zero risk of polluting `~/.claude/` etc. | Adds Docker as a developer-machine dependency |
| Smoke tests use init-event introspection — no flaky "ask the model to list skills" | Image is ~1.5 GB after agents install |
| Each run is ~3 minutes wall-clock end-to-end | Slower than `pytest tests/installer` (1.8s today) |
| Works for the 4 CLI agents that are 4/7 of our install matrix | Doesn't cover Cursor IDE / Claude Desktop / VS Code Copilot — those need a separate (likely manual) story |

## Costs

Per single-agent install + smoke test: 1–3 round trips, each ~$0.0001–$0.0005 on Haiku/gpt-4o-mini-tier OpenRouter models. **Full four-agent sweep: under 1¢.**

A contributor running this 100 times a month spends < $1.

## Implementation phases

**Phase 1 — minimum viable harness (~2 days)**
- `docs/installer/docker/Dockerfile` + `scripts/docker-test-harness.sh`
- Smoke test for one agent (Claude Code) to validate the loop
- README section explaining `OPENROUTER_API_KEY` setup and `make docker-test`

**Phase 2 — fan out to remaining tier-1 agents (~3 days)**
- Codex / Goose / OpenCode smoke tests
- Per-agent uninstall verification (the manifest-revert path)
- Hook-fire verification for Claude Code (`--include-hook-events`)

**Phase 3 — pytest gating + docs (~1 day)**
- `tests/installer/test_docker_harness.py` with `@pytest.mark.docker`
- `docs/installer/docker.md` user-facing how-to
- Script to wipe the OpenRouter usage stats / log per-run cost so contributors can see what they spent

## Risks and open questions

1. **OpenRouter outages.** If OR is down, the harness fails. Mitigation: `--skip-on-network-error` flag for CI-equivalent contributors who need a local-only smoke. Network failure is correctly classified as flake, not a regression.
2. **Model drift on OpenRouter.** OR may stop offering `anthropic/claude-haiku-4-5` at the same price tier. Mitigation: pin the model in the entrypoint, version-bump as needed.
3. **Agent-version drift.** The agents auto-update their internal logic. Init-event format could change (it has, even between Claude Code minor versions). Mitigation: Dockerfile pins agent versions, contributors bump explicitly, and the harness reports version at start so a regression-vs-version-drift is distinguishable.
4. **Tier-2 fallback.** If a contributor *does* have Anthropic / OpenAI / GitHub tokens, should the harness optionally use them for higher-fidelity testing? Lean: yes, behind `RF_HARNESS_USE_VENDOR_TOKENS=1`, but defer to Phase 4.
5. **Goose configure step.** The release install script wants a connected configure flow. We sidestep with `CONFIGURE=false` (verified in the probe) and a mounted config.yaml — but if Goose changes that env-var name, the build breaks. Mitigation: lock the install URL to a specific release tag.
6. **Image size.** 1.5 GB is hefty for `docker pull`. We don't push it; each contributor builds locally. Buildkit cache makes the second build ~5s.

## What this proposal is NOT proposing

- **Not** replacing the existing `tests/installer/` suite. Those stay primary and CI-bound.
- **Not** adding the Docker harness to GitHub Actions. Local-only; opt-in.
- **Not** introducing a new install format or transform. The harness exercises whatever the installer ships.
- **Not** trying to test GUI agents. Cursor IDE / Claude Desktop / VS Code Copilot remain out of scope; they get covered by manual maintainer testing or a separate hand-driven recipe.

## Decision points for the reviewer

Before I implement:

1. **Make `make docker-test` the primary entry**, or is a pytest marker (`pytest -m docker`) preferable? They can coexist; pick what should be documented as the canonical invocation.
2. **Cost gate**: do we want a `--max-cost` flag that aborts after $X spend? Probably not for v1 (typical run is sub-cent), but flagging.
3. **Claude Code's `anthropic/*`-only OR limitation**: acceptable? Or do we want a Tier-1.5 fallback that uses a real Anthropic token when present, so we can also test Sonnet there?
4. **Tier-3 agents**: do we add a separate manual checklist (`docs/installer/manual-test-cursor.md` etc.) for Cursor IDE / Claude Desktop / VS Code Copilot, or accept them as untested-by-harness?

## Reference: the verified Docker probe

The exploratory `docs/installer/probe/Dockerfile` from this investigation builds and shows all four agents responding to `--version` (except Goose's binary path which we documented above). It's not part of the proposed harness — just the artifact that proved the install side of the equation. Either fold it into the proposal's Phase 1 or delete; my preference is fold so future contributors see exactly what we tested.
