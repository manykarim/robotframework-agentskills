# skill-content-verification Specification

## Purpose
Keep library-skill content truthful: every keyword a skill teaches exists in, and is not deprecated by, the library version the skill targets, and a deterministic check enforces this in CI so defects cannot silently return in rarely reviewed reference files.

## Requirements

### Requirement: Library skills only teach existing, non-deprecated keywords

Every keyword call in the Robot Framework content of a library skill (fenced ```robotframework blocks in `SKILL.md` and `references/*.md`, and `.robot`/`.resource` files under `assets/`) SHALL resolve to a keyword that exists in the skill's target library or in a Robot Framework standard library, or to a user keyword defined in the same skill. No such call SHALL resolve to a keyword that libdoc marks as deprecated. This applies to rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance and rf-platynui.

#### Scenario: Deprecated Browser wait replaced
- **WHEN** rf-browser content is checked against the installed Browser library
- **THEN** it contains no call to `Wait Until Network Is Idle`
- **AND** network-idle waiting is taught as `Wait For Load State    networkidle`

#### Scenario: Deprecated Appium state assertions replaced
- **WHEN** rf-appium content is checked against AppiumLibrary 3.2.1 or later
- **THEN** it contains no call to `Element Should Be Visible`, `Element Should Be Enabled` or `Element Should Be Disabled`
- **AND** it contains no call to the removed `Long Press`, `Click A Point`, `Zoom` or `Pinch` keywords

#### Scenario: Nonexistent Selenium keywords removed
- **WHEN** rf-selenium content is checked against SeleniumLibrary 6.8.0 or later
- **THEN** it contains no call to `Wait Until Element Count Is Greater Than` or any other keyword that the library does not define and the skill does not define as a user keyword

#### Scenario: Locally defined user keywords are accepted
- **WHEN** a code block or example file defines a keyword in a `*** Keywords ***` section and calls it
- **THEN** that call is not reported as unknown

### Requirement: Keyword arguments with fixed vocabularies are valid

Where the skill describes a keyword whose argument takes a closed set of values, the skill SHALL describe the keyword's purpose correctly and use only values the library accepts. In particular, rf-browser SHALL describe `Wait For Condition` as a timed wrapper around Browser assertion getters, not a JavaScript wait. Its `condition` argument SHALL be a valid condition name, written without the `Get` prefix.

#### Scenario: Wait For Condition used correctly
- **WHEN** rf-browser content that calls `Wait For Condition` is read
- **THEN** each `condition` argument is a valid condition name such as `Text`, `Element States` or `Url`, never `Get Text` or `Get Page Ids`
- **AND** the surrounding prose does not call it a custom JavaScript condition

### Requirement: Skills use native control structures

Library-skill content SHALL use native Robot Framework control structures (`IF`/`ELSE`, `FOR`, `TRY`, `VAR`) instead of `Run Keyword If` and `Run Keyword Unless`. Skills SHALL NOT recommend a failure-screenshot teardown that duplicates the library's own `run_on_failure` behaviour.

#### Scenario: No legacy conditional keywords
- **WHEN** library-skill content is checked
- **THEN** it contains no call to `Run Keyword If` or `Run Keyword Unless`

#### Scenario: No redundant screenshot teardown in rf-browser
- **WHEN** rf-browser `SKILL.md` is read
- **THEN** it does not recommend `Test Teardown    Run Keyword If Test Failed    Take Screenshot`
- **AND** it states that Browser takes a screenshot on failure through `run_on_failure`

### Requirement: Deterministic keyword checker gates CI

The repository SHALL provide a deterministic checker that extracts keyword calls from library-skill content and resolves them against libdoc of the skill's library plus the standard libraries. It SHALL exit non-zero when any call is unknown, deprecated, or a legacy `Run Keyword If`/`Unless`, unless an allowlist entry covers the call. Each allowlist entry SHALL name the skill, the file, the keyword and a reason. The checker SHALL run in a CI job and in the pytest suite. When a target library is not installed, the checker SHALL report that skill as skipped and SHALL NOT pass it silently.

#### Scenario: Clean repository passes
- **WHEN** the checker runs on the repository with all target libraries installed
- **THEN** it exits 0 and reports each checked skill with its file count

#### Scenario: Injected defect fails
- **WHEN** a fixture skill contains a call to a deprecated or nonexistent keyword that no allowlist entry covers
- **THEN** the checker exits non-zero and names the skill, file, line and keyword, with close-match suggestions when available

#### Scenario: Allowlisted exception passes
- **WHEN** a call is unknown but matches an allowlist entry for that skill and file
- **THEN** the checker does not fail on it

#### Scenario: Stale allowlist entry reported
- **WHEN** an allowlist entry matches no call in the current content
- **THEN** the checker fails and names the stale entry

#### Scenario: Missing library is not a silent pass
- **WHEN** a target library cannot be imported
- **THEN** the checker's output marks that skill as `skipped (library not installed)`
- **AND** in CI, where all target libraries are installed, a skipped skill fails the job

### Requirement: Fixes land in the canonical source and are synced

Keyword corrections SHALL be made in the root `skills/` directory and propagated to the plugin and VS Code copies by the sync script. The cross-channel drift check SHALL pass after the change.

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the fixes
- **THEN** the drift check reports no drift
- **AND** the checker gives the same result on the plugin copies as on the root copies
