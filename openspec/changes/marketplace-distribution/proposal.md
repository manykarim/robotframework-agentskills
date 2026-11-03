## Why

Users install rf-agentskills today through the `rf-agentskills` Python installer, the Claude Code plugin, or an unpublished VS Code extension that only contributes the 12 skills. Coding agents now share a plugin-marketplace model, and on 2026-10-08 we checked how each one treats our existing Claude-format marketplace and plugin.
- **Copilot CLI 1.0.91, Codex 0.153.4 and VS Code 1.138:** tested live; all three load it as-is.
- **Cursor CLI 2026.10.01:** checked statically; its plugin loader reads `.claude-plugin/` and converts Claude-format hooks.

One git repository can therefore be the install source for most agents, globally or per project, without a VS Code extension. Gaps remain only where an agent uses another subagent or hook mechanism (Codex subagents, OpenCode subagents and hooks), and where agents send different hook input for the same kind of edit.

## What Changes

- **One Claude-format marketplace for every plugin-capable agent.** The existing `.claude-plugin/marketplace.json` and `plugins/rf-agentskills/.claude-plugin/plugin.json` serve Claude Code, Copilot CLI, VS Code Copilot, Codex and Cursor. No agent-specific manifests are added. The README documents global and project install, version pinning and component support per agent.
- **Hook scripts accept every agent's edit input.** The input shapes differ:
  - Claude: `tool_input.file_path`;
  - Cursor: `file_path`;
  - VS Code `create_file`: `tool_input.filePath`;
  - Codex and VS Code `apply_patch`: patch text in `tool_input.command` or `tool_input.input`.

  The scripts must also stay correct when an agent runs every hook for every tool (VS Code ignores matchers in Claude-format hooks).
- **Per-agent variants where the format really differs,** generated from the canonical plugin sources and drift-checked:
  - Codex subagents as TOML (`name`, `description`, `developer_instructions`);
  - OpenCode subagents (`mode: subagent`);
  - an OpenCode JS plugin that runs the same hook scripts on OpenCode events.
- **Project-scope bootstrap in the installer.** A new mode writes the committed `.claude/settings.json` entries (`extraKnownMarketplaces` + `enabledPlugins`):
  - Claude Code enables the plugin;
  - Copilot CLI loads it (tested);
  - VS Code recommends it (docs);
  - Cursor imports it when the plugin is installed in Claude Code (CLI code).

  The installer also installs the Codex TOML subagents and prints the per-user Codex commands, because Codex does not load a committed repository marketplace (tested). File-copy installs stay for OpenCode, Goose, Claude Desktop and offline use.
- **The plugin stops setting a default main agent.** `plugins/rf-agentskills/settings.json` (`{"agent": "rf-test-architect"}`) is removed.
- **BREAKING (distribution): the VS Code extension channel is retired.** Its replacements:
  - VS Code users load the plugin through `chat.plugins.marketplaces` or `chat.pluginLocations` (user scope), or the workspace recommendation in `.claude/settings.json` (project scope);
  - `rf-agentskills install --agent copilot` still copies files.

  `vscode-extension/`, its CI build and its release asset are removed, and the spec requirements that list the VS Code channel drop it.

## Capabilities

### New Capabilities
- `agent-plugin-marketplace`: the repository as one Claude-format marketplace for every plugin-capable agent. Covers plugin contents without a default agent, install, scope and pinning documentation per agent, CI validation of the manifests, and release tags as pinnable refs.
- `agent-variants`: Codex subagent TOML, OpenCode subagents and the OpenCode hook plugin, generated from the canonical plugin sources and drift-checked.
- `installer-plugin-bootstrap`: the installer mode that writes project-scope marketplace configuration and per-agent setup instead of copying files.

### Modified Capabilities
- `skill-catalog`: channel lists and the lockstep version rule no longer include the VS Code extension.
- `libdoc-skill`: channel scenarios drop the VS Code tree.
- `library-skill-structure`: channel scenarios drop the VS Code tree.
- `robotcode-skill`: the distribution requirement drops the VS Code channel.
- `language-skill`: the distribution requirement drops the VS Code channel.
- `skill-metadata-conformance`: identifier and sync requirements drop the VS Code channel.
- `platynui-skill`: the distribution requirement drops the VS Code channel.
- `setup-skill`: the distribution requirement drops the VS Code channel.
- `python-library-skill`: the distribution requirement drops the VS Code channel.
- `skill-script-execution`: path rules name only the root and plugin channels.
- `skill-content-verification`: fixes are synced to the plugin copies only.
- `rf-validation-hooks`: hook scripts accept every agent's edit input, and the OpenCode hook plugin calls the same scripts.
- `plugin-subagents`: portability is reached through generated variants for agents that use another subagent format (Codex, OpenCode).

## Impact

- **Repository:** `.claude-plugin/marketplace.json` and `plugins/rf-agentskills/` (`settings.json` removed, `variants/` added, hook scripts' input handling); `vscode-extension/` removed.
- **Scripts and CI:** `scripts/sync-skills.sh` and `scripts/check-drift.sh` (VS Code channel removed, variants added); a new variant generator; `ci.yml` (VS Code build job removed, manifest validation added); `release.yml` (`.vsix` asset removed); `RELEASING.md`.
- **Installer:** `installer/src/rf_agentskills/` gets the plugin-bootstrap mode, plus Codex and OpenCode variants in its adapters, with tests.
- **Docs and tests:** README install matrix per agent; tests that reference `vscode-extension/` are updated.
- **Users:**
  - VS Code users move from the extension, which was never published on the VS Code Marketplace, to the plugin.
  - Claude Code users lose the automatic `rf-test-architect` main agent.
  - Codex users get skills and hooks from the plugin after trusting its hooks once (`/hooks`), and subagents from the installer.
