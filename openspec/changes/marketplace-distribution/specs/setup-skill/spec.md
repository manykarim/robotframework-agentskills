## MODIFIED Requirements

### Requirement: Setup skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin and installer channels are generated from the root skill under the same `rf-setup` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-setup/` with `name: rf-setup`

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
