## MODIFIED Requirements

### Requirement: rf-robotcode complements the script-based skills

The skill SHALL tell agents to check once whether `robotcode` is available and prefer it when it is, and to use `rf-results` and `rf-libdoc` when it is not. Each of those two skills SHALL point back to `rf-robotcode`. Neither of them SHALL be deprecated or have its script behaviour changed.

#### Scenario: Fallback guidance in rf-robotcode
- **WHEN** `SKILL.md` of `rf-robotcode` is read
- **THEN** it has a companion section that names `rf-results` as the fallback for result analysis and `rf-libdoc` as the fallback for keyword search and keyword docs when `robotcode` is not installed
- **AND** it does not name `rf-libdoc-search` or `rf-libdoc-explain`

#### Scenario: Cross-links from the script-based skills
- **WHEN** the `SKILL.md` of `rf-results` and `rf-libdoc` is read
- **THEN** each mentions `rf-robotcode` as the preferred option when `robotcode` is on PATH
- **AND** each still documents its script usage
