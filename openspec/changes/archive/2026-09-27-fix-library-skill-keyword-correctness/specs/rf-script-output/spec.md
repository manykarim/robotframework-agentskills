## ADDED Requirements

### Requirement: rf_results output carries no criticality grouping

`rf_results.py` and the `rf_results_analyze` MCP tool SHALL NOT emit a `criticality` key in the `details` section, and the rf-results skill SHALL NOT describe criticality grouping. Robot Framework removed test criticality in 4.0. Tag-based grouping stays available through `details.tags`. This is a breaking change to the `details` shape, and the change that makes it SHALL record it in the installer CHANGELOG.

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
