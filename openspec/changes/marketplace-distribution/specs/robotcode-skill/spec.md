## MODIFIED Requirements

### Requirement: Skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin and installer channels are generated from the root skill under the same `rf-robotcode` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-robotcode/` with `name: rf-robotcode`

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
