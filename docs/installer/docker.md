# rf-agentskills Docker test harness

Local-only end-to-end validation of the installer in a clean container.
Catches install bugs that don't show up in the pytest-tempdir suite —
specifically, the "agent silently ignored my install" failure mode.

**Not** part of CI. Opt-in by maintainers before pushing non-trivial
installer changes.

## Quick start

```bash
# Default sweep — all 7 agents, no API calls, ~10 seconds
scripts/docker-test-harness.sh
```

First invocation builds the image (~75s); subsequent runs reuse it.

## What it does

1. Builds (or reuses) `rf-agentskills-test:latest`. Inside: `python:3.12-slim` +
   `uv` + Node 20 + `claude`, `codex`, `opencode`, `goose` CLI agents + `jq`.
2. Bind-mounts the repo at `/work` (read-only), tmpfs-mounts `/root` and
   `/tmp` so no agent state survives between runs.
3. Installs `rf-agentskills` from the mounted source via `uv pip install -e .`.
4. For each requested agent:
   - `rf-agentskills install --agent <name>`
   - Runs `docs/installer/docker/checks/<name>.sh --post-install`
   - `rf-agentskills uninstall --agent <name>`
   - Runs `docs/installer/docker/checks/<name>.sh --post-uninstall`
5. Prints a per-agent pass/fail summary; exits non-zero if anything failed.

## Coverage matrix

What's checked **without** any API call:

| Agent | Filesystem placement | Config-merge shape | Agent-side validation |
|---|---|---|---|
| Claude Code | skills, agents, hooks block, MCP entry, plugin tree | `settings.json`/`mcp.json` JSON keys | `claude plugin validate` (parses manifest, no LLM call) |
| Codex | skills at `.agents/skills/`, agents `.toml`, MCP `[mcp_servers.*]` | TOML round-trip + key checks | grep skill-installer source for `.agents/skills` discovery path |
| Goose | skills at `.agents/skills/`, MCP extension YAML, `.goosehints` persona | YAML key paths | `goose info` (config readable) |
| OpenCode | skills, agents, MCP `mcp.<name>` block | JSON nested keys | **`opencode debug skill`** (native introspection — proves OpenCode WILL find the skill) |
| Cursor | native `~/.cursor/skills/` (post-2.4), `~/.cursor/agents/`, MCP, hooks with namespaced matchers | JSON + matcher rewrite | (none — Cursor is GUI; file checks only) |
| Claude Desktop | `~/.config/Claude/claude_desktop_config.json` MCP entry only | JSON | (none — GUI) |
| Copilot (VS Code) | reuses Claude Code paths (Copilot reads them natively) | same as Claude Code | (none — extension only loads inside VS Code) |

OpenCode's `opencode debug skill` is the strongest signal: it walks
the agent's own skill discovery paths and emits JSON. If our install
shows up there, the agent will find it at runtime — no LLM call needed.

## Optional: API smoke tests

For higher-fidelity checks (Claude Code's `system/init` event, Codex's
session rollout, etc.), pass `--api`:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
scripts/docker-test-harness.sh --api
```

This adds 1 LLM round-trip per agent — total cost typically under 1¢
at OpenRouter haiku-tier pricing. Get a key at
<https://openrouter.ai/keys>.

OpenRouter env wiring is set automatically:

```
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1   (Claude Code → anthropic/* models on OR)
ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY
GOOSE_PROVIDER=openrouter, GOOSE_MODEL=anthropic/claude-haiku-4-5
GOOSE_DISABLE_KEYRING=1                           (no keyring in headless container)
OPENROUTER_API_KEY                                (Codex / OpenCode read this directly)
```

API smoke tests are skipped automatically for GUI-only adapters
(Cursor, Claude Desktop, Copilot).

## Common flags

```bash
scripts/docker-test-harness.sh                    # full sweep, no API
scripts/docker-test-harness.sh --agents claude-code codex   # subset
scripts/docker-test-harness.sh --rebuild           # force fresh image build
scripts/docker-test-harness.sh --api               # add LLM smoke tests
scripts/docker-test-harness.sh --api --agents goose opencode   # combine
```

## What this does NOT replace

`tests/installer/` is the workhorse — 107 cases, 2-second runtime, runs
in CI. It validates transforms, manifest tracking, and plan structure
exhaustively in a Python tempdir. The Docker harness is slower (~10s
without API, ~30s with) and adds: real npm-installed agents, real
filesystem layouts, real cross-agent introspection.

Use both:

| When | Tool |
|---|---|
| Every commit, every PR | `pytest tests/installer/` |
| Before pushing a non-trivial installer change | `scripts/docker-test-harness.sh` |
| Before tagging a release | `scripts/docker-test-harness.sh --api` |

## Files

- `docs/installer/docker/Dockerfile` — image definition
- `docs/installer/docker/entrypoint.sh` — in-container test driver
- `docs/installer/docker/checks/<agent>.sh` — per-agent assertions
- `docs/installer/docker/checks/_lib.sh` — shared `need_file` /
  `need_yaml_key` / `need_toml_key` / `need_json_key` helpers
- `scripts/docker-test-harness.sh` — host-side wrapper

The check scripts and entrypoint are bind-mounted at runtime, so
iterating on them doesn't require an image rebuild.

## Troubleshooting

**"input device is not a TTY"** — harmless; only affects colour
output. The harness doesn't require a tty.

**`docker build` fails on Goose download** — the install script wants
network. Check connectivity from inside Docker (corporate proxies
often block GitHub releases).

**API smoke fails with "no token"** — `--api` requires
`OPENROUTER_API_KEY`. The default no-API mode covers ~80% of failure
modes; reserve `--api` for release prep.

**Goose's interactive `configure` step hangs the build** — the
Dockerfile passes `CONFIGURE=false` to skip it. If the install script
ever changes that env var, we'll see a hang at the Goose layer; fix
by pinning the install URL to a known release tag.
