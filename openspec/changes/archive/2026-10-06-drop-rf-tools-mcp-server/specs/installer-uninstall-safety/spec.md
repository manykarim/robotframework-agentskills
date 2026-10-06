## MODIFIED Requirements

### Requirement: Config merges preserve entries owned by other tools

Merging rf-agentskills config into a shared file SHALL add only rf-agentskills' own entries and SHALL NOT modify, replace, or remove entries placed there by the user or other tools (Claude Code `settings.json` hooks, `.mcp.json` servers, and the equivalent TOML/YAML config).

#### Scenario: Installing alongside a foreign hook keeps it
- **WHEN** `settings.json` already contains a `PostToolUse` matcher-group from another tool and a user-authored `Notification` hook, and rf-agentskills installs its hooks
- **THEN** rf-agentskills' hook entries are added
- **AND** the foreign `PostToolUse` group and the user's `Notification` hook are still present and unchanged

#### Scenario: Installing alongside a foreign MCP server keeps it
- **WHEN** `.mcp.json` already contains `mcpServers.some-other-server` and rf-agentskills is installed
- **THEN** `.mcp.json` is unchanged (rf-agentskills writes no MCP server) and `some-other-server` is still present

#### Scenario: Re-install is idempotent
- **WHEN** rf-agentskills is installed twice into the same target
- **THEN** the hooks block contains exactly one copy of each rf-agentskills matcher-group (no duplicates)

### Requirement: Uninstall removes exactly what rf-agentskills added

Uninstall SHALL remove only rf-agentskills-owned files and config entries,
identified by ownership marker / manifest record, leaving every foreign and
user-authored entry intact and never leaving orphaned rf-agentskills hook
commands behind.

#### Scenario: Uninstall removes only our hooks
- **WHEN** rf-agentskills is uninstalled from a `settings.json` that also holds a foreign `PostToolUse` group and a user `Notification` hook
- **THEN** all rf-agentskills hook entries are removed
- **AND** the foreign group and the user `Notification` hook remain
- **AND** no remaining hook command references the removed `rf-agentskills-files` install directory

#### Scenario: Uninstall removes only our MCP server
- **WHEN** rf-agentskills is uninstalled from a `.mcp.json` that holds `some-other-server` and an `rf-tools` entry recorded by an older installer
- **THEN** `rf-tools` is gone and `some-other-server` remains

#### Scenario: Empty containers pruned, shared file kept
- **WHEN** removing rf-agentskills' entries empties a hook event list or the `hooks` object, but other top-level keys (e.g. `model`) or foreign entries remain
- **THEN** the emptied event/`hooks` container is pruned
- **AND** the file is retained (not deleted) because foreign content remains
- **AND** the file is deleted only when it would otherwise be an empty object

#### Scenario: User-modified installed files are not deleted
- **WHEN** a file rf-agentskills installed was subsequently edited by the user (hash differs from the manifest record)
- **THEN** uninstall skips it and reports it as skipped rather than deleting it

## ADDED Requirements

### Requirement: Re-install retires the rf-tools MCP server

Installing over a record written by an installer that registered the `rf-tools` MCP server SHALL remove the `rf-tools` entry from every config it was merged into (Claude Code / Copilot `.mcp.json`, Copilot `.vscode/mcp.json`, Cursor `mcp.json`, Codex `config.toml` `[mcp_servers.rf-tools]`, OpenCode `opencode.json` `mcp`, Goose `config.yaml` `extensions`, Claude Desktop `claude_desktop_config.json`), keep every other entry, and delete the server files it staged (hash-checked, user-modified files kept). The install output SHALL name each cleaned config file, and `--dry-run` SHALL list the removals.

#### Scenario: Upgrade cleans the old server and keeps a foreign one
- **WHEN** the manifest records an `rf-tools` merge into `.mcp.json`, which also holds `some-other-server`, and a staged `servers/rf-tools-server.py`, and rf-agentskills is installed again
- **THEN** `.mcp.json` holds only `some-other-server`
- **AND** `rf-tools-server.py` is deleted and no longer tracked

#### Scenario: Every config shape is cleaned
- **WHEN** retired `rf-tools` entries exist in a Codex `config.toml`, a Goose `config.yaml`, a Copilot `.vscode/mcp.json` and a `claude_desktop_config.json`, next to user entries
- **THEN** only the `rf-tools` entries are removed

#### Scenario: Selecting mcp is ignored
- **WHEN** `rf-agentskills install --what skills,mcp` runs
- **THEN** it prints a note that `mcp` is ignored and installs the skills
