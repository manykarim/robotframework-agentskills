## MODIFIED Requirements

### Requirement: robotcode skill exists and follows the house structure

The repository SHALL provide a skill at `skills/rf-robotcode/` with a `SKILL.md` whose frontmatter has `name: rf-robotcode` (matching its directory) and a non-empty `description`, a `references/` directory and an `assets/examples/` directory.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/rf-robotcode/SKILL.md` exists with frontmatter `name: rf-robotcode` and a non-empty `description` that mentions robotcode and at least discovery, debugging and results
- **AND** `references/` and `assets/examples/` exist and each contain at least one file

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter and structure checks applied to every other skill

### Requirement: Skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin, VS Code extension and installer channels are generated from the root skill under the same `rf-robotcode` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-robotcode/` with `name: rf-robotcode`, and to `vscode-extension/skills/rf-robotcode/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
