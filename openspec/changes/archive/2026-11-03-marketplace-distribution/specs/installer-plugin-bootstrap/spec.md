## Purpose

Let a project adopt rf-agentskills through the marketplace (committed configuration that teammates pick up) instead of copied files, with the installer handling what each agent cannot do from a marketplace.

## ADDED Requirements

### Requirement: Installer writes project-scope marketplace configuration

`rf-agentskills install --mode plugin` (project scope) SHALL merge into the project's `.claude/settings.json` an `extraKnownMarketplaces` entry for `robotframework-agentskills` (GitHub source `manykarim/robotframework-agentskills`, optionally pinned to a tag with `--ref`) and `enabledPlugins` `rf-agentskills@robotframework-agentskills: true`, keeping every other key. With `--agent copilot` it SHALL write the same keys to `.github/copilot/settings.json`. It SHALL copy no skills, subagents or hooks for these agents. The manifest SHALL record the merged keys so that uninstall removes only them. The committed entries SHALL be enough for Copilot CLI to load the plugin, and SHALL make VS Code recommend it and Claude Code enable it.

#### Scenario: Copilot CLI picks up the committed configuration
- **WHEN** the committed `.claude/settings.json` holds the two entries and a teammate starts Copilot CLI in the trusted project
- **THEN** the plugin's skills, subagents and hooks are loaded without a user-level install

#### Scenario: Existing settings preserved
- **WHEN** `.claude/settings.json` already holds hooks and other plugins
- **THEN** after `--mode plugin` they are unchanged and the two entries are added; uninstall removes only those two entries

### Requirement: Installer covers agents a marketplace cannot fully serve

In plugin mode the installer SHALL also do the following.
- **Codex:** install the TOML subagents, and print or, with `--yes`, run `codex plugin marketplace add manykarim/robotframework-agentskills` and `codex plugin add rf-agentskills@robotframework-agentskills`, because Codex does not load a committed repository marketplace.
- **Cursor:** print the steps to add the marketplace (its git URL) to the Cursor account. Cursor also imports the plugin when it is installed in Claude Code and enabled in `.claude/settings.json`, through its third-party imports.
- **OpenCode, Goose and Claude Desktop:** keep the file-copy install, since they have no plugin marketplace.

#### Scenario: Codex in plugin mode
- **WHEN** `rf-agentskills install --mode plugin --agent codex` runs without `--yes`
- **THEN** it writes `.codex/agents/*.toml` and prints the two `codex plugin` commands without running them

### Requirement: File-copy mode stays available

Without `--mode plugin`, the installer SHALL behave as before for every agent (file copies with the manifest), so offline and pinned-copy installs keep working.

#### Scenario: Default mode unchanged
- **WHEN** `rf-agentskills install --agent claude-code` runs without `--mode`
- **THEN** skills, subagents and hooks are copied into `.claude/` as in installer 0.7.0
