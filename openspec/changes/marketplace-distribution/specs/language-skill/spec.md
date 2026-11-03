## MODIFIED Requirements

### Requirement: Skill is distributed to every channel without drift

The skill SHALL be propagated by the sync tooling to the Claude Code plugin (`plugins/rf-agentskills/skills/rf-language/`, with its own `scripts/rf_conventions.py`) and included in the installer assets through the plugin mirror. The drift check and the skill validator SHALL pass. In addition, the context-injection hook's skill list SHALL name `rf-language`; the subagents `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` SHALL direct the agent to `rf-language` (and, for migration, to its `references/migration.md` and the `rf_conventions` report); the README skill table and project structure SHALL list the skill; the content CHANGELOG SHALL announce it.

#### Scenario: Channels populated
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the plugin copy exists with `name: rf-language` and `scripts/check-drift.sh` exits 0

#### Scenario: Installer ships the skill
- **WHEN** the installer is built and installs for Claude Code into a temporary project
- **THEN** `.claude/skills/rf-language/SKILL.md` exists and is recorded in the install manifest

#### Scenario: Hook and subagents reference the skill
- **WHEN** a prompt mentioning a `.robot` or `.resource` file triggers the context-injection hook
- **THEN** the injected text lists `rf-language`
- **AND** `rf-test-architect.md`, `rf-keyword-consultant.md` and `rf-migration-guide.md` name `rf-language`
