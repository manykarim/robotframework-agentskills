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

```bash
pipx install rf-agentskills
rf-agentskills install --agent claude-code
```

Or for every detected agent in one shot:

```bash
rf-agentskills install --all
```

## Subcommands

```
rf-agentskills install   --agent <name> [--scope user|project] [--prefix DIR]
                         [--what skills,agents,hooks,mcp] [--dry-run] [--force]
rf-agentskills uninstall --agent <name>
rf-agentskills list                # what's installed where, per the manifest
rf-agentskills targets             # which agents are detected on this machine
rf-agentskills doctor              # what works, what doesn't, what needs user action
rf-agentskills version
```

See `docs/installer/proposal.md` (in the parent repo) for the full
design, compatibility matrix, and per-agent install recipes.
