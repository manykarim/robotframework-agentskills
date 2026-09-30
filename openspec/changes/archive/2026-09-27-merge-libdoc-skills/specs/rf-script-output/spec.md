## MODIFIED Requirements

### Requirement: In-repo consumers stay consistent with the contract

The MCP server and skill documentation SHALL emit/describe the same output contract as `rf_libdoc.py`. The contract SHALL be documented in the single `rf-libdoc` skill's `SKILL.md`. The MCP tools `rf_libdoc_search` and `rf_libdoc_explain` SHALL keep their names. Changes to the script's schema SHALL be reflected in `rf-tools-server.py` and the `rf-libdoc` skill doc in the same change, and the cross-channel drift check SHALL pass.

#### Scenario: MCP server matches the script schema
- **WHEN** the `rf-tools` MCP libdoc tools (`rf_libdoc_search`, `rf_libdoc_explain`) run
- **THEN** their output uses the same `mode`/`results` schema and minimal library references as the CLI script

#### Scenario: Contract documented once
- **WHEN** the shipped skills are searched for the output-contract description (`mode`, `results`, `usage.params`)
- **THEN** it is found in the `rf-libdoc` skill and matches the script's behaviour

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the change
- **THEN** the drift check reports no drift
