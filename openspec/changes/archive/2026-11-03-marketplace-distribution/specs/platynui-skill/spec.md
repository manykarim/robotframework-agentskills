## MODIFIED Requirements

### Requirement: Skill is integrated into distribution channels without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin channel is generated from the single source under the same `rf-platynui` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-platynui/` with `name: rf-platynui`

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift
