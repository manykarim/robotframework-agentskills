## MODIFIED Requirements

### Requirement: Distributed without drift

The skill SHALL be copied by `scripts/sync-skills.sh` to `plugins/rf-agentskills/skills/rf-python-library/`, included in the installer assets, named in the `UserPromptSubmit` hook's skill list, and listed in the README skill table. `scripts/check-drift.sh` SHALL pass after sync, and the script SHALL be a regular file (no symlink) in every channel.

#### Scenario: All channels in sync
- **WHEN** `scripts/sync-skills.sh` runs and then `scripts/check-drift.sh`
- **THEN** the drift check passes and each channel contains `rf-python-library/scripts/check_library.py` as a regular file

#### Scenario: Hook mentions the skill
- **WHEN** the context-injection hook runs on the prompt "my robot framework library says it contains no keywords"
- **THEN** the injected text names `rf-python-library`
