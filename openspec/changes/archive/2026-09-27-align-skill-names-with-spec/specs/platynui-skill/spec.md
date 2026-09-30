## MODIFIED Requirements

### Requirement: PlatynUI library skill exists and follows the house structure

The repository SHALL provide a Robot Framework PlatynUI library skill at `skills/rf-platynui/`, structured like the existing Browser/Selenium/Appium skills: a `SKILL.md` with valid frontmatter (`name: rf-platynui` matching its directory, and a `description`), a `references/` directory of deep-dive documents, and an `assets/examples/` directory of `.robot` examples.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/rf-platynui/SKILL.md` exists with frontmatter `name: rf-platynui` and a non-empty `description`
- **AND** `references/` and `assets/examples/` subdirectories exist with at least one file each

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter/structure checks applied to every other skill

### Requirement: Skill is integrated into distribution channels without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin and VS Code extension channels are generated from the single source under the same `rf-platynui` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-platynui/` with `name: rf-platynui` and to `vscode-extension/skills/rf-platynui/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
