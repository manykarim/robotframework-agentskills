## MODIFIED Requirements

### Requirement: rf_results output carries no criticality grouping

`rf_results.py` SHALL NOT emit a `criticality` key in the `details` section, and the rf-results skill SHALL NOT describe criticality grouping. Robot Framework removed test criticality in 4.0. Tag-based grouping stays available through `details.tags`. This is a breaking change to the `details` shape, and the change that makes it SHALL record it in the installer CHANGELOG.

#### Scenario: Details section without criticality
- **WHEN** `rf_results.py --output output.xml --sections details` runs
- **THEN** `details` contains `suites`, `failed_tests` and `tags`
- **AND** `details` has no `criticality` key

#### Scenario: Skill text has no criticality wording
- **WHEN** the rf-results `SKILL.md` (frontmatter description and body) is read
- **THEN** it does not mention criticality

#### Scenario: Tags still cover critical-style grouping
- **WHEN** a test carries a tag such as `critical` or `smoke`
- **THEN** its counts appear under that tag's entry in `details.tags`

## REMOVED Requirements

### Requirement: In-repo consumers stay consistent with the contract
**Reason**: Its MCP-server half no longer applies (the `rf-tools` server is removed); the documentation half moves to "Skill documentation stays consistent with the contract".
**Migration**: None needed.

## ADDED Requirements

### Requirement: Skill documentation stays consistent with the contract

The skill documentation SHALL describe the same output contract as `rf_libdoc.py`. The contract SHALL be documented in the single `rf-libdoc` skill's `SKILL.md`. Changes to the script's schema SHALL be reflected in the `rf-libdoc` skill doc in the same change, and the cross-channel drift check SHALL pass.

#### Scenario: Contract documented once
- **WHEN** the shipped skills are searched for the output-contract description (`mode`, `results`, `usage.params`)
- **THEN** it is found in the `rf-libdoc` skill and matches the script's behaviour

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the change
- **THEN** the drift check reports no drift
