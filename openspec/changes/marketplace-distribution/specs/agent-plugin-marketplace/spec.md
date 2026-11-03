## Purpose

Make this repository the plugin marketplace from which Claude Code, GitHub Copilot (CLI and VS Code), Codex and Cursor install rf-agentskills, at user or project scope, at a released or pinned version.

## ADDED Requirements

### Requirement: One Claude-format marketplace serves every plugin-capable agent

The repository root SHALL carry `.claude-plugin/marketplace.json` listing the plugin `rf-agentskills` with source `./plugins/rf-agentskills`. The plugin directory SHALL carry `.claude-plugin/plugin.json`.

These two files SHALL be the only plugin manifests:
- The repository SHALL NOT add a root `plugin.json` in the Agent Plugins format, because Copilot CLI, Codex and Cursor prefer it over `.claude-plugin/plugin.json` and would then treat hooks and subagents as unsupported.
- It SHALL NOT add `.cursor-plugin/` manifests, because Cursor reads `.claude-plugin/` and converts Claude-format hooks itself.

#### Scenario: Copilot CLI installs from the repository
- **WHEN** `copilot plugin marketplace add manykarim/robotframework-agentskills` and `copilot plugin install rf-agentskills@robotframework-agentskills` run
- **THEN** the plugin installs with its 12 skills, its 4 subagents are offered for delegation, and its hooks run on `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse` and `Stop`

#### Scenario: Codex installs from the repository
- **WHEN** `codex plugin marketplace add manykarim/robotframework-agentskills` and `codex plugin add rf-agentskills@robotframework-agentskills` run, and the user trusts the plugin's hooks once
- **THEN** a session lists the 12 skills under the plugin's namespace and the plugin hooks run

#### Scenario: VS Code loads the plugin
- **WHEN** VS Code Copilot loads the plugin through `chat.plugins.marketplaces` or `chat.pluginLocations`
- **THEN** agent mode lists the 12 skills and 4 subagents, and the plugin hooks run with `CLAUDE_PLUGIN_ROOT` set

#### Scenario: Manifests stay consistent
- **WHEN** CI validates the repository
- **THEN** the marketplace entry and `.claude-plugin/plugin.json` carry the same name and version, no root `plugin.json` or `.cursor-plugin/` exists, and `claude plugin validate plugins/rf-agentskills` passes

### Requirement: The plugin sets no default main agent

The plugin SHALL NOT ship a `settings.json`, or a `settings` manifest key, that sets `agent`. Enabling the plugin SHALL leave the user's main agent unchanged, and the subagents SHALL be available only for delegation.

#### Scenario: Plugin without default agent
- **WHEN** the plugin tree is listed
- **THEN** it contains no `settings.json`, and `.claude-plugin/plugin.json` has no `settings.agent`

### Requirement: Install, scope and pinning are documented per agent

The README SHALL document, for Claude Code, Copilot CLI, VS Code Copilot, Codex and Cursor:
- how to add the marketplace and install the plugin;
- what user scope and project scope mean for that agent, and the committed file that enables project scope where the agent supports one;
- how to pin a released version (`#v<version>` or `--ref v<version>`).

It SHALL state per agent:
- which plugin components work there (skills, subagents, hooks);
- any one-time step, such as trusting hooks in Codex (`/hooks`) or enabling VS Code's plugin and hook settings.

It SHALL point OpenCode, Goose and Claude Desktop users to the installer.

#### Scenario: Agent support matrix
- **WHEN** a reader looks up Codex in the README
- **THEN** it says that the plugin provides skills and hooks (after trusting them once with `/hooks`), that subagents come from the installer, and that project scope needs the per-user `codex plugin` commands

### Requirement: Releases keep the marketplace installable at a tag

Every content release tag `v<version>` SHALL point to a commit whose marketplace and plugin manifests carry `<version>`, so that a marketplace pinned to the tag installs exactly that release.

#### Scenario: Pinned install
- **WHEN** a user adds the marketplace pinned to `v2.1.0`
- **THEN** the installed plugin reports version `2.1.0`
