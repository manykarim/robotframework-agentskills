## MODIFIED Requirements

### Requirement: Project scope is the default, user scope is opt-in

Installs SHALL default to project scope, writing into the current directory's
per-agent config; `--scope user` SHALL be required to perform a global
(home-directory) install.

#### Scenario: Default writes into the project
- **WHEN** `rf-agentskills install --agents claude-code` runs with no `--scope`
- **THEN** files are written under the current directory (e.g. `./.claude/...`), not under `~`
- **AND** `--project` defaults to the current working directory

#### Scenario: User scope still available
- **WHEN** `--scope user` is passed
- **THEN** the install targets the home-directory layout (e.g. `~/.claude`) as before
