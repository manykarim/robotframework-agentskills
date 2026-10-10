## MODIFIED Requirements

### Requirement: Fixes land in the canonical source and are synced

Keyword corrections SHALL be made in the root `skills/` directory and propagated to the plugin copies by the sync script. The cross-channel drift check SHALL pass after the change.

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the fixes
- **THEN** the drift check reports no drift
- **AND** the checker gives the same result on the plugin copies as on the root copies
