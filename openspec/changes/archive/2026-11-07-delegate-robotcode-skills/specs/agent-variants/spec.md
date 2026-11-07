## MODIFIED Requirements

### Requirement: Codex receives TOML subagents

For each `agents/*.md`, a Codex subagent file SHALL exist in TOML with `name`, `description` and `developer_instructions` (the Markdown body). The installer SHALL install it to `.codex/agents/` (project scope) or `~/.codex/agents/` (user scope), because Codex plugins cannot ship subagents.

#### Scenario: Codex lists the subagents
- **WHEN** the installer has set up Codex for a project
- **THEN** `.codex/agents/` holds `rf-test-architect.toml`, `rf-debug-expert.toml` and `rf-migration-guide.toml`, each with the three required fields, and no `rf-keyword-consultant.toml`

### Requirement: OpenCode receives subagents and a hook plugin

For each `agents/*.md`, an OpenCode agent file SHALL exist with frontmatter `description` and `mode: subagent`. A subagent whose Claude frontmatter restricts tools SHALL carry the matching OpenCode `permission`.

An OpenCode JS plugin SHALL run the same hook scripts on OpenCode events:
- `tool.execute.after` for edits of `.robot`/`.resource` files, standing in for the validation `PostToolUse` hook;
- `session.created`, standing in for the environment check `SessionStart` hook.

Any canonical hook that has no OpenCode equivalent SHALL be listed as not ported. The installer SHALL install these to `.opencode/agents/` and `.opencode/plugins/` (project scope) or the matching `~/.config/opencode/` folders (user scope).

#### Scenario: OpenCode validation after an edit
- **WHEN** OpenCode edits a `.robot` file with a syntax error in a project the installer set up
- **THEN** the plugin runs the validation script and reports the error to the agent

#### Scenario: OpenCode subagents
- **WHEN** OpenCode starts in that project
- **THEN** `@rf-debug-expert`, `@rf-test-architect` and `@rf-migration-guide` are available, and `@rf-keyword-consultant` is not
