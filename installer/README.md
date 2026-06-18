# rf-agentskills

Cross-agent installer for Robot Framework agent skills. Ships the
`plugins/rf-agentskills/` bundle (11 skills, 4 subagents, hooks,
helper scripts, MCP server) and writes it into the install paths of
seven coding agents:

| Agent | Status |
|---|---|
| Claude Code (CLI) | full native — skills, agents, hooks, MCP |
| GitHub Copilot (VS Code 1.108+) | full native (preview flags req'd) |
| OpenAI Codex | skills + MCP native; subagents transformed; hooks experimental |
| Cursor 1.7+ | skills→rules, hooks adapted, native MCP |
| OpenCode | subagents + MCP native; skills→commands; hooks deferred |
| Project Goose | MCP + persona text only |
| Claude Desktop | MCP only |

## Install

Zero-install one-liner (no prior `pip install` needed):

```bash
uvx rf-agentskills install        # or: pipx run rf-agentskills install
```

Bare `install` is **interactive** in a terminal — it shows a multi-select of
known agents with the ones detected on your machine pre-checked, then writes
into the current project. Prefer a persistent install? `pipx install
rf-agentskills` first.

### Non-interactive (CI / scripts)

Fully scriptable — no prompt when you pass an explicit selection, `--yes`, or
when stdin isn't a TTY:

```bash
rf-agentskills install --agents claude-code,cursor   # explicit list
rf-agentskills install --agents all                  # every known agent
rf-agentskills install --agents detected --yes       # only detected, no prompt
rf-agentskills install --agent claude-code           # single (back-compat)
```

`--agents none` is a no-op. With nothing detected and no selection in a
non-interactive context, the command exits non-zero and lists the valid agents.

### Scope: project (default) vs user

Installs default to **project scope**, writing into the current directory
(e.g. `./.claude/`) — reviewable per-repo, and `uninstall` from the same
directory needs no arguments. Use `--scope user` for a global install under
your home directory:

```bash
rf-agentskills install --agents all                  # → ./<agent dirs> (project)
rf-agentskills install --agents all --scope user      # → ~/<agent dirs> (global)
```

The uninstall manifest follows scope: project installs record it in
`<project>/.rf-agentskills/`, user installs in the global data dir — so two
projects never collide.

### Installing a pre-release

Pre-releases (e.g. `0.5.0rc2`) need an opt-in: `pipx install --pip-args=--pre rf-agentskills`, or with uv `uv tool install --prerelease allow rf-agentskills` / an exact pin `rf-agentskills==0.5.0rc2`.

**Troubleshooting — "no version of rf-agentskills==<rc>":** if `uv add`/`uv pip`/`pip` reports it can't find a pre-release you know was just published, your index cache is stale (common the same day a release lands). Refresh it:

```bash
uv cache clean rf-agentskills      # or: uv add --refresh …
pip install --no-cache-dir --pre rf-agentskills
```

To make pre-release intent self-documenting in a project, add `[tool.uv]\nprerelease = "allow"` to its `pyproject.toml`.

## Subcommands

```
rf-agentskills install   [--agents all|none|detected|<csv> | --agent <name> | --all]
                         [--scope project|user] [--project DIR] [--prefix DIR]
                         [--what skills,agents,hooks,mcp] [--yes] [--no-input]
                         [--dry-run] [--force]
rf-agentskills uninstall --agent <name> [--scope project|user] [--project DIR]
rf-agentskills list                # what's installed where, per the manifest
rf-agentskills targets             # which agents are detected on this machine
rf-agentskills doctor              # what works, what doesn't, what needs user action
rf-agentskills version
```

See `docs/installer/proposal.md` (in the parent repo) for the full
design, compatibility matrix, and per-agent install recipes.
