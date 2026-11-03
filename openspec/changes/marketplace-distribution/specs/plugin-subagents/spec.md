## MODIFIED Requirements

### Requirement: Subagent files are portable across agents

Subagent files SHALL be usable unchanged by Claude Code, Copilot CLI, VS Code Copilot and Cursor, which read the Claude subagent format from the plugin. Agents with another format SHALL receive generated variants with the same instructions: TOML for Codex and OpenCode agent files with `mode: subagent` (see `agent-variants`). Bodies SHALL refer to skills by identifier and SHALL NOT name MCP tools of the bundle (it ships none). They SHALL NOT depend on Claude-only variable expansion. Frontmatter fields that only Claude Code understands SHALL either be ignored harmlessly by the other agents or be removed for them by the installer.

#### Scenario: OpenCode install
- **WHEN** the installer installs the subagents for an OpenCode target
- **THEN** each installed file is the generated OpenCode variant, parses as an OpenCode subagent, and its instructions refer only to skills and tools that the install provides
