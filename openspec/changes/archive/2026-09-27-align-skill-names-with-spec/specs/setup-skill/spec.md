## MODIFIED Requirements

### Requirement: Setup skill exists and follows the house structure

The repository SHALL provide a skill at `skills/rf-setup/` with a `SKILL.md` whose frontmatter has `name: rf-setup` (matching its directory) and a non-empty `description`, a `references/` directory and an `assets/examples/` directory.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/rf-setup/SKILL.md` exists with frontmatter `name: rf-setup` and a description that mentions installing Robot Framework and uv, venv/pip and poetry
- **AND** `references/` and `assets/examples/` exist and each contain at least one file

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter and structure checks applied to every other skill

### Requirement: Setup skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin, VS Code extension and installer channels are generated from the root skill under the same `rf-setup` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-setup/` with `name: rf-setup`, and to `vscode-extension/skills/rf-setup/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
