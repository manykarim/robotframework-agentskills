## MODIFIED Requirements

### Requirement: Subagent files are portable across agents

Subagent files SHALL be usable unchanged by every agent the installer ships them to (Claude Code, OpenCode, Cursor). Bodies SHALL refer to skills by identifier and SHALL NOT name MCP tools of the bundle (it ships none). They SHALL NOT depend on Claude-only variable expansion. Frontmatter fields that only Claude Code understands SHALL either be ignored harmlessly by the other agents or be removed for them by the installer.

#### Scenario: OpenCode install
- **WHEN** the installer copies the subagents to an OpenCode target
- **THEN** each installed file parses as an OpenCode agent, and its instructions refer only to skills and tools that the install provides
